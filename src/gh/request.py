# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""GitHub API request dispatch and response helpers.

Functions:
  request(method, path, body)    -- dispatch via Dedalus enclave
  build_url(endpoint, **params)  -- URL with query string (None-safe)

Coercion helpers (safe extraction from untyped API dicts):
  _str(val, default)             -- coerce to str
  _int(val, default)             -- coerce to int
  _opt_str(val)                  -- coerce to str | None
  _bool(val, *, default)         -- coerce to bool
  _nested_str(obj, key)          -- extract str from nested dict
  _labels(val)                   -- extract label names from label objects
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from dedalus_mcp import HttpMethod, HttpRequest, get_context

from gh.config import github
from gh.types import GhResult


# --- Request dispatch ---


async def request(
    method: HttpMethod, path: str, body: dict[str, Any] | None = None
) -> GhResult:
    """Execute a GitHub API request via Dedalus enclave.

    Args:
        method: HTTP method.
        path: API path (e.g. "/repos/{owner}/{repo}").
        body: JSON request body.

    Returns:
        GhResult wrapping the raw API response.

    """
    ctx = get_context()
    resp = await ctx.dispatch(github, HttpRequest(method=method, path=path, body=body))
    if resp.success and resp.response is not None:
        result = GhResult(success=True, data=resp.response.body)
        return result
    error = resp.error.message if resp.error else "Request failed"
    result = GhResult(success=False, error=error)
    return result


# --- URL helpers ---


def build_url(endpoint: str, **params: str | int | bool | None) -> str:
    """Build URL path with query parameters, omitting None values.

    Booleans are lowercased ("true"/"false") to match GitHub API conventions.

    Args:
        endpoint: Base URL path.
        **params: Query parameters (None values are dropped).

    Returns:
        URL path with encoded query string.

    """
    filtered: dict[str, str] = {}
    for key, val in params.items():
        if val is None:
            continue
        filtered[key] = str(val).lower() if isinstance(val, bool) else str(val)
    if not filtered:
        return endpoint
    url = f"{endpoint}?{urlencode(filtered)}"
    return url


# --- Coercion helpers (safe extraction from untyped API dicts) ---


def _str(val: Any, default: str = "") -> str:  # noqa: ANN401 — raw JSON extraction
    """Safely coerce to string."""
    return str(val) if val is not None else default


def _int(val: Any, default: int = 0) -> int:  # noqa: ANN401 — raw JSON extraction
    """Safely coerce to int."""
    if val is None:
        return default
    try:
        return int(val)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return default


def _opt_str(val: Any) -> str | None:  # noqa: ANN401 — raw JSON extraction
    """Safely coerce to optional string."""
    return str(val) if val is not None else None


def _bool(val: Any, *, default: bool = False) -> bool:  # noqa: ANN401 — raw JSON extraction
    """Safely coerce to bool."""
    return bool(val) if val is not None else default


def _nested_str(obj: Any, key: str) -> str | None:  # noqa: ANN401 — raw JSON extraction
    """Extract a string from a nested dict, e.g. ``d.get("user", {}).get("login")``."""
    if isinstance(obj, dict):
        return _opt_str(obj.get(key))
    return None


def _labels(val: Any) -> list[str]:  # noqa: ANN401 — raw JSON extraction
    """Extract label names from GitHub label objects."""
    if not isinstance(val, list):
        return []
    return [
        _str(label.get("name"))
        for label in val
        if isinstance(label, dict) and label.get("name")
    ]
