"""Behavior checks for project isolation, missing source and portable setup."""
import csv
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("shared_bmad", SOURCE / "bmad.py")
bmad = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bmad)


class Loading(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = (Path(self.temp.name) / "neutral-project").resolve()
        self.project.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def local_config(self):
        path = self.project / "_bmad/bmm/config.yaml"
        path.parent.mkdir(parents=True)
        path.write_text('user_name: Local Survey\noutput_folder: "{project-root}/artifacts"\n')
        return path

    def test_absolute_framework_config_still_uses_active_project_override(self):
        local = self.local_config()
        selected = bmad.resource(str(SOURCE / "runtime/bmm/config.yaml"), self.project)
        self.assertEqual(selected, local)
        self.assertIn(str(self.project / "artifacts"), bmad.render(selected, self.project))

    def test_neutral_project_defaults_do_not_inherit_klever_name(self):
        selected = bmad.resource("bmm/config.yaml", self.project)
        text = bmad.render(selected, self.project)
        self.assertIn('project_name: "neutral-project"', text)
        self.assertIn('user_name: Gabriel', text)
        self.assertNotIn('Klever Gab', text)
        self.assertIn(str(self.project / "_bmad-output"), text)
        self.assertFalse((self.project / "_bmad").exists())

    def test_persona_resource_and_config_roots_are_distinct(self):
        local = self.local_config()
        _, path = bmad.select("Atlas")
        text = bmad.render(path, self.project)
        self.assertIn(str(local), text)
        self.assertIn(str(SOURCE / "runtime/core/tasks/workflow.xml"), text)
        self.assertIn(str(self.project), text)

    def test_missing_and_unknown_roles_fail_instead_of_substituting(self):
        for role in ["agent-builder", "imaginary-security-persona"]:
            with self.subTest(role=role), self.assertRaises(ValueError):
                bmad.select(role)

    def test_parent_traversal_and_external_resources_are_rejected(self):
        for resource in ["../registry.json", "/etc/passwd", "_bmad/../../private.txt"]:
            with self.subTest(resource=resource), self.assertRaises(ValueError):
                bmad.resource(resource, self.project)

    def test_external_project_config_symlink_is_rejected(self):
        config = self.project / "_bmad/bmm/config.yaml"
        config.parent.mkdir(parents=True)
        outside = Path(self.temp.name) / "foreign.yaml"
        outside.write_text("foreign: true\n")
        config.symlink_to(outside)
        with self.assertRaises(ValueError):
            bmad.resource("bmm/config.yaml", self.project)

    def test_effective_party_roster_contains_available_custom_roles_once(self):
        text = bmad.render(SOURCE / "runtime/_config/agent-manifest.csv", self.project)
        rows = list(csv.DictReader(io.StringIO(text)))
        names = [r["displayName"] for r in rows]
        self.assertEqual(names.count("Atlas"), 1)
        self.assertEqual(names.count("Leo"), 1)
        self.assertEqual(names.count("Dexter"), 1)
        for row in rows:
            self.assertTrue(Path(row["path"]).is_file())

    def test_recovered_dexter_aliases_and_menu_use_real_resources(self):
        _, source = bmad.select("Dexter")
        self.assertEqual(source, bmad.select("debugger")[1])
        self.assertEqual(source, bmad.select("bmad-agent-bmm-debugger")[1])
        text = bmad.render(source, self.project)
        self.assertIn('name="Dexter"', text)
        self.assertIn(str(SOURCE / "runtime/core/workflows/party-mode/workflow.md"), text)
        self.assertNotIn('exec="_bmad/bmm/agents/workflows/', text)
        old = "_bmad/bmm/agents/workflows/party-mode/workflow.md"
        self.assertTrue(bmad.resource(old, self.project).is_file())
        self.assertIn('Do NOT begin investigation until the user describes the incident', text)

    def test_legacy_yaml_commands_keep_the_selected_workflow_and_engine(self):
        commands = bmad.registry()["commands"]
        for name, row in commands.items():
            if row["kind"] == "agent":
                bmad.select(row["agent"])
                continue
            with self.subTest(command=name):
                target = bmad.resource(row["target"], self.project)
                self.assertTrue(target.is_file())
                if target.suffix == ".yaml":
                    self.assertNotEqual(row["target"], row["engine"])
                    engine = bmad.resource(row["engine"], self.project)
                    self.assertTrue(engine.is_file())
                    self.assertIn("workflow-config", row["instructions"])

    def test_relocated_home_setup_preserves_instructions_and_is_idempotent(self):
        home = (Path(self.temp.name) / "different-user").resolve()
        shared = home / ".claude-shared-config"
        payload = shared / "bmad"
        shutil.copytree(SOURCE, payload, symlinks=True, ignore=shutil.ignore_patterns("__pycache__"))
        skill = shared / "skills/bmad"
        skill.mkdir(parents=True)
        shutil.copy2(SOURCE.parent / "skills/bmad/SKILL.md", skill / "SKILL.md")
        (home / ".codex").mkdir()
        user = home / ".codex/AGENTS.md"
        user.write_text("Keep existing user guidance.\n")
        command = [sys.executable, str(payload / "setup.py"), "--home", str(home)]
        subprocess.run(command, check=True, capture_output=True)
        first = user.read_bytes()
        subprocess.run(command, check=True, capture_output=True)
        self.assertEqual(user.read_bytes(), first)
        self.assertTrue(first.startswith(b"Keep existing user guidance."))
        self.assertEqual(user.read_text().count("shared-bmad-loading:start"), 1)
        for host in [".agents", ".claude"]:
            self.assertEqual((home / host / "skills/bmad").resolve(), skill)
        result = subprocess.run([sys.executable, str(payload / "bmad.py"), "resolve", "Atlas"],
                                cwd=self.project, check=True, capture_output=True, text=True)
        self.assertTrue(json.loads(result.stdout)["source"].startswith(str(home)))
        # A conflicting registration must preserve both it and existing user guidance.
        link = home / ".agents/skills/bmad"
        link.unlink()
        link.mkdir()
        (link / "preserved.txt").write_text("preserve conflict")
        conflict = subprocess.run(command, capture_output=True)
        self.assertNotEqual(conflict.returncode, 0)
        self.assertEqual(user.read_bytes(), first)
        self.assertEqual((link / "preserved.txt").read_text(), "preserve conflict")


if __name__ == "__main__":
    unittest.main()
