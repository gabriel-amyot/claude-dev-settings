#!/usr/bin/env python3
"""Mechanical no-code-change gate for the tech-doc-review-flow.

Asserts that every .py file changed on the branch differs from the base ref by
comments and docstrings ONLY, and that no .py file outside the allowed list
changed at all. Comments never reach the AST; docstrings are stripped before
comparison. Any executable-code drift fails the run.

Usage:
    python3 ast-guard.py --repo <worktree> --base <ref> [--allow f1.py f2.py ...]

Exit 0: no executable-code drift. Exit 1: drift or disallowed file. Exit 2: usage/error.
"""

import argparse
import ast
import subprocess
import sys

DEFAULT_ALLOWED = [
    "src/ttd_trading_mcp/documents.py",
    "src/ttd_trading_mcp/bid_safety.py",
    "src/ttd_trading_mcp/discovery.py",
    "src/ttd_trading_mcp/server.py",
]


def strip_docstrings(tree: ast.AST) -> ast.AST:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                node.body = body[1:]
    return tree


def normalised_dump(source: str, label: str) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        print(f"FAIL {label}: does not parse: {exc}")
        sys.exit(1)
    return ast.dump(strip_docstrings(tree), include_attributes=False)


def git(repo: str, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"ERROR git {' '.join(args)}: {result.stderr.strip()}")
        sys.exit(2)
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--allow", nargs="*", default=DEFAULT_ALLOWED)
    args = parser.parse_args()

    changed = [
        line
        for line in git(args.repo, "diff", "--name-only", args.base, "--", "*.py").splitlines()
        if line.strip()
    ]

    failures = []
    for path in changed:
        if path not in args.allow:
            failures.append(f"{path}: .py file outside the allowed list changed")
            continue
        base_source = git(args.repo, "show", f"{args.base}:{path}")
        try:
            with open(f"{args.repo}/{path}", encoding="utf-8") as handle:
                work_source = handle.read()
        except FileNotFoundError:
            failures.append(f"{path}: deleted on branch")
            continue
        if normalised_dump(base_source, f"{path}@{args.base}") != normalised_dump(
            work_source, f"{path}@worktree"
        ):
            failures.append(f"{path}: executable code differs from {args.base}")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        sys.exit(1)

    print(f"OK ast-guard: {len(changed)} changed .py file(s), zero executable-code drift vs {args.base}")


if __name__ == "__main__":
    main()
