# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Input validation for GitHub API parameters.

Prevents malformed owner/repo/path values from reaching URL construction.

Functions:
  validate_owner(owner)            -- validate user or org name
  validate_repo(repo)              -- validate repository name
  validate_owner_repo(owner, repo) -- validate both
  validate_path(path)              -- validate file path (relative, no nulls)
  validate_ref(ref)                -- validate git ref (branch, tag, SHA)
"""

from __future__ import annotations

import re


# GitHub owner/repo names: alphanumeric, hyphens, underscores, dots.
_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


def validate_owner(owner: str) -> None:
    """Validate a GitHub owner (user or org) name."""
    if not owner or not _NAME_RE.match(owner):
        msg = f"Invalid GitHub owner: {owner!r}"
        raise ValueError(msg)


def validate_repo(repo: str) -> None:
    """Validate a repository name."""
    if not repo or not _NAME_RE.match(repo):
        msg = f"Invalid repository name: {repo!r}"
        raise ValueError(msg)


def validate_owner_repo(owner: str, repo: str) -> None:
    """Validate both owner and repo."""
    validate_owner(owner)
    validate_repo(repo)


def validate_path(path: str) -> None:
    """Validate a file path within a repository."""
    if not path:
        msg = "File path cannot be empty"
        raise ValueError(msg)
    if "\x00" in path:
        msg = "File path cannot contain null bytes"
        raise ValueError(msg)
    if path.startswith("/"):
        msg = "File path must be relative"
        raise ValueError(msg)


def validate_ref(ref: str) -> None:
    """Validate a git ref (branch, tag, SHA)."""
    if not ref:
        msg = "Git ref cannot be empty"
        raise ValueError(msg)
    if "\x00" in ref:
        msg = "Git ref cannot contain null bytes"
        raise ValueError(msg)
