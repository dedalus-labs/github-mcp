# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Pull request tools.

Functions:
  gh_list_prs               -- list pull requests
  gh_get_pr                 -- get PR by number
  gh_create_pr              -- create a pull request
  gh_update_pr              -- update an existing PR
  gh_merge_pr               -- merge a pull request
  gh_list_pr_files          -- list files changed in a PR
  gh_list_pr_reviews        -- list reviews on a PR
  gh_list_pr_review_comments -- list inline code review comments
"""

from __future__ import annotations

from dedalus_mcp import HttpMethod, tool
from dedalus_mcp.types import ToolAnnotations

from gh.guards import validate_owner_repo
from gh.request import _bool, _int, _nested_str, _opt_str, _str, build_url, request
from gh.types import (
    GhResult,
    JSONObject,
    PrFileInfo,
    PrInfo,
    PrReviewCommentInfo,
    PrReviewInfo,
)


def _parse_pr(raw: JSONObject) -> PrInfo:
    """Parse a raw API dict into PrInfo."""
    mergeable = raw.get("mergeable")
    return PrInfo(
        number=_int(raw.get("number")),
        title=_str(raw.get("title")),
        state=_str(raw.get("state")),
        head=_str(_nested_str(raw.get("head"), "ref")),
        base=_str(_nested_str(raw.get("base"), "ref")),
        author=_nested_str(raw.get("user"), "login"),
        draft=_bool(raw.get("draft")),
        mergeable=mergeable if isinstance(mergeable, bool) else None,
    )


@tool(
    description="List pull requests in a GitHub repository",
    tags=["prs", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_prs(
    owner: str, repo: str, state: str = "open", per_page: int = 30, page: int = 1
) -> list[PrInfo]:
    """List pull requests.

    Args:
        owner: Repository owner.
        repo: Repository name.
        state: PR state ("open", "closed", "all").
        per_page: Results per page (default 30).
        page: Page number (default 1).

    Returns:
        List of PrInfo.

    """
    validate_owner_repo(owner, repo)
    url = build_url(
        f"/repos/{owner}/{repo}/pulls", state=state, per_page=per_page, page=page
    )
    response = await request(HttpMethod.GET, url)
    if not response.success:
        msg = response.error or "Failed to list PRs"
        raise RuntimeError(msg)
    prs = [
        _parse_pr(item)
        for item in (response.data if isinstance(response.data, list) else [])
    ]
    return prs


@tool(
    description="Get a specific pull request by number",
    tags=["prs", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_get_pr(owner: str, repo: str, pr_number: int) -> PrInfo:
    """Get pull request details.

    Args:
        owner: Repository owner.
        repo: Repository name.
        pr_number: PR number.

    Returns:
        PrInfo.

    """
    validate_owner_repo(owner, repo)
    response = await request(HttpMethod.GET, f"/repos/{owner}/{repo}/pulls/{pr_number}")
    if not response.success:
        msg = response.error or "Failed to get PR"
        raise RuntimeError(msg)
    pr = _parse_pr(response.data if isinstance(response.data, dict) else {})
    return pr


@tool(
    description="Create a pull request",
    tags=["prs", "write"],
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def gh_create_pr(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str | None = None,
    draft: bool = False,  # noqa: FBT001, FBT002
) -> PrInfo:
    """Create a pull request.

    Args:
        owner: Repository owner.
        repo: Repository name.
        title: PR title.
        head: Branch containing changes.
        base: Branch to merge into.
        body: PR description (Markdown).
        draft: Create as draft PR.

    Returns:
        PrInfo of created PR.

    """
    validate_owner_repo(owner, repo)
    payload: JSONObject = {"title": title, "head": head, "base": base, "draft": draft}
    if body:
        payload["body"] = body
    response = await request(HttpMethod.POST, f"/repos/{owner}/{repo}/pulls", payload)
    if not response.success:
        msg = response.error or "Failed to create PR"
        raise RuntimeError(msg)
    pr = _parse_pr(response.data if isinstance(response.data, dict) else {})
    return pr


@tool(
    description="Update a pull request (title, body, state, base branch)",
    tags=["prs", "write"],
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def gh_update_pr(
    owner: str,
    repo: str,
    pr_number: int,
    title: str | None = None,
    body: str | None = None,
    state: str | None = None,
    base: str | None = None,
) -> PrInfo:
    """Update an existing pull request.

    Args:
        owner: Repository owner.
        repo: Repository name.
        pr_number: PR number.
        title: New title (optional).
        body: New description (optional).
        state: New state — "open" or "closed" (optional).
        base: New base branch (optional).

    Returns:
        Updated PrInfo.

    """
    validate_owner_repo(owner, repo)
    payload: JSONObject = {}
    if title is not None:
        payload["title"] = title
    if body is not None:
        payload["body"] = body
    if state is not None:
        payload["state"] = state
    if base is not None:
        payload["base"] = base
    if not payload:
        msg = "At least one field (title, body, state, base) must be provided"
        raise ValueError(msg)
    response = await request(
        HttpMethod.PATCH, f"/repos/{owner}/{repo}/pulls/{pr_number}", payload
    )
    if not response.success:
        msg = response.error or "Failed to update PR"
        raise RuntimeError(msg)
    pr = _parse_pr(response.data if isinstance(response.data, dict) else {})
    return pr


@tool(
    description="Merge a pull request",
    tags=["prs", "write"],
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def gh_merge_pr(
    owner: str,
    repo: str,
    pr_number: int,
    merge_method: str = "merge",
    commit_title: str | None = None,
    commit_message: str | None = None,
) -> GhResult:
    """Merge a pull request.

    Args:
        owner: Repository owner.
        repo: Repository name.
        pr_number: PR number.
        merge_method: Merge strategy ("merge", "squash", "rebase").
        commit_title: Custom merge commit title.
        commit_message: Custom merge commit message.

    Returns:
        GhResult with merge status.

    """
    validate_owner_repo(owner, repo)
    payload: JSONObject = {"merge_method": merge_method}
    if commit_title:
        payload["commit_title"] = commit_title
    if commit_message:
        payload["commit_message"] = commit_message
    result = await request(
        HttpMethod.PUT, f"/repos/{owner}/{repo}/pulls/{pr_number}/merge", payload
    )
    return result


@tool(
    description="List files changed in a pull request",
    tags=["prs", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_pr_files(
    owner: str, repo: str, pr_number: int, per_page: int = 30, page: int = 1
) -> list[PrFileInfo]:
    """List files changed in a PR.

    Args:
        owner: Repository owner.
        repo: Repository name.
        pr_number: PR number.
        per_page: Results per page (default 30).
        page: Page number (default 1).

    Returns:
        List of PrFileInfo.

    """
    validate_owner_repo(owner, repo)
    url = build_url(
        f"/repos/{owner}/{repo}/pulls/{pr_number}/files", per_page=per_page, page=page
    )
    response = await request(HttpMethod.GET, url)
    if not response.success:
        msg = response.error or "Failed to list PR files"
        raise RuntimeError(msg)
    files = [
        PrFileInfo(
            filename=_str(entry.get("filename")),
            status=_str(entry.get("status")),
            additions=_int(entry.get("additions")),
            deletions=_int(entry.get("deletions")),
            changes=_int(entry.get("changes")),
        )
        for entry in (response.data if isinstance(response.data, list) else [])
    ]
    return files


# --- Reviews ---


@tool(
    description="List reviews on a pull request",
    tags=["prs", "reviews", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_pr_reviews(
    owner: str, repo: str, pr_number: int, per_page: int = 30, page: int = 1
) -> list[PrReviewInfo]:
    """List pull request reviews.

    Args:
        owner: Repository owner.
        repo: Repository name.
        pr_number: PR number.
        per_page: Results per page (default 30).
        page: Page number (default 1).

    Returns:
        List of PrReviewInfo.

    """
    validate_owner_repo(owner, repo)
    url = build_url(
        f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews", per_page=per_page, page=page
    )
    response = await request(HttpMethod.GET, url)
    if not response.success:
        msg = response.error or "Failed to list PR reviews"
        raise RuntimeError(msg)
    reviews = [
        PrReviewInfo(
            id=_int(review.get("id")),
            state=_str(review.get("state")),
            user=_nested_str(review.get("user"), "login"),
            body=_str(review.get("body")),
            submitted_at=_opt_str(review.get("submitted_at")),
        )
        for review in (response.data if isinstance(response.data, list) else [])
    ]
    return reviews


@tool(
    description="List inline code review comments on a pull request",
    tags=["prs", "reviews", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_pr_review_comments(
    owner: str, repo: str, pr_number: int, per_page: int = 30, page: int = 1
) -> list[PrReviewCommentInfo]:
    """List inline review comments (line-level feedback).

    Args:
        owner: Repository owner.
        repo: Repository name.
        pr_number: PR number.
        per_page: Results per page (default 30).
        page: Page number (default 1).

    Returns:
        List of PrReviewCommentInfo.

    """
    validate_owner_repo(owner, repo)
    url = build_url(
        f"/repos/{owner}/{repo}/pulls/{pr_number}/comments",
        per_page=per_page,
        page=page,
    )
    response = await request(HttpMethod.GET, url)
    if not response.success:
        msg = response.error or "Failed to list PR review comments"
        raise RuntimeError(msg)
    comments = [
        PrReviewCommentInfo(
            id=_int(entry.get("id")),
            path=_str(entry.get("path")),
            body=_str(entry.get("body")),
            user=_nested_str(entry.get("user"), "login"),
            line=entry.get("line") if isinstance(entry.get("line"), int) else None,
            side=_opt_str(entry.get("side")),
            created_at=_opt_str(entry.get("created_at")),
        )
        for entry in (response.data if isinstance(response.data, list) else [])
    ]
    return comments


pr_tools = [
    gh_list_prs,
    gh_get_pr,
    gh_create_pr,
    gh_update_pr,
    gh_merge_pr,
    gh_list_pr_files,
    gh_list_pr_reviews,
    gh_list_pr_review_comments,
]
