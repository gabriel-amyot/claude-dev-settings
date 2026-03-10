---
name: index-context
description: "Recursively generate or update INDEX.md files across a folder tree. Each INDEX.md provides enough metadata for progressive disclosure: subfolders get a one-liner + pointer, files get a one-liner description. Use when indexing a project, ticket tree, documentation folder, or any knowledge base."
---

# Index Folder

Recursively walks a folder tree and creates/updates INDEX.md files for progressive disclosure.

**Usage:** `/index-folder <PATH> [--dry-run] [--depth <N>]`

**Examples:**
```
/index-folder tickets/SPV-3                    # Index SPV-3 and all subfolders
/index-folder documentation/                   # Index the docs tree
/index-folder .                                # Index from current directory
/index-folder tickets/ --depth 1              # Only top-level ticket folders
/index-folder tickets/SPV-66 --dry-run        # Preview what would be created
```

## Arguments

- `<PATH>`: Required. Root folder to index. Relative to cwd or absolute.
- `--dry-run`: Optional. List folders that need indexes without creating them.
- `--depth <N>`: Optional. Max recursion depth. Default: unlimited.

## Rules

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

## Steps

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

## Edge Cases

- **Binary files** (images, PDFs, zips): List them with a generic description based on filename. Do not attempt to read them.
- **Very large folders** (50+ files): Group files by prefix or date pattern if a natural grouping exists. Otherwise list them flat.
- **Existing INDEX.md with custom sections:** Preserve custom sections. Only modify/add entries in the standard "Subfolders" and "Files" sections.
- **CLAUDE.md files in folder:** Do not index CLAUDE.md files (they are loaded automatically by the system). Skip them silently.
- **README.md:** Index it like any other file. It often serves as the primary context document for a folder.
