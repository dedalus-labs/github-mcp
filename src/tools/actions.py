# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""GitHub Actions tools — workflows, runs, CI diagnosis.

Functions:
  gh_list_workflows     -- list workflows
  gh_list_workflow_runs -- list workflow runs
  gh_dispatch_workflow  -- trigger workflow dispatch
  gh_rerun_workflow     -- re-run a workflow
  gh_ci_diagnosis       -- diagnose CI failures (compound: run + jobs + steps)
"""

from __future__ import annotations

from dedalus_mcp import HttpMethod, tool
from dedalus_mcp.types import ToolAnnotations

from gh.guards import validate_owner_repo
from gh.request import _int, _opt_str, _str, build_url, request
from gh.types import (
    CiDiagnosisInfo,
    GhResult,
    JSONObject,
    WorkflowInfo,
    WorkflowJobInfo,
    WorkflowJobStep,
    WorkflowRunInfo,
)


# --- Workflows ---


@tool(
    description="List GitHub Actions workflows in a repository",
    tags=["actions", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_workflows(owner: str, repo: str) -> list[WorkflowInfo]:
    """List workflows.

    Args:
        owner: Repository owner.
        repo: Repository name.

    Returns:
        List of WorkflowInfo.

    """
    validate_owner_repo(owner, repo)
    response = await request(HttpMethod.GET, f"/repos/{owner}/{repo}/actions/workflows")
    if not response.success:
        msg = response.error or "Failed to list workflows"
        raise RuntimeError(msg)
    items = (
        response.data.get("workflows", []) if isinstance(response.data, dict) else []
    )
    workflows = [
        WorkflowInfo(
            id=_int(workflow.get("id")),
            name=_str(workflow.get("name")),
            state=_str(workflow.get("state")),
        )
        for workflow in items
    ]
    return workflows


@tool(
    description="List GitHub Actions workflow runs",
    tags=["actions", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_list_workflow_runs(
    owner: str, repo: str, workflow_id: int | None = None, per_page: int = 10
) -> list[WorkflowRunInfo]:
    """List workflow runs.

    Args:
        owner: Repository owner.
        repo: Repository name.
        workflow_id: Filter by workflow ID (optional).
        per_page: Results per page (default 10).

    Returns:
        List of WorkflowRunInfo.

    """
    validate_owner_repo(owner, repo)
    if workflow_id:
        path = build_url(
            f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs",
            per_page=per_page,
        )
    else:
        path = build_url(f"/repos/{owner}/{repo}/actions/runs", per_page=per_page)
    response = await request(HttpMethod.GET, path)
    if not response.success:
        msg = response.error or "Failed to list workflow runs"
        raise RuntimeError(msg)
    items = (
        response.data.get("workflow_runs", [])
        if isinstance(response.data, dict)
        else []
    )
    runs = [
        WorkflowRunInfo(
            id=_int(run.get("id")),
            name=_opt_str(run.get("name")),
            status=_opt_str(run.get("status")),
            conclusion=_opt_str(run.get("conclusion")),
            branch=_opt_str(run.get("head_branch")),
            created_at=_opt_str(run.get("created_at")),
        )
        for run in items
    ]
    return runs


@tool(
    description="Trigger a GitHub Actions workflow via dispatch event",
    tags=["actions", "write"],
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def gh_dispatch_workflow(
    owner: str,
    repo: str,
    workflow_id: int | str,
    ref: str,
    inputs: dict[str, str] | None = None,
) -> GhResult:
    """Trigger workflow dispatch.

    Args:
        owner: Repository owner.
        repo: Repository name.
        workflow_id: Workflow ID or filename.
        ref: Git ref to run on (branch, tag).
        inputs: Workflow inputs (optional).

    Returns:
        GhResult (empty on success — 204 response).

    """
    validate_owner_repo(owner, repo)
    body: JSONObject = {"ref": ref}
    if inputs:
        body["inputs"] = inputs
    result = await request(
        HttpMethod.POST,
        f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches",
        body,
    )
    return result


@tool(
    description="Re-run a GitHub Actions workflow",
    tags=["actions", "write"],
    annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True),
)
async def gh_rerun_workflow(owner: str, repo: str, run_id: int) -> GhResult:
    """Re-run a workflow.

    Args:
        owner: Repository owner.
        repo: Repository name.
        run_id: Workflow run ID.

    Returns:
        GhResult.

    """
    validate_owner_repo(owner, repo)
    result = await request(
        HttpMethod.POST, f"/repos/{owner}/{repo}/actions/runs/{run_id}/rerun"
    )
    return result


# --- CI Diagnosis (compound) ---


def _parse_job(raw: dict) -> WorkflowJobInfo:
    """Parse a raw job dict into WorkflowJobInfo with steps."""
    raw_steps = raw.get("steps", []) if isinstance(raw.get("steps"), list) else []
    steps = [
        WorkflowJobStep(
            name=_str(step.get("name")),
            status=_str(step.get("status")),
            conclusion=_opt_str(step.get("conclusion")),
            number=_int(step.get("number")),
        )
        for step in raw_steps
    ]
    return WorkflowJobInfo(
        id=_int(raw.get("id")),
        name=_str(raw.get("name")),
        status=_str(raw.get("status")),
        conclusion=_opt_str(raw.get("conclusion")),
        steps=steps,
    )


@tool(
    description=(
        "Diagnose CI failures for a branch or run. Returns the workflow run, "
        "all jobs with step-level detail, and highlights which jobs/steps failed. "
        "Provide either run_id (exact run) or branch (latest run on that branch)."
    ),
    tags=["actions", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def gh_ci_diagnosis(
    owner: str, repo: str, run_id: int | None = None, branch: str | None = None
) -> CiDiagnosisInfo:
    """Compound CI diagnosis — run metadata + jobs + failed steps.

    Args:
        owner: Repository owner.
        repo: Repository name.
        run_id: Specific workflow run ID (takes precedence over branch).
        branch: Get the latest run on this branch.

    Returns:
        CiDiagnosisInfo with run metadata, all jobs, and filtered failed_jobs.

    Raises:
        RuntimeError: If no run is found or API call fails.

    """
    validate_owner_repo(owner, repo)

    # Step 1: resolve the run
    if run_id:
        response = await request(
            HttpMethod.GET, f"/repos/{owner}/{repo}/actions/runs/{run_id}"
        )
        if not response.success:
            msg = response.error or f"Failed to get run {run_id}"
            raise RuntimeError(msg)
        run = response.data if isinstance(response.data, dict) else {}
    elif branch:
        response = await request(
            HttpMethod.GET,
            build_url(f"/repos/{owner}/{repo}/actions/runs", branch=branch, per_page=1),
        )
        if not response.success:
            msg = response.error or f"No runs found for branch {branch!r}"
            raise RuntimeError(msg)
        runs = (
            response.data.get("workflow_runs", [])
            if isinstance(response.data, dict)
            else []
        )
        if not runs:
            msg = f"No workflow runs found for branch {branch!r}"
            raise RuntimeError(msg)
        run = runs[0]
    else:
        msg = "Provide either run_id or branch"
        raise RuntimeError(msg)

    resolved_run_id = _int(run.get("id"))

    # Step 2: get jobs for this run
    response = await request(
        HttpMethod.GET, f"/repos/{owner}/{repo}/actions/runs/{resolved_run_id}/jobs"
    )
    if not response.success:
        msg = response.error or "Failed to list jobs"
        raise RuntimeError(msg)
    raw_jobs = response.data.get("jobs", []) if isinstance(response.data, dict) else []
    jobs = [_parse_job(item) for item in raw_jobs]
    failed_jobs = [job for job in jobs if job.conclusion == "failure"]

    result = CiDiagnosisInfo(
        run_id=resolved_run_id,
        run_name=_opt_str(run.get("name")),
        status=_opt_str(run.get("status")),
        conclusion=_opt_str(run.get("conclusion")),
        branch=_opt_str(run.get("head_branch")),
        jobs=jobs,
        failed_jobs=failed_jobs,
    )
    return result


action_tools = [
    gh_list_workflows,
    gh_list_workflow_runs,
    gh_dispatch_workflow,
    gh_rerun_workflow,
    gh_ci_diagnosis,
]
