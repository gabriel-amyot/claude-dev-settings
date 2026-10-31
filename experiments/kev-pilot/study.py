#!/usr/bin/env python3
"""Run a bounded, resumable-in-evidence local feasibility study without live hooks."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def save(path, value):
    temporary = path.with_suffix(".new")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def event(path, **value):
    with (path / "events.jsonl").open("a") as stream:
        stream.write(json.dumps({"at": now(), **value}) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def run_study(args):
    data, study = args.data.resolve(), args.study.resolve()
    lock = (data / "study.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        event(study, event="study_reentry_rejected", reason="another study holds the local run lock")
        lock.close()
        return 1
    state = json.loads((study / "status.json").read_text())
    if state.get("status") != "starting":
        event(study, event="study_reentry_rejected", reason="study already started or terminal")
        lock.close()
        return 1
    started_server = False
    server_instance = None

    def update(status, **fields):
        state.update(status=status, updated_at=now(), **fields)
        save(study / "status.json", state)

    def command(stage, argv, timeout):
        event(study, event="stage_attempt", stage=stage, argv=argv)
        update("running", stage=stage)
        start = time.monotonic()
        with (study / (stage + ".log")).open("a") as log:
            try:
                result = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
                code = result.returncode
            except subprocess.TimeoutExpired:
                code = 124
        event(study, event="stage_outcome", stage=stage, returncode=code, seconds=time.monotonic()-start)
        if stage in ("probes", "benchmark", "diagnostic"):
            observed = []
            for line in (study / (stage + ".log")).read_text().splitlines():
                try:
                    value = json.loads(line)
                except ValueError:
                    continue
                if isinstance(value, dict) and isinstance(value.get("run"), str):
                    candidate = Path(value["run"]).resolve()
                    if (data / "runs") in candidate.parents and (candidate / "manifest.json").is_file():
                        observed.append(str(candidate))
            state["run_paths"] = sorted(set(state.get("run_paths", []) + observed))
            update("running", stage=stage)
            if code == 0 and not observed:
                raise RuntimeError(f"stage {stage} returned no run receipt")
        if code:
            raise RuntimeError(f"stage {stage} failed, see its retained log")

    try:
        if args.wait_bootstrap:
            update("waiting_for_bootstrap", stage="download")
            deadline = time.monotonic() + args.bootstrap_wait_seconds
            while True:
                try:
                    receipt = json.loads(args.wait_bootstrap.read_text())
                except json.JSONDecodeError:
                    if time.monotonic() >= deadline:
                        raise RuntimeError("bootstrap receipt remained unreadable within wait budget")
                    time.sleep(1)
                    continue
                if receipt["status"] == "completed":
                    event(study, event="bootstrap_observed", status="completed", receipt=str(args.wait_bootstrap))
                    break
                if receipt["status"] == "failed":
                    raise RuntimeError("bootstrap failed; preserve its receipt and investigate")
                if time.monotonic() > deadline:
                    raise RuntimeError("bootstrap wait budget exhausted; no inference attempted")
                time.sleep(5)
        python = str(args.source.resolve() / ".venv/bin/python")
        command("offline-tests", [python, "-m", "unittest", "discover", "-s", str(HERE / "tests"), "-v"], 120)
        command("runtime-start", [python, str(HERE / "runtime.py"), "start", "--data", str(data), "--source", str(args.source), "--offline"], 30)
        server_instance = json.loads((study / "runtime-start.log").read_text())
        started_server = True
        from local_client import Client
        from retrieval import assert_source_unchanged
        snapshot = json.loads((data / "snapshot.json").read_text())
        assert_source_unchanged(Path(snapshot["root"]), snapshot)
        deadline = time.monotonic() + 180
        update("running", stage="model-initialization")
        last_error = None
        while time.monotonic() < deadline:
            try:
                model = Client(data / "server.key", timeout=2).get_models()
                event(study, event="server_ready", metadata=model)
                break
            except Exception as error:
                last_error = f"{type(error).__name__}: {error}"
                time.sleep(3)
        else:
            raise RuntimeError(f"model did not become ready: {last_error}")
        command("runtime-ready", [python, str(HERE / "runtime.py"), "status", "--data", str(data)], 10)
        command("probes", [python, str(HERE / "probes.py"), "--data", str(data)], 180)
        command("benchmark", [python, str(HERE / "pilot.py"), "--data", str(data), "benchmark"], 1300)
        command("diagnostic", [python, str(HERE / "pilot.py"), "--data", str(data), "diagnostic"], 1300)
        assert_source_unchanged(Path(snapshot["root"]), snapshot)
        update("completed", stage="finished", quality_decision="INSUFFICIENT_EVIDENCE", source_integrity="unchanged")
    except Exception as error:
        event(study, event="study_error", error=f"{type(error).__name__}: {error}")
        update("failed", error=f"{type(error).__name__}: {error}", quality_decision="INSUFFICIENT_EVIDENCE")
    finally:
        terminal_status = state["status"]
        terminal_stage = state.get("stage")
        if started_server and not args.keep_server:
            try:
                command("runtime-stop", [str(args.source.resolve() / ".venv/bin/python"), str(HERE / "runtime.py"), "stop", "--data", str(data),
                        "--expected-pid", str(server_instance["pid"]), "--expected-identity", server_instance["identity"]], 10)
            except Exception as error:
                event(study, event="cleanup_error", error=f"{type(error).__name__}: {error}")
        state["updated_at"] = now()
        # Runtime cleanup is a stage, not a replacement for the study's terminal state.
        state["status"] = terminal_status
        state["stage"] = terminal_stage
        save(study / "status.json", state)
        write_summary(study, state, data)
        lock.close()
    return 1 if state["status"] == "failed" else 0


def write_summary(study, state, data):
    reports = []
    for owned in state.get("run_paths", []):
        run_path = Path(owned).resolve()
        if (data / "runs").resolve() not in run_path.parents:
            raise ValueError("study run receipt is outside its data directory")
        path = run_path / "report.json"
        if not path.exists():
            from pilot import report
            report(run_path)
        reports.append(json.loads(path.read_text()))
    summary = {"study_status": state["status"], "stage": state.get("stage"),
               "quality_decision": "INSUFFICIENT_EVIDENCE", "production_enabled": False,
               "error": state.get("error"), "runs": reports}
    save(study / "summary.json", summary)
    lines = ["# Local Kev study", "", f"Study status: `{state['status']}`.",
             "Quality decision: **INSUFFICIENT_EVIDENCE**. Production remains disabled.", "",
             "All attempts and stage logs remain in private local evidence storage.", ""]
    if state.get("error"):
        lines.append(f"Error: {state['error']}")
    for report in reports:
        lines.append(f"- {report['kind']}: {report['completed_requests']} completed, {report['failed_requests']} failed, {report['not_run_requests']} not run.")
    (study / "summary.md").write_text("\n".join(lines)+"\n")


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("start", "status", "_run"))
    parser.add_argument("--data", type=Path, default=HERE / ".local")
    parser.add_argument("--source", type=Path, default=Path.home() / "Library/Caches/kev-pilot/source")
    parser.add_argument("--study", type=Path)
    parser.add_argument("--wait-bootstrap", type=Path)
    parser.add_argument("--bootstrap-wait-seconds", type=int, default=3600)
    parser.add_argument("--keep-server", action="store_true")
    args = parser.parse_args()
    if args.command == "_run":
        return run_study(args)
    if args.command == "status":
        for path in sorted((args.data / "studies").glob("*/status.json")):
            print(path.read_text())
        return 0
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    study = args.data.resolve() / "studies" / stamp
    study.mkdir(parents=True, mode=0o700)
    state = {"status": "starting", "started_at": now(), "quality_decision": "INSUFFICIENT_EVIDENCE", "production_enabled": False}
    save(study / "status.json", state)
    argv = [sys.executable, str(Path(__file__).resolve()), "_run", "--data", str(args.data.resolve()),
            "--source", str(args.source.resolve()), "--study", str(study),
            "--bootstrap-wait-seconds", str(args.bootstrap_wait_seconds)]
    if args.wait_bootstrap:
        argv += ["--wait-bootstrap", str(args.wait_bootstrap.resolve())]
    if args.keep_server:
        argv += ["--keep-server"]
    with (study / "process.log").open("w") as log:
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    event(study, event="study_spawned", pid=process.pid)
    print(json.dumps({"study": str(study), "pid": process.pid, "status": "started"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
