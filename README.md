# Cairn Lite

**A portable project-context protocol for handoffs across AI agents.**

Cairn Lite lets Codex, Claude, and other file-capable agents recover the same
project decisions, evidence, and boundaries from a small set of plain Markdown
files.

It is not a universal AI memory. It is a transparent, Git-friendly project
learning layer that stays under your control.

> Status: experimental. The file format is usable, but may evolve before 1.0.

## Why

Agent conversations are isolated. Project knowledge should not be.

Cairn Lite gives each agent the same recovery path:

```text
enter project
  → read a thin instruction block
  → scan the latest 5 log entries
  → open only the relevant topic
  → record only material changes
```

This reduces repeated context handoffs without turning `AGENTS.md` or
`CLAUDE.md` into an ever-growing memory dump.

## Install

Python 3.9+ is required.

```bash
pipx install git+https://github.com/alexliu072903-bit/cairn-lite.git
```

For local development:

```bash
git clone https://github.com/alexliu072903-bit/cairn-lite.git
cd cairn-lite
python3 -m pip install -e .
```

## Quick start

Initialize Cairn Lite inside an existing project:

```bash
cd /path/to/your-project
cairn init
cairn validate
cairn status
```

`cairn init` is additive and idempotent:

- it creates missing Cairn files;
- it appends a marked, removable block to an existing `AGENTS.md`;
- it appends `@AGENTS.md` to an existing `CLAUDE.md` when needed;
- it never overwrites existing project instructions or Cairn files.

Preview all changes first:

```bash
cairn init --dry-run
```

## Generated structure

```text
AGENTS.md                    thin routing instructions
CLAUDE.md                    imports AGENTS.md
.cairn/
  PROTOCOL.md                complete writing and reading rules
  config.json                small machine-readable configuration
cairn/
  LOG.md                     reverse-chronological pointer index
  topics/
    README.md                topic format guide
    <topic>.md               one evolving project conclusion
```

Agents read the latest log entries and only the topic relevant to the current
task. They do not load the whole knowledge directory by default.

## What belongs in Cairn

Record a change only when at least one condition is true:

- a product or technical decision changed;
- a failure, root cause, or fix was verified;
- an existing conclusion was disproved or materially narrowed;
- a validated pattern may be reusable elsewhere.

Do not record routine progress, raw meeting notes, task status, unverified
guesses, secrets, credentials, or personal data.

Product Frames, PRDs, code, schemas, and task systems remain authoritative for
their own scope. Cairn Lite records why a conclusion changed and what evidence
supports it; it does not replace the source of truth.

## Commands

| Command | Purpose |
|---|---|
| `cairn init [path]` | Add the protocol without overwriting existing files |
| `cairn validate [path]` | Check structure, config, topics, and log limits |
| `cairn status [path]` | Show recent changes and topic states |
| `cairn test write --agent NAME [path]` | Write a hidden handoff challenge |
| `cairn test read --agent NAME [path]` | Read and verify the challenge from another agent |
| `cairn test clean [path]` | Remove the temporary challenge |

All commands support `--help`. `validate` and `status` also support `--json`.

## Cross-agent test

1. Open the same project as the **primary folder** in Claude Desktop Code.
2. Ask Claude to run:

   ```bash
   cairn test write --agent claude
   ```

   The six-digit code is written to the project but not printed.

3. Open a fresh Codex task with the same primary folder.
4. Ask Codex to run:

   ```bash
   cairn test read --agent codex
   ```

The test passes only when a different agent reads the challenge from the same
resolved project directory.

File access alone is not enough. In each agent, also confirm:

```text
primary folder
working directory
automatically active AGENTS.md
```

All three must point to the same project root.

The CLI verifies distinct agent labels and one resolved filesystem root. It
cannot authenticate which AI product issued a command, so the cold-session
procedure above remains part of the test.

## Safety and removal

Cairn Lite does not send data to an external service. External knowledge-base
writes require explicit human confirmation in the default protocol.

To remove it:

1. delete `.cairn/` and `cairn/`;
2. remove the text between `<!-- cairn-lite:start -->` and
   `<!-- cairn-lite:end -->` in `AGENTS.md`;
3. remove `@AGENTS.md` from `CLAUDE.md` only if Cairn Lite added it and nothing
   else depends on it.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please keep proposals narrow,
agent-agnostic, and reversible.

## License

[MIT](LICENSE)

## Appendix

- [HISTORY.md](HISTORY.md) — why Cairn Lite was redesigned this way
- [docs/PROTOCOL.md](docs/PROTOCOL.md) — protocol specification
- [SECURITY.md](SECURITY.md) — security and privacy reporting

## Acknowledgements

Cairn Lite was inspired by
[iBlinkQ/project-cairn](https://github.com/iBlinkQ/project-cairn). This
implementation was written from scratch around a smaller, local-first,
agent-agnostic protocol.
