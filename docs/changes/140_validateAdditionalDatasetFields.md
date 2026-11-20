# Validace dalších hodnot syntetického datasetu

[T046 revize 6](../tasks/46_addTemplatesTestsAndTraceability.md),
T046-S03, T046-S04, T046-AC04 a T046-AC07. Oprava
[issue #91](https://github.com/p-rum/kgmaker/issues/91) navazuje na sloučený
[#43](https://github.com/p-rum/kgmaker/pull/43). Zdrojová baseline
`465b121992aad50c2885acef0fd038531a31293a`. Cílový GitHub main
`8f362471a8254ff9a0e44870c490a1dcb6b067b1` přidává samostatný PR review workflow.

## T046-S03 / T046-AC04, AC07 — validace kandidáta

[`testgen.schema_errors`](../../src/kgmaker/testgen.py) dříve přijala například
`{"extra":"bad"}` vůči `{"type":"object","additionalProperties":{"type":"integer","minimum":1}}`.
Nyní používá stejnou rekurzivní kontrolu známých i dodatečných hodnot. Pro tento
typový problém vrací `$.extra:type`. Nepovolený tvar keywordu nebo chybějící
podporovaný typ schématu odmítne i bez datové hodnoty navíc. Vynechaný klíč a
booleany mají zpětně kompatibilní chování. Formát kandidáta i uložených revizí
zůstává kompatibilní.

Validace i apply sdílejí kontrolu. Neplatný kladný kandidát se nezapíše.
Ověření zahrnuje přesný stav souborů před a po odmítnutí.

## T046-S04 / T046-AC04 — vnořená kontrola a downstream

Pole objektů a vnořená omezení fungují ve stejném subsetu. Vnořený nepodporovaný
keyword se objeví v `unchecked_constraints` s dataset ID a cestou. Příklad
je `numbers:$["metrics.v2"][0].name:pattern`. Report o návrhu má execution
`NOT_RUN`. Export JSON/CSV, freshness a lineage používají existující kontrakty.

Nezávislé review reprodukovalo shodnou chybovou cestu pro doslovný klíč
`"x.y"` a vnořené `x → y` uvnitř typované dodatečné hodnoty. Druhá úprava
rozlišuje `$.extra["x.y"]` od `$.extra.x.y` a zachovává starší formát mimo
typovanou část. Vnořené nepoužité podsložky jsou mimo validační průchod.
Steelman našel stejnou záměnu v předchozích rodičích. T052 předal nález
`artifact:04c51fcfc91e0f034b8ed59fbeda493d67afbd110706a4621e4a768475fa015c`
v iteraci 1. Finální formát uchovává přesný prefix s indexy až ke kořeni,
například `$["a.b"][0].extra:type`. Klasické diagnostiky mimo typovanou větev
stále používají svůj původní formát.

[README](../../README.md), [CLI a dataset příklady](../delivery-workflow.md),
[spravovaná reference](../../.agents/skills/kgmaker-testgen/references/candidate.md)
a odpovídající [instalační template](../../src/kgmaker/skills.py) popisují stejný
subset. [Acceptance](../acceptance-inventory.md), [stav](../production-analysis-progress.md)
a historický [change58](58_addExistingFunctionTests.md) evidují tento follow-up.

## Skutečné kontroly

- `pytest -p no:cacheprovider -q --tb=short tests/test_delivery.py -k additional_properties`
  na původním zdroji — RED, 3 FAIL, 21 deselected.
- `pytest -p no:cacheprovider -q --tb=short tests/test_delivery.py tests/test_synthetic_data.py tests/test_skills.py tests/test_workflow.py tests/test_workflow_profiles.py tests/test_provenance.py`
  — 103 PASS, 0 SKIP, Python 3.12. Testy ověřují typ, minimum, vnořenou cestu,
  oba booleany, nepodporovaný tvar a nulovou mutaci apply.
- `git diff --check` — PASS. Úplná sada, GitHub Actions a externí T045 review
  pro nový pár jsou NOT_RUN. Validace kandidáta probíhá staticky a rozsah
  compiler a runtime evidence se tím nemění.
