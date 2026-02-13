# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""User tools.

Functions:
  gh_whoami -- get authenticated user profile
"""

from __future__ import annotations

from dedalus_mcp import HttpMethod, tool
from dedalus_mcp.types import ToolAnnotations

from gh.request import _opt_str, _str, request
from gh.types import UserInfo


@tool(
    description="Get the authenticated GitHub user's profile",
    tags=["user", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_whoami() -> UserInfo:
    """Get authenticated user profile.

    Returns:
        UserInfo with login, name, and email.

    """
    response = await request(HttpMethod.GET, "/user")
    if not response.success:
        msg = response.error or "Failed to get user profile"
        raise RuntimeError(msg)
    data = response.data if isinstance(response.data, dict) else {}
    user = UserInfo(
        login=_str(data.get("login")),
        name=_opt_str(data.get("name")),
        email=_opt_str(data.get("email")),
    )
    return user


user_tools = [gh_whoami]
