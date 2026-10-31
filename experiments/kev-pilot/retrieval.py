"""Read-only global-library snapshots and explicit, offline retrieval comparisons.

The legacy baseline preserves scoring and prompt suppression, but excludes org
libraries, out-of-scope targets, and per-session deduplication. It never runs a hook.
Sparse labels remain sparse: unjudged results are not counted as irrelevant.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re

STOP = set("klever proximity measurement supervisr guide rules notes session learnings findings patterns overview index claude full table usage workflow workflows reference catalog architecture process structure checks checklist general https http docs documentation about gotchas".split())
SHORT_OK = set("xml sql api iam bq ci cd mr pr dns ssh jwt ttl dac iac gcp vpc csv env poi zip cbg dma mcp adr ac um ui ux e2e tls s3 vm cli npm jvm orm ddl".split())
ALIAS_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|(?:\s*([^|]*?)\s*\|)?")
BASELINE_DEVIATIONS = [
    "Global context Markdown only; org libraries and other alias targets excluded.",
    "No session deduplication, matching a fresh recall state on each query.",
    "No hook execution, pointer injection, or dedup marker writes.",
    "Prompt-length and library/librarian/bibliotheque suppression preserved.",
]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _scan(root: Path):
    """Do not traverse symlink directories or read any symlink files."""
    files, observations = {}, []
    def visit(directory):
        for path in sorted(directory.iterdir()):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                observations.append({"kind": "symlink_excluded", "path": relative})
            elif path.is_dir():
                visit(path)
            elif path.is_file() and path.suffix == ".md":
                files[relative] = path.read_bytes()
    context = root / "context"
    if context.is_symlink():
        observations.append({"kind": "symlink_excluded", "path": "context"})
    elif context.is_dir():
        visit(context)
    for name in ("ALIASES.md", "INDEX.md", "CATALOG.md"):
        path = root / name
        if path.is_symlink():
            observations.append({"kind": "symlink_excluded", "path": name})
        elif path.is_file():
            files[name] = path.read_bytes()
        else:
            observations.append({"kind": "missing_metadata", "path": name})
    return files, observations


def snapshot_library(root: Path, hook: Path) -> dict:
    root = Path(root).resolve(strict=True)
    raw, observations = _scan(root)
    rows = []
    for line in raw.get("ALIASES.md", b"").decode("utf-8").splitlines():
        m = ALIAS_ROW.match(line)
        if not m:
            continue
        alias, target, note, keywords = m.group(1), m.group(2), m.group(3), m.group(4) or ""
        if alias.lower() in ("alias", "---", ":---") or alias.startswith("-"):
            continue
        p = PurePosixPath(target)
        if p.is_absolute() or ".." in p.parts or not target.startswith("context/") or p.suffix != ".md":
            observations.append({"kind": "out_of_scope_alias", "path": target, "alias": alias})
            continue
        if target not in raw:
            observations.append({"kind": "missing_alias_target", "path": target, "alias": alias})
            continue
        rows.append({"alias": alias, "path": target, "note": note, "keywords": keywords})
    documents = []
    for relative, content in sorted(raw.items()):
        if not relative.startswith("context/"):
            continue
        text = content.decode("utf-8")
        title = next((s[2:].strip() for s in text.splitlines() if s.startswith("# ")), Path(relative).stem)
        aliases = [row for row in rows if row["path"] == relative]
        documents.append({"id": relative, "relative_path": relative, "title": title, "text": text,
                          "aliases": [row["alias"] for row in aliases], "alias_rows": aliases})
    manifest = {name: _sha(content) for name, content in sorted(raw.items())}
    hook_bytes = Path(hook).read_bytes()
    digest_input = {"files": manifest, "hook_sha256": _sha(hook_bytes)}
    return {"root": str(root), "documents": documents, "alias_rows": rows, "files": manifest,
            "hook_sha256": digest_input["hook_sha256"], "hook_path": str(Path(hook).resolve()),
            "corpus_manifest_sha256": _sha(json.dumps(digest_input, sort_keys=True).encode()),
            "observations": observations, "baseline_deviations": BASELINE_DEVIATIONS.copy()}


def assert_source_unchanged(root: Path, manifest: dict) -> bool:
    expected = manifest.get("files", manifest)
    raw, _ = _scan(Path(root).resolve(strict=True))
    actual = {name: _sha(content) for name, content in raw.items()}
    if actual != expected:
        changed = sorted(name for name in set(actual) | set(expected) if actual.get(name) != expected.get(name))
        raise RuntimeError("library source changed: " + ", ".join(changed))
    if "hook_path" in manifest and _sha(Path(manifest["hook_path"]).read_bytes()) != manifest["hook_sha256"]:
        raise RuntimeError("recall hook source changed")
    return True


def _stem(word):
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[:-len(suffix)]
    return word


def _words(text):
    return {word for word in re.findall(r"[a-z0-9]{2,}", text.lower()) if len(word) >= 4 or word in SHORT_OK}


def legacy_rank(query: str, snapshot: dict) -> list[str]:
    if len(query) < 10 or re.search(r"bibliot|librarian|\blibrary\b", query, re.I):
        return []
    lower = query.lower()
    words = _words(lower)
    words |= {_stem(word) for word in words}
    def tokens(text):
        base = {word for word in _words(text) - STOP if not re.match(r"^(20\d\d|ktp\d*|spv\d*)$", word)}
        return base | {_stem(word) for word in base}
    scores = {}
    for row in snapshot["alias_rows"]:
        phrase = row["alias"].lower().replace("-", " ").replace("_", " ")
        score = 3 if len(phrase) >= 5 and phrase in lower else 0
        curated = tokens(row["alias"] + " " + row["note"] + " " + Path(row["path"]).stem)
        mined = tokens(row["keywords"]) - curated
        hit_curated = curated & words
        if not hit_curated and not score:
            continue
        score += len(hit_curated) + 0.5 * len(mined & words)
        if score >= 2:
            scores[row["path"]] = max(scores.get(row["path"], 0), score)
    return sorted(scores, key=lambda key: -scores[key])[:5]


def lexical_rank(query: str, snapshot: dict, limit: int = 20) -> list[str]:
    """BM25 metadata baseline: titles, filenames, aliases and curated notes only."""
    def tokens(text):
        return re.findall(r"[a-z0-9]+", text.lower())
    query_tokens = set(tokens(query))
    docs = []
    for doc in snapshot["documents"]:
        metadata = " ".join(row["alias"] + " " + row["note"] for row in doc["alias_rows"])
        docs.append((doc["id"], Counter(tokens(doc["title"] + " " + doc["id"] + " " + metadata))))
    if not docs or limit <= 0:
        return []
    n, average = len(docs), sum(sum(terms.values()) for _, terms in docs) / len(docs)
    df = {term: sum(term in terms for _, terms in docs) for term in query_tokens}
    scored = []
    for doc_id, terms in docs:
        length, score = sum(terms.values()), 0.0
        for term in query_tokens:
            tf = terms.get(term, 0)
            if tf:
                idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                score += idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * length / (average or 1)))
        if score:
            scored.append((score, doc_id))
    return [doc_id for _, doc_id in sorted(scored, key=lambda pair: (-pair[0], pair[1]))[:limit]]


def metrics(labels: dict, ranking: list[str]) -> dict:
    """Grades: 0 irrelevant, 1 background, 2 useful, 3 essential; null unjudged.

    Recall denominator is the supplied judged useful set. It is NOT corpus recall
    unless labels cover the corpus. Missing returned labels invalidate quality
    metrics rather than becoming negative labels. Empty useful sets have undefined
    recall/nDCG and remain null, including intentional no-match cases.
    """
    if any(value is not None and (type(value) is not int or value not in range(4)) for value in labels.values()):
        raise ValueError("labels must be integer grades 0..3 or null")
    if len(set(ranking)) != len(ranking):
        raise ValueError("ranking contains duplicate document IDs")
    top = ranking[:5]
    unknown = sum(labels.get(doc_id) is None for doc_id in top)
    useful = {doc_id for doc_id, grade in labels.items() if grade is not None and grade >= 2}
    grades = [labels.get(doc_id) for doc_id in top]
    def dcg(values):
        return sum((2 ** grade - 1) / math.log2(index + 2) for index, grade in enumerate(values))
    ideal = dcg(sorted((v for v in labels.values() if v is not None), reverse=True)[:5])
    valid = not unknown and bool(labels)
    return {"recall_at_5": len(useful & set(top)) / len(useful) if valid and useful else None,
            "ndcg_at_5": dcg(grades) / ideal if valid and ideal else None,
            "first_useful_hit": next((i + 1 for i, doc_id in enumerate(top) if doc_id in useful), None) if valid else None,
            "irrelevant_at_5": sum(grade == 0 for grade in grades) if valid else None,
            "judged_at_5": len(top) - unknown, "unjudged_at_5": unknown,
            "quality_metrics_known": valid, "judged_useful_documents": len(useful),
            "scope": "supplied labels only; authored diagnostics are not a holdout"}
