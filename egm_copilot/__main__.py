import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from egm_copilot import __version__


UPSTREAM = "https://github.com/google/elephant-goldfish-model.git"
REVISION = "72d06f52a2482885d9a64bd24b291c6e8628942c"
SKILLS = (
    "egm-brainstorm", "egm-draft", "egm-review", "egm-review-loop",
    "egm-resolve", "egm-bootstrap", "egm-drift-report",
)
REVIEWERS = {
    "egm-design": "design_critic.md",
    "egm-codebase-details": "codebase_details.md",
    "egm-comprehension": "comprehension.md",
    "egm-implementation-readiness": "implementation_readiness.md",
    "egm-structural": "structural.md",
    "egm-style": "style.md",
    "egm-zoom-out": "zoom_out.md",
    "egm-inventive-catalyst": "inventive_catalyst.md",
}
RUNTIME_DIRS = ("skills", "agents", "resources", "docs", "assets", "com.github.copilot")
RUNTIME_FILES = ("LICENSE", "README.md", "plugin.json")

LANGUAGE_POLICY = """## Working language (VS Code adapter override)

Use the language explicitly requested by the user for conversation, drafts,
specifications and review reports. Otherwise use the conversation's language.
French is fully supported: do not refuse or postpone egm-draft because the
brief, request or desired artifact is in French. Do not require an English
translation before continuing.
This language policy overrides English-only requirements in canonical EGM
skills, personas and document standards. Interpret "Plain-English" as clear,
direct language, not as a requirement to write in English. Keep all other
workflow rules and human approval gates unchanged.
Keep canonical filenames, paths, code identifiers and machine-required markers
unchanged; retain headings verbatim when a workflow requires exact headings.
Pass the chosen output language explicitly in each reviewer task without
forwarding conversation history. Reviewers must apply this policy as well.
"""


def digest(content):
    return hashlib.sha256(content).hexdigest()


def text(content):
    return content.encode("utf-8")


def link(source, target):
    return "<" + relative_path(target, source.parent) + ">"


def relative_path(target, base):
    try:
        return Path(os.path.relpath(target, base)).as_posix()
    except ValueError:
        return target.as_posix()


def locations(args):
    if args.scope == "project":
        github = args.project.expanduser().resolve() / ".github"
        return github / "egm-copilot", github / "skills", github / "agents"
    home = Path.home() / ".copilot"
    agents_dir = args.vscode_prompts_dir.expanduser().resolve() if args.vscode_prompts_dir else home / "agents"
    return home / "egm-copilot", home / "skills", agents_dir


def adapter_guide():
    return """# EGM for VS Code (experimental)

This file's parent directory is the installed EGM package root (EGM_ROOT).
Resolve it to an absolute path using the file-reading tool, not the terminal.
Read the requested canonical skills/<name>/SKILL.md in this package first.
Read referenced agents/, resources/, docs/ and skill references from this
package, not from similarly named files in the user's project. Resolve user
documents and artifacts against the user's project working directory. Never
change the working directory to the package. Stop if a resource is missing.
When a workflow calls another EGM skill, read its canonical SKILL.md here.

## Native delegation

Use the VS Code native agent delegation tool. Inspect its actual schema.
Delegate directly to the installed egm-design, egm-codebase-details,
egm-comprehension, egm-implementation-readiness, egm-structural, egm-style,
egm-zoom-out or egm-inventive-catalyst profiles, without a namespace prefix.
Use a new child for every invocation. Pass only the task, absolute package
root, target, ranges, persona, standards and explicit reading list. Never
forward parent conversation, memory, private rationale or expected answers.
Do not use a reviewer as the main conversation. If a required profile or
fresh-context delegation is unavailable, stop: an inline review is not a
Goldfish review. A failed, denied or incomplete child is not a passing review.

For synthesizer steps, read agents/synthesizer.md, delegate directly to the
required reviewers, then synthesize in the main session. Reviewers have only
read and search tools; they return findings and paths read without writing.
Do not grant extra tools or run nested delegation. Keep all artifact writes
in the main session. For bootstrap, stop if the workflow needs worker tools
that the installed profiles cannot provide; do not silently broaden access.

## Human gates and limits

Follow the canonical workflow, approval gates, stage order and artifact names.
Ask one plain-text question and wait when a question tool is unavailable.
Do not treat tool absence as approval. Honor EGM artifact directory when supplied.
Do not claim instruction exclusion: VS Code can inject project or user
instructions. Fresh conversation context is not filesystem isolation.
This adapter does not validate model behavior.

""" + LANGUAGE_POLICY


def build_files(source, root, skills_dir, agents_dir):
    runtime = root / "runtime"
    required = [source / "skills" / name / "SKILL.md" for name in SKILLS]
    required.extend(source / "agents" / name for name in REVIEWERS.values())
    required.extend(source / name for name in RUNTIME_FILES)
    required.extend((source / "agents/synthesizer.md", source / "resources/document_standards"))
    if any(not path.exists() for path in required):
        raise ValueError("Incomplete EGM source: skills, personas, standards and license are required.")
    files = {}
    for name in (*RUNTIME_DIRS, *RUNTIME_FILES):
        origin = source / name
        if not origin.exists():
            raise ValueError(f"Missing EGM runtime resource: {origin}")
        candidates = sorted(origin.rglob("*")) if origin.is_dir() else [origin]
        for candidate in candidates:
            if candidate.is_symlink():
                raise ValueError(f"Symbolic links are not accepted in the EGM source: {candidate}")
            if candidate.is_file():
                files[runtime / candidate.relative_to(source)] = candidate.read_bytes()
    guide = runtime / "VSCODE.md"
    files[guide] = text(adapter_guide())
    for name in SKILLS:
        destination = skills_dir / name / "SKILL.md"
        files[destination] = text(
            f"---\nname: {name}\ndescription: 'Use {name} with the Elephant-Goldfish Model in VS Code.'\n"
            "disable-model-invocation: true\n---\n\n"
            f"Read the [VS Code adapter guide]({link(destination, guide)}) first.\n"
            f"Then read and execute the [canonical {name} workflow]"
            f"({link(destination, runtime / 'skills' / name / 'SKILL.md')}).\n"
            "Preserve the user's arguments and follow all human approval gates.\n"
            "\n" + LANGUAGE_POLICY
        )
    destination = agents_dir / "egm.agent.md"
    files[destination] = text(
        "---\nname: egm\ndescription: 'Design and review with EGM in VS Code.'\n"
        "tools: [read, search, edit, agent]\n---\n\n"
        f"Read the [VS Code adapter guide]({link(destination, guide)}) before work.\n"
        "Ask which EGM workflow to run if none was requested. Read that workflow's\n"
        "canonical SKILL.md from the installed package. Follow its human gates.\n"
        "Delegate Goldfish reviews only to the installed read-only reviewer profiles.\n"
        "\n" + LANGUAGE_POLICY
    )
    for name, persona in REVIEWERS.items():
        destination = agents_dir / f"{name}.agent.md"
        files[destination] = text(
            f"---\nname: {name}\ndescription: 'EGM {name} read-only Goldfish reviewer.'\n"
            "tools: [read, search]\nuser-invocable: false\n---\n\n"
            f"Read the [canonical persona]({link(destination, runtime / 'agents' / persona)}) first.\n"
            "Use only the assigned task and explicit reading list. The caller must\n"
            "supply absolute paths to the installed package, target and standards.\n"
            "Read bundled standards only under that package's resources/document_standards/.\n"
            "Do not retrieve parent history or memory. Read prior reports only when\n"
            "explicitly supplied and required by this workflow stage. Do not edit,\n"
            "execute commands, delegate or use MCP tools. Return findings and paths\n"
            "read to the caller. Missing resources mean an incomplete review.\n"
            "Do not claim isolation or tool enforcement from self-report.\n"
            "\n" + LANGUAGE_POLICY
        )
    return files


def load_manifest(root):
    path = root / "manifest.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("package") != "egm-copilot" or data.get("schema") != 1:
        raise ValueError("Unrecognized installation manifest.")
    return data


def managed_files(root, manifest):
    return {os.path.abspath(root / path): checksum for path, checksum in manifest.get("files", {}).items()}


def check_managed(root, old, files, require_present=False):
    previous = managed_files(root, old)
    for filename in set(previous) | {str(path) for path in files}:
        path = Path(filename)
        if path.is_symlink():
            raise ValueError(f"Refusing symbolic-link destination: {path}")
        if require_present and not path.exists():
            raise ValueError(f"Missing installed file: {path}")
        if path.exists():
            if not path.is_file() or filename not in previous:
                raise ValueError(f"Existing unmanaged file; nothing changed: {path}")
            if digest(path.read_bytes()) != previous[filename]:
                raise ValueError(f"Modified installed file; nothing changed: {path}")


def apply_files(files, removed):
    affected = set(files) | set(removed)
    before = {path: path.read_bytes() if path.exists() else None for path in affected}
    try:
        for path, content in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
                temporary.write(content)
                temporary_path = Path(temporary.name)
            try:
                temporary_path.replace(path)
            finally:
                temporary_path.unlink(missing_ok=True)
        for path in removed:
            path.unlink(missing_ok=True)
    except OSError:
        for path, content in before.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(content)
        raise


def install(source, root, skills_dir, agents_dir, revision):
    old = load_manifest(root)
    files = build_files(source, root, skills_dir, agents_dir)
    check_managed(root, old, files)
    manifest = {
        "schema": 1, "package": "egm-copilot", "version": __version__,
        "upstream": UPSTREAM, "revision": revision,
        "directories": [relative_path(path, root) for path in (root, skills_dir, agents_dir)],
        "files": {relative_path(path, root): digest(content) for path, content in files.items()},
    }
    removed = {Path(path) for path in managed_files(root, old)} - set(files)
    files[root / "manifest.json"] = text(json.dumps(manifest, indent=2) + "\n")
    apply_files(files, removed)


def uninstall(root):
    manifest = load_manifest(root)
    if not manifest:
        raise ValueError(f"No EGM Copilot installation found at {root}")
    check_managed(root, manifest, {})
    removed = {Path(path) for path in managed_files(root, manifest)} | {root / "manifest.json"}
    apply_files({}, removed)
    boundaries = [(root / path).resolve() for path in manifest["directories"]]
    directories = {
        parent for file in removed for parent in file.parents
        if any(parent == boundary or boundary in parent.parents for boundary in boundaries)
    }
    for path in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass


def fetch_source(destination, revision):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("--revision must be a full lowercase 40-character commit SHA.")
    for command in (
        ["git", "init", "--quiet", str(destination)],
        ["git", "-C", str(destination), "fetch", "--quiet", "--depth=1", UPSTREAM, revision],
        ["git", "-C", str(destination), "checkout", "--quiet", "--detach", "FETCH_HEAD"],
    ):
        subprocess.run(command, check=True)
    actual = subprocess.check_output(
        ["git", "-C", str(destination), "rev-parse", "HEAD"], text=True,
    ).strip()
    if actual != revision:
        raise ValueError("Downloaded EGM revision does not match the requested commit.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install EGM for GitHub Copilot in VS Code.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("command", choices=("install", "uninstall", "status"))
    parser.add_argument("--scope", choices=("project", "user"), default="project")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--vscode-prompts-dir", type=Path, help="Override the user agent directory (legacy VS Code profiles).")
    parser.add_argument("--source", type=Path, help="Use a trusted local complete EGM checkout (offline).")
    parser.add_argument("--revision", default=REVISION, help="Full upstream commit SHA for network installs.")
    args = parser.parse_args(argv)
    root, skills_dir, agents_dir = locations(args)
    try:
        if args.command == "status":
            manifest = load_manifest(root)
            if not manifest:
                raise ValueError(f"No EGM Copilot installation found at {root}")
            check_managed(root, manifest, {}, require_present=True)
            print(json.dumps(manifest, indent=2))
        elif args.command == "uninstall":
            uninstall(root)
            print(f"EGM Copilot removed: {root}")
        else:
            if args.source:
                install(args.source.expanduser().resolve(), root, skills_dir, agents_dir, "local-unverified")
            else:
                if not shutil.which("git"):
                    raise ValueError("Git is required for downloading EGM. Install Git or use --source.")
                with tempfile.TemporaryDirectory(prefix="egm-copilot-") as temporary:
                    source = Path(temporary) / "upstream"
                    fetch_source(source, args.revision)
                    install(source, root, skills_dir, agents_dir, args.revision)
            print(f"EGM Copilot installed: {root}\nReload VS Code, select the egm agent, then use /egm-brainstorm.")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"egm-copilot: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())