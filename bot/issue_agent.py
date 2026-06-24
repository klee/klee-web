#!/usr/bin/env python3
"""Turn a labeled GitHub issue into an agent-authored draft pull request."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "bot" / "prompts" / "issue_task.md"

READY_LABEL = os.environ.get("ISSUE_AGENT_READY_LABEL", "agent:ready")
WORKING_LABEL = os.environ.get("ISSUE_AGENT_WORKING_LABEL", "agent:working")
BLOCKED_LABEL = os.environ.get("ISSUE_AGENT_BLOCKED_LABEL", "agent:blocked")
PR_OPENED_LABEL = os.environ.get("ISSUE_AGENT_PR_OPENED_LABEL", "agent:pr-opened")

LABELS = {
    READY_LABEL: ("0e8a16", "Reviewed issue that the issue agent may work on."),
    WORKING_LABEL: ("fbca04", "Issue agent is currently attempting this issue."),
    BLOCKED_LABEL: ("d73a4a", "Issue agent could not finish without human help."),
    PR_OPENED_LABEL: ("5319e7", "Issue agent opened a pull request for this issue."),
}


class AgentError(RuntimeError):
    """Expected failure that should be reported back to the issue."""


class GitHubError(RuntimeError):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"GitHub API returned {status}: {body}")
        self.status = status
        self.body = body


@dataclass
class CommandResult:
    returncode: int
    output: str


class GitHubClient:
    def __init__(self, repo: str, token: str) -> None:
        self.repo = repo
        self.token = token
        self.base_url = f"https://api.github.com/repos/{repo}"

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | list[Any] | None = None,
    ) -> Any:
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        request = Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

        try:
            with urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise GitHubError(error.code, body) from error

        if not body:
            return None
        return json.loads(body)

    def get_issue(self, issue_number: int) -> dict[str, Any]:
        return self.request("GET", f"/issues/{issue_number}")

    def comment(self, issue_number: int, body: str) -> None:
        self.request("POST", f"/issues/{issue_number}/comments", {"body": body})

    def ensure_label(self, name: str, color: str, description: str) -> None:
        encoded = quote(name, safe="")
        try:
            self.request("GET", f"/labels/{encoded}")
        except GitHubError as error:
            if error.status != 404:
                raise
            self.request(
                "POST",
                "/labels",
                {"name": name, "color": color, "description": description},
            )

    def add_labels(self, issue_number: int, labels: list[str]) -> None:
        if labels:
            self.request("POST", f"/issues/{issue_number}/labels", {"labels": labels})

    def remove_label(self, issue_number: int, label: str) -> None:
        try:
            self.request("DELETE", f"/issues/{issue_number}/labels/{quote(label, safe='')}")
        except GitHubError as error:
            if error.status != 404:
                raise

    def list_open_prs_for_branch(self, branch: str) -> list[dict[str, Any]]:
        owner = self.repo.split("/", 1)[0]
        query = urlencode({"state": "open", "head": f"{owner}:{branch}"})
        return self.request("GET", f"/pulls?{query}")

    def create_pull_request(self, title: str, body: str, head: str, base: str) -> dict[str, Any]:
        return self.request(
            "POST",
            "/pulls",
            {
                "title": title,
                "body": body,
                "head": head,
                "base": base,
                "draft": True,
                "maintainer_can_modify": True,
            },
        )


def run_command(command: str | list[str], *, env: dict[str, str] | None = None) -> CommandResult:
    shell = isinstance(command, str)
    print(f"+ {command if shell else shlex.join(command)}", flush=True)
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        shell=shell,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=int(os.environ.get("ISSUE_AGENT_COMMAND_TIMEOUT_SECONDS", "1800")),
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="", flush=True)
    return CommandResult(completed.returncode, completed.stdout or "")


def run_git(*args: str) -> CommandResult:
    return run_command(["git", *args])


def checked(command: str | list[str], *, env: dict[str, str] | None = None) -> str:
    result = run_command(command, env=env)
    if result.returncode != 0:
        raise AgentError(result.output)
    return result.output


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:48] or "task"


def labels_for(issue: dict[str, Any]) -> set[str]:
    return {label["name"] for label in issue.get("labels", [])}


def truthy(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").lower() in {"1", "true", "yes", "on"}


def truncate(value: str, limit: int = 5000) -> str:
    if len(value) <= limit:
        return value
    return value[-limit:]


def checks_from_env() -> list[str]:
    raw = os.environ.get("ISSUE_AGENT_CHECKS", "")
    return [line.strip() for line in raw.splitlines() if line.strip() and not line.startswith("#")]


def workflow_url() -> str | None:
    server = os.environ.get("GITHUB_SERVER_URL")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if not (server and repo and run_id):
        return None
    return f"{server}/{repo}/actions/runs/{run_id}"


def render_command(template: str, *, prompt_file: Path, issue_number: int, branch: str) -> str:
    replacements = {
        "{prompt_file}": shlex.quote(str(prompt_file)),
        "{issue_number}": str(issue_number),
        "{branch}": shlex.quote(branch),
    }
    command = template
    for marker, value in replacements.items():
        command = command.replace(marker, value)
    return command


def build_prompt(issue: dict[str, Any], branch: str, base_branch: str, checks: list[str]) -> str:
    base_prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""
    label_names = ", ".join(sorted(labels_for(issue))) or "none"
    checks_text = "\n".join(f"- `{check}`" for check in checks) or "- No checks configured."
    body = issue.get("body") or "_No issue body provided._"

    return textwrap.dedent(
        f"""
        {base_prompt.strip()}

        ## GitHub Issue

        - Number: #{issue["number"]}
        - Title: {issue["title"]}
        - URL: {issue["html_url"]}
        - Author: @{issue["user"]["login"]}
        - Labels: {label_names}
        - Base branch: `{base_branch}`
        - Working branch: `{branch}`

        ## Issue Body

        {body}

        ## Verification Commands

        {checks_text}

        ## Extra Instructions

        {os.environ.get("ISSUE_AGENT_EXTRA_INSTRUCTIONS", "").strip() or "_None._"}
        """
    ).strip() + "\n"


def prepare_branch(branch: str, base_branch: str) -> None:
    checked(["git", "config", "user.name", os.environ.get("ISSUE_AGENT_GIT_NAME", "issue-agent")])
    checked(
        [
            "git",
            "config",
            "user.email",
            os.environ.get("ISSUE_AGENT_GIT_EMAIL", "issue-agent@users.noreply.github.com"),
        ]
    )
    checked(["git", "fetch", "origin", base_branch])
    checked(["git", "checkout", "-B", branch, f"origin/{base_branch}"])


def commit_and_push(issue: dict[str, Any], branch: str) -> None:
    checked(["git", "add", "-A"])
    diff = run_git("diff", "--cached", "--quiet")
    if diff.returncode == 0:
        raise AgentError("The agent finished but did not produce any git changes.")

    title = issue["title"].strip().replace("\n", " ")
    checked(["git", "commit", "-m", f"Fix #{issue['number']}: {title}"])
    checked(["git", "push", "--force-with-lease", "origin", f"HEAD:{branch}"])


def run_checks(checks: list[str]) -> None:
    for check in checks:
        result = run_command(check)
        if result.returncode != 0:
            raise AgentError(f"Verification failed for `{check}`.\n\n{result.output}")


def open_or_reuse_pr(
    client: GitHubClient,
    issue: dict[str, Any],
    branch: str,
    base_branch: str,
    checks: list[str],
) -> dict[str, Any]:
    existing = client.list_open_prs_for_branch(branch)
    if existing:
        return existing[0]

    body = textwrap.dedent(
        f"""
        Automated draft PR for #{issue["number"]}.

        Closes #{issue["number"]}.

        Verification run by the issue agent:
        {chr(10).join(f"- `{check}`" for check in checks) or "- No checks configured."}
        """
    ).strip()
    return client.create_pull_request(
        title=f"Fix #{issue['number']}: {issue['title']}",
        body=body,
        head=branch,
        base=base_branch,
    )


def mark_working(client: GitHubClient, issue_number: int) -> None:
    for name, (color, description) in LABELS.items():
        client.ensure_label(name, color, description)
    client.add_labels(issue_number, [WORKING_LABEL])
    client.remove_label(issue_number, READY_LABEL)
    client.remove_label(issue_number, BLOCKED_LABEL)


def mark_blocked(client: GitHubClient, issue_number: int, message: str) -> None:
    client.add_labels(issue_number, [BLOCKED_LABEL])
    client.remove_label(issue_number, WORKING_LABEL)
    client.comment(
        issue_number,
        textwrap.dedent(
            f"""
            Issue agent could not finish this one.

            ```text
            {truncate(message)}
            ```

            {f"Workflow run: {workflow_url()}" if workflow_url() else ""}
            """
        ).strip(),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", required=True, type=int, help="GitHub issue number to work on")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"), help="owner/name")
    parser.add_argument(
        "--base",
        default=os.environ.get("ISSUE_AGENT_BASE_BRANCH", "main"),
        help="Base branch for the agent branch and PR",
    )
    parser.add_argument("--dry-run", default=os.environ.get("ISSUE_AGENT_DRY_RUN", "false"))
    return parser.parse_args()


"""Main function of the issue agent"""
def main() -> int:
    args = parse_args()
    # GITHUB REPOSITORY is automatically defined, should always be available when running as github action
    if not args.repo:
        raise SystemExit("Set GITHUB_REPOSITORY or pass --repo owner/name.")

    # defined in issue-agent.yml, enables this agent to make PR to the repo
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Set GH_TOKEN or GITHUB_TOKEN.")


    # construct the toke and get the issue in the argument
    client = GitHubClient(args.repo, token)
    issue = client.get_issue(args.issue)
    if "pull_request" in issue:
        raise SystemExit(f"#{args.issue} is a pull request, not an issue.")
    if issue["state"] != "open":
        raise SystemExit(f"#{args.issue} is not open.")

    issue_labels = labels_for(issue)
    if READY_LABEL not in issue_labels and not truthy(args.dry_run):
        print(f"Skipping #{args.issue}: missing `{READY_LABEL}` label.")
        return 0
    if PR_OPENED_LABEL in issue_labels and not truthy(os.environ.get("ISSUE_AGENT_ALLOW_RETRY")):
        print(f"Skipping #{args.issue}: `{PR_OPENED_LABEL}` is already present.")
        return 0

    branch = (
        f"{os.environ.get('ISSUE_AGENT_BRANCH_PREFIX', 'agent/issue')}-"
        f"{args.issue}-{slugify(issue['title'])}"
    )
    checks = checks_from_env()
    prompt = build_prompt(issue, branch, args.base, checks)
    prompt_file = Path(tempfile.gettempdir()) / f"issue-agent-{args.issue}-prompt.md"
    prompt_file.write_text(prompt, encoding="utf-8")
    print(f"Prompt written to {prompt_file}")

    if truthy(args.dry_run):
        print(prompt)
        client.comment(
            args.issue,
            f"I built the issue-agent prompt in dry-run mode and did not run the agent.\n\n"
            f"{f'Workflow run: {workflow_url()}' if workflow_url() else ''}",
        )
        return 0

    command_template = os.environ.get("ISSUE_AGENT_COMMAND", "").strip()
    if not command_template:
        message = (
            "ISSUE_AGENT_COMMAND is not configured. Set it as a repository variable, "
            "for example a command that reads $ISSUE_AGENT_PROMPT_FILE or uses {prompt_file}."
        )
        mark_working(client, args.issue)
        mark_blocked(client, args.issue, message)
        raise AgentError(message)

    mark_working(client, args.issue)
    client.comment(
        args.issue,
        textwrap.dedent(
            f"""
            Issue agent picked this up on branch `{branch}`.

            {f"Workflow run: {workflow_url()}" if workflow_url() else ""}
            """
        ).strip(),
    )

    try:
        prepare_branch(branch, args.base)

        env = os.environ.copy()
        env.update(
            {
                "ISSUE_AGENT_PROMPT_FILE": str(prompt_file),
                "ISSUE_AGENT_ISSUE_NUMBER": str(args.issue),
                "ISSUE_AGENT_BRANCH": branch,
            }
        )
        command = render_command(
            command_template,
            prompt_file=prompt_file,
            issue_number=args.issue,
            branch=branch,
        )
        checked(command, env=env)

        run_checks(checks)
        commit_and_push(issue, branch)
        pr = open_or_reuse_pr(client, issue, branch, args.base, checks)

        client.add_labels(args.issue, [PR_OPENED_LABEL])
        client.remove_label(args.issue, WORKING_LABEL)
        client.comment(
            args.issue,
            textwrap.dedent(
                f"""
                Issue agent opened a draft PR: {pr["html_url"]}

                Verification completed:
                {chr(10).join(f"- `{check}`" for check in checks) or "- No checks configured."}
                """
            ).strip(),
        )
        return 0
    except Exception as error:
        mark_blocked(client, args.issue, str(error))
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AgentError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
