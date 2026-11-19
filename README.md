# Handoff for Codex and Claude Code

Handoff passes an implementation brief or a pinned GitHub pull request to the other coding agent. It saves results on your machine and supports incremental re-review, a pause for user questions, and approval before the fifth distinct reviewed commit.

## Install

Requires Python 3.8+, Git, and the receiving agent's command-line client. PR review also needs an authenticated GitHub CLI and a github.com `origin` over HTTPS or SSH. The script targets macOS and Linux.

Install the same skill for either agent. If a destination already has a skill named `handoff`, inspect it before replacing it.

| Agent | Copy `skills/handoff/` into | Invoke in a project |
|---|---|---|
| Codex | `~/.agents/skills/` | `$handoff` |
| Claude Code | `~/.claude/skills/` | `/handoff` |

Start the agent in the project where you want to use the skill. Name the implementation and review roles in your request. The selected agent processes the brief and repository material through its provider.

## Run directly

From the project, using the script from an installed or cloned skill:

```sh
/path/to/skills/handoff/scripts/handoff review --pr 37 --head COMMIT_SHA --from codex --to claude
/path/to/skills/handoff/scripts/handoff implement --from claude --to codex --brief handoff-requests/tasks/example/brief.md
```

Use `--workspace /path/to/project` to run from another directory. Relative brief paths are resolved inside that workspace. Omit `--repo` for a Git repository at the workspace root. For a workspace containing several repositories, pass the direct child directory name with `--repo`. Implementation can take several `--repo` arguments. The implementation base defaults to the local `origin/main` reference and can be set with `--base`.

For re-review, pass `--since PREVIOUS_SHA` to send the change since the previous reviewed commit and any unresolved findings recorded for that SHA. If Git cannot establish the incremental range, the script uses the full PR diff. After a user answers a reviewer's question, resume with `--user-answer "answer"`. Use `--approved-by-user` only after the user approves the next round.

## Local output

- `handoff-requests/tasks/<task>/brief.md` is a suggested location for implementation briefs.
- `handoff-requests/<repo>/pr-<number>/` holds the PR brief and the latest `review.md`.
- `.handoff-runs/` holds individual run records. Successful reviews remove their temporary checkout. Implementation checkouts retain their changes for you to inspect and apply.

## Tests

```sh
python3 -B -m unittest discover -s tests -v
```

Tests use temporary Git repositories and stub CLIs and run offline.
