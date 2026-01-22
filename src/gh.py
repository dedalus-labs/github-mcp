# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""GitHub API tools.

Credentials provided by client via token exchange.
Supports repos, issues, PRs, workflows, deployments, and more.
"""

from typing import Any

from pydantic.dataclasses import dataclass

from dedalus_mcp import HttpMethod, HttpRequest, get_context, tool
from dedalus_mcp.auth import Connection, SecretKeys
from dedalus_mcp.types import ToolAnnotations

github = Connection(name="github-mcp", secrets=SecretKeys(token="GITHUB_TOKEN"), auth_header_format="token {api_key}")


@dataclass(frozen=True)
class GhResult:
    """GitHub API result."""

    success: bool
    data: Any = None
    error: str | None = None


async def _req(method: HttpMethod, path: str, body: Any = None) -> GhResult:
    """Execute GitHub API request."""
    ctx = get_context()
    resp = await ctx.dispatch(github, HttpRequest(method=method, path=path, body=body))
    if resp.success:
        return GhResult(success=True, data=resp.response.body)
    return GhResult(success=False, error=resp.error.message if resp.error else "Request failed")


# --- User ---


@tool(
    description="Get the authenticated GitHub user's profile",
    tags=["user", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_whoami() -> GhResult:
    """Get authenticated user profile.

    Returns:
        GhResult with login, name, and email

    """
    r = await _req(HttpMethod.GET, "/user")
    if r.success:
        u = r.data
        return GhResult(success=True, data={"login": u.get("login"), "name": u.get("name"), "email": u.get("email")})
    return r


# --- Repositories ---


@tool(
    description="List repositories for the authenticated user",
    tags=["repos", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_repos(per_page: int = 10) -> GhResult:
    """List user's repositories sorted by last update.

    Args:
        per_page: Number of repos to return (default 10)

    Returns:
        GhResult with list of {name, full_name, stars}

    """
    r = await _req(HttpMethod.GET, f"/user/repos?per_page={per_page}&sort=updated")
    if r.success and isinstance(r.data, list):
        return GhResult(
            success=True,
            data=[
                {"name": x.get("name"), "full_name": x.get("full_name"), "stars": x.get("stargazers_count", 0)}
                for x in r.data
            ],
        )
    return GhResult(success=True, data=[]) if r.success else r


@tool(
    description="Get details for a specific GitHub repository",
    tags=["repos", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_get_repo(owner: str, repo: str) -> GhResult:
    """Get repository details.

    Args:
        owner: Repository owner (user or org)
        repo: Repository name

    Returns:
        GhResult with full repo object

    """
    return await _req(HttpMethod.GET, f"/repos/{owner}/{repo}")


# --- Files ---


@tool(
    description="Get file contents from a GitHub repository",
    tags=["files", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_get_file(owner: str, repo: str, path: str, ref: str | None = None) -> GhResult:
    """Get file contents (base64 encoded for binary).

    Args:
        owner: Repository owner
        repo: Repository name
        path: File path in repo
        ref: Git ref (branch, tag, commit SHA)

    Returns:
        GhResult with file content and metadata

    """
    url = f"/repos/{owner}/{repo}/contents/{path}"
    if ref:
        url += f"?ref={ref}"
    return await _req(HttpMethod.GET, url)


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
        owner: Repository owner
        repo: Repository name
        path: File path in repo
        content_base64: Base64-encoded file content
        message: Commit message
        branch: Target branch (default: repo default)
        sha: SHA of existing file (required for updates)

    Returns:
        GhResult with commit info

    """
    body: dict[str, Any] = {"message": message, "content": content_base64}
    if branch:
        body["branch"] = branch
    if sha:
        body["sha"] = sha
    return await _req(HttpMethod.PUT, f"/repos/{owner}/{repo}/contents/{path}", body)


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
        owner: Repository owner
        repo: Repository name
        path: File path in repo
        message: Commit message
        sha: SHA of file to delete
        branch: Target branch (default: repo default)

    Returns:
        GhResult with commit info

    """
    body: dict[str, Any] = {"message": message, "sha": sha}
    if branch:
        body["branch"] = branch
    return await _req(HttpMethod.DELETE, f"/repos/{owner}/{repo}/contents/{path}", body)


# --- Issues ---


@tool(
    description="List issues in a GitHub repository",
    tags=["issues", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_issues(owner: str, repo: str, state: str = "open", per_page: int = 10) -> GhResult:
    """List issues (excludes pull requests).

    Args:
        owner: Repository owner
        repo: Repository name
        state: Issue state ("open", "closed", "all")
        per_page: Number to return (default 10)

    Returns:
        GhResult with list of {number, title, state}

    """
    r = await _req(HttpMethod.GET, f"/repos/{owner}/{repo}/issues?state={state}&per_page={per_page}")
    if r.success and isinstance(r.data, list):
        return GhResult(
            success=True,
            data=[
                {"number": i.get("number"), "title": i.get("title"), "state": i.get("state")}
                for i in r.data
                if "pull_request" not in i
            ],
        )
    return GhResult(success=True, data=[]) if r.success else r


@tool(
    description="Get a specific issue by number",
    tags=["issues", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_get_issue(owner: str, repo: str, issue_number: int) -> GhResult:
    """Get issue details.

    Args:
        owner: Repository owner
        repo: Repository name
        issue_number: Issue number

    Returns:
        GhResult with full issue object

    """
    return await _req(HttpMethod.GET, f"/repos/{owner}/{repo}/issues/{issue_number}")


# --- Pull Requests ---


@tool(
    description="List pull requests in a GitHub repository",
    tags=["prs", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_prs(owner: str, repo: str, state: str = "open", per_page: int = 10) -> GhResult:
    """List pull requests.

    Args:
        owner: Repository owner
        repo: Repository name
        state: PR state ("open", "closed", "all")
        per_page: Number to return (default 10)

    Returns:
        GhResult with list of {number, title, head, base}

    """
    r = await _req(HttpMethod.GET, f"/repos/{owner}/{repo}/pulls?state={state}&per_page={per_page}")
    if r.success and isinstance(r.data, list):
        return GhResult(
            success=True,
            data=[
                {
                    "number": p.get("number"),
                    "title": p.get("title"),
                    "head": p.get("head", {}).get("ref"),
                    "base": p.get("base", {}).get("ref"),
                }
                for p in r.data
            ],
        )
    return GhResult(success=True, data=[]) if r.success else r


@tool(
    description="Get a specific pull request by number",
    tags=["prs", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_get_pr(owner: str, repo: str, pr_number: int) -> GhResult:
    """Get pull request details.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number

    Returns:
        GhResult with full PR object

    """
    return await _req(HttpMethod.GET, f"/repos/{owner}/{repo}/pulls/{pr_number}")


# --- Workflows ---


@tool(
    description="List GitHub Actions workflows in a repository",
    tags=["actions", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_workflows(owner: str, repo: str) -> GhResult:
    """List workflows.

    Args:
        owner: Repository owner
        repo: Repository name

    Returns:
        GhResult with list of {id, name, state}

    """
    r = await _req(HttpMethod.GET, f"/repos/{owner}/{repo}/actions/workflows")
    if r.success and isinstance(r.data, dict):
        return GhResult(
            success=True,
            data=[
                {"id": w.get("id"), "name": w.get("name"), "state": w.get("state")} for w in r.data.get("workflows", [])
            ],
        )
    return GhResult(success=True, data=[]) if r.success else r


@tool(
    description="List GitHub Actions workflow runs",
    tags=["actions", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_workflow_runs(owner: str, repo: str, workflow_id: int | None = None, per_page: int = 10) -> GhResult:
    """List workflow runs.

    Args:
        owner: Repository owner
        repo: Repository name
        workflow_id: Filter by workflow ID (optional)
        per_page: Number to return (default 10)

    Returns:
        GhResult with list of {id, name, status, conclusion}

    """
    if workflow_id:
        path = f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs?per_page={per_page}"
    else:
        path = f"/repos/{owner}/{repo}/actions/runs?per_page={per_page}"
    r = await _req(HttpMethod.GET, path)
    if r.success and isinstance(r.data, dict):
        return GhResult(
            success=True,
            data=[
                {"id": x.get("id"), "name": x.get("name"), "status": x.get("status"), "conclusion": x.get("conclusion")}
                for x in r.data.get("workflow_runs", [])
            ],
        )
    return GhResult(success=True, data=[]) if r.success else r


@tool(
    description="Trigger a GitHub Actions workflow via dispatch event",
    tags=["actions", "write"],
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def gh_dispatch_workflow(
    owner: str, repo: str, workflow_id: int | str, ref: str, inputs: dict[str, str] | None = None
) -> GhResult:
    """Trigger workflow dispatch.

    Args:
        owner: Repository owner
        repo: Repository name
        workflow_id: Workflow ID or filename
        ref: Git ref to run on (branch, tag)
        inputs: Workflow inputs (optional)

    Returns:
        GhResult (empty on success - 204 response)

    """
    body: dict[str, Any] = {"ref": ref}
    if inputs:
        body["inputs"] = inputs
    return await _req(HttpMethod.POST, f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches", body)


@tool(
    description="Cancel a running GitHub Actions workflow",
    tags=["actions", "write"],
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
async def gh_cancel_workflow_run(owner: str, repo: str, run_id: int) -> GhResult:
    """Cancel a workflow run.

    Args:
        owner: Repository owner
        repo: Repository name
        run_id: Workflow run ID

    Returns:
        GhResult (empty on success)

    """
    return await _req(HttpMethod.POST, f"/repos/{owner}/{repo}/actions/runs/{run_id}/cancel")


@tool(
    description="Re-run a GitHub Actions workflow",
    tags=["actions", "write"],
    annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True),
)
async def gh_rerun_workflow(owner: str, repo: str, run_id: int) -> GhResult:
    """Re-run a workflow.

    Args:
        owner: Repository owner
        repo: Repository name
        run_id: Workflow run ID

    Returns:
        GhResult (empty on success)

    """
    return await _req(HttpMethod.POST, f"/repos/{owner}/{repo}/actions/runs/{run_id}/rerun")


# --- Variables & Secrets ---


@tool(
    description="List GitHub Actions variables for a repository",
    tags=["actions", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_actions_variables(owner: str, repo: str) -> GhResult:
    """List actions variables.

    Args:
        owner: Repository owner
        repo: Repository name

    Returns:
        GhResult with variables list

    """
    return await _req(HttpMethod.GET, f"/repos/{owner}/{repo}/actions/variables")


@tool(
    description="List GitHub Actions secrets (names only, values are never exposed)",
    tags=["actions", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_secrets(owner: str, repo: str) -> GhResult:
    """List secrets (names only).

    Args:
        owner: Repository owner
        repo: Repository name

    Returns:
        GhResult with list of {name, updated_at}

    """
    r = await _req(HttpMethod.GET, f"/repos/{owner}/{repo}/actions/secrets")
    if r.success and isinstance(r.data, dict):
        return GhResult(
            success=True,
            data=[{"name": s.get("name"), "updated_at": s.get("updated_at")} for s in r.data.get("secrets", [])],
        )
    return GhResult(success=True, data=[]) if r.success else r


# --- Deployments & Environments ---


@tool(
    description="List deployments for a GitHub repository",
    tags=["deployments", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_deployments(owner: str, repo: str, environment: str | None = None, per_page: int = 10) -> GhResult:
    """List deployments.

    Args:
        owner: Repository owner
        repo: Repository name
        environment: Filter by environment name (optional)
        per_page: Number to return (default 10)

    Returns:
        GhResult with list of {id, environment, ref}

    """
    path = f"/repos/{owner}/{repo}/deployments?per_page={per_page}"
    if environment:
        path += f"&environment={environment}"
    r = await _req(HttpMethod.GET, path)
    if r.success and isinstance(r.data, list):
        return GhResult(
            success=True,
            data=[{"id": d.get("id"), "environment": d.get("environment"), "ref": d.get("ref")} for d in r.data],
        )
    return GhResult(success=True, data=[]) if r.success else r


@tool(
    description="List environments configured for a GitHub repository",
    tags=["deployments", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_environments(owner: str, repo: str) -> GhResult:
    """List environments.

    Args:
        owner: Repository owner
        repo: Repository name

    Returns:
        GhResult with list of {id, name}

    """
    r = await _req(HttpMethod.GET, f"/repos/{owner}/{repo}/environments")
    if r.success and isinstance(r.data, dict):
        return GhResult(
            success=True, data=[{"id": e.get("id"), "name": e.get("name")} for e in r.data.get("environments", [])]
        )
    return GhResult(success=True, data=[]) if r.success else r


# --- Commit Status ---


@tool(
    description="Get combined commit status for a git ref",
    tags=["commits", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_get_commit_status(owner: str, repo: str, ref: str) -> GhResult:
    """Get combined status for a ref.

    Args:
        owner: Repository owner
        repo: Repository name
        ref: Git ref (branch, tag, commit SHA)

    Returns:
        GhResult with combined status object

    """
    return await _req(HttpMethod.GET, f"/repos/{owner}/{repo}/commits/{ref}/status")


@tool(
    description="List individual status checks for a git ref",
    tags=["commits", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_commit_statuses(owner: str, repo: str, ref: str) -> GhResult:
    """List status checks for a ref.

    Args:
        owner: Repository owner
        repo: Repository name
        ref: Git ref (branch, tag, commit SHA)

    Returns:
        GhResult with list of {state, context, description}

    """
    r = await _req(HttpMethod.GET, f"/repos/{owner}/{repo}/commits/{ref}/statuses")
    if r.success and isinstance(r.data, list):
        return GhResult(
            success=True,
            data=[
                {"state": s.get("state"), "context": s.get("context"), "description": s.get("description")}
                for s in r.data
            ],
        )
    return GhResult(success=True, data=[]) if r.success else r


# --- Discussions ---


@tool(
    description="List GitHub Discussions in a repository (via GraphQL)",
    tags=["discussions", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_discussions(owner: str, repo: str, per_page: int = 10) -> GhResult:
    """List discussions using GraphQL API.

    Args:
        owner: Repository owner
        repo: Repository name
        per_page: Number to return (default 10)

    Returns:
        GhResult with GraphQL response containing discussions

    """
    query = """
    query($owner: String!, $repo: String!, $first: Int!) {
      repository(owner: $owner, name: $repo) {
        discussions(first: $first) {
          nodes { number title category { name } author { login } }
        }
      }
    }
    """
    body = {"query": query, "variables": {"owner": owner, "repo": repo, "first": per_page}}
    return await _req(HttpMethod.POST, "/graphql", body)


gh_tools = [
    gh_whoami,
    gh_list_repos,
    gh_get_repo,
    gh_get_file,
    gh_put_file,
    gh_delete_file,
    gh_list_issues,
    gh_get_issue,
    gh_list_prs,
    gh_get_pr,
    gh_list_workflows,
    gh_list_workflow_runs,
    gh_dispatch_workflow,
    gh_cancel_workflow_run,
    gh_rerun_workflow,
    gh_list_actions_variables,
    gh_list_secrets,
    gh_list_deployments,
    gh_list_environments,
    gh_get_commit_status,
    gh_list_commit_statuses,
    gh_list_discussions,
]
