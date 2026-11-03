"""Compiler-backed persistence XML precedence and fail-closed behavior."""
from pathlib import Path
import hashlib

import pytest

from kgmaker.inspection import inspect_jvm
from kgmaker.model import KnowledgeGraph

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "workers"

JPA_STUBS = {
    "Entity": "@Target(ElementType.TYPE) public @interface Entity {}",
    "Table": "@Target(ElementType.TYPE) public @interface Table { String name() default \"\"; }",
    "Id": "@Target(ElementType.FIELD) public @interface Id {}",
    "Column": "@Target(ElementType.FIELD) public @interface Column { String name() default \"\"; }",
}


def project(root: Path, *, mapping: str, descriptor: str | None = None) -> Path:
    for name, declaration in JPA_STUBS.items():
        api = root / "src/main/java/jakarta/persistence" / f"{name}.java"
        api.parent.mkdir(parents=True, exist_ok=True)
        api.write_text(
            "package jakarta.persistence; import java.lang.annotation.*; "
            f"@Retention(RetentionPolicy.RUNTIME) {declaration}", encoding="utf-8")
    source = root / "src/main/java/demo/Order.java"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text('''package demo;
import jakarta.persistence.*;
@Entity @Table(name="annotation_orders") class Order {
  @Id @Column(name="annotation_id") long id;
  @Column(name="annotation_name") String name;
  @Column(name="annotation_extra") String extra;
}
''', encoding="utf-8")
    if descriptor is None:
        descriptor = '''<?xml version="1.0"?>
<persistence xmlns="https://jakarta.ee/xml/ns/persistence" version="3.1">
  <persistence-unit name="orders"><mapping-file>META-INF/orders.xml</mapping-file></persistence-unit>
</persistence>'''
    descriptor_path = root / "META-INF/persistence.xml"
    descriptor_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor_path.write_text(descriptor, encoding="utf-8")
    mapping_path = root / "META-INF/orders.xml"
    mapping_path.write_text(mapping, encoding="utf-8")
    return root


def inspect(root: Path, *, strict=False, persistence_unit="orders"):
    result = inspect_jvm(root, kotlin_backend="k1", home=HOME, classpath=[],
                         build_context={"persistence_unit": persistence_unit},
                         publish=not strict, strict=strict)
    return KnowledgeGraph.from_dict(result["graph"]) if not strict else result


def table_for(graph: KnowledgeGraph):
    entity = next(node for node in graph.nodes if node.kind == "class" and node.name == "Order")
    table_id = next(edge.target for edge in graph.edges if edge.source == entity.id and edge.kind == "maps_to_table")
    return next(node for node in graph.nodes if node.id == table_id)


def columns_for(graph: KnowledgeGraph, attribute_name: str) -> list[str]:
    attribute = next(node for node in graph.nodes if node.kind == "orm_attribute" and node.name == attribute_name)
    return [next(node.name for node in graph.nodes if node.id == edge.target)
            for edge in graph.edges if edge.source == attribute.id and edge.kind == "maps_to_column"]


def test_orm_xml_partial_overrides_take_precedence_and_record_hashed_source(tmp_path):
    mapping = '''<?xml version="1.0"?>
<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
  <entity class="demo.Order"><table name="xml_orders"/><attributes>
    <id name="id"><column name="xml_id"/></id>
  </attributes></entity>
</entity-mappings>'''
    root = project(tmp_path, mapping=mapping)
    graph = inspect(root)
    assert table_for(graph).metadata["logical_name"] == "xml_orders"
    assert columns_for(graph, "Order.id") == ["xml_id"]
    assert columns_for(graph, "Order.name") == ["annotation_name"]
    xml_hash = hashlib.sha256((root / "META-INF/orders.xml").read_bytes()).hexdigest()
    proof = [item for item in graph.evidence if item.get("source_file") == "META-INF/orders.xml"]
    assert proof and all(item.get("xml_sha256") == xml_hash for item in proof)
    assert all(item.get("persistence_unit") == "orders" for item in proof)


def test_orm_xml_missing_explicit_column_does_not_fall_back_to_annotation(tmp_path):
    mapping = '''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
      <entity class="demo.Order"><attribute-override name="name"/></entity></entity-mappings>'''
    graph = inspect(project(tmp_path, mapping=mapping))
    assert columns_for(graph, "Order.name") == []
    attribute = next(node for node in graph.nodes if node.kind == "orm_attribute" and node.name == "Order.name")
    assert attribute.metadata["mapping_status"] == "UNKNOWN"
    assert any(item.get("code") == "ORM_XML_COLUMN_UNKNOWN" and item.get("attribute") == "name"
               for item in graph.diagnostics)


def test_orm_xml_metadata_complete_suppresses_annotation_fallback(tmp_path):
    mapping = '''<?xml version="1.0"?>
<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1" metadata-complete="true">
  <entity class="demo.Order"><table name="complete_orders"/><attributes>
    <id name="id"><column name="xml_id"/></id>
    <basic name="name"><column name="xml_name"/></basic>
  </attributes></entity>
</entity-mappings>'''
    graph = inspect(project(tmp_path, mapping=mapping))
    table = table_for(graph)
    assert table.metadata["logical_name"] == "complete_orders"
    assert columns_for(graph, "Order.id") == ["xml_id"]
    assert columns_for(graph, "Order.name") == ["xml_name"]
    assert "annotation_id" not in {node.name for node in graph.nodes if node.kind == "orm_column"}
    assert "annotation_name" not in {node.name for node in graph.nodes if node.kind == "orm_column"}
    assert "annotation_extra" not in {node.name for node in graph.nodes if node.kind == "orm_column"}
    extra = next(node for node in graph.nodes if node.kind == "orm_attribute" and node.name == "Order.extra")
    assert extra.metadata["mapping_status"] == "UNKNOWN"


def test_orm_xml_metadata_complete_isolated_by_canonical_entity_owner(tmp_path):
    mapping = '''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
      <entity class="demo.Order" metadata-complete="true"><table name="demo_orders"/><attributes>
        <id name="id"><column name="demo_id"/></id>
        <basic name="name"><column name="demo_name"/></basic>
      </attributes></entity></entity-mappings>'''
    root = project(tmp_path, mapping=mapping)
    other = root / "src/main/java/other/Order.java"
    other.parent.mkdir(parents=True, exist_ok=True)
    other.write_text('''package other;
import jakarta.persistence.*;
@Entity @Table(name="other_orders") class Order {
  @Id @Column(name="other_id") long id;
  @Column(name="other_name") String name;
}
''', encoding="utf-8")

    graph = inspect(root)
    other_name = next(node for node in graph.nodes if node.kind == "orm_attribute"
                      and node.name == "Order.name"
                      and node.path == "src/main/java/other/Order.java")
    assert [next(node.name for node in graph.nodes if node.id == edge.target)
            for edge in graph.edges if edge.source == other_name.id and edge.kind == "maps_to_column"] == ["other_name"]
    demo_extra = next(node for node in graph.nodes if node.kind == "orm_attribute"
                      and node.name == "Order.extra"
                      and node.path == "src/main/java/demo/Order.java")
    assert demo_extra.metadata["mapping_status"] == "UNKNOWN"


def test_invalid_xml_class_reference_is_diagnostic_and_strict_publication_preserves_graph(tmp_path):
    valid = '''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
  <entity class="demo.Order"><table name="valid_orders"/></entity></entity-mappings>'''
    root = project(tmp_path, mapping=valid)
    first = inspect_jvm(root, kotlin_backend="k1", home=HOME, classpath=[],
                        build_context={"persistence_unit": "orders"})
    store = root / ".kgmaker/graph.json"
    before = store.read_bytes()
    (root / "META-INF/orders.xml").write_text(
        '''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
        <entity class="missing.DoesNotExist"><table name="bad"/></entity></entity-mappings>''', encoding="utf-8")
    rejected = inspect_jvm(root, kotlin_backend="k1", home=HOME, classpath=[],
                           build_context={"persistence_unit": "orders"}, strict=True)
    assert rejected["exit_code"] == 4
    assert store.read_bytes() == before
    assert any(item.get("code") == "ORM_XML_CLASS_UNRESOLVED" for item in rejected["diagnostics"])


def test_orm_xml_declared_mapping_file_order_is_preserved(tmp_path):
    descriptor = '''<persistence xmlns="https://jakarta.ee/xml/ns/persistence" version="3.1">
      <persistence-unit name="orders">
        <mapping-file>META-INF/first.xml</mapping-file>
        <mapping-file>META-INF/second.xml</mapping-file>
      </persistence-unit>
    </persistence>'''
    mapping = '''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
      <entity class="demo.Order"><table name="default_orders"/></entity></entity-mappings>'''
    root = project(tmp_path, mapping=mapping, descriptor=descriptor)
    for filename, name in (("first.xml", "first_orders"), ("second.xml", "second_orders")):
        (root / "META-INF" / filename).write_text(
            f'''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
            <entity class="demo.Order"><table name="{name}"/></entity></entity-mappings>''', encoding="utf-8")
    graph = inspect(root)
    table = table_for(graph)
    assert table.metadata["logical_name"] == "second_orders"
    assert table.metadata["xml_mapping_order"] == 1
    assert table.metadata["xml_mapping_file"] == "META-INF/second.xml"


def test_selected_persistence_unit_ignores_other_units_mapping_files(tmp_path):
    descriptor = '''<persistence xmlns="https://jakarta.ee/xml/ns/persistence" version="3.1">
      <persistence-unit name="orders"><mapping-file>META-INF/orders-unit.xml</mapping-file></persistence-unit>
      <persistence-unit name="archive"><mapping-file>META-INF/archive-unit.xml</mapping-file></persistence-unit>
    </persistence>'''
    mapping = '''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
      <entity class="demo.Order"><table name="default_orders"/></entity></entity-mappings>'''
    root = project(tmp_path, mapping=mapping, descriptor=descriptor)
    for filename, name in (("orders-unit.xml", "orders_unit_table"), ("archive-unit.xml", "archive_unit_table")):
        (root / "META-INF" / filename).write_text(
            f'''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
            <entity class="demo.Order"><table name="{name}"/></entity></entity-mappings>''', encoding="utf-8")
    graph = inspect(root, persistence_unit="orders")
    assert table_for(graph).metadata["logical_name"] == "orders_unit_table"
    assert "archive_unit_table" not in {node.name for node in graph.nodes if node.kind == "orm_table"}


@pytest.mark.parametrize("listed,expected_table", [("demo.Order", "annotation_orders"),
                                                       ("demo.Other", None)])
def test_persistence_unit_exclude_unlisted_classes_controls_annotation_fallback(tmp_path, listed, expected_table):
    descriptor = f'''<persistence xmlns="https://jakarta.ee/xml/ns/persistence" version="3.1">
      <persistence-unit name="orders"><class>{listed}</class><exclude-unlisted-classes>true</exclude-unlisted-classes>
      </persistence-unit></persistence>'''
    root = project(tmp_path, mapping="<entity-mappings xmlns=\"https://jakarta.ee/xml/ns/persistence/orm\" version=\"3.1\"/>",
                   descriptor=descriptor)
    graph = inspect(root)
    tables = [node for node in graph.nodes if node.kind == "orm_table"]
    if expected_table:
        assert table_for(graph).metadata["logical_name"] == expected_table
    else:
        assert not tables
        assert not [node for node in graph.nodes if node.kind == "orm_column"]
        assert any(item.get("code") == "ORM_XML_METADATA_COMPLETE_CLASS_UNMAPPED"
                   and item.get("class") == "demo.Order" for item in graph.diagnostics)


def test_metadata_complete_xml_can_define_attributes_without_jpa_annotations(tmp_path):
    mapping = '''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
      <entity class="demo.Order" metadata-complete="true"><table name="xml_only_orders"/><attributes>
        <id name="id"><column name="xml_id"/></id>
        <basic name="name"><column name="xml_name"/></basic>
      </attributes></entity></entity-mappings>'''
    root = project(tmp_path, mapping=mapping)
    source = root / "src/main/java/demo/Order.java"
    source.write_text('''package demo;
class Order { long id; String name; }
''', encoding="utf-8")
    graph = inspect(root)
    assert table_for(graph).metadata["logical_name"] == "xml_only_orders"
    assert columns_for(graph, "Order.id") == ["xml_id"]
    assert columns_for(graph, "Order.name") == ["xml_name"]
    assert all((node.metadata or {}).get("mapping_source") == "ORM_XML"
               for node in graph.nodes if node.kind == "orm_attribute")


def test_xml_mapped_superclass_column_updates_existing_inherited_projection(tmp_path):
    mapping = '''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
      <mapped-superclass class="demo.Base"><attributes>
        <basic name="created"><column name="xml_created"/></basic>
      </attributes></mapped-superclass></entity-mappings>'''
    root = project(tmp_path, mapping=mapping)
    base = root / "src/main/java/demo/Base.java"
    base.write_text('''package demo;
import jakarta.persistence.*;
@MappedSuperclass class Base { @Id Long id; @Column(name="annotation_created") String created; }
''', encoding="utf-8")
    entity = root / "src/main/java/demo/Order.java"
    entity.write_text('''package demo;
import jakarta.persistence.*;
@Entity class Order extends Base {}
''', encoding="utf-8")
    graph = inspect(root)
    assert columns_for(graph, "Order.created") == ["xml_created"]
    inherited = next(node for node in graph.nodes if node.kind == "orm_attribute" and node.name == "Order.created")
    assert inherited.metadata["declaring_owner"] == "demo.Base"
    assert inherited.metadata["effective_owner"] == "demo.Order"


def test_xml_inheritance_strategy_rebinds_inherited_attributes_to_final_table(tmp_path):
    mapping = '''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
      <entity class="demo.Order"><inheritance strategy="TABLE_PER_CLASS"/></entity>
    </entity-mappings>'''
    root = project(tmp_path, mapping=mapping)
    source = root / "src/main/java/demo/Order.java"
    source.write_text('''package demo;
import jakarta.persistence.*;
@Entity class Order { @Id @Column(name="annotation_id") long id; }
''', encoding="utf-8")
    graph = inspect(root)
    root_table = table_for(graph)
    assert root_table.metadata["inheritance_strategy"] == "TABLE_PER_CLASS"


@pytest.mark.parametrize("mapping,diagnostic", [
    ('''<entity-mappings xmlns="urn:foreign" version="1"><entity class="demo.Order"/></entity-mappings>''',
     "ORM_XML_NAMESPACE_UNSUPPORTED"),
    ('''<!DOCTYPE entity-mappings [<!ENTITY ext SYSTEM "file:///etc/passwd">]>
    <entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
    <entity class="demo.Order"><table name="&ext;"/></entity></entity-mappings>''',
     "ORM_XML_UNSAFE_DECLARATION"),
    ('''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
      <entity class="demo.Order"><cacheable>true</cacheable></entity></entity-mappings>''',
     "ORM_XML_CONSTRUCT_UNSUPPORTED"),
])
def test_unsupported_or_external_xml_never_claims_annotation_mapping(tmp_path, mapping, diagnostic):
    graph = inspect(project(tmp_path, mapping=mapping))
    assert any(item.get("code") == diagnostic for item in graph.diagnostics)
    assert not [node for node in graph.nodes if node.kind == "orm_table"]
    assert not [node for node in graph.nodes if node.kind == "orm_column"]
    assert all(node.metadata.get("mapping_status") == "UNKNOWN"
               for node in graph.nodes if node.kind == "orm_attribute")


@pytest.mark.parametrize("encoding,bom", [("utf-8", False), ("utf-8", True),
                                           ("utf-16-le", False), ("utf-16-le", True),
                                           ("utf-16-be", False), ("utf-16-be", True)])
def test_xml_dtd_is_rejected_independent_of_encoding(tmp_path, encoding, bom):
    from kgmaker.framework import _safe_jpa_xml
    (tmp_path / "META-INF").mkdir()
    xml = '<?xml version="1.0" encoding="' + encoding + '"?><!DOCTYPE x [<!ENTITY name "expanded">]><x>&name;</x>'
    raw = xml.encode(encoding)
    if bom:
        raw = ({"utf-8": b"\xef\xbb\xbf", "utf-16-le": b"\xff\xfe", "utf-16-be": b"\xfe\xff"}[encoding] + raw)
    (tmp_path / "META-INF/input.xml").write_bytes(raw)
    document, error = _safe_jpa_xml(tmp_path, "META-INF/input.xml")
    assert document is None
    assert error["code"] == "ORM_XML_UNSAFE_DECLARATION"


def test_xml_unknown_encoding_and_oversize_are_bounded_diagnostics(tmp_path, monkeypatch):
    from kgmaker.framework import MAX_JPA_XML_BYTES, _safe_jpa_xml
    (tmp_path / "META-INF").mkdir()
    path = tmp_path / "META-INF/input.xml"
    path.write_bytes(b'<?xml version="1.0" encoding="x-unknown"?><x/>')
    _, error = _safe_jpa_xml(tmp_path, "META-INF/input.xml")
    assert error["code"] == "ORM_XML_ENCODING_UNSUPPORTED"
    path.write_bytes(b" " * (MAX_JPA_XML_BYTES + 1))
    original_open = Path.open
    reads = []
    class ReadSpy:
        def __init__(self, stream): self.stream = stream
        def __enter__(self): return self
        def __exit__(self, *args): return self.stream.__exit__(*args)
        def read(self, size=-1):
            reads.append(size)
            return self.stream.read(size)
    def spy_open(self, *args, **kwargs):
        stream = original_open(self, *args, **kwargs)
        return ReadSpy(stream) if self == path else stream
    monkeypatch.setattr(Path, "open", spy_open)
    _, error = _safe_jpa_xml(tmp_path, "META-INF/input.xml")
    assert error["code"] == "ORM_XML_SIZE_LIMIT"
    assert reads == [MAX_JPA_XML_BYTES + 1]


def test_xml_namespace_reset_strictly_preserves_previous_store(tmp_path):
    good = '''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
      <entity class="demo.Order"><table name="good_orders"/></entity></entity-mappings>'''
    root = project(tmp_path, mapping=good)
    inspect_jvm(root, kotlin_backend="k1", home=HOME, classpath=[], build_context={"persistence_unit": "orders"})
    store = root / ".kgmaker/graph.json"
    before = store.read_bytes()
    reset = '''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
      <entity xmlns="" class="demo.Order"><table name="reset_orders"/></entity></entity-mappings>'''
    (root / "META-INF/orders.xml").write_text(reset, encoding="utf-8")
    rejected = inspect_jvm(root, kotlin_backend="k1", home=HOME, classpath=[],
                           build_context={"persistence_unit": "orders"}, strict=True)
    assert rejected["exit_code"] == 4
    assert store.read_bytes() == before
    assert any(item.get("code") == "ORM_XML_NAMESPACE_UNSUPPORTED" for item in rejected["diagnostics"])


def test_invalid_encoding_and_utf16_dtd_strictly_preserve_previous_store(tmp_path):
    root = project(tmp_path, mapping='''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
      <entity class="demo.Order"><table name="good_orders"/></entity></entity-mappings>''')
    inspect_jvm(root, kotlin_backend="k1", home=HOME, classpath=[], build_context={"persistence_unit": "orders"})
    store = root / ".kgmaker/graph.json"
    before = store.read_bytes()
    invalid_payloads = [
        ('<?xml version="1.0" encoding="utf-16"?><!DOCTYPE x [<!ENTITY t "bad">]><entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1"><entity class="demo.Order"><table name="&t;"/></entity></entity-mappings>').encode("utf-16-le"),
        b'<?xml version="1.0" encoding="unknown-encoding"?><entity-mappings/>',
    ]
    for payload in invalid_payloads:
        (root / "META-INF/orders.xml").write_bytes(payload)
        rejected = inspect_jvm(root, kotlin_backend="k1", home=HOME, classpath=[],
                               build_context={"persistence_unit": "orders"}, strict=True)
        assert rejected["exit_code"] == 4
        assert store.read_bytes() == before
        assert any(item.get("code") in {"ORM_XML_UNSAFE_DECLARATION", "ORM_XML_ENCODING_UNSUPPORTED"}
                   for item in rejected["diagnostics"])


def test_standard_nested_metadata_complete_and_access_are_honored(tmp_path):
    mapping = '''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
      <persistence-unit-metadata><xml-mapping-metadata-complete/>
        <persistence-unit-defaults><access>FIELD</access></persistence-unit-defaults>
      </persistence-unit-metadata>
      <entity class="demo.Order"><table name="standard_orders"/><attributes>
        <id name="id"><column name="standard_id"/></id>
        <basic name="name"><column name="standard_name"/></basic>
      </attributes></entity></entity-mappings>'''
    graph = inspect(project(tmp_path, mapping=mapping))
    assert table_for(graph).metadata["logical_name"] == "standard_orders"
    assert columns_for(graph, "Order.id") == ["standard_id"]
    assert columns_for(graph, "Order.name") == ["standard_name"]
    assert "annotation_extra" not in {node.name for node in graph.nodes if node.kind == "orm_column"}
    from kgmaker.framework import _jpa_xml_model
    model = _jpa_xml_model(tmp_path, {"persistence_unit": "orders"})
    assert model["default_access"] == "FIELD"
    mapping = (tmp_path / "META-INF/orders.xml").read_text(encoding="utf-8").replace("<access>FIELD", "<access>PROPERTY")
    (tmp_path / "META-INF/orders.xml").write_text(mapping, encoding="utf-8")
    assert _jpa_xml_model(tmp_path, {"persistence_unit": "orders"})["default_access"] == "PROPERTY"


def test_xml_capture_invalidates_same_length_edits_and_new_referenced_file(tmp_path):
    from kgmaker.graph_provider import validate_context_snapshot
    from kgmaker.worker_protocol import WorkerError
    root = project(tmp_path, mapping='''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
      <entity class="demo.Order"><table name="xml_orders"/></entity></entity-mappings>''')
    inspected = inspect_jvm(root, kotlin_backend="k1", home=HOME, classpath=[],
                            build_context={"persistence_unit": "orders"})
    captured = next(item for item in KnowledgeGraph.from_dict(inspected["graph"]).contexts if item.get("language") == "jvm")
    assert captured["jpa_xml_inputs"]["version"] == "jpa-xml-input-capture-1"
    mapping = root / "META-INF/orders.xml"
    original = mapping.read_text(encoding="utf-8")
    replacement = original.replace("xml_orders", "new_orders")
    assert len(original) == len(replacement)
    mapping.write_text(replacement, encoding="utf-8")
    with pytest.raises(WorkerError, match="persistence XML inputs changed"):
        validate_context_snapshot(root, captured)
    mapping.write_text(original, encoding="utf-8")
    descriptor = root / "META-INF/persistence.xml"
    descriptor_text = descriptor.read_text(encoding="utf-8")
    changed_descriptor = descriptor_text.replace("META-INF/orders.xml", "META-INF/otherx.xml")
    assert len(descriptor_text) == len(changed_descriptor)
    descriptor.write_text(changed_descriptor, encoding="utf-8")
    with pytest.raises(WorkerError, match="persistence XML inputs changed"):
        validate_context_snapshot(root, captured)
    descriptor.write_text(descriptor_text.replace("META-INF/orders.xml", "META-INF/missing.xml"), encoding="utf-8")
    refreshed = inspect_jvm(root, kotlin_backend="k1", home=HOME, classpath=[],
                            build_context={"persistence_unit": "orders"})
    missing_context = next(item for item in KnowledgeGraph.from_dict(refreshed["graph"]).contexts
                           if item.get("language") == "jvm")
    missing = next(item for item in missing_context["jpa_xml_inputs"]["inputs"]
                    if item["path"] == "META-INF/missing.xml")
    assert missing["status"] == "missing"
    (root / "META-INF/missing.xml").write_text(original, encoding="utf-8")
    with pytest.raises(WorkerError, match="persistence XML inputs changed"):
        validate_context_snapshot(root, missing_context)


def test_xml_input_capture_detects_default_appearance_deletion_and_symlink_retarget(tmp_path):
    from kgmaker.inspection import jpa_xml_input_snapshot
    root = tmp_path
    selected = {"persistence_unit": None}
    initial = jpa_xml_input_snapshot(root, selected)
    assert all(item["status"] == "missing" for item in initial["inputs"])
    (root / "META-INF").mkdir()
    (root / "META-INF/orm.xml").write_text("<x/>", encoding="utf-8")
    appeared = jpa_xml_input_snapshot(root, selected)
    assert appeared != initial
    (root / "META-INF/orm.xml").unlink()
    assert jpa_xml_input_snapshot(root, selected) == initial
    (root / "META-INF/a.xml").write_text("<a/>", encoding="utf-8")
    (root / "META-INF/b.xml").write_text("<b/>", encoding="utf-8")
    try:
        (root / "META-INF/orm.xml").symlink_to("a.xml")
    except OSError:
        pytest.skip("symlink creation is unavailable")
    first_link = jpa_xml_input_snapshot(root, selected)
    (root / "META-INF/orm.xml").unlink()
    (root / "META-INF/orm.xml").symlink_to("b.xml")
    second_link = jpa_xml_input_snapshot(root, selected)
    assert first_link != second_link


def test_legacy_jvm_context_is_readable_without_xml_and_stale_with_xml(tmp_path):
    from kgmaker.graph_provider import validate_context_snapshot
    from kgmaker.worker_protocol import WorkerError
    legacy = {"language": "jvm", "scope": "production", "source_snapshot_version": "selected-source-set-1",
              "source_files": {}, "worker": {}}
    validate_context_snapshot(tmp_path, legacy)
    (tmp_path / "META-INF").mkdir()
    (tmp_path / "META-INF/orm.xml").write_text("<entity-mappings/>", encoding="utf-8")
    with pytest.raises(WorkerError, match="uncaptured persistence XML"):
        validate_context_snapshot(tmp_path, legacy)


@pytest.mark.parametrize("language,version", [("jvm", "selected-source-set-3"),
                                                ("jvm", []), ("jvm", {}),
                                                ("typescript", "selected-source-set-2")])
def test_unsupported_or_mismatched_jvm_snapshot_versions_fail_closed(tmp_path, language, version):
    from kgmaker.graph_provider import validate_context_snapshot
    from kgmaker.worker_protocol import WorkerError
    (tmp_path / "META-INF").mkdir()
    (tmp_path / "META-INF/orm.xml").write_text("<entity-mappings/>", encoding="utf-8")
    context = {"language": language, "scope": "production", "source_snapshot_version": version,
               "source_files": {}, "worker": {}}
    with pytest.raises(WorkerError, match="snapshot version|snapshot on a non-JVM"):
        validate_context_snapshot(tmp_path, context)


def test_external_persistence_descriptor_symlink_is_captured_as_invalid(tmp_path):
    from kgmaker.framework import _jpa_xml_model
    from kgmaker.inspection import jpa_xml_input_snapshot
    (tmp_path / "META-INF").mkdir()
    outside = tmp_path.parent / (tmp_path.name + "-outside.xml")
    outside.write_text('<persistence/>', encoding="utf-8")
    descriptor = tmp_path / "META-INF/persistence.xml"
    try:
        descriptor.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    assert any(item.get("code") == "ORM_XML_FILE_INVALID"
               for item in _jpa_xml_model(tmp_path, {"persistence_unit": "orders"})["diagnostics"])
    captured = jpa_xml_input_snapshot(tmp_path, {"language": "jvm", "persistence_unit": "orders"})
    assert next(item for item in captured["inputs"] if item["path"] == "META-INF/persistence.xml")["status"] == "invalid"
    from kgmaker.graph_provider import validate_context_snapshot
    from kgmaker.worker_protocol import WorkerError
    legacy = {"language": "jvm", "scope": "production", "source_snapshot_version": "selected-source-set-1",
              "source_files": {}, "worker": {}}
    with pytest.raises(WorkerError, match="uncaptured persistence XML"):
        validate_context_snapshot(tmp_path, legacy)


def test_looped_persistence_descriptor_symlink_is_captured_without_exception(tmp_path):
    from kgmaker.framework import _safe_jpa_xml
    from kgmaker.inspection import jpa_xml_input_snapshot
    (tmp_path / "META-INF").mkdir()
    first = tmp_path / "loop-a.xml"
    second = tmp_path / "loop-b.xml"
    try:
        first.symlink_to(second)
        second.symlink_to(first)
        (tmp_path / "META-INF/persistence.xml").symlink_to(first)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    document, error = _safe_jpa_xml(tmp_path, "META-INF/persistence.xml")
    assert document is None and error["code"] == "ORM_XML_FILE_INVALID"
    captured = jpa_xml_input_snapshot(tmp_path, {"language": "jvm", "persistence_unit": "orders"})
    assert next(item for item in captured["inputs"] if item["path"] == "META-INF/persistence.xml")["status"] == "invalid"


def test_entity_override_does_not_delete_sibling_inherited_xml_column(tmp_path):
    mapping = '''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
      <mapped-superclass class="demo.Base"><attributes><basic name="created"><column name="base_created"/></basic></attributes></mapped-superclass>
      <entity class="demo.Order"><attribute-override name="created"><column name="order_created"/></attribute-override></entity>
    </entity-mappings>'''
    root = project(tmp_path, mapping=mapping)
    base = root / "src/main/java/jakarta/persistence/MappedSuperclass.java"
    base.write_text('package jakarta.persistence; import java.lang.annotation.*; @Retention(RetentionPolicy.RUNTIME) @Target(ElementType.TYPE) public @interface MappedSuperclass {}', encoding="utf-8")
    (root / "src/main/java/demo/Base.java").write_text('''package demo; import jakarta.persistence.*;
@MappedSuperclass class Base { @Id Long id; @Column(name="annot_created") String created; }
''', encoding="utf-8")
    (root / "src/main/java/demo/Order.java").write_text('''package demo; import jakarta.persistence.*;
@Entity @Table(name="orders") class Order extends Base {}
''', encoding="utf-8")
    (root / "src/main/java/demo/Other.java").write_text('''package demo; import jakarta.persistence.*;
@Entity @Table(name="others") class Other extends Base {}
''', encoding="utf-8")
    graph = inspect(root)
    assert columns_for(graph, "Order.created") == ["order_created"]
    assert columns_for(graph, "Other.created") == ["base_created"]
