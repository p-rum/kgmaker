"""Domain-aware extraction for database, messaging, APIs, and TypeScript apps.

These parsers are deliberately conservative. They record concrete declarations
and string references found in source/configuration; unresolved paths and
ambiguous relationships are omitted instead of guessed.
"""

from __future__ import annotations

import json
import hashlib
import re
from dataclasses import replace
from pathlib import Path

from .model import Edge, Node

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

SQL_CREATE_TABLE = re.compile(
    r"\bCREATE\s+(?:TEMP(?:ORARY)?\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?P<name>(?:\"[^\"]+\"|[\w$]+)(?:\s*\.\s*(?:\"[^\"]+\"|[\w$]+))?)"
    r"\s*\((?P<body>[\s\S]*?)\)\s*;",
    re.IGNORECASE,
)
SQL_COLUMN_SKIP = {"constraint", "primary", "foreign", "unique", "check", "exclude"}
SQL_COLUMN_START = re.compile(r"^\s*(?:\"([^\"]+)\"|([\w$]+))\s+([\w]+)")
SQL_TABLE_REF = re.compile(
    r"\b(?:FROM|JOIN|UPDATE|INTO|REFERENCES)\s+"
    r"((?:\"[^\"]+\"|[\w$]+)(?:\s*\.\s*(?:\"[^\"]+\"|[\w$]+))?)",
    re.IGNORECASE,
)

JVM_CLASS = re.compile(
    r"^\s*(?:(?:public|internal|private|protected|open|abstract|data|sealed|enum)\s+)*"
    r"(?:class|interface|object|record)\s+(\w+)",
    re.MULTILINE,
)
JPA_ENTITY = re.compile(r"@(?:jakarta|javax)\.persistence\.Entity\b|@Entity\b")
JPA_TABLE = re.compile(r"@(?:jakarta|javax)\.persistence\.Table\s*\(([^)]*)\)|@Table\s*\(([^)]*)\)")
JPA_TABLE_NAME = re.compile(r"\bname\s*=\s*[\"']([^\"']+)[\"']")
JPA_REPOSITORY = re.compile(r"\b(?:JpaRepository|CrudRepository|PagingAndSortingRepository)\s*<\s*(\w+)")
SNAKE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")

KAFKA_LISTENER = re.compile(r"@KafkaListener\s*\(([\s\S]{0,1200}?)\)", re.MULTILINE)
KAFKA_SEND = re.compile(r"\b(?:KafkaTemplate|kafkaTemplate|kafka\w*Template)\b[\s\S]{0,120}?\.send\s*\(\s*[\"']([^\"']+)[\"']")
KAFKA_RECORD = re.compile(r"\b(?:ProducerRecord|NewTopic)\s*<[^>]*>\s*\(\s*[\"']([^\"']+)[\"']|\b(?:ProducerRecord|NewTopic)\s*\(\s*[\"']([^\"']+)[\"']")
KAFKA_TOPIC_BUILDER = re.compile(r"\bTopicBuilder\s*\.\s*name\s*\(\s*[\"']([^\"']+)[\"']")
KAFKA_CONFIG = re.compile(r"(?im)^\s*(?:[\w.-]*kafka[\w.-]*\.)?(?:topic|topics|destination)\s*[:=]\s*(?:\[\s*)?[\"']?([\w.-]+)")

SPRING_MAPPING = re.compile(r"@(?P<annotation>Get|Post|Put|Patch|Delete|Request)Mapping\s*(?:\((?P<args>[^)]*)\))?", re.MULTILINE)
SPRING_EXCHANGE = re.compile(r"@(?P<method>Get|Post|Put|Patch|Delete)Exchange\s*(?:\((?P<args>[^)]*)\))?", re.MULTILINE)
KOTLIN_KTOR = re.compile(r"\b(?P<method>get|post|put|patch|delete)\s*\(\s*[\"'](?P<path>/[^\"']*)[\"']", re.IGNORECASE)
FEIGN_CLIENT = re.compile(r"@FeignClient\s*\(([^)]*)\)", re.DOTALL)
FEIGN_NAME = re.compile(r"\b(?:name|value|contextId)\s*=\s*[\"']([^\"']+)[\"']")
FEIGN_URL = re.compile(r"\burl\s*=\s*[\"']([^\"']+)[\"']")

FETCH_CALL = re.compile(r"\bfetch\s*\(\s*[\"'`]([^\"'`]+)[\"'`]", re.MULTILINE)
HTTP_CLIENT_CALL = re.compile(r"\.\s*(?P<method>get|post|put|patch|delete|head|options)\s*\(\s*[\"'`]([^\"'`]+)[\"'`]", re.IGNORECASE)
TS_ROUTE_EXPORT = re.compile(r"\bexport\s+(?:async\s+)?function\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s*\(", re.IGNORECASE)
OPENAPI_YAML_PATH = re.compile(r"^\s{1,8}(?P<path>/[^\s:#]+)\s*:\s*(?:#.*)?$", re.MULTILINE)
OPENAPI_YAML_METHOD = re.compile(r"^\s{2,12}(?P<method>get|post|put|patch|delete|head|options)\s*:\s*(?:#.*)?$", re.MULTILINE | re.IGNORECASE)
OPENAPI_OPERATION = re.compile(r"^\s{2,16}operationId\s*:\s*[\"']?([^\s#\"']+)", re.MULTILINE)
POSTGRES_MARKER = re.compile(r"\b(?:jdbc:postgresql:|org\.postgresql|postgres(?:ql)?://)", re.IGNORECASE)
KAFKA_MARKER = re.compile(r"\b(?:org\.apache\.kafka|org\.springframework\.kafka|spring\.kafka|kafkatemplate|kafkalistener)\b|^\s*kafka\s*:", re.IGNORECASE | re.MULTILINE)
WEBCLIENT_URI = re.compile(r"\.\s*(?P<method>get|post|put|patch|delete)\s*\(\s*\)\s*\.\s*uri\s*\(\s*[\"']([^\"']+)[\"']", re.IGNORECASE)


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _unquote_identifier(value: str) -> str:
    return ".".join(part.strip().strip('"`') for part in value.strip().split("."))


def _canon(value: str) -> str:
    return _unquote_identifier(value).lower()


def _node_id(kind: str, key: str) -> str:
    return f"{kind}:{_canon(key)}"


def _shared_node(kind: str, key: str, display: str, path: str, line: int | None = None, summary: str | None = None) -> Node:
    return Node(id=_node_id(kind, key), kind=kind, name=display, path=path, line=line, summary=summary)


def _split_sql_items(body: str) -> list[str]:
    result: list[str] = []
    start = depth = 0
    quote: str | None = None
    for index, char in enumerate(body):
        if quote:
            if char == quote:
                quote = None
        elif char in "\"'`":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            result.append(body[start:index].strip())
            start = index + 1
    tail = body[start:].strip()
    if tail:
        result.append(tail)
    return result


def _sql_objects(text: str, path: str, file_id: str) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    for match in SQL_CREATE_TABLE.finditer(text):
        raw_name = _unquote_identifier(match.group("name"))
        line = _line(text, match.start())
        table = _shared_node("db_table", raw_name, raw_name, path, line)
        nodes.append(table)
        edges.append(Edge(file_id, table.id, "defines_table", f"CREATE TABLE at line {line}"))
        for item in _split_sql_items(match.group("body")):
            column_match = SQL_COLUMN_START.match(item)
            if not column_match:
                continue
            column_name = column_match.group(1) or column_match.group(2)
            if column_name.lower() in SQL_COLUMN_SKIP:
                continue
            column = Node(
                id=_node_id("db_column", f"{raw_name}.{column_name}"),
                kind="db_column",
                name=column_name,
                path=path,
                line=line + match.group("body")[:match.group("body").find(item)].count("\n"),
                signature=column_match.group(3),
            )
            nodes.append(column)
            edges.append(Edge(table.id, column.id, "contains_column", column_match.group(3).upper()))
    return nodes, edges


def _entity_edges(text: str, path: str, symbols: list[Node], tables: dict[str, Node], columns: dict[str, Node]) -> list[Edge]:
    edges: list[Edge] = []
    type_symbols = [node for node in symbols if node.kind == "type"]
    lines = text.splitlines()
    for symbol in type_symbols:
        previous_type_lines = [node.line for node in type_symbols if node.line and node.line < (symbol.line or 1)]
        prefix_start = max(previous_type_lines, default=0)
        prefix = "\n".join(lines[prefix_start:(symbol.line or 1) - 1])
        if not JPA_ENTITY.search(prefix):
            continue
        table_match = JPA_TABLE.search(prefix)
        args = next((group for group in table_match.groups() if group), "") if table_match else ""
        name_match = JPA_TABLE_NAME.search(args)
        table_name = name_match.group(1) if name_match else SNAKE_BOUNDARY.sub("_", symbol.name).lower()
        candidates = [node for key, node in tables.items() if key.split(".")[-1] == _canon(table_name).split(".")[-1]]
        if len(candidates) == 1:
            edges.append(Edge(
                symbol.id,
                candidates[0].id,
                "maps_to_table",
                "@Table annotation" if name_match else "inferred from @Entity class name",
                confidence="EXTRACTED" if name_match else "INFERRED",
                confidence_score=1.0 if name_match else 0.75,
            ))
            table = candidates[0]
            start = symbol.line or 1
            next_type_lines = [node.line for node in type_symbols if node.line and node.line > start]
            end = min(next_type_lines, default=len(lines) + 1)
            body = "\n".join(lines[start:end])
            for column_match in re.finditer(r"@Column(?:\s*\(([^)]*)\))?", body):
                args = column_match.group(1) or ""
                explicit = JPA_TABLE_NAME.search(args)
                if explicit:
                    column_name = explicit.group(1)
                else:
                    trailing = body[column_match.end():column_match.end() + 160]
                    property_match = re.search(r"\b(?:val|var)\s+(\w+)|\b(?:private|protected|public)?\s*[\w<>?,.\[\]]+\s+(\w+)\s*[;=]", trailing)
                    column_name = next((value for value in property_match.groups() if value), "") if property_match else ""
                column_key = _node_id("db_column", f"{table.name}.{column_name}")
                if column_name and column_key in columns:
                    edges.append(Edge(symbol.id, column_key, "maps_to_column", "@Column annotation"))

    for match in JPA_REPOSITORY.finditer(text):
        model_name = match.group(1)
        repositories = [node for node in symbols if node.kind == "type" and node.line and node.line <= _line(text, match.start())]
        if not repositories:
            continue
        repository = repositories[-1]
        models = [node for node in type_symbols if node.name == model_name]
        if len(models) == 1:
            edges.append(Edge(repository.id, models[0].id, "repository_for", "Spring Data repository generic"))
    return edges


def _string_literals(value: str) -> list[str]:
    return re.findall(r"[\"']([^\"']+)[\"']", value)


def _kafka_references(text: str, path: str, file_id: str) -> tuple[list[Node], list[Edge]]:
    found: dict[str, Node] = {}
    edges: list[Edge] = []

    def add(topic: str, offset: int, relation: str, evidence: str) -> None:
        topic = topic.strip()
        if not topic or topic.startswith("${") or " " in topic or topic.startswith("#"):
            return
        node = found.setdefault(_canon(topic), _shared_node("kafka_topic", topic, topic, path, _line(text, offset)))
        edges.append(Edge(file_id, node.id, relation, evidence))

    for match in KAFKA_LISTENER.finditer(text):
        topic_arg = re.search(r"\btopics?\s*=\s*", match.group(1))
        if topic_arg:
            rest = match.group(1)[topic_arg.end():].lstrip()
            if rest.startswith(("[", "{")):
                close = "]" if rest[0] == "[" else "}"
                end = rest.find(close)
                topic_values = rest[1:end] if end >= 0 else rest
            else:
                topic_values = rest.split(",", 1)[0]
            for topic in _string_literals(topic_values):
                add(topic, match.start(), "consumes", "@KafkaListener")
    for pattern in (KAFKA_SEND, KAFKA_RECORD, KAFKA_TOPIC_BUILDER):
        for match in pattern.finditer(text):
            topic = next((group for group in match.groups() if group), "")
            relation = "produces" if pattern in (KAFKA_SEND, KAFKA_RECORD) else "declares_topic"
            add(topic, match.start(), relation, match.group(0).strip()[:100])

    if KAFKA_MARKER.search(text):
        for match in KAFKA_CONFIG.finditer(text):
            add(match.group(1), match.start(), "configures_topic", match.group(0).strip()[:100])
    return list(found.values()), edges


def normalize_api_path(path: str) -> str:
    path = path.strip().split("?", 1)[0]
    path = re.sub(r"\$\{[^}]+\}|\{\{[^}]+\}\}", "{param}", path)
    path = re.sub(r"\{[^{}]+\}", "{param}", path)
    path = re.sub(r":([A-Za-z_]\w*)", r"{\1}", path)
    path = re.sub(r"/{2,}", "/", path)
    if not path.startswith("/"):
        path = "/" + path
    return path.rstrip("/") or "/"


def _api_node(method: str, path: str, source: str, line: int | None, operation: str | None = None) -> Node:
    method = method.upper()
    normalized = normalize_api_path(path)
    return Node(
        id=f"api_endpoint:{method}:{normalized.lower()}",
        kind="api_endpoint",
        name=f"{method} {normalized}",
        path=source,
        line=line,
        summary=f"operationId: {operation}" if operation else None,
    )


HTTP_CAPTURE_VERSION = 'http-raw-capture-1'


def _http_registration(method: str, route: str | None, source: str, text: str,
                       line: int | None, provider: str, *, variant: str = "",
                       method_route: str | None = None, class_prefix: str | None = "",
                       operation: str | None = None, source_sha256: str | None = None) -> Node:
    """Retain declaration data before the legacy shared endpoint ID loses it.

    Only path components enter metadata. Full URIs, query/userinfo and arbitrary
    annotation/configuration bodies never become copied registration payloads.
    """
    reasons = []
    def safe_path(value):
        if value is None:
            return None
        if (not isinstance(value, str) or len(value) > 8192 or any(c in value for c in '\r\n\0')
                or re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', value) or '://' in value or value.startswith('//')):
            reasons.append('UNSUPPORTED_ROUTE')
            return None
        if '?' in value or '#' in value:
            reasons.append('ROUTE_QUERY_OMITTED')
        return value.split('?', 1)[0].split('#', 1)[0]
    original = safe_path(route)
    method_path, prefix = safe_path(method_route), safe_path(class_prefix)
    if original is None or prefix is None:
        reasons.append('DYNAMIC_ROUTE')
    if any('${' in value or '{{' in value for value in (original, method_path, prefix) if value is not None):
        reasons.append('DYNAMIC_ROUTE')
    if original and not original.startswith('/'):
        reasons.append('DYNAMIC_ROUTE')
    normalized = normalize_api_path(original) if original is not None and not reasons else None
    variant_text = variant if isinstance(variant, str) else json.dumps(variant, sort_keys=True)
    fingerprint = hashlib.sha256(json.dumps([variant_text, route, method_route, class_prefix], ensure_ascii=False).encode('utf-8')).hexdigest()
    record = {'version': 1, 'provider': provider, 'http_method': method.upper(),
              'original_route': original, 'normalized_route': normalized,
              'method_route': method_path, 'class_prefix': prefix,
              'source_path': source, 'source_sha256': source_sha256 or hashlib.sha256(text.encode('utf-8')).hexdigest(),
              'source_line': line, 'variant_fingerprint': fingerprint,
              'unresolved_reasons': sorted(set(reasons)),
              'operation_id': operation if isinstance(operation, str) and re.fullmatch(r'[A-Za-z_][\w.-]{0,127}', operation) else None}
    legacy_path = route if route is not None else method_route
    if legacy_path is not None:
        # Preserve legacy graph identity even when the new projection must keep
        # its route unresolved. Unsafe URI material is never copied to metadata.
        node = _api_node(method, legacy_path, source, line, record['operation_id'])
    else:
        key = hashlib.sha256(json.dumps([source, line, method, fingerprint]).encode()).hexdigest()
        node = Node('api_endpoint:' + method.upper() + ':unresolved:' + key,
                    'api_endpoint', method.upper() + ' UNKNOWN', source, line=line)
    return replace(node, metadata={'http_registrations': [record]})


def _merge_api_node(first: Node, second: Node) -> Node:
    records = [*(first.metadata or {}).get('http_registrations', []),
               *(second.metadata or {}).get('http_registrations', [])]
    unique = {json.dumps(record, sort_keys=True, ensure_ascii=False): record for record in records}
    return replace(first, metadata={**(first.metadata or {}),
                                   'http_registrations': [unique[key] for key in sorted(unique)]})


def _keep_api(nodes: dict[str, Node], node: Node) -> None:
    nodes[node.id] = _merge_api_node(nodes[node.id], node) if node.id in nodes else node


def _mapping_path(args: str) -> str | None:
    match = re.search(r"(?:path|value)\s*=\s*\{?\s*[\"']([^\"']+)[\"']|^\s*[\"']([^\"']+)[\"']", args)
    return next((group for group in match.groups() if group), None) if match else None


def _openapi_yaml(text: str, path: str, file_id: str, *, source_sha256: str | None = None) -> tuple[list[Node], list[Edge]]:
    lines = text.splitlines()
    paths_start = next((i for i, line in enumerate(lines) if re.match(r"^\s*paths\s*:\s*(?:#.*)?$", line)), None)
    if paths_start is None:
        return [], []
    nodes: dict[str, Node] = {}
    edges: list[Edge] = []
    current_path: str | None = None
    current_method: str | None = None
    current_operation: str | None = None

    def flush(offset: int) -> None:
        if current_path and current_method:
            node = _http_registration(current_method, current_path, path, text, offset + 1,
                                      'openapi-yaml', source_sha256=source_sha256, variant=current_operation or '', operation=current_operation)
            _keep_api(nodes, node)
            edges.append(Edge(file_id, node.id, "declares_endpoint", current_operation or "OpenAPI path and method",
                              source_file=path, source_line=offset + 1))

    for index in range(paths_start + 1, len(lines)):
        line = lines[index]
        if line and not line[0].isspace():
            flush(index - 1)
            break
        path_match = OPENAPI_YAML_PATH.match(line)
        if path_match:
            flush(index - 1)
            current_path = path_match.group("path")
            current_method = None
            current_operation = None
            continue
        method_match = OPENAPI_YAML_METHOD.match(line)
        if method_match:
            flush(index - 1)
            current_method = method_match.group("method")
            current_operation = None
            continue
        if current_method:
            operation_match = OPENAPI_OPERATION.match(line)
            if operation_match:
                current_operation = operation_match.group(1)
    flush(len(lines) - 1)
    return list(nodes.values()), edges


def _openapi_json(text: str, path: str, file_id: str, *, source_sha256: str | None = None) -> tuple[list[Node], list[Edge]]:
    try:
        document = json.loads(text)
    except (ValueError, TypeError):
        return [], []
    if not isinstance(document, dict) or not isinstance(document.get("paths"), dict):
        return [], []
    nodes: dict[str, Node] = {}
    edges: list[Edge] = []
    for api_path, operations in document["paths"].items():
        if not isinstance(operations, dict):
            continue
        for method, operation in operations.items():
            if method.lower() not in HTTP_METHODS:
                continue
            operation_id = operation.get("operationId") if isinstance(operation, dict) else None
            node = _http_registration(method, api_path, path, text, None, 'openapi-json', source_sha256=source_sha256,
                                      variant=operation_id or '', operation=operation_id)
            _keep_api(nodes, node)
            edges.append(Edge(file_id, node.id, "declares_endpoint", operation_id or "OpenAPI path and method",
                              source_file=path))
    return list(nodes.values()), edges


def _api_references(text: str, path: str, language: str, file_id: str, *, source_sha256: str | None = None) -> tuple[list[Node], list[Edge]]:
    nodes: dict[str, Node] = {}
    edges: list[Edge] = []

    def add(method: str, endpoint_path: str | None, offset: int, relation: str, evidence: str,
            *, provider: str | None = None, method_route: str | None = None,
            class_prefix: str | None = "", variant: str = "") -> None:
        if provider:
            node = _http_registration(method, endpoint_path, path, text, _line(text, offset), provider, source_sha256=source_sha256,
                                      method_route=method_route, class_prefix=class_prefix, variant=variant)
            _keep_api(nodes, node)
            edges.append(Edge(file_id, node.id, relation, evidence, source_file=path,
                              source_line=_line(text, offset)))
            return
        if not endpoint_path.startswith("/"):
            return
        node = _api_node(method, endpoint_path, path, _line(text, offset))
        nodes.setdefault(node.id, node)
        edges.append(Edge(file_id, node.id, relation, evidence))

    if language == "jvm":
        classes = list(JVM_CLASS.finditer(text))
        for match in SPRING_MAPPING.finditer(text):
            annotation = match.group("annotation").lower()
            method = annotation.removesuffix("mapping").upper()
            args = match.group("args") or ""
            endpoint = _mapping_path(args)
            if endpoint is not None or annotation != 'request' or re.search(r'\bmethod\s*=', args):
                if method == "REQUEST":
                    request_method = re.search(r"\bmethod\s*=\s*(?:RequestMethod\.)?(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)", args, re.IGNORECASE)
                    if not request_method:
                        continue  # A class-level mapping contributes a prefix, not an HTTP operation.
                    method = request_method.group(1).upper()
                method_route = endpoint if endpoint is not None else ('' if not args.strip() else None)
                prefix = ''
                previous = [class_match for class_match in classes if class_match.start() < match.start()]
                if previous:
                    current_class = previous[-1]
                    earlier_classes = [class_match for class_match in classes if class_match.start() < current_class.start()]
                    prefix_start = earlier_classes[-1].end() if earlier_classes else 0
                    class_annotations = text[prefix_start:current_class.start()]
                    class_mapping = next((
                        class_mapping
                        for class_mapping in SPRING_MAPPING.finditer(class_annotations)
                        if class_mapping.group("annotation").lower() == "request"
                    ), None)
                    if class_mapping:
                        prefix_args = class_mapping.group('args') or ''
                        prefix = _mapping_path(prefix_args) if prefix_args.strip() else ''
                endpoint = f"{prefix.rstrip('/')}/{method_route.lstrip('/')}" if prefix is not None and method_route is not None else None
                add(method, endpoint, match.start(), "declares_endpoint", "Spring MVC mapping annotation",
                    provider='spring-source', method_route=method_route, class_prefix=prefix, variant=args)
        for match in SPRING_EXCHANGE.finditer(text):
            method = match.group("method").upper()
            endpoint = _mapping_path(match.group("args") or "")
            if endpoint:
                add(method, endpoint, match.start(), "calls_endpoint", "Spring HTTP interface annotation")
        for match in KOTLIN_KTOR.finditer(text):
            add(match.group("method"), match.group("path"), match.start(), "declares_endpoint", "Ktor route declaration candidate",
                provider='ktor-source', method_route=match.group('path'))
        for match in WEBCLIENT_URI.finditer(text):
            add(match.group("method"), match.group(2), match.start(), "calls_endpoint", "WebClient or RestClient URI call")
        for match in FEIGN_CLIENT.finditer(text):
            name_match = FEIGN_NAME.search(match.group(1))
            url_match = FEIGN_URL.search(match.group(1))
            service = (name_match.group(1) if name_match else (url_match.group(1) if url_match else "")).strip()
            if service:
                service_node = _shared_node("external_service", service, service, path, _line(text, match.start()))
                nodes.setdefault(service_node.id, service_node)
                edges.append(Edge(file_id, service_node.id, "uses_external_service", "@FeignClient; endpoint URL omitted"))

    if language == "javascript":
        for match in FETCH_CALL.finditer(text):
            tail = text[match.end():match.end() + 300]
            method_match = re.search(r"\bmethod\s*:\s*[\"']([A-Za-z]+)[\"']", tail, re.IGNORECASE)
            method = method_match.group(1) if method_match else "GET"
            add(method, match.group(1), match.start(), "calls_endpoint", "fetch call")
        for match in HTTP_CLIENT_CALL.finditer(text):
            add(match.group("method"), match.group(2), match.start(), "calls_endpoint", "HTTP client method and path")

    return list(nodes.values()), edges


def _typescript_routes(path: str, text: str, file_id: str) -> tuple[list[Node], list[Edge]]:
    file_path = Path(path)
    parts = list(file_path.parts)
    route: str | None = None
    route_line = 1
    for marker in ("app", "pages"):
        if marker not in parts:
            continue
        start = parts.index(marker) + 1
        route_parts = parts[start:]
        if route_parts and route_parts[-1].lower() in {"page.tsx", "page.ts", "page.jsx", "page.js", "index.tsx", "index.ts", "index.jsx", "index.js", "route.ts", "route.js"}:
            route_parts = route_parts[:-1]
        else:
            route_parts = [p.rsplit(".", 1)[0] for p in route_parts]
        route_parts = [re.sub(r"^\[\.\.\.(.+)\]$", r"*\1", re.sub(r"^\[(.+)\]$", r"{\1}", part)) for part in route_parts if not (part.startswith("(") and part.endswith(")"))]
        route = "/" + "/".join(route_parts)
        break

    nodes: list[Node] = []
    edges: list[Edge] = []
    if route is not None:
        node = Node(id=f"frontend_route:{path}", kind="frontend_route", name=route, path=path, line=route_line)
        nodes.append(node)
        edges.append(Edge(file_id, node.id, "defines_route", "file-based TypeScript route"))

    for match in TS_ROUTE_EXPORT.finditer(text):
        method = match.group(1).upper()
        route_path = route if route is not None else "/"
        endpoint = _api_node(method, route_path, path, _line(text, match.start()))
        nodes.append(endpoint)
        edges.append(Edge(file_id, endpoint.id, "declares_endpoint", "Next.js route handler export"))
    return nodes, edges


def _technology_nodes(text: str, path: str, file_id: str) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    if POSTGRES_MARKER.search(text):
        node = _shared_node("technology", "PostgreSQL", "PostgreSQL", path)
        nodes.append(node)
        edges.append(Edge(file_id, node.id, "connects_to", "PostgreSQL driver or connection string"))
    if KAFKA_MARKER.search(text):
        node = _shared_node("technology", "Kafka", "Kafka", path)
        nodes.append(node)
        edges.append(Edge(file_id, node.id, "uses_messaging", "Kafka import, client, annotation, or configuration"))
    return nodes, edges


def extract_domain(path: str, text: str, language: str, file_id: str, symbols: list[Node], *, source_sha256: str | None = None) -> tuple[list[Node], list[Edge]]:
    """Return file-local domain nodes and evidence-backed edges."""
    nodes: list[Node] = []
    edges: list[Edge] = []
    suffix = Path(path).suffix.lower()
    if suffix == ".sql":
        domain_nodes, domain_edges = _sql_objects(text, path, file_id)
        nodes.extend(domain_nodes)
        edges.extend(domain_edges)
    if language == "jvm":
        domain_nodes, domain_edges = _kafka_references(text, path, file_id)
        nodes.extend(domain_nodes)
        edges.extend(domain_edges)
        domain_nodes, domain_edges = _api_references(text, path, language, file_id, source_sha256=source_sha256)
        nodes.extend(domain_nodes)
        edges.extend(domain_edges)
    elif language == "javascript":
        domain_nodes, domain_edges = _api_references(text, path, language, file_id, source_sha256=source_sha256)
        nodes.extend(domain_nodes)
        edges.extend(domain_edges)
        if suffix in {".tsx", ".jsx"} or "/app/" in f"/{path}/" or "/pages/" in f"/{path}/":
            domain_nodes, domain_edges = _typescript_routes(path, text, file_id)
            nodes.extend(domain_nodes)
            edges.extend(domain_edges)
    elif suffix in {".yaml", ".yml", ".properties"} and KAFKA_MARKER.search(text):
        domain_nodes, domain_edges = _kafka_references(text, path, file_id)
        nodes.extend(domain_nodes)
        edges.extend(domain_edges)

    domain_nodes, domain_edges = _technology_nodes(text, path, file_id)
    nodes.extend(domain_nodes)
    edges.extend(domain_edges)
    return nodes, edges


def extract_openapi(path: str, text: str, file_id: str, *, source_sha256: str | None = None) -> tuple[list[Node], list[Edge]]:
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        return _openapi_json(text, path, file_id, source_sha256=source_sha256)
    if suffix in {".yaml", ".yml"}:
        return _openapi_yaml(text, path, file_id, source_sha256=source_sha256)
    return [], []


def connect_persistence(symbols_by_file: dict[str, list[Node]], text_by_file: dict[str, str], nodes: list[Node]) -> list[Edge]:
    tables: dict[str, Node] = {}
    columns: dict[str, Node] = {}
    for node in nodes:
        if node.kind == "db_table":
            tables[_canon(node.name)] = node
        elif node.kind == "db_column":
            columns[node.id] = node
    edges: list[Edge] = []
    for path, symbols in symbols_by_file.items():
        text = text_by_file[path]
        if Path(path).suffix.lower() in {".kt", ".kts", ".java"}:
            edges.extend(_entity_edges(text, path, symbols, tables, columns))
        # SQL text embedded in repositories and annotations still provides table references.
        for match in SQL_TABLE_REF.finditer(text):
            table_name = _canon(match.group(1))
            candidates = [node for key, node in tables.items() if key == table_name or key.endswith("." + table_name)]
            if len(candidates) != 1:
                continue
            if match.group(0).lstrip().upper().startswith("REFERENCES"):
                local_tables = [node for node in tables.values() if node.path == path and node.line and node.line <= _line(text, match.start())]
                if local_tables:
                    source_table = max(local_tables, key=lambda node: node.line or 0)
                    edges.append(Edge(source_table.id, candidates[0].id, "references_table", "SQL foreign-key reference"))
                    continue
            owner = next((node for node in symbols if node.line and node.line <= _line(text, match.start())), None)
            if owner:
                edges.append(Edge(owner.id, candidates[0].id, "queries_table", f"SQL table reference at line {_line(text, match.start())}"))
    return edges


def merge_domain_nodes(nodes: list[Node]) -> list[Node]:
    """Deduplicate shared API/topic/technology/table nodes, keeping first evidence path."""
    unique: dict[str, Node] = {}
    for node in nodes:
        if node.kind in {"api_endpoint", "kafka_topic", "technology", "external_service", "db_table", "db_column"}:
            if node.kind == 'api_endpoint' and node.id in unique:
                unique[node.id] = _merge_api_node(unique[node.id], node)
            else:
                unique.setdefault(node.id, node)
        else:
            unique[node.id] = node
    return list(unique.values())
