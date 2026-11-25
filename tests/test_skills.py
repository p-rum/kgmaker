"""Target-project installation contracts, independent of instruction wording."""

from pathlib import Path

import pytest

from kgmaker.cli import init, main
from kgmaker.skills import SKILL_FILES


def snapshot(root):
    return {
        p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in root.rglob("*") if p.is_file() and not p.is_symlink()
    }


def test_init_installs_complete_skills_and_local_references(tmp_path, capsys):
    assert init(tmp_path) == 0
    output = capsys.readouterr().out
    entrypoints = [p for p in SKILL_FILES if p.name == "SKILL.md"]
    assert len(entrypoints) == 6
    for path, text in SKILL_FILES.items():
        assert (tmp_path / path).read_text(encoding="utf-8") == text
        assert path.as_posix() in output
    excel = (tmp_path / ".agents/skills/kgmaker-excel-migration/SKILL.md").read_text(encoding="utf-8")
    assert "Never run any workbook macro or execute workbook code under any circumstances." in excel
    assert "Do not open or preview the workbook in Excel, LibreOffice" in excel
    # Relative Markdown references resolve in an installed project, without docs/.
    import re
    for path in entrypoints:
        for relative in re.findall(r"\]\((references/[^)]+)\)", SKILL_FILES[path]):
            assert (tmp_path / path.parent / relative).is_file()
    assert not (tmp_path / "docs").exists()
    assert not (tmp_path / ".codex").exists()
    assert not (tmp_path / ".agents/skills/kgmaker").exists()


def test_repository_skill_copies_match_distributed_templates():
    root = Path(__file__).resolve().parents[1]
    for path, text in SKILL_FILES.items():
        assert (root / path).read_text(encoding="utf-8") == text, str(path)


def test_upgrade_adds_excel_migration_skill_to_existing_installation(tmp_path, monkeypatch):
    from kgmaker.installation import run

    relative = Path(".agents/skills/kgmaker-excel-migration/SKILL.md")
    with monkeypatch.context() as old_release:
        old_release.delitem(SKILL_FILES, relative)
        assert init(tmp_path) == 0
        assert not (tmp_path / relative).exists()

    assert run(tmp_path, "upgrade") == 0
    assert (tmp_path / relative).read_text(encoding="utf-8") == SKILL_FILES[relative]


def test_repeated_init_keeps_bytes_mtimes_and_user_edits(tmp_path):
    assert init(tmp_path) == 0
    for relative in SKILL_FILES:
        (tmp_path / relative).write_text("User-owned customization\n", encoding="utf-8")
    foreign = tmp_path / ".agents/skills/team-specific/SKILL.md"
    foreign.parent.mkdir()
    foreign.write_text("Own team skill\n", encoding="utf-8")
    instructions = tmp_path / ".github/copilot-instructions.md"
    instructions.write_text("Our target project instructions\n", encoding="utf-8")
    before = snapshot(tmp_path)
    assert init(tmp_path) == 0
    assert snapshot(tmp_path) == before


def test_explicit_force_restores_declared_templates_only(tmp_path):
    assert init(tmp_path) == 0
    first = next(iter(SKILL_FILES))
    (tmp_path / first).write_text("modified", encoding="utf-8")
    foreign = tmp_path / ".agents/skills/custom.txt"
    foreign.write_text("preserve", encoding="utf-8")
    assert init(tmp_path, force=True) == 0
    assert (tmp_path / first).read_text(encoding="utf-8") == SKILL_FILES[first]
    assert foreign.read_text(encoding="utf-8") == "preserve"


@pytest.mark.parametrize("force", [False, True])
@pytest.mark.parametrize("relative", [
    ".agents", ".agents/skills", ".agents/skills/kgmaker-context",
    ".agents/skills/kgmaker-context/SKILL.md",
    ".agents/skills/kgmaker-testgen/references",
    ".agents/skills/kgmaker-testgen/references/candidate.md",
])
def test_symlink_collision_has_zero_mutation(tmp_path, force, relative, capsys):
    root, outside = tmp_path / "target", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "user.txt").write_text("must survive", encoding="utf-8")
    link = root / relative
    link.parent.mkdir(parents=True, exist_ok=True)
    target = outside / "user.txt" if link.suffix else outside
    link.symlink_to(target, target_is_directory=target.is_dir())
    before = snapshot(tmp_path)
    before_paths = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    assert init(root, force=force) == 2
    assert link.is_symlink()
    assert snapshot(tmp_path) == before
    assert {p.relative_to(tmp_path) for p in tmp_path.rglob("*")} == before_paths
    assert "Symlink" in capsys.readouterr().err


@pytest.mark.parametrize("relative,is_dir", [
    (".agents", False),
    (".agents/skills/kgmaker-context/SKILL.md", True),
    (".agents/skills/kgmaker-testgen/references", False),
    (".agents/skills/kgmaker-testgen/references/candidate.md", True),
])
def test_non_regular_destination_has_zero_mutation(tmp_path, relative, is_dir):
    collision = tmp_path / relative
    collision.parent.mkdir(parents=True, exist_ok=True)
    if is_dir:
        collision.mkdir()
    else:
        collision.write_text("preserve", encoding="utf-8")
    before = snapshot(tmp_path)
    before_paths = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    assert init(tmp_path) == 2
    assert snapshot(tmp_path) == before
    assert {p.relative_to(tmp_path) for p in tmp_path.rglob("*")} == before_paths


def test_scan_does_not_install_skills(tmp_path, monkeypatch):
    (tmp_path / "sample.py").write_text("def example():\n    return 1\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["kgmaker", "scan", "--root", str(tmp_path)])
    with pytest.raises(SystemExit) as exit_info:
        main()
    assert exit_info.value.code == 0
    assert not (tmp_path / ".agents").exists()


def test_init_cli_accepts_root_outside_working_directory(tmp_path, monkeypatch):
    cwd, target = tmp_path / "cwd", tmp_path / "target"
    cwd.mkdir()
    target.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setattr("sys.argv", ["kgmaker", "init", "--root", str(target)])
    with pytest.raises(SystemExit) as exit_info:
        main()
    assert exit_info.value.code == 0
    assert not list(cwd.iterdir())
    assert all((target / path).is_file() for path in SKILL_FILES)


def reference_example(name, filename):
    """Exercise published JSON examples against the actual runtime contracts."""
    import json
    import re

    text = SKILL_FILES[Path(f".agents/skills/{name}/references/{filename}")]
    return json.loads(re.search(r"```json\n(.*?)\n```", text, re.S).group(1))


def test_data_audit_reference_runs_through_feature_validators(tmp_path):
    from kgmaker import feature
    from kgmaker.data_check import data_check

    (tmp_path / "Account.kt").write_text("data class Account(val balance: Double)\n")
    requirement = "Use the account balance."
    (tmp_path / "requirement.md").write_text(requirement)
    analysis = "the-current-analysis-id"
    packet = feature.prepare(tmp_path, "requirement.md", analysis)
    specification = reference_example("kgmaker-data-audit", "data-requirements.md")
    specification["requirement_hash"] = packet["requirement_hash"]
    specification["requirements"][0].update(text=requirement, source_quote=requirement)
    specification["inputs"][0]["name"] = "balance"
    before = snapshot(tmp_path)
    result = data_check(tmp_path, analysis, specification)
    assert result["valid"], result
    assert snapshot(tmp_path) == before
    candidate = result["candidate"]
    assert candidate["input_requirements"][0]["availability"] == "UNKNOWN"
    assert feature.validate(tmp_path, analysis, candidate)["valid"]
    assert feature.apply(tmp_path, analysis, candidate)["valid"]


def test_testgen_reference_validates_without_export_or_execution(tmp_path):
    from kgmaker import testgen

    (tmp_path / "src").mkdir()
    code = "def example(value):\n    return value * 2\n"
    (tmp_path / "src/example.py").write_text(code)
    packet = testgen.prepare(tmp_path, "current-suite-id", "src/example.py", framework="unittest")
    candidate = reference_example("kgmaker-testgen", "candidate.md")
    candidate["packet_id"] = packet["packet_id"]
    candidate["cases"][0]["target_ids"] = [packet["target"]["id"]]
    source = next(item for item in packet["sources"] if item["path"] == "src/example.py")
    for citation in [candidate["cases"][0]["expected"]["citations"][0],
                     candidate["datasets"][0]["citations"][0]]:
        citation.update(sha256=source["sha256"], quote=code.rstrip())
    before = snapshot(tmp_path)
    result = testgen.validate(tmp_path, "current-suite-id", candidate)
    assert result["valid"], result
    assert snapshot(tmp_path) == before
    assert testgen.apply(tmp_path, "current-suite-id", candidate)["valid"]
    assert not (tmp_path / "tests").exists()
    assert testgen.report(tmp_path, "current-suite-id")["execution"] == "NOT_RUN"
