// Load a rendered report.html script with a tiny DOM stub; render every tab; fail on any exception.
const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf8');
const script = html.split('<script>')[1].split('</script>')[0];
const els = {};
function el(id) {
  if (!els[id]) els[id] = {id, innerHTML: '', textContent: '', hidden: false, dataset: {}, tabIndex: 0, style: {}, value: 'report',
    attrs: {}, setAttribute(k, v) { this.attrs[k] = v }, getAttribute(k) { return this.attrs[k] || (k === 'aria-controls' ? 'p-' + this.id.slice(2) : null) },
    querySelectorAll() { return [] }, querySelector() { return null }, remove() {}, contains() { return false }, scrollIntoView() {},
    append() {}, focus() {}, click() {}, closest() { return null }, getBoundingClientRect() { return {left: 0, top: 0, width: 1, height: 1} }};
  return els[id];
}
const panel = html.split('id="p-closure"')[1] || '';
el('p-closure').innerHTML = panel.slice(panel.indexOf('>') + 1, panel.indexOf('<div role="tabpanel" id="p-journey"'));
const tabIds = ['t-mission', 't-closure', 't-journey', 't-graph', 't-latest', 't-sources'];
global.document = {getElementById: el, querySelectorAll: s => s === '[role=tab]' ? tabIds.map(el) : [], addEventListener() {},
  createElement: () => el('tmp'), body: {append() {}}, documentElement: {dataset: {}}, execCommand() {}};
global.window = {addEventListener() {}}; global.location = {hash: process.argv[3] || ''};
global.history = {replaceState() {}}; global.navigator = {clipboard: {writeText: async () => {}}};
global.setTimeout = () => 0;
eval(script);
for (const t of ['mission', 'closure', 'journey', 'graph', 'latest', 'sources']) show(t);
if (!el('p-mission').innerHTML.includes('closure readiness')) throw new Error('mission tile missing');
if (!el('p-closure').innerHTML.includes('cl-needs')) throw new Error('closure panel lost');
console.log('ok', Object.keys(els).length);
