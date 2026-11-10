"""Shared helpers for the mission skill scripts.

Run every script with: uv run --quiet --with pyyaml python3 <script> ...
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys

import yaml

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
PM_ROOT = pathlib.Path(os.environ.get(
    "MISSION_PM_ROOT",
    "/Users/gamyot/Developer/grp-beklever-com/project-management")).resolve()
MISSIONS_DIR = PM_ROOT / "missions"
GH_REPO = "gabriel-amyot/klever-project-management"
GH_BLOB = f"https://github.com/{GH_REPO}/blob/main/"
JIRA_BROWSE = "https://beklever.atlassian.net/browse/"


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def mission_dir(slug_or_path: str) -> pathlib.Path:
    p = pathlib.Path(slug_or_path)
    if p.is_dir() and (p / "mission.yaml").exists():
        return p.resolve()
    if p.name == "mission.yaml" and p.exists():
        return p.parent.resolve()
    d = MISSIONS_DIR / slug_or_path
    if not (d / "mission.yaml").exists():
        sys.exit(f"mission not found: {slug_or_path} (looked in {d})")
    return d


def load(d: pathlib.Path) -> dict:
    return yaml.safe_load((d / "mission.yaml").read_text()) or {}


def save(d: pathlib.Path, data: dict) -> None:
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)
    (d / "mission.yaml").write_text(text)


def set_top(d: pathlib.Path, key: str, value) -> None:
    """Set one top-level scalar or flow-mapping key in place, without reflowing the file."""
    f = d / "mission.yaml"
    text = f.read_text()
    rendered = yaml.safe_dump({key: value}, default_flow_style=True, width=10_000, allow_unicode=True).strip()
    rendered = rendered[1:-1] if rendered.startswith("{") else rendered
    pat = re.compile(rf"^{re.escape(key)}:.*$", re.M)
    text = pat.sub(lambda _: rendered, text, count=1) if pat.search(text) else text.rstrip("\n") + "\n" + rendered + "\n"
    f.write_text(text)


def load_computed(d: pathlib.Path) -> dict:
    f = d / "computed.json"
    return json.loads(f.read_text()) if f.exists() else {}


def run(cmd: list[str], check: bool = True, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if check and r.returncode != 0:
        sys.exit(f"command failed ({r.returncode}): {' '.join(cmd)}\n{r.stderr.strip()}")
    return r


def gh_url(path: pathlib.Path) -> str:
    try:
        return GH_BLOB + str(path.resolve().relative_to(PM_ROOT))
    except ValueError:
        return path.resolve().as_uri()
