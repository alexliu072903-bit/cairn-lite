from __future__ import annotations

import json


START_MARKER = "<!-- cairn-lite:start -->"
END_MARKER = "<!-- cairn-lite:end -->"

AGENTS_BLOCK = f"""\
{START_MARKER}
## Cairn Lite

- Read `.cairn/PROTOCOL.md`, then the latest 5 entries in `cairn/LOG.md`.
- Run `cairn handoff status` (without the CLI, read the front matter of
  `cairn/handoffs/*.md`). If a handoff addressed to you is `open`,
  `acknowledged`, or `running`, follow the Handoffs section of the protocol
  before other work.
- Read only topic files relevant to the current task.
- Record only material changes defined by the protocol.
- Do not replace authoritative project documents or existing instructions.
- External knowledge-base writes require explicit human confirmation.
{END_MARKER}
"""

PROTOCOL = """\
# Cairn Lite protocol

## Responsibility

Cairn Lite is the project-learning layer. It keeps the reasoning and evidence
behind material project conclusions so another session or agent can continue
without reconstructing history.

Product Frames, PRDs, code, schemas, and task systems remain authoritative for
their own scope. Cairn Lite may point to them but must not duplicate or replace
them.

## Startup reading

1. Read the latest 5 entries in `cairn/LOG.md`.
2. Identify the topic relevant to the current task.
3. Read only that topic file.
4. Read older entries or other topics only when a visible pointer requires it.

Do not load the entire `cairn/` directory by default.

## Material-change test

Record a change only when at least one condition is true:

- A product or technical decision changed.
- A failure, root cause, or fix was verified.
- An existing conclusion was disproved or materially narrowed.
- A validated pattern may be reusable in another project.

Do not record routine progress, file lists, raw meeting notes, unverified
guesses, task status, secrets, credentials, or personal data.

## Writing rules

- `cairn/LOG.md` is a short reverse-chronological index.
- Each LOG entry has at most 6 non-empty body lines.
- `cairn/topics/<topic>.md` holds the current conclusion for one topic.
- When a conclusion changes, preserve the prior judgment under Evolution.
- Add a LOG pointer; do not silently rewrite history.
- Never write to an external knowledge base without explicit human
  confirmation of the candidate, scope, and destination.

## Topic contract

Each topic contains:

1. Current judgment
2. Evidence
3. Boundaries
4. Evolution
5. Sources
6. Validation log

Allowed status values are `hypothesis`, `validated`, and `invalidated`.
Unknowns remain hypotheses.

## Handoffs

A handoff passes one piece of work from the agent that planned it to the agent
that carries it out, and carries the results back. It is a working file, not
project knowledge: it lives in `cairn/handoffs/<id>.md`, stays out of Git by
default, and is exempt from the material-change test. When a handoff produces
a durable conclusion, record it as a topic or in the decision store it cites.

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
   decisions and sources instead of repeating them.
2. On re-entry, read the Readback, Log, and Questions before planning again.
   Answer a question by changing `- [ ]` to `- [x]` and writing the answer
   under it; ask the human owner when the answer is theirs to give.

Do not delete Log entries or answered questions. `cairn validate` checks the
statuses and sections.

## Removal

Delete `.cairn/` and `cairn/`, then remove the marked Cairn Lite block from
`AGENTS.md`. Remove `@AGENTS.md` from `CLAUDE.md` only if nothing else uses it.
"""

CONFIG = json.dumps(
    {
        "version": 1,
        "latest_log_entries": 5,
        "external_writes_require_confirmation": True,
        "handoffs_in_git": False,
    },
    indent=2,
) + "\n"

LOG = """\
# Cairn log

Newest entries appear first. Each entry is a short summary plus a pointer, not
the full conclusion. Keep each entry to at most 6 non-empty body lines.
"""

TOPICS_README = """\
# Topic files

Create one Markdown file per durable project topic.

```markdown
---
status: hypothesis
updated: YYYY-MM-DD
---

# Topic name

## Current judgment

## Evidence

## Boundaries

## Evolution

## Sources

## Validation log
```

Allowed status values: `hypothesis`, `validated`, `invalidated`.
"""

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
created: {date}
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
