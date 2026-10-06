from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import __version__
from .templates import (
    AGENTS_BLOCK,
    CONFIG,
    END_MARKER,
    HANDOFF_HEADINGS,
    HANDOFF_STATUSES,
    HANDOFF_TEMPLATE,
    PROTOCOL,
    START_MARKER,
)


CONFIG_PATH = Path(".cairn/config.json")
PROTOCOL_PATH = Path(".cairn/PROTOCOL.md")
HANDOFF_PATH = Path(".cairn/handoff-test.json")
HANDOFFS_PATH = Path("cairn/handoffs")
HANDOFFS_IGNORE = "cairn/handoffs/"
HANDOFF_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
CONFIG_VERSIONS = (1, 2)


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


def _ensure_gitignore(path: Path, dry_run: bool) -> str:
    if not path.exists():
        return _write_new(path, HANDOFFS_IGNORE + "\n", dry_run)

    text = path.read_text(encoding="utf-8")
    if any(line.strip() == HANDOFFS_IGNORE for line in text.splitlines()):
        return f"skip   {path}"

    if not dry_run:
        separator = "" if not text or text.endswith("\n") else "\n"
        path.write_text(text + separator + HANDOFFS_IGNORE + "\n", encoding="utf-8")
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
        _ensure_agents(root / "AGENTS.md", dry_run),
        _ensure_claude(root / "CLAUDE.md", dry_run),
        _ensure_gitignore(root / ".gitignore", dry_run),
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


def _sections(text: str) -> Dict[str, str]:
    matches = list(re.finditer(r"(?m)^## (.+)$", text))
    result: Dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = re.sub(r"<!--.*?-->", "", text[match.end() : end], flags=re.S)
        result[match.group(1).strip()] = body.strip()
    return result


def _handoff_files(root: Path) -> List[Path]:
    directory = root / HANDOFFS_PATH
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.md"))


def _read_handoff(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    metadata = _frontmatter(text)
    sections = _sections(text)
    questions = sections.get("Questions", "")
    return {
        "id": metadata.get("handoff", path.stem),
        "status": metadata.get("status", "unknown"),
        "from": metadata.get("from", "unknown"),
        "to": metadata.get("to", "unknown"),
        "planner_url": metadata.get("planner_url") or None,
        "open_questions": len(re.findall(r"(?m)^\s*- \[ \]", questions)),
        "metadata": metadata,
        "sections": sections,
    }


def _check_handoff(root: Path, path: Path) -> List[str]:
    name = str(path.relative_to(root))
    handoff = _read_handoff(path)
    metadata, sections = handoff["metadata"], handoff["sections"]
    status = handoff["status"]
    errors = []

    if metadata.get("handoff") != path.stem:
        errors.append(f"{name}: `handoff` must match the file name")
    if status not in HANDOFF_STATUSES:
        errors.append(f"{name} has invalid or missing status")
    for key in ("from", "to"):
        if not metadata.get(key):
            errors.append(f"{name} is missing `{key}`")
    planner_url = metadata.get("planner_url")
    if planner_url and not planner_url.startswith("https://"):
        errors.append(f"{name}: `planner_url` must start with https://")
    for heading in HANDOFF_HEADINGS:
        if heading not in sections:
            errors.append(f"{name} is missing `## {heading}`")

    if status not in ("open", "cancelled") and not sections.get("Readback"):
        errors.append(f"{name} is {status} but has no Readback")
    if status == "blocked" and not handoff["open_questions"]:
        errors.append(f"{name} is blocked but has no open question")
    if status in ("running", "done") and handoff["open_questions"]:
        errors.append(
            f"{name} has open questions; set status to blocked or answer them"
        )
    if status == "done" and not sections.get("Log"):
        errors.append(f"{name} is done but has no Log entry")
    return errors


def handoff_new(
    path: str,
    handoff_id: str,
    title: str,
    from_agent: str,
    to_agent: str,
    planner_url: Optional[str] = None,
) -> Path:
    root = _root(path)
    _load_config(root)
    if not HANDOFF_ID.match(handoff_id):
        raise CairnError("handoff id must use lowercase letters, digits, and -")
    if planner_url and not planner_url.startswith("https://"):
        raise CairnError("planner_url must start with https://")
    target = root / HANDOFFS_PATH / f"{handoff_id}.md"
    if target.exists():
        raise CairnError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        HANDOFF_TEMPLATE.format(
            id=handoff_id,
            title=title,
            from_agent=from_agent,
            to_agent=to_agent,
            planner_line=f"planner_url: {planner_url}\n" if planner_url else "",
            date=datetime.now(timezone.utc).date().isoformat(),
        ),
        encoding="utf-8",
    )
    return target


def handoff_status(path: str) -> Dict[str, Any]:
    root = _root(path)
    handoffs = []
    for item in _handoff_files(root):
        handoff = _read_handoff(item)
        handoffs.append(
            {
                "file": str(item.relative_to(root)),
                "id": handoff["id"],
                "status": handoff["status"],
                "from": handoff["from"],
                "to": handoff["to"],
                "planner_url": handoff["planner_url"],
                "open_questions": handoff["open_questions"],
            }
        )
    return {"root": str(root), "handoffs": handoffs}


def validate_project(path: str) -> Dict[str, Any]:
    root = _root(path)
    errors: List[str] = []
    warnings: List[str] = []

    required = (
        PROTOCOL_PATH,
        CONFIG_PATH,
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
            if config.get("version") not in CONFIG_VERSIONS:
                errors.append("config version must be 1 or 2")
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

    handoff_files = _handoff_files(root)
    for item in handoff_files:
        errors.extend(_check_handoff(root, item))
    if handoff_files and config.get("handoffs_in_git") is not True:
        ignored = any(
            ignore.is_file()
            and any(
                line.strip() == HANDOFFS_IGNORE
                for line in ignore.read_text(encoding="utf-8").splitlines()
            )
            for ignore in (root / ".gitignore", root / ".git/info/exclude")
        )
        if not ignored:
            warnings.append(
                f"{HANDOFFS_IGNORE} is not in .gitignore; handoffs may be committed"
            )

    return {
        "ok": not errors,
        "root": str(root),
        "errors": errors,
        "warnings": warnings,
        "handoff_count": len(handoff_files),
    }


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
    print(f"handoffs: {result['handoff_count']}")


def _print_handoffs(result: Dict[str, Any]) -> None:
    if not result["handoffs"]:
        print("No handoffs.")
        return
    for item in result["handoffs"]:
        line = f"- {item['status']}: {item['id']} ({item['from']} -> {item['to']})"
        if item["open_questions"]:
            line += f", {item['open_questions']} open question(s)"
        print(line)
        print(f"  {item['file']}")
        if item["planner_url"]:
            print(f"  planner_url: {item['planner_url']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cairn",
        description="Pass work between AI agents through one shared handoff file.",
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
        "status", help="same as `cairn handoff status`"
    )
    status_parser.add_argument("path", nargs="?", default=".")
    status_parser.add_argument("--json", action="store_true")

    handoff_parser = commands.add_parser(
        "handoff", help="pass work between agents and carry results back"
    )
    handoff_commands = handoff_parser.add_subparsers(
        dest="handoff_command", required=True
    )

    new_parser = handoff_commands.add_parser("new", help="create a handoff")
    new_parser.add_argument("id")
    new_parser.add_argument("--title", required=True)
    new_parser.add_argument("--from", dest="from_agent", required=True)
    new_parser.add_argument("--to", dest="to_agent", required=True)
    new_parser.add_argument(
        "--planner-url", help="https link where the planner can be reached"
    )
    new_parser.add_argument("--path", default=".")

    list_parser = handoff_commands.add_parser(
        "status", help="list handoffs, their status, and open questions"
    )
    list_parser.add_argument("path", nargs="?", default=".")
    list_parser.add_argument("--json", action="store_true")

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
            result = handoff_status(args.path)
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                _print_handoffs(result)
            return 0

        if args.command == "handoff":
            if args.handoff_command == "new":
                target = handoff_new(
                    args.path,
                    args.id,
                    args.title,
                    args.from_agent,
                    args.to_agent,
                    args.planner_url,
                )
                print(f"create {target}")
                return 0
            result = handoff_status(args.path)
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                _print_handoffs(result)
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
