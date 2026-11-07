#!/usr/bin/env python3
"""Self-containment check for a factory-style skill. Read-only. Report only.

Generalizes service-factory/gates/version_guard.py to any skill directory. It does not
change the skill. A FAIL is an audit finding, not a fix.

Checks (each PASS / FAIL / WARN / N/A):
  version_coupling  SKILL.md `version:` equals the top `## X.Y.Z` entry in CHANGELOG.md
  carried_spec      a spec file is carried inside the skill (default glob docs/spec/*.md)
  spec_source       SKILL.md `spec_source:` resolves to a file inside the skill (WARN if absent)
  external_tether   SKILL.md and the carried spec do not point at an external second copy
  runs_ledger       runs/INDEX.md exists when the skill produces runs (runs/ dir or --run-producing)
  execution_laws    extracted laws exist (contracts/ dir or a laws-of-execution.md file)

Usage: self_containment_check.py <skill-dir> [<skill-dir> ...] [--spec-glob GLOB] [--run-producing]
Exit 0 = no FAIL in any skill; 1 = at least one FAIL; 2 = usage error.
"""
import argparse
import json
import re
import sys
from pathlib import Path

FRONTMATTER = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)
CHANGELOG_VER = re.compile(r'^##\s+\[?v?(\d+\.\d+\.\d+)', re.MULTILINE)
SKILL_MD_TETHERS = ('session-retros',)
SPEC_TETHERS = ('session-retros', 'project-management/')


def frontmatter_value(text, key):
    m = FRONTMATTER.match(text)
    if not m:
        return ''
    for line in m.group(1).splitlines():
        if line.startswith(key + ':'):
            return line.split(':', 1)[1].strip().strip('"\'')
    return ''


def check_skill(skill_dir, spec_glob='docs/spec/*.md', run_producing=False):
    d = Path(skill_dir)
    res = {'skill': d.name, 'path': str(d), 'checks': {}}
    c = res['checks']
    skill_md_path = d / 'SKILL.md'
    if not skill_md_path.is_file():
        c['skill_md'] = ['FAIL', 'SKILL.md missing']
        res['pass'] = False
        return res
    skill_md = skill_md_path.read_text()

    version = frontmatter_value(skill_md, 'version')
    changelog = (d / 'CHANGELOG.md').read_text() if (d / 'CHANGELOG.md').is_file() else ''
    m = CHANGELOG_VER.search(changelog)
    top = m.group(1) if m else ''
    if not version:
        c['version_coupling'] = ['FAIL', 'SKILL.md has no version: frontmatter']
    elif not changelog:
        c['version_coupling'] = ['FAIL', 'CHANGELOG.md missing']
    elif not top:
        c['version_coupling'] = ['FAIL', 'CHANGELOG.md has no ## X.Y.Z entry']
    elif top != version:
        c['version_coupling'] = ['FAIL', f'SKILL.md version {version} != CHANGELOG top {top}']
    else:
        c['version_coupling'] = ['PASS', version]

    specs = sorted(p for p in d.glob(spec_glob) if p.is_file())
    c['carried_spec'] = (['PASS', ', '.join(p.name for p in specs)] if specs
                         else ['FAIL', f'no carried spec matches {spec_glob}'])

    spec_source = frontmatter_value(skill_md, 'spec_source')
    if not spec_source:
        c['spec_source'] = ['WARN', 'no spec_source: pointer in SKILL.md frontmatter']
    elif not (d / spec_source).is_file():
        c['spec_source'] = ['FAIL', f'spec_source {spec_source} does not resolve inside the skill']
    else:
        c['spec_source'] = ['PASS', spec_source]

    tethers = [f'SKILL.md: {t}' for t in SKILL_MD_TETHERS if t in skill_md]
    for p in specs:
        text = p.read_text()
        tethers += [f'{p.name}: {t}' for t in SPEC_TETHERS if t in text]
    c['external_tether'] = ['FAIL', '; '.join(tethers)] if tethers else ['PASS', 'none']

    if run_producing or (d / 'runs').is_dir():
        c['runs_ledger'] = (['PASS', 'runs/INDEX.md'] if (d / 'runs' / 'INDEX.md').is_file()
                            else ['FAIL', 'skill produces runs but runs/INDEX.md is missing'])
    else:
        c['runs_ledger'] = ['N/A', 'no runs/ directory']

    laws = (d / 'contracts').is_dir() or any(d.rglob('laws-of-execution.md'))
    c['execution_laws'] = (['PASS', 'contracts/ or laws-of-execution.md'] if laws
                           else ['FAIL', 'no contracts/ dir and no laws-of-execution.md'])

    res['pass'] = not any(v[0] == 'FAIL' for v in c.values())
    return res


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('skill_dirs', nargs='+')
    p.add_argument('--spec-glob', default='docs/spec/*.md')
    p.add_argument('--run-producing', action='store_true')
    a = p.parse_args(argv)
    results = [check_skill(s, a.spec_glob, a.run_producing) for s in a.skill_dirs]
    print(json.dumps(results, indent=2))
    return 0 if all(r['pass'] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
