from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import __version__
from .templates import (
    AGENTS_BLOCK,
    CONFIG,
    END_MARKER,
    LOG,
    PROTOCOL,
    START_MARKER,
    TOPICS_README,
)


CONFIG_PATH = Path(".cairn/config.json")
PROTOCOL_PATH = Path(".cairn/PROTOCOL.md")
LOG_PATH = Path("cairn/LOG.md")
TOPICS_PATH = Path("cairn/topics")
HANDOFF_PATH = Path(".cairn/handoff-test.json")
TOPIC_HEADINGS = (
    "Current judgment",
    "Evidence",
    "Boundaries",
    "Evolution",
    "Sources",
    "Validation log",
)
TOPIC_STATUSES = {"hypothesis", "validated", "invalidated"}


class CairnError(RuntimeError):
    pass


def _root(path: str) -> Path:
    return Path(path).expanduser().resolve()


def _write_new(path: Path, content: str, dry_run: bool) -> str:
    if path.exists():
        return f"skip   {path}"
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return f"create {path}"


def _preflight_agents(path: Path) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    starts = text.count(START_MARKER)
    ends = text.count(END_MARKER)
    reversed_markers = (
        starts == 1
        and ends == 1
        and text.index(START_MARKER) > text.index(END_MARKER)
    )
    if starts != ends or starts > 1 or reversed_markers:
        raise CairnError(
            f"{path} has incomplete or duplicate Cairn Lite markers; "
            "fix them before running init"
        )


def _ensure_agents(path: Path, dry_run: bool) -> str:
    if not path.exists():
        content = "# Project instructions\n\n" + AGENTS_BLOCK
        return _write_new(path, content, dry_run)

    text = path.read_text(encoding="utf-8")
    if START_MARKER in text:
        return f"skip   {path}"

    if not dry_run:
        separator = "\n" if text.endswith("\n") else "\n\n"
        path.write_text(text + separator + AGENTS_BLOCK, encoding="utf-8")
    return f"append {path}"


def _ensure_claude(path: Path, dry_run: bool) -> str:
    import_line = "@AGENTS.md"
    if not path.exists():
        return _write_new(path, import_line + "\n", dry_run)

    text = path.read_text(encoding="utf-8")
    if any(line.strip() == import_line for line in text.splitlines()):
        return f"skip   {path}"

    if not dry_run:
        separator = "" if not text or text.endswith("\n") else "\n"
        path.write_text(text + separator + import_line + "\n", encoding="utf-8")
    return f"append {path}"


def init_project(path: str, dry_run: bool = False) -> List[str]:
    root = _root(path)
    if root.exists() and not root.is_dir():
        raise CairnError(f"{root} is not a directory")

    _preflight_agents(root / "AGENTS.md")

    if not dry_run:
        root.mkdir(parents=True, exist_ok=True)

    actions = [
        _write_new(root / PROTOCOL_PATH, PROTOCOL, dry_run),
        _write_new(root / CONFIG_PATH, CONFIG, dry_run),
        _write_new(root / LOG_PATH, LOG, dry_run),
        _write_new(root / TOPICS_PATH / "README.md", TOPICS_README, dry_run),
        _ensure_agents(root / "AGENTS.md", dry_run),
        _ensure_claude(root / "CLAUDE.md", dry_run),
    ]
    return actions


def _load_config(root: Path) -> Dict[str, Any]:
    path = root / CONFIG_PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CairnError(f"missing {path}; run `cairn init` first") from exc
    except json.JSONDecodeError as exc:
        raise CairnError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CairnError(f"{path} must contain a JSON object")
    return data


def _frontmatter(text: str) -> Dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    result: Dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def _log_blocks(text: str) -> List[Tuple[str, List[str], str]]:
    matches = list(re.finditer(r"(?m)^## (.+)$", text))
    blocks: List[Tuple[str, List[str], str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end]
        non_empty = [line for line in body.splitlines() if line.strip()]
        rendered = text[match.start() : end].strip()
        blocks.append((match.group(1).strip(), non_empty, rendered))
    return blocks


def validate_project(path: str) -> Dict[str, Any]:
    root = _root(path)
    errors: List[str] = []
    warnings: List[str] = []

    required = (
        PROTOCOL_PATH,
        CONFIG_PATH,
        LOG_PATH,
        TOPICS_PATH / "README.md",
        Path("AGENTS.md"),
        Path("CLAUDE.md"),
    )
    for relative in required:
        if not (root / relative).is_file():
            errors.append(f"missing {relative}")

    config: Dict[str, Any] = {}
    if (root / CONFIG_PATH).is_file():
        try:
            config = _load_config(root)
        except CairnError as exc:
            errors.append(str(exc))
        else:
            if config.get("version") != 1:
                errors.append("config version must be 1")
            latest_entries = config.get("latest_log_entries")
            if type(latest_entries) is not int or latest_entries < 1:
                errors.append("latest_log_entries must be a positive integer")
            if config.get("external_writes_require_confirmation") is not True:
                errors.append(
                    "external_writes_require_confirmation must be true"
                )

    agents_path = root / "AGENTS.md"
    if agents_path.is_file():
        text = agents_path.read_text(encoding="utf-8")
        complete_block = (
            text.count(START_MARKER) == 1
            and text.count(END_MARKER) == 1
            and text.index(START_MARKER) < text.index(END_MARKER)
        )
        if not complete_block:
            errors.append("AGENTS.md must contain one complete Cairn Lite block")

    claude_path = root / "CLAUDE.md"
    if claude_path.is_file():
        lines = claude_path.read_text(encoding="utf-8").splitlines()
        if not any(line.strip() == "@AGENTS.md" for line in lines):
            errors.append("CLAUDE.md must import @AGENTS.md")

    log_path = root / LOG_PATH
    if log_path.is_file():
        for title, body_lines, _ in _log_blocks(
            log_path.read_text(encoding="utf-8")
        ):
            if len(body_lines) > 6:
                errors.append(
                    f"LOG entry {title!r} has {len(body_lines)} body lines; max is 6"
                )

    topic_files = []
    topics_dir = root / TOPICS_PATH
    if topics_dir.is_dir():
        topic_files = sorted(
            item
            for item in topics_dir.glob("*.md")
            if item.name.lower() != "readme.md"
        )

    if not topic_files:
        warnings.append("no topic files yet")

    for topic in topic_files:
        text = topic.read_text(encoding="utf-8")
        metadata = _frontmatter(text)
        status = metadata.get("status")
        if status not in TOPIC_STATUSES:
            errors.append(
                f"{topic.relative_to(root)} has invalid or missing status"
            )
        for heading in TOPIC_HEADINGS:
            if f"## {heading}" not in text:
                errors.append(
                    f"{topic.relative_to(root)} is missing `## {heading}`"
                )

    return {
        "ok": not errors,
        "root": str(root),
        "errors": errors,
        "warnings": warnings,
        "topic_count": len(topic_files),
    }


def status_project(path: str) -> Dict[str, Any]:
    root = _root(path)
    config = _load_config(root)
    limit = config.get("latest_log_entries", 5)
    if not isinstance(limit, int) or limit < 1:
        raise CairnError("latest_log_entries must be a positive integer")

    log_path = root / LOG_PATH
    if not log_path.is_file():
        raise CairnError(f"missing {log_path}; run `cairn init` first")

    entries = [
        {"title": title, "body": body}
        for title, _, body in _log_blocks(log_path.read_text(encoding="utf-8"))[
            :limit
        ]
    ]

    topics = []
    topics_dir = root / TOPICS_PATH
    if topics_dir.is_dir():
        for topic in sorted(topics_dir.glob("*.md")):
            if topic.name.lower() == "readme.md":
                continue
            metadata = _frontmatter(topic.read_text(encoding="utf-8"))
            topics.append(
                {
                    "file": str(topic.relative_to(root)),
                    "status": metadata.get("status", "unknown"),
                    "updated": metadata.get("updated", "unknown"),
                }
            )

    return {"root": str(root), "entries": entries, "topics": topics}


def _write_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def handoff_write(path: str, agent: str, replace: bool = False) -> Dict[str, Any]:
    root = _root(path)
    _load_config(root)
    state_path = root / HANDOFF_PATH
    if state_path.exists() and not replace:
        raise CairnError(
            f"{state_path} already exists; use `cairn test clean` or --replace"
        )

    state = {
        "version": 1,
        "root": str(root),
        "writer": agent,
        "code": f"{secrets.randbelow(1_000_000):06d}",
        "written_at": datetime.now(timezone.utc).isoformat(),
        "readers": [],
    }
    _write_json_atomic(state_path, state)
    return {
        "ok": True,
        "message": "handoff challenge written; code intentionally hidden",
        "root": str(root),
        "writer": agent,
    }


def handoff_read(path: str, agent: str) -> Dict[str, Any]:
    root = _root(path)
    state_path = root / HANDOFF_PATH
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CairnError(
            f"missing {state_path}; ask the source agent to run `cairn test write`"
        ) from exc
    except json.JSONDecodeError as exc:
        raise CairnError(f"invalid handoff state: {exc}") from exc

    if state.get("root") != str(root):
        raise CairnError("handoff root does not match the current project root")
    if state.get("writer", "").casefold() == agent.casefold():
        raise CairnError("reader must be a different agent from the writer")

    reader = {
        "agent": agent,
        "read_at": datetime.now(timezone.utc).isoformat(),
    }
    readers = state.setdefault("readers", [])
    if not isinstance(readers, list):
        raise CairnError("handoff readers field is invalid")
    readers.append(reader)
    _write_json_atomic(state_path, state)

    return {
        "ok": True,
        "code": state.get("code"),
        "root": str(root),
        "writer": state.get("writer"),
        "reader": agent,
    }


def handoff_clean(path: str) -> bool:
    state_path = _root(path) / HANDOFF_PATH
    if not state_path.exists():
        return False
    state_path.unlink()
    return True


def _print_validation(result: Dict[str, Any]) -> None:
    label = "PASS" if result["ok"] else "FAIL"
    print(f"{label} {result['root']}")
    for error in result["errors"]:
        print(f"error: {error}")
    for warning in result["warnings"]:
        print(f"warning: {warning}")
    print(f"topics: {result['topic_count']}")


def _print_status(result: Dict[str, Any]) -> None:
    print(result["root"])
    print("\nRecent changes:")
    if result["entries"]:
        for entry in result["entries"]:
            print(f"- {entry['title']}")
    else:
        print("- none")
    print("\nTopics:")
    if result["topics"]:
        for topic in result["topics"]:
            print(
                f"- {topic['status']}: {topic['file']} "
                f"(updated {topic['updated']})"
            )
    else:
        print("- none")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cairn",
        description="Portable project context for handoffs across AI agents.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    init_parser = commands.add_parser(
        "init", help="initialize Cairn Lite without overwriting existing files"
    )
    init_parser.add_argument("path", nargs="?", default=".")
    init_parser.add_argument("--dry-run", action="store_true")

    validate_parser = commands.add_parser(
        "validate", help="validate the Cairn Lite structure"
    )
    validate_parser.add_argument("path", nargs="?", default=".")
    validate_parser.add_argument("--json", action="store_true")

    status_parser = commands.add_parser(
        "status", help="show recent changes and topic states"
    )
    status_parser.add_argument("path", nargs="?", default=".")
    status_parser.add_argument("--json", action="store_true")

    test_parser = commands.add_parser(
        "test", help="run a blind cross-agent filesystem handoff test"
    )
    test_commands = test_parser.add_subparsers(dest="test_command", required=True)

    write_parser = test_commands.add_parser(
        "write", help="write a hidden six-digit challenge"
    )
    write_parser.add_argument("path", nargs="?", default=".")
    write_parser.add_argument("--agent", required=True)
    write_parser.add_argument("--replace", action="store_true")

    read_parser = test_commands.add_parser(
        "read", help="read a challenge written by another agent"
    )
    read_parser.add_argument("path", nargs="?", default=".")
    read_parser.add_argument("--agent", required=True)

    clean_parser = test_commands.add_parser(
        "clean", help="remove the temporary handoff challenge"
    )
    clean_parser.add_argument("path", nargs="?", default=".")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            actions = init_project(args.path, args.dry_run)
            if args.dry_run:
                print("Dry run:")
            for action in actions:
                print(action)
            return 0

        if args.command == "validate":
            result = validate_project(args.path)
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                _print_validation(result)
            return 0 if result["ok"] else 1

        if args.command == "status":
            result = status_project(args.path)
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                _print_status(result)
            return 0

        if args.test_command == "write":
            result = handoff_write(args.path, args.agent, args.replace)
            print(result["message"])
            print(f"writer: {result['writer']}")
            print(f"root: {result['root']}")
            return 0

        if args.test_command == "read":
            result = handoff_read(args.path, args.agent)
            print("PASS cross-agent handoff")
            print(f"code: {result['code']}")
            print(f"writer: {result['writer']}")
            print(f"reader: {result['reader']}")
            print(f"root: {result['root']}")
            return 0

        if args.test_command == "clean":
            removed = handoff_clean(args.path)
            print("removed" if removed else "nothing to remove")
            return 0
    except CairnError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 2


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
