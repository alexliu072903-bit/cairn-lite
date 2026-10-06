from __future__ import annotations

import json


START_MARKER = "<!-- cairn-lite:start -->"
END_MARKER = "<!-- cairn-lite:end -->"

AGENTS_BLOCK = f"""\
{START_MARKER}
## Cairn Lite

- Run `cairn handoff status` (without the CLI, read the front matter of
  `cairn/handoffs/*.md`). If a handoff addressed to you is `open`,
  `acknowledged`, or `running`, read `.cairn/PROTOCOL.md` and follow it before
  other work.
- Do not replace authoritative project documents or existing instructions.
- External writes (push, publish, external knowledge bases) require explicit
  human confirmation in your own conversation.
{END_MARKER}
"""

PROTOCOL = """\
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

## Removal

Delete `.cairn/` and `cairn/`, then remove the marked Cairn Lite block from
`AGENTS.md`. Remove `@AGENTS.md` from `CLAUDE.md` only if nothing else uses it.
"""

CONFIG = json.dumps(
    {
        "version": 2,
        "external_writes_require_confirmation": True,
        "handoffs_in_git": False,
    },
    indent=2,
) + "\n"

HANDOFF_STATUSES = (
    "open",
    "acknowledged",
    "running",
    "blocked",
    "done",
    "cancelled",
)

HANDOFF_HEADINGS = (
    "Goal",
    "Decisions",
    "Design",
    "Acceptance",
    "Out of scope",
    "Readback",
    "Log",
    "Questions",
)

HANDOFF_TEMPLATE = """\
---
handoff: {id}
status: open
from: {from_agent}
to: {to_agent}
{planner_line}created: {date}
---

# {title}

## Goal

<!-- One paragraph: what the human owner wants when this is done. -->

## Decisions

<!-- Pointers only, never copies, e.g. `cairn-context: my-project/v1-scope`
or a file path. The executor does not change these. -->

## Design

<!-- Hypothesis. The executor may change it and records why in the Log. -->

## Acceptance

<!-- Checkable items. Only the human owner changes them. -->

## Out of scope

## Readback

<!-- Executor, before any other work: goal, out of scope, stop point. -->

## Log

<!-- Executor appends: date, step, result, evidence, deviation. -->

## Questions

<!-- `- [ ] question`; answered as `- [x]` with the answer below. -->
"""
