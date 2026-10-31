"""Manage one authenticated native Kev MLX process. Installs nothing."""
from __future__ import annotations

import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import time

from local_client import Client, ClientError, DEFAULT_PORT, PINNED_RUN, PINNED_SOURCE


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def identity(pid):
    if type(pid) is not int or pid <= 1:
        return None
    query = subprocess.run(["ps", "-p", str(pid), "-o", "lstart=", "-o", "command="], capture_output=True, text=True)
    return query.stdout.strip() if query.returncode == 0 else None


def write_private(path, record):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(record, stream, indent=2)
        stream.write("\n")


def event(data, **record):
    fd = os.open(data / "runtime-events.jsonl", os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(json.dumps({"at": now(), **record}, sort_keys=True) + "\n")


def load_state(data):
    path = data / "server.json"
    return json.loads(path.read_text()) if path.exists() else None


def owned(state):
    return bool(state and state.get("identity") and identity(state.get("pid")) == state["identity"])


def start(args, data):
    if args.run != PINNED_RUN:
        raise ClientError("runtime requires the registered pinned Kev-4B checkpoint")
    if owned(load_state(data)):
        raise ClientError("the recorded server is already running")
    source = args.source.resolve()
    revision = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    if revision != PINNED_SOURCE:
        raise ClientError("source revision mismatch")
    if subprocess.run(["git", "-C", str(source), "diff", "--quiet", "HEAD", "--", "kev"], check=False).returncode:
        raise ClientError("serving source has local modifications")
    python = source / ".venv/bin/python"
    if not python.is_file():
        raise ClientError("source environment is not installed")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", DEFAULT_PORT))
    token = secrets.token_hex(32)
    key = data / "server.key"
    fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(token + "\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("KEV_")}
    env.update(KEV_API_KEY=token, KEV_BACKEND="mlx", KEV_TRUNCATE_STATES="0", HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false", PYTHONUNBUFFERED="1")
    if args.offline:
        env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    command = [str(python), "-m", "kev.serve", "--run", args.run, "--host", "127.0.0.1", "--port", str(DEFAULT_PORT), "--device", "mps"]
    started = now()
    event(data, action="start_attempt", source_revision=revision, run=args.run, started_at=started, offline=args.offline)
    log_path = data / ("server-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".log")
    fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as log:
        process = subprocess.Popen(command, cwd=source, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    state = {"pid": process.pid, "identity": identity(process.pid), "source": str(source), "source_revision": revision, "run": args.run, "started_at": started, "log": str(log_path), "offline": args.offline}
    write_private(data / "server.json", state)
    event(data, action="spawned", **state)
    print(json.dumps({"status": "starting", **state}, indent=2))


def status(args, data):
    state = load_state(data)
    result = {"status": "stopped", "state": state}
    if owned(state):
        result["status"] = "initializing"
        try:
            result["models"] = Client(data / "server.key", expected_run=state["run"], timeout=2).get_models()
            result["status"] = "ready"
            if not state.get("ready_at"):
                state["ready_at"] = now()
                write_private(data / "server.json", state)
                event(data, action="ready", started_at=state["started_at"], ready_at=state["ready_at"], models=result["models"])
        except ClientError as exc:
            result["detail"] = str(exc)
    elif state:
        result["status"] = "exited_or_identity_changed"
        if not state.get("exit_observed_at"):
            state["exit_observed_at"] = now()
            write_private(data / "server.json", state)
            event(data, action="exit_observed", pid=state.get("pid"), started_at=state.get("started_at"), was_ready=bool(state.get("ready_at")))
    print(json.dumps(result, indent=2))


def stop(args, data):
    state = load_state(data)
    if not owned(state):
        raise ClientError("no matching owned server process; nothing was stopped")
    os.kill(state["pid"], signal.SIGTERM)
    event(data, action="stop_requested", pid=state["pid"], identity=state["identity"])
    print(json.dumps({"status": "stop_requested", "pid": state["pid"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("start", "status", "stop"))
    parser.add_argument("--source", type=Path, default=Path.home() / "Library/Caches/kev-pilot/source")
    parser.add_argument("--data", type=Path, default=Path(__file__).parent / ".local")
    parser.add_argument("--run", default=PINNED_RUN)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    data = args.data.absolute()
    if data.is_symlink():
        parser.error("data directory cannot be a symlink")
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(data, 0o700)
    fd = os.open(data / "runtime.lock", os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            globals()[args.command](args, data)
        except (ClientError, OSError, subprocess.CalledProcessError, ValueError) as exc:
            event(data, action=args.command + "_failed", error_type=type(exc).__name__, message=str(exc) if isinstance(exc, ClientError) else "local runtime operation failed")
            parser.exit(1, str(exc) + "\n" if isinstance(exc, ClientError) else "local runtime operation failed\n")


if __name__ == "__main__":
    main()
