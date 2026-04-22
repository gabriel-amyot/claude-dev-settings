---
name: index-context
description: "Recursively generate or update INDEX.md files. Supports --scope architecture (ADRs, design docs) or --scope specs (specifications). Default: full recursive. Use after creating or modifying documents in documentation/ or agent-os/ folders. Input: folder path + optional --scope. Returns: created/updated INDEX.md files."
---

# Index Folder

Recursively walks a folder tree and creates/updates INDEX.md files for progressive disclosure.

**Usage:** `/index-context <PATH> [--dry-run] [--depth <N>] [--scope <architecture|specs>]`

**Examples:**
```
/index-context tickets/SPV-3                    # Index SPV-3 and all subfolders
/index-context documentation/                   # Index the docs tree
/index-context .                                # Index from current directory
/index-context tickets/ --depth 1              # Only top-level ticket folders
/index-context tickets/SPV-66 --dry-run        # Preview what would be created
/index-context agent-os/ --scope architecture  # Index only ADRs and design docs
/index-context agent-os/ --scope specs         # Index only specifications and contracts
```

## Arguments

- `<PATH>`: Required. Root folder to index. Relative to cwd or absolute.
- `--dry-run`: Optional. List folders that need indexes without creating them.
- `--depth <N>`: Optional. Max recursion depth. Default: unlimited.
- `--scope <architecture|specs>`: Optional. Restrict indexing to a specific domain. Default: full recursive.

## Scope Modes

### `--scope architecture`
Focus on architecture documentation: ADRs, system diagrams, design docs, subsystem patterns.

- Targets: `agent-os/specs/architecture/` and nested subdirectories (especially `decisions/`)
- Output format: `index.yml` (YAML, not INDEX.md) with `type`, `status`, and `supersedes` fields for ADRs
- ADR entries include: number extracted from filename, status from `## Status` section, `supersedes` if applicable
- Sorts ADR entries by ADR number, not alphabetically
- Skips directories with fewer than 2 `.md` files

**index.yml format for architecture:**
```yaml
# Architecture Index - [Subsection Name]
#
# Progressive disclosure entry point for architecture documentation.

file-name-without-extension:
  description: One-line description here
  type: architecture-doc  # or: adr, diagram, pattern, subsystem
  status: Accepted        # ADRs only
  file: agent-os/specs/architecture/[subsection]/file-name.md
```

### `--scope specs`
Focus on specifications: API contracts, architecture docs, integration requirements.

- Targets: `agent-os/specs/` full tree (api-contracts + architecture + any nested categories)
- Output format: `index.yml` (YAML) with minimal one-line descriptions
- Creates a root `agent-os/specs/index.yml` mapping top-level categories
- Alphabetizes entries by filename
- Skips directories with fewer than 2 `.md` files

**index.yml format for specs:**
```yaml
# Specs Index - [Directory Name]
#
# Progressive disclosure — load only the specs you need.

file-name-without-extension:
  description: One-line description here
  file: relative/path/from/repo-root.md
```

### No scope (default)
Full recursive indexing across the given path. Produces `INDEX.md` files (Markdown format) suitable for any project, ticket tree, library, or knowledge base.

## Rules (default full-recursive mode)

Three rules govern all indexing:

### Rule 1: Every document folder gets an INDEX.md
A "document folder" is any folder containing `.md`, `.yaml`, `.yml`, `.json`, or `.txt` files (excluding INDEX.md itself, CLAUDE.md, and hidden files/folders like `.git`, `.specstory`).

### Rule 2: INDEX.md describes contents with minimal metadata
Each entry provides enough context to decide whether to load it, without reading it.

**Format for files:**
```
- `filename.md` — One-line description of purpose/content (date if relevant)
```

**Format for subfolders:**
```
- `subfolder/` — One-line purpose. See `subfolder/INDEX.md`
```

### Rule 3: Depth-first, bottom-up
Process deepest folders first so parent INDEX.md entries can reference child indexes.

## Steps (default mode)

### 1. Resolve target path
Convert the argument to an absolute path. Verify it exists and is a directory.

### 2. Discover the tree
Use Glob to find all files recursively. Build a list of folders that qualify as "document folders" (contain indexable files). Exclude:
- Hidden directories (`.git/`, `.specstory/`, `.work-assistant-config/`)
- `node_modules/`, `target/`, `build/`, `dist/`, `__pycache__/`
- `archive/` folders (index only the archive root, not contents)

### 3. Sort depth-first
Order folders deepest-first so children are indexed before parents.

### 4. For each folder, generate or update INDEX.md

**If INDEX.md exists:** Read it. Check for missing files (new files not yet indexed) and stale entries (files that no longer exist). Report additions and removals. Preserve existing descriptions for files that haven't changed. Add new entries at the end of the appropriate section.

**If INDEX.md does not exist:** Create one.

**To generate a file description:**
1. Read the first 30 lines of the file
2. Write a single sentence describing its purpose
3. Include date if the filename or content contains one
4. Keep it under 15 words

**INDEX.md structure:**
```markdown
# Index — {folder name or context}

## Subfolders
- `subfolder-a/` — Purpose. See `subfolder-a/INDEX.md`
- `subfolder-b/` — Purpose. See `subfolder-b/INDEX.md`

## Files
- `file-a.md` — Description (YYYY-MM-DD)
- `file-b.yaml` — Description
```

Omit the "Subfolders" section if there are no subfolders. Omit the "Files" section if there are no files (folder only contains subfolders).

### 5. Report summary
After completion, print:
```
Indexed N folders. Created M new INDEX.md files, updated K existing.
```

If `--dry-run`, instead print:
```
Would index N folders:
  - path/to/folder-a/ (new INDEX.md)
  - path/to/folder-b/ (update: 3 new files, 1 stale entry)
```

## Steps (--scope architecture)

### 1. Scan Architecture Tree
Start from `agent-os/specs/architecture/` (or the provided path). Recursively find all directories containing `.md` files. Skip directories with fewer than 2 `.md` files.

### 2. Process Each Directory
1. Load existing `index.yml` if present
2. Compare with current files: new files need descriptions, deleted files get removed, existing files stay
3. For new files: read first 30 lines, generate one-line description
4. For deleted files: remove automatically and report

### 3. Special Handling for ADRs (architecture/decisions/)
- Extract ADR number from filename prefix (e.g., `001-` → ADR-001)
- Extract title from `# ADR-XXX: Title` header
- Extract status from `## Status` section
- Sort by ADR number, not alphabetically
- Include `supersedes:` for ADRs that replace older decisions

### 4. Create Architecture Root Index
Generate/update `agent-os/specs/architecture/index.yml` mapping subsections and individual docs.

## Steps (--scope specs)

### 1. Scan Directory Tree
Start from `agent-os/specs/` (or the provided path). Recursively find all directories. Skip directories with fewer than 2 `.md` files.

### 2. Process Each Directory
Same as architecture scope: diff existing vs current, handle additions/removals.

### 3. Create Root Index
Generate/update `agent-os/specs/index.yml` mapping top-level categories to their `index.yml` files.

## Edge Cases

- **Binary files** (images, PDFs, zips): List them with a generic description based on filename. Do not attempt to read them.
- **Very large folders** (50+ files): Group files by prefix or date pattern if a natural grouping exists. Otherwise list them flat.
- **Existing INDEX.md with custom sections:** Preserve custom sections. Only modify/add entries in the standard "Subfolders" and "Files" sections.
- **CLAUDE.md files in folder:** Do not index CLAUDE.md files (they are loaded automatically by the system). Skip them silently.
- **README.md:** Index it like any other file. It often serves as the primary context document for a folder.
- **.index-stale marker:** If a `.index-stale` file is found in a directory, prioritize that directory for refresh and remove the marker after updating.
