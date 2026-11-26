# Čtecí Mermaid diagram dodaného procesu

26. listopadu 2026. [T035](../tasks/T-035_render-business-process-mermaid.md),
první výřez nad `main` `c4a1edb59f140faeafba0d5e979023bba185f3f1` se sloučeným
JSON rozsahem T034. Výchozí `ProcessView` obsahoval původní technické uzly a
přechody. Pro tento model chyběl veřejný Mermaid renderer.

## T035-S01 a AC01 — výskyty a služby

`kgmaker.process_render.render_process_mermaid(view)` přijímá existující typovaný
`ProcessView` schema 1. Podgrafy používají jen výslovně uvedené `service:` owner
ID, ostatní uzly zůstávají mimo service lanes. Renderer zachovává každý původní
uzel a orientovanou hranu včetně paralelních výskytů. Vazby `async` mají tečkovanou
šipku. Komentáře mapují výskyty zpět na stejný dodaný model.

## T035-S02 a AC01/05 — podmínky, cykly a hranice

Podmínky, retry, výjimky a smyčky vycházejí z technických popisků, relací a
atributů `ProcessView`. U fan-outu renderer nevkládá pořadí mezi konzumenty.
Viditelné hranice přebírají doložený stav a freshness. Diagram zachovává
rozsah, kontext, provenance, mezery a explicitní `PARTIAL` či `TRUNCATED`.
Výsledek neodvozuje runtime pozorování ani úspěšné doručení.

## T035-S03 a AC03/04/05 — stabilita, escaping a limity

ID jsou deterministická podle výskytu v modelu. Nový modul přímo používá
stávající bezpečný textový a JSON encoder Mermaid, kontrolu bezpečnosti výstupu
a sdílený ohraničený průchod vstupem. Při neplatném typu, scope nebo kontextu,
nebezpečném obsahu či překročené velikosti skončí `ProcessMermaidError` bez
výstupu. Schéma modelu, úložiště, architektonické renderery a obě existující
CLI cesty se nemění. Migrace není potřeba.

## T035-S04 a AC01/03–05 — skutečné testy

Na baseline validní `checkout.json` narazil na chybějící modul
`kgmaker.process_render`, **1 FAIL**, raw exit 1. Další cílená regrese zachytila
neescapovaný text scope v titulku návrhu. Titulek, uzly a hrany nyní používají
stejný textový encoder. JSON metadata chrání odpovídající sdílený encoder.

`tests/test_t035_render_business_process_mermaid.py` prověřuje:

- `test_t023_checked_in_branch_cycle_and_origins_are_deterministic` a
  `test_t023_golden_parses_and_renders_branch_cycle` pro podmínky, cyklus,
  7 uzlů, 8 hran, původní důkazy, nulové I/O a shodu kanonických bajtů.
- `test_t028_projection_places_service_lanes_without_ordering_fanout` pro
  stávající projekci T028 se dvěma explicitními vlastníky, 13 uzly a 12 hranami.
- `test_real_t029_javac_retry_dlt_keeps_static_boundary_and_exception_path`
  pro skutečný Javac 21.0.6, 22 uzlů a 24 hran. Zachová výjimku, retry, DLT
  a doložené `NOT_OBSERVED` i soubory a JSON vstupu.
- `test_truncated_parallel_edges_escaped_text_and_no_unverified_business_label`
  pro bezpečný text v popiscích i titulku, `TRUNCATED`, 7 uzlů a 9 hran, včetně
  dvou shodně orientovaných výskytů. Dodaný příznak `APPROVED` sám nezmění popisek.
- `test_invalid_input_and_limits_leave_supplied_and_last_valid_artifact_unchanged`
  a `test_output_bound_refuses_the_whole_diagram` pro odmítnutí bez vedlejších
  účinků.

Čtyři diagramy zpracoval připnutý Mermaid 11.4.1 s jsdom 26.0.0 a Node 24.22.3
z existujícího locku. `tests/rendering/validate_t035_process.mjs` porovnal vrcholy,
orientované hrany a lanes přímo z parseru. V SVG ověřil počty vrcholů a hran
a absenci aktivních prvků a odkazů z dodaného textu. Reálný cílený běh skončil
**109 PASS / 0 SKIP / 0 FAIL** za 14,06 s. Zahrnul 11 případů T035 a regrese
T021 (28), T023 (69) a jednu původní kontrolu fan-outu T028. SHA-256 JUnit
`4dc00fea63063eca471d577114de3a6d0c912c0795442677d85caac10f4f09d0`.

Tento místní doklad patří stromu `437cc36b71520e601b194d88f9b614e7303d8558`,
který byl zveřejněn při otevření [draftu #183](https://github.com/p-rum/kgmaker/pull/183)
jako head `ab02b75d254ce52b224086953fd59d22f817eec3` nad `c4a1edb5`.

## T035-S05 a AC06 — dokumentace a předání

[README](../../README.md#local-technical-process-paths-t025) a
[Python příklad](../process-paths.md#mermaid-for-a-supplied-processview-t035)
ukazují cílové použití čistého rendereru. [Revize zadání](../tasks/T-035_render-business-process-mermaid.md),
[acceptance](../acceptance-inventory.md#t035--mermaid-nad-dodaným-typovaným-processview)
a [stavová matice](../production-analysis-progress.md) vedou otevřený výřez
ve stavu `PR_OPEN / PARTIAL`. Úplná sada, nezávislé review a hostované CI
měly v uvedeném místním ověření stav NOT_RUN. T036 stále čeká na dodání T035.
Zbývá připojení CLI, autorita schválených popisků z T032 (AC02) a navazující
vysvětlení a export.
