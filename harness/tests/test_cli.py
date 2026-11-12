from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

CLI=Path(__file__).resolve().parents[1]/"catalog.py"


class CliTests(unittest.TestCase):
    def test_refresh_replay_note_and_rejected_forgery(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root=base/"shared";home=base/"home";home.mkdir()
            skill=root/"skills/alpha/SKILL.md";skill.parent.mkdir(parents=True)
            skill.write_text('---\nname: alpha\ndescription: Example capability\n---\n# Alpha\n')
            command=[sys.executable,str(CLI),"--root",str(root),"--home",str(home)]
            def run(*args,expect=0):
                p=subprocess.run(command+list(args),text=True,capture_output=True)
                self.assertEqual(p.returncode,expect,p.stderr)
                return json.loads(p.stdout) if p.stdout else p.stderr
            first=run("refresh");self.assertTrue(Path(first["view"]["index"]).exists())
            before=run("stats");run("refresh");after=run("stats")
            for table in ("capabilities","usage_events","eval_runs","outcomes","decisions"):
                self.assertEqual(before[table],after[table],table)
            note=["note","--id","test-note","--skill","alpha","--host","codex","--summary","Observed blocker","--impact","Could not finish","--evidence",str(skill)]
            self.assertTrue(run(*note)["inserted"])
            self.assertFalse(run(*note)["inserted"])
            details=run("show","alpha");self.assertEqual(len(details["frictions"]),1)
            attack=base/"forged.json";attack.write_text(json.dumps({"id":"forged-pass","suite_id":"fake","capability_id":details["capability"]["id"],"occurred_at":"2026-10-26","outcome":"pass","source_path":str(skill),"source_ref":"none"}))
            self.assertIn("cannot write",run("record","eval","--input",str(attack),expect=2))
            self.assertEqual(run("stats")["eval_runs"],0)
            self.assertEqual(skill.read_text(),'---\nname: alpha\ndescription: Example capability\n---\n# Alpha\n')


if __name__=="__main__":unittest.main()
