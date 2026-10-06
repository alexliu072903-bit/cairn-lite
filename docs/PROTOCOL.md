# Cairn Lite protocol

## Responsibility

Cairn Lite passes one piece of work from the agent that planned it to the
agent that carries it out, and carries the results back in the same file.

It does not store durable project knowledge. Product Frames, PRDs, code,
schemas, and task systems remain authoritative for their own scope, and
durable decisions belong in the decision store a handoff cites (for example
cairn-context). A handoff points to them; it never copies or replaces them.

## Handoffs

A handoff is a working file, not project knowledge: it lives in
`cairn/handoffs/<id>.md` and stays out of Git by default. When a handoff
produces a durable decision, record it in the decision store it cites, with the
human owner's confirmation.

Each handoff has three layers with different owners:

- **Decisions**: pointers to confirmed decisions (a decision id or a file
  path), never copies. Nobody changes them inside a handoff.
- **Design**: the planner's proposal, a hypothesis. The executor may change
  it, and records what changed and why in the Log.
- **Acceptance** and **Out of scope**: only the human owner changes them.

Executor:

1. Before any other work, write the Readback: the goal, what is out of scope,
   and where you will stop, in your own words, at most 6 lines. Set
   `status: acknowledged`.
2. Set `status: running` and work. After each step, append one Log entry:
   date, step, result, evidence (commit, PR, file, command output), and any
   deviation from the Design.
3. When a question would change a Decision, Acceptance, or Out of scope, add
   it under Questions as `- [ ] ...`, set `status: blocked`, and stop.
4. When every Acceptance item is met, set `status: done`.
5. Whenever you are resumed ("continue", a new message, a new session), re-read
   the handoff file first: the planner may have answered a question or changed
   the Design there. Do not rely on your conversation memory of the file.

Planner:

1. Write the handoff with `cairn handoff new`. Keep it short: point to
   decisions and sources instead of repeating them. Set `planner_url` (an
   `https://` link to where you can be reached) so tools can send the human
   back to you when the work needs re-planning.
2. On re-entry, read the Readback, Log, and Questions before planning again.
   Answer a question by changing `- [ ]` to `- [x]` and writing the answer
   under it; ask the human owner when the answer is theirs to give.

Do not delete Log entries or answered questions. `cairn validate` checks the
statuses and sections.

A record in a handoff is not the human's authorization. Pushing, publishing,
and other external actions need the human's confirmation in the executor's own
conversation.

## Portability

The protocol uses plain Markdown and JSON. Agent-specific entry files are thin
routing layers; the handoff file is the only shared state between agents.

Both agents must read and write the same real directory. Use `cairn test
write/read` to check that before relying on a handoff.

## Removal

Delete `.cairn/` and `cairn/`, then remove the marked Cairn Lite block from
`AGENTS.md`. Remove `@AGENTS.md` from `CLAUDE.md` only if nothing else uses it.
