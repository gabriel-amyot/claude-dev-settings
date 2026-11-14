#!/usr/bin/env python3
"""Offline Kev feasibility experiments. Raw packets stay in private local storage."""
from __future__ import annotations

import argparse
import base64
from collections import defaultdict
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import time
import uuid

from local_client import Client
from retrieval import assert_source_unchanged, legacy_rank, lexical_rank, metrics, snapshot_library

HERE = Path(__file__).resolve().parent
BASE = "Qwen/Qwen3.5-4B-Base"
BASE_REVISION = "1001bb4d826a52d1f399e183466143f4da7b741b"


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def protect_output(output, source):
    output, source = Path(output).resolve(), Path(source).resolve()
    if output == source or source in output.parents:
        raise ValueError("experiment output must be outside the source library")


def code_hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(HERE.glob("*.py"))}


def source_checkout(root):
    try:
        head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
        status = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain", "--", "."], stderr=subprocess.DEVNULL)
        return {"head": head, "dirty": bool(status), "status_sha256": hashlib.sha256(status).hexdigest()}
    except (OSError, subprocess.CalledProcessError):
        return {"status": "not-a-readable-git-checkout"}


def observed_server_rss(data):
    try:
        state = json.loads((Path(data) / "server.json").read_text())
        pid = state["pid"]
        if type(pid) is not int or pid <= 1:
            return None
        value = subprocess.check_output(["ps", "-p", str(pid), "-o", "rss="], stderr=subprocess.DEVNULL, text=True).strip()
        return int(value)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError):
        return None


def tokenizer():
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(BASE, revision=BASE_REVISION, local_files_only=True)


def packet(query, document, tok, maximum):
    """Labels, IDs and grading notes never enter this packet."""
    prefix = f"User request:\n{query}\n\nCandidate title:\n{document['title']}\n\nCandidate reference text:\n"
    original = document["text"]
    state = prefix + original
    original_tokens = len(tok.encode(state))
    if original_tokens <= maximum:
        return state, {"state_tokens": original_tokens, "document_prefix_used": False, "omitted_tokens": 0}
    prefix_tokens = len(tok.encode(prefix))
    if prefix_tokens >= maximum - 16:
        raise ValueError("query and title exceed token budget")
    keep = maximum - prefix_tokens - 16
    while keep > 0:
        state = prefix + tok.decode(tok.encode(original)[:keep])
        count = len(tok.encode(state))
        if count <= maximum:
            return state, {"state_tokens": count, "document_prefix_used": True,
                           "omitted_tokens": original_tokens - count}
        keep -= 16
    raise ValueError("cannot fit packet within token budget")


class Run:
    def __init__(self, kind, data, protocol, snapshot, planned):
        protect_output(data, snapshot["root"])
        run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + kind
        self.path = Path(data) / "runs" / run_id
        self.path.mkdir(parents=True, mode=0o700)
        self.protocol, self.snapshot = protocol, snapshot
        self.started = time.monotonic()
        self.meta = {"run_id": run_id, "kind": kind, "started_at": now(), "status": "started",
                     "protocol": protocol, "protocol_sha256": digest(protocol), "code_sha256": code_hashes(),
                     "corpus_manifest_sha256": snapshot["corpus_manifest_sha256"], "planned_requests": planned,
                     "source_checkout": snapshot.get("source_checkout", {"status": "not-recorded"}),
                     "server_rss_kib_before": observed_server_rss(data),
                     "quality_decision": "INSUFFICIENT_EVIDENCE", "production_enabled": False}
        write_json(self.path / "manifest.json", self.meta)
        write_json(self.path / "source-manifest.json", {k: v for k, v in snapshot.items() if k != "documents"})
        print(json.dumps({"run": str(self.path), "status": "started"}), flush=True)

    def append(self, **record):
        with (self.path / "receipts.jsonl").open("a") as stream:
            stream.write(json.dumps({"at": now(), **record}, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def expired(self):
        return time.monotonic() - self.started >= self.protocol["latency"]["maximum_seconds"]

    def request(self, client, state, questions, phase="measured", **context):
        if self.expired():
            return None
        request_id = uuid.uuid4().hex
        payload = {"state": state, "questions": questions}
        self.append(event="attempt", request_id=request_id, phase=phase, payload=payload,
                    payload_sha256=digest(payload), **context)
        start = time.perf_counter()
        try:
            result = client.request(state, questions)
            self.append(event="outcome", request_id=request_id, phase=phase, status="completed",
                        wall_ms=(time.perf_counter()-start)*1000, response=result, **context)
            return result
        except Exception as error:
            self.append(event="outcome", request_id=request_id, phase=phase, status="failed",
                        wall_ms=(time.perf_counter()-start)*1000,
                        error=f"{type(error).__name__}: {error}", fallback_policy="query caller may retain lexical baseline", **context)
            return None

    def finish(self, status="completed", **fields):
        self.meta.update(status=status, finished_at=now(), elapsed_seconds=time.monotonic()-self.started,
                         server_rss_kib_after=observed_server_rss(self.path.parents[1]), **fields)
        write_json(self.path / "manifest.json", self.meta)
        summary = report(self.path)
        self.meta["status"] = summary["run_status"]
        write_json(self.path / "manifest.json", self.meta)
        return summary


def percentile(values, quantile):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered)-1)*quantile
    low = math.floor(index)
    return ordered[low] + (ordered[math.ceil(index)]-ordered[low])*(index-low)


def read_receipts(path):
    """Keep the original bytes and recover valid records around corruption."""
    if not path.exists():
        return [], []
    raw = path.read_bytes()
    records, issues = [], []
    lines = raw.splitlines(keepends=True)
    for index, line in enumerate(lines):
        try:
            row = json.loads(line, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite receipt")))
            if not isinstance(row, dict) or not isinstance(row.get("event"), str):
                raise ValueError("receipt must be an event object")
            if row["event"] in ("attempt", "outcome") and not isinstance(row.get("request_id"), str):
                raise ValueError("request ID is missing")
            if row["event"] == "outcome":
                if row.get("status") not in ("completed", "failed"):
                    raise ValueError("outcome status is invalid")
                latency = row.get("wall_ms")
                if type(latency) not in (int, float) or not math.isfinite(latency) or latency < 0:
                    raise ValueError("outcome latency is invalid")
            if row["event"] == "query_outcome":
                latency = row.get("wall_ms")
                if type(row.get("candidate_count")) is not int or row["candidate_count"] < 1:
                    raise ValueError("query candidate count is invalid")
                if type(latency) not in (int, float) or not math.isfinite(latency) or latency < 0:
                    raise ValueError("query latency is invalid")
            records.append(row)
        except (ValueError, UnicodeError, RecursionError):
            issues.append({"line": index+1, "kind": "torn_trailing_record" if index == len(lines)-1 and not line.endswith(b"\n") else "malformed_record",
                           "sha256": hashlib.sha256(line).hexdigest(), "bytes_base64": base64.b64encode(line).decode()})
    return records, issues


def effective_status(manifest, attempted, completed, failed, unfinished, corrupted=False):
    if manifest["status"] == "failed" or corrupted:
        return "failed"
    if not attempted:
        return "no_measured_requests"
    if unfinished or attempted < manifest["planned_requests"]:
        return "incomplete"
    if not completed:
        return "failed"
    return "completed_with_errors" if failed else "completed"


def summarize(manifest, records, corruptions=None):
    attempts = {r["request_id"]: r for r in records if r.get("event") == "attempt" and r.get("phase") == "measured"}
    outcomes = {r["request_id"]: r for r in records if r.get("event") == "outcome" and r.get("phase") == "measured"}
    completed = [r for k, r in outcomes.items() if k in attempts and r["status"] == "completed"]
    failed = [r for k, r in outcomes.items() if k in attempts and r["status"] == "failed"]
    strata = {}
    for key in sorted({r.get("stratum", "diagnostic") for r in attempts.values()}):
        ids = {request_id for request_id, row in attempts.items() if row.get("stratum", "diagnostic") == key}
        successes = [row["wall_ms"] for request_id, row in outcomes.items() if request_id in ids and row["status"] == "completed"]
        failures = [row["wall_ms"] for request_id, row in outcomes.items() if request_id in ids and row["status"] == "failed"]
        strata[key] = {"attempted": len(ids), "n": len(successes), "failed": len(failures),
                       "unfinished": len(ids-set(outcomes)), "p50_ms": percentile(successes, .5), "p95_ms": percentile(successes, .95),
                       "failure_p50_ms": percentile(failures, .5), "failure_p95_ms": percentile(failures, .95)}
    queries = [r for r in records if r.get("event") == "query_outcome"]
    unfinished = len(set(attempts)-set(outcomes))
    return {"run_id": manifest["run_id"], "kind": manifest["kind"],
            "run_status": effective_status(manifest, len(attempts), len(completed), len(failed), unfinished, bool(corruptions)),
            "quality_decision": "INSUFFICIENT_EVIDENCE", "production_enabled": False,
            "planned_requests": manifest["planned_requests"], "attempted_requests": len(attempts),
            "completed_requests": len(completed), "failed_requests": len(failed),
            "unfinished_requests": unfinished,
            "not_run_requests": max(0, manifest["planned_requests"]-len(attempts)),
            "priming_attempts": sum(r.get("event") == "attempt" and r.get("phase") == "prime" for r in records),
            "strata": strata, "query_count": len(queries),
            "no_candidate_queries": sum(r.get("event") == "no_candidates" for r in records),
            "receipt_corruption_count": len(corruptions or []),
            "receipt_corruptions": [{k: v for k, v in issue.items() if k != "bytes_base64"} for issue in (corruptions or [])],
            "queries_with_fallback": sum(bool(r.get("fallback")) for r in queries),
            "query_latency": {str(n): {"n": len(v), "p50_ms": percentile(v, .5), "p95_ms": percentile(v, .95)}
                              for n, v in _query_times(queries).items()},
            "corpus_manifest_sha256": manifest["corpus_manifest_sha256"],
            "protocol_sha256": manifest["protocol_sha256"],
            "server_rss_kib_before": manifest.get("server_rss_kib_before"),
            "server_rss_kib_after": manifest.get("server_rss_kib_after"),
            "source_integrity": manifest.get("source_integrity", "not_verified"),
            "limitations": ["Authored diagnostics are not independent quality evidence.",
                            "Sparse labels leave unjudged documents unknown.",
                            "Exploratory p95 from small cells is not a population tail bound.",
                            "Scores are ordinal expected values, not measured accuracy."]}


def _query_times(queries):
    groups = defaultdict(list)
    for row in queries:
        groups[row["candidate_count"]].append(row["wall_ms"])
    return groups


def report(path):
    path = Path(path)
    manifest = json.loads((path / "manifest.json").read_text())
    receipt = path / "receipts.jsonl"
    records, corruptions = read_receipts(receipt)
    if corruptions:
        write_json(path / "receipt-corruption.json", corruptions)
    summary = summarize(manifest, records, corruptions)
    write_json(path / "report.json", summary)
    lines = ["# Kev pilot evidence", "", "Quality decision: **INSUFFICIENT_EVIDENCE**. Production remains disabled.", "",
             f"Run: `{summary['run_id']}`. State: `{summary['run_status']}`.", "",
             f"Requests: {summary['planned_requests']} planned, {summary['attempted_requests']} attempted, "
             f"{summary['completed_requests']} completed, {summary['failed_requests']} failed, "
             f"{summary['unfinished_requests']} unfinished, {summary['not_run_requests']} not run.",
             f"Priming attempts: {summary['priming_attempts']}. Source integrity: `{summary['source_integrity']}`.", "",
             f"Receipt corruption: {summary['receipt_corruption_count']}. Empty candidate queries: {summary['no_candidate_queries']}.", "",
             "| Stratum | Attempts | Completed | Failed | Unfinished | Success p50 ms | Success p95 ms | Failure p50 ms | Failure p95 ms |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for key, value in summary["strata"].items():
        durations = ["unknown" if value[name] is None else f"{value[name]:.1f}" for name in ("p50_ms", "p95_ms", "failure_p50_ms", "failure_p95_ms")]
        lines.append(f"| {key} | {value['attempted']} | {value['n']} | {value['failed']} | {value['unfinished']} | " + " | ".join(durations) + " |")
    if summary["query_latency"]:
        lines.extend(["", "Whole-query latency includes every candidate and any failed attempt.", ""])
        for count, value in summary["query_latency"].items():
            lines.append(f"- {count} candidates, n={value['n']}: p50 {value['p50_ms']:.1f} ms, p95 {value['p95_ms']:.1f} ms.")
    lines.extend(["", *[f"- {text}" for text in summary["limitations"]], "",
                  f"Corpus hash: `{summary['corpus_manifest_sha256']}`.",
                  f"Protocol hash: `{summary['protocol_sha256']}`.", ""])
    (path / "report.md").write_text("\n".join(lines))
    print(json.dumps({"run": str(path), "completed": summary["completed_requests"], "failed": summary["failed_requests"],
                      "not_run": summary["not_run_requests"], "quality_decision": summary["quality_decision"]}), flush=True)
    return summary


def client_for(args, protocol):
    return Client(Path(args.data) / "server.key", expected_run=protocol["model"], timeout=protocol["latency"]["timeout_seconds"])


def run_guarded(run, client_factory, function):
    status, fields = "completed", {}
    try:
        assert_source_unchanged(Path(run.snapshot["root"]), run.snapshot)
        client = client_factory()
        run.append(event="models_before", metadata=client.get_models())
        function(client)
        run.append(event="models_after", metadata=client.get_models())
        assert_source_unchanged(Path(run.snapshot["root"]), run.snapshot)
        fields["source_integrity"] = "unchanged"
        if run.expired():
            fields["stop_reason"] = "budget_exhausted"
    except Exception as error:
        status = "failed"
        run.append(event="run_error", error=f"{type(error).__name__}: {error}")
        try:
            assert_source_unchanged(Path(run.snapshot["root"]), run.snapshot)
            fields["source_integrity"] = "unchanged"
        except Exception:
            fields["source_integrity"] = "changed_or_unverifiable"
    return run.finish(status, **fields)


def benchmark(args, protocol, snapshot):
    latency = protocol["latency"]
    cells = [(length, count, cache, repeat) for length in latency["state_tokens"]
             for count in latency["question_counts"] for cache in latency["cache_strata"]
             for repeat in range(latency["repetitions_per_cell"])]
    random.Random(latency["random_seed"]).shuffle(cells)
    query_cells = [(count, repeat) for count in latency["query_candidate_counts"]
                   for repeat in range(latency["query_repetitions_per_count"])]
    random.Random(latency["random_seed"] + 1).shuffle(query_cells)
    planned = len(cells) + sum(count for count, _ in query_cells)
    run = Run("benchmark", args.data, protocol, snapshot, planned)

    def execute(client):
        tok = tokenizer()
        for index, (length, count, cache, repeat) in enumerate(cells):
            if run.expired():
                break
            prefix = f"Record {run.meta['run_id']} {index}. "
            encoded = tok.encode(prefix + "The reference describes routine software engineering observations. " * length)
            state = tok.decode(encoded[:length])
            actual = len(tok.encode(state))
            if actual > min(length, protocol["max_state_tokens"]):
                raise ValueError("benchmark state exceeds its exact token budget")
            questions = {f"q{i}": {"type": "noul", "instructions": "Does the reference discuss software engineering?"} for i in range(count)}
            stratum = f"tokens={length};questions={count};{cache}"
            if cache == "repeated-state":
                if run.request(client, state, questions, phase="prime", stratum=stratum, state_tokens=actual) is None:
                    run.append(event="prime_failure", stratum=stratum, index=index)
                    continue
            run.request(client, state, questions, stratum=stratum, state_tokens=actual, repetition=repeat)
            print(json.dumps({"progress": index+1, "planned": len(cells), "stratum": stratum}), flush=True)
        documents = snapshot["documents"]
        for count, repeat in query_cells:
            if run.expired():
                break
            if len(documents) < count:
                run.append(event="query_not_run", candidate_count=count, reason="insufficient corpus documents")
                continue
            query = f"Find reference material about reliable agent state, review evidence, and recovery. Request {repeat}."
            started, failed = time.perf_counter(), False
            ids = lexical_rank(query, snapshot, limit=count)
            filled = count - len(ids)
            ids.extend(doc["id"] for doc in documents if doc["id"] not in ids)
            selected_ids = ids[:count]
            by_id = {doc["id"]: doc for doc in documents}
            selected = [by_id[doc_id] for doc_id in selected_ids]
            for document in selected:
                if run.expired():
                    failed = True
                    break
                state, packet_info = packet(query, document, tok, protocol["max_state_tokens"])
                answer = run.request(client, state, {"relevance": {"type": "score", "instructions": protocol["relevance_instructions"],
                                     "criteria": protocol["relevance_levels"]}},
                                     stratum=f"whole-query;candidate-count={count}", **packet_info)
                failed = failed or answer is None
            run.append(event="query_outcome", candidate_count=count, wall_ms=(time.perf_counter()-started)*1000,
                       fallback=failed, kev_success=not failed, benchmark_only=True, zero_score_pool_fill=filled)
            assert_source_unchanged(Path(snapshot["root"]), snapshot)
            print(json.dumps({"whole_query_completed": count, "repetition": repeat, "fallback": failed}), flush=True)
    return run_guarded(run, lambda: client_for(args, protocol), execute)


def diagnostic(args, protocol, snapshot):
    cases = [json.loads(line) for line in Path(args.fixtures).read_text().splitlines() if line.strip()]
    if args.limit:
        cases = cases[:args.limit]
    by_id = {document["id"]: document for document in snapshot["documents"]}
    pools = [(case, lexical_rank(case["query"], snapshot, limit=protocol["candidate_pool"])) for case in cases]
    run = Run("diagnostic", args.data, protocol, snapshot, sum(len(pool) for _, pool in pools))
    write_json(run.path / "diagnostic-labels.json", cases)
    run.meta.update(dataset_sha256=digest(cases), dataset_type=protocol["diagnostic_dataset"],
                    query_count_planned=len(cases), explicit_query_limit=args.limit)
    write_json(run.path / "manifest.json", run.meta)

    def execute(client):
        tok = tokenizer()
        for case, pool in pools:
            if run.expired():
                break
            if not pool:
                run.append(event="no_candidates", case_id=case["id"], dataset_type=case["dataset_type"],
                           candidate_count=0, status="not_run", kev_success=False)
                continue
            start, scores, failed = time.perf_counter(), {}, False
            for document_id in pool:
                if run.expired():
                    failed = True
                    break
                try:
                    state, packet_info = packet(case["query"], by_id[document_id], tok, protocol["max_state_tokens"])
                except Exception as error:
                    failed = True
                    run.append(event="packet_rejected", case_id=case["id"], error=f"{type(error).__name__}: {error}")
                    continue
                result = run.request(client, state, {"relevance": {"type": "score", "instructions": protocol["relevance_instructions"],
                                   "criteria": protocol["relevance_levels"]}}, case_id=case["id"], document_id=document_id, **packet_info)
                if result is None:
                    failed = True
                else:
                    scores[document_id] = result["answers"]["relevance"]["score"]
            ranked = pool if failed else sorted(pool, key=lambda key: (-scores[key], pool.index(key)))
            labels = case["labels"]
            useful = {key for key, grade in labels.items() if grade is not None and grade >= 2}
            run.append(event="query_outcome", case_id=case["id"], dataset_type=case["dataset_type"], candidate_count=len(pool),
                       wall_ms=(time.perf_counter()-start)*1000, fallback=failed, kev_success=not failed,
                       candidate_recall_judged_only=len(useful & set(pool))/len(useful) if useful else None,
                       lexical=metrics(labels, pool), kev=metrics(labels, ranked),
                       legacy=metrics(labels, legacy_rank(case["query"], snapshot)),
                       lexical_order=pool, kev_order=ranked)
            print(json.dumps({"case_completed": case["id"], "candidate_count": len(pool), "fallback": failed}), flush=True)
            assert_source_unchanged(Path(snapshot["root"]), snapshot)
    return run_guarded(run, lambda: client_for(args, protocol), execute)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=HERE / ".local")
    sub = parser.add_subparsers(dest="command", required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("--library", type=Path, required=True)
    snap.add_argument("--hook", type=Path, required=True)
    sub.add_parser("benchmark")
    diag = sub.add_parser("diagnostic")
    diag.add_argument("--fixtures", type=Path, default=HERE / "fixtures/diagnostic_queries.jsonl")
    diag.add_argument("--limit", type=int, default=0, help="Explicit exploratory subset; zero runs every authored case")
    rep = sub.add_parser("report")
    rep.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "report":
        return 0 if report(args.run)["run_status"] == "completed" else 1
    if args.command == "snapshot":
        protect_output(args.data, args.library)
        args.data.mkdir(parents=True, mode=0o700, exist_ok=True)
        destination = args.data / "snapshot.json"
        if destination.exists():
            raise FileExistsError("snapshot exists; preserve it and select a new --data directory")
        snapshot = snapshot_library(args.library, args.hook)
        snapshot["source_checkout"] = source_checkout(args.library)
        write_json(destination, snapshot)
        print(json.dumps({"snapshot": str(destination), "documents": len(snapshot["documents"]), "corpus_manifest_sha256": snapshot["corpus_manifest_sha256"]}))
        return 0
    protocol = json.loads((HERE / "protocol.json").read_text())
    snapshot = json.loads((args.data / "snapshot.json").read_text())
    result = benchmark(args, protocol, snapshot) if args.command == "benchmark" else diagnostic(args, protocol, snapshot)
    return 0 if result["run_status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
