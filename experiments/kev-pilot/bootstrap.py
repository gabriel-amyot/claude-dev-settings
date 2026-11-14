#!/usr/bin/env python3
"""Install pinned upstream Kev into a private cache and retain an attempt receipt."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SOURCE_COMMIT = "2074cc44256200bb37540103fa4572901faa10f3"
MODEL_REVISION = "139fdd94f1b6a6ad80cc15e08fcb99cac885a101"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path.home() / "Library/Caches/kev-pilot/source")
    parser.add_argument("--data", type=Path, default=Path(__file__).parent / ".local")
    args = parser.parse_args()
    args.data.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    receipt_path = args.data / f"bootstrap-{stamp}.json"
    log_path = args.data / f"bootstrap-{stamp}.log"
    receipt = {"started_at": stamp, "source_commit": SOURCE_COMMIT, "model_revision": MODEL_REVISION,
               "status": "started", "steps": [], "log": str(log_path)}

    def save():
        temporary = receipt_path.with_suffix(".new")
        temporary.write_text(json.dumps(receipt, indent=2) + "\n")
        temporary.replace(receipt_path)

    def run(command, cwd=None):
        step = {"command": command, "status": "started"}
        receipt["steps"].append(step)
        save()
        start = time.monotonic()
        with log_path.open("ab") as log:
            result = subprocess.run(command, cwd=cwd, stdout=log, stderr=log)
        step.update(returncode=result.returncode, seconds=time.monotonic()-start,
                    status="completed" if result.returncode == 0 else "failed")
        save()
        if result.returncode:
            raise RuntimeError(f"bootstrap command failed ({result.returncode}), see {log_path}")

    save()
    try:
        if not args.source.exists():
            run(["git", "clone", "https://github.com/jaredpalmer/kev.git", str(args.source)])
            run(["git", "checkout", "--detach", SOURCE_COMMIT], args.source)
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.source, text=True).strip()
        if actual != SOURCE_COMMIT:
            raise ValueError(f"source revision mismatch: {actual}")
        if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=args.source):
            raise ValueError("upstream tracked source is dirty")
        receipt["uv_lock_sha256"] = hashlib.sha256((args.source / "uv.lock").read_bytes()).hexdigest()
        run(["uv", "sync", "--locked", "--extra", "serve", "--no-dev", "--python", "3.13"], args.source)
        model_receipt = args.data.resolve() / f"models-{stamp}.json"
        script = '''
import hashlib, json
from pathlib import Path
from huggingface_hub import snapshot_download, HfApi
adapter = Path(snapshot_download("jaredpalmer/kev-4b", revision=REV,
    allow_patterns=["*.json", "*.safetensors", "*.pt", "*.txt", "*.jinja"]))
config = json.loads((adapter / "training_config.json").read_text())
base = config["args"]["base"]
revision = config.get("base_revision")
if not revision:
    raise RuntimeError("checkpoint does not pin its base revision")
base_revision = HfApi().model_info(base, revision=revision).sha
base_path = Path(snapshot_download(base, revision=base_revision,
    allow_patterns=["*.json", "*.safetensors", "*.txt", "*.jinja", "*.model"]))
files = {}
for root in (adapter, base_path):
    for path in sorted(root.rglob("*")):
        if path.is_file():
            files[str(path)] = {"size":path.stat().st_size,
                "sha256":hashlib.file_digest(path.open("rb"), "sha256").hexdigest()}
Path(OUTPUT).write_text(json.dumps({"adapter_revision":REV,"adapter_path":str(adapter),
    "base":base,"base_revision":base_revision,"base_path":str(base_path),"files":files},indent=2)+"\\n")
'''
        script = "REV=" + repr(MODEL_REVISION) + "\nOUTPUT=" + repr(str(model_receipt)) + "\n" + script
        run([str(args.source / ".venv/bin/python"), "-c", script], args.source)
        receipt.update(status="completed", model_receipt=str(model_receipt))
    except Exception as error:
        receipt.update(status="failed", error=f"{type(error).__name__}: {error}")
    receipt["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    save()
    print(json.dumps({"status": receipt["status"], "receipt": str(receipt_path), "log": str(log_path)}))
    return 0 if receipt["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
