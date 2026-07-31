from __future__ import annotations

import json


START_MARKER = "<!-- cairn-lite:start -->"
END_MARKER = "<!-- cairn-lite:end -->"

AGENTS_BLOCK = f"""\
{START_MARKER}
## Cairn Lite

- Read `.cairn/PROTOCOL.md`, then the latest 5 entries in `cairn/LOG.md`.
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

## Removal

Delete `.cairn/` and `cairn/`, then remove the marked Cairn Lite block from
`AGENTS.md`. Remove `@AGENTS.md` from `CLAUDE.md` only if nothing else uses it.
"""

CONFIG = json.dumps(
    {
        "version": 1,
        "latest_log_entries": 5,
        "external_writes_require_confirmation": True,
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
