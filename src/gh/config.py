# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""GitHub connection configuration.

Evaluated at import time, after ``load_dotenv()`` in ``main.py``
has already injected the .env file.

Objects:
  github -- Connection with token auth and configurable base URL
"""

from __future__ import annotations

import os

from dedalus_mcp.auth import Connection, SecretKeys


github = Connection(
    name="github-mcp",
    secrets=SecretKeys(token="GITHUB_TOKEN"),  # noqa: S106
    base_url=os.getenv("GITHUB_BASE_URL", "https://api.github.com"),
    auth_header_format="token {api_key}",
)
