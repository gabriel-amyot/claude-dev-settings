#!/usr/bin/env python3
"""
Status Index Skill - Generate or refresh STATUS_SNAPSHOT.yaml for tickets and epics.

Usage: status_index.py <ticket-path> [--dry-run] [--push-jira]
Example: status_index.py SPV-3/SPV-8
         status_index.py SPV-3 --dry-run
         status_index.py SPV-3 --push-jira
"""

import sys
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
import subprocess
import yaml


def get_project_management_root() -> Path:
    """Find project-management root directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / "project-management").exists():
            return current / "project-management"
        if (current.name == "project-management"):
            return current
        current = current.parent

    # Fallback to supervisr-ai structure
    home = Path.home()
    supervisr_pm = home / "Developer" / "supervisr-ai" / "project-management"
    if supervisr_pm.exists():
        return supervisr_pm

    raise RuntimeError("Cannot find project-management directory")


def resolve_ticket_path(ticket_path: str) -> Path:
    """Resolve ticket path relative to tickets directory."""
    pm_root = get_project_management_root()
    tickets_dir = pm_root / "tickets"

    resolved = tickets_dir / ticket_path
    if not resolved.exists():
        raise RuntimeError(f"Ticket path not found: {resolved}")

    return resolved


def is_leaf_ticket(ticket_path: Path) -> bool:
    """Check if ticket is a leaf (no sub-tickets) or parent (has sub-tickets)."""
    for item in ticket_path.iterdir():
        if item.is_dir() and re.match(r'^[A-Z]+-\d+$', item.name):
            return False
    return True


def read_ac_yaml(ticket_path: Path) -> Tuple[Optional[Dict[str, Any]]]:
    """Read ac.yaml and return the full data structure."""
    ac_file = ticket_path / "jira" / "ac.yaml"

    if not ac_file.exists():
        return None

    try:
        with open(ac_file, 'r') as f:
            data = yaml.safe_load(f) or {}
        return data
    except Exception as e:
        print(f"Warning: Error reading {ac_file}: {e}", file=sys.stderr)
        return None


def read_readme(ticket_path: Path) -> Optional[str]:
    """Read title from README.md."""
    readme = ticket_path / "README.md"
    if not readme.exists():
        return None

    try:
        with open(readme, 'r') as f:
            first_line = f.readline().strip()
            # Extract title from markdown h1
            if first_line.startswith('#'):
                return first_line.lstrip('#').strip()
    except:
        pass

    return None


def read_existing_snapshot(ticket_path: Path) -> Optional[Dict[str, Any]]:
    """Read existing STATUS_SNAPSHOT.yaml if present."""
    snapshot_file = ticket_path / "STATUS_SNAPSHOT.yaml"
    if not snapshot_file.exists():
        return None

    try:
        with open(snapshot_file, 'r') as f:
            return yaml.safe_load(f) or {}
    except:
        return None


def calculate_completion_from_ac(ac_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """Calculate completion percentage from acceptance criteria."""
    criteria = ac_data.get('criteria', [])

    if not criteria:
        return 0.0, {
            'total': 0,
            'done': 0,
            'in_progress': 0,
            'pending_validation': 0,
            'not_started': 0,
            'blocked': 0,
            'completed_points': 0,
            'total_points': 0
        }

    status_counts = {
        'done': 0,
        'in_progress': 0,
        'pending_validation': 0,
        'not_started': 0,
        'blocked': 0
    }

    completed_points = 0
    total_points = 0

    for item in criteria:
        if not isinstance(item, dict):
            continue

        status = item.get('status', 'not_started')
        points = item.get('points', 1)

        status_counts[status] = status_counts.get(status, 0) + 1
        total_points += points

        if status == 'done':
            completed_points += points

    completion = (completed_points / total_points * 100) if total_points > 0 else 0

    summary = {
        'total': len(criteria),
        'done': status_counts.get('done', 0),
        'in_progress': status_counts.get('in_progress', 0),
        'pending_validation': status_counts.get('pending_validation', 0),
        'not_started': status_counts.get('not_started', 0),
        'blocked': status_counts.get('blocked', 0),
        'completed_points': completed_points,
        'total_points': total_points
    }

    return completion, summary


def get_status_from_completion(completion: float) -> str:
    """Derive status from completion percentage."""
    if completion >= 100:
        return 'done'
    elif completion > 0:
        return 'in_progress'
    else:
        return 'not_started'


def extract_blockers(criteria: List[Dict[str, Any]]) -> Optional[List[str]]:
    """Extract blockers from criteria marked as blocked."""
    blockers = []

    for item in criteria:
        if not isinstance(item, dict):
            continue

        status = item.get('status', '')
        if status == 'blocked':
            ac_id = item.get('id', '')
            description = item.get('description', '')
            blocker_msg = item.get('blocker', '')

            if blocker_msg:
                blockers.append(f"{ac_id}: {blocker_msg}")
            else:
                blockers.append(f"{ac_id}: {description} (blocked)")

    return blockers if blockers else None


def index_leaf_ticket(ticket_path: Path, ticket_id: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
    """Index a leaf ticket and return snapshot data."""
    ac_data = read_ac_yaml(ticket_path)

    # Default values
    title = read_readme(ticket_path) or ticket_id
    story_points = 1
    assignee = None
    completion = 0.0
    ac_summary = None
    ac_breakdown = None
    blockers = None

    if ac_data:
        story_points = ac_data.get('story_points', 1)
        title = ac_data.get('title', title)
        assignee = ac_data.get('assignee')

        criteria = ac_data.get('criteria', [])
        completion, ac_summary = calculate_completion_from_ac(ac_data)
        blockers = extract_blockers(criteria)

        # Create ac_breakdown matching the existing format
        ac_breakdown = []
        for item in criteria:
            breakdown_item = {
                'id': item.get('id'),
                'description': item.get('description'),
                'points': item.get('points', 1),
                'status': item.get('status', 'not_started')
            }
            if 'validated' in item:
                breakdown_item['validated'] = item['validated']
            if 'blocker' in item:
                breakdown_item['blocker'] = item['blocker']
            ac_breakdown.append(breakdown_item)

    status = get_status_from_completion(completion)

    snapshot = {
        'ticket': ticket_id
    }

    if parent_id:
        snapshot['parent'] = parent_id

    snapshot.update({
        'title': title,
        'status': status,
    })

    if assignee:
        snapshot['assignee'] = assignee

    snapshot['story_points'] = story_points
    snapshot['completion'] = round(completion, 1)
    snapshot['last_indexed'] = datetime.now(timezone.utc).isoformat()

    if ac_summary:
        snapshot['ac_summary'] = ac_summary

    if ac_breakdown:
        snapshot['ac_breakdown'] = ac_breakdown

    # Preserve git_state from existing snapshot if present
    existing = read_existing_snapshot(ticket_path)
    if existing and 'git_state' in existing:
        snapshot['git_state'] = existing['git_state']

    if blockers:
        snapshot['blockers'] = blockers

    if existing and 'notes' in existing:
        snapshot['notes'] = existing['notes']

    return snapshot


def index_epic(ticket_path: Path, ticket_id: str) -> Tuple[Dict[str, Any], List[Tuple[str, Dict[str, Any]]]]:
    """Index an epic and all its sub-tickets recursively (bottom-up)."""
    sub_snapshots = []

    # First, recursively index all sub-tickets
    for item in sorted(ticket_path.iterdir()):
        if not item.is_dir() or not re.match(r'^[A-Z]+-\d+$', item.name):
            continue

        sub_id = item.name
        if is_leaf_ticket(item):
            sub_snapshot = index_leaf_ticket(item, sub_id, parent_id=ticket_id)
            sub_snapshots.append((sub_id, sub_snapshot))
        else:
            # Recursively index nested parent
            nested_epic, nested_leaves = index_epic(item, sub_id)
            sub_snapshots.extend(nested_leaves)

    # Calculate epic-level weighted completion
    direct_children = [snap for _, snap in sub_snapshots if snap.get('parent') == ticket_id]

    total_sp = sum(snap.get('story_points', 1) for snap in direct_children)
    if total_sp > 0 and direct_children:
        weighted_sum = sum(snap.get('completion', 0) * snap.get('story_points', 1) for snap in direct_children)
        completion = weighted_sum / total_sp
    else:
        completion = 0

    # Collect critical blockers from children
    critical_blockers_set = set()
    for snap in direct_children:
        if snap.get('blockers'):
            for blocker in snap['blockers']:
                if isinstance(blocker, str):
                    critical_blockers_set.add(blocker)

    critical_blockers = sorted(list(critical_blockers_set)) if critical_blockers_set else None

    title = read_readme(ticket_path) or ticket_id

    # Create sub_tickets section
    sub_tickets_dict = {}
    for snap in direct_children:
        sub_id = snap['ticket']
        blocker = None
        if snap.get('blockers') and isinstance(snap['blockers'], list) and len(snap['blockers']) > 0:
            blocker = snap['blockers'][0]

        sub_tickets_dict[sub_id] = {
            'title': snap.get('title'),
            'status': snap.get('status'),
            'completion': snap.get('completion'),
            'story_points': snap.get('story_points'),
            'snapshot': f"./{sub_id}/STATUS_SNAPSHOT.yaml"
        }
        if blocker:
            sub_tickets_dict[sub_id]['blocker'] = blocker

    epic = {
        'epic': ticket_id,
        'title': title,
        'completion': round(completion, 1),
        'last_indexed': datetime.now(timezone.utc).isoformat(),
        'sub_tickets': sub_tickets_dict
    }

    if critical_blockers:
        epic['critical_blockers'] = critical_blockers

    # Preserve notes from existing snapshot
    existing = read_existing_snapshot(ticket_path)
    if existing and 'notes' in existing:
        epic['notes'] = existing['notes']

    return epic, sub_snapshots


def write_yaml(data: Dict[str, Any], output_file: Path, dry_run: bool = False) -> None:
    """Write snapshot data to YAML file."""
    content = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)

    if dry_run:
        print(f"\n--- DRY RUN: {output_file} ---")
        print(content)
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(content)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: status_index.py <ticket-path> [--dry-run] [--push-jira]")
        print("Example: status_index.py SPV-3")
        sys.exit(1)

    ticket_path_str = sys.argv[1]
    dry_run = '--dry-run' in sys.argv
    push_jira = '--push-jira' in sys.argv

    try:
        ticket_path = resolve_ticket_path(ticket_path_str)
        ticket_id = ticket_path.name
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if is_leaf_ticket(ticket_path):
            # Index single leaf ticket
            parent_id = ticket_path.parent.name if ticket_path.parent.name != 'tickets' else None
            snapshot = index_leaf_ticket(ticket_path, ticket_id, parent_id=parent_id)

            snapshot_file = ticket_path / "STATUS_SNAPSHOT.yaml"
            write_yaml(snapshot, snapshot_file, dry_run=dry_run)

            if not dry_run:
                print(f"Indexed {ticket_id}: completion={snapshot.get('completion', 0)}%")

            if push_jira:
                # TODO: Implement Jira posting
                print(f"Note: --push-jira not yet implemented")
        else:
            # Index epic recursively
            epic, all_snapshots = index_epic(ticket_path, ticket_id)

            # Write all leaf/child snapshots
            for sub_id, snapshot in all_snapshots:
                sub_path = ticket_path / sub_id
                if sub_path.exists() and is_leaf_ticket(sub_path):
                    snapshot_file = sub_path / "STATUS_SNAPSHOT.yaml"
                    write_yaml(snapshot, snapshot_file, dry_run=dry_run)

                    if not dry_run:
                        print(f"Indexed {sub_id}: completion={snapshot.get('completion', 0)}%")

            # Write epic snapshot
            epic_file = ticket_path / "STATUS_SNAPSHOT.yaml"
            write_yaml(epic, epic_file, dry_run=dry_run)

            if not dry_run:
                print(f"Indexed epic {ticket_id}: completion={epic.get('completion', 0)}%")

            if push_jira:
                # TODO: Implement Jira posting
                print(f"Note: --push-jira not yet implemented")

        if dry_run:
            print("\nDRY RUN — no files written")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
