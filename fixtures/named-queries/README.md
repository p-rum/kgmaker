# Named query compiler fixture

T003-S06-W06, JPA rule `annotation-source-v9-named-query-containers`.
`tests/test_named_query_containers.py` copies these files to an isolated project,
adds bounded Jakarta/Spring API stubs, and invokes the real JVM worker/Javac.
The fixture does not build or execute an application or connect to a database.

`Model.java` includes explicit and repeatable JPQL/native containers, repository
references, parameters and DTO projections. Native literal/comment-only table
lookalikes and commented UPDATE/DELETE statements exercise lexical boundaries. `orm.xml` supplies root/entity
queries, duplicates, incomplete definitions and annotation/XML collisions.
Tests also select two persistence units, replace XML table names, reject malformed
mapping, and verify strict/cancel/timeout publication and offline refresh.

Expected results and exact verification: [change120](../../docs/changes/120_namedQueryContainers.md).
