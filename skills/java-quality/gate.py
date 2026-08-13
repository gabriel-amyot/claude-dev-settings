#!/usr/bin/env python3
"""
Control panel CLI for the PMD Java quality gate.

Every knob is edited here rather than by hand, so a typo cannot silently
disable the gate. Writes are validated before they land: a ruleset change is
rejected if PMD refuses to load the result, and the previous version is
restored.

Commands
    status                       what is on, what repos opted in
    on | off                     master switch
    scope <changed-lines|whole-file>
    rules                        active rules, blocking vs advisory
    advisory <Rule>              stop a rule blocking
    block <Rule>                 make a rule block
    threshold <Rule> <prop> <n>  tune a built-in rule threshold
    scan [path]                  run the ruleset now, no editing
    adopt <repo-path>            copy the ruleset into another repo
    doctor                       verify the whole gate end to end
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CONFIG = Path.home() / ".claude" / "pmd-java-gate.json"
HOOK = Path.home() / ".claude" / "hooks" / "pmd-java-gate.py"
SETTINGS = Path.home() / ".claude" / "settings.json"
USER_RULESET = Path(__file__).resolve().parent / "klever-java-rules.xml"

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def load_config():
    if not CONFIG.is_file():
        die(f"No config at {CONFIG}. The gate may not be installed.")
    try:
        return json.loads(CONFIG.read_text())
    except json.JSONDecodeError as exc:
        die(f"Config is not valid JSON: {exc}")


def save_config(cfg):
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")


def die(msg):
    print(f"{RED}{msg}{RESET}", file=sys.stderr)
    sys.exit(1)


def pmd_binary(cfg):
    return cfg.get("pmd_binary", "/opt/homebrew/bin/pmd")


def find_ruleset(cfg, start=None):
    """Repo ruleset wins, user ruleset is the default.

    These are one engineer's standards, not a ratified team standard, so they
    live in personal config rather than in a shared product repo. A repo-level
    file means the team ratified them and CI consumes them, so it takes
    precedence when present.
    """
    rel = cfg.get("ruleset_path", "config/pmd/klever-java-rules.xml")
    root = git_root(start or Path.cwd())
    if root and rel and (root / rel).is_file():
        return root / rel
    if USER_RULESET.is_file():
        return USER_RULESET
    return None


def git_root(path):
    try:
        out = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            return Path(out.stdout.strip())
    except (subprocess.SubprocessError, OSError):
        pass
    return None


def validate_ruleset(cfg, ruleset):
    """True if PMD can actually load it. This is the gate against a dead gate."""
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "Probe.java"
        probe.write_text("public class Probe { void a() {} }\n")
        try:
            out = subprocess.run(
                [pmd_binary(cfg), "check", "-d", str(probe), "-R", str(ruleset),
                 "-f", "text", "--no-cache", "--no-progress"],
                capture_output=True, text=True, timeout=60,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            return False, str(exc)
        if out.returncode not in (0, 4):
            errs = "\n".join(l for l in out.stderr.splitlines()
                             if "[ERROR]" in l or "Cannot" in l or "Unable" in l)
            return False, errs or out.stderr[:600]
    return True, ""


def parse_rules(ruleset):
    """(custom_rules, referenced_rules) by name, in file order."""
    text = ruleset.read_text()
    custom = re.findall(r'<rule\s+name="([^"]+)"', text)
    refs = re.findall(r'<rule\s+ref="[^"]*/([^"/]+)"', text)
    return custom, refs


# ----------------------------------------------------------------- commands

def cmd_status(cfg, args):
    on = cfg.get("enabled", True)
    print(f"{'Gate:':<22}{GREEN + 'ON' + RESET if on else RED + 'OFF' + RESET}")
    print(f"{'Scope:':<22}{cfg.get('scope')}")
    print(f"{'Advisory rules:':<22}{', '.join(cfg.get('advisory_rules', [])) or '(none)'}")
    print(f"{'Timeout:':<22}{cfg.get('timeout_seconds')}s")
    print(f"{'Ruleset path:':<22}{cfg.get('ruleset_path')}")

    ruleset = find_ruleset(cfg)
    if ruleset:
        ok, err = validate_ruleset(cfg, ruleset)
        mark = GREEN + "loads OK" + RESET if ok else RED + "BROKEN" + RESET
        print(f"{'Active ruleset:':<22}{ruleset}  [{mark}]")
        if not ok:
            print(f"{RED}{err}{RESET}")
    else:
        print(f"{'Active ruleset:':<22}{YELLOW}none found{RESET}")

    source = "user config" if ruleset == USER_RULESET else "repo (team-ratified)"
    print(f"{'Rules come from:':<22}{source}")

    print(f"\n{DIM}Applies to: every Java file you edit, from the user ruleset.{RESET}")
    base = Path.home() / "Developer" / "grp-beklever-com"
    rel = cfg.get("ruleset_path")
    found = list(base.glob(f"**/{rel}")) if base.is_dir() else []
    if found:
        print(f"{DIM}Repos with their own ratified ruleset (these override):{RESET}")
        for f in found[:20]:
            print(f"  {f.parent.parent.parent}")
    else:
        print(f"{DIM}No repo has promoted these rules yet. Nothing in CI enforces "
              f"them.{RESET}")


def cmd_toggle(cfg, args, value):
    cfg["enabled"] = value
    save_config(cfg)
    state = GREEN + "ON" + RESET if value else RED + "OFF" + RESET
    print(f"Gate is now {state}.")
    if not value:
        print(f"{DIM}Java edits will no longer be checked. Re-enable with: /pmd on{RESET}")


def cmd_scope(cfg, args):
    if not args or args[0] not in ("changed-lines", "whole-file"):
        die("Usage: scope <changed-lines|whole-file>")
    cfg["scope"] = args[0]
    save_config(cfg)
    print(f"Scope set to {GREEN}{args[0]}{RESET}.")
    if args[0] == "whole-file":
        print(f"{DIM}Every violation in an edited file will now report, including "
              f"pre-existing debt.{RESET}")
    else:
        print(f"{DIM}Only lines your edit touched will report. New files lint whole.{RESET}")


def cmd_rules(cfg, args):
    ruleset = find_ruleset(cfg)
    if not ruleset:
        die("No ruleset found.")
    custom, refs = parse_rules(ruleset)
    advisory = set(cfg.get("advisory_rules", []))
    print(f"{DIM}{ruleset}{RESET}\n")
    print(f"{'RULE':<28}{'SOURCE':<10}EFFECT")
    for name in custom:
        eff = (YELLOW + "advisory" + RESET) if name in advisory else (RED + "blocks" + RESET)
        print(f"{name:<28}{'custom':<10}{eff}")
    for name in refs:
        eff = (YELLOW + "advisory" + RESET) if name in advisory else (RED + "blocks" + RESET)
        print(f"{name:<28}{'built-in':<10}{eff}")


def cmd_advisory(cfg, args, make_advisory):
    if not args:
        die("Usage: advisory <RuleName>   |   block <RuleName>")
    rule = args[0]
    ruleset = find_ruleset(cfg)
    if ruleset:
        custom, refs = parse_rules(ruleset)
        if rule not in custom + refs:
            print(f"{YELLOW}Warning: '{rule}' is not in the ruleset. "
                  f"Setting it anyway.{RESET}")
    lst = cfg.setdefault("advisory_rules", [])
    if make_advisory:
        if rule not in lst:
            lst.append(rule)
        print(f"{rule} is now {YELLOW}advisory{RESET}. It reports but never blocks.")
    else:
        if rule in lst:
            lst.remove(rule)
        print(f"{rule} now {RED}blocks{RESET}.")
    save_config(cfg)


def cmd_threshold(cfg, args):
    if len(args) < 3:
        die("Usage: threshold <RuleName> <propertyName> <value>\n"
            "  e.g. threshold CyclomaticComplexity methodReportLevel 6")
    rule, prop, value = args[0], args[1], args[2]
    ruleset = find_ruleset(cfg)
    if not ruleset:
        die("No ruleset found.")

    text = ruleset.read_text()
    # Narrow to this rule's own block so we cannot edit a neighbour's property.
    pattern = re.compile(
        r'(<rule\s+(?:ref|name)="[^"]*(?:/|\b)' + re.escape(rule) + r'"[^>]*>)(.*?)(</rule>)',
        re.DOTALL)
    match = pattern.search(text)
    if not match:
        die(f"Rule '{rule}' not found in {ruleset}")

    head, body, tail = match.groups()
    prop_re = re.compile(r'(<property\s+name="' + re.escape(prop) + r'"\s+value=")([^"]*)(")')
    if prop_re.search(body):
        old = prop_re.search(body).group(2)
        new_body = prop_re.sub(lambda m: m.group(1) + value + m.group(3), body)
        change = f"{old} -> {value}"
    elif "<properties>" in body:
        new_body = body.replace(
            "<properties>",
            f'<properties>\n      <property name="{prop}" value="{value}"/>', 1)
        change = f"added, = {value}"
    else:
        new_body = body.rstrip() + (
            f'\n    <properties>\n      <property name="{prop}" value="{value}"/>\n'
            f'    </properties>\n  ')
        change = f"added, = {value}"

    backup = ruleset.with_suffix(ruleset.suffix + ".bak")
    shutil.copy(ruleset, backup)
    ruleset.write_text(text[:match.start()] + head + new_body + tail + text[match.end():])

    ok, err = validate_ruleset(cfg, ruleset)
    if not ok:
        shutil.copy(backup, ruleset)
        backup.unlink(missing_ok=True)
        die(f"Change rejected, PMD could not load the result. Ruleset restored.\n{err}")
    backup.unlink(missing_ok=True)
    print(f"{GREEN}{rule}.{prop}{RESET}: {change}")
    print(f"{DIM}Validated, PMD loads the ruleset.{RESET}")


def cmd_scan(cfg, args):
    target = Path(args[0]).expanduser().resolve() if args else Path.cwd()
    ruleset = find_ruleset(cfg, target)
    if not ruleset:
        die("No ruleset found for that path.")
    print(f"{DIM}ruleset: {ruleset}{RESET}\n")
    out = subprocess.run(
        [pmd_binary(cfg), "check", "-d", str(target), "-R", str(ruleset),
         "-f", "json", "--no-cache", "--no-progress"],
        capture_output=True, text=True, timeout=300,
    )
    if out.returncode not in (0, 4):
        die("PMD failed:\n" + out.stderr[:1500])
    try:
        report = json.loads(out.stdout)
    except json.JSONDecodeError:
        die("PMD output was not JSON.")

    advisory = set(cfg.get("advisory_rules", []))
    counts, rows = {}, []
    for fe in report.get("files", []):
        fname = fe.get("filename", "")
        for v in fe.get("violations", []):
            rule = v.get("rule", "?")
            counts[rule] = counts.get(rule, 0) + 1
            rows.append((fname, v.get("beginline"), rule))
    if not rows:
        print(f"{GREEN}Clean. No violations.{RESET}")
        return
    print(f"{'COUNT':<8}{'RULE':<28}EFFECT")
    for rule, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        eff = (YELLOW + "advisory" + RESET) if rule in advisory else (RED + "blocks" + RESET)
        print(f"{n:<8}{rule:<28}{eff}")
    print(f"\n{len(rows)} violation(s) across "
          f"{len({r[0] for r in rows})} file(s).")


def cmd_adopt(cfg, args):
    """Promote personal rules into a shared repo. A deliberate, human decision.

    The gate already runs everywhere from the user-level ruleset. This does not
    switch it on, it publishes the rules to a team repo so CI can enforce them
    for everyone. That changes other people's builds, so it is not something to
    do casually or as part of clearing a phase.
    """
    if not args:
        die("Usage: adopt <path-to-repo>")
    repo = Path(args[0]).expanduser().resolve()
    root = git_root(repo)
    if not root:
        die(f"{repo} is not inside a git repo.")
    if not USER_RULESET.is_file():
        die(f"User ruleset missing at {USER_RULESET}")
    dest = root / cfg.get("ruleset_path")
    if dest.is_file():
        print(f"{YELLOW}{dest} already exists. Not overwriting.{RESET}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(USER_RULESET, dest)
    print(f"{GREEN}Promoted to repo:{RESET} {root.name}")
    print(f"  wrote {dest}")
    print(f"{YELLOW}This publishes your personal standards to a shared repo.{RESET}")
    print(f"{DIM}It only bites the team once CI consumes it (maven-pmd-plugin "
          f"<rulesets>). Get agreement before merging.{RESET}")


def cmd_doctor(cfg, args):
    problems = []

    def check(label, ok, detail=""):
        mark = GREEN + "PASS" + RESET if ok else RED + "FAIL" + RESET
        print(f"  [{mark}] {label}" + (f"  {DIM}{detail}{RESET}" if detail else ""))
        if not ok:
            problems.append(label)

    print("PMD gate doctor\n")
    check("hook script exists", HOOK.is_file(), str(HOOK))
    binary = pmd_binary(cfg)
    check("pmd binary present", Path(binary).is_file() or bool(shutil.which(binary)), binary)

    wired = False
    try:
        s = json.loads(SETTINGS.read_text())
        for m in s.get("hooks", {}).get("PostToolUse", []):
            for h in m.get("hooks", []):
                if "pmd-java-gate" in h.get("command", ""):
                    wired = True
    except (OSError, json.JSONDecodeError):
        pass
    check("registered in settings.json", wired, "PostToolUse Edit|Write")
    check("gate enabled", cfg.get("enabled", True),
          "" if cfg.get("enabled", True) else "enabled:false in config")

    ruleset = find_ruleset(cfg)
    check("ruleset found", ruleset is not None, str(ruleset or ""))
    if ruleset:
        ok, err = validate_ruleset(cfg, ruleset)
        check("ruleset loads in PMD", ok, "" if ok else err.splitlines()[0] if err else "")

    # End-to-end: does the hook actually block on known-bad code?
    if ruleset and HOOK.is_file():
        root = ruleset.parent.parent.parent
        probe = root / "src" / "main" / "java" / "__PmdDoctorProbe.java"
        try:
            probe.parent.mkdir(parents=True, exist_ok=True)
            probe.write_text(
                "public class __PmdDoctorProbe {\n"
                "    Object bad() { return null; }\n}\n")
            res = subprocess.run(
                ["python3", str(HOOK)],
                input=json.dumps({"tool_input": {"file_path": str(probe)}}),
                capture_output=True, text=True, timeout=60)
            check("hook blocks on bad code", res.returncode == 2,
                  f"exit {res.returncode}, expected 2")
        except (OSError, subprocess.SubprocessError) as exc:
            check("hook blocks on bad code", False, str(exc))
        finally:
            probe.unlink(missing_ok=True)

    print()
    if problems:
        print(f"{RED}{len(problems)} problem(s):{RESET} " + ", ".join(problems))
        sys.exit(1)
    print(f"{GREEN}All checks passed. The gate is live and blocking.{RESET}")


COMMANDS = {
    "status": cmd_status,
    "on": lambda c, a: cmd_toggle(c, a, True),
    "off": lambda c, a: cmd_toggle(c, a, False),
    "scope": cmd_scope,
    "rules": cmd_rules,
    "advisory": lambda c, a: cmd_advisory(c, a, True),
    "block": lambda c, a: cmd_advisory(c, a, False),
    "threshold": cmd_threshold,
    "scan": cmd_scan,
    "adopt": cmd_adopt,
    "doctor": cmd_doctor,
}


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, rest = args[0], args[1:]
    if cmd not in COMMANDS:
        die(f"Unknown command '{cmd}'. Try: {', '.join(COMMANDS)}")
    COMMANDS[cmd](load_config(), rest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
