# T046-S03 — Testovací návrhy existující funkcionality

## Problém a skutečná změna

Uživatel požaduje projektové šablony, generování testů/dat pro existující
funkcionalitu a dohledatelný řetězec požadavek–analýza–task–změna–test s osobami.
Offline testgen prepare/validate/apply/report/export nad source/graph/workspace evidence. Kandidát už obsahuje společný kontrakt datasetů; oddělené datové acceptance a další hranice ověřuje S04. Host agent vytváří návrh, kgmaker model nevolá.

Zadání: [T046](../tasks/46_addTemplatesTestsAndTraceability.md), Revision 1.
Krok: T046-S03; požadavky T046-R01–R05; acceptance T046-AC02, AC03, AC08.
Baseline balíku: `33dc239a6d2eca2f42364a7b314aeb377e4b441a`.
Závislé PR výslovně používají předchozí větev balíku jako base; po merge se
retargetují a znovu ověří integrace. Žádný z těchto PR se automaticky nemerguje.

## Kompatibilita a příklad

V1 task se čte bez změny identity, implementace/review doplní v2 content bindings.
Starší klient musí být aktualizován před čtením v2. Šablony jsou projektové;
workflow journal a testgen state jsou lokální. LLM pracuje v hostiteli bez API klíče.
Příklad celého postupu a přesné JSON kontrakty: [delivery workflow](../delivery-workflow.md).

## Ověření

- PASS: test_delivery.py bez gate a CLI routing scénářů (10 případů).
- PASS: Python compile a `git diff --check` nad připravenými zdroji.
- E2E (finální integrovaný balík S06): exportovaný unittest skutečně projde, po záměrné změně funkce selže.
- NOT_RUN: pytest sada (pytest není instalován), GitHub CI a nezávislé review.
- SKIP/blocked: skutečné JVM/K2/TypeScript worker kontroly vyžadující nedostupný
  JDK 21+/připravené worker distribuce; žádná širší toolchain podpora se neprohlašuje.

Git transport zde nefunguje kvůli proxy; upstream soubory a publikace používají
GitHub konektor. Po obnovení upstream tree a podepsaného commit objektu má lokální HEAD přesně
upstream SHA `33dc239a6d2eca2f42364a7b314aeb377e4b441a`; shoda byla ověřena hashem. Oba velké artefakty byly obnoveny přes
Git blobs se shodnými upstream blob SHA před zpracováním změn.

## Omezení a zbývající práce

Lokální osoba má LOCAL_DECLARED trust; hash není autentizace/podpis. Charakterizace
kódu není business oracle. Testgen výstupy jsou NOT_RUN a data SYNTHETIC; skutečné
běhy se evidují odděleně. Neznámé constraints/syntaxe nejsou PASS. Konzervativní
freshness může vyžadovat nový packet i po exportu testů. Dokončení tohoto kroku
neznamená dokončení jiných T003/T004 acceptance. Před merge zbývá nezávislé review
a dostupné požadované CI; cílové schopnosti celého balíku zpřístupňuje až S06.

## Opravy nezávislého review — 2026-10-27

Kanonické cesty a JSON datové porovnání. Společná kontrola kanonické cesty chrání validate i skutečný export kódu/dat, včetně ./ aliasů a case. Sdílený engine používá rekurzivní JSON equality pro enum/FK a FK hodnoty sbírá jen z existujících cílových klíčů.

Vztah k T046 revizi 2, AC01/AC04/AC06/AC07. Cílená sada tohoto inkrementu
má 35 testů; finální integrovaná stdlib sada má 209 případů, 5 explicitních
skips. Přesné nové výsledky CI a nové base/head jsou v PR; původní SHA ani
staré CI výsledky nejsou vydávány za schválení oprav. Python compile a diff
whitespace check jsou součástí ověření. Lokální pytest se nepodařilo nainstalovat
z dostupného indexu; úplnou pytest/worker matici ověřuje skutečné GitHub CI.

CI dodatečně odhalilo zastaralé generované snapshoty v dílčích PR. Každý
inkrement nyní zvlášť obnovuje semantic metadata a GRAPH.md/GRAPH.mmd příkazy
semantic update/apply/validate a scan/check. Neoslabuje se CI ani validátor;
chybný snapshot se nahrazuje výstupem nad přesným zdrojem daného inkrementu.


## Integrace aktuálního main (2026-11-05)

Zachovává main `9eec41a403b4e6601fe3addac168bf39d37f31b6`, jeho nové capabilities, pravidla T045 revize 2 a sémantickou historii. Zdrojové změny T046 sloučeny bez konfliktů; společné dokumenty zachovávají obě rozšíření. Výsledky kontrol této nové revize následují po jejich skutečném provedení.


Aktualizovaný integrační baseline: `5ffe09952930a5a3e7a5d7b88a08560b7775ee9d` (zahrnuje remote contract mapping). Vlastní dostupná Python sada tohoto inkrementu: 43 passed, 1 warning, 21 subtests passed in 2.19s. Žádné nové worker/toolchain tvrzení. Semantic/grafy se znovu obnovují pro tento zdrojový snapshot.


## Integrace 2026-11-06 přes GitHub plugin

Baseline `250e7c16250a97b9f8df5256b9894c8119dc64d9`. Zachovává nové main capabilities včetně architecture CLI; vlastní cílené pytest ověření tohoto inkrementu: 77 passed, 1 warning, 21 subtests passed in 8.06s. Semantic a grafy se obnovují pro tento snapshot. Historické výsledky výše nejsou vydávány za nová head review.
