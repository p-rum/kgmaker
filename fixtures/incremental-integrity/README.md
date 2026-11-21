# Mutation workspace and cold compiler oracle

This T047-S01 fixture assembles the existing Kotlin/TypeScript, Kafka and Flyway
fixtures in an isolated workspace. Run the replay and oracle with the project
test runner.

```bash
python -m pytest -q tests/test_incremental_equivalence.py
```

The oracle records independent expectations for the initial source graph,
workspace contract path, missing compiler-backed frontend path, and Kafka proof
gap. The source-only baseline leaves the JVM build release manifest absent. The mutations report exact
changed paths and a SHA-256 digest of the resulting file map. The tests rebuild
the fixture in an isolated directory and compare both runs byte for byte.

The test suite also checks a workspace snapshot after each of the ten mutations.
Only the expected qualified file hashes change. The hand-written oracle follows
the overloads through signature change, move and delete, the new declaration after add,
and its unchanged caller. Kafka topic changes retain `UNKNOWN` and
`CONFIG_SCOPE_UNPROVEN`. V11 adds `public.extra` in the offline Flyway schema
with `MIGRATION_DERIVED` provenance and `UNASSESSED` data availability. The
contract and tsconfig edits are checked as input changes in this source-only
run. [Test evidence](../../docs/changes/137_prepareIncrementalMutationOracle.md).

An isolated source-only case puts byte-identical `fixture.shared.Twin`
declarations in both repositories at `src/Twin.kt`. Each declaration belongs
to its own repository file. Moving the entire fixture to a different absolute
directory changes its reported roots and preserves the source map and graph.

Logical identity across line movement currently fails under strict XFAIL.
The explicit Kotlin oracle compares two cold inspections around the addition of
`Added.kt`. With prepared JDK21 and pinned Kotlin 2.1.10 K1/K2 workers it proves
the previously unresolved `missingScore()` resolves in a new compiler context.
The caller bytes stay identical and the integer overload remains the selected
call target. This check publishes no compiler graph.

A second cold Kotlin test changes `score(Int)` to `score(Boolean)` while
`Caller.kt` and the declaration of `score(String)` keep the same bytes. Both
workers report `score(2)` as unresolved without a declared target or dispatch
candidate. The unchanged `score("xy")` still resolves to the String overload in
the new compiler context. The check publishes no compiler graph.

The cold deletion check uses the existing move and delete mutations to remove
`Renamed.kt`. K1 and K2 report the byte-identical caller's `score("xy")` as
unresolved in a new context, with no target or dispatch candidate. The control
call still resolves to `Added.kt` in both contexts. Both inspections use
`publish=False` and leave the fixture without a persisted compiler graph.

The Kafka test captures each backend module with JDK21, K1 or K2 and an explicit
resource source-set mapping for profile `blue`. The matching graph contains one
`kafka_binding_match` edge between the resolved producer and consumer. After
changing only the consumer topic and capturing compiler evidence in a fresh
index, both bindings are resolved and refer to different topics. Delivery
remains `NOT_OBSERVED`.

The backend-to-frontend variant uses the actual Kotlin `ExposureOutput.decline`
field, the declared OpenAPI response and an exact typed TypeScript client
projection rendered in JSX. The oracle checks the property declaration in the
client file and the occurrence in the page. The TypeScript 5.7.3 worker analyzes
the synthetic client and JSX without installing packages into the fixture. The
workspace path uses content-checked contract/client hashes and a `LOCAL_DECLARED` release
record. Changing the OpenAPI release version also changes the contract checksum.
With both stale inputs, the old client provenance is rejected with
`VALUE_FLOW_GENERATION_OR_RELEASE_UNKNOWN`. The endpoint has no remaining
compiler-backed bindings to any client target.

The JVM artifact variant uses an explicit offline Gradle 8.13 build to publish a
real Java 21 JAR and an execution-bound producer manifest. A dedicated JVM
verifier inside the frontend repository records the same JAR bytes and resolves
its exact method. The workspace reports one `supplies_classpath` edge when all
hashes and context selectors agree. A wrong output hash or changed JAR bytes in
the consumer classpath produces `PARTIAL` and removes the edge. The TypeScript
context has no JVM classpath and keeps its separate API contract evidence.
The rest of the mutation matrix and incremental equivalence remain open.
See [the recorded verification](../../docs/changes/137_prepareIncrementalMutationOracle.md).

```bash
KGMAKER_TEST_GRADLE=/path/to/gradle-8.13/bin/gradle \
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 python -m pytest -q \
  tests/test_incremental_equivalence.py tests/test_workspace.py tests/test_kafka_bindings.py \
  tests/test_cross_repo_artifacts.py
```
