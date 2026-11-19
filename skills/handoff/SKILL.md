---
name: handoff
description: Pass an implementation brief or a pinned GitHub PR between Codex and Claude Code when the user requests a split between the two agents.
---

# Handoff

Use [scripts/handoff](scripts/handoff) from this skill. Pass `--workspace` with the absolute project directory and use `--repo` only for Git repositories directly below it. Use the sender and recipient specified by the user.

- `implement --from AGENT --to AGENT --brief PATH` passes an implementation or fix brief and returns a path to the result and its work copy.
- `review --pr NUMBER --head SHA --from AGENT --to AGENT` reviews the pinned PR. Add `--brief PATH` for task-specific requirements or test results. For re-review, add `--since PREVIOUS_SHA` and give only new context in the brief.

Read the result path printed by the command. Relay unresolved questions in the calling chat and pass the user's answer with `--user-answer`. At the fifth distinct reviewed commit and later, seek approval for the next round before using `--approved-by-user`. Include any reviews done outside this command when applying that limit. Check the user has authorized sharing the task with the receiving agent before dispatch. Follow the project's directions for publishing or merging.

## Reusable review notes

When opening a PR, include a brief review point only if a lesson from implementation could recur. Read existing references only when the change can affect the behavior they cover, including through shared code or configuration. Pass only the relevant point in the brief.

Review results may include a short reference candidate. After verifying the fix, keep project-specific lessons in the project's private documentation. Keep cross-project lessons in the local checkout's ignored `knowledge/` directory or another established private location. If no private location is known, report the candidate in the calling chat. Record when the lesson applies and what to check. For the local `knowledge/` directory, create `index.md` when saving the first verified lesson. Update one row per note with the affected behavior, what to check, and a relative link. Consult the index when it exists and open only relevant notes. Keep the index and notes out of Git.
