# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Typed models for GitHub API responses.

Enums:
  MergeMethod              -- pull request merge strategies

Result types (frozen dataclasses):
  GhResult                 -- raw API result (write ops / unstructured)
  UserInfo                 -- authenticated user profile
  RepoInfo                 -- repository summary
  BranchInfo               -- branch reference
  IssueInfo                -- issue summary
  CommentInfo              -- issue or PR comment
  PrInfo                   -- pull request summary
  PrFileInfo               -- file changed in a PR
  PrReviewInfo             -- pull request review
  PrReviewCommentInfo      -- inline code review comment
  WorkflowInfo             -- GitHub Actions workflow
  WorkflowRunInfo          -- workflow run
  WorkflowJobStep          -- step within a workflow job
  WorkflowJobInfo          -- job within a workflow run
  CiDiagnosisInfo          -- compound CI diagnosis (run + jobs + failures)
  CommitInfo               -- commit summary
  CommitStatusInfo         -- individual commit status check
  CheckRunInfo             -- GitHub Check Run (Actions CI)
  CompareInfo              -- comparison between two refs
  SearchResult             -- search result container

Type aliases:
  JSONPrimitive            -- scalar JSON values
  JSONValue                -- recursive JSON value (pre-3.12 TypeAlias)
  JSONObject               -- dict[str, JSONValue]
  JSONArray                -- list[JSONValue]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeAlias


# --- JSON types ---

JSONPrimitive: TypeAlias = str | int | float | bool | None
"""Scalar JSON values. Non-recursive, safe as plain union."""

JSONValue: TypeAlias = str | int | float | bool | dict[str, Any] | list[Any] | None
"""Recursive JSON value: primitive, object, or array.

Cannot be truly recursive with TypeAlias (pre-3.12); uses Any for nesting.
PEP 695 ``type`` statements (3.12+) resolve this via lazy evaluation.
"""

JSONObject: TypeAlias = dict[str, JSONValue]
"""JSON object: string keys mapped to JSON values."""

JSONArray: TypeAlias = list[JSONValue]
"""JSON array: ordered sequence of JSON values."""


# --- Enums ---


class MergeMethod(str, Enum):
    """Pull request merge strategies."""

    merge = "merge"
    squash = "squash"
    rebase = "rebase"


# --- Generic result ---


@dataclass(frozen=True, slots=True)
class GhResult:
    """Raw GitHub API result.

    Used for write operations that don't produce structured output
    (e.g. workflow dispatch returns 204) and as the internal request
    return type.
    """

    # fmt: off
    success: bool
    data:    JSONValue | None = None
    error:   str | None       = None
    # fmt: on


# --- User ---


@dataclass(frozen=True, slots=True)
class UserInfo:
    """Authenticated user profile."""

    # fmt: off
    login: str
    name:  str | None = None
    email: str | None = None
    # fmt: on


# --- Repositories ---


@dataclass(frozen=True, slots=True)
class RepoInfo:
    """Repository summary."""

    # fmt: off
    name:           str
    full_name:      str
    description:    str | None = None
    private:        bool       = False
    stars:          int        = 0
    language:       str | None = None
    default_branch: str        = "main"
    updated_at:     str | None = None
    # fmt: on


@dataclass(frozen=True, slots=True)
class BranchInfo:
    """Branch reference."""

    # fmt: off
    name:      str
    sha:       str
    protected: bool = False
    # fmt: on


# --- Issues ---


@dataclass(frozen=True, slots=True)
class IssueInfo:
    """Issue summary."""

    # fmt: off
    number:     int
    title:      str
    state:      str
    author:     str | None       = None
    labels:     list[str]        = field(default_factory=list)
    created_at: str | None       = None
    # fmt: on


@dataclass(frozen=True, slots=True)
class CommentInfo:
    """Issue or PR comment."""

    # fmt: off
    id:         int
    author:     str | None = None
    body:       str        = ""
    created_at: str | None = None
    # fmt: on


# --- Pull Requests ---


@dataclass(frozen=True, slots=True)
class PrInfo:
    """Pull request summary."""

    # fmt: off
    number:    int
    title:     str
    state:     str
    head:      str
    base:      str
    author:    str | None  = None
    draft:     bool        = False
    mergeable: bool | None = None
    # fmt: on


@dataclass(frozen=True, slots=True)
class PrFileInfo:
    """File changed in a pull request."""

    # fmt: off
    filename:  str
    status:    str
    additions: int = 0
    deletions: int = 0
    changes:   int = 0
    # fmt: on


@dataclass(frozen=True, slots=True)
class PrReviewInfo:
    """Pull request review."""

    # fmt: off
    id:           int
    state:        str
    user:         str | None = None
    body:         str        = ""
    submitted_at: str | None = None
    # fmt: on


@dataclass(frozen=True, slots=True)
class PrReviewCommentInfo:
    """Inline code review comment on a pull request."""

    # fmt: off
    id:         int
    path:       str
    body:       str        = ""
    user:       str | None = None
    line:       int | None = None
    side:       str | None = None
    created_at: str | None = None
    # fmt: on


# --- Actions / CI ---


@dataclass(frozen=True, slots=True)
class WorkflowInfo:
    """GitHub Actions workflow."""

    # fmt: off
    id:    int
    name:  str
    state: str
    # fmt: on


@dataclass(frozen=True, slots=True)
class WorkflowRunInfo:
    """Workflow run."""

    # fmt: off
    id:         int
    name:       str | None = None
    status:     str | None = None
    conclusion: str | None = None
    branch:     str | None = None
    created_at: str | None = None
    # fmt: on


@dataclass(frozen=True, slots=True)
class WorkflowJobStep:
    """A step within a workflow job."""

    # fmt: off
    name:       str
    status:     str
    conclusion: str | None = None
    number:     int        = 0
    # fmt: on


@dataclass(frozen=True, slots=True)
class WorkflowJobInfo:
    """A job within a workflow run."""

    # fmt: off
    id:         int
    name:       str
    status:     str
    conclusion: str | None            = None
    steps:      list[WorkflowJobStep] = field(default_factory=list)
    # fmt: on


@dataclass(frozen=True, slots=True)
class CiDiagnosisInfo:
    """Compound CI diagnosis — run metadata + jobs + failed jobs."""

    # fmt: off
    run_id:      int
    run_name:    str | None
    status:      str | None
    conclusion:  str | None
    branch:      str | None
    jobs:        list[WorkflowJobInfo]        = field(default_factory=list)
    failed_jobs: list[WorkflowJobInfo]        = field(default_factory=list)
    # fmt: on


# --- Commits ---


@dataclass(frozen=True, slots=True)
class CommitInfo:
    """Commit summary."""

    # fmt: off
    sha:    str
    message: str
    author: str | None = None
    date:   str | None = None
    # fmt: on


@dataclass(frozen=True, slots=True)
class CommitStatusInfo:
    """Individual commit status check."""

    # fmt: off
    state:       str
    context:     str
    description: str | None = None
    # fmt: on


@dataclass(frozen=True, slots=True)
class CheckRunInfo:
    """GitHub Check Run (Actions CI result)."""

    # fmt: off
    id:           int
    name:         str
    status:       str
    conclusion:   str | None = None
    started_at:   str | None = None
    completed_at: str | None = None
    # fmt: on


# --- Comparison ---


@dataclass(frozen=True, slots=True)
class CompareInfo:
    """Comparison between two git refs."""

    # fmt: off
    status:        str
    ahead_by:      int                   = 0
    behind_by:     int                   = 0
    total_commits: int                   = 0
    files:         list[PrFileInfo]      = field(default_factory=list)
    commits:       list[CommitInfo]      = field(default_factory=list)
    # fmt: on


# --- Search ---


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Search result container.

    ``items`` are left as raw dicts because the shape varies
    by search type (code vs issues vs repos).
    """

    # fmt: off
    total_count:        int
    incomplete_results: bool            = False
    items:              list[JSONObject] = field(default_factory=list)
    # fmt: on
