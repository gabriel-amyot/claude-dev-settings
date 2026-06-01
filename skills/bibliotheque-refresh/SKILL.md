---
name: bibliotheque-refresh
description: Refresh the Bibliothèque after a new Notion export. Compares file sizes against MANIFEST.yaml to detect changed/new pages and re-distills only those pages with YAML frontmatter, wikilinks, and alias registration. Run when a new Notion export lands in notion-wiki/export/.
nav:
  bay: know
  when: "Refresh Bibliotheque after new Notion export. Re-distills changed pages."
  when_not: "Processing inbox captures (use /bibliotheque-librarian)."
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

### Step 3: Read SCHEMA.md and ALIASES.md

Before dispatching agents, read the wiki schema and existing aliases:
```
documentation/bibliotheque/SCHEMA.md    ← page types, frontmatter spec
documentation/bibliotheque/ALIASES.md   ← existing alias map
```

### Step 4: Dispatch targeted agents

For each modified/new file, determine its `classification` from the manifest and dispatch a distillation agent with:
- The specific file(s) to re-distill
- The target bibliotheque page to update
- Instructions to append/replace only the relevant section
- **Wiki enrichment instructions:**
  - Add YAML frontmatter per SCHEMA.md (title, type, created, updated, tags, aliases, related)
  - Add 3-5 `[[wikilinks]]` in the body text linking to related pages (check ALIASES.md for canonical names)
  - For dated filenames, include a semantic alias in the `aliases:` frontmatter field

### Step 5: Update ALIASES.md

For each re-distilled page with a dated filename, add an alias entry to ALIASES.md if one doesn't already exist.

### Step 6: Update LOG.md

Append a batch entry:
```markdown
## {YYYY-MM-DD}

- **REFRESH** — Re-distilled N modified pages, N new pages from Notion export
- **ALIAS** — Added N new aliases
```

### Step 7: Update MANIFEST.yaml

After distillation, update the size_bytes for changed entries and add new entries.

## Notes

- Do not re-distill files that haven't changed
- Deleted files in the export should NOT auto-delete from the Bibliothèque — always ask the user first
- The manifest is the source of truth for what was distilled when
- Every re-distilled page must have frontmatter and wikilinks per SCHEMA.md conventions
- Cross-wiki links use `[[wiki-id::page-stem]]` syntax (see WIKI_REGISTRY.yaml for valid wiki IDs)
