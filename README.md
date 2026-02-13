# github-mcp

A GitHub MCP server built with the Dedalus MCP framework.

Connects to the GitHub REST and GraphQL APIs via a personal access token
(or OAuth through Dedalus Auth) and exposes LLM-friendly tools for
repositories, issues, pull requests, Actions CI, search, and more.

## Features

- **Repositories**: list, inspect, branch enumeration, create/delete branches, compare refs
- **Files**: read, create/update, delete
- **Issues & comments**: CRUD, filtering, labels, assignees
- **Pull requests**: list, inspect, create, update, merge, changed files
- **PR reviews**: list reviews, inline code review comments
- **Actions CI**: workflows, runs, dispatch, rerun, step-level failure diagnosis
- **Commits & checks**: history, legacy Status API, modern Check Runs API
- **Search**: code search, issue/PR search across GitHub

## Setup

```bash
cp .env.example .env
# Edit .env with your keys
```

Required:
- `GITHUB_TOKEN` — a GitHub PAT (classic or fine-grained). Needs `repo` scope at minimum.

Optional:
- `GITHUB_BASE_URL` — defaults to `https://api.github.com` (set for GitHub Enterprise)
- `DEDALUS_API_KEY` — your Dedalus API key (for deployed usage)
- `DEDALUS_API_URL` — defaults to `https://api.dedaluslabs.ai`
- `DEDALUS_AS_URL` — defaults to `https://as.dedaluslabs.ai`

## Usage

### Run the server

```bash
uv run src/main.py
```

Starts on `http://127.0.0.1:8080/mcp` (Streamable HTTP, stateless).

### Test locally

Verify your connection config and token work without deploying:

```bash
PYTHONPATH=src uv run python -c "
import asyncio
from dotenv import load_dotenv; load_dotenv()
from dedalus_mcp.testing import ConnectionTester, TestRequest
from gh.config import github

async def test():
    t = ConnectionTester.from_env(github)
    r = await t.request(TestRequest(path='/user'))
    print(f'{r.status} — {r.body[\"login\"]}' if r.success else f'FAIL: {r.status}')

asyncio.run(test())
"
```

A full client demo (DedalusRunner + OAuth browser flow) is in `src/_client.py`.

### Lint and typecheck

```bash
uv run --group lint ruff check src/
uv run --group lint ruff format --check src/
uv run --group lint ty check
```

## Available Tools

| Tool | Description | R/W |
|------|-------------|-----|
| `gh_whoami` | Get the authenticated user's profile | R |
| `gh_list_repos` | List repositories for the authenticated user | R |
| `gh_get_repo` | Get details for a specific repository | R |
| `gh_list_branches` | List branches in a repository | R |
| `gh_create_ref` | Create a git ref (branch/tag) remotely | W |
| `gh_delete_branch` | Delete a branch remotely | W |
| `gh_compare` | Compare two refs — commits and files changed | R |
| `gh_get_file` | Get file contents from a repository | R |
| `gh_put_file` | Create or update a file in a repository | W |
| `gh_delete_file` | Delete a file from a repository | W |
| `gh_list_issues` | List issues in a repository (excludes pull requests) | R |
| `gh_get_issue` | Get a specific issue by number | R |
| `gh_create_issue` | Create a new issue | W |
| `gh_update_issue` | Update an existing issue (title, body, state, labels, assignees) | W |
| `gh_list_comments` | List comments on an issue or pull request | R |
| `gh_create_comment` | Create a comment on an issue or pull request | W |
| `gh_list_prs` | List pull requests in a repository | R |
| `gh_get_pr` | Get a specific pull request by number | R |
| `gh_create_pr` | Create a pull request | W |
| `gh_update_pr` | Update a PR (title, body, state, base branch) | W |
| `gh_merge_pr` | Merge a pull request | W |
| `gh_list_pr_files` | List files changed in a pull request | R |
| `gh_list_pr_reviews` | List reviews on a pull request | R |
| `gh_list_pr_review_comments` | List inline code review comments on a PR | R |
| `gh_list_workflows` | List GitHub Actions workflows | R |
| `gh_list_workflow_runs` | List workflow runs | R |
| `gh_dispatch_workflow` | Trigger a workflow via dispatch event | W |
| `gh_rerun_workflow` | Re-run a workflow | W |
| `gh_ci_diagnosis` | Diagnose CI failures — run + jobs + failed steps | R |
| `gh_list_commits` | List commits in a repository | R |
| `gh_get_commit_status` | Get combined commit status for a ref (legacy Status API) | R |
| `gh_list_commit_statuses` | List individual status checks (legacy Status API) | R |
| `gh_list_check_runs` | List check runs for a ref (modern Checks API / Actions) | R |
| `gh_search_code` | Search code across GitHub repositories | R |
| `gh_search_issues` | Search issues and pull requests across GitHub | R |

## Notes

- Auth uses `token {api_key}` header format (GitHub PAT). For fine-grained tokens, grant the
  specific repository permissions you need. Classic tokens need at least `repo` scope.
- All list endpoints accept `per_page` (default 30, max 100) and pagination parameters.
- `gh_list_issues` excludes pull requests by default (GitHub's REST API returns PRs as issues).
- `gh_list_check_runs` is the modern Checks API — use this for GitHub Actions results.
  `gh_get_commit_status` / `gh_list_commit_statuses` cover the legacy Status API only.
- `gh_ci_diagnosis` is a compound tool: resolves a run (by ID or latest on a branch),
  fetches all jobs, and returns step-level detail so the agent can see *which step* failed.
- `gh_compare` returns commits and changed files between two refs — useful for reviewing
  what a branch introduces without a local checkout.
- `gh_create_ref` expects the full ref path (e.g. `refs/heads/my-branch`).
  `gh_delete_branch` takes just the branch name.
- `gh_list_pr_review_comments` returns inline (line-level) code review comments, which are
  distinct from general issue comments returned by `gh_list_comments`.
- `gh_search_code` requires at least one qualifier (e.g., `repo:`, `org:`, `user:`).
- Write tools require a token with write permissions on the target repository.
- `GITHUB_BASE_URL` supports GitHub Enterprise Server (`https://github.example.com/api/v3`).

## License

MIT
