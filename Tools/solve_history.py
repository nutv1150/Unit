"""Persistent, bounded history for solve/tool operations.

The store deliberately records metadata supplied by callers only.  In
particular, a path in ``files`` is never opened, copied, or removed.
"""

from __future__ import annotations

import html
import json
import os
import re
import sqlite3
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping


CATEGORIES = ("Data Hashing", "File Inspection", "Pipeline")
STATUSES = ("Running", "Success", "Failed")
MAX_TEXT = 16 * 1024
MAX_FILES = 128
MAX_FILES_TOTAL = 16 * 1024
MAX_FILE_TEXT = 4 * 1024
_BYTE_SAMPLE_SIZE = MAX_TEXT
_TRUNCATION_MARKER = " ... [truncated]"
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = (_PROJECT_ROOT / "data" / "solve_history.sqlite3").resolve()

_SENSITIVE_WORDS = frozenset(
    {
        "pass",
        "passwd",
        "password",
        "secret",
        "token",
        "key",
        "apikey",
        "accesskey",
        "privatekey",
    }
)
_SENSITIVE_FLAG_RE = re.compile(
    r"(?i)^[-_]*(?:pass(?:word|wd)?|secret|token|api[-_]?key|access[-_]?key|private[-_]?key|key)(?:[-_].*)?$"
)
_EQUALS_SECRET_RE = re.compile(
    r"(?i)(?P<prefix>(?<![\w-])(?:--?)?(?:pass(?:word|wd)?|secret|token|api[-_]?key|access[-_]?key|private[-_]?key|key)\b\s*=\s*)(?P<value>\"[^\"]*\"|'[^']*'|[^\s,;&]+)"
)
_COLON_SECRET_RE = re.compile(
    r"(?i)(?P<prefix>(?<![\w-])\"?(?:pass(?:word|wd)?|secret|token|api[-_]?key|access[-_]?key|private[-_]?key|key)\"?\s*:\s*)(?P<value>\"[^\"]*\"|'[^']*'|[^\s,;&}]+)"
)
_ARGV_SECRET_RE = re.compile(
    r"(?i)(?P<prefix>(?<![\w-])--?(?:pass(?:word|wd)?|secret|token|api[-_]?key|access[-_]?key|private[-_]?key|key)\b\s+)(?P<value>\"[^\"]*\"|'[^']*'|[^\s,;&]+)"
)


def _is_sensitive_name(value: Any) -> bool:
    if str(value) in ('-k', '-K', '-p'):
        return True
    text = str(value).strip().lstrip("-").replace("-", "_").lower()
    compact = text.replace("_", "")
    return text in _SENSITIVE_WORDS or compact in _SENSITIVE_WORDS or bool(
        _SENSITIVE_FLAG_RE.match(text)
    )


def _redact_text(value: str) -> str:
    """Best-effort masking of common ``key=value`` and JSON-like values."""

    value = _EQUALS_SECRET_RE.sub(r"\g<prefix>[REDACTED]", value)
    value = _COLON_SECRET_RE.sub(r"\g<prefix>[REDACTED]", value)
    value = _ARGV_SECRET_RE.sub(r"\g<prefix>[REDACTED]", value)
    return re.sub(r"(?<!\w)(-[kKp]\s+)(\"[^\"]*\"|'[^']*'|[^\s,;&]+)", r"\1[REDACTED]", value)


def _redact_structure(value: Any) -> Any:
    """Redact sensitive mapping values and values following argv flags."""

    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _is_sensitive_name(key) else _redact_structure(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        result = []
        redact_next = False
        for item in value:
            if redact_next:
                result.append("[REDACTED]")
                redact_next = False
                continue
            if isinstance(item, str) and _is_sensitive_name(item):
                result.append(item)
                redact_next = True
                continue
            result.append(_redact_structure(item))
        return result
    if isinstance(value, (bytes, bytearray, memoryview)):
        return _serialize_bytes(value)
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _limit_text(value: str) -> str:
    if len(value) <= MAX_TEXT:
        return value
    return value[: MAX_TEXT - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER


def _limit_file_text(value: str) -> str:
    if len(value) <= MAX_FILE_TEXT:
        return value
    return value[: MAX_FILE_TEXT - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER


def _serialize_text(value: Any) -> str:
    """Turn caller data into bounded, readable text without opening paths."""

    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return _serialize_bytes(value)
    if isinstance(value, (Mapping, list, tuple)):
        clean = _redact_structure(value)
        try:
            text = json.dumps(clean, ensure_ascii=False, separators=(",", ":"), default=str)
        except (TypeError, ValueError):
            text = str(clean)
    else:
        text = _redact_text(str(value))
    return _limit_text(text)


def _serialize_bytes(value: bytes | bytearray | memoryview) -> str:
    """Render a bounded byte sample as readable UTF-8 or bounded hex.

    The full value is never converted to hex.  This is important for tool
    output that may contain a large byte stream.  Invalid/non-printable UTF-8
    is represented as hex so binary data remains unambiguous.
    """

    total_size = len(value)
    sample = bytes(value[:_BYTE_SAMPLE_SIZE])
    try:
        decoded = sample.decode("utf-8")
        printable = all(character.isprintable() or character in "\r\n\t" for character in decoded)
    except UnicodeDecodeError:
        decoded = ""
        printable = False
    if printable:
        text = _redact_text(decoded)
        if total_size > len(sample):
            text += _TRUNCATION_MARKER
        return _limit_text(text)

    hex_sample_size = max(1, (MAX_TEXT - len("hex:") - len(_TRUNCATION_MARKER)) // 2)
    hex_sample = sample[:hex_sample_size]
    text = "hex:" + hex_sample.hex()
    if total_size > len(hex_sample):
        text += _TRUNCATION_MARKER
    return _limit_text(text)


def _serialize_files(files: Any) -> str:
    if files is None:
        values = []
    elif isinstance(files, (str, os.PathLike, bytes, bytearray, memoryview)):
        values = [files]
    else:
        try:
            values = list(files)
        except TypeError:
            values = [files]
    result = []
    truncated = False
    for index, item in enumerate(values):
        if index >= MAX_FILES - 1:
            truncated = True
            break
        if isinstance(item, (bytes, bytearray, memoryview)):
            text = _serialize_bytes(item)
        else:
            text = str(item)
        result.append(_limit_file_text(text))
        if len(json.dumps(result + (["[truncated]"] if truncated else []), ensure_ascii=False, separators=(",", ":"))) > MAX_FILES_TOTAL:
            result.pop()
            truncated = True
            break
    if truncated:
        result.append("[truncated]")
    serialized = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    if len(serialized) > MAX_FILES_TOTAL:
        # The item limit above normally makes this unnecessary, but retain a
        # valid JSON list even if constants are changed later.
        result = ["[truncated]"]
        serialized = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    return serialized


def _validate_category(category: str) -> str:
    if category == "All":
        return category
    if category not in CATEGORIES:
        raise ValueError(f"Unknown history category: {category!r}")
    return category


def _validate_status(status: str) -> str:
    if status not in STATUSES:
        raise ValueError(f"Unknown history status: {status!r}")
    return status


class SolveHistoryStore:
    """SQLite-backed history with stable begin-order sequence numbers."""

    def __init__(self, path: str | os.PathLike[str] | None = None):
        self.path = ":memory:" if path == ":memory:" else Path(path or DEFAULT_DB_PATH).expanduser().resolve()
        self._lock = threading.RLock()
        self._closed = False
        self._preexisting_files: set[Path] = set()
        if self.path != ":memory:":
            self._preexisting_files = {
                candidate
                for candidate in (
                    self.path,
                    Path(str(self.path) + "-wal"),
                    Path(str(self.path) + "-shm"),
                )
                if candidate.exists()
            }
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connect_path = str(self.path)
        else:
            connect_path = ":memory:"
        self._connection = sqlite3.connect(
            connect_path, timeout=5.0, isolation_level=None, check_same_thread=False
        )
        try:
            self._initialize_database()
        except BaseException:
            self._connection.close()
            self._closed = True
            raise

    def _initialize_database(self) -> None:
        self._connection.execute("PRAGMA busy_timeout = 5000")
        self._connection.execute("PRAGMA foreign_keys = ON")
        if self.path != ":memory:":
            self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS solve_history_meta (
                name TEXT PRIMARY KEY,
                value INTEGER NOT NULL
            );
            INSERT OR IGNORE INTO solve_history_meta(name, value)
                VALUES ('next_seq', 1);
            CREATE TABLE IF NOT EXISTS solve_history_events (
                id TEXT PRIMARY KEY,
                seq INTEGER NOT NULL UNIQUE,
                category TEXT NOT NULL CHECK(category IN ('Data Hashing', 'File Inspection', 'Pipeline')),
                tool TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('Running', 'Success', 'Failed')),
                input TEXT NOT NULL DEFAULT '',
                options TEXT NOT NULL DEFAULT '',
                output TEXT NOT NULL DEFAULT '',
                error TEXT NOT NULL DEFAULT '',
                files TEXT NOT NULL DEFAULT '[]',
                group_id TEXT,
                parent_id TEXT
            );
            CREATE INDEX IF NOT EXISTS solve_history_events_category_seq
                ON solve_history_events(category, seq);
            """
        )
        self._make_new_database_files_private()

    def _make_new_database_files_private(self) -> None:
        """Protect files created by this store without changing user files."""

        if self.path == ":memory:":
            return
        for candidate in (
            self.path,
            Path(str(self.path) + "-wal"),
            Path(str(self.path) + "-shm"),
        ):
            if candidate in self._preexisting_files or not candidate.exists():
                continue
            try:
                os.chmod(candidate, 0o600)
            except OSError:
                pass

    def _ensure_open(self) -> sqlite3.Connection:
        if self._closed:
            raise RuntimeError("SolveHistoryStore is closed")
        return self._connection

    @staticmethod
    def _optional_id(value: Any) -> str | None:
        if value is None:
            return None
        return _limit_text(str(value))

    def begin(
        self,
        category: str,
        tool: str,
        input_data: Any = "",
        options: Any = "",
        group_id: Any = None,
        parent_id: Any = None,
        files: Any = None,
    ) -> str:
        _validate_category(category)
        if category == "All":
            raise ValueError("'All' is a list/clear filter, not an event category")
        connection = self._ensure_open()
        event_id = uuid.uuid4().hex
        with self._lock:
            try:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT value FROM solve_history_meta WHERE name = 'next_seq'"
                ).fetchone()
                seq = int(row[0]) if row else 1
                connection.execute(
                    "INSERT OR REPLACE INTO solve_history_meta(name, value) VALUES ('next_seq', ?)",
                    (seq + 1,),
                )
                connection.execute(
                    """INSERT INTO solve_history_events
                       (id, seq, category, tool, status, input, options, output, error, files, group_id, parent_id)
                       VALUES (?, ?, ?, ?, 'Running', ?, ?, '', '', ?, ?, ?)""",
                    (
                        event_id,
                        seq,
                        category,
                        _serialize_text(tool),
                        _serialize_text(input_data),
                        _serialize_text(options),
                        _serialize_files(files),
                        self._optional_id(group_id),
                        self._optional_id(parent_id),
                    ),
                )
                connection.commit()
                self._make_new_database_files_private()
            except Exception:
                connection.rollback()
                raise
        return event_id

    def finish(
        self,
        event_id: str,
        status: str,
        output_data: Any = "",
        error: Any = "",
        files: Any = None,
    ) -> None:
        _validate_status(status)
        connection = self._ensure_open()
        output_text = _serialize_text(output_data)
        error_text = _serialize_text(error)
        with self._lock:
            try:
                connection.execute("BEGIN IMMEDIATE")
                if files is None:
                    cursor = connection.execute(
                        "UPDATE solve_history_events SET status = ?, output = ?, error = ? WHERE id = ?",
                        (status, output_text, error_text, str(event_id)),
                    )
                else:
                    cursor = connection.execute(
                        "UPDATE solve_history_events SET status = ?, output = ?, error = ?, files = ? WHERE id = ?",
                        (status, output_text, error_text, _serialize_files(files), str(event_id)),
                    )
                if cursor.rowcount != 1:
                    raise KeyError(f"Unknown history event: {event_id!r}")
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    @staticmethod
    def _row_to_event(row: tuple[Any, ...]) -> dict[str, Any]:
        try:
            files = json.loads(row[9]) if row[9] else []
        except (TypeError, ValueError, json.JSONDecodeError):
            files = []
        if not isinstance(files, list):
            files = []
        return {
            "id": row[0],
            "seq": int(row[1]),
            "category": row[2],
            "tool": row[3],
            "status": row[4],
            "input": row[5],
            "options": row[6],
            "output": row[7],
            "error": row[8],
            "files": [str(item) for item in files],
            "group_id": row[10],
            "parent_id": row[11],
        }

    def list_events(self, category: str = "All") -> list[dict[str, Any]]:
        _validate_category(category)
        connection = self._ensure_open()
        query = "SELECT id, seq, category, tool, status, input, options, output, error, files, group_id, parent_id FROM solve_history_events"
        params: tuple[Any, ...] = ()
        if category != "All":
            query += " WHERE category = ?"
            params = (category,)
        query += " ORDER BY seq ASC"
        with self._lock:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_event(row) for row in rows]

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        connection = self._ensure_open()
        with self._lock:
            row = connection.execute(
                "SELECT id, seq, category, tool, status, input, options, output, error, files, group_id, parent_id FROM solve_history_events WHERE id = ?",
                (str(event_id),),
            ).fetchone()
        return self._row_to_event(row) if row else None

    def clear(self, category: str = "All") -> int:
        _validate_category(category)
        connection = self._ensure_open()
        with self._lock:
            try:
                connection.execute("BEGIN IMMEDIATE")
                if category == "All":
                    cursor = connection.execute("DELETE FROM solve_history_events")
                else:
                    cursor = connection.execute(
                        "DELETE FROM solve_history_events WHERE category = ?", (category,)
                    )
                count = cursor.rowcount
                # Restart the visible numbering only when no history remains.
                # UUID record IDs are never reused, so old source links cannot
                # accidentally point to a new record with the same number.
                if connection.execute("SELECT 1 FROM solve_history_events LIMIT 1").fetchone() is None:
                    connection.execute("UPDATE solve_history_meta SET value = 1 WHERE name = 'next_seq'")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return count

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._connection.close()
                self._closed = True

    def __enter__(self) -> "SolveHistoryStore":
        self._ensure_open()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()


def _event_text(event: Mapping[str, Any], key: str) -> str:
    value = event.get(key, "")
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return "" if value is None else str(value)


def export_html(path: str | os.PathLike[str], events: Iterable[Mapping[str, Any]]) -> None:
    """Write a static escaped HTML report atomically with private permissions."""

    destination = Path(path).expanduser().resolve()
    if destination.exists() and destination.is_file():
        try:
            with destination.open("rb") as file_obj:
                if file_obj.read(16) == b"SQLite format 3\x00":
                    raise ValueError("Refusing to overwrite a SQLite database")
        except OSError:
            pass
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = list(events)
    rendered = []
    for event in rows:
        files = event.get("files") or []
        if not isinstance(files, (list, tuple)):
            files = [files]
        file_html = "".join(f"<li><code>{html.escape(str(item), quote=True)}</code></li>" for item in files)
        rendered.append(
            "<article>"
            f"<h2>#{html.escape(_event_text(event, 'seq'), quote=True)} "
            f"{html.escape(_event_text(event, 'tool'), quote=True)}</h2>"
            "<dl>"
            + "".join(
                f"<dt>{label}</dt><dd><code>{html.escape(_event_text(event, key), quote=True)}</code></dd>"
                for label, key in (
                    ("ID", "id"),
                    ("Category", "category"),
                    ("Status", "status"),
                    ("Group", "group_id"),
                    ("Parent", "parent_id"),
                    ("Input", "input"),
                    ("Options", "options"),
                    ("Output", "output"),
                    ("Error", "error"),
                )
            )
            + "</dl><h3>Files</h3><ul>"
            + file_html
            + "</ul></article>"
        )
    document = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>UNIT solve history</title><style>"
        "body{font:14px system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#222}"
        "article{border:1px solid #ccd2d8;border-radius:6px;padding:1rem;margin:1rem 0}"
        "dl{display:grid;grid-template-columns:8rem 1fr;gap:.35rem 1rem}dt{font-weight:600}"
        "dd{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}code{white-space:pre-wrap}"
        "ul{margin-top:.25rem}</style></head><body>"
        f"<h1>UNIT solve history</h1><p>{len(rows)} event(s)</p>"
        + ("".join(rendered) or "<p>No events.</p>")
        + "</body></html>"
    )
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent, prefix=".solve-history-", suffix=".tmp", delete=False
        ) as file_obj:
            temporary_path = file_obj.name
            os.chmod(temporary_path, 0o600)
            file_obj.write(document)
            file_obj.flush()
            os.fsync(file_obj.fileno())
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass


__all__ = ["CATEGORIES", "STATUSES", "MAX_TEXT", "DEFAULT_DB_PATH", "SolveHistoryStore", "export_html"]
