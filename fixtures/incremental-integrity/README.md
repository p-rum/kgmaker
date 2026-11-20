# Mutation workspace and cold Kotlin oracle

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

The test suite also checks a workspace snapshot after each of the nine mutations.
Only the expected qualified file hashes change. The hand-written oracle follows
the original overloads through move and delete, the new declaration after add,
and its unchanged caller. Kafka topic changes retain `UNKNOWN` and
`CONFIG_SCOPE_UNPROVEN`. V11 adds `public.extra` in the offline Flyway schema
with `MIGRATION_DERIVED` provenance and `UNASSESSED` data availability. The
contract and tsconfig edits are checked as input changes in this source-only
run. [Test evidence](../../docs/changes/137_prepareIncrementalMutationOracle.md).

Logical identity across line movement currently fails under strict XFAIL.
The explicit Kotlin oracle compares two cold inspections around the addition of
`Added.kt`. With prepared JDK21 and pinned Kotlin 2.1.10 K1/K2 workers it proves
the previously unresolved `missingScore()` resolves in a new compiler context.
The caller bytes stay identical and the integer overload remains the selected
call target. This check publishes no compiler graph. Positive release/Kafka
binding, the rest of the compiler mutation matrix and incremental equivalence
remain open.
