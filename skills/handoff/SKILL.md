---
name: handoff
description: Pass an implementation brief or a pinned GitHub PR between Codex and Claude Code when the user requests a split between the two agents.
---

# Handoff

Use [scripts/handoff](scripts/handoff) from this skill. Pass `--workspace` with the absolute project directory and use `--repo` only for Git repositories directly below it. Use the sender and recipient specified by the user.

- `implement --from AGENT --to AGENT --brief PATH` passes an implementation or fix brief and returns a path to the result and its work copy.
- `review --pr NUMBER --head SHA --from AGENT --to AGENT` reviews the pinned PR. Add `--brief PATH` for task-specific requirements or test results. For re-review, add `--since PREVIOUS_SHA` and give only new context in the brief.

Read the result path printed by the command. Relay unresolved questions in the calling chat and pass the user's answer with `--user-answer`. At the fifth distinct reviewed commit and later, seek approval for the next round before using `--approved-by-user`. Include any reviews done outside this command when applying that limit. Check the user has authorized sharing the task with the receiving agent before dispatch. Follow the project's directions for publishing or merging.
