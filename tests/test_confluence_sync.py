"""T001 FA-28–30 / T003-AC12 offline synchronization boundary."""
from dataclasses import replace

import pytest

from kgmaker.analysis_model import AnalysisError
from kgmaker.confluence_sync import (
    FakeConfluenceAdapter,
    PageSnapshot,
    approve,
    audit_json,
    prepare_publish,
    publish_approved,
    pull_selected,
    save_pull_snapshot,
)


def page():
    return PageSnapshot("42", 7, "Analysis", "<h1>Analysis</h1>\n<p>Owner content</p>\n")


def test_pull_is_explicit_bounded_and_fake_is_not_live(tmp_path):
    adapter = FakeConfluenceAdapter([page()])
    snapshot = pull_selected(adapter, ["42"])
    assert snapshot["adapter_kind"] == "FAKE_TEST_ONLY"
    assert snapshot["live_connection"] is False
    assert snapshot["pages"][0]["version"] == 7
    saved = save_pull_snapshot(tmp_path, snapshot)
    assert saved.is_file()
    with pytest.raises(AnalysisError, match="Unknown"):
        pull_selected(adapter, ["missing"])


def test_fa28_page_version_change_after_approval_conflicts_without_overwrite():
    adapter = FakeConfluenceAdapter([page()])
    package = prepare_publish(page(), "feature-report", "<p>Proposed TO_BE report</p>")
    approval = approve(package, "decision-1")
    adapter.mutate_page("42", "<p>Concurrent owner edit</p>")
    with pytest.raises(AnalysisError, match="VERSION_CONFLICT") as error:
        publish_approved(adapter, package, approval)
    assert error.value.code == 3
    current = adapter.pull(["42"])[0]
    assert current.content == "<p>Concurrent owner edit</p>"
    assert current.version == 8


def test_fa29_payload_change_after_approval_is_rejected_before_adapter_write():
    adapter = FakeConfluenceAdapter([page()])
    package = prepare_publish(page(), "feature-report", "<p>First proposal</p>")
    approval = approve(package, "decision-1")
    forged = replace(package, proposed_section="<p>Changed proposal</p>")
    with pytest.raises(AnalysisError, match="payload changed"):
        publish_approved(adapter, forged, approval)
    assert adapter.pull(["42"])[0] == page()


def test_fa30_publish_preserves_owner_content_and_reimport_remains_to_be():
    adapter = FakeConfluenceAdapter([page()])
    package = prepare_publish(page(), "feature-report", "<p>Proposed report</p>")
    assert "Owner content" in package.proposed_content
    assert "kgmaker-managed:feature-report:start" in package.proposed_content
    assert "+<p>Proposed report</p>" in package.diff
    approval = approve(package, "decision-1")
    audit = publish_approved(adapter, package, approval)
    pulled = adapter.pull(["42"])[0]
    assert pulled.proposal_state == "TO_BE"
    assert pulled.version == 8
    assert audit.live_connection is False
    assert audit.proposal_state == "TO_BE"
    assert "Proposed report" not in audit_json(audit)


def test_approval_is_bound_to_package_page_and_base_version():
    package = prepare_publish(page(), "feature-report", "<p>Proposed report</p>")
    approval = approve(package, "decision-1")
    adapter = FakeConfluenceAdapter([page()])
    for forged in (
        replace(approval, page_id="different"),
        replace(approval, base_version=6),
        replace(approval, payload_hash="0" * 64),
        replace(approval, approval_id="forged"),
    ):
        with pytest.raises(AnalysisError, match="does not match"):
            publish_approved(adapter, package, forged)
    assert adapter.pull(["42"])[0] == page()
