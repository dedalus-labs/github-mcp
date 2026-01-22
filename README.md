# GitHub MCP Server

A GitHub MCP server built with the [Dedalus MCP framework](https://dedaluslabs.ai). Provides secure access to GitHub APIs with credential encryption and JIT token exchange.

## Features

### Available Tools

#### User

| Tool | Description |
|------|-------------|
| `gh_whoami` | Get authenticated user's profile |

#### Repositories

| Tool | Description |
|------|-------------|
| `gh_list_repos` | List repositories for authenticated user |
| `gh_get_repo` | Get details for a specific repository |

#### Files

| Tool | Description |
|------|-------------|
| `gh_get_file` | Get file contents from a repository |
| `gh_put_file` | Create or update a file in a repository |
| `gh_delete_file` | Delete a file from a repository |

#### Issues

| Tool | Description |
|------|-------------|
| `gh_list_issues` | List issues in a repository |
| `gh_get_issue` | Get a specific issue by number |

#### Pull Requests

| Tool | Description |
|------|-------------|
| `gh_list_prs` | List pull requests in a repository |
| `gh_get_pr` | Get a specific pull request by number |

#### Workflows

| Tool | Description |
|------|-------------|
| `gh_list_workflows` | List GitHub Actions workflows |
| `gh_list_workflow_runs` | List workflow runs |
| `gh_dispatch_workflow` | Trigger a workflow via dispatch event |
| `gh_cancel_workflow_run` | Cancel a running workflow |
| `gh_rerun_workflow` | Re-run a workflow |

#### Variables & Secrets

| Tool | Description |
|------|-------------|
| `gh_list_actions_variables` | List Actions variables |
| `gh_list_secrets` | List Actions secrets (names only) |

#### Deployments & Environments

| Tool | Description |
|------|-------------|
| `gh_list_deployments` | List deployments |
| `gh_list_environments` | List environments |

#### Commit Status

| Tool | Description |
|------|-------------|
| `gh_get_commit_status` | Get combined commit status |
| `gh_list_commit_statuses` | List individual status checks |

#### Discussions

| Tool | Description |
|------|-------------|
| `gh_list_discussions` | List GitHub Discussions (GraphQL) |

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- GitHub Personal Access Token
- Dedalus API Key

## Setup

1. **Clone the repository**

```bash
git clone https://github.com/dedalus-labs/github-mcp.git
cd github-mcp
```

2. **Install dependencies**

```bash
uv sync
```

3. **Configure environment variables**

Create a `.env` file based on .env.example:


## Client Usage

### Using DedalusRunner

```python
import asyncio
import os

from dotenv import load_dotenv
from dedalus_labs import AsyncDedalus, DedalusRunner
from dedalus_mcp.auth import Connection, SecretKeys, SecretValues

load_dotenv()

# Define the GitHub connection
github = Connection(
    name="github-mcp",
    secrets=SecretKeys(token="GITHUB_TOKEN"),
    base_url="https://api.github.com",
)

# Bind credentials (encrypted client-side, decrypted at dispatch time)
github_secrets = SecretValues(github, token=os.getenv("GITHUB_TOKEN", ""))


async def main():
    client = AsyncDedalus(
        api_key=os.getenv("DEDALUS_API_KEY"),
        base_url=os.getenv("DEDALUS_API_URL"),
        as_base_url=os.getenv("DEDALUS_AS_URL"),
    )
    runner = DedalusRunner(client)

    result = await runner.run(
        input="List my GitHub repositories, limit to 3.",
        model="openai/gpt-5",
        mcp_servers=["issac/github-mcp"],
        credentials=[github_secrets],
    )

    print(result.output)

if __name__ == "__main__":
    asyncio.run(main())
```

## License

MIT License - see [LICENSE](LICENSE) for details.
