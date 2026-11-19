---
name: handoff
description: Pass an implementation brief or a pinned GitHub PR between Codex and Claude Code when the user requests a split between the two agents.
---

# Handoff

Resolve the actual workspace first, especially if the session started at an old path. Before making checkouts, read applicable project instructions and the workspace’s `HANDOFF.md`, if present. Follow the project's instructions for its configured handoff command. If the project has no configured command, run this skill's [scripts/handoff](scripts/handoff) with `--workspace` set to the absolute project directory. For that script, use `--repo` only for Git repositories directly below the workspace. Use the sender and recipient specified by the user.

Before the first handoff in a workspace, check whether its output paths are inside a Git worktree. If they are, add `/.handoff-runs/` and `/handoff-requests/` to the workspace's `.gitignore` where existing rules do not already cover them. If any handoff files are already tracked, tell the user.

- `implement --from AGENT --to AGENT --brief PATH` passes an implementation or fix brief and returns a path to the result and its work copy.
- `review --pr NUMBER --head SHA --from AGENT --to AGENT` reviews the pinned PR. Add `--brief PATH` for task-specific requirements or test results. For re-review, add `--since PREVIOUS_SHA` and give only new context in the brief.

Wait for a saved result on the requested HEAD. For actionable findings, fix and verify them, push if authorized, and re-review the new HEAD before reporting completion. On parse failure, read the preserved output, then get a saved result before treating the review as complete. Verify factual questions from available code or evidence and attach the relevant evidence to the next brief. Bring decisions that need a human to the calling chat and resume with the user's answer via `--user-answer`. At the fifth distinct reviewed commit and later, seek approval for the next round before using `--approved-by-user`. Include any reviews done outside this command when applying that limit. Check the user has authorized sharing the task with the receiving agent before dispatch. Follow the project's directions for publishing or merging.

## Reusable review notes

When opening a PR, include a brief review point only if a lesson from implementation could recur. Read existing references only when the change can affect the behavior they cover, including through shared code or configuration. Pass relevant points from private notes only when authorized for sharing with the receiving agent.

Review results may include a short reference candidate. After verifying the fix, keep project-specific lessons in the project's private documentation. For cross-project lessons, use `knowledge/` in the calling agent's installed skill directory (`~/.agents/skills/handoff/` for Codex or `~/.claude/skills/handoff/` for Claude Code in a user install), or another established private location. Use the install directory even if `SKILL.md` is linked to a checkout. If no private location is known, report the candidate in the calling chat. Record when the lesson applies and what to check. For the local `knowledge/` directory, create `index.md` when saving the first verified lesson. Update one row per note with the affected behavior, what to check, and a relative link. Consult the index when it exists and open only relevant notes. Keep the index and notes out of Git.
