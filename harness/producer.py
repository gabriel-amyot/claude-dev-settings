"""Publish references/results after existing producers write their own artifacts.

A telemetry failure must never change an eval or report producer's exit status.
Failed deliveries are retained in a bounded local spool for explicit retry.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timezone

KINDS = {"usage-scan", "reference-scan", "tax-scan", "eval-sweep", "factory-telemetry", "crawl-scorecard"}
MAX_PENDING = 100
MAX_BYTES = 512 * 1024


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _root(root=None):
    return Path(root or os.environ.get("HARNESS_ROOT") or Path.home() / ".claude-shared-config").expanduser().resolve()


def _load_store(root):
    path = root / "harness" / "store.py"
    spec = importlib.util.spec_from_file_location("harness_producer_store", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("shared harness store is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fingerprint(source):
    if source.is_file():
        return hashlib.sha256(source.read_bytes()).hexdigest()
    if source.is_dir():
        h = hashlib.sha256()
        for p in sorted(source.glob("run-*.yaml")):
            h.update(p.name.encode())
            h.update(p.read_bytes())
        return h.hexdigest()
    raise FileNotFoundError(str(source))


def _capability(store, module, root, owner):
    rows = store.rows("SELECT id FROM capabilities WHERE name=? ORDER BY id", (owner,))
    if len(rows) == 1:
        return rows[0]["id"]
    source = root / "skills" / owner / "SKILL.md"
    path = str(source.resolve()) if source.is_file() else "unresolved://" + owner
    identity = path if source.is_file() else "owner:" + owner
    capability_id = module.stable_id("capability", identity)
    if store.rows("SELECT id FROM capabilities WHERE id=?", (capability_id,)):
        return capability_id
    # Do not manufacture a compatibility or current-version assertion.
    store.record("capability", {"id": capability_id, "kind": "skill", "name": owner,
        "description": "Producer-referenced capability; inventory details pending.",
        "source_path": path, "revision": "unknown", "discovered_at": _now(), "active": source.is_file()}, producer="collector")
    return capability_id


def _eval_source_ref(source, record):
    """Bind typed results to the exact report assertion understood by legacy import.

    New sweeps supply line+heading hash. A legacy caller can be matched only when
    its date/suite/verdict identifies one assertion; ambiguous matches are rejected.
    """
    supplied = record.get("source_ref")
    lines = Path(source).read_text(errors="replace").splitlines()
    exact = re.fullmatch(r"line:(\d+); assertion_sha256:([a-f0-9]{64})", supplied or "")
    if exact:
        index = int(exact.group(1)) - 1
        if index < 0 or index >= len(lines) or hashlib.sha256(lines[index].encode()).hexdigest() != exact.group(2):
            raise ValueError("eval assertion reference does not match original report")
        assertion = re.match(r"^## (PASS|FAIL)\s*[—-]\s*(.+?)\s*\(exit\s+([^)]*)\)", lines[index])
        if not assertion:
            raise ValueError("eval reference does not identify a supported result assertion")
        verdict, target, code = assertion.groups()
        outcome = "pass" if verdict == "PASS" else ("error" if code == "timeout" else "fail")
        if target != record["suite_id"] or outcome != record["outcome"]:
            raise ValueError("typed eval result contradicts its source assertion")
        return supplied
    candidates = []
    has_assertions = False
    occurred = None
    for lineno, line in enumerate(lines, 1):
        stamp = re.search(r"Layer A sweep\s*[—-]\s*(\d{4}-\d{2}-\d{2})", line)
        if stamp:
            occurred = stamp.group(1)
        match = re.match(r"^## (PASS|FAIL)\s*[—-]\s*(.+?)\s*\(exit\s+([^)]*)\)", line)
        if not match or not occurred:
            continue
        has_assertions = True
        verdict, target, code = match.groups()
        outcome = "pass" if verdict == "PASS" else ("error" if code == "timeout" else "fail")
        if target == record["suite_id"] and outcome == record["outcome"] and occurred == record["occurred_at"][:10]:
            candidates.append(f"line:{lineno}; assertion_sha256:" + hashlib.sha256(line.encode()).hexdigest())
    if len(candidates) > 1:
        raise ValueError("eval result matches multiple report assertions; supply exact line/hash provenance")
    if has_assertions and not candidates:
        raise ValueError("typed eval result has no matching source assertion")
    return candidates[0] if candidates else (supplied or "event:" + record["occurred_at"] + "/" + record["suite_id"])


def _deliver(envelope, root, db):
    module = _load_store(root)
    with module.Store(db) as store:
        artifact_id = module.stable_id("producer-artifact", envelope["kind"], envelope["source_path"], envelope["fingerprint"])
        if not store.rows("SELECT id FROM artifacts WHERE id=?", (artifact_id,)):
            store.record("artifact", {"id": artifact_id, "kind": envelope["kind"],
                "source_path": envelope["source_path"], "fingerprint": envelope["fingerprint"],
                "observed_at": envelope["observed_at"], "summary": "Original producer artifact; preserved in place."}, producer="collector")
        if envelope["kind"] in {"usage-scan", "factory-telemetry", "reference-scan", "tax-scan"}:
            bridge_path = root / "harness/bridges.py"
            spec = importlib.util.spec_from_file_location("harness_producer_bridges", bridge_path)
            bridge = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = bridge
            # bridges imports the shared store by its ordinary module name.
            sys.modules.setdefault("store", module)
            spec.loader.exec_module(bridge)
            home = Path(os.environ.get("HARNESS_HOME", str(Path.home())))
            registry, _ = bridge.inventory(store, root, home)
            if envelope["kind"] == "usage-scan":
                options = (envelope.get("records") or [{}])[0]
                if set(options) - {"org", "days"}:
                    raise ValueError("unknown usage scan publication options")
                org = options.get("org", "klever")
                days = options.get("days", 90)
                if org not in {"klever", "supervisrai", "personal"} or type(days) is not int or days < 1:
                    raise ValueError("invalid usage scan publication scope")
                bridge.collect_activity(store, registry, home, org=org, days=days)
            elif envelope["kind"] == "factory-telemetry":
                result = bridge.ingest_factories(store, registry, root, org="klever")
                for warning in result.get("warnings", []):
                    print("WARN harness factory bridge: " + warning, file=sys.stderr)
            return
        for index, record in enumerate(envelope.get("records") or []):
            if not isinstance(record, dict):
                raise ValueError("producer record must be an object")
            if envelope["kind"] == "eval-sweep":
                allowed = {"suite_id", "owner_skill", "occurred_at", "outcome", "source_ref", "revision", "host", "layer", "summary", "id"}
                if set(record) - allowed:
                    raise ValueError("unknown eval record fields")
                capability_id = _capability(store, module, root, record.get("owner_skill") or record["suite_id"].split("/")[0])
                when = record["occurred_at"]
                assertion_ref = _eval_source_ref(envelope["source_path"], record)
                existing = store.rows("SELECT id,outcome FROM eval_runs WHERE source_path=? AND source_ref=?", (envelope["source_path"], assertion_ref))
                if existing:
                    if any(row["outcome"] != record["outcome"] for row in existing):
                        raise ValueError("conflicting outcomes for the same report assertion")
                    continue
                payload = {"id": record.get("id") or module.stable_id("eval", envelope["source_path"], when, record["suite_id"], str(index)),
                    "suite_id": record["suite_id"], "capability_id": capability_id, "occurred_at": when,
                    "outcome": record["outcome"], "source_path": envelope["source_path"],
                    "source_ref": assertion_ref, "revision": record.get("revision"),
                    "host": record.get("host", "unknown"), "layer": record.get("layer", "A"),
                    "summary": record.get("summary") or "Original eval result; details in source artifact."}
                store.record("eval", payload, producer="eval-runner")
            elif envelope["kind"] in {"factory-telemetry", "crawl-scorecard"}:
                owner = record.get("owner_skill") or ("dark-factory" if envelope["kind"] == "factory-telemetry" else record.get("crawl_type", "unknown"))
                capability_id = _capability(store, module, root, owner)
                when = record.get("occurred_at") or envelope["observed_at"]
                store.record("outcome", {"id": record.get("id") or module.stable_id("outcome", envelope["source_path"], envelope["fingerprint"], str(index)),
                    "capability_id": capability_id, "occurred_at": when, "status": str(record.get("status") or record.get("exit_reason") or "unknown"),
                    "source_path": envelope["source_path"], "source_ref": str(record.get("source_ref", index)),
                    "host": record.get("host", "unknown"), "role": record.get("role", "unknown"),
                    "revision": record.get("revision"), "summary": str(record.get("summary") or "Original producer outcome; details in source artifact.")}, producer="collector")
            else:
                raise ValueError("this producer publishes artifact references, not typed records")


def _render(db, root):
    if os.environ.get("HARNESS_RENDER", "1") == "0":
        return
    module = _load_store(root)
    sys.modules.setdefault("store", module)
    spec = importlib.util.spec_from_file_location("harness_producer_render", root / "harness/render.py")
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    with module.Store(db) as store:
        renderer.render(store, Path(os.environ.get("HARNESS_VIEW", str(root / "harness/view"))))


def _spool(envelope, root):
    pending = root / "harness" / "data" / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    if len(raw) > MAX_BYTES:
        raise ValueError("delivery exceeds spool size limit; original artifact remains authoritative")
    identity = {key: value for key, value in envelope.items() if key != "observed_at"}
    identity_bytes = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    target = pending / (hashlib.sha256(identity_bytes).hexdigest() + ".json")
    if target.exists():
        return target
    if len(list(pending.glob("*.json"))) >= MAX_PENDING:
        raise RuntimeError("pending-delivery capacity reached; no existing deliveries discarded")
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=pending)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return target


def publish(kind, source_path, records=None, *, root=None, db=None):
    """Return delivery success; never propagate telemetry failures to a producer."""
    shared = None
    source = source_path
    envelope = None
    try:
        shared = _root(root)
        source = Path(source_path).expanduser().resolve()
        if kind not in KINDS:
            raise ValueError("unsupported producer kind")
        envelope = {"kind": kind, "source_path": str(source), "fingerprint": _fingerprint(source),
                    "observed_at": _now(), "records": records or []}
        database = Path(db or os.environ.get("HARNESS_DB") or shared / "harness/data/harness.sqlite")
        _deliver(envelope, shared, database)
        _render(database, shared)
        return True
    except Exception as error:
        print(f"WARN harness publication failed ({kind}): {type(error).__name__}: {error}", file=sys.stderr)
        if envelope is not None:
            try:
                target = _spool(envelope, shared)
                print(f"WARN harness delivery pending: {target}", file=sys.stderr)
            except Exception as spool_error:
                print(f"WARN harness pending delivery could not be saved: {spool_error}; original artifact: {source}", file=sys.stderr)
        return False


def retry_pending(*, root=None, db=None):
    shared = _root(root)
    result = {"delivered": 0, "pending": 0}
    for path in sorted((shared / "harness/data/pending").glob("*.json")):
        try:
            envelope = json.loads(path.read_text())
            if envelope.get("kind") not in KINDS:
                raise ValueError("unsupported pending producer")
            database = Path(db or os.environ.get("HARNESS_DB") or shared / "harness/data/harness.sqlite")
            _deliver(envelope, shared, database)
            _render(database, shared)
            path.unlink()
            result["delivered"] += 1
        except Exception as error:
            result["pending"] += 1
            print(f"WARN harness pending delivery retained ({path.name}): {error}", file=sys.stderr)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=sorted(KINDS))
    parser.add_argument("--source")
    parser.add_argument("--records", help="JSON records file")
    parser.add_argument("--retry", action="store_true")
    args = parser.parse_args()
    if args.retry:
        print(json.dumps(retry_pending()))
        return 0
    if not args.kind or not args.source:
        parser.error("--kind and --source are required")
    records = None
    if args.records:
        raw = json.loads(sys.stdin.read() if args.records == "-" else Path(args.records).read_text())
        if args.kind == "crawl-scorecard" and isinstance(raw, dict):
            records = [{"owner_skill": raw.get("crawl_type", "unknown"),
                        "occurred_at": str(raw.get("date", "unknown")),
                        "status": raw.get("exit_reason", "unknown"),
                        "source_ref": "/".join(str(raw.get(k, "unknown")) for k in ("date", "crawl_type", "ticket", "crawl_number")),
                        "summary": "Original crawl scorecard entry; metrics retained in source."}]
        elif isinstance(raw, list):
            records = raw
        else:
            parser.error("--records must contain a JSON array")
    publish(args.kind, args.source, records)
    # The producer's own status remains authoritative, including publication failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
