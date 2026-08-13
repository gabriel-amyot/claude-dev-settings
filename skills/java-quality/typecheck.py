#!/usr/bin/env python3
"""
On-demand Java diagnostics via the Eclipse JDT language server.

WHY THIS EXISTS
    PMD parses a file in isolation and matches patterns. It does not know what
    a method returns, whether a symbol resolves, or whether the types line up.
    jdtls runs the real Eclipse compiler against the project's full Maven
    classpath, so it catches the entire class of defect PMD structurally
    cannot: does not compile, wrong type, missing method, bad arity,
    unresolved import, unused private member, unreachable code.

WHY THIS IS ON DEMAND AND NOT A HOOK
    A language server is stateful. It holds a workspace index that goes stale
    when you switch branches or edit pom.xml, and a stale index produces
    confident wrong answers. That is the same failure shape as reasoning about
    the wrong deploy branch. It is tolerable when a human asked a question and
    is reading the answer. It is not tolerable when it silently blocks edits.

    PMD occupies the in-loop slot precisely because it is stateless.

COST
    First run against a repo imports the Maven project and can take 30-90s.
    The workspace index is cached under ~/.cache/jdtls-workspaces/<repo-hash>,
    so later runs are typically 10-20s. There is no way to make a cold JVM
    plus a project import fast. Warm reuse across invocations would need a
    persistent daemon, which is the stateful complexity this deliberately
    avoids for now.

USAGE
    jdtls_check.py <file.java> [--timeout N] [--json] [--rebuild]
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

JDTLS = "/opt/homebrew/bin/jdtls"
# Pin the server JVM. The brew formula defaults to the newest openjdk, and
# JDK 25+ is known to break Lombok and Mockito in these repos.
PREFERRED_JDK = "/Library/Java/JavaVirtualMachines/zulu-21.jdk/Contents/Home"
WORKSPACE_BASE = Path.home() / ".cache" / "jdtls-workspaces"

SEVERITY = {1: "ERROR", 2: "WARN", 3: "INFO", 4: "HINT"}
GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


class LspClient:
    """Minimal LSP client over stdio. Speaks only what jdtls needs to work."""

    def __init__(self, proc, verbose=False):
        self.proc = proc
        self.verbose = verbose
        self._next_id = 1
        self.responses = {}
        self.diagnostics = {}
        self.status = []
        self.lock = threading.Lock()
        self.reader = threading.Thread(target=self._read_loop, daemon=True)
        self.reader.start()

    # ---------------------------------------------------------------- wire

    def _send(self, payload):
        body = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        try:
            self.proc.stdin.write(header + body)
            self.proc.stdin.flush()
        except (BrokenPipeError, ValueError):
            pass

    def request(self, method, params):
        with self.lock:
            rid = self._next_id
            self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        return rid

    def notify(self, method, params):
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def respond(self, rid, result):
        self._send({"jsonrpc": "2.0", "id": rid, "result": result})

    def _read_loop(self):
        stream = self.proc.stdout
        while True:
            length = None
            # Headers, terminated by a blank line.
            while True:
                line = stream.readline()
                if not line:
                    return
                line = line.decode("utf-8", "replace").strip()
                if line.lower().startswith("content-length:"):
                    length = int(line.split(":")[1].strip())
                elif line == "":
                    break
            if length is None:
                continue
            raw = stream.read(length)
            if not raw:
                return
            try:
                msg = json.loads(raw.decode("utf-8", "replace"))
            except json.JSONDecodeError:
                continue
            self._dispatch(msg)

    def _dispatch(self, msg):
        if self.verbose:
            print(f"{DIM}<- {msg.get('method') or 'response ' + str(msg.get('id'))}{RESET}",
                  file=sys.stderr)

        method = msg.get("method")

        # Server -> client requests. jdtls stalls if these go unanswered.
        if method and "id" in msg:
            if method == "workspace/configuration":
                items = msg.get("params", {}).get("items", [])
                self.respond(msg["id"], [{} for _ in items])
            elif method == "window/workDoneProgress/create":
                self.respond(msg["id"], None)
            elif method == "client/registerCapability":
                self.respond(msg["id"], None)
            else:
                self.respond(msg["id"], None)
            return

        if method == "textDocument/publishDiagnostics":
            p = msg.get("params", {})
            self.diagnostics[p.get("uri", "")] = p.get("diagnostics", [])
            return

        if method == "language/status":
            self.status.append(msg.get("params", {}))
            return

        if "id" in msg and method is None:
            self.responses[msg["id"]] = msg
            return

    # ------------------------------------------------------------- helpers

    def wait_for_response(self, rid, timeout):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if rid in self.responses:
                return self.responses[rid]
            if self.proc.poll() is not None:
                return None
            time.sleep(0.05)
        return None

    def wait_for_service_ready(self, timeout):
        """jdtls emits language/status ServiceReady once the project is usable."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            for s in self.status:
                if s.get("type") in ("ServiceReady", "Started"):
                    return True
            if self.proc.poll() is not None:
                return False
            time.sleep(0.2)
        return False


def git_root(path):
    try:
        out = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            return Path(out.stdout.strip())
    except (subprocess.SubprocessError, OSError):
        pass
    return None


def project_root(file_path):
    """Nearest ancestor with a pom.xml, else the git root, else the parent."""
    for parent in file_path.parents:
        if (parent / "pom.xml").is_file():
            return parent
    return git_root(file_path) or file_path.parent


def workspace_for(root, rebuild=False):
    digest = hashlib.sha256(str(root).encode()).hexdigest()[:16]
    ws = WORKSPACE_BASE / f"{root.name}-{digest}"
    if rebuild and ws.exists():
        shutil.rmtree(ws, ignore_errors=True)
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def java_executable():
    candidate = Path(PREFERRED_JDK) / "bin" / "java"
    if candidate.is_file():
        return str(candidate)
    return shutil.which("java") or "java"


def _version_key(path):
    try:
        return tuple(int(p) for p in path.parent.name.split("."))
    except ValueError:
        return (0,)


def lombok_jar(root):
    """Find a lombok jar to load as a javaagent.

    Without this, jdtls reports a wall of phantom errors on any Lombok class:
    '@Slf4j log cannot be resolved', '@RequiredArgsConstructor blank final may
    not have been initialized', '@Getter method is undefined'. The
    java.jdt.ls.lombokSupport setting alone does NOT do this. jdtls does not
    bundle lombok, so the agent must come from the local Maven repository.

    Prefer the version the project declares, so the agent matches what the
    build actually uses.
    """
    base = Path.home() / ".m2" / "repository" / "org" / "projectlombok" / "lombok"
    if not base.is_dir():
        return None
    jars = [j for j in base.glob("*/lombok-*.jar")
            if "sources" not in j.name and "javadoc" not in j.name]
    if not jars:
        return None

    pom = root / "pom.xml"
    if pom.is_file():
        try:
            text = pom.read_text(encoding="utf-8", errors="replace")
            match = re.search(r"<lombok\.version>\s*([0-9.]+)\s*</lombok\.version>", text)
            if match:
                wanted = match.group(1)
                for jar in jars:
                    if jar.parent.name == wanted:
                        return jar
        except OSError:
            pass

    return max(jars, key=_version_key)


def run(file_path, timeout, rebuild, verbose):
    file_path = file_path.expanduser().resolve()
    if not file_path.is_file():
        return None, f"No such file: {file_path}"
    if file_path.suffix != ".java":
        return None, f"Not a Java file: {file_path}"

    root = project_root(file_path)
    ws = workspace_for(root, rebuild)
    fresh = not any(ws.iterdir())

    if not Path(JDTLS).is_file():
        return None, f"jdtls not found at {JDTLS}. Install with: brew install jdtls"

    cmd = [JDTLS, "--java-executable", java_executable(), "-data", str(ws)]
    agent = lombok_jar(root)
    if agent:
        cmd.insert(1, f"--jvm-arg=-javaagent:{agent}")
    elif verbose:
        print(f"{YELLOW}No lombok jar found. Expect phantom errors on Lombok "
              f"classes.{RESET}", file=sys.stderr)
    try:
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL if not verbose else None,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"Could not start jdtls: {exc}"

    client = LspClient(proc, verbose)
    root_uri = root.as_uri()

    init_id = client.request("initialize", {
        "processId": os.getpid(),
        "rootUri": root_uri,
        "workspaceFolders": [{"uri": root_uri, "name": root.name}],
        "capabilities": {
            "textDocument": {
                "publishDiagnostics": {"relatedInformation": True},
                "synchronization": {"didSave": True},
            },
            "workspace": {"configuration": True, "workspaceFolders": True},
            "window": {"workDoneProgress": True},
        },
        "initializationOptions": {
            "settings": {
                "java": {
                    "errors": {"incompleteClasspath": {"severity": "warning"}},
                    "configuration": {
                        "updateBuildConfiguration": "automatic",
                        "runtimes": [
                            {"name": "JavaSE-17",
                             "path": "/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home"},
                            {"name": "JavaSE-21", "path": PREFERRED_JDK, "default": True},
                        ],
                    },
                    "import": {"maven": {"enabled": True}},
                    # Lombok is used across these repos. Without this, every
                    # generated getter reads as an unresolved method.
                    "jdt": {"ls": {"lombokSupport": {"enabled": True}}},
                }
            }
        },
    })

    resp = client.wait_for_response(init_id, timeout=min(timeout, 120))
    if resp is None:
        proc.kill()
        return None, "jdtls did not respond to initialize. It may have crashed."

    client.notify("initialized", {})

    # Project import. Cold workspaces must resolve the whole Maven classpath.
    import_budget = timeout if fresh else min(timeout, 60)
    client.wait_for_service_ready(import_budget)

    uri = file_path.as_uri()
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        proc.kill()
        return None, f"Could not read {file_path}: {exc}"

    client.notify("textDocument/didOpen", {
        "textDocument": {"uri": uri, "languageId": "java", "version": 1, "text": text},
    })

    # Diagnostics arrive asynchronously and can be republished as the classpath
    # resolves. Settle rather than taking the first result, otherwise a cold
    # run reports phantom "cannot be resolved" errors that vanish a second later.
    deadline = time.time() + min(timeout, 90)
    last, stable_since = None, None
    while time.time() < deadline:
        current = client.diagnostics.get(uri)
        if current is not None:
            key = json.dumps(current, sort_keys=True)
            if key == last:
                if stable_since and time.time() - stable_since > 3.0:
                    break
            else:
                last, stable_since = key, time.time()
        if proc.poll() is not None:
            break
        time.sleep(0.3)

    diags = client.diagnostics.get(uri, [])

    try:
        sid = client.request("shutdown", {})
        client.wait_for_response(sid, timeout=5)
        client.notify("exit", {})
        proc.wait(timeout=5)
    except (subprocess.SubprocessError, OSError):
        proc.kill()

    return {"file": str(file_path), "root": str(root), "workspace": str(ws),
            "cold_start": fresh, "diagnostics": diags}, None


def render(result):
    diags = result["diagnostics"]
    rel = result["file"]
    try:
        rel = str(Path(result["file"]).relative_to(result["root"]))
    except ValueError:
        pass

    if not diags:
        print(f"{GREEN}Clean.{RESET} jdtls found no problems in {rel}")
        return 0

    buckets = {}
    for d in diags:
        buckets.setdefault(d.get("severity", 1), []).append(d)

    errors = len(buckets.get(1, []))
    warns = len(buckets.get(2, []))
    head = []
    if errors:
        head.append(f"{RED}{errors} error(s){RESET}")
    if warns:
        head.append(f"{YELLOW}{warns} warning(s){RESET}")
    other = sum(len(v) for k, v in buckets.items() if k not in (1, 2))
    if other:
        head.append(f"{other} info")
    print(f"{rel}: " + ", ".join(head) + "\n")

    for sev in sorted(buckets):
        for d in sorted(buckets[sev], key=lambda x: x["range"]["start"]["line"]):
            line = d["range"]["start"]["line"] + 1
            col = d["range"]["start"]["character"] + 1
            label = SEVERITY.get(sev, "?")
            colour = RED if sev == 1 else (YELLOW if sev == 2 else DIM)
            src = d.get("source", "java")
            print(f"  {colour}{label:<6}{RESET}{rel}:{line}:{col}  {d.get('message','').strip()}"
                  f"  {DIM}[{src}]{RESET}")
    return 1 if errors else 0


def main():
    ap = argparse.ArgumentParser(description="On-demand Java diagnostics via jdtls")
    ap.add_argument("file", type=Path)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--rebuild", action="store_true",
                    help="Discard the cached workspace index first. Use after a "
                         "branch switch or pom.xml change produces stale results.")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    started = time.time()
    result, error = run(args.file, args.timeout, args.rebuild, args.verbose)
    if error:
        print(f"{RED}{error}{RESET}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    code = render(result)
    elapsed = time.time() - started
    note = " (cold start, workspace index built)" if result["cold_start"] else ""
    print(f"\n{DIM}{elapsed:.1f}s{note}{RESET}")
    return code


if __name__ == "__main__":
    sys.exit(main())
