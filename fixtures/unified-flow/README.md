# Unified flow acceptance fixture

`src/main/java/Checkout.java` is explicitly inspected by
`tests/test_unified_flow_views.py::test_actual_javac_public_formats_parser_and_readonly_failures`.
It contains alternative branches, a loop, a static call/return and an intentionally
unresolved gateway. Javac/JDK21 is required for the actual acceptance; the application
is never executed. Rendering after inspection forbids subprocess and network calls.

The separate producer-shaped `model_graph()` in that test module is a schema
fixture, not a compiler run. Its checked-in golden JSON/Markdown/Mermaid in
`tests/golden/unified-flow/` includes mutually exclusive branches, an async boundary,
a cycle, unresolved detail and exact proof references. Parser verification uses
pinned `tests/rendering/package-lock.json` (Mermaid11.4.1/jsdom26):

```sh
node tests/rendering/validate_unified.mjs tests/golden/unified-flow/branch.mmd tests/golden/unified-flow/branch.json
```

Dependencies must be prepared explicitly; rendering never installs them.
[Change128](../../docs/changes/128_unifiedFlowViews.md) records the exact environment,
commands, earlier failures, final PASS and remaining scope. See
[public contract](../../docs/unified-flow-views.md) for legacy input, budgets and atomic output.
