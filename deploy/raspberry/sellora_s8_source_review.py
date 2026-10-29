#!/usr/bin/env python3
"""Prepare a private source-review DRAFT in the native owner's terminal.

No source execution, service queries, upload or release approval is performed.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
from uuid import uuid4

OWNER_UID = 1000
OWNER_HOME = Path("/home/btcradar")
UNIT_DIR = OWNER_HOME / ".config/systemd/user"
SCRIPT_DIR = OWNER_HOME / ".local/bin"
# Exact source locations supplied by the owner. This does not allow directory
# traversal/scanning or neighboring credential, archive or state files.
OBSERVED_SOURCE_PATHS = {
    "sellora-runtime-health-watchdog.service": OWNER_HOME / ".local/lib/sellora/api_watchdog.py",
    "sellora-db-backup.service": OWNER_HOME / "runtime/sellora/protected-backups/backup-sellora.sh",
    "sellora-offhost-encrypted-backup.service": OWNER_HOME / "runtime/sellora/protected-backups/push-to-nexolab.sh",
    "sellora-google-drive-backup.service": OWNER_HOME / "runtime/sellora/protected-backups/upload-to-google-drive.sh",
}
UNIT_NAMES = tuple(prefix + suffix for prefix in (
    "sellora-runtime-health-watchdog", "sellora-db-backup",
    "sellora-offhost-encrypted-backup", "sellora-google-drive-backup",
) for suffix in (".service", ".timer"))
WATCHDOG_HASHES = {
    "sellora-runtime-health-watchdog.service": "100b7f1a7beff35434f8b6b4abdcdbfeea7b89834b8d630cc37f349cee9e2ff7",
    "sellora-runtime-health-watchdog.timer": "50250e27377c9a7c47ebfab2a5aabcc96e169829d94437cdc4dfa399800fa4dc",
}
UNIT_LIMIT, SCRIPT_LIMIT, TOTAL_LIMIT, SCRIPT_COUNT_LIMIT = 16_384, 131_072, 524_288, 16
REDACTION_DETAIL_LIMIT = 128
SOURCE_DIRECTIVES = {"ExecStart", "ExecStartPre", "ExecStartPost"}
SENSITIVE_DIRECTIVE = re.compile(r"environment|credential|password|secret|token|standardinput(?:text|data)", re.I)
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?<![A-Za-z0-9_])[\"']?[A-Za-z0-9_]*(?:password|passwd|secret|token|api_?key|private_?key|access_?key)"
    r"[A-Za-z0-9_]*[\"']?\s*(?::[^=\n]{0,80})?\s*[:=]"
)
SCRIPT_NAME = re.compile(r"sellora[A-Za-z0-9_.-]{0,120}\Z", re.ASCII)
DIRECTIVE = re.compile(r"\s*([A-Za-z][A-Za-z0-9]*)\s*=(.*)\Z")


class ReviewError(Exception):
    """Only fixed codes may be printed."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ReviewError(code)


def directory_fd(path: Path) -> int:
    require(path.is_absolute() and ".." not in path.parts, "unsafe_source_path")
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def read_source(path: Path, limit: int) -> tuple[str, dict]:
    require(path.parent == UNIT_DIR and path.name in UNIT_NAMES or script_token(str(path)) is not None,
            "source_path_not_allowed")
    parent = directory_fd(path.parent)
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, "rb") as source:
            before = os.fstat(source.fileno())
            require(stat.S_ISREG(before.st_mode), "source_not_regular")
            require(before.st_size <= limit, "source_too_large")
            raw = source.read(limit + 1)
            after = os.fstat(source.fileno())
            require(len(raw) <= limit, "source_too_large")
            require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                    (after.st_size, after.st_mtime_ns, after.st_ctime_ns), "source_changed_during_read")
    finally:
        os.close(parent)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ReviewError("source_not_text") from None
    require(not any(ord(char) < 32 and char not in "\n\r\t" or ord(char) == 127 for char in text), "source_not_text")
    return text, {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                  "mode": f"{stat.S_IMODE(before.st_mode):04o}", "uid": before.st_uid, "gid": before.st_gid}


def script_token(token: str) -> Path | None:
    path = Path(token)
    if path in OBSERVED_SOURCE_PATHS.values():
        return path
    if not path.is_absolute() or path.parent != SCRIPT_DIR or SCRIPT_NAME.fullmatch(path.name) is None:
        return None
    return path if path.suffix in {".py", ".sh", ""} else None


def observed_references(value: str) -> tuple[set[Path], bool]:
    """Lex quoted wrapper text only; never expand/evaluate a shell expression."""
    pending, references, budget, complete = [(value, 0)], set(), 128, True
    while pending:
        expression, depth = pending.pop()
        lexer = shlex.shlex(expression, posix=True, punctuation_chars=True)
        lexer.whitespace_split, lexer.commenters = True, ""
        try:
            for token in lexer:
                budget -= 1
                if budget < 0:
                    return references, False
                path = Path(token)
                if path in OBSERVED_SOURCE_PATHS.values():
                    references.add(path)
                if token != expression and any(char.isspace() or char in "\"'();<>|&" for char in token):
                    if depth < 2:
                        pending.append((token, depth + 1))
                    else:
                        complete = False
        except ValueError:
            complete = False
    return references, complete


def unit_copy(text: str) -> tuple[str, set[Path], list[dict], list[dict]]:
    lines, scripts, redactions, unresolved = text.splitlines(), set(), [], []
    index = 0
    while index < len(lines):
        start = index
        match = DIRECTIVE.fullmatch(lines[index])
        index += 1
        if not match:
            continue
        key, value = match.groups()
        continued = value.rstrip().endswith("\\")
        while continued and index < len(lines):
            value += "\n" + lines[index]
            continued = lines[index].rstrip().endswith("\\")
            index += 1
        redact = SENSITIVE_DIRECTIVE.search(key) is not None
        if key in SOURCE_DIRECTIVES:
            try:
                tokens = shlex.split(value) if index == start + 1 else []
            except ValueError:
                tokens = []
            references = {path for token in tokens if (path := script_token(token)) is not None}
            observed, complete = observed_references(value)
            references.update(observed)
            if not complete:
                unresolved.append({"line": start + 1, "code": "lexical_source_discovery_incomplete"})
            scripts.update(references)
            supported = len(tokens) == 1 and script_token(tokens[0]) is not None
            supported |= (len(tokens) in {2, 3} and tokens[0] in {"/usr/bin/python3", "/usr/bin/python"}
                          and script_token(tokens[-1]) is not None and (len(tokens) == 2 or tokens[1] == "-u"))
            supported |= (len(tokens) == 2 and tokens[0] in {"/bin/bash", "/usr/bin/bash", "/bin/sh", "/usr/bin/sh"}
                          and script_token(tokens[1]) is not None)
            if not supported:
                redact = True
                unresolved.append({"line": start + 1, "code": "unsupported_invocation"})
        elif key.startswith("Exec"):
            redact = True
            unresolved.append({"line": start + 1, "code": "other_exec_directive_not_collected"})
        if redact:
            redactions.append({"line": start + 1, "end_line": index, "directive": key})
            lines[start] = key + "=[REDACTED; OWNER REVIEW REQUIRED]"
            for offset in range(start + 1, index):
                lines[offset] = "# [REDACTED CONTINUATION]"
    return "\n".join(lines), scripts, redactions, unresolved


def script_copy(text: str) -> tuple[str, list[dict]]:
    lines, redactions, redact_remaining = [], [], False
    for number, line in enumerate(text.splitlines(), 1):
        suspicious = SECRET_ASSIGNMENT.search(line) is not None or "PRIVATE KEY-----" in line
        if suspicious:
            # Ambiguous multiline literals cannot be safely bounded by a simple
            # assignment matcher. Omit the remainder rather than expose it.
            redact_remaining |= ("\"\"\"" in line or "'''" in line or line.endswith("\\") or "<<" in line
                                 or "PRIVATE KEY-----" in line or any(line.count(quote) % 2 for quote in ("'", '"')))
        if suspicious or redact_remaining:
            lines.append("# [REDACTED possible inline credential; original line " + str(number) + "]")
            redactions.append({"line": number, "reason": "possible_inline_credential"})
        else:
            lines.append(line)
    return "\n".join(lines), redactions


def prepare() -> dict:
    require(os.getuid() == OWNER_UID and os.isatty(0), "native_owner_terminal_required")
    files, sections, scripts, unresolved, total = [], [], set(), [], 0

    def collect(path: Path, limit: int, kind: str) -> None:
        nonlocal total
        try:
            text, metadata = read_source(path, limit)
            if path.name in WATCHDOG_HASHES:
                require(metadata["sha256"] == WATCHDOG_HASHES[path.name], "watchdog_source_changed")
            total += metadata["bytes"]
            require(total <= TOTAL_LIMIT, "source_total_limit")
            if kind == "script" and path.suffix == "":
                first = text.splitlines()[0] if text.splitlines() else ""
                require(first in {"#!/usr/bin/python3", "#!/usr/bin/env python3", "#!/bin/sh", "#!/bin/bash",
                                  "#!/usr/bin/bash", "#!/usr/bin/env bash", "#!/usr/bin/env sh"}, "unsupported_script_shebang")
            if kind == "unit":
                copy, references, redactions, issues = unit_copy(text)
                scripts.update(references)
                unresolved.extend(dict(issue, path=str(path)) for issue in issues)
                expected = OBSERVED_SOURCE_PATHS.get(path.name)
                if expected is not None and expected not in references:
                    unresolved.append({"unit": path.name, "path": str(expected), "code": "observed_source_reference_not_found"})
                if path.suffix == ".service" and not references:
                    unresolved.append({"path": str(path), "code": "no_eligible_direct_script_reference"})
            else:
                copy, redactions = script_copy(text)
            metadata.update(kind=kind, redactions=redactions[:REDACTION_DETAIL_LIMIT], redaction_count=len(redactions),
                            redactions_truncated=len(redactions) > REDACTION_DETAIL_LIMIT)
            files.append(metadata)
            sections.append("## " + str(path) + "\n\nOriginal SHA-256: `" + metadata["sha256"] +
                            "`\n\n" + "\n".join("    " + line for line in copy.splitlines()) + "\n")
        except (ReviewError, OSError) as exc:
            if isinstance(exc, ReviewError):
                code = str(exc)
            else:
                code = "source_missing" if exc.errno == errno.ENOENT else "source_unavailable_or_unsafe"
            if path.name in WATCHDOG_HASHES or code == "source_total_limit":
                raise ReviewError(code) from None
            unresolved.append({"path": str(path), "code": code})

    for name in UNIT_NAMES:
        collect(UNIT_DIR / name, UNIT_LIMIT, "unit")
    require(len(scripts) <= SCRIPT_COUNT_LIMIT, "source_count_limit")
    for path in sorted(scripts):
        collect(path, SCRIPT_LIMIT, "script")
    collected = {Path(item["path"]) for item in files if item["kind"] == "script"}
    for unit, path in OBSERVED_SOURCE_PATHS.items():
        if path not in collected:
            unresolved.append({"unit": unit, "path": str(path), "code": "observed_source_not_collected"})
    summary = {"units_collected": sum(item["kind"] == "unit" for item in files), "scripts_collected": len(collected),
               "observed_sources_expected": len(OBSERVED_SOURCE_PATHS),
               "observed_sources_collected": sum(path in collected for path in OBSERVED_SOURCE_PATHS.values())}
    unresolved.append({"code": "transitive_dependencies_not_collected"})
    unresolved.append({"code": "dropins_environment_credentials_state_logs_and_backup_data_not_collected"})
    header = ("# Sellora source review — OWNER REVIEW DRAFT\n\n"
              "Review and edit this exact file locally BEFORE attaching it in chat. It may still contain inline secrets. "
              "Remove credentials before attachment and identify every redaction. Automatic redaction is conservative, "
              "not comprehensive sanitization. Redactions affecting lock, commands, encryption or restore behavior "
              "leave the corresponding release gate unresolved.\n\n"
              "Only eight fixed user-unit files and eligible script references are collected. "
              "Four owner-observed source paths are explicitly allowlisted, not their directories. "
              "Transitive dependencies and drop-ins are not collected. No source is executed; no source or backup "
              "mechanism is approved by this draft. Original hashes identify original bytes, not the edited copies.\n\n"
              "## Collection metadata and omissions\n\n" +
              "\n".join("    " + line for line in json.dumps(
                  {"collection_summary": summary, "files": files, "unresolved_dependencies": unresolved},
                  ensure_ascii=False, indent=2).splitlines()) + "\n\n")
    draft = (header + "\n".join(sections)).encode("utf-8")
    require(len(draft) <= TOTAL_LIMIT * 3, "draft_size_limit")
    home = directory_fd(OWNER_HOME)
    name = "sellora-s8-source-review-" + uuid4().hex
    try:
        os.mkdir(name, mode=0o700, dir_fd=home)
        folder = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=home)
        try:
            descriptor = os.open("review.md", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=folder)
            try:
                with os.fdopen(descriptor, "wb") as target:
                    target.write(draft)
                    target.flush()
                    os.fsync(target.fileno())
            except BaseException:
                try:
                    os.unlink("review.md", dir_fd=folder)
                except FileNotFoundError:
                    pass
                raise
        finally:
            os.close(folder)
    finally:
        os.close(home)
    return {"result": "SOURCE_REVIEW_DRAFT", "artifact_path": str(OWNER_HOME / name / "review.md"),
            "review_required": True, "collection_summary": summary, "files": files, "unresolved_dependencies": unresolved}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", required=True)
    parser.parse_args(argv)
    try:
        result = prepare()
    except KeyboardInterrupt:
        result = {"result": "FAILED", "check": "interrupted"}
    except ReviewError as exc:
        result = {"result": "FAILED", "check": str(exc)}
    except Exception:
        result = {"result": "FAILED", "check": "source_review_failed"}
    print(json.dumps(result))
    return 1 if result["result"] == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
