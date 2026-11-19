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

## Review scope and performance

An initial review uses the full PR diff. With `--since`, a re-review starts with the changes since the previous reviewed SHA and any unresolved findings saved for that SHA. The reviewer can still inspect related files in the checkout. Keep the brief focused on new requirements, recent changes, and test results. Open private knowledge notes only when the changed behavior makes them relevant.

Each run creates an isolated checkout, so even a small re-review has checkout overhead. Runtime and token savings have not been benchmarked on live reviews. The offline tests verify the review scope and handoff behavior.

## Local output

If the workspace is inside a Git worktree, ignore `/.handoff-runs/` and `/handoff-requests/` in its `.gitignore` before running Handoff. The calling agent can set these rules up when using the skill. Already tracked files need separate handling.

- `handoff-requests/tasks/<task>/brief.md` is a suggested location for implementation briefs.
- `handoff-requests/<repo>/pr-<number>/` holds the PR brief and the latest `review.md`.
- `.handoff-runs/` holds individual run records. Successful reviews remove their temporary checkout. Implementation checkouts retain their changes for you to inspect and apply.

## Private review knowledge

If `knowledge/index.md` does not exist, create it when saving your first verified, reusable review lesson. Add one row per note with when it applies, what to check, and a relative link. Use the index to open only notes relevant to the current change.

The index and notes stay local. Git tracks only `knowledge/.gitkeep`.

## Tests

```sh
python3 -B -m unittest discover -s tests -v
```

Tests use temporary Git repositories and stub CLIs and run offline.
