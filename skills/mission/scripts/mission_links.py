"""Reference linking for the mission report: one tokenizer pass per text field.

linkify(text, ctx) returns safe HTML. Every recognized reference becomes an <a>:
  #N                -> GitHub issue in gh_repo;   owner/repo#N -> that repo's issue
  KEY-N             -> jira_browse + KEY-N        (KEY-N{2,5} expands to KEY-N2, KEY-N5)
  <repo> !N, repo!N -> merge request of that repo (repos in the org config); a bare !N takes the nearest
                       earlier repo word in the text, then the context repo
  <sha>             -> commit URL when a repo is known; job N -> CI job; comment N -> Jira focusedCommentId
  CO-n, T-n         -> in-page anchor when ctx.anchors holds the id
A reference that cannot be linked (unknown repo, a branch name) is shown as dotted <code class="nolink">
with a reason, never as a bare ID. bare_refs(html) lists the #N / KEY-N / !N tokens left outside an <a>:
the Layer A check fails the render on any of them.

The org values (gh_repo, jira_browse, repos, jira_link_pattern) come from the mission config. The harness holds none.
"""
from __future__ import annotations

import html
import re
from html.parser import HTMLParser

from mission_lib import CONFIG, GH_REPO, JIRA_BROWSE

# Upper-case prefixes that look like tracker keys but are mission or document IDs.
NOT_JIRA = {"DEC", "ART", "CO", "ADR", "UTF", "SHA", "ISO", "RFC", "HTTP", "TLS", "AC"}
JIRA_LINK_PATTERN = CONFIG.get("jira_link_pattern") or r"[A-Z][A-Z0-9]{1,9}-\d+"
REPOS = {name: (v if isinstance(v, dict) else {"url": v}) for name, v in (CONFIG.get("repos") or {}).items()}


def _alias_map() -> dict[str, str]:
    out = {}
    for name, v in REPOS.items():
        for a in [name, *(v.get("aliases") or [])]:
            out[str(a)] = name
    return out


ALIASES = _alias_map()
_ALIAS_RE = "|".join(sorted((re.escape(a) for a in ALIASES), key=len, reverse=True)) or r"(?!x)x"
_JIRA = rf"(?:{JIRA_LINK_PATTERN})"

TOKEN = re.compile(
    r"(?P<url>(?:https?|file)://[^\s<>\"')\]]+)"
    rf"|(?P<braces>\b(?P<bkey>{_JIRA})\{{(?P<blist>\d+(?:,\d+)+)\}})"
    rf"|(?P<branch>\b{_JIRA}-[a-z0-9][\w.-]*)"
    rf"|(?P<repo_gh>\b[\w.-]+/[\w.-]+#(?P<rgn>\d+)\b)"
    rf"|(?:(?P<mrrepo>(?<![\w-])(?:{_ALIAS_RE}))\s?|(?<![\w!]))!(?P<mr>\d+)\b"
    rf"|(?P<job>\bjob (?P<jobn>\d{{4,}})\b)"
    rf"|(?P<jc>\bcomment (?P<jcn>\d{{4,}})\b)"
    rf"|(?P<anchor>\b(?:CO|T)-\d+\b)"
    rf"|(?P<jira>\b{_JIRA}\b)"
    rf"|(?P<gh>(?<![\w/&#])#(?P<ghn>\d+)\b)"
    rf"|(?P<sha>(?<!hash )(?<!batch )\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])(?:[0-9a-f]{{40}}|[0-9a-f]{{7,10}})\b)"
)
BARE_GH = re.compile(r"(?<![\w/&#])#\d+\b")
BARE_MR = re.compile(r"(?<![\w!])!\d+\b")
BARE_JIRA = re.compile(rf"\b{_JIRA}\b")
REPO_WORD = re.compile(rf"(?<![\w-])({_ALIAS_RE})(?![\w])") if ALIASES else None


def e(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def a(url: str, text: str, cls: str = "ref") -> str:
    return f'<a class="{cls}" href="{e(url)}" target="_blank" rel="noopener">{text}</a>'


def nolink(raw: str, why: str) -> str:
    return f'<code class="nolink" title="{e(why)}">{e(raw)}</code>'


def is_jira_key(tok: str) -> bool:
    return bool(re.fullmatch(_JIRA, tok)) and tok.split("-")[0] not in NOT_JIRA


def jira_url(key: str) -> str | None:
    return JIRA_BROWSE + key if JIRA_BROWSE else None


def gh_issue_url(n, repo: str | None = None) -> str | None:
    repo = repo or GH_REPO
    return f"https://github.com/{repo}/issues/{n}" if repo else None


def repo_of(text: str) -> str | None:
    """The last repo word in the text, as a repo name."""
    if not REPO_WORD:
        return None
    hits = REPO_WORD.findall(str(text or ""))
    return ALIASES.get(hits[-1]) if hits else None


def _repo_url(repo: str | None, kind: str, n: str) -> str | None:
    if not repo or repo not in REPOS:
        return None
    base = str(REPOS[repo].get("url") or "").rstrip("/")
    if not base:
        return None
    github = REPOS[repo].get("forge") == "github" or "github.com" in base
    path = {"mr": ("pull" if github else "-/merge_requests"), "commit": ("commit" if github else "-/commit"),
            "job": ("actions/runs" if github else "-/jobs")}[kind]
    return f"{base}/{path}/{n}"


class Ctx:
    """Per-field context: a fallback repo (from the thread) and the in-page anchors."""

    def __init__(self, repo: str | None = None, anchors: set[str] | None = None):
        self.repo, self.anchors = repo, anchors or set()


def linkify(text, ctx: Ctx | None = None) -> str:
    ctx = ctx or Ctx()
    s = str(text if text is not None else "")
    out, pos, last_jira = [], 0, None
    for m in TOKEN.finditer(s):
        g, raw = m.groupdict(), m.group(0)
        if g["jira"] and not is_jira_key(raw):
            continue
        out.append(e(s[pos:m.start()]))
        pos = m.end()
        before = s[:m.start()]
        repo = repo_of(before) or ctx.repo
        if g["url"]:
            out.append(a(raw, e(raw if len(raw) <= 60 else raw[:57] + "...")))
        elif g["braces"]:
            key, prefix = g["bkey"], g["bkey"]
            parts = []
            for d in g["blist"].split(","):
                k = prefix + d if len(d) < 3 else re.sub(r"\d+$", d, key)
                u = jira_url(k)
                parts.append(a(u, e(k)) if u else nolink(k, "no jira_browse in the mission config"))
            out.append(", ".join(parts))
        elif g["branch"]:
            out.append(nolink(raw, "a branch or file name, not a ticket") + '<sup class="nl">branch</sup>')
        elif g["repo_gh"]:
            repo_name = raw.split("#")[0]
            out.append(a(f"https://github.com/{repo_name}/issues/{g['rgn']}", e(raw)) if "/" in repo_name and "." not in repo_name.split("/")[0]
                       else nolink(raw, "unknown forge"))
        elif g["mr"]:
            r = ALIASES.get(g["mrrepo"]) if g["mrrepo"] else repo
            u = _repo_url(r, "mr", g["mr"])
            out.append(a(u, e(raw)) if u else nolink(raw, "merge request of an unknown repo: add the repo to repos in the mission config"))
        elif g["job"]:
            u = _repo_url(repo, "job", g["jobn"])
            out.append(a(u, e(raw)) if u else e(raw))
        elif g["jc"]:
            u = jira_url(last_jira) if last_jira else None
            out.append(a(f"{u}?focusedCommentId={g['jcn']}", e(raw)) if u else e(raw))
        elif g["anchor"]:
            out.append(f'<a class="ref in" href="#{e(raw)}">{e(raw)}</a>' if raw in ctx.anchors else f'<span class="sid">{e(raw)}</span>')
        elif g["jira"]:
            last_jira = raw
            u = jira_url(raw)
            out.append(a(u, e(raw)) if u else nolink(raw, "no jira_browse in the mission config"))
        elif g["gh"]:
            u = gh_issue_url(g["ghn"])
            out.append(a(u, e(raw)) if u else nolink(raw, "no gh_repo in the mission config"))
        elif g["sha"]:
            u = _repo_url(repo, "commit", raw)
            out.append(a(u, f"<code>{e(raw)}</code>") if u else f"<code>{e(raw)}</code>")
    out.append(e(s[pos:]))
    return "".join(out)


# ---------------------------------------------------------------- typed links

def classify(link: dict | None) -> dict | None:
    """Normalize a link: a GitHub issue URL becomes kind gh with ref #N, a tracker browse URL kind jira, an MR URL kind mr."""
    if not isinstance(link, dict) or not link.get("url"):
        return link
    u, out = str(link["url"]), dict(link)
    m = re.search(r"github\.com/([\w.-]+/[\w.-]+)/issues/(\d+)", u)
    if m:
        out["kind"] = "gh"
        out.setdefault("ref", f"#{m.group(2)}" if m.group(1) == GH_REPO else f"{m.group(1)}#{m.group(2)}")
        return out
    m = re.search(r"/browse/([A-Z][A-Z0-9]+-\d+)", u)
    if m:
        out["kind"] = "jira"
        out.setdefault("ref", m.group(1))
        return out
    m = re.search(r"/(?:-/)?(?:merge_requests|pull)/(\d+)", u)
    if m:
        out["kind"] = "mr"
        out.setdefault("ref", f"!{m.group(1)}")
        return out
    if u.startswith("file://") and out.get("kind") in (None, "url"):
        out["kind"] = "file"
    return out


KIND_LABEL = {"jira": "Jira", "gh": "GitHub", "mr": "MR", "file": "file", "folder": "folder", "session": "session",
              "url": "link", "slack": "Slack", "commit": "commit", "job": "CI job"}


def kind_label(link: dict) -> str:
    u = str(link.get("url") or "")
    if "/commit/" in u:
        return "commit"
    if "/jobs/" in u:
        return "CI job"
    return KIND_LABEL.get(classify(link).get("kind"), link.get("kind") or "link")


def chip(link: dict | None, ctx: Ctx | None = None) -> str:
    if not isinstance(link, dict) or not link.get("url"):
        return ""
    t = link.get("title") or link.get("ref") or link["url"]
    return (f'<a class="chip" href="{e(link["url"])}" target="_blank" rel="noopener"><b>{e(kind_label(link))}</b>'
            f'{e(t)}</a>')


def tokens(text) -> set[str]:
    """Reference tokens in a text: #N, KEY-N, !N (for matching records that talk about the same thing)."""
    s = str(text or "")
    out = {f"#{n}" for n in re.findall(r"(?<![\w/&#])#(\d+)\b", s)}
    out |= {k for k in re.findall(rf"\b{_JIRA}\b(?!\{{)", s) if is_jira_key(k)}
    for key, lst in re.findall(rf"\b({_JIRA})\{{(\d+(?:,\d+)+)\}}", s):
        out |= {key + d for d in lst.split(",")}
    out |= {f"!{n}" for n in re.findall(r"(?<![\w!])!(\d+)\b", s)}
    return out


def link_tokens(link: dict | None) -> set[str]:
    if not isinstance(link, dict):
        return set()
    c = classify(link) or {}
    out = tokens(link.get("title")) | tokens(c.get("ref"))
    u = str(c.get("url") or "")
    for rx, fmt in ((r"/issues/(\d+)$", "#{}"), (r"/browse/([A-Z][A-Z0-9]+-\d+)$", "{}"), (r"/(?:merge_requests|pull)/(\d+)$", "!{}")):
        mm = re.search(rx, u.split("?")[0].split("#")[0].rstrip("/"))
        if mm:
            out.add(fmt.format(mm.group(1)))
    if not out and c.get("kind") in ("gh", "jira", "mr") and c.get("ref"):
        out.add(str(c["ref"]))
    return out


# ---------------------------------------------------------------- the bare-reference check

class _Bare(HTMLParser):
    SKIP = {"a", "script", "style", "pre"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[bool] = []
        self.found: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "img", "input", "meta", "link", "hr", "wbr"):
            return
        cls = dict(attrs).get("class") or ""
        self.stack.append(tag in self.SKIP or "nolink" in cls.split())

    def handle_endtag(self, tag):
        if tag in ("br", "img", "input", "meta", "link", "hr", "wbr"):
            return
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if any(self.stack):
            return
        for rx in (BARE_GH, BARE_MR):
            self.found += rx.findall(data)
        self.found += [k for k in BARE_JIRA.findall(data) if is_jira_key(k)]


def bare_refs(fragment: str) -> list[str]:
    p = _Bare()
    p.feed(fragment)
    p.close()
    return p.found
