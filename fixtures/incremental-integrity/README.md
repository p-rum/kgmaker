# Source-only mutation workspace

This T047-S01 fixture assembles the existing Kotlin/TypeScript, Kafka and Flyway
fixtures in an isolated workspace. Run the replay and oracle with the project
test runner.

```bash
python -m pytest -q tests/test_incremental_equivalence.py
```

The oracle records independent expectations for the initial source graph,
workspace contract path, missing compiler-backed frontend path, and Kafka proof
gap. The release manifest is intentionally absent. The mutations report exact
changed paths and a SHA-256 digest of the resulting file map. The tests rebuild
the fixture in an isolated directory and compare both runs byte for byte.

Logical identity across line movement currently fails under strict XFAIL.
This fixture measures source-only behavior. Further T047 tests are required
for compiler resolution, positive release/Kafka binding, all mutation cases and
incremental equivalence.
