---
name: bibliotheque-refresh
description: Refresh the Bibliothèque after a new Notion export. Compares file sizes against MANIFEST.yaml to detect changed/new pages and re-distills only those pages. Run when a new Notion export lands in notion-wiki/export/.
---

# Bibliothèque Refresh

Use this skill when a new Notion export has been dropped into `notion-wiki/export/`.

## What it does

1. Walks the new export, compares file sizes against `notion-wiki/MANIFEST.yaml`
2. Categorizes files as: unchanged | modified | new | deleted
3. Reports the delta to the user
4. Dispatches targeted distillation agents only for modified/new files
5. Updates MANIFEST.yaml

## Steps

### Step 1: Detect changes

Run:
```bash
python3 << 'EOF'
import os, yaml

manifest_path = "documentation/notion-wiki/MANIFEST.yaml"
export_root = "documentation/notion-wiki/export"

with open(manifest_path) as f:
    manifest = yaml.safe_load(f)

manifest_index = {p['notion_path']: p for p in manifest.get('pages', [])}

unchanged, modified, new_files, deleted = [], [], [], []

for root, dirs, files in os.walk(export_root):
    for fname in files:
        if not fname.endswith('.md'):
            continue
        full_path = os.path.join(root, fname)
        rel_path = os.path.relpath(full_path, export_root)
        size = os.path.getsize(full_path)
        
        if rel_path in manifest_index:
            if manifest_index[rel_path]['size_bytes'] != size:
                modified.append((rel_path, size))
            else:
                unchanged.append(rel_path)
        else:
            new_files.append((rel_path, size))

manifest_paths = set(manifest_index.keys())
current_paths = set()
for root, dirs, files in os.walk(export_root):
    for fname in files:
        if fname.endswith('.md'):
            current_paths.add(os.path.relpath(os.path.join(root, fname), export_root))

deleted = manifest_paths - current_paths

print(f"Unchanged: {len(unchanged)}")
print(f"Modified: {len(modified)}")
print(f"New: {len(new_files)}")
print(f"Deleted: {len(deleted)}")
if modified:
    print("\nModified files:")
    for p, s in modified: print(f"  {p} ({s} bytes)")
if new_files:
    print("\nNew files:")
    for p, s in new_files: print(f"  {p} ({s} bytes)")
if deleted:
    print("\nDeleted files (manual review needed):")
    for p in deleted: print(f"  {p}")
EOF
```

### Step 2: Human review

Present the delta report to the user. Ask:
- "Do you want to re-distill the N modified/new pages?"
- "These deleted pages were in the manifest — should I remove them from the Bibliothèque?"

### Step 3: Dispatch targeted agents

For each modified/new file, determine its `classification` from the manifest and dispatch a distillation agent with:
- The specific file(s) to re-distill
- The target bibliotheque page to update
- Instructions to append/replace only the relevant section

### Step 4: Update MANIFEST.yaml

After distillation, update the size_bytes for changed entries and add new entries.

## Notes

- Do not re-distill files that haven't changed
- Deleted files in the export should NOT auto-delete from the Bibliothèque — always ask the user first
- The manifest is the source of truth for what was distilled when
