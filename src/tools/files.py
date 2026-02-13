# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""File content tools.

Returns GhResult (raw API response) because file content payloads
(base64 data, metadata) are most useful to the model unprocessed.

Functions:
  gh_get_file    -- get file contents (base64 for binary)
  gh_put_file    -- create or update a file
  gh_delete_file -- delete a file
"""

from __future__ import annotations

from dedalus_mcp import HttpMethod, tool
from dedalus_mcp.types import ToolAnnotations

from gh.guards import validate_owner_repo, validate_path
from gh.request import build_url, request
from gh.types import (  # noqa: TC001 — needed at runtime for tool schema
    GhResult,
    JSONObject,
)


@tool(
    description="Get file contents from a GitHub repository",
    tags=["files", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_get_file(
    owner: str, repo: str, path: str, ref: str | None = None
) -> GhResult:
    """Get file contents (base64 encoded for binary).

    Args:
        owner: Repository owner.
        repo: Repository name.
        path: File path in repo.
        ref: Git ref (branch, tag, commit SHA).

    Returns:
        GhResult with file content and metadata.

    """
    validate_owner_repo(owner, repo)
    validate_path(path)
    url = build_url(f"/repos/{owner}/{repo}/contents/{path}", ref=ref)
    result = await request(HttpMethod.GET, url)
    return result


@tool(
    description="Create or update a file in a GitHub repository",
    tags=["files", "write"],
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def gh_put_file(
    owner: str,
    repo: str,
    path: str,
    content_base64: str,
    message: str,
    branch: str | None = None,
    sha: str | None = None,
) -> GhResult:
    """Create or update file.

    Args:
        owner: Repository owner.
        repo: Repository name.
        path: File path in repo.
        content_base64: Base64-encoded file content.
        message: Commit message.
        branch: Target branch (default: repo default).
        sha: SHA of existing file (required for updates).

    Returns:
        GhResult with commit info.

    """
    validate_owner_repo(owner, repo)
    validate_path(path)
    body: JSONObject = {"message": message, "content": content_base64}
    if branch:
        body["branch"] = branch
    if sha:
        body["sha"] = sha
    result = await request(
        HttpMethod.PUT, f"/repos/{owner}/{repo}/contents/{path}", body
    )
    return result


@tool(
    description="Delete a file from a GitHub repository",
    tags=["files", "write"],
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
async def gh_delete_file(
    owner: str, repo: str, path: str, message: str, sha: str, branch: str | None = None
) -> GhResult:
    """Delete a file.

    Args:
        owner: Repository owner.
        repo: Repository name.
        path: File path in repo.
        message: Commit message.
        sha: SHA of file to delete.
        branch: Target branch (default: repo default).

    Returns:
        GhResult with commit info.

    """
    validate_owner_repo(owner, repo)
    validate_path(path)
    body: JSONObject = {"message": message, "sha": sha}
    if branch:
        body["branch"] = branch
    result = await request(
        HttpMethod.DELETE, f"/repos/{owner}/{repo}/contents/{path}", body
    )
    return result


file_tools = [gh_get_file, gh_put_file, gh_delete_file]
