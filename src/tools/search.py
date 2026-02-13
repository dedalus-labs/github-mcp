# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""GitHub Search tools.

Functions:
  gh_search_code   -- search code across repos
  gh_search_issues -- search issues and pull requests
"""

from __future__ import annotations

from dedalus_mcp import HttpMethod, tool
from dedalus_mcp.types import ToolAnnotations

from gh.request import _bool, _int, build_url, request
from gh.types import SearchResult


@tool(
    description="Search for code across GitHub repositories",
    tags=["search", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_search_code(q: str, per_page: int = 30, page: int = 1) -> SearchResult:
    """Search code.

    Args:
        q: Search query (e.g. "addClass repo:jquery/jquery", "filename:.env").
        per_page: Results per page (default 30).
        page: Page number (default 1).

    Returns:
        SearchResult with matching files.

    """
    url = build_url("/search/code", q=q, per_page=per_page, page=page)
    response = await request(HttpMethod.GET, url)
    if not response.success:
        msg = response.error or "Failed to search code"
        raise RuntimeError(msg)
    data = response.data if isinstance(response.data, dict) else {}
    raw_items = data.get("items")
    result = SearchResult(
        total_count=_int(data.get("total_count")),
        incomplete_results=_bool(data.get("incomplete_results")),
        items=raw_items if isinstance(raw_items, list) else [],
    )
    return result


@tool(
    description="Search issues and pull requests across GitHub",
    tags=["search", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_search_issues(q: str, per_page: int = 30, page: int = 1) -> SearchResult:
    """Search issues and pull requests.

    Args:
        q: Search query (e.g. "bug label:bug", "is:pr is:open review:required").
        per_page: Results per page (default 30).
        page: Page number (default 1).

    Returns:
        SearchResult with matching issues/PRs.

    """
    url = build_url("/search/issues", q=q, per_page=per_page, page=page)
    response = await request(HttpMethod.GET, url)
    if not response.success:
        msg = response.error or "Failed to search issues"
        raise RuntimeError(msg)
    data = response.data if isinstance(response.data, dict) else {}
    raw_items = data.get("items")
    result = SearchResult(
        total_count=_int(data.get("total_count")),
        incomplete_results=_bool(data.get("incomplete_results")),
        items=raw_items if isinstance(raw_items, list) else [],
    )
    return result


search_tools = [gh_search_code, gh_search_issues]
