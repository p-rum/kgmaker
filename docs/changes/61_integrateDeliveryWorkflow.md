# T046-S06 — CLI, agenti a předání delivery workflow

## Problém a skutečná změna

Uživatel požaduje projektové šablony, generování testů/dat pro existující
funkcionalitu a dohledatelný řetězec požadavek–analýza–task–změna–test s osobami.
Propojuje template/testgen/trace CLI, init defaults, omezený role context, agent templates a profily. Přidává kompletní české schema/příklady/limity, stavovou matici a acceptance inventář. Udržuje původní sémantickou historii a obnovuje generované grafy příkazem.

Zadání: [T046](../tasks/46_addTemplatesTestsAndTraceability.md), Revision 1.
Krok: T046-S06; požadavky T046-R01–R05; acceptance T046-AC01–AC08.
Baseline balíku: `33dc239a6d2eca2f42364a7b314aeb377e4b441a`.
Závislé PR výslovně používají předchozí větev balíku jako base; po merge se
retargetují a znovu ověří integrace. Žádný z těchto PR se automaticky nemerguje.

## Kompatibilita a příklad

V1 task se čte bez změny identity, implementace/review doplní v2 content bindings.
Starší klient musí být aktualizován před čtením v2. Šablony jsou projektové;
workflow journal a testgen state jsou lokální. LLM pracuje v hostiteli bez API klíče.
Příklad celého postupu a přesné JSON kontrakty: [delivery workflow](../delivery-workflow.md).

## Ověření

- PASS: finální stdlib unittest sada: 198 testů, OK, 5 explicitních skips; 23 cílených delivery/templates/data/provenance případů.
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

Úplné CAS předání CLI. sync-analysis, sync-testgen a capture-change předávají expected_revision do atomické transakce. Read-only příkazy ji nepřijímají. Integrovaný balík přenáší všech šest oprav a jejich regresní důkazy.

Vztah k T046 revizi 2, AC01/AC04/AC06/AC07. Cílená sada tohoto inkrementu
má 44 testů; finální integrovaná stdlib sada má 209 případů, 5 explicitních
skips. Přesné nové výsledky CI a nové base/head jsou v PR; původní SHA ani
staré CI výsledky nejsou vydávány za schválení oprav. Python compile a diff
whitespace check jsou součástí ověření. Lokální pytest se nepodařilo nainstalovat
z dostupného indexu; úplnou pytest/worker matici ověřuje skutečné GitHub CI.

CI dodatečně odhalilo zastaralé generované snapshoty v dílčích PR. Každý
inkrement nyní zvlášť obnovuje semantic metadata a GRAPH.md/GRAPH.mmd příkazy
semantic update/apply/validate a scan/check. Neoslabuje se CI ani validátor;
chybný snapshot se nahrazuje výstupem nad přesným zdrojem daného inkrementu.


## Integrace main a nové ověření (2026-11-05)

Baseline `9eec41a403b4e6601fe3addac168bf39d37f31b6`; T046 opravy byly integrovány bez zdrojových konfliktů. Nové main funkce (včetně Thymeleaf v2, data realms a compiler capability) zůstávají zachované; tři souběžná rozšíření dokumentace byla spojena. Sémantická historie obsahuje všech 239 main epizod a 3 původní T046 epizody.

Skutečné lokální ověření nad touto integrací: 52 cílených pytest testů PASS (38 subtests); celá dostupná pytest sada 1152 PASS, 1045 SKIP, 60 subtests PASS (42,36 s), bez selhání. Skips nejsou PASS a tento běh nedokládá compiler/build/Windows toolchain acceptance. Změna T046 upravuje offline Python kontrakty; žádný worker ani nová main capability nebyly přepsány. Nezávislé review aktuálních base/head a GitHub publikace jsou samostatné následující kroky, nikoli tímto dokumentem potvrzený výsledek. GH CI se podle T045 revize 2 uvádí odděleně.


Finální integrační baseline 2026-11-05: `5ffe09952930a5a3e7a5d7b88a08560b7775ee9d`, včetně nového remote contract mapping. Skutečný nový plný dostupný pytest běh: **1231 PASS /1055 SKIP**, 60 subtests PASS, bez selhání (42,98 s). Cílená sada T046/context/feature/Thymeleaf/remote mapping: **179 PASS /10 SKIP**, 51 subtests PASS (5,23 s). Toolchain SKIP nejsou PASS; worker/package data zůstávají identická s tímto main. Historické výsledky nad9eec zůstávají oddělenou evidencí. Nezávislé review a publikace se ověřují nad novými přesnými SHA.


T046 integrace 2026-11-06 nad `250e7c16250a97b9f8df5256b9894c8119dc64d9`: plná dostupná pytest sada **1577 PASS /1056 SKIP**, 60 subtests PASS, bez selhání (60,33 s). Cílená sada včetně architecture CLI: **229 PASS /10 SKIP**, 51 subtests PASS (16,01 s). Oba CLI dispatchery zůstávají aktivní. Skips nedokládají nepřipravené compiler/build/Windows toolchainy. Předčasný běh před dokončením snapshotu byl přerušen a nezapočítává se; uvedený výsledek pochází z následného dokončeného běhu. GitHub publikace/review/merge se ověřují odděleně.
