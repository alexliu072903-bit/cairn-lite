from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from cairn_lite.cli import (
    CairnError,
    HANDOFF_PATH,
    handoff_clean,
    handoff_read,
    handoff_write,
    init_project,
    main,
    status_project,
    validate_project,
)
from cairn_lite.templates import END_MARKER, START_MARKER


class InitTests(unittest.TestCase):
    def test_init_creates_valid_project_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            init_project(directory)
            root = Path(directory)
            first_agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            first_claude = (root / "CLAUDE.md").read_text(encoding="utf-8")

            init_project(directory)

            self.assertEqual(
                first_agents,
                (root / "AGENTS.md").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                first_claude,
                (root / "CLAUDE.md").read_text(encoding="utf-8"),
            )
            self.assertEqual(first_agents.count(START_MARKER), 1)
            self.assertEqual(first_agents.count(END_MARKER), 1)
            self.assertTrue(validate_project(directory)["ok"])

    def test_init_appends_without_overwriting_existing_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text(
                "# Existing\n\nKeep this rule.\n", encoding="utf-8"
            )
            (root / "CLAUDE.md").write_text(
                "# Claude\n\nKeep this too.\n", encoding="utf-8"
            )

            init_project(directory)

            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            claude = (root / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("Keep this rule.", agents)
            self.assertIn(START_MARKER, agents)
            self.assertIn("Keep this too.", claude)
            self.assertIn("@AGENTS.md", claude)

    def test_broken_marker_aborts_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text(START_MARKER, encoding="utf-8")

            with self.assertRaises(CairnError):
                init_project(directory)

            self.assertFalse((root / ".cairn").exists())

    def test_reversed_markers_abort_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text(
                f"{END_MARKER}\n{START_MARKER}\n", encoding="utf-8"
            )

            with self.assertRaises(CairnError):
                init_project(directory)

            self.assertFalse((root / ".cairn").exists())

    def test_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            init_project(directory, dry_run=True)
            self.assertEqual(list(Path(directory).iterdir()), [])


class ValidationTests(unittest.TestCase):
    def test_invalid_config_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_project(directory)
            config_path = root / ".cairn/config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["external_writes_require_confirmation"] = False
            config_path.write_text(json.dumps(config), encoding="utf-8")

            result = validate_project(directory)

            self.assertFalse(result["ok"])
            self.assertTrue(
                any(
                    "external_writes_require_confirmation" in error
                    for error in result["errors"]
                )
            )

    def test_boolean_log_limit_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_project(directory)
            config_path = root / ".cairn/config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["latest_log_entries"] = True
            config_path.write_text(json.dumps(config), encoding="utf-8")

            result = validate_project(directory)

            self.assertFalse(result["ok"])
            self.assertIn(
                "latest_log_entries must be a positive integer",
                result["errors"],
            )

    def test_status_reads_topics_and_recent_log(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_project(directory)
            (root / "cairn/topics/example.md").write_text(
                """\
---
status: validated
updated: 2026-07-31
---

# Example

## Current judgment
Done.

## Evidence
Test.

## Boundaries
Local only.

## Evolution
Created.

## Sources
Test.

## Validation log
Passed.
""",
                encoding="utf-8",
            )
            (root / "cairn/LOG.md").write_text(
                "# Cairn log\n\n## 2026-07-31 — Example\n\n- See topic.\n",
                encoding="utf-8",
            )

            result = status_project(directory)

            self.assertEqual(result["entries"][0]["title"], "2026-07-31 — Example")
            self.assertEqual(result["topics"][0]["status"], "validated")
            self.assertTrue(validate_project(directory)["ok"])


class HandoffTests(unittest.TestCase):
    def test_different_agents_complete_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            init_project(directory)
            written = handoff_write(directory, "claude")
            read = handoff_read(directory, "codex")

            self.assertTrue(written["ok"])
            self.assertTrue(read["ok"])
            self.assertRegex(read["code"], r"^\d{6}$")
            self.assertEqual(read["writer"], "claude")
            self.assertEqual(read["reader"], "codex")
            self.assertTrue((Path(directory) / HANDOFF_PATH).exists())
            self.assertTrue(handoff_clean(directory))
            self.assertFalse((Path(directory) / HANDOFF_PATH).exists())

    def test_same_agent_cannot_verify_its_own_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            init_project(directory)
            handoff_write(directory, "Codex")

            with self.assertRaises(CairnError):
                handoff_read(directory, "codex")

    def test_cli_hides_code_on_write_and_prints_it_on_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            init_project(directory)
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(io.StringIO()):
                write_exit = main(
                    ["test", "write", directory, "--agent", "claude"]
                )
            state = json.loads(
                (Path(directory) / HANDOFF_PATH).read_text(encoding="utf-8")
            )
            self.assertEqual(write_exit, 0)
            self.assertNotIn(state["code"], output.getvalue())

            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(io.StringIO()):
                read_exit = main(
                    ["test", "read", directory, "--agent", "codex"]
                )
            self.assertEqual(read_exit, 0)
            self.assertIn(state["code"], output.getvalue())


class HandoffFileTests(unittest.TestCase):
    def _new(self, directory: str) -> Path:
        from cairn_lite.cli import handoff_new

        init_project(directory)
        return handoff_new(directory, "site-v1", "Site v1", "claude", "codex")

    def _set(self, path: Path, old: str, new: str) -> None:
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_init_keeps_handoffs_out_of_git(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".gitignore").write_text("node_modules/", encoding="utf-8")
            init_project(directory)
            init_project(directory)
            ignore = (root / ".gitignore").read_text(encoding="utf-8")
            self.assertEqual(ignore, "node_modules/\ncairn/handoffs/\n")

    def test_new_handoff_is_valid_and_listed(self) -> None:
        from cairn_lite.cli import handoff_new, handoff_status

        with tempfile.TemporaryDirectory() as directory:
            self._new(directory)
            result = validate_project(directory)
            self.assertTrue(result["ok"], result["errors"])
            self.assertEqual(result["handoff_count"], 1)
            [item] = handoff_status(directory)["handoffs"]
            self.assertEqual(
                (item["id"], item["status"], item["to"]),
                ("site-v1", "open", "codex"),
            )
            with self.assertRaises(CairnError):
                handoff_new(directory, "site-v1", "Again", "claude", "codex")
            with self.assertRaises(CairnError):
                handoff_new(directory, "Bad Id", "Bad", "claude", "codex")

    def test_planner_url_is_optional_and_must_be_https(self) -> None:
        from cairn_lite.cli import handoff_new, handoff_status

        with tempfile.TemporaryDirectory() as directory:
            init_project(directory)
            url = "https://claude.ai/code/project/demo"
            path = handoff_new(
                directory, "with-url", "With URL", "claude", "codex", url
            )
            text = path.read_text(encoding="utf-8")
            self.assertIn(f"planner_url: {url}\n", text)
            handoff_new(directory, "no-url", "No URL", "claude", "codex")
            urls = {
                item["id"]: item["planner_url"]
                for item in handoff_status(directory)["handoffs"]
            }
            self.assertEqual(urls, {"no-url": None, "with-url": url})
            self.assertTrue(validate_project(directory)["ok"])

            with self.assertRaises(CairnError):
                handoff_new(
                    directory, "bad-url", "Bad", "claude", "codex", "http://x"
                )
            self._set(path, url, "file:///Users/me/plan.md")
            result = validate_project(directory)
            self.assertFalse(result["ok"])
            self.assertIn("`planner_url` must start with https://", result["errors"][0])

    def test_acknowledged_requires_readback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._new(directory)
            self._set(path, "status: open", "status: acknowledged")
            errors = validate_project(directory)["errors"]
            self.assertTrue(any("no Readback" in error for error in errors))

            self._set(path, "## Log", "Build the site; stop at the PR.\n\n## Log")
            self.assertTrue(validate_project(directory)["ok"])

    def test_blocked_and_open_questions_must_agree(self) -> None:
        from cairn_lite.cli import handoff_status

        with tempfile.TemporaryDirectory() as directory:
            path = self._new(directory)
            self._set(path, "## Log", "Goal understood.\n\n## Log")
            self._set(path, "status: open", "status: blocked")
            errors = validate_project(directory)["errors"]
            self.assertTrue(any("no open question" in error for error in errors))

            path.write_text(
                path.read_text(encoding="utf-8") + "\n- [ ] Keep Writing?\n",
                encoding="utf-8",
            )
            self.assertTrue(validate_project(directory)["ok"])
            [item] = handoff_status(directory)["handoffs"]
            self.assertEqual(item["open_questions"], 1)

            self._set(path, "status: blocked", "status: running")
            errors = validate_project(directory)["errors"]
            self.assertTrue(any("open questions" in error for error in errors))

    def test_done_requires_log(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._new(directory)
            self._set(path, "## Log", "Goal understood.\n\n## Log")
            self._set(path, "status: open", "status: done")
            errors = validate_project(directory)["errors"]
            self.assertTrue(any("no Log entry" in error for error in errors))

    def test_cli_handoff_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            init_project(directory)
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(
                    [
                        "handoff", "new", "site-v1", "--title", "Site v1",
                        "--from", "claude", "--to", "codex", "--path", directory,
                        "--planner-url", "https://claude.ai/code/project/demo",
                    ]
                )
            self.assertEqual(code, 0)
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(["handoff", "status", directory])
            self.assertEqual(code, 0)
            self.assertIn("open: site-v1 (claude -> codex)", output.getvalue())
            self.assertIn(
                "planner_url: https://claude.ai/code/project/demo",
                output.getvalue(),
            )


if __name__ == "__main__":
    unittest.main()
