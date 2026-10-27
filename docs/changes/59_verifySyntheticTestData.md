# T046-S04 — Ověření syntetických dat

## Problém a skutečná změna

Uživatel požaduje projektové šablony, generování testů/dat pro existující
funkcionalitu a dohledatelný řetězec požadavek–analýza–task–změna–test s osobami.
Doplňuje samostatnou acceptance podporovaných constraints, nullable/boolean/enum/required a přiznaného unsupported pattern. Foreign keys, negativní datasety a JSON/CSV export sdílejí kandidátový engine zavedený v S03.

Zadání: [T046](../tasks/46_addTemplatesTestsAndTraceability.md), Revision 1.
Krok: T046-S04; požadavky T046-R01–R05; acceptance T046-AC04.
Baseline balíku: `33dc239a6d2eca2f42364a7b314aeb377e4b441a`.
Závislé PR výslovně používají předchozí větev balíku jako base; po merge se
retargetují a znovu ověří integrace. Žádný z těchto PR se automaticky nemerguje.

## Kompatibilita a příklad

V1 task se čte bez změny identity, implementace/review doplní v2 content bindings.
Starší klient musí být aktualizován před čtením v2. Šablony jsou projektové;
workflow journal a testgen state jsou lokální. LLM pracuje v hostiteli bez API klíče.
Příklad celého postupu a přesné JSON kontrakty: [delivery workflow](../delivery-workflow.md).

## Ověření

- PASS: test_synthetic_data.py (3 případy), datové a exportní scénáře test_delivery.py.
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

Regrese datových mezí. Acceptance explicitně pokrývá false versus 0, vnořené hodnoty, numerickou ekvivalenci 1/1.0, nullable enum a FK missing versus explicitní null. Oprava sdíleného enginu je v dependency S03.

Vztah k T046 revizi 2, AC01/AC04/AC06/AC07. Cílená sada tohoto inkrementu
má 39 testů; finální integrovaná stdlib sada má 209 případů, 5 explicitních
skips. Přesné nové výsledky CI a nové base/head jsou v PR; původní SHA ani
staré CI výsledky nejsou vydávány za schválení oprav. Python compile a diff
whitespace check jsou součástí ověření. Lokální pytest se nepodařilo nainstalovat
z dostupného indexu; úplnou pytest/worker matici ověřuje skutečné GitHub CI.

CI dodatečně odhalilo zastaralé generované snapshoty v dílčích PR. Každý
inkrement nyní zvlášť obnovuje semantic metadata a GRAPH.md/GRAPH.mmd příkazy
semantic update/apply/validate a scan/check. Neoslabuje se CI ani validátor;
chybný snapshot se nahrazuje výstupem nad přesným zdrojem daného inkrementu.
