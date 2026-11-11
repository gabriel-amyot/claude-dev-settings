#!/usr/bin/env python3
"""Layer A suite for harness-audit/scripts/self_containment_check.py.

Builds fixture skill directories in a temp dir. Run: python3 run_self_containment_evals.py
Exit 0 = all pass, 1 = a case failed.

Discriminating cases: the old harness-audit had no self-containment check at all, so a
version drift (case 02) or an external spec tether (case 04) was never reported.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), 'scripts', 'self_containment_check.py')
PASS = FAIL = 0


def check(name, cond, detail=''):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f'  PASS  {name}')
    else:
        FAIL += 1
        print(f'  FAIL  {name}  {detail}')


def make_skill(root, name, version='1.2.0', changelog_top='1.2.0', spec=True, spec_source=True,
               spec_text='# Spec\n', runs=True, runs_index=True, laws=True, skill_extra=''):
    d = os.path.join(root, name)
    os.makedirs(d)
    fm = ['---', f'name: {name}']
    if version:
        fm.append(f'version: "{version}"')
    if spec_source:
        fm.append('spec_source: docs/spec/spec-1.0.0.md')
    fm.append('---')
    with open(os.path.join(d, 'SKILL.md'), 'w') as f:
        f.write('\n'.join(fm) + f'\n\n# {name}\n{skill_extra}\n')
    if changelog_top:
        with open(os.path.join(d, 'CHANGELOG.md'), 'w') as f:
            f.write(f'# Changelog\n\n## {changelog_top} (2026-11-06)\n- change\n\n## 1.0.0\n- first\n')
    if spec:
        os.makedirs(os.path.join(d, 'docs', 'spec'))
        with open(os.path.join(d, 'docs', 'spec', 'spec-1.0.0.md'), 'w') as f:
            f.write(spec_text)
    if runs:
        os.makedirs(os.path.join(d, 'runs'))
        if runs_index:
            open(os.path.join(d, 'runs', 'INDEX.md'), 'w').write('# Runs\n')
    if laws:
        os.makedirs(os.path.join(d, 'contracts'))
    return d


def run(*dirs):
    r = subprocess.run([sys.executable, SCRIPT, *dirs], capture_output=True, text=True)
    try:
        return r.returncode, json.loads(r.stdout)
    except json.JSONDecodeError:
        return r.returncode, r.stderr


def status(results, check_name):
    return results[0]['checks'][check_name][0]


def main():
    tmp = tempfile.mkdtemp(prefix='self-contain-eval-')
    try:
        rc, res = run(make_skill(tmp, 'c01-complete'))
        check('01 complete skill passes', rc == 0 and res[0]['pass'], res)

        rc, res = run(make_skill(tmp, 'c02-drift', version='1.3.0', changelog_top='1.2.0'))
        check('02 version drift -> FAIL', rc == 1 and status(res, 'version_coupling') == 'FAIL', res)

        rc, res = run(make_skill(tmp, 'c03-no-spec', spec=False, spec_source=False))
        check('03 no carried spec -> FAIL', rc == 1 and status(res, 'carried_spec') == 'FAIL', res)
        check('03 no spec_source -> WARN, not FAIL', status(res, 'spec_source') == 'WARN', res)

        rc, res = run(make_skill(tmp, 'c04-tether', spec_text='See project-management/tickets/X for the live spec.\n'))
        check('04 spec points at an external copy -> FAIL', rc == 1 and status(res, 'external_tether') == 'FAIL', res)

        rc, res = run(make_skill(tmp, 'c05-runs-no-index', runs_index=False))
        check('05 runs/ without INDEX.md -> FAIL', rc == 1 and status(res, 'runs_ledger') == 'FAIL', res)

        rc, res = run(make_skill(tmp, 'c06-not-a-factory', runs=False))
        check('06 no runs/ -> runs_ledger N/A', rc == 0 and status(res, 'runs_ledger') == 'N/A', res)

        rc, res = run(make_skill(tmp, 'c07-no-laws', laws=False))
        check('07 no contracts/ or laws file -> FAIL', rc == 1 and status(res, 'execution_laws') == 'FAIL', res)

        d = make_skill(tmp, 'c08-laws-file', laws=False)
        open(os.path.join(d, 'docs', 'spec', 'laws-of-execution.md'), 'w').write('# Laws\n')
        rc, res = run(d)
        check('08 laws-of-execution.md satisfies execution_laws', status(res, 'execution_laws') == 'PASS', res)

        rc, res = run(make_skill(tmp, 'c09-no-version', version=''))
        check('09 missing version -> FAIL', rc == 1 and status(res, 'version_coupling') == 'FAIL', res)

        rc, res = run(os.path.join(tmp, 'c01-complete'), os.path.join(tmp, 'c02-drift'))
        check('10 multi-skill run exits 1 if any skill fails', rc == 1 and len(res) == 2, res)

        before = sorted(os.listdir(os.path.join(tmp, 'c01-complete')))
        run(os.path.join(tmp, 'c01-complete'))
        check('11 check is read-only', sorted(os.listdir(os.path.join(tmp, 'c01-complete'))) == before)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
