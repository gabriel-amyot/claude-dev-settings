#!/usr/bin/env python3
"""Archive Ticket CLI for Claude Code - intelligently archive tickets with artifact promotion"""
import os
import sys
import json
import shutil
import re
from pathlib import Path
from datetime import datetime


def find_project_root(start_path=None):
    """Find project-management directory by walking up from current directory"""
    current = Path(start_path or os.getcwd()).resolve()

    while current != current.parent:
        pm_path = current / "project-management"
        if pm_path.exists() and pm_path.is_dir():
            return pm_path
        current = current.parent

    return None


def read_claude_md(pm_root):
    """Read CLAUDE.md or fall back to GEMINI.md for context"""
    claude_md = pm_root / "CLAUDE.md"
    gemini_md = pm_root / "GEMINI.md"

    if claude_md.exists():
        return claude_md.read_text()
    elif gemini_md.exists():
        return gemini_md.read_text()
    return None


def find_ticket_path(pm_root, ticket_id):
    """Find ticket path in project-management structure"""
    # Try common patterns
    patterns = [
        pm_root / "tickets" / "MVP-epic" / ticket_id,
        pm_root / "tickets" / ticket_id,
        pm_root / ticket_id
    ]

    for path in patterns:
        if path.exists() and path.is_dir():
            return path

    return None


def scan_artifacts(ticket_path):
    """Scan for ADRs, contracts, and implementation plan"""
    artifacts = {
        "adrs": [],
        "contracts": [],
        "implementation_plan": None,
        "meeting_notes": []
    }

    # Scan for ADRs
    adr_dir = ticket_path / "architecture" / "adr"
    if adr_dir.exists():
        for adr_file in adr_dir.glob("*.md"):
            artifacts["adrs"].append(adr_file)

    # Scan for contracts
    contracts_dir = ticket_path / "architecture" / "contracts"
    if contracts_dir.exists():
        for contract_file in contracts_dir.glob("*"):
            if contract_file.is_file():
                artifacts["contracts"].append(contract_file)

    # Check for implementation plan
    impl_plan = ticket_path / f"{ticket_path.name}-IMPLEMENTATION_PLAN.md"
    if not impl_plan.exists():
        # Try without prefix
        impl_plan = ticket_path / "IMPLEMENTATION_PLAN.md"

    if impl_plan.exists():
        artifacts["implementation_plan"] = impl_plan

    # Count meeting notes
    meeting_notes_dir = ticket_path / "meeting_notes"
    if meeting_notes_dir.exists():
        artifacts["meeting_notes"] = list(meeting_notes_dir.glob("*.md"))

    return artifacts


def get_next_adr_number(global_adr_dir):
    """Get next available ADR number"""
    if not global_adr_dir.exists():
        return 1

    max_num = 0
    for adr_file in global_adr_dir.glob("*.md"):
        match = re.match(r"(\d+)-", adr_file.name)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)

    return max_num + 1


def check_adr_conflicts(artifacts, global_adr_dir):
    """Check for ADR numbering conflicts"""
    conflicts = []

    for adr_path in artifacts["adrs"]:
        match = re.match(r"(\d+)-(.+)", adr_path.name)
        if match:
            num, title = match.groups()
            global_adr = global_adr_dir / adr_path.name
            if global_adr.exists():
                conflicts.append({
                    "file": adr_path.name,
                    "issue": "File already exists in global ADRs",
                    "suggestion": f"Will renumber to {get_next_adr_number(global_adr_dir):04d}-{title}"
                })

    return conflicts


def analyze_artifacts(pm_root, artifacts):
    """Analyze artifacts and check for conflicts"""
    global_adr_dir = pm_root / "documentation" / "architecture" / "adr"
    global_contracts_dir = pm_root / "documentation" / "architecture" / "contracts"

    analysis = {
        "adr_conflicts": check_adr_conflicts(artifacts, global_adr_dir),
        "new_contracts": [],
        "modified_contracts": [],
        "tasks_complete": None
    }

    # Check contracts
    for contract_path in artifacts["contracts"]:
        global_contract = global_contracts_dir / contract_path.name
        if global_contract.exists():
            analysis["modified_contracts"].append(contract_path.name)
        else:
            analysis["new_contracts"].append(contract_path.name)

    # Check implementation plan for open tasks
    if artifacts["implementation_plan"]:
        content = artifacts["implementation_plan"].read_text()
        # Simple check for common "not done" markers
        if any(marker in content.lower() for marker in ["[ ]", "todo", "in progress", "blocked"]):
            analysis["tasks_complete"] = False
        else:
            analysis["tasks_complete"] = True

    return analysis


def promote_artifacts(pm_root, artifacts, analysis, dry_run=False):
    """Promote artifacts to global documentation"""
    global_adr_dir = pm_root / "documentation" / "architecture" / "adr"
    global_contracts_dir = pm_root / "documentation" / "architecture" / "contracts"

    global_adr_dir.mkdir(parents=True, exist_ok=True)
    global_contracts_dir.mkdir(parents=True, exist_ok=True)

    promoted = {"adrs": [], "contracts": []}

    # Promote ADRs
    for adr_path in artifacts["adrs"]:
        # Check if renumbering needed
        needs_renumber = any(c["file"] == adr_path.name for c in analysis["adr_conflicts"])

        if needs_renumber:
            match = re.match(r"(\d+)-(.+)", adr_path.name)
            if match:
                _, title = match.groups()
                new_num = get_next_adr_number(global_adr_dir)
                dest_name = f"{new_num:04d}-{title}"
            else:
                dest_name = adr_path.name
        else:
            dest_name = adr_path.name

        dest_path = global_adr_dir / dest_name

        if not dry_run:
            shutil.copy2(adr_path, dest_path)

        promoted["adrs"].append({
            "source": str(adr_path),
            "dest": str(dest_path),
            "renumbered": needs_renumber
        })

    # Promote contracts
    for contract_path in artifacts["contracts"]:
        dest_path = global_contracts_dir / contract_path.name

        if not dry_run:
            # For modified contracts, we just copy (Claude will handle intelligent merge)
            shutil.copy2(contract_path, dest_path)

        promoted["contracts"].append({
            "source": str(contract_path),
            "dest": str(dest_path),
            "modified": contract_path.name in analysis["modified_contracts"]
        })

    return promoted


def archive_ticket(pm_root, ticket_path, dry_run=False):
    """Move ticket to archive with timestamp"""
    archive_dir = pm_root / "tickets" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d")
    dest_path = archive_dir / f"{ticket_path.name}-{timestamp}"

    if dest_path.exists():
        # Add time if same date archive exists
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dest_path = archive_dir / f"{ticket_path.name}-{timestamp}"

    if not dry_run:
        shutil.move(str(ticket_path), str(dest_path))

    return str(dest_path)


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: archive_skill.py <command> [options]"}))
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "scan":
            # Scan a ticket and report what would be archived
            if len(sys.argv) < 3:
                print(json.dumps({"error": "scan requires ticket ID"}))
                sys.exit(1)

            ticket_id = sys.argv[2]
            pm_root = find_project_root()

            if not pm_root:
                print(json.dumps({"error": "Could not find project-management directory"}))
                sys.exit(1)

            ticket_path = find_ticket_path(pm_root, ticket_id)
            if not ticket_path:
                print(json.dumps({"error": f"Could not find ticket {ticket_id}"}))
                sys.exit(1)

            artifacts = scan_artifacts(ticket_path)
            analysis = analyze_artifacts(pm_root, artifacts)

            result = {
                "ticket_id": ticket_id,
                "ticket_path": str(ticket_path),
                "artifacts": {
                    "adrs": [str(p) for p in artifacts["adrs"]],
                    "contracts": [str(p) for p in artifacts["contracts"]],
                    "implementation_plan": str(artifacts["implementation_plan"]) if artifacts["implementation_plan"] else None,
                    "meeting_notes_count": len(artifacts["meeting_notes"])
                },
                "analysis": analysis
            }

            print(json.dumps(result, indent=2))

        elif command == "archive":
            # Actually perform the archive operation
            if len(sys.argv) < 3:
                print(json.dumps({"error": "archive requires ticket ID"}))
                sys.exit(1)

            ticket_id = sys.argv[2]
            dry_run = "--dry-run" in sys.argv

            pm_root = find_project_root()
            if not pm_root:
                print(json.dumps({"error": "Could not find project-management directory"}))
                sys.exit(1)

            ticket_path = find_ticket_path(pm_root, ticket_id)
            if not ticket_path:
                print(json.dumps({"error": f"Could not find ticket {ticket_id}"}))
                sys.exit(1)

            artifacts = scan_artifacts(ticket_path)
            analysis = analyze_artifacts(pm_root, artifacts)
            promoted = promote_artifacts(pm_root, artifacts, analysis, dry_run=dry_run)
            archive_path = archive_ticket(pm_root, ticket_path, dry_run=dry_run)

            result = {
                "success": True,
                "ticket_id": ticket_id,
                "promoted": promoted,
                "archived_to": archive_path,
                "dry_run": dry_run
            }

            print(json.dumps(result, indent=2))

        else:
            print(json.dumps({"error": f"Unknown command: {command}"}))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
