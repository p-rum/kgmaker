import json
from pathlib import Path

import pytest

from kgmaker.completion import INVENTORY, plan, run


def write_inventory(root, entries):
    tasks = root / "docs/tasks"
    tasks.mkdir(parents=True, exist_ok=True)
    lines = []
    for item, delivery, verification, dependency, owner in entries:
        (tasks / f"{item}.md").write_text(
            f"# {item}\n\n- Depends on: {dependency}\n", encoding="utf-8")
        lines.append(
            f"| [{item}](tasks/{item}.md) | {delivery} | {verification} | "
            f"baseline | source | — | {owner} |")
    (root / INVENTORY).write_text("\n".join(lines), encoding="utf-8")


def test_priority_ready_and_blocked_work(tmp_path):
    write_inventory(tmp_path, [
        ("T001", "MERGED", "FAIL", "baseline", "cache regression"),
        ("T002", "PLANNED", "NOT_RUN", "T001", "reverse dependency index"),
        ("T003", "PR_OPEN", "NOT_RUN", "baseline", "review"),
        ("T004", "PLANNED", "NOT_RUN", "baseline", "oracle"),
        ("T005", "PLANNED", "NOT_RUN", "T097", "unverified"),
        ("T006", "PLANNED", "NOT_RUN", "baseline", "Upstream owner: T001"),
        ("T007", "MERGED", "PARTIAL; bounded subset VERIFIED_IN_SCOPE", "T001", "history"),
        ("T008", "PLANNED", "NOT_RUN", "T007; requirement T001-R01", "indirect"),
        ("T009", "PLANNED", "NOT_RUN", "T0A1", "invalid dependency"),
    ])
    before = {p: p.read_bytes() for p in tmp_path.rglob("*.md")}
    result = plan(tmp_path, jobs=2)
    assert result["dispatch"] == ["T001", "T003"]
    assert result["items"]["T002"]["blockers"] == ["T001: MERGED/FAIL"]
    assert result["items"]["T005"]["blockers"] == ["T097: dependency requires source review"]
    assert result["items"]["T006"]["action"] == "shared"
    assert result["items"]["T007"]["verification"] == "PARTIAL"
    assert result["items"]["T008"]["dependencies"] == ("T007",)
    assert result["items"]["T008"]["blockers"] == ["T001: indirect dependency FAIL"]
    assert result["items"]["T009"]["dependencies"] is None
    assert result["items"]["T009"]["blockers"] == ["dependency declaration requires source review"]
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*.md")}
    assert plan(tmp_path, jobs=3)["dispatch"] == ["T001", "T003", "T004"]


def test_cycle_rejected_without_dispatch(tmp_path):
    write_inventory(tmp_path, [
        ("T001", "PLANNED", "NOT_RUN", "T002", "cycle"),
        ("T002", "PLANNED", "NOT_RUN", "[T001](T001.md)", "cycle"),
    ])
    with pytest.raises(ValueError, match=r"dependency cycle.*T00"):
        plan(tmp_path)


def test_real_inventory_is_readable_without_a_network_or_a_graph():
    root = Path(__file__).resolve().parents[1]
    result = plan(root, jobs=4)
    assert len(result["items"]) >= 119
    assert "T003-S09-W05" in result["items"]["T003-S10-W01"]["dependencies"]
    assert result["items"]["T047-S01"]["dependencies"] == ()
    assert "T003-S10-W03" in result["items"]["T047-S04"]["dependencies"]
    assert "T003-S10-W02" in result["items"]["T003-S10-W04"]["dependencies"]
    assert "T021" in result["items"]["T022"]["dependencies"]
    assert result["items"]["T025"]["dependencies"] == (
        "T003-S04-W01", "T003-S04-W02", "T003-S04-W03", "T003-S04-W04",
        "T003-S04-W05", "T023", "T024",
    )
    assert "T025" in result["items"]["T043"]["dependencies"]
    assert "T003-S12-W01" not in result["items"]["T003-S12-W01"]["dependencies"]
    assert "T003-S12" in result["items"]["T003-S12-W01"]["dependencies"]
    assert result["items"]["T047-S10"]["conditional_dependencies"] == ("T047-S02",)
    assert "T047-S02" not in result["items"]["T047-S10"]["dependencies"]
    assert "T003-S11-W07" not in result["items"]["T047-S13"]["dependencies"]


def test_t003_umbrella_blocks_only_until_all_documented_packages_are_delivered(tmp_path):
    packages = [
        ("T003-S04-W01", "MERGED", "PARTIAL", "baseline", "history"),
        ("T003-S04-W02", "PLANNED", "NOT_RUN", "baseline", "pending"),
    ]
    repair = ("T025", "MERGED", "FAIL", "T003-S04", "regression")
    write_inventory(tmp_path, [*packages, repair])
    result = plan(tmp_path, jobs=2)
    assert result["items"]["T025"]["blockers"] == ["T003-S04-W02: PLANNED/NOT_RUN"]
    packages[1] = ("T003-S04-W02", "MERGED", "PARTIAL", "baseline", "history")
    write_inventory(tmp_path, [*packages, repair])
    assert plan(tmp_path)["dispatch"] == ["T025"]


def test_cli_reports_invalid_inventory_without_payload(tmp_path, capsys):
    from types import SimpleNamespace

    write_inventory(tmp_path, [("T001", "WRONG", "NOT_RUN", "baseline", "invalid")])
    assert run(SimpleNamespace(root=tmp_path, jobs=1)) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "T001" in captured.err


def test_cli_emits_json(tmp_path, capsys):
    from types import SimpleNamespace

    write_inventory(tmp_path, [("T001", "PLANNED", "NOT_RUN", "baseline", "work")])
    assert run(SimpleNamespace(root=tmp_path, jobs=1)) == 0
    assert json.loads(capsys.readouterr().out)["dispatch"] == ["T001"]


def test_failed_offline_boundary_is_reviewable_without_a_self_cycle(tmp_path):
    item = "T003-S12-W01"
    write_inventory(tmp_path, [(item, "MERGED", "FAIL", "offline boundary T003-S12", "repair")])
    result = plan(tmp_path)
    assert result["items"][item]["action"] == "repair"
    assert result["items"][item]["blockers"] == ["T003-S12: dependency requires source review"]
