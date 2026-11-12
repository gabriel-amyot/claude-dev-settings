"""Validated local writes for the shared harness catalog.

The helper is the supported write interface. Producer labels are attribution and
policy, not an authentication boundary against arbitrary local file access.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid
from collections.abc import Mapping


class ValidationError(ValueError):
    """The supplied record does not satisfy its domain contract."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def stable_id(*parts) -> str:
    value = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


HOSTS = {"claude", "codex", "shared", "unknown"}
FIELDS = {
    "capability": ("capabilities", ("id",),
        "id kind name description source_path revision discovered_at", {"group_name": "ungrouped", "active": True}),
    "availability": ("availability", ("capability_id", "host", "role", "path"),
        "capability_id host role path status observed_at evidence", {}),
    "dependency": ("dependencies", ("capability_id", "target_id", "relationship"),
        "capability_id target_id relationship evidence", {}),
    "usage": ("usage_events", ("id",),
        "id capability_id host role session_id occurred_at signal source_path source_ref",
        {"revision": None, "outcome": "unknown", "count": 1}),
    "friction": ("frictions", ("id",),
        "id capability_id host role session_id occurred_at summary impact evidence",
        {"status": "open", "resolves_id": None}),
    "eval_suite": ("eval_suites", ("id",),
        "id suite_id capability_id layer source_path observed_at", {"runner": None, "last_green": None}),
    "eval": ("eval_runs", ("id",),
        "id suite_id capability_id occurred_at outcome source_path source_ref",
        {"revision": None, "host": "unknown", "layer": "unknown", "summary": None}),
    "outcome": ("outcomes", ("id",),
        "id capability_id occurred_at status source_path source_ref",
        {"host": "unknown", "role": "unknown", "revision": None, "summary": None}),
    "decision": ("decisions", ("id",),
        "id capability_id occurred_at action status rationale authority evidence", {}),
    "coverage": ("coverage", ("id",),
        "id source host scope observed_at status detail", {"since": None, "until": None}),
    "artifact": ("artifacts", ("id",),
        "id kind source_path fingerprint observed_at", {"summary": None}),
}
MUTABLE = {"capability", "availability", "dependency", "coverage", "eval_suite"}
ALLOWED = {
    "collector": {"capability", "availability", "dependency", "usage", "outcome", "coverage", "artifact", "eval_suite"},
    "eval-runner": {"eval", "artifact"},
    "agent": {"friction", "decision", "artifact"},
    "maintainer": {"friction", "decision", "artifact"},
}
ENUMS = {
    ("capability", "kind"): {"skill", "agent", "hook", "workflow"},
    ("availability", "status"): {"discovered", "validated", "blocked", "unknown"},
    ("dependency", "relationship"): {"references", "requires", "delegates"},
    ("usage", "signal"): {"invoked", "loaded", "historical_estimate"},
    ("usage", "outcome"): {"unknown", "success", "failure"},
    ("friction", "status"): {"open", "resolved"},
    ("eval", "outcome"): {"pass", "fail", "error", "skipped", "unknown"},
    ("decision", "action"): {"keep", "promote", "polish", "review", "retire", "prioritize", "propose"},
    ("decision", "status"): {"proposed", "approved"},
    ("coverage", "status"): {"complete", "partial", "unavailable"},
}
TIMESTAMPS = {"occurred_at", "observed_at", "discovered_at", "since", "until", "last_green"}


def _timestamp(value: str, field: str) -> None:
    try:
        if len(value) == 10:
            dt.date.fromisoformat(value)
        else:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("timezone required")
    except ValueError as exc:
        raise ValidationError(f"{field} must be an ISO date or timezone-aware datetime") from exc


def _validated(kind: str, payload, producer: str) -> dict:
    if kind not in FIELDS:
        raise ValidationError(f"Unknown record kind: {kind!r}")
    if producer not in ALLOWED or kind not in ALLOWED[producer]:
        raise PermissionError(f"Producer {producer!r} cannot write {kind!r}")
    if not isinstance(payload, Mapping):
        raise ValidationError("Record payload must be an object")
    _, _, required_text, defaults = FIELDS[kind]
    required = set(required_text.split())
    unknown = set(payload) - required - set(defaults)
    missing = required - set(payload)
    if unknown or missing:
        raise ValidationError(f"Invalid {kind} fields; unknown={sorted(unknown)}, missing={sorted(missing)}")
    record = {**defaults, **payload}
    for field, default in defaults.items():
        if record[field] is None and default is not None:
            record[field] = default
    for field, value in record.items():
        if field == "active":
            if type(value) is not bool:
                raise ValidationError("active must be a boolean")
            record[field] = int(value)
            continue
        if field == "count":
            if type(value) is not int or value <= 0:
                raise ValidationError("count must be a positive integer")
            continue
        if value is None:
            if field in required:
                raise ValidationError(f"{field} cannot be null")
            continue
        if not isinstance(value, str):
            raise ValidationError(f"{field} must be a string")
        if not value.strip() and field != "description":
            raise ValidationError(f"{field} cannot be empty")
        if field in TIMESTAMPS:
            _timestamp(value, field)
        allowed = HOSTS if field == "host" else ENUMS.get((kind, field))
        if allowed is not None and value not in allowed:
            raise ValidationError(f"Invalid {kind}.{field}: {value!r}")
    if kind == "decision":
        expected = "proposed" if producer == "agent" else "approved"
        if record["status"] != expected:
            raise PermissionError(f"{producer} decisions must have status {expected}")
    if kind == "friction":
        if producer == "agent" and (record["status"] != "open" or record["resolves_id"] is not None):
            raise PermissionError("Agents can report open friction, not resolve it")
        if producer == "maintainer" and (record["status"] != "resolved" or not record["resolves_id"]):
            raise PermissionError("Maintainer friction records must identify the resolved observation")
        if record.get("resolves_id") == record["id"]:
            raise ValidationError("A friction cannot resolve itself")
    record["producer"] = producer
    return record


class Store:
    """One local connection; each record is an atomic transaction."""

    def __init__(self, db_path, backup_before_write=True):
        self.path = str(db_path)
        existed = self.path != ":memory:" and Path(self.path).is_file()
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA busy_timeout = 15000")
        try:
            version = self.conn.execute("PRAGMA user_version").fetchone()[0]
            if version > 1:
                raise ValidationError(f"Unsupported future schema version {version}")
            self.conn.execute("PRAGMA journal_mode = WAL")
            schema = (Path(__file__).parent / "schema" / "001.sql").read_text()
            self.conn.executescript("BEGIN IMMEDIATE;\n" + schema + "\nCOMMIT;")
            self._snapshot_needed = bool(backup_before_write and existed and any(
                self.conn.execute(f'SELECT EXISTS(SELECT 1 FROM "{table}")').fetchone()[0]
                for table, *_ in FIELDS.values()
            ))
        except BaseException:
            self.conn.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self.conn.close()

    def record(self, kind: str, payload, producer: str = "agent") -> bool:
        record = _validated(kind, payload, producer)
        table, keys, _, _ = FIELDS[kind]
        condition = " AND ".join(f'"{key}" = ?' for key in keys)
        key_values = [record[key] for key in keys]
        # Snapshot a committed state through SQLite, never copy a live WAL file.
        # A no-change replay should not create another backup.
        before = self.conn.execute(f'SELECT * FROM "{table}" WHERE {condition}', key_values).fetchone()
        if self._snapshot_needed and (before is None or dict(before) != record):
            self._backup_before_mutation()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            existing = self.conn.execute(f'SELECT * FROM "{table}" WHERE {condition}', key_values).fetchone()
            if existing is not None:
                if dict(existing) == record:
                    self.conn.execute("COMMIT")
                    return False
                if kind not in MUTABLE:
                    raise ValidationError(f"Conflicting immutable {kind} record: {key_values!r}")
            if kind == "friction" and record["resolves_id"]:
                original = self.conn.execute("SELECT capability_id,status FROM frictions WHERE id = ?", (record["resolves_id"],)).fetchone()
                if original is None or original["status"] != "open" or original["capability_id"] != record["capability_id"]:
                    raise ValidationError("Resolution must reference an open observation for the same capability")
            columns = list(record)
            names = ",".join(f'"{name}"' for name in columns)
            values = [record[name] for name in columns]
            placeholders = ",".join("?" for _ in columns)
            if existing is None:
                self.conn.execute(f'INSERT INTO "{table}" ({names}) VALUES ({placeholders})', values)
            else:
                updates = ",".join(f'"{name}" = ?' for name in columns if name not in keys)
                changed = [record[name] for name in columns if name not in keys]
                self.conn.execute(f'UPDATE "{table}" SET {updates} WHERE {condition}', changed + key_values)
            self.conn.execute("COMMIT")
            return True
        except sqlite3.IntegrityError as exc:
            self.conn.execute("ROLLBACK")
            raise ValidationError(str(exc)) from exc
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise

    def _backup_before_mutation(self):
        if not self._snapshot_needed:
            return
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        destination = Path(self.path).parent / "backups" / f"{Path(self.path).stem}-{stamp}-{uuid.uuid4().hex[:8]}.sqlite"
        self.backup(destination)
        self._snapshot_needed = False

    def replace_references(self, capability_id, targets, producer="collector"):
        """Atomically replace one source's current static reference metadata."""
        if producer != "collector":
            raise PermissionError("Only the collector can replace reference metadata")
        if not isinstance(capability_id, str) or not capability_id:
            raise ValidationError("capability_id must be a nonempty string")
        source = self.conn.execute("SELECT active FROM capabilities WHERE id=?", (capability_id,)).fetchone()
        if source is None:
            raise ValidationError("Reference source capability does not exist")
        desired = []
        for target in targets:
            if not isinstance(target, Mapping) or set(target) != {"target_id", "evidence"}:
                raise ValidationError("Reference targets require only target_id and evidence")
            desired.append(_validated("dependency", {"capability_id": capability_id,
                "target_id": target["target_id"], "relationship": "references",
                "evidence": target["evidence"]}, producer))
        if not source["active"]:
            desired = []
        desired = sorted({(row["target_id"], row["evidence"]): row for row in desired}.values(), key=lambda row: row["target_id"])
        old = [dict(row) for row in self.conn.execute("SELECT * FROM dependencies WHERE capability_id=? AND relationship='references' ORDER BY target_id", (capability_id,))]
        if old == desired:
            return 0
        self._backup_before_mutation()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            self.conn.execute("DELETE FROM dependencies WHERE capability_id=? AND relationship='references'", (capability_id,))
            self.conn.executemany("INSERT INTO dependencies(capability_id,target_id,relationship,evidence,producer) VALUES(?,?,?,?,?)", [tuple(row[key] for key in ["capability_id", "target_id", "relationship", "evidence", "producer"]) for row in desired])
            self.conn.execute("COMMIT")
            return len(old) + len(desired)
        except sqlite3.IntegrityError as exc:
            self.conn.execute("ROLLBACK")
            raise ValidationError(str(exc)) from exc
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise

    def clear_inactive_dependencies(self):
        """Drop current edges owned by absent sources, preserving every history table."""
        count = self.conn.execute("SELECT count(*) FROM dependencies WHERE capability_id IN (SELECT id FROM capabilities WHERE active=0)").fetchone()[0]
        if not count:
            return 0
        self._backup_before_mutation()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            self.conn.execute("DELETE FROM dependencies WHERE capability_id IN (SELECT id FROM capabilities WHERE active=0)")
            self.conn.execute("COMMIT")
            return count
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise

    def rows(self, sql: str, parameters=()) -> list[dict]:
        allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}

        def authorize(action, *_):
            return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY

        self.conn.set_authorizer(authorize)
        try:
            return [dict(row) for row in self.conn.execute(sql, parameters).fetchall()]
        except sqlite3.DatabaseError as exc:
            raise ValidationError(f"Read-only query rejected: {exc}") from exc
        finally:
            # Python before 3.11 cannot reliably disable the callback with None.
            self.conn.set_authorizer(lambda *_: sqlite3.SQLITE_OK)

    def backup(self, path):
        destination = Path(path)
        if self.path != ":memory:" and destination.resolve() == Path(self.path).resolve():
            raise ValidationError("Backup destination cannot be the active database")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(destination) as target:
            self.conn.backup(target)
