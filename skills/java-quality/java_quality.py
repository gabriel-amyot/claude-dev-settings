#!/usr/bin/env python3
"""
Java quality, one entry point.

Two engines sit behind this, because neither can do the other's job:

  gate.py       PMD. Stateless, ~1s, runs automatically on every Java edit via
                a PostToolUse hook. Catches raw Object returns, return null,
                complexity, magic literals, javadoc bloat.

  typecheck.py  Eclipse JDT language server. Stateful, ~8s, on demand only.
                Catches what PMD structurally cannot: does not compile, type
                mismatch, undefined method, wrong arity, unresolved import.

Verified on a probe file: PMD found 0, jdtls found 4. Neither is a review.

COMMANDS
    (none) | status        what is on, what it is checking
    off | on               kill switch for the always-on gate
    relax <Rule>           rule reports but stops blocking
    strict <Rule>          rule blocks again
    rules                  every rule, blocking vs advisory
    scope <mode>           changed-lines | whole-file
    threshold <Rule> <prop> <n>
    scan [path]            lint now, change nothing
    compiles <file.java>   typecheck one file  [--rebuild]
    adopt <repo-path>      opt another repo into the gate
    doctor                 end-to-end self test of both engines
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RED, DIM, RESET = "\033[31m", "\033[2m", "\033[0m"


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def usage():
    print(__doc__)
    return 0


def main():
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help", "help"):
        return usage()

    verb = args[0] if args else "status"
    rest = args[1:]

    # Typechecking is a separate process: it is a long-running LSP session and
    # keeping it out of this process avoids inheriting its threads.
    if verb in ("compiles", "compile", "typecheck"):
        if not rest:
            print(f"{RED}Usage: compiles <file.java> [--rebuild]{RESET}", file=sys.stderr)
            return 1
        return subprocess.call([sys.executable, str(HERE / "typecheck.py")] + rest)

    gate = load("gate")
    cfg = gate.load_config()

    routes = {
        "status": gate.cmd_status,
        "on": lambda c, a: gate.cmd_toggle(c, a, True),
        "off": lambda c, a: gate.cmd_toggle(c, a, False),
        "relax": lambda c, a: gate.cmd_advisory(c, a, True),
        "strict": lambda c, a: gate.cmd_advisory(c, a, False),
        "rules": gate.cmd_rules,
        "scope": gate.cmd_scope,
        "threshold": gate.cmd_threshold,
        "scan": gate.cmd_scan,
        "adopt": gate.cmd_adopt,
        "doctor": gate.cmd_doctor,
    }

    if verb not in routes:
        print(f"{RED}Unknown command '{verb}'.{RESET}", file=sys.stderr)
        print(f"{DIM}Try: {', '.join(list(routes) + ['compiles'])}{RESET}", file=sys.stderr)
        return 1

    routes[verb](cfg, rest)

    if verb == "doctor":
        # The gate's doctor covers PMD. Confirm the typecheck engine too,
        # otherwise 'doctor passed' would overstate what was actually verified.
        print()
        tc = load("typecheck")
        jdtls_ok = Path(tc.JDTLS).is_file()
        jdk_ok = (Path(tc.PREFERRED_JDK) / "bin" / "java").is_file()
        lombok = tc.lombok_jar(Path.cwd())
        for label, ok, detail in (
            ("jdtls installed", jdtls_ok, tc.JDTLS),
            ("pinned JDK present", jdk_ok, tc.PREFERRED_JDK),
            ("lombok agent found", lombok is not None,
             str(lombok) if lombok else "MISSING, expect phantom Lombok errors"),
        ):
            mark = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
            print(f"  [{mark}] {label}  {DIM}{detail}{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
