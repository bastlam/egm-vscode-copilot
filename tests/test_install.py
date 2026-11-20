from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from egm_copilot.__main__ import (
    LANGUAGE_POLICY, REVIEWERS, RUNTIME_DIRS, RUNTIME_FILES, SKILLS, install, main, uninstall,
)


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="egm test spaces ")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.source = self.base / "source"
        for directory in RUNTIME_DIRS:
            (self.source / directory).mkdir(parents=True)
        for name in RUNTIME_FILES:
            (self.source / name).write_text(name, encoding="utf-8")
        for name in SKILLS:
            skill = self.source / "skills" / name
            skill.mkdir()
            (skill / "SKILL.md").write_text(f"---\nname: {name}\n---\nCanonical {name}", encoding="utf-8")
        for name in (*REVIEWERS.values(), "synthesizer.md"):
            (self.source / "agents" / name).write_text("Canonical persona", encoding="utf-8")
        standards = self.source / "resources/document_standards"
        standards.mkdir()
        (standards / "standard.md").write_text("Canonical standard", encoding="utf-8")
        self.root = self.base / "project/.github/egm-copilot"
        self.skills = self.root.parent / "skills"
        self.agents = self.root.parent / "agents"

    def install(self):
        install(self.source, self.root, self.skills, self.agents, "test-revision")

    def test_complete_install_and_idempotence(self):
        self.install()
        first = (self.root / "manifest.json").read_bytes()
        self.install()
        self.assertEqual(first, (self.root / "manifest.json").read_bytes())
        self.assertEqual(len(list(self.skills.glob("*/SKILL.md"))), 7)
        self.assertEqual(len(list(self.agents.glob("*.agent.md"))), 9)
        for name in SKILLS:
            self.assertEqual(
                (self.source / "skills" / name / "SKILL.md").read_bytes(),
                (self.root / "runtime/skills" / name / "SKILL.md").read_bytes(),
            )
        for name in REVIEWERS:
            profile = (self.agents / f"{name}.agent.md").read_text(encoding="utf-8")
            self.assertIn("tools: [read, search]", profile)
            self.assertIn("user-invocable: false", profile)
            self.assertNotIn("include-custom-instructions:", profile)

    def test_unmanaged_conflict_changes_nothing(self):
        self.agents.mkdir(parents=True)
        conflict = self.agents / "egm.agent.md"
        conflict.write_text("User agent", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unmanaged"):
            self.install()
        self.assertEqual(conflict.read_text(encoding="utf-8"), "User agent")
        self.assertFalse(self.root.exists())

    def test_language_override_reaches_draft_and_reviewers_without_changing_upstream(self):
        draft = self.source / "skills/egm-draft/SKILL.md"
        canonical = b"Plain-English Standard: You MUST write all drafts in English.\n"
        draft.write_bytes(canonical)
        self.install()
        self.assertEqual((self.root / "runtime/skills/egm-draft/SKILL.md").read_bytes(), canonical)
        entries = [self.root / "runtime/VSCODE.md"]
        entries.extend(self.skills / name / "SKILL.md" for name in SKILLS)
        entries.extend(self.agents.glob("*.agent.md"))
        self.assertEqual(len(entries), 17)
        for entry in entries:
            content = entry.read_text(encoding="utf-8")
            self.assertIn(LANGUAGE_POLICY, content, entry)
            self.assertNotIn("Canonical workflow language requirements remain unchanged", content)
        self.assertIn("overrides English-only requirements", LANGUAGE_POLICY)
        self.assertIn("French is fully supported", LANGUAGE_POLICY)
        self.assertIn("Pass the chosen output language explicitly", LANGUAGE_POLICY)

    def test_modified_files_block_update_and_uninstall(self):
        self.install()
        modified = self.root / "runtime/README.md"
        modified.write_text("User changes", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Modified"):
            self.install()
        with self.assertRaisesRegex(ValueError, "Modified"):
            uninstall(self.root)
        self.assertTrue((self.root / "manifest.json").exists())

    def test_uninstall_preserves_other_files(self):
        self.install()
        user_file = self.agents / "other.agent.md"
        user_file.write_text("User agent", encoding="utf-8")
        uninstall(self.root)
        self.assertTrue(user_file.exists())
        self.assertFalse(self.root.exists())
        self.assertFalse(self.skills.exists())

    def test_incomplete_source_is_rejected(self):
        (self.source / "agents/design_critic.md").unlink()
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            self.install()
        self.assertFalse(self.root.exists())

    def test_utf8_accents_survive_install_status_update_and_uninstall(self):
        project = self.base / "projet été équipe"
        root = project / ".github/egm-copilot"
        filename = "spécification-équipe.md"
        content = "# Spécification\nÉléphant, français, cœur, Noël, déjà approuvé.\n"
        (self.source / "docs" / filename).write_bytes(content.encode("utf-8"))
        options = ["--project", str(project)]
        for attempt in range(2):
            with self.subTest(attempt=attempt), redirect_stdout(io.StringIO()):
                self.assertEqual(main(["install", *options, "--source", str(self.source)]), 0)
            self.assertEqual((root / "runtime/docs" / filename).read_bytes(), content.encode("utf-8"))
        manifest = (root / "manifest.json").read_text(encoding="utf-8")
        self.assertIn(filename, manifest)
        self.assertNotIn("\\u00e9", manifest)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["status", *options]), 0)
        self.assertIn(filename, output.getvalue())
        self.assertIn("runtime/docs/" + filename, json.loads(output.getvalue())["files"])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["uninstall", *options]), 0)
        self.assertFalse(root.exists())
        self.assertIn("Write generated text artifacts as UTF-8", LANGUAGE_POLICY)
        self.assertIn("do not transliterate French to ASCII", LANGUAGE_POLICY)

    def test_relative_links_survive_project_relocation(self):
        self.install()
        moved = self.base / "relocated project"
        self.root.parent.parent.rename(moved)
        import re
        for file in (moved / ".github").rglob("*.md"):
            if "runtime" in file.parts:
                continue
            for target in re.findall(r"\]\(<([^>]+)>\)", file.read_text(encoding="utf-8")):
                self.assertTrue((file.parent / target).is_file(), (file, target))
        relocated_root = moved / ".github/egm-copilot"
        install(self.source, relocated_root, moved / ".github/skills", moved / ".github/agents", "test")
        uninstall(relocated_root)
        self.assertTrue(moved.exists())
        self.assertFalse(relocated_root.exists())

    def test_user_scope_does_not_change_vscode_settings(self):
        home = self.base / "fake home"
        prompts = home / "Code profile/prompts"
        prompts.mkdir(parents=True)
        settings = prompts.parent / "settings.json"
        settings.write_text('{"existing": true}', encoding="utf-8")
        options = ["--scope", "user", "--vscode-prompts-dir", str(prompts)]
        with patch("pathlib.Path.home", return_value=home), redirect_stdout(io.StringIO()):
            self.assertEqual(main(["install", *options, "--source", str(self.source)]), 0)
            self.assertTrue((home / ".copilot/skills/egm-review/SKILL.md").is_file())
            self.assertTrue((prompts / "egm.agent.md").is_file())
            self.assertEqual(main(["status", *options]), 0)
            self.assertEqual(main(["uninstall", *options]), 0)
        self.assertEqual(settings.read_text(encoding="utf-8"), '{"existing": true}')

    def test_user_scope_defaults_to_native_copilot_directory(self):
        home = self.base / "native home"
        with patch("pathlib.Path.home", return_value=home), redirect_stdout(io.StringIO()):
            self.assertEqual(main(["install", "--scope", "user", "--source", str(self.source)]), 0)
            self.assertTrue((home / ".copilot/agents/egm.agent.md").is_file())
            self.assertEqual(main(["uninstall", "--scope", "user"]), 0)

    def test_status_detects_missing_files_and_install_repairs_them(self):
        self.install()
        missing = self.agents / "egm.agent.md"
        missing.unlink()
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(["status", "--project", str(self.root.parent.parent)]), 1)
        self.install()
        self.assertTrue(missing.is_file())

    def test_project_cli(self):
        self.assertEqual(main([
            "install", "--project", str(self.base / "cli project"),
            "--source", str(self.source),
        ]), 0)
        manifest = self.base / "cli project/.github/egm-copilot/manifest.json"
        self.assertEqual(json.loads(manifest.read_text(encoding="utf-8"))["revision"], "local-unverified")

    @unittest.skipIf(os.name == "nt" or not shutil.which("bash"), "Requires Linux Bash")
    def test_linux_installer_from_another_directory(self):
        self.run_installer(["bash", str(Path(__file__).resolve().parents[1] / "install.sh")])

    @unittest.skipUnless(shutil.which("pwsh") or shutil.which("powershell"), "Requires PowerShell")
    def test_windows_installer_from_another_directory(self):
        shell = shutil.which("pwsh") or shutil.which("powershell")
        self.run_installer([
            shell, "-NoProfile", "-NonInteractive", "-File",
            str(Path(__file__).resolve().parents[1] / "install.ps1"),
        ])

    @unittest.skipUnless(os.name == "nt", "Requires Windows PowerShell")
    def test_windows_portable_python_fallback(self):
        wrapper = self.base / "bootstrap.ps1"
        wrapper.write_text(r"""
$ErrorActionPreference = 'Stop'
function Get-Command {
    param($Name, $ErrorAction)
    if ($env:EGM_TEST_SCENARIO -eq 'empty-launcher' -and $Name -eq 'py') {
        [PSCustomObject]@{ Source = 'Invoke-EmptyLauncher' }
    }
}
function Invoke-EmptyLauncher { $global:LASTEXITCODE = 103 }
function Invoke-WebRequest {
    param($Uri, $OutFile, [switch]$UseBasicParsing)
    Set-Content -LiteralPath $env:EGM_TEST_DOWNLOAD -Value $Uri
    if ($env:EGM_TEST_SCENARIO -eq 'download-error') { throw 'Test download failed' }
    Set-Content -LiteralPath $OutFile -Value 'Mock archive'
}
function Get-FileHash {
    param($LiteralPath, $Algorithm)
    $hash = '90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159'
    if ($env:EGM_TEST_SCENARIO -eq 'hash-error') { $hash = 'invalid' }
    [PSCustomObject]@{ Hash = $hash }
}
function Expand-Archive {
    param($LiteralPath, $DestinationPath)
    Set-Content -LiteralPath $env:EGM_TEST_EXTRACTED -Value 'extracted'
    Set-Item -Path "Function:\global:$DestinationPath\python.exe" -Value {
        if ($env:EGM_TEST_SCENARIO -eq 'installer-error') {
            $global:LASTEXITCODE = 23
            return
        }
        & $env:EGM_TEST_PYTHON -I @args
        $global:LASTEXITCODE = $LASTEXITCODE
    }
}
$previousProtocol = [Net.ServicePointManager]::SecurityProtocol
try {
    & $env:EGM_TEST_INSTALLER @args
    $code = $LASTEXITCODE
} finally {
    [IO.File]::WriteAllText($env:EGM_TEST_RESTORED, $env:PYTHONPATH)
    if ([Net.ServicePointManager]::SecurityProtocol -ne $previousProtocol) {
        throw 'TLS settings were not restored'
    }
}
exit $code
""", encoding="ascii")
        shells = {shutil.which("powershell"), shutil.which("pwsh")} - {None}
        scenarios = ("missing", "empty-launcher", "download-error", "hash-error",
                     "installer-error", "explicit-invalid")
        for shell in sorted(shells):
            for scenario in scenarios:
                with self.subTest(shell=shell, scenario=scenario):
                    case = self.base / Path(shell).stem / scenario
                    case.mkdir(parents=True)
                    temporary = case / "temp"
                    temporary.mkdir()
                    project = case / "project with spaces"
                    download = case / "download.txt"
                    extracted = case / "extracted.txt"
                    restored = case / "restored.txt"
                    result = subprocess.run(
                        [shell, "-NoProfile", "-NonInteractive", "-File", str(wrapper),
                         "--project", str(project), "--source", str(self.source)],
                        cwd=self.base, capture_output=True, text=True,
                        env={
                            **os.environ,
                            "EGM_PYTHON": "missing-egm-python" if scenario == "explicit-invalid" else "",
                            "EGM_TEST_SCENARIO": scenario,
                            "EGM_TEST_PYTHON": sys.executable,
                            "EGM_TEST_INSTALLER": str(Path(__file__).resolve().parents[1] / "install.ps1"),
                            "EGM_TEST_DOWNLOAD": str(download),
                            "EGM_TEST_EXTRACTED": str(extracted),
                            "EGM_TEST_RESTORED": str(restored),
                            "PROCESSOR_ARCHITECTURE": "AMD64",
                            "PROCESSOR_ARCHITEW6432": "AMD64",
                            "PYTHONPATH": "original python path",
                            "TEMP": str(temporary),
                            "TMP": str(temporary),
                        },
                    )
                    self.assertEqual(list(temporary.iterdir()), [])
                    self.assertEqual(restored.read_text(), "original python path")
                    self.assertIn("[EGM] Searching for Python 3.10+...", result.stdout)
                    if scenario == "explicit-invalid":
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn("EGM_PYTHON", result.stderr)
                        self.assertFalse(download.exists())
                        self.assertNotIn("[EGM] Installation completed.", result.stdout)
                        continue
                    self.assertIn("Downloading portable Python", result.stdout)
                    self.assertIn("[EGM] Removing temporary portable Python files...", result.stdout)
                    self.assertEqual("Verifying portable Python archive" in result.stdout,
                                     scenario != "download-error")
                    self.assertEqual("Extracting portable Python" in result.stdout,
                                     scenario not in ("download-error", "hash-error"))
                    self.assertTrue(download.exists(), result.stdout + result.stderr)
                    self.assertIn("https://www.python.org/", download.read_text())
                    self.assertEqual(extracted.exists(),
                                     scenario not in ("download-error", "hash-error"))
                    if scenario in ("missing", "empty-launcher"):
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertTrue((project / ".github/agents/egm.agent.md").is_file())
                        self.assertIn("[EGM] Installing EGM...", result.stdout)
                        self.assertIn("[EGM] Installation completed.", result.stdout)
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertNotIn("[EGM] Installation completed.", result.stdout)
                        self.assertFalse((project / ".github").exists())
                        if scenario == "installer-error":
                            self.assertEqual(result.returncode, 23)
                            self.assertIn("[EGM] Installation failed (exit code 23).", result.stdout)
                        else:
                            self.assertIn("download failed" if scenario == "download-error"
                                          else "SHA-256", result.stderr)

    def run_installer(self, command):
        project = self.base / "projet été avec espaces"
        result = subprocess.run(
            [*command, "--project", str(project), "--source", str(self.source)],
            cwd=self.base, capture_output=True, text=True,
            env={**os.environ, "EGM_PYTHON": sys.executable},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((project / ".github/agents/egm.agent.md").is_file())


if __name__ == "__main__":
    unittest.main()