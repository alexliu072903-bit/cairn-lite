# Changelog

All notable changes to this project will be documented here.

## [Unreleased]

- Reposition Cairn Lite around handoffs: one shared file through which a
  planner agent and an executor agent pass work and results.
- Add `cairn handoff new` and `cairn handoff status`, handoff validation, and
  the optional `planner_url` field.
- Remove project notes (`cairn/LOG.md`, `cairn/topics/`). Durable decisions
  belong in a decision store such as cairn-context. Projects initialized by
  earlier versions still validate; their notes files are ignored.
- `cairn status` now lists handoffs, the same as `cairn handoff status`.

## [0.1.0] - 2026-07-31

- Add non-destructive, idempotent project initialization.
- Add structural validation and compact status output.
- Add a blind cross-agent handoff test.
- Add the first version of the Cairn Lite protocol.
