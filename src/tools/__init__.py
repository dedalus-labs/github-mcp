# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Tool registry for github-mcp.

Modules:
  users   -- gh_whoami
  repos   -- gh_list_repos, gh_get_repo, gh_list_branches,
             gh_create_ref, gh_delete_branch, gh_compare
  files   -- gh_get_file, gh_put_file, gh_delete_file
  issues  -- gh_list_issues, gh_get_issue, gh_create_issue, gh_update_issue,
             gh_list_comments, gh_create_comment
  pulls   -- gh_list_prs, gh_get_pr, gh_create_pr, gh_update_pr, gh_merge_pr,
             gh_list_pr_files, gh_list_pr_reviews, gh_list_pr_review_comments
  actions -- gh_list_workflows, gh_list_workflow_runs, gh_dispatch_workflow,
             gh_rerun_workflow, gh_ci_diagnosis
  commits -- gh_list_commits, gh_get_commit_status, gh_list_commit_statuses,
             gh_list_check_runs
  search  -- gh_search_code, gh_search_issues
"""

from __future__ import annotations

from tools.actions import action_tools
from tools.commits import commit_tools
from tools.files import file_tools
from tools.issues import issue_tools
from tools.pulls import pr_tools
from tools.repos import repo_tools
from tools.search import search_tools
from tools.users import user_tools


gh_tools = [
    *user_tools,
    *repo_tools,
    *file_tools,
    *issue_tools,
    *pr_tools,
    *action_tools,
    *commit_tools,
    *search_tools,
]
