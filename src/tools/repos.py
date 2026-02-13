# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Repository, branch, and comparison tools.

Functions:
  gh_list_repos    -- list authenticated user's repos
  gh_get_repo      -- get repo details
  gh_list_branches -- list branches in a repo
  gh_create_ref    -- create a git ref (branch/tag) remotely
  gh_delete_branch -- delete a branch remotely
  gh_compare       -- compare two refs (diff, commits, files)
"""

from __future__ import annotations

from dedalus_mcp import HttpMethod, tool
from dedalus_mcp.types import ToolAnnotations

from gh.guards import validate_owner_repo
from gh.request import _bool, _int, _nested_str, _opt_str, _str, build_url, request
from gh.types import (
    BranchInfo,
    CommitInfo,
    CompareInfo,
    GhResult,
    JSONObject,
    PrFileInfo,
    RepoInfo,
)


def _parse_repo(raw: dict) -> RepoInfo:
    """Parse a raw API dict into RepoInfo."""
    return RepoInfo(
        name=_str(raw.get("name")),
        full_name=_str(raw.get("full_name")),
        description=_opt_str(raw.get("description")),
        private=_bool(raw.get("private")),
        stars=_int(raw.get("stargazers_count")),
        language=_opt_str(raw.get("language")),
        default_branch=_str(raw.get("default_branch"), "main"),
        updated_at=_opt_str(raw.get("updated_at")),
    )


# --- Repositories ---


@tool(
    description="List repositories for the authenticated user",
    tags=["repos", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_repos(per_page: int = 30, page: int = 1) -> list[RepoInfo]:
    """List user's repositories sorted by last update.

    Args:
        per_page: Results per page (default 30, max 100).
        page: Page number (default 1).

    Returns:
        List of RepoInfo summaries.

    """
    url = build_url("/user/repos", per_page=per_page, page=page, sort="updated")
    response = await request(HttpMethod.GET, url)
    if not response.success:
        msg = response.error or "Failed to list repos"
        raise RuntimeError(msg)
    items = response.data if isinstance(response.data, list) else []
    repos = [_parse_repo(item) for item in items]
    return repos


@tool(
    description="Get details for a specific GitHub repository",
    tags=["repos", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_get_repo(owner: str, repo: str) -> RepoInfo:
    """Get repository details.

    Args:
        owner: Repository owner (user or org).
        repo: Repository name.

    Returns:
        RepoInfo with full details.

    """
    validate_owner_repo(owner, repo)
    response = await request(HttpMethod.GET, f"/repos/{owner}/{repo}")
    if not response.success:
        msg = response.error or "Failed to get repo"
        raise RuntimeError(msg)
    info = _parse_repo(response.data if isinstance(response.data, dict) else {})
    return info


# --- Branches ---


@tool(
    description="List branches in a GitHub repository",
    tags=["repos", "branches", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_branches(
    owner: str, repo: str, per_page: int = 30, page: int = 1
) -> list[BranchInfo]:
    """List branches.

    Args:
        owner: Repository owner.
        repo: Repository name.
        per_page: Results per page (default 30).
        page: Page number (default 1).

    Returns:
        List of BranchInfo.

    """
    validate_owner_repo(owner, repo)
    url = build_url(f"/repos/{owner}/{repo}/branches", per_page=per_page, page=page)
    response = await request(HttpMethod.GET, url)
    if not response.success:
        msg = response.error or "Failed to list branches"
        raise RuntimeError(msg)
    branches = [
        BranchInfo(
            name=_str(branch.get("name")),
            sha=_str(_nested_str(branch.get("commit"), "sha")),
            protected=_bool(branch.get("protected")),
        )
        for branch in (response.data if isinstance(response.data, list) else [])
    ]
    return branches


# --- Git Refs ---


@tool(
    description="Create a git ref (branch or tag) remotely without a local checkout",
    tags=["repos", "branches", "write"],
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def gh_create_ref(owner: str, repo: str, ref: str, sha: str) -> GhResult:
    """Create a git reference.

    Args:
        owner: Repository owner.
        repo: Repository name.
        ref: Full ref name (e.g. "refs/heads/my-branch").
        sha: SHA to point the ref at.

    Returns:
        GhResult with the created ref.

    """
    validate_owner_repo(owner, repo)
    payload: JSONObject = {"ref": ref, "sha": sha}
    result = await request(HttpMethod.POST, f"/repos/{owner}/{repo}/git/refs", payload)
    return result


@tool(
    description="Delete a branch remotely (e.g. post-merge cleanup)",
    tags=["repos", "branches", "write"],
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
async def gh_delete_branch(owner: str, repo: str, branch: str) -> GhResult:
    """Delete a branch via the Git References API.

    Args:
        owner: Repository owner.
        repo: Repository name.
        branch: Branch name (without refs/heads/ prefix).

    Returns:
        GhResult (empty on success — 204 response).

    """
    validate_owner_repo(owner, repo)
    if not branch:
        msg = "Branch name cannot be empty"
        raise ValueError(msg)
    result = await request(
        HttpMethod.DELETE, f"/repos/{owner}/{repo}/git/refs/heads/{branch}"
    )
    return result


# --- Comparison ---


@tool(
    description=(
        "Compare two git refs — see commits and files changed between them. "
        "Useful for reviewing what a branch introduces without a local checkout."
    ),
    tags=["repos", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_compare(owner: str, repo: str, base: str, head: str) -> CompareInfo:
    """Compare two refs (branches, tags, or SHAs).

    Args:
        owner: Repository owner.
        repo: Repository name.
        base: Base ref (e.g. "main").
        head: Head ref (e.g. "feature-branch").

    Returns:
        CompareInfo with status, commit count, files, and commits.

    """
    validate_owner_repo(owner, repo)
    response = await request(
        HttpMethod.GET, f"/repos/{owner}/{repo}/compare/{base}...{head}"
    )
    if not response.success:
        msg = response.error or f"Failed to compare {base}...{head}"
        raise RuntimeError(msg)
    data = response.data if isinstance(response.data, dict) else {}

    raw_files_val = data.get("files")
    raw_files = raw_files_val if isinstance(raw_files_val, list) else []
    files = [
        PrFileInfo(
            filename=_str(entry.get("filename")),
            status=_str(entry.get("status")),
            additions=_int(entry.get("additions")),
            deletions=_int(entry.get("deletions")),
            changes=_int(entry.get("changes")),
        )
        for entry in raw_files
    ]

    raw_commits_val = data.get("commits")
    raw_commits = raw_commits_val if isinstance(raw_commits_val, list) else []
    commits: list[CommitInfo] = []
    for entry in raw_commits:
        raw_commit = entry.get("commit")
        commit_obj = raw_commit if isinstance(raw_commit, dict) else {}
        raw_author = commit_obj.get("author")
        commit_author = raw_author if isinstance(raw_author, dict) else {}
        commits.append(
            CommitInfo(
                sha=_str(entry.get("sha")),
                message=_str(commit_obj.get("message")),
                author=_nested_str(entry.get("author"), "login"),
                date=_opt_str(commit_author.get("date")),
            )
        )

    result = CompareInfo(
        status=_str(data.get("status")),
        ahead_by=_int(data.get("ahead_by")),
        behind_by=_int(data.get("behind_by")),
        total_commits=_int(data.get("total_commits")),
        files=files,
        commits=commits,
    )
    return result


repo_tools = [
    gh_list_repos,
    gh_get_repo,
    gh_list_branches,
    gh_create_ref,
    gh_delete_branch,
    gh_compare,
]
