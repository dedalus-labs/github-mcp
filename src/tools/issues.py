# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Issue and comment tools.

Comments use the ``/issues/{number}/comments`` endpoint which works
for both issues *and* pull requests (GitHub treats them identically).

Functions:
  gh_list_issues   -- list issues (excludes PRs)
  gh_get_issue     -- get issue by number
  gh_create_issue  -- create a new issue
  gh_update_issue  -- update an existing issue
  gh_list_comments -- list comments on issue or PR
  gh_create_comment -- create a comment
"""

from __future__ import annotations

from dedalus_mcp import HttpMethod, tool
from dedalus_mcp.types import ToolAnnotations

from gh.guards import validate_owner_repo
from gh.request import _int, _labels, _nested_str, _opt_str, _str, build_url, request
from gh.types import CommentInfo, IssueInfo, JSONObject


def _parse_issue(raw: JSONObject) -> IssueInfo:
    """Parse a raw API dict into IssueInfo."""
    return IssueInfo(
        number=_int(raw.get("number")),
        title=_str(raw.get("title")),
        state=_str(raw.get("state")),
        author=_nested_str(raw.get("user"), "login"),
        labels=_labels(raw.get("labels")),
        created_at=_opt_str(raw.get("created_at")),
    )


def _parse_comment(raw: JSONObject) -> CommentInfo:
    """Parse a raw API dict into CommentInfo."""
    return CommentInfo(
        id=_int(raw.get("id")),
        author=_nested_str(raw.get("user"), "login"),
        body=_str(raw.get("body")),
        created_at=_opt_str(raw.get("created_at")),
    )


# --- Issues ---


@tool(
    description="List issues in a GitHub repository (excludes pull requests)",
    tags=["issues", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: str | None = None,
    assignee: str | None = None,
    per_page: int = 30,
    page: int = 1,
) -> list[IssueInfo]:
    """List issues (pull requests are excluded from results).

    Args:
        owner: Repository owner.
        repo: Repository name.
        state: Issue state ("open", "closed", "all").
        labels: Comma-separated label names to filter by.
        assignee: Filter by assignee login.
        per_page: Results per page (default 30).
        page: Page number (default 1).

    Returns:
        List of IssueInfo.

    """
    validate_owner_repo(owner, repo)
    url = build_url(
        f"/repos/{owner}/{repo}/issues",
        state=state,
        labels=labels,
        assignee=assignee,
        per_page=per_page,
        page=page,
    )
    response = await request(HttpMethod.GET, url)
    if not response.success:
        msg = response.error or "Failed to list issues"
        raise RuntimeError(msg)
    items = response.data if isinstance(response.data, list) else []
    issues = [_parse_issue(item) for item in items if "pull_request" not in item]
    return issues


@tool(
    description="Get a specific issue by number",
    tags=["issues", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_get_issue(owner: str, repo: str, issue_number: int) -> IssueInfo:
    """Get issue details.

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue number.

    Returns:
        IssueInfo.

    """
    validate_owner_repo(owner, repo)
    response = await request(
        HttpMethod.GET, f"/repos/{owner}/{repo}/issues/{issue_number}"
    )
    if not response.success:
        msg = response.error or "Failed to get issue"
        raise RuntimeError(msg)
    issue = _parse_issue(response.data if isinstance(response.data, dict) else {})
    return issue


@tool(
    description="Create a new issue in a GitHub repository",
    tags=["issues", "write"],
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def gh_create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> IssueInfo:
    """Create an issue.

    Args:
        owner: Repository owner.
        repo: Repository name.
        title: Issue title.
        body: Issue body (Markdown).
        labels: Label names to apply.
        assignees: Usernames to assign.

    Returns:
        IssueInfo of created issue.

    """
    validate_owner_repo(owner, repo)
    payload: JSONObject = {"title": title}
    if body:
        payload["body"] = body
    if labels:
        payload["labels"] = labels
    if assignees:
        payload["assignees"] = assignees
    response = await request(HttpMethod.POST, f"/repos/{owner}/{repo}/issues", payload)
    if not response.success:
        msg = response.error or "Failed to create issue"
        raise RuntimeError(msg)
    issue = _parse_issue(response.data if isinstance(response.data, dict) else {})
    return issue


@tool(
    description="Update an existing issue (title, body, state, labels, assignees)",
    tags=["issues", "write"],
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def gh_update_issue(
    owner: str,
    repo: str,
    issue_number: int,
    title: str | None = None,
    body: str | None = None,
    state: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> IssueInfo:
    """Update an issue.

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue number.
        title: New title.
        body: New body (Markdown).
        state: New state ("open" or "closed").
        labels: Replace all labels (full list).
        assignees: Replace all assignees (full list).

    Returns:
        IssueInfo of updated issue.

    """
    validate_owner_repo(owner, repo)
    payload: JSONObject = {}
    if title is not None:
        payload["title"] = title
    if body is not None:
        payload["body"] = body
    if state is not None:
        payload["state"] = state
    if labels is not None:
        payload["labels"] = labels
    if assignees is not None:
        payload["assignees"] = assignees
    response = await request(
        HttpMethod.PATCH, f"/repos/{owner}/{repo}/issues/{issue_number}", payload
    )
    if not response.success:
        msg = response.error or "Failed to update issue"
        raise RuntimeError(msg)
    issue = _parse_issue(response.data if isinstance(response.data, dict) else {})
    return issue


# --- Comments (shared between issues and PRs) ---


@tool(
    description="List comments on a GitHub issue or pull request",
    tags=["issues", "comments", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_comments(
    owner: str, repo: str, issue_number: int, per_page: int = 30, page: int = 1
) -> list[CommentInfo]:
    """List comments on an issue or PR.

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue or PR number.
        per_page: Results per page (default 30).
        page: Page number (default 1).

    Returns:
        List of CommentInfo.

    """
    validate_owner_repo(owner, repo)
    url = build_url(
        f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
        per_page=per_page,
        page=page,
    )
    response = await request(HttpMethod.GET, url)
    if not response.success:
        msg = response.error or "Failed to list comments"
        raise RuntimeError(msg)
    comments = [
        _parse_comment(item)
        for item in (response.data if isinstance(response.data, list) else [])
    ]
    return comments


@tool(
    description="Create a comment on a GitHub issue or pull request",
    tags=["issues", "comments", "write"],
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def gh_create_comment(
    owner: str, repo: str, issue_number: int, body: str
) -> CommentInfo:
    """Create a comment (works for both issues and PRs).

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue or PR number.
        body: Comment body (Markdown).

    Returns:
        CommentInfo of created comment.

    """
    validate_owner_repo(owner, repo)
    response = await request(
        HttpMethod.POST,
        f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
        {"body": body},
    )
    if not response.success:
        msg = response.error or "Failed to create comment"
        raise RuntimeError(msg)
    comment = _parse_comment(response.data if isinstance(response.data, dict) else {})
    return comment


issue_tools = [
    gh_list_issues,
    gh_get_issue,
    gh_create_issue,
    gh_update_issue,
    gh_list_comments,
    gh_create_comment,
]
