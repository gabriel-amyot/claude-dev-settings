# react-force-graph-2d Gotchas

## ResizeObserver Infinite Loop (Critical)

Never use a ResizeObserver on a container and feed the measured dimensions back as `width`/`height` props to `ForceGraph2D` inside that same container. The canvas element grows the parent, which fires the observer, which increases the dimensions, which grows the canvas again. Page crashes white within seconds.

**Fix:** Use fixed dimensions for the canvas. The panel width is known from CSS (e.g., `w-80` = 320px). Height can be set via `calc()` on the container with `overflow: hidden`. No observer needed.

**Bad pattern:**
```jsx
const ro = new ResizeObserver(() => {
  setGraphSize({ w: rect.width, h: rect.height }); // feeds back into ForceGraph2D
});
ro.observe(graphPanelRef.current); // observes the container that holds ForceGraph2D
```

**Good pattern:**
```jsx
<div style={{ height: "calc(60vh - 2rem)" }} className="overflow-hidden">
  <ForceGraph2D width={308} height={350} />
</div>
```

## Wikilink Parsing

When extracting `[[wikilinks]]` from markdown, strip fenced code blocks first. Schema docs and README files contain example wikilinks inside triple-backtick blocks that should not be treated as real links.

```python
FENCED_CODE_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
cleaned = FENCED_CODE_RE.sub("", content)
links = re.findall(r"\[\[([^\]]+)\]\]", cleaned)
```
