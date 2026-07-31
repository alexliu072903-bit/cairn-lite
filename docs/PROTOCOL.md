# Cairn Lite protocol

## Responsibility

Cairn Lite is the project-learning layer. It preserves the reasoning and
evidence behind material project conclusions so another session or agent can
continue without reconstructing history.

Product Frames, PRDs, code, schemas, and task systems remain authoritative for
their own scope. Cairn Lite may point to them but must not duplicate or replace
them.

## Startup reading

1. Read `.cairn/PROTOCOL.md`.
2. Read the latest configured entries in `cairn/LOG.md`.
3. Identify the topic relevant to the current task.
4. Read only that topic.
5. Read older entries or other topics only when a visible pointer requires it.

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
- Each LOG entry has no more than 6 non-empty body lines.
- `cairn/topics/<topic>.md` holds the current conclusion for one topic.
- A topic states its evidence, boundaries, evolution, sources, and validation.
- When a conclusion changes, update Current judgment and preserve the prior
  judgment under Evolution.
- Add a LOG pointer; do not silently rewrite history.
- Never write to an external knowledge base without explicit human
  confirmation of the candidate, scope, and destination.

## Topic contract

Every topic contains:

1. Current judgment
2. Evidence
3. Boundaries
4. Evolution
5. Sources
6. Validation log

Allowed status values are:

- `hypothesis`
- `validated`
- `invalidated`

Unknowns remain hypotheses. Do not convert them into settled facts.

## Portability

The protocol uses plain Markdown and JSON. Agent-specific entry files are thin
routing layers; durable project knowledge remains in `cairn/`.

Different copies of a project can diverge. Use an existing synchronization or
version-control system when multiple machines need the same files.
