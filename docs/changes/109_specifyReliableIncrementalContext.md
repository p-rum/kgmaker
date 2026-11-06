# 109 — Zadání spolehlivého inkrementálního kontextu

Datum: 2026-11-06
Typ: dokumentační změna, SPECIFICATION
Baseline: fbb0957be895e1e8967339bba6cd7e4b4e7b769f

## Problém

Technický přehled popsal rizika zaniklých příchozích vazeb, vynechaných ochranných mechanismů, neúplné hranice dopadu a zastaralých testových výsledků. KGMAKER již má související zadání i implementaci; obecný nový plán by mohl zdvojit cache nebo rozpracované T046 workflow.

## Skutečné změny

- Přidáno [T047](../tasks/47_addReliableIncrementalContext.md), revize 1: 13 implementačních kroků, konkrétní moduly, větve, závislosti, datové kontrakty, acceptance T047-AC01–AC13 a negativní mutation matice.
- Zdokumentována source-only identita s řádkem, existující compiler freshness a hranice příchozích důkazů. Plán odděluje logical key, occurrence, context a evidence revision.
- Přidán návrh podpůrných skupin OR/AND, atomických generací, bezpečnostního kontextu, řízeného traversal, contract-impact a content-bound dokladů testu.
- Zohledněny T003-S10, T013/T014, T037/T038 a otevřené T046 PR; nevzniká druhá číselná řada ani paralelní journal.
- Doplněn registr. T046 zůstává rezervované otevřeným PR #41.

## Kompatibilita

Žádná změna runtime kódu, schématu, CLI ani uložených grafů. Migrace a rollout v T047 jsou budoucí požadavky. Žádná acceptance implementace není tímto dokumentem označena PASS.

## Provedené kontroly

- Přečteny AGENTS.md, copilot instructions, registr, cílené moduly a relevantní testy nad baseline přes GitHub.
- Zkontrolován main tree a seznam všech 7 otevřených PR (#4, #40–45), včetně jejich změněných souborů. Nejvyšší přidělené Task ID 46; nejvyšší change-note číslo 108. Nové identity T047 a 109.
- Programově ověřeny lokální Markdown odkazy, existence zmiňovaných baseline modulů, kontinuita S01–S13/R01–R13/AC01–AC13, unikátní registrace a absence koncových whitespace v nových dokumentech.
- Ověřeny primární abstrakty A.S.E 2.0 a Soei. Neznovuověřené podrobnosti Knot incidentu a Ripple jsou v zadání výslovně označeny; nejsou základem tvrzení o chybě KGMAKERu.

## Neprovedené kontroly

Runtime testy, CLI/scan/memory workflow, compiler fixtures, benchmark, GitHub CI a nezávislé review nebyly spuštěny v této dokumentační práci. Není lokální checkout; rekognoskace byla přes konektor. GRAPH.md konektor vrátil bez obsahu; závěry byly ověřovány ve zdrojích. Generované grafy se ručně nemění.

## Příklad

Přidání komentáře nad Kotlin metodou má zachovat její logical key. Konkrétní source range a freshness důkazu se mohou změnit. Po změně signatury musí nezměněný caller projít novým rozlišením; stará hrana se nesmí připojit podle podobného názvu. Test PASS před editací nesmí potvrzovat ověření upravených vstupů.

## Zbývající práce

Implementace všech kroků T047, jejich runtime acceptance, benchmark a review. Nejprve dodat S01 fixture/oracle a S02 stabilní klíče; S10/S11 počkají na skutečné upstream kontrakty T046. Dokumentační PR nic nemerguje.
