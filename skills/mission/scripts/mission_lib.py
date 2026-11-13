"""Shared helpers for the mission skill scripts.

Run every script with: uv run --quiet --with pyyaml python3 <script> ...
"""
from __future__ import annotations

import contextlib
import datetime as dt
import fcntl
import json
import os
import pathlib
import re
import subprocess
import sys

try:
    import yaml
except ModuleNotFoundError:
    import os, shutil, sys
    _uv, _main = shutil.which("uv"), getattr(sys.modules.get("__main__"), "__file__", None)
    if _uv and _main and os.environ.get("UV_DEPS_REEXEC") != os.path.abspath(_main):
        os.environ["UV_DEPS_REEXEC"] = os.path.abspath(_main)
        os.execv(_uv, [_uv, "run", "--quiet", "--with", "pyyaml", "python", os.path.abspath(_main), *sys.argv[1:]])
    raise

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
JIRA_SKILL = SKILL_DIR.parent / "jira" / "jira_skill.py"
NO_PM_ROOT = pathlib.Path("/nonexistent/mission-pm-root")


def _yaml_file(p: pathlib.Path) -> dict:
    try:
        return (yaml.safe_load(p.read_text()) or {}) if p.is_file() else {}
    except (OSError, yaml.YAMLError):
        return {}


# Deployment config lives outside the harness (no org names in this repo).
# 1. User config: $MISSION_CONFIG or ~/.config/mission/config.yaml -> pm_root (and optional overrides).
# 2. Org config, versioned in the PM repo: <pm_root>/missions/_meta/config.yaml ->
#    gh_repo, jira_browse, jira_org, jira_key_pattern, mr_unknown_reason.
# A missing value is never guessed: tracker calls then report UNKNOWN.
USER_CONFIG_FILE = pathlib.Path(os.environ.get("MISSION_CONFIG") or pathlib.Path.home() / ".config" / "mission" / "config.yaml")
_USER = _yaml_file(USER_CONFIG_FILE)
PM_ROOT = pathlib.Path(os.environ.get("MISSION_PM_ROOT") or _USER.get("pm_root") or NO_PM_ROOT).expanduser().resolve()
MISSIONS_DIR = PM_ROOT / "missions"
ORG_CONFIG_FILE = MISSIONS_DIR / "_meta" / "config.yaml"
CONFIG = {**_yaml_file(ORG_CONFIG_FILE), **{k: v for k, v in _USER.items() if k != "pm_root"}}
GH_REPO = CONFIG.get("gh_repo")
GH_BLOB = f"https://github.com/{GH_REPO}/blob/main/" if GH_REPO else None
JIRA_BROWSE = CONFIG.get("jira_browse") or ""
JIRA_ORG = CONFIG.get("jira_org")
JIRA_KEY_PATTERN = CONFIG.get("jira_key_pattern") or r"[A-Z][A-Z0-9]+-\d+"
MR_UNKNOWN_REASON = CONFIG.get("mr_unknown_reason") or "open MRs not checked: the forge needs extra auth; check them by hand"


def config_problem() -> str | None:
    if PM_ROOT == NO_PM_ROOT.resolve():
        return f"no PM root: set MISSION_PM_ROOT or pm_root in {USER_CONFIG_FILE}"
    if not PM_ROOT.is_dir():
        return f"PM root {PM_ROOT} does not exist"
    return None


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def mission_dir(slug_or_path: str) -> pathlib.Path:
    p = pathlib.Path(slug_or_path)
    if p.is_dir() and (p / "mission.yaml").exists():
        return p.resolve()
    if p.name == "mission.yaml" and p.exists():
        return p.parent.resolve()
    if config_problem():
        sys.exit(config_problem())
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
    if not GH_BLOB:
        return path.resolve().as_uri()
    try:
        return GH_BLOB + str(path.resolve().relative_to(PM_ROOT))
    except ValueError:
        return path.resolve().as_uri()


def set_section(d: pathlib.Path, key: str, value) -> None:
    """Replace one top-level block (for example threads:) in place. Every other line of the file stays as it is.

    The block runs from its 'key:' line to the next top-level key. A missing block is appended at the end.
    Use it inside locked(d), because several sessions write the same record.
    """
    f = d / "mission.yaml"
    lines = f.read_text().splitlines(keepends=True)
    block = yaml.safe_dump({key: value}, sort_keys=False, allow_unicode=True, width=120, default_flow_style=False)
    start = next((i for i, ln in enumerate(lines) if re.match(rf"^{re.escape(key)}:(\s|$)", ln)), None)
    if start is None:
        text = "".join(lines)
        f.write_text(text.rstrip("\n") + "\n\n" + block)
        return
    end = start + 1
    while end < len(lines) and (not lines[end].strip() or lines[end][0] in " -\t"):
        end += 1
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    f.write_text("".join(lines[:start]) + block + "".join(lines[end:]))


@contextlib.contextmanager
def locked(d: pathlib.Path):
    """An exclusive flock on mission.yaml for a read-modify-write (like the ledger helper)."""
    with open(d / "mission.yaml", "r+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def closeout_home(d: pathlib.Path) -> pathlib.Path:
    """Where a mission's close-out files live: the mission folder, or missions/_closeout/<slug>/ when the
    sweep ran before the mission record existed."""
    if (d / "closeout.yaml").exists():
        return d
    alt = MISSIONS_DIR / "_closeout" / d.name
    return alt if (alt / "closeout.yaml").exists() else d
