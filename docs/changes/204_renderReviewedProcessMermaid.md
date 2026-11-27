# Čtecí Mermaid diagram se schválenými popisky T032

27. listopadu 2026. [T035](../tasks/T-035_render-business-process-mermaid.md)
rozšiřuje ověřenou technickou cestu z [#183](https://github.com/p-rum/kgmaker/pull/183).
Technický diagram zachovával všechny výskyty dodaného `ProcessView`. Chyběla cesta,
která by připojila popisky po schválení v existujícím místním úložišti T032.
Výchozí zdrojový commit je `e7b2f36ef764c16c566db20ec06cee82e47c84ba`.

## T035-S01 a T035-AC02 — účinné schválení stejného pohledu

`src/kgmaker/process_render.py` přidává `render_reviewed_process_mermaid`. Čte
efektivní rozhodnutí [T032](../process-review-store.md) nad stejnou normalizovanou
kopií `ProcessView`, z níž vytváří diagram. Vstupem je existující místní kořen
úložiště a výslovně dodané dokumenty a konflikty. T032 posuzuje přesnou aktuálnost
podkladů vůči uloženému schválení s deklarovanou místní identitou
`LOCAL_DECLARATION_NOT_AUTHENTICATED`. Dřívější schválení může po pozdějším
odmítnutí zůstat účinné, pokud stále odpovídá dodanému modelu a podkladům.
Pouhý příznak v dodaném modelu schválení nedokládá.

`EMPTY`, `REJECTED` a `NEEDS_REVALIDATION` skončí příslušným kódem
`PROCESS_MERMAID_REVIEW_*` bez diagramu. Chyba čtení či vstupu přebírá existující
diagnostiku T032. `test_reviewed_diagram_requires_current_local_approval_and_original_captures`
ověřuje všechny tři stavy, změněný model, chybějící i změněný podklad, výslovný
konflikt a poslední schválení jiné verze. Porovnává také obsah a časy změn souborů.

## T035-S02 a T035-S03 · T035-AC02 až T035-AC05 — přesné výskyty

Společný renderer doplní schválený popisek do titulku procesu nebo k přesnému ID
uzlu či hrany. Opakovaný shodný popisek téhož výskytu zobrazí jednou. Titul a
technické texty, mapovací komentáře, orientace, pořadí a násobnost výskytů, lanes,
coverage, kontext a původní důkazy zůstávají zachované. Stávající čistá funkce
`render_process_mermaid` má stejný golden SHA-256
`55881e998d92ad88d42a03e3f28f259256827b9429ed1ce1c8be4f3833de57fa`.

Stávající escaping a kontrola bezpečnosti platí i pro přidané popisky.
Rozpočet povoluje nejvýše 500 hran, 50 000 jednotek UTF-16 v těle flowchartu
a 4 000 000 bajtů UTF-8 v celém výstupu. Funkce nevytváří soubory ani nepřepisuje
schválení či technickou evidenci. Migrace schématu nebo úložiště není potřeba.
`test_approved_label_obeys_diagram_safety_and_host_budget` ověřuje odmítnutí textu
schváleného T032, který neprojde ochranou výstupu, a překročení rozpočtu UTF-16
po připojení jiného schváleného textu. Čistý diagram daného vstupu se vejde do
rozpočtu. Odmítnutí zachová vstupy i poslední uložený diagram.

## T035-S04 · T035-AC02 až T035-AC04 — skutečné ověření

`test_effective_reviewed_labels_bind_to_exact_title_node_and_parallel_edge`
zapíše skutečné APPROVE a následné REJECT přes veřejné T032 API. Rozšířený
`tests/rendering/validate_t035_process.mjs` ověřuje v Mermaid 11.4.1 a jsdom 26.0.0
titulek, právě jeden uzel a právě jeden ze dvou paralelních přechodů. Parser
porovnává sedm uzlů, devět orientovaných hran a jednu lane se stejnými mapovacími
záznamy. SVG zachovává popisky jako text. Test porovnává JSON modelu a obsah
i časy změn souborů včetně posledního uloženého diagramu.

Čtyři nové případy na výchozím zdroji selhaly kvůli chybějícímu rozhraní.
Raw exit 1, JUnit SHA-256
`649f72da75c1a2ba902d30b0432b51ca2ed09225446cd1023ed1cb80061ad333`.
Přípravný běh T032 a T035 v neúplné kopii skončil 60 PASS a chybou při přípravě
Javacu, protože kopie postrádala soubor se zámkem závislostí. Po zahrnutí
připnutých zámků prošlo všech 61 případů, 0 SKIP, 0 FAIL, raw exit 0. Běh použil
CPython 3.13.18, uzamčené Mermaid a jsdom a skutečný Javac 21.0.6 pro retry a DLT.
JUnit SHA-256 `e367bee4d2d2b90f0489938c1435047dbb6d9dd8cbd5d0bbf95608c53e3bcebe`.
Tento doklad patří zdrojovému stromu `881229aa1793498269a1e4e15c137bc3d5d8eaba`
nad `e7b2f36ef764c16c566db20ec06cee82e47c84ba`. Obsah všech vstupů kopie zůstal
stejný, včetně tří souborů implementace a testů v indexu.

## T035-S05 a T035-AC06 — předání výřezu

Po sloučení [#187](https://github.com/p-rum/kgmaker/pull/187) je základem tohoto
výřezu commit `675887aade744579a36e58b0f90822427afb4fde` z větve `main`.
Ve zdrojovém indexu `8f368886a922a3d68198bc37171ae430f0c76a8a` mají tři soubory změny stejný obsah
jako v cíleně ověřeném stromu. Příklad a hranice rozhraní uvádějí
[README](../../README.md#local-technical-process-paths-t025) a
[návod k procesu](../process-paths.md#mermaid-for-a-supplied-processview-t035).
[Acceptance](../acceptance-inventory.md#t035--mermaid-nad-dodaným-typovaným-processview)
dokládá AC02 a [stavová matice](../production-analysis-progress.md) zachovává
`MERGED / PARTIAL` pro dosavadní dodávku. Sloučená technická cesta splňuje
závislost T036 podle [dokladu #187](203_recordRendererExporterEvidence.md).

Širší Mermaid CLI a výkaz T036 mají samostatný rozsah. Příkaz `process render`
nadále vydává JSON. Při uvedeném přípravném ověření měly úplná sada, nezávislá
recenze integrovaného výřezu a hostované CI stav `NOT_RUN`.
