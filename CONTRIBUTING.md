# Contributing

Contributions are welcome when they keep Cairn Lite:

- agent-agnostic;
- local-first;
- inspectable as plain files;
- non-destructive by default;
- small enough to understand without a framework.

## Development

```bash
git clone https://github.com/alexliu072903-bit/cairn-lite.git
cd cairn-lite
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
```

## Pull requests

1. Keep each change focused.
2. Add or update tests for behavior changes.
3. Update README or protocol documentation when user-facing behavior changes.
4. Do not add runtime dependencies without a concrete need.
5. Do not introduce automatic external writes or destructive migrations.

Bug reports should include the command, expected result, actual result, Python
version, operating system, and a minimal project structure when safe to share.
Never include secrets or private project content.
