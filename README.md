# Cairn Lite

[English](README.md) | [简体中文](README.zh-CN.md)

**A local protocol for two AI agents to work through one shared handoff file.**

The planner writes the goal, boundaries, and acceptance criteria. The executor
restates the task, does the work, logs each step, and writes blocking questions
back into the same file. The human shows up in three places only: setting the
goal, making decisions, and accepting the result.

It replaces this pattern: write a long handoff document, paste a prompt into
another agent, then relay progress and questions back and forth by hand.

> Status: experimental. The file format is usable, but may evolve before 1.0.

## One full loop

```text
human: a one-line goal
  → the planner (e.g. Claude in the cloud) writes a handoff: goal, decisions,
    suggested design, acceptance, out of scope
  → the executor (e.g. Codex on your machine) enters the project and finds the
    handoff through AGENTS.md on its own
  → the executor writes a readback, works, and logs each step with evidence
  → a question that would change a decision, acceptance, or scope goes under
    Questions; the handoff is marked blocked and the executor stops
  → the planner or the human answers in the same file; the executor re-reads
    the handoff whenever it is resumed
  → every acceptance item is met: done
```

The planner reads progress from the handoff instead of asking the human, and the
human copies and pastes nothing.

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

Add the protocol to the project you want to hand off, then open a handoff:

```bash
cd /path/to/your-project
cairn init
cairn handoff new site-v1 --title "Personal site v1" --from claude --to codex \
  --planner-url https://claude.ai/your-project-link
```

The planner fills in Goal, Decisions, Design, Acceptance, and Out of scope in
`cairn/handoffs/site-v1.md`. The executor finds it the next time it enters the
project; no prompt needs to be pasted.

See every handoff and its status at any time:

```bash
cairn handoff status
```

`cairn init` is append-only, safe to run more than once, and never overwrites
existing files. Preview it with `cairn init --dry-run`. It:

- appends a marked, removable block to `AGENTS.md` that tells each agent to
  check for handoffs addressed to it when it enters the project;
- appends `@AGENTS.md` to `CLAUDE.md` when needed;
- adds `cairn/handoffs/` to `.gitignore`. Handoffs are working notes that often
  hold local paths and private context, so they stay out of Git by default.

## Handoffs

One file per piece of work: `cairn/handoffs/<id>.md`.

The front matter holds the status (`open`, `acknowledged`, `running`,
`blocked`, `done`, `cancelled`), plus `from`, `to`, and an optional
`planner_url`.

| Section | Owner | Rule |
|---|---|---|
| Goal | human | What the human wants when this is done |
| Decisions | human | Pointers to confirmed decisions, never copies |
| Design | planner | A hypothesis; the executor may change it and logs why |
| Acceptance, Out of scope | human | Only the owner changes them |
| Readback | executor | Written first: the goal, what is out of scope, where to stop |
| Log | executor | One entry per step, with evidence |
| Questions | executor | Questions that would change a decision; then `blocked` and stop |

Executor rules:

1. Before any other work, write the readback in your own words (at most 6
   lines) and set `status: acknowledged`.
2. Set `status: running` and work; after each step, append a Log entry with
   evidence.
3. When a question would change Decisions, Acceptance, or Out of scope, add it
   under Questions, set `status: blocked`, and stop.
4. When every acceptance item is met, set `status: done`.
5. Whenever you are resumed ("continue", a new message, a new session), re-read
   the handoff first instead of relying on conversation memory.

A record in a handoff is not the human's authorization. Pushing, publishing,
and other external actions need the human's confirmation in the executor's own
conversation.

`cairn validate` checks that status and content agree: `acknowledged` needs a
readback, `blocked` needs an open question, `done` needs a log entry, and
`planner_url` must start with `https://`.

## Working with other tools

Cairn Lite covers one piece of work, from handing it off to finishing it. It
works on its own, or as part of a loop with:

- **[cairn-context](https://github.com/alexliu072903-bit/cairn-context)**:
  records durable decisions across tasks. A handoff's Decisions section points
  to them instead of copying them.
- **AirJelly**: reads a handoff's status when the executor stops. On `blocked`
  or `done` it shows a card so the human can choose what happens next; when the
  work needs re-planning, it uses `planner_url` to send the human back to the
  planner.

## Commands

| Command | Purpose |
|---|---|
| `cairn init [path]` | Add the protocol without overwriting existing files |
| `cairn handoff new ID --title T --from A --to B [--planner-url URL]` | Create a handoff |
| `cairn handoff status [path]` | List handoffs, their status, and open questions |
| `cairn validate [path]` | Check structure, config, and handoffs |
| `cairn status [path]` | Same as `cairn handoff status` |
| `cairn test write/read/clean` | Check that two agents share one project directory (see appendix) |

All commands support `--help`. `validate`, `status`, and `handoff status` also
support `--json`.

## Security and removal

Cairn Lite does not send data to external services. The protocol requires
explicit human confirmation before writing to any external knowledge base.

To remove it:

1. delete `.cairn/` and `cairn/`;
2. delete the block between `<!-- cairn-lite:start -->` and
   `<!-- cairn-lite:end -->` in `AGENTS.md`;
3. remove `@AGENTS.md` from `CLAUDE.md` only if nothing else depends on it.

## Appendix

### Upgrading from earlier versions

Earlier versions of Cairn Lite also kept project notes (`cairn/LOG.md` and
`cairn/topics/`). They have been removed; [HISTORY.md](HISTORY.md) explains
why. Older projects still pass `cairn validate`: those files are ignored, and
you may keep or delete them. For decisions you want to keep long term, use
cairn-context.

`cairn init` does not rewrite an existing instruction block. To switch to the
new entry rules, delete the content between `<!-- cairn-lite:start -->` and
`<!-- cairn-lite:end -->` in `AGENTS.md` and `.cairn/PROTOCOL.md`, then run
`cairn init` again.

### Check that both agents see the same directory

Handoffs only work when the planner and the executor read and write the same
real directory.

1. In Claude, run `cairn test write --agent claude`. A six-digit code is
   written to the project without being printed.
2. In Codex, open the same directory and run `cairn test read --agent codex`.
3. When it passes, run `cairn test clean`.

Also confirm that the primary folder, the working directory, and the
auto-loaded `AGENTS.md` point to the same project root in both agents. The CLI
can verify the directory, not which AI product issued the command.

### More documents

- [docs/PROTOCOL.md](docs/PROTOCOL.md): protocol specification
- [HISTORY.md](HISTORY.md): how Cairn Lite evolved
- [CONTRIBUTING.md](CONTRIBUTING.md): contributing
- [SECURITY.md](SECURITY.md): reporting security and privacy issues

## License

[MIT](LICENSE)
