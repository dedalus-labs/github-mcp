# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Commit, status check, and check run tools.

Functions:
  gh_list_commits         -- list commits in a repo
  gh_get_commit_status    -- get combined status for a ref (legacy Status API)
  gh_list_commit_statuses -- list individual status checks (legacy Status API)
  gh_list_check_runs      -- list check runs for a ref (Actions / Checks API)
"""

from __future__ import annotations

from dedalus_mcp import HttpMethod, tool
from dedalus_mcp.types import ToolAnnotations

from gh.guards import validate_owner_repo, validate_ref
from gh.request import _int, _nested_str, _opt_str, _str, build_url, request
from gh.types import CheckRunInfo, CommitInfo, CommitStatusInfo, GhResult


@tool(
    description="List commits in a repository",
    tags=["commits", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_commits(
    owner: str,
    repo: str,
    sha: str | None = None,
    path: str | None = None,
    author: str | None = None,
    per_page: int = 30,
    page: int = 1,
) -> list[CommitInfo]:
    """List commits.

    Args:
        owner: Repository owner.
        repo: Repository name.
        sha: Branch name or commit SHA to start listing from.
        path: Only commits touching this file path.
        author: Filter by author (GitHub login or email).
        per_page: Results per page (default 30).
        page: Page number (default 1).

    Returns:
        List of CommitInfo.

    """
    validate_owner_repo(owner, repo)
    url = build_url(
        f"/repos/{owner}/{repo}/commits",
        sha=sha,
        path=path,
        author=author,
        per_page=per_page,
        page=page,
    )
    response = await request(HttpMethod.GET, url)
    if not response.success:
        msg = response.error or "Failed to list commits"
        raise RuntimeError(msg)
    items = response.data if isinstance(response.data, list) else []
    results: list[CommitInfo] = []
    for entry in items:
        raw_commit = entry.get("commit")
        commit_obj = raw_commit if isinstance(raw_commit, dict) else {}
        raw_author = commit_obj.get("author")
        commit_author = raw_author if isinstance(raw_author, dict) else {}
        results.append(
            CommitInfo(
                sha=_str(entry.get("sha")),
                message=_str(commit_obj.get("message")),
                author=_nested_str(entry.get("author"), "login"),
                date=_opt_str(commit_author.get("date")),
            )
        )
    return results


@tool(
    description="Get combined commit status for a git ref",
    tags=["commits", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_get_commit_status(owner: str, repo: str, ref: str) -> GhResult:
    """Get combined status for a ref.

    Args:
        owner: Repository owner.
        repo: Repository name.
        ref: Git ref (branch, tag, commit SHA).

    Returns:
        GhResult with combined status object.

    """
    validate_owner_repo(owner, repo)
    validate_ref(ref)
    result = await request(
        HttpMethod.GET, f"/repos/{owner}/{repo}/commits/{ref}/status"
    )
    return result


@tool(
    description="List individual status checks for a git ref",
    tags=["commits", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_commit_statuses(
    owner: str, repo: str, ref: str
) -> list[CommitStatusInfo]:
    """List status checks for a ref.

    Args:
        owner: Repository owner.
        repo: Repository name.
        ref: Git ref (branch, tag, commit SHA).

    Returns:
        List of CommitStatusInfo.

    """
    validate_owner_repo(owner, repo)
    validate_ref(ref)
    response = await request(
        HttpMethod.GET, f"/repos/{owner}/{repo}/commits/{ref}/statuses"
    )
    if not response.success:
        msg = response.error or "Failed to list commit statuses"
        raise RuntimeError(msg)
    statuses = [
        CommitStatusInfo(
            state=_str(entry.get("state")),
            context=_str(entry.get("context")),
            description=_opt_str(entry.get("description")),
        )
        for entry in (response.data if isinstance(response.data, list) else [])
    ]
    return statuses


# --- Check Runs (Actions / Checks API) ---


@tool(
    description=(
        "List check runs for a git ref (branch, tag, or SHA). "
        "This is the modern Checks API used by GitHub Actions — "
        "use this instead of gh_get_commit_status for Actions CI results."
    ),
    tags=["commits", "actions", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_check_runs(
    owner: str, repo: str, ref: str, per_page: int = 30, page: int = 1
) -> list[CheckRunInfo]:
    """List check runs for a ref.

    Args:
        owner: Repository owner.
        repo: Repository name.
        ref: Git ref (branch, tag, commit SHA).
        per_page: Results per page (default 30).
        page: Page number (default 1).

    Returns:
        List of CheckRunInfo.

    """
    validate_owner_repo(owner, repo)
    validate_ref(ref)
    url = build_url(
        f"/repos/{owner}/{repo}/commits/{ref}/check-runs", per_page=per_page, page=page
    )
    response = await request(HttpMethod.GET, url)
    if not response.success:
        msg = response.error or "Failed to list check runs"
        raise RuntimeError(msg)
    items = (
        response.data.get("check_runs", []) if isinstance(response.data, dict) else []
    )
    check_runs = [
        CheckRunInfo(
            id=_int(check.get("id")),
            name=_str(check.get("name")),
            status=_str(check.get("status")),
            conclusion=_opt_str(check.get("conclusion")),
            started_at=_opt_str(check.get("started_at")),
            completed_at=_opt_str(check.get("completed_at")),
        )
        for check in items
    ]
    return check_runs


commit_tools = [
    gh_list_commits,
    gh_get_commit_status,
    gh_list_commit_statuses,
    gh_list_check_runs,
]
