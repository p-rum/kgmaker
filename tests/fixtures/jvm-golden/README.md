# Hand-labelled JVM acceptance corpus — T003-S04-W05

`expected.json` is a reviewed test inventory, not an application catalog or a
worker-generated snapshot. Expectations must be checked against source and the
compiler support contract before changing them. There is no accept/update switch.

The explicit prerequisite base is `fe36c554f88b8509457cd9eb8ea439325cd03dc3`
(`stack/t003-s04-w05-prerequisites`): approved local PR35 head
`89e50cf4cf8edbebc4f9d08879656698c75ebd50` and PR37 head
`c8867f3367e2ada0348d5cd44584162ec4558530`, both descending from main `33dc239`.
These upstream implementations remain separate; the corpus adds no runtime code.

| Case | K1 resolved / unresolved source sites | K2 resolved / unresolved source sites | K2 unsupported Kotlin CFGs |
|---|---:|---:|---:|
| Existing mixed Java/Kotlin golden | 5 / 0 | 5 / 0 | 3 |
| Java owner/overload, branches, recursion, lambda/reference, reflection + invalid calls | 12 / 2 | 12 / 2 | 0 |
| Existing K2 source fixture (also inspected with K1) | 4 / 2 | 3 / 3 | 8 |
| Extension/default/inline/suspend + Java caller | 4 / 0 | 4 / 0 | 5 |
| Existing actual ordered dependency dispatch fixture | 3 / 0 | 3 / 0 | 0 |

Resolved counts include two method-reference creation sites per backend. Those
sites never become executable call adjacency. Unsupported entries are separate
exact model/CFG diagnostic identities: the corpus does not invent an
`UNSUPPORTED` call-site evidence kind. The inventory also retains unsupported collapsed Java expression order and
SHA-bound multi-release stdlib candidate-enumeration diagnostics; physical JVM
lookup is separate. Diagnostic event multiplicity is checked, not a runtime
precision denominator. K1 source-level inline extension attribution is checked as such (inline metadata,
no invented callee source location), not a claim that a public facade member is
physically invoked. The K2 mapped String builtin remains an
unresolved target; it is not silently attributed to a fabricated JVM member.

The existing five-call inventory is reused from
`fixtures/build-inspection/ground-truth.json` (its existing entries gain manual
source locators); the existing ordered JAR producer
is reused from `test_dependency_dispatch.py`. `Advanced.kt`, `Work.kt` and
`Helper.java` were moved byte-for-byte from existing inline fixtures and remain
shared by their original tests. The Advanced property/operator/initializer
matrix is an upstream proof, not a second duplicated expected-result catalog.

Actual JDK21 and Kotlin2.1.10 workers inspect copied source and prepared class
inputs. Fixture compilation is explicit and no project application, reflection
or coroutine code is executed. Inspection verifies unchanged source/class/store
bytes. Every selected source call has its hash, range, caller/target declaration
identity and status checked. Counts, extra/missing/retargeted/stronger observations
and unsupported diagnostic identities fail the test. Opposite CFG branches are
not a sequence; recursive process traversal remains bounded.

Run the corpus after explicitly preparing the same prerequisites as the mandatory
compiler CI job:

```bash
PYTHONPATH=src KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 \
  python -m pytest -q tests/test_jvm_golden_corpus.py
```

K1 language1.9 compatibility and K2 language2.1 attribution are different support
matrices. Neither static corpus equality nor resolved reflection APIs establish
runtime dispatch, input feasibility, network/data availability, global async
order or production-project precision. S04 and T003 remain bounded/PARTIAL.

K1 default-argument declaration metadata is supported while its CFG evaluation
remains explicitly unsupported; the corresponding source diagnostic is inventoried.
