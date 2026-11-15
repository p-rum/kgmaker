# T003-S07-W08 ranking fixture

`src/main/java/Orders.java` is explicitly inspected by the Javac worker in
`tests/test_evidence_ranking.py::test_actual_javac_ranking_fixture_and_public_cli`.
The missing `MissingClient` is intentional: incomplete evidence must remain
visible. `Currency.decide` has a real call path; Currency/Order type references,
test assertions, configuration mentions and method-reference construction do not
establish production invocation. Interface dispatch remains bounded by the worker.
No application or build is run. The test copies source files to a temporary root.

The in-memory v1/v2/v3 model fixtures use explicitly modeled inspection metadata
and fixture-file hashes, not fabricated native results. They additionally test
authority admission, cross-variant boundaries, side effects, ambiguous and
runtime edges, invalid references, variant provenance, no mutation and deterministic
ordering. They are schema fixtures, not compiler execution evidence.
See [capability](../../docs/evidence-ranking.md) and
[change126](../../docs/changes/126_evidenceRanking.md) for actual checks and limits.
