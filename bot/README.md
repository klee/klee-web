# Issue Agent

This folder contains the dispatcher used by `.github/workflows/issue-agent.yml`.
It turns a reviewed GitHub issue into an agent-authored draft pull request.

## Setup

Configure these repository variables and secrets before applying `agent:ready`
to real issues:

- `ISSUE_AGENT_COMMAND` repository variable: shell command that runs your coding
  agent. The dispatcher writes the task prompt to `$ISSUE_AGENT_PROMPT_FILE` and
  also replaces `{prompt_file}`, `{issue_number}`, and `{branch}` placeholders.
- `ISSUE_AGENT_INSTALL_COMMAND` repository variable, optional: command that
  installs your chosen agent CLI on the GitHub Actions runner.
- `DEEPSEEK_API_KEY` repository secret, if using OpenCode or another agent with
  DeepSeek.
- `AGENT_GITHUB_TOKEN` repository secret, optional: use a GitHub App token or
  PAT if you want bot-created pull requests to run CI without GitHub's
  `GITHUB_TOKEN` approval behavior.

Example command shape:

```sh
your-agent-cli --prompt-file {prompt_file}
```

If your agent reads from standard input instead, use a shell command:

```sh
your-agent-cli < {prompt_file}
```

## OpenCode with DeepSeek

OpenCode is a good fit for GitHub Actions because it has a non-interactive
`opencode run` command and supports DeepSeek as a provider.

Add this repository secret:

```text
DEEPSEEK_API_KEY
```

Add this repository variable:

```text
ISSUE_AGENT_INSTALL_COMMAND=npm install -g opencode-ai
```

Add this repository variable:

```text
ISSUE_AGENT_COMMAND=opencode run --model deepseek/deepseek-v4-pro --file {prompt_file} --dangerously-skip-permissions "Read the attached issue-agent prompt, implement the requested repository change, and then stop. Do not commit, push, or open a pull request."
```

The dispatcher script handles commit, push, checks, and the draft pull request
after OpenCode exits. The `--dangerously-skip-permissions` flag is what lets
OpenCode edit files in non-interactive CI; only apply `agent:ready` to issues
you have reviewed.

If the model id changes, temporarily run this in the workflow or locally after
installing OpenCode:

```sh
opencode models deepseek --refresh
```

## Workflow

1. Create an issue with clear acceptance criteria.
2. A maintainer reviews it and applies `agent:ready`.
3. The workflow creates labels if needed, claims the issue with
   `agent:working`, and creates an `agent/issue-...` branch.
4. The configured agent command runs against the generated prompt.
5. The dispatcher runs:

   ```sh
   cd backend && uv run pytest tests/unit
   cd frontend && npm run build
   ```

6. If checks pass and files changed, it commits, pushes, opens a draft PR, and
   labels the issue `agent:pr-opened`.
7. If the agent fails, checks fail, or no files changed, it comments with the
   failure and labels the issue `agent:blocked`.

Use the workflow's manual `dry_run` input to inspect the generated prompt without
running the agent.
