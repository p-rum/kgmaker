from pathlib import Path

from kgmaker.framework import _jpa_xml_model


ORM = "https://jakarta.ee/xml/ns/persistence/orm"


def write_orm(root: Path, body: str) -> None:
    target = root / "META-INF" / "orm.xml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f'<entity-mappings xmlns="{ORM}" version="3.1">{body}</entity-mappings>',
        encoding="utf-8",
    )


def test_xml_named_query_and_native_query_are_captured_with_provenance(tmp_path):
    write_orm(
        tmp_path,
        '<named-query name="Order.byTenant"><query>select o from Order o where o.tenant = :tenant</query></named-query>'
        '<named-native-query name="Order.raw"><query>select * from orders</query></named-native-query>',
    )
    model = _jpa_xml_model(tmp_path, {})
    assert [item["name"] for item in model["named_queries"]] == ["Order.byTenant", "Order.raw"]
    assert {item["language"] for item in model["named_queries"]} == {"JPQL", "NATIVE_SQL"}
    assert all(item["provenance"]["xml_mapping_file"] == "META-INF/orm.xml" for item in model["named_queries"])


def test_xml_named_query_duplicate_is_ambiguous_and_missing_body_is_unresolved(tmp_path):
    write_orm(
        tmp_path,
        '<named-query name="Order.duplicate"><query>select o from Order o</query></named-query>'
        '<named-query name="Order.duplicate"><query>select o from Order o where o.id = 1</query></named-query>'
        '<named-native-query name="Order.missing"/>',
    )
    model = _jpa_xml_model(tmp_path, {})
    duplicate = [item for item in model["named_queries"] if item["name"] == "Order.duplicate"]
    assert len(duplicate) == 2 and all(item["ambiguous"] for item in duplicate)
    codes = {item["code"] for item in model["diagnostics"]}
    assert "ORM_XML_NAMED_QUERY_AMBIGUOUS" in codes
    assert "ORM_XML_NAMED_QUERY_UNRESOLVED" in codes


def test_xml_incomplete_duplicate_name_cannot_fall_back_to_valid_definition(tmp_path):
    write_orm(
        tmp_path,
        '<named-query name="Order.same"/>'
        '<named-query name="Order.same"><query>select o from Order o</query></named-query>',
    )
    model = _jpa_xml_model(tmp_path, {})
    assert any(item["name"] == "Order.same" and item.get("ambiguous") for item in model["named_queries"])
    assert "ORM_XML_NAMED_QUERY_AMBIGUOUS" in {item["code"] for item in model["diagnostics"]}
