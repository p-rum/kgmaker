"""Read-only ingestion and validation of local Confluence HTML exports.

The parser deliberately uses only the standard library.  HTML, Mermaid and
Draw.io inputs are treated as evidence; code graph facts remain authoritative.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field, replace
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .analysis_model import AnalysisError, read_json
from .model import Edge, KnowledgeGraph, Node

CONFLUENCE_CACHE_FILE = Path(".kgmaker/confluence-index.json")
DEFAULT_REPORT_FILE = Path("docs/generated/confluence-inconsistencies.md")
ATTACHMENT_EXTENSIONS = {".drawio", ".xml", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".json", ".yaml", ".yml", ".pdf", ".txt"}
IMAGE_EXTENSIONS = {".svg", ".png", ".jpg", ".jpeg", ".webp"}
DIAGRAM_EXTENSIONS = {".drawio", ".xml", ".svg"}
CALL_KINDS = {"calls", "calls_endpoint", "depends_on", "uses_external_service"}
MERMAID_START = re.compile(r"^\s*(?:flowchart|graph|sequenceDiagram|classDiagram|stateDiagram(?:-v2)?|erDiagram)\b", re.I)
ARROW = re.compile(r"(?:^|\s)([\w][\w .:/-]*?)\s*(?:--+>|-+>|==+>|-+>>|-->>|->>)\s*(?:\|[^|]*\|\s*)?([\w][\w .:/-]*?)(?:\s*[:;]|\s*$)")
PROSE_CALL = re.compile(r"\b([A-Z][\w.-]*(?:\s+[A-Z][\w.-]*)?)\s+(calls?|invokes?|connects to|depends on)\s+([A-Z][\w.-]*(?:\s+[A-Z][\w.-]*)?)\b", re.I)
APPROVALS_FILE = "kgmaker-approved-requirements.json"


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _safe_rel(path: str) -> str:
    return PurePosixPath(path.replace("\\", "/")).as_posix().lstrip("./")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class ConfluenceDocument:
    id: str
    title: str
    file: str
    sections: list[dict[str, Any]] = field(default_factory=list)
    internal_links: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    diagrams: list[dict[str, Any]] = field(default_factory=list)
    text: str = ""
    sha256: str = ""
    approvals: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DocumentationAssertion:
    id: str
    document_file: str
    document_title: str
    section: str
    subject: str
    relation: str
    target: str
    statement: str
    source_kind: str = "CONFLUENCE_HTML"
    source_file: str | None = None
    status: str = "NOT_VERIFIABLE_FROM_CODE"
    category: str = "NOT_VERIFIABLE_FROM_CODE"
    confidence: str = "LOW"
    code_fact: str | None = None
    code_location: str | None = None
    matched_code_entities: list[str] = field(default_factory=list)
    authority: str = "UNAPPROVED_OR_UNKNOWN"
    approval_id: str | None = None
    decision_id: str | None = None
    decision_revision: int | None = None
    approval_status: str | None = None
    approved_document_sha256: str | None = None


class _ExportHTMLParser(HTMLParser):
    """Small structural parser for Confluence's exported HTML."""

    ignored_tags = {"script", "style", "nav", "footer", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.headings: list[str] = []
        self.sections: list[dict[str, Any]] = []
        self.links: list[str] = []
        self.attachments: list[str] = []
        self.images: list[str] = []
        self.code_blocks: list[tuple[str, str]] = []
        self._ignored = 0
        self._tag_stack: list[str] = []
        self._text_stack: list[list[str]] = []
        self._heading_level: int | None = None
        self._heading_buffer: list[str] = []
        self._block_buffer: list[str] = []
        self._block_kind = "paragraph"
        self._code_buffer: list[str] = []
        self._code_class = ""

    def _attrs(self, attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key.casefold(): value or "" for key, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        values = self._attrs(attrs)
        self._tag_stack.append(tag)
        if tag in self.ignored_tags or (values.get("class", "").casefold().find("navigation") >= 0):
            self._ignored += 1
            return
        if tag == "img":
            src = values.get("src") or values.get("data-image-src")
            if src:
                self.images.append(src)
                if Path(src.split("?", 1)[0]).suffix.casefold() in ATTACHMENT_EXTENSIONS:
                    self.attachments.append(src)
        elif tag == "a":
            href = values.get("href", "")
            if href and not href.startswith(("http:", "https:", "mailto:", "#")):
                self.links.append(href)
                if Path(href.split("?", 1)[0]).suffix.casefold() in ATTACHMENT_EXTENSIONS:
                    self.attachments.append(href)
        elif tag == "title":
            self._text_stack.append([])
        elif re.fullmatch(r"h[1-6]", tag):
            self._heading_level = int(tag[1])
            self._heading_buffer = []
        elif tag in {"p", "li", "td", "th", "caption", "blockquote"}:
            self._block_buffer = []
            self._block_kind = tag
        elif tag == "pre":
            self._code_buffer = []
            self._code_class = values.get("class", "")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if self._ignored:
            if tag in self.ignored_tags:
                self._ignored -= 1
            if self._tag_stack:
                self._tag_stack.pop()
            return
        if tag == "title" and self._text_stack:
            self.title = " ".join("".join(self._text_stack.pop()).split())
        elif re.fullmatch(r"h[1-6]", tag) and self._heading_level:
            text = " ".join("".join(self._heading_buffer).split())
            if text:
                self.headings.append(text)
                self.sections.append({"heading": text, "level": self._heading_level, "text": ""})
            self._heading_level = None
        elif tag == "pre":
            code = "".join(self._code_buffer).strip()
            if code:
                self.code_blocks.append((self._code_class, code))
        elif tag in {"p", "li", "td", "th", "caption", "blockquote"}:
            text = " ".join("".join(self._block_buffer).split())
            if text:
                if self.sections:
                    self.sections[-1]["text"] = (self.sections[-1].get("text", "") + " " + text).strip()
                else:
                    self.sections.append({"heading": "", "level": 0, "text": text})
        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._ignored:
            return
        if self._text_stack:
            self._text_stack[-1].append(data)
        if self._heading_level:
            self._heading_buffer.append(data)
        if self._block_buffer is not None:
            self._block_buffer.append(data)
        if self._code_buffer is not None and self._tag_stack and "pre" in self._tag_stack:
            self._code_buffer.append(data)

    @property
    def text(self) -> str:
        return "\n".join(
            item["text"] for item in self.sections if item.get("text")
        )


def _resolve_local_ref(value: str, current_file: str) -> str | None:
    clean = html.unescape(value.split("?", 1)[0].split("#", 1)[0])
    if not clean or clean.startswith(("http:", "https:", "mailto:", "data:")):
        return None
    return _safe_rel(str(PurePosixPath(current_file).parent.joinpath(clean)))


def _parse_mermaid(source: str) -> list[tuple[str, str, str]]:
    if not MERMAID_START.search(source.strip().splitlines()[0] if source.strip() else ""):
        return []
    relations: list[tuple[str, str, str]] = []
    for line in source.splitlines():
        match = ARROW.search(line)
        if not match:
            continue
        left = re.sub(r"[\[\]{}()\"`]", "", match.group(1)).strip()
        right = re.sub(r"[\[\]{}()\"`]", "", match.group(2)).strip()
        if left and right and left.casefold() not in {"flowchart", "graph"}:
            relations.append((left, "CONNECTS_TO", right))
    return relations


def _parse_drawio(path: Path, source_file: str) -> list[tuple[str, str, str]]:
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, ET.ParseError, UnicodeError):
        return []
    labels: dict[str, str] = {}
    relations: list[tuple[str, str, str]] = []
    for cell in root.iter():
        if cell.tag.rsplit("}", 1)[-1] != "mxCell":
            continue
        cell_id = cell.attrib.get("id", "")
        value = html.unescape(cell.attrib.get("value", "")).strip()
        if cell_id and value:
            labels[cell_id] = re.sub(r"<[^>]+>", " ", value).strip()
    for cell in root.iter():
        if cell.tag.rsplit("}", 1)[-1] != "mxCell" or cell.attrib.get("edge") != "1":
            continue
        left, right = labels.get(cell.attrib.get("source", ""), ""), labels.get(cell.attrib.get("target", ""), "")
        if left and right:
            relations.append((left, "CONNECTS_TO", right))
    return relations


def _parse_svg(path: Path) -> list[tuple[str, str, str]]:
    # Structured SVG text is useful as entity evidence; connectors without a
    # semantic marker remain intentionally unasserted.
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, ET.ParseError, UnicodeError):
        return []
    labels = [" ".join("".join(node.itertext()).split()) for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "text"]
    return [] if len(labels) < 2 else []


def _document_from_html(path: Path, export_root: Path, digest: str) -> ConfluenceDocument:
    relative = _safe_rel(str(path.relative_to(export_root)))
    parser = _ExportHTMLParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    title = parser.title or (parser.headings[0] if parser.headings else path.stem)
    links = sorted({_resolve_local_ref(value, relative) for value in parser.links if _resolve_local_ref(value, relative)})
    attachments = sorted({_resolve_local_ref(value, relative) for value in parser.attachments if _resolve_local_ref(value, relative)})
    images = sorted({_resolve_local_ref(value, relative) for value in parser.images if _resolve_local_ref(value, relative)})
    diagrams: list[dict[str, Any]] = []
    for class_name, code in parser.code_blocks:
        if MERMAID_START.search(code.strip().splitlines()[0] if code.strip() else "") or "mermaid" in class_name.casefold():
            diagrams.append({"file": relative, "kind": "MERMAID", "source": code, "relations": _parse_mermaid(code)})
    return ConfluenceDocument(
        id=f"confluence:{relative}", title=title, file=relative, sections=parser.sections,
        internal_links=links, attachments=attachments, images=images, diagrams=diagrams,
        text=parser.text, sha256=digest,
    )


def _load_cache(root: Path) -> dict[str, Any]:
    try:
        data = json.loads((root / CONFLUENCE_CACHE_FILE).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}


def _write_cache(root: Path, payload: dict[str, Any]) -> None:
    target = root / CONFLUENCE_CACHE_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def discover_export(export_root: Path) -> list[Path]:
    return sorted(path for path in export_root.rglob("*") if path.is_file() and path.suffix.casefold() in {".html", ".htm"})


def ingest_export(export_root: Path, repository_root: Path) -> tuple[list[ConfluenceDocument], list[dict[str, Any]], dict[str, Any]]:
    """Parse/reuse a local export and return documents, diagram relations and cache."""
    export_root = export_root.resolve()
    if not export_root.is_dir():
        raise ValueError(f"Confluence export directory does not exist: {export_root}")
    old = _load_cache(repository_root)
    old_pages = old.get("pages", {}) if isinstance(old.get("pages"), dict) else {}
    documents: list[ConfluenceDocument] = []
    attachments: list[dict[str, Any]] = []
    for path in discover_export(export_root):
        relative = _safe_rel(str(path.relative_to(export_root)))
        digest = _sha(path)
        cached = old_pages.get(relative)
        if isinstance(cached, dict) and cached.get("sha256") == digest:
            documents.append(ConfluenceDocument(**{key: cached.get(key, default) for key, default in {
                "id": f"confluence:{relative}", "title": path.stem, "file": relative, "sections": [],
                "internal_links": [], "attachments": [], "images": [], "diagrams": [], "text": "", "sha256": digest,
                "approvals": [],
            }.items()}))
        else:
            documents.append(_document_from_html(path, export_root, digest))
    for document in documents:
        document.approvals = []
    by_file = {document.file: document for document in documents}
    approvals_path = export_root / APPROVALS_FILE
    if approvals_path.is_file():
        approvals = read_json(approvals_path)
        if not isinstance(approvals, dict) or approvals.get("schema_version") != 1 \
                or not isinstance(approvals.get("requirements"), list):
            raise AnalysisError("Invalid approved-requirements sidecar")
        seen = set()
        assertion_keys = set()
        allowed = {"id", "document_file", "document_sha256", "section", "subject", "relation", "target",
                   "statement", "decision_id", "decision_revision", "approval_status"}
        for item in approvals["requirements"]:
            if not isinstance(item, dict) or set(item) != allowed or not isinstance(item.get("id"), str) \
                    or not item["id"] or item["id"] in seen:
                raise AnalysisError("Invalid/duplicate approved requirement")
            seen.add(item["id"])
            document = by_file.get(item.get("document_file"))
            if document is None or item.get("document_sha256") != document.sha256 \
                    or item.get("statement") not in document.text:
                raise AnalysisError("Approved requirement is not bound to the exact exported document")
            if item.get("approval_status") not in {"APPROVED", "UNAPPROVED"} \
                    or type(item.get("decision_revision")) is not int or item["decision_revision"] < 1 \
                    or not isinstance(item.get("decision_id"), str) or not item["decision_id"]:
                raise AnalysisError("Approved requirement requires explicit decision provenance")
            if item.get("relation") not in {"CALLS", "CONNECTS_TO", "DEPENDS_ON", "BUSINESS_RULE"} \
                    or any(not isinstance(item.get(key), str) or not item[key]
                           for key in ("section", "subject", "target", "statement")):
                raise AnalysisError("Approved requirement has an unsupported assertion contract")
            assertion_key = tuple(item[key] for key in ("document_file", "subject", "relation", "target", "statement"))
            if assertion_key in assertion_keys:
                raise AnalysisError("Ambiguous approvals for the same documented assertion")
            assertion_keys.add(assertion_key)
            document.approvals.append(item)
    referenced = {item for doc in documents for item in [*doc.attachments, *doc.images]}
    for relative in sorted(referenced):
        attachment_path = export_root / relative
        if not attachment_path.is_file():
            continue
        digest = _sha(attachment_path)
        relations: list[tuple[str, str, str]] = []
        ext = attachment_path.suffix.casefold()
        if ext in DIAGRAM_EXTENSIONS:
            relations = _parse_drawio(attachment_path, relative) if ext in {".drawio", ".xml"} else _parse_svg(attachment_path)
        attachments.append({"file": relative, "sha256": digest, "kind": "DIAGRAM" if ext in DIAGRAM_EXTENSIONS else "IMAGE", "relations": relations})
        for doc in documents:
            if relative in doc.attachments:
                doc.diagrams.extend({"file": relative, "kind": item["kind"], "source": "", "relations": item["relations"]} for item in attachments[-1:])
    # Validate exact extraction before publishing any cache generation.
    for document in documents:
        _assertions_from_document(document)
    cache = {"approvals_sha256": _sha(approvals_path) if approvals_path.is_file() else None,
             "schema_version": 1, "directory": str(export_root), "pages": {doc.file: asdict(doc) for doc in documents}, "attachments": attachments}
    _write_cache(repository_root, cache)
    return documents, attachments, cache


def current_documentation_assertions(cache: dict[str, Any]) -> list[dict[str, Any]]:
    """Read-only content check; legacy index remains readable but needs refresh."""
    export_root = Path(cache["directory"])
    if "approvals_sha256" not in cache:
        raise AnalysisError("Confluence validation index is stale; rerun `kgmaker docs check`.")
    approval_path = export_root / APPROVALS_FILE
    current_hash = _sha(approval_path) if approval_path.is_file() else None
    if current_hash != cache["approvals_sha256"]:
        raise AnalysisError("Confluence approval index is stale; rerun `kgmaker docs check`.")
    for relative, page in cache.get("pages", {}).items():
        path = export_root / relative
        if not path.is_file() or _sha(path) != page.get("sha256"):
            raise AnalysisError("Confluence document index is stale; rerun `kgmaker docs check`.")
    for attachment in cache.get("attachments", []):
        path = export_root / attachment["file"]
        if not path.is_file() or _sha(path) != attachment.get("sha256"):
            raise AnalysisError("Confluence attachment index is stale; rerun `kgmaker docs check`.")
    return cache.get("assertions", [])


def _assertions_from_document(doc: ConfluenceDocument) -> list[DocumentationAssertion]:
    assertions: list[DocumentationAssertion] = []
    for index, match in enumerate(PROSE_CALL.finditer(doc.text)):
        subject, verb, target = match.group(1).strip(), match.group(2).casefold(), match.group(3).strip().rstrip(".,;:")
        relation = "CALLS" if verb.startswith(("call", "invoke")) else "CONNECTS_TO" if "connect" in verb else "DEPENDS_ON"
        assertions.append(DocumentationAssertion(
            id=f"{doc.id}:assertion:{index}", document_file=doc.file, document_title=doc.title,
            section=next((item["heading"] for item in doc.sections if item.get("heading") and item.get("heading") in match.group(0)), ""),
            subject=subject, relation=relation, target=target, statement=match.group(0).strip(),
        ))
    offset = len(assertions)
    for diagram in doc.diagrams:
        for index, (subject, relation, target) in enumerate(diagram.get("relations", [])):
            assertions.append(DocumentationAssertion(
                id=f"{doc.id}:diagram:{offset + index}", document_file=doc.file, document_title=doc.title,
                section=next((item["heading"] for item in doc.sections if item.get("heading")), ""),
                subject=subject, relation=relation, target=target, statement=f"{subject} → {target}",
                source_kind=diagram.get("kind", "DIAGRAM"), source_file=diagram.get("file") or doc.file,
            ))
    for sentence in re.split(r"(?<=[.!?])\s+", doc.text):
        if len(sentence) > 30 and re.search(r"\b(?:because|must|required|requires|before|after)\b", sentence, re.I) and not PROSE_CALL.search(sentence):
            assertions.append(DocumentationAssertion(
                id=f"{doc.id}:business:{offset + len(assertions)}", document_file=doc.file, document_title=doc.title,
                section=next((item["heading"] for item in doc.sections if item.get("heading")), ""),
                subject=doc.title, relation="BUSINESS_RULE", target=sentence.strip(), statement=sentence.strip(),
            ))
    used = set()
    for assertion in assertions:
        approval = next((item for item in doc.approvals
                         if item["subject"] == assertion.subject
                         and item["relation"] == assertion.relation
                         and item["target"] == assertion.target
                         and item["statement"] == assertion.statement), None)
        if approval is None:
            continue
        used.add(approval["id"])
        assertion.authority = ("APPROVED_REQUIREMENT" if approval["approval_status"] == "APPROVED"
                               else "UNAPPROVED")
        assertion.approval_id = approval["id"]
        assertion.decision_id = approval["decision_id"]
        assertion.decision_revision = approval["decision_revision"]
        assertion.approval_status = approval["approval_status"]
        assertion.approved_document_sha256 = approval["document_sha256"]
    missing = [item["id"] for item in doc.approvals if item["id"] not in used]
    if missing:
        raise AnalysisError("Approved requirement does not match an extracted assertion: " + ", ".join(missing))
    return assertions


def _code_nodes(graph: KnowledgeGraph) -> dict[str, list[Node]]:
    result: dict[str, list[Node]] = {}
    for node in graph.nodes:
        result.setdefault(_norm(node.name), []).append(node)
    return result


def _missing_category(assertion: DocumentationAssertion) -> str:
    """Classify unresolved claims without treating missing external systems as false."""
    statement = f"{assertion.relation} {assertion.target}".casefold()
    if any(token in statement for token in ("endpoint", "rest", "http", "api")):
        return "DOCUMENTED_ENDPOINT_NOT_FOUND"
    if any(token in statement for token in ("event", "topic", "kafka", "message")):
        return "DOCUMENTED_EVENT_NOT_FOUND"
    if any(token in statement for token in ("database", "table", "column", "sql")):
        return "DOCUMENTED_DATABASE_RELATION_NOT_FOUND"
    return "DOCUMENTED_RELATION_NOT_FOUND"


def validate_documents(documents: list[ConfluenceDocument], graph: KnowledgeGraph) -> list[DocumentationAssertion]:
    nodes = _code_nodes(graph)
    edges = [edge for edge in graph.edges if edge.kind in CALL_KINDS or edge.kind in {"produces", "consumes", "maps_to_table", "calls_endpoint"}]
    by_source: dict[str, list[Edge]] = {}
    for edge in edges:
        by_source.setdefault(edge.source, []).append(edge)
    all_nodes = {node.id: node for node in graph.nodes}
    assertions = [assertion for doc in documents for assertion in _assertions_from_document(doc)]
    for assertion in assertions:
        if assertion.relation == "BUSINESS_RULE":
            if assertion.authority != "APPROVED_REQUIREMENT":
                assertion.category = "UNAPPROVED_OR_UNKNOWN"
            continue
        source_matches = nodes.get(_norm(assertion.subject), [])
        target_matches = nodes.get(_norm(assertion.target), [])
        assertion.matched_code_entities = [node.id for node in source_matches + target_matches]
        if not source_matches:
            assertion.category = assertion.status = "DOCUMENTED_ENTITY_NOT_FOUND"
            assertion.confidence = "LOW"
            continue
        source = source_matches[0]
        source_ids = {source.id}
        source_file = next((node for node in graph.nodes if node.kind == "file" and node.path == source.path), None)
        if source_file:
            source_ids.add(source_file.id)
        outgoing = [edge for source_id in source_ids for edge in by_source.get(source_id, [])]
        exact = [edge for edge in outgoing if edge.target in {node.id for node in target_matches}]
        if exact:
            edge = exact[0]
            assertion.category = assertion.status = "VERIFIED_BY_CODE"
            assertion.confidence = "HIGH"
            target = all_nodes.get(edge.target)
            assertion.code_fact = f"{source.name} {assertion.relation.lower()} {target.name if target else assertion.target}"
            assertion.code_location = f"{source.path}:{source.line or ''}".rstrip(":")
        elif outgoing and assertion.relation in {"CALLS", "CONNECTS_TO", "DEPENDS_ON"}:
            edge = outgoing[0]
            target = all_nodes.get(edge.target)
            assertion.category = assertion.status = (
                "IMPLEMENTATION_VS_APPROVED_REQUIREMENT"
                if assertion.authority == "APPROVED_REQUIREMENT"
                else "DIAGRAM_CONTRADICTS_CODE" if assertion.source_kind in {"MERMAID", "DIAGRAM"}
                else "CONTRADICTED_BY_CODE"
            )
            assertion.confidence = "HIGH"
            assertion.code_fact = f"{source.name} calls {target.name if target else edge.target}"
            assertion.code_location = f"{source.path}:{source.line or ''}".rstrip(":")
        elif not target_matches:
            assertion.category = assertion.status = _missing_category(assertion)
            assertion.confidence = "MEDIUM"
        else:
            assertion.category = assertion.status = "POSSIBLY_STALE"
            assertion.confidence = "LOW"
    return assertions


def merge_into_graph(graph: KnowledgeGraph, documents: list[ConfluenceDocument], attachments: list[dict[str, Any]], assertions: list[DocumentationAssertion]) -> KnowledgeGraph:
    nodes = list(graph.nodes)
    edges = list(graph.edges)
    existing_nodes = {node.id for node in nodes}
    existing_edges = {(edge.source, edge.target, edge.kind) for edge in edges}
    for doc in documents:
        doc_node = Node(doc.id, "confluence_document", doc.title, doc.file, summary="Local Confluence HTML export")
        if doc_node.id not in existing_nodes:
            nodes.append(doc_node); existing_nodes.add(doc_node.id)
        for target in doc.internal_links:
            target_id = f"confluence:{target}"
            if target_id in existing_nodes and (doc.id, target_id, "references") not in existing_edges:
                edges.append(Edge(doc.id, target_id, "references", evidence="relative HTML link", source_file=doc.file)); existing_edges.add((doc.id, target_id, "references"))
    for item in attachments:
        attachment_id = f"confluence-attachment:{item['file']}"
        if attachment_id not in existing_nodes:
            nodes.append(Node(attachment_id, "confluence_attachment", item["file"], item["file"], summary=item["kind"]))
            existing_nodes.add(attachment_id)
        for doc in documents:
            if item["file"] in doc.attachments or item["file"] in doc.images:
                key = (doc.id, attachment_id, "contains_attachment")
                if key not in existing_edges:
                    edges.append(Edge(doc.id, attachment_id, "contains_attachment", evidence="local HTML reference", source_file=doc.file))
                    existing_edges.add(key)
    code_nodes = _code_nodes(graph)
    for assertion in assertions:
        source = code_nodes.get(_norm(assertion.subject), [])
        doc_id = f"confluence:{assertion.document_file}"
        if source and (source[0].id, doc_id, "documented_in") not in existing_edges:
            edges.append(Edge(source[0].id, doc_id, "documented_in", evidence=assertion.statement, source_file=assertion.document_file)); existing_edges.add((source[0].id, doc_id, "documented_in"))
        if source:
            target = code_nodes.get(_norm(assertion.target), [])
            target_id = target[0].id if target else f"confluence-entity:{_norm(assertion.target)}"
            if target_id not in existing_nodes:
                nodes.append(Node(target_id, "confluence_entity", assertion.target, assertion.document_file)); existing_nodes.add(target_id)
            kind = f"documented_{assertion.relation.casefold()}"
            if (source[0].id, target_id, kind) not in existing_edges:
                edges.append(Edge(source[0].id, target_id, kind, evidence=assertion.statement, confidence="EXTRACTED", source_file=assertion.document_file)); existing_edges.add((source[0].id, target_id, kind))
    return replace(graph, nodes=nodes, edges=edges)


def render_report(assertions: list[DocumentationAssertion], report_path: Path, export_root: Path, revision: str = "working tree") -> str:
    groups: dict[str, list[DocumentationAssertion]] = {}
    for assertion in assertions:
        if assertion.status in {"VERIFIED_BY_CODE"}:
            continue
        groups.setdefault(assertion.category, []).append(assertion)
    lines = ["# Confluence inconsistencies", "", f"Generated from code revision: {revision}", f"Confluence source: {export_root}", ""]
    if not groups:
        lines.append("No documentation inconsistencies or unresolved assertions detected.")
    for category, items in sorted(groups.items()):
        lines.extend([f"## {category}", ""])
        for item in items:
            lines.extend([f"### {item.subject} → {item.target}", f"Status: {item.status}", f"Confidence: {item.confidence}", f"Documentation: `{item.document_file}` — {item.document_title}"])
            if item.section:
                lines.append(f"Section: {item.section}")
            lines.append(f"Documentation says: {item.statement}")
            if item.code_fact:
                lines.append(f"Current code: {item.code_fact}")
            if item.code_location:
                lines.append(f"Evidence: `{item.code_location}`")
            if item.source_file and item.source_file != item.document_file:
                lines.append(f"Diagram/attachment: `{item.source_file}`")
            if item.authority == "APPROVED_REQUIREMENT":
                lines.append(f"Authority: APPROVED_REQUIREMENT — decision `{item.decision_id}` revision {item.decision_revision}; document hash `{item.approved_document_sha256}`")
                action = "Review the implementation against the approved requirement; do not rewrite either source automatically."
            else:
                lines.append("Authority: UNAPPROVED_OR_UNKNOWN")
                action = "Review the documented section and update it if the current code is intentional."
            lines.extend(["Suggested action: " + action, ""])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return report_path.as_posix()


def persist_validation_index(root: Path, assertions: list[DocumentationAssertion]) -> None:
    """Persist assertion evidence and the reverse code-entity index for revalidation."""
    cache = _load_cache(root)
    cache["assertions"] = [asdict(item) for item in assertions]
    cache["reverse_index"] = {
        entity_id: [item.id for item in assertions if entity_id in item.matched_code_entities]
        for entity_id in sorted({entity_id for item in assertions for entity_id in item.matched_code_entities})
    }
    _write_cache(root, cache)


def resolve_confluence_dir(root: Path, cli_value: str | None) -> Path | None:
    if cli_value:
        candidate = Path(cli_value)
        return (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    candidates = [root / ".kgmaker" / "config.json", root / "kgmaker.json", root / ".kgmaker" / "config.yaml", root / ".kgmaker" / "config.yml", root / "kgmaker.yaml", root / "kgmaker.yml"]
    for config_path in candidates:
        try:
            raw = config_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if config_path.suffix == ".json":
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            section = data.get("documentation", {}).get("confluence", {}) if isinstance(data, dict) else {}
            if section.get("enabled", True) and section.get("directory"):
                value = Path(str(section["directory"]))
                return (root / value).resolve() if not value.is_absolute() else value.resolve()
        else:
            enabled = True
            directory = None
            for line in raw.splitlines():
                stripped = line.strip()
                if stripped.startswith("enabled:"):
                    enabled = stripped.split(":", 1)[1].strip().casefold() not in {"false", "no", "0"}
                elif stripped.startswith("directory:"):
                    directory = stripped.split(":", 1)[1].strip().strip("\"'")
            if enabled and directory:
                value = Path(directory)
                return (root / value).resolve() if not value.is_absolute() else value.resolve()
    return None


def documentation_check(root: Path, confluence_dir: str | None = None, report: str | None = None, graph: KnowledgeGraph | None = None) -> tuple[int, int, int, Path]:
    export_root = resolve_confluence_dir(root, confluence_dir)
    report_path = Path(report) if report else DEFAULT_REPORT_FILE
    if not report_path.is_absolute():
        report_path = root / report_path
    if export_root is None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("# Confluence inconsistencies\n\nNo Confluence export configured.\n", encoding="utf-8")
        return 0, 0, 0, report_path
    if graph is None:
        graph = KnowledgeGraph(1, str(root), "", [], [], {})
    documents, attachments, _ = ingest_export(export_root, root)
    assertions = validate_documents(documents, graph)
    persist_validation_index(root, assertions)
    render_report(assertions, report_path, export_root)
    contradictions = sum(item.status in {"CONTRADICTED_BY_CODE", "DIAGRAM_CONTRADICTS_CODE"} for item in assertions)
    review = sum(item.status not in {"VERIFIED_BY_CODE", "CONTRADICTED_BY_CODE", "DIAGRAM_CONTRADICTS_CODE"} for item in assertions)
    return len(documents), contradictions, review, report_path
