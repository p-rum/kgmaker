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
