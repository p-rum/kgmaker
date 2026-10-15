"""Explicit Confluence synchronization boundary with an offline fake adapter.

No URL, authentication scheme or live API behavior is guessed here. A real
connector must implement the same protocol for a documented host/version.
"""
from __future__ import annotations

import difflib
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Protocol

from .analysis_model import AnalysisError, canonical, digest, write_json

SCHEMA_VERSION = 1
MAX_PAGE_CHARS = 2_000_000


@dataclass(frozen=True)
class PageSnapshot:
    page_id: str
    version: int
    title: str
    content: str
    attachments: tuple[dict, ...] = ()
    source: str = "CONFLUENCE_ADAPTER"
    proposal_state: str | None = None


@dataclass(frozen=True)
class PublishPackage:
    schema_version: int
    package_id: str
    page_id: str
    base_version: int
    managed_section: str
    proposed_section: str
    current_content: str
    proposed_content: str
    diff: str
    payload_hash: str
    proposal_state: str = "TO_BE"


@dataclass(frozen=True)
class Approval:
    schema_version: int
    approval_id: str
    package_id: str
    page_id: str
    base_version: int
    payload_hash: str
    decision_id: str
    status: str = "APPROVED"


@dataclass(frozen=True)
class PublishAudit:
    schema_version: int
    adapter_kind: str
    live_connection: bool
    page_id: str
    old_version: int
    new_version: int
    payload_hash: str
    approval_id: str
    package_id: str
    proposal_state: str = "TO_BE"


class ConfluenceSyncAdapter(Protocol):
    adapter_kind: str
    live_connection: bool

    def pull(self, page_ids: list[str]) -> list[PageSnapshot]: ...

    def publish(self, page_id: str, expected_version: int, content: str,
                *, payload_hash: str, proposal_state: str) -> PageSnapshot: ...


def _validate_page(page: PageSnapshot) -> None:
    if not page.page_id or type(page.version) is not int or page.version < 1 or not page.title:
        raise AnalysisError("Confluence page requires ID, positive version and title")
    if not isinstance(page.content, str) or len(page.content) > MAX_PAGE_CHARS:
        raise AnalysisError("Confluence page content is invalid or exceeds the bounded size")
    if page.proposal_state not in {None, "TO_BE"}:
        raise AnalysisError("Pulled proposal state must remain TO_BE")


class FakeConfluenceAdapter:
    """Deterministic test adapter; it is explicitly never a live integration."""

    adapter_kind = "FAKE_TEST_ONLY"
    live_connection = False

    def __init__(self, pages: list[PageSnapshot]):
        self._pages: dict[str, PageSnapshot] = {}
        for page in pages:
            _validate_page(page)
            if page.page_id in self._pages:
                raise AnalysisError("Duplicate fake Confluence page ID")
            self._pages[page.page_id] = page

    def pull(self, page_ids: list[str]) -> list[PageSnapshot]:
        if not isinstance(page_ids, list) or not page_ids or len(set(page_ids)) != len(page_ids):
            raise AnalysisError("Pull requires unique explicit page IDs")
        missing = [page_id for page_id in page_ids if page_id not in self._pages]
        if missing:
            raise AnalysisError("Unknown Confluence page IDs: " + ", ".join(missing))
        return [self._pages[page_id] for page_id in page_ids]

    def publish(self, page_id: str, expected_version: int, content: str,
                *, payload_hash: str, proposal_state: str) -> PageSnapshot:
        page = self._pages.get(page_id)
        if page is None:
            raise AnalysisError("Confluence publish page is absent")
        if page.version != expected_version:
            raise AnalysisError(
                f"CONFLUENCE_VERSION_CONFLICT: expected {expected_version}, current {page.version}", 3
            )
        if proposal_state != "TO_BE":
            raise AnalysisError("Published proposal content must remain TO_BE")
        updated = replace(page, version=page.version + 1, content=content, proposal_state="TO_BE")
        self._pages[page_id] = updated
        return updated

    def mutate_page(self, page_id: str, content: str) -> None:
        """Simulate an independent writer for concurrency acceptance tests."""
        page = self._pages[page_id]
        self._pages[page_id] = replace(page, version=page.version + 1, content=content)


def pull_selected(adapter: ConfluenceSyncAdapter, page_ids: list[str]) -> dict:
    pages = adapter.pull(page_ids)
    for page in pages:
        _validate_page(page)
    return {"schema_version": SCHEMA_VERSION, "adapter_kind": adapter.adapter_kind,
            "live_connection": adapter.live_connection, "pages": [asdict(page) for page in pages]}


def save_pull_snapshot(root: Path, snapshot: dict, name: str = "pull-snapshot.json") -> Path:
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != SCHEMA_VERSION:
        raise AnalysisError("Invalid Confluence pull snapshot")
    target = root / ".kgmaker" / "confluence-sync" / name
    if target.resolve().parent != (root / ".kgmaker" / "confluence-sync").resolve():
        raise AnalysisError("Confluence snapshot filename must stay in its isolated directory")
    write_json(target, snapshot)
    return target


def _markers(section: str) -> tuple[str, str]:
    if not isinstance(section, str) or not section or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in section):
        raise AnalysisError("Managed Confluence section ID is invalid")
    return f"<!-- kgmaker-managed:{section}:start -->", f"<!-- kgmaker-managed:{section}:end -->"


def _replace_section(content: str, section: str, body: str) -> str:
    start, end = _markers(section)
    if start in body or end in body:
        raise AnalysisError("Proposed section must not contain management markers")
    first, last = content.find(start), content.find(end)
    if (first < 0) != (last < 0) or (first >= 0 and last < first):
        raise AnalysisError("Managed Confluence section markers are malformed")
    managed = f"{start}\n{body.rstrip()}\n{end}"
    if first < 0:
        return content.rstrip() + ("\n\n" if content.strip() else "") + managed + "\n"
    if content.find(start, first + len(start)) >= 0 or content.find(end, last + len(end)) >= 0:
        raise AnalysisError("Managed Confluence section markers are ambiguous")
    return content[:first] + managed + content[last + len(end):]


def prepare_publish(page: PageSnapshot, managed_section: str, proposed_section: str) -> PublishPackage:
    _validate_page(page)
    if not isinstance(proposed_section, str) or not proposed_section.strip() or len(proposed_section) > MAX_PAGE_CHARS:
        raise AnalysisError("Proposed Confluence section is empty or too large")
    proposed_content = _replace_section(page.content, managed_section, proposed_section)
    payload = {"schema_version": SCHEMA_VERSION, "page_id": page.page_id,
               "base_version": page.version, "managed_section": managed_section,
               "proposed_section": proposed_section, "current_content": page.content,
               "proposed_content": proposed_content, "proposal_state": "TO_BE"}
    payload_hash = digest(payload)
    package_id = "confluence-package:" + payload_hash
    diff = "".join(difflib.unified_diff(
        page.content.splitlines(keepends=True), proposed_content.splitlines(keepends=True),
        fromfile=f"page-{page.page_id}@{page.version}",
        tofile=f"page-{page.page_id}@proposed", lineterm="\n",
    ))
    return PublishPackage(**payload, package_id=package_id, diff=diff, payload_hash=payload_hash)


def _package_hash(package: PublishPackage) -> str:
    return digest({key: value for key, value in asdict(package).items()
                   if key not in {"package_id", "payload_hash", "diff"}})


def _package_diff(package: PublishPackage) -> str:
    return "".join(difflib.unified_diff(
        package.current_content.splitlines(keepends=True),
        package.proposed_content.splitlines(keepends=True),
        fromfile=f"page-{package.page_id}@{package.base_version}",
        tofile=f"page-{package.page_id}@proposed", lineterm="\n",
    ))


def _validate_package(package: PublishPackage) -> None:
    if package.schema_version != SCHEMA_VERSION or _package_hash(package) != package.payload_hash \
            or package.package_id != "confluence-package:" + package.payload_hash \
            or package.diff != _package_diff(package) or package.proposal_state != "TO_BE":
        raise AnalysisError("Confluence package integrity mismatch", 3)


def _approval_id(approval: Approval) -> str:
    value = {key: value for key, value in asdict(approval).items() if key != "approval_id"}
    return "confluence-approval:" + digest(value)


def approve(package: PublishPackage, decision_id: str) -> Approval:
    _validate_package(package)
    if not isinstance(decision_id, str) or not decision_id.strip():
        raise AnalysisError("Approval requires an explicit decision ID")
    value = {"schema_version": SCHEMA_VERSION, "package_id": package.package_id,
             "page_id": package.page_id, "base_version": package.base_version,
             "payload_hash": package.payload_hash, "decision_id": decision_id,
             "status": "APPROVED"}
    approval = Approval(**value, approval_id="")
    return replace(approval, approval_id=_approval_id(approval))


def publish_approved(adapter: ConfluenceSyncAdapter, package: PublishPackage,
                     approval: Approval) -> PublishAudit:
    try:
        _validate_package(package)
    except AnalysisError as exc:
        raise AnalysisError("Confluence payload changed after approval", 3) from exc
    expected = {"package_id": package.package_id, "page_id": package.page_id,
                "base_version": package.base_version, "payload_hash": package.payload_hash}
    if approval.status != "APPROVED" or approval.approval_id != _approval_id(approval) \
            or any(getattr(approval, key) != value for key, value in expected.items()):
        raise AnalysisError("Approval does not match the exact payload hash and base version", 3)
    updated = adapter.publish(package.page_id, package.base_version, package.proposed_content,
                              payload_hash=package.payload_hash, proposal_state=package.proposal_state)
    _validate_page(updated)
    if updated.version != package.base_version + 1 or updated.content != package.proposed_content:
        raise AnalysisError("Confluence adapter returned an inconsistent publish result", 3)
    return PublishAudit(
        SCHEMA_VERSION, adapter.adapter_kind, adapter.live_connection, package.page_id,
        package.base_version, updated.version, package.payload_hash, approval.approval_id,
        package.package_id,
    )


def audit_json(audit: PublishAudit) -> str:
    """Return a bounded audit record without page contents or credentials."""
    return canonical(asdict(audit))
