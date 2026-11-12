#!/usr/bin/env python3
"""Select and render migrated BMAD resources without loading unrelated bodies."""
import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "runtime"


def registry():
    return json.loads((ROOT / "registry.json").read_text())


def resource(value, project):
    """Resolve framework assets centrally, but prefer active-project config."""
    project = project.resolve()
    value = value.replace("{project-root}", str(project))
    if "/_bmad/" in value:
        value = value.split("/_bmad/", 1)[1]
    elif value.startswith("_bmad/"):
        value = value[len("_bmad/"):]
    value = registry().get("resource_aliases", {}).get(value, value)
    expanded = Path(value).expanduser()
    if expanded.is_absolute():
        resolved = expanded.resolve()
        try:
            resolved.relative_to(ROOT)
        except ValueError:
            raise ValueError("Resource is outside the shared BMAD payload")
        if resolved.is_relative_to(RUNTIME) and resolved.name == "config.yaml":
            return resource(str(resolved.relative_to(RUNTIME)), project)
        return resolved
    if ".." in expanded.parts:
        raise ValueError("Parent traversal is not a BMAD resource path")
    if value.endswith("/config.yaml"):
        local = project / "_bmad" / value
        if local.is_file():
            resolved = local.resolve()
            if not resolved.is_relative_to(project) and not resolved.is_relative_to(ROOT):
                raise ValueError("Project config links outside the project and shared runtime")
            return resolved
    path = (RUNTIME / expanded).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Resource escapes the shared BMAD payload")
    return path


def select(name):
    key = name.strip().lower()
    for row in registry()["personas"]:
        if key in [row["id"].lower(), row["name"].lower()] + row.get("aliases", []):
            if row["status"] != "available":
                raise ValueError(row["name"] + " unavailable: " + row["reason"])
            path = (ROOT / row["path"]).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file():
                raise ValueError("Persona source is missing: " + row["id"])
            return row, path
    raise ValueError("Unknown BMAD role: " + name + ". Use list; do not invent a replacement.")


def render(path, project):
    project = project.resolve()
    text = path.read_text()
    # Keep recovered source bytes intact while repairing known legacy resource names.
    for old, new in registry().get("resource_aliases", {}).items():
        resolved = str(resource(new, project))
        text = text.replace("{project-root}/_bmad/" + old, resolved)
        text = text.replace("_bmad/" + old, resolved)
    # Resolve configuration before the generic framework prefix, preserving local overrides.
    text = re.sub(r"\{project-root\}/_bmad/([\w-]+/config\.yaml)",
                  lambda m: str(resource(m.group(1), project)), text)
    text = text.replace("{project-root}/_bmad/", str(RUNTIME) + "/")
    text = text.replace("{project-root}", str(project))
    text = text.replace("{project-name}", project.name)
    if path.name == "agent-manifest.csv":
        rows = list(csv.DictReader(io.StringIO(text)))
        fields = list(rows[0])
        for row in rows:
            row["path"] = str(resource(row["path"], project))
        known = {row["name"] for row in rows}
        for row in registry()["personas"]:
            if row["status"] == "available" and row["id"] not in known:
                rows.append({"name": row["id"], "displayName": row["name"],
                             "title": row["role"], "role": row["role"], "module": "custom",
                             "path": str(ROOT / row["path"]),
                             "identity": "Read the complete selected custom persona before adoption."})
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        text = out.getvalue()
    return text


def check():
    errors = []
    for row in registry()["personas"]:
        if row["status"] == "available":
            try:
                select(row["id"])
            except ValueError as exc:
                errors.append(str(exc))
    for path in RUNTIME.rglob("*"):
        if path.is_symlink() and not path.exists():
            errors.append("Broken runtime link: " + str(path.relative_to(ROOT)))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List metadata only, without reading persona bodies")
    sub.add_parser("check", help="Validate source availability without activating roles")
    for command in ["resolve", "agent", "read"]:
        p = sub.add_parser(command)
        p.add_argument("name")
    p = sub.add_parser("command", help="Resolve one explicit legacy command and its workflow engine")
    p.add_argument("name")
    p = sub.add_parser("workflows", help="Filter workflow metadata, without reading workflows")
    p.add_argument("query", nargs="?", default="")
    args = parser.parse_args()
    project = args.project_root.expanduser().resolve()
    if not project.is_dir():
        parser.error("Project root does not exist")
    try:
        if args.command == "list":
            rows = [{k: r[k] for k in ["id", "name", "role", "status"]}
                    for r in registry()["personas"]]
            print(json.dumps(rows, indent=2))
        elif args.command == "check":
            errors = check()
            print(json.dumps({"ok": not errors, "errors": errors,
                              "runtime": str(RUNTIME), "project_root": str(project)}, indent=2))
            return bool(errors)
        elif args.command in ["resolve", "agent"]:
            row, path = select(args.name)
            if args.command == "resolve":
                print(json.dumps({**row, "source": str(path), "runtime_root": str(RUNTIME),
                                  "project_root": str(project),
                                  "config": str(resource(row.get("module", "bmm") + "/config.yaml", project))}, indent=2))
            else:
                print(render(path, project), end="")
        elif args.command == "command":
            name = args.name.removeprefix("source-command-").lstrip("/$")
            commands = registry().get("commands", {})
            if name not in commands:
                raise ValueError("Unknown legacy BMAD command: " + name)
            row = commands[name]
            if row["kind"] == "agent":
                select(row["agent"])
            print(json.dumps(row, indent=2))
        elif args.command == "read":
            path = resource(args.name, project)
            if not path.is_file():
                raise ValueError("BMAD resource is unavailable: " + args.name)
            print(render(path, project), end="")
        elif args.command == "workflows":
            query = args.query.lower()
            with (RUNTIME / "_config/workflow-manifest.csv").open() as f:
                rows = [r for r in csv.DictReader(f) if query in (r.get("name", "") + " " + r.get("description", "")).lower()]
            print(json.dumps(rows, indent=2))
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
