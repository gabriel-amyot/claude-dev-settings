#!/usr/bin/env python3
"""Layer A behavior suite for disk-management scripts.

Runs scan.sh and size_items.sh hermetically. HOME points to a temp fixture tree.
PATH starts with stub `df`, `brew` and `docker` commands, so the result does not
depend on the host disk. The suite checks behavior (which volume the verdict
names, per-item sizes), not command strings in the scripts.

Override the script under test with SCAN_SH=/path/to/scan.sh to prove that an
older revision fails (the 2026-09-21 revision ran only `df -h /`).

Exit code 0 = all cases pass, 1 = any case fails.
"""
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCAN_SH = Path(os.environ.get("SCAN_SH", SKILL_DIR / "scripts" / "scan.sh"))
SIZE_SH = SKILL_DIR / "scripts" / "size_items.sh"

# Root volume looks healthy (73%), data volume is full (100%): the 2026-09-21 incident.
STUB_DF = r"""#!/bin/bash
human=0
paths=()
for a in "$@"; do
  case "$a" in
    -h) human=1 ;;
    -*) ;;
    *) paths+=("$a") ;;
  esac
done
if [ $human = 1 ]; then
  echo "Filesystem Size Used Avail Capacity Mounted on"
else
  echo "Filesystem 1024-blocks Used Available Capacity Mounted on"
fi
for p in "${paths[@]}"; do
  if [ "$p" = "/" ]; then
    if [ $human = 1 ]; then echo "/dev/disk3s1s1 460Gi 10Gi 3.7Gi 73% /"
    else echo "/dev/disk3s1s1 482344960 10485760 3879731 73% /"; fi
  else
    if [ $human = 1 ]; then echo "/dev/disk3s5 460Gi 404Gi 0Bi 100% $p"
    else echo "/dev/disk3s5 482344960 423624704 0 100% $p"; fi
  fi
done
"""

STUB_BREW = r"""#!/bin/bash
case "$*" in
  --cache) echo "$HOME/Library/Caches/Homebrew" ;;
  *cleanup*-n*|*cleanup*--dry-run*) echo "Would remove: /opt/homebrew/vendor/portable-ruby/3.3.1 (1,700 files, 34MB)"
    echo "==> This operation would free approximately 5.2GB of disk space." ;;
  *cleanup*) echo "STUB-BREW-REAL-CLEANUP-CALLED" ;;
esac
"""

STUB_DOCKER = "#!/bin/bash\necho 'TYPE TOTAL ACTIVE SIZE RECLAIMABLE'\n"


def write_exec(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def make_file(path: Path, kib: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(b"\0" * kib * 1024)


def build_world(root: Path) -> dict:
    home = root / "home"
    stubs = root / "stubs"
    data_volume = root / "DataVolume"
    for d in (home / "Library/Application Support", home / "Library/Caches/Homebrew", home / "Downloads", stubs, data_volume):
        d.mkdir(parents=True, exist_ok=True)
    write_exec(stubs / "df", STUB_DF)
    write_exec(stubs / "brew", STUB_BREW)
    write_exec(stubs / "docker", STUB_DOCKER)
    steam_common = home / "Library/Application Support/Steam/steamapps/common"
    make_file(steam_common / "Liftoff/data.bin", 3072)
    make_file(steam_common / "DRL Simulator/data.bin", 1024)
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["PATH"] = f"{stubs}:{env.get('PATH', '/usr/bin:/bin')}"
    env["DATA_VOLUME"] = str(data_volume)
    return {"env": env, "data_volume": str(data_volume), "steam_common": steam_common, "root": root}


def run(cmd, env):
    return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)


def verdict_line(out: str) -> str:
    return next((l for l in out.splitlines() if l.startswith("CAPACITY_VERDICT:")), "")


def case_verdict_names_full_data_volume(w):
    out = run(["bash", str(SCAN_SH), "--df-only"], w["env"]).stdout
    line = verdict_line(out)
    ok = "100%" in line and line.rstrip().split(" (")[0].endswith(w["data_volume"])
    return ok, f"verdict line: {line!r}"


def case_full_scan_verdict_and_no_mutation(w):
    res = run(["bash", str(SCAN_SH)], w["env"])
    line = verdict_line(res.stdout)
    ok = "100%" in line and "STUB-BREW-REAL-CLEANUP-CALLED" not in res.stdout
    return ok, f"verdict line: {line!r}"


def case_after_shot_mode_skips_locations(w):
    out = run(["bash", str(SCAN_SH), "--df-only"], w["env"]).stdout
    ok = bool(verdict_line(out)) and "Application Support" not in out
    return ok, "df-only output must hold the verdict and no location sections"


def case_non_apfs_falls_back_to_root(w):
    env = dict(w["env"])
    env["DATA_VOLUME"] = str(w["root"] / "does-not-exist")
    out = run(["bash", str(SCAN_SH), "--df-only"], env).stdout
    line = verdict_line(out)
    ok = "73%" in line and line.split(" (")[0].endswith(" /")
    return ok, f"verdict line: {line!r}"


def case_brew_reclaimable_reported(w):
    out = run(["bash", str(SCAN_SH)], w["env"]).stdout
    ok = "would free approximately 5.2GB" in out
    return ok, "scan must surface the brew --prune=all dry-run summary"


def case_size_items_children_split(w):
    if not SIZE_SH.exists():
        return False, f"missing {SIZE_SH}"
    out = run(["bash", str(SIZE_SH), "--children", str(w["steam_common"])], w["env"]).stdout
    items = [l for l in out.splitlines() if l.startswith("ITEM ")]
    ok = (
        len(items) == 2
        and items[0].startswith("ITEM 3.0M ") and items[0].endswith("/Liftoff")
        and items[1].startswith("ITEM 1.0M ") and items[1].endswith("/DRL Simulator")
        and "TOTAL 4.0M" in out
    )
    return ok, f"output: {out.strip()!r}"


def case_size_items_named_paths(w):
    if not SIZE_SH.exists():
        return False, f"missing {SIZE_SH}"
    target = w["steam_common"] / "DRL Simulator"
    out = run(["bash", str(SIZE_SH), str(target), str(w["root"] / "missing")], w["env"]).stdout
    items = [l for l in out.splitlines() if l.startswith("ITEM ")]
    ok = len(items) == 1 and items[0].endswith("/DRL Simulator") and "TOTAL 1.0M" in out
    return ok, f"output: {out.strip()!r}"


CASES = [
    case_verdict_names_full_data_volume,
    case_full_scan_verdict_and_no_mutation,
    case_after_shot_mode_skips_locations,
    case_non_apfs_falls_back_to_root,
    case_brew_reclaimable_reported,
    case_size_items_children_split,
    case_size_items_named_paths,
]


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory(prefix="disk-mgmt-evals-") as tmp:
        world = build_world(Path(tmp))
        for case in CASES:
            try:
                ok, detail = case(world)
            except Exception as exc:  # noqa: BLE001
                ok, detail = False, f"exception: {exc}"
            print(f"{'PASS' if ok else 'FAIL'}  {case.__name__}" + ("" if ok else f"  -- {detail}"))
            failures += 0 if ok else 1
    print(f"\n{len(CASES) - failures}/{len(CASES)} passed (scan.sh = {SCAN_SH})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
