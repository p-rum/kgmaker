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


## Integrace f115 a oprava kumulativní dokumentace — 2026-11-06

- Task/Step/Acceptance: T046 / T046-S03 / T046-AC02/AC03.
- Výchozí main: `f115aa4a1c37683f3be9e4607111d51d9c1301c1`; předchozí publikovaný head tohoto kroku: `71e48f88b566a66b02e95c9b2a6bea527fd1483f`.
- Problém: main nově vyžaduje evidenci každého kroku; pozdější části stacku vracely staré verze dodatků předchozích change notes.
- Skutečná změna: nové `AGENTS.md`, `src/kgmaker/agent_rules.py`, governance části `src/kgmaker/agents.py` a spravované `.github`/`.junie` instrukce jsou převzaty z main. Tento inkrement nemění delivery instrukce přidávané v S06. Žádný T046 runtime algoritmus, JSON kontrakt nebo compiler/build adaptér se nemění.
- Historie: note56 až note58 obsahují kumulativní plné dodatky předchozích kroků včetně datumů, SHA a skutečných výsledků. Kontrola zachování všech 21 původních verzí v šesti stage snapshots prošla před zápisem; staré výsledky nejsou přeznačeny na nové PASS.
- Dotčené evidenční soubory: kumulativní `docs/changes/56_addDeliveryReferences.md`, `docs/changes/57_addArtifactTemplates.md`, `docs/changes/58_addExistingFunctionTests.md`, `README.md`, `docs/production-analysis-progress.md`, `docs/acceptance-inventory.md`, registr a v S06 revize zadání T046. `.kgmaker/semantic.json` a GRAPH se obnovují podporovanými příkazy; všechny publikované epizody zůstávají zachovány.
- Kompatibilita: v1/v2 workflow ID, append-only journal, template/testgen/trace příkazy, default-off policy i LOCAL_DECLARED identita zůstávají stejné. Standardní init dále chrání uživatelské úpravy; žádný `--force` není použit.

### Dopad dokumentačních ploch

| Plocha | Aktualizace nebo konkrétní bez dopadu |
|---|---|
| README | Zachována nová main governance i existující T046 návod; příkazy a limity offline režimu se nemění. |
| Capability/API: `docs/delivery-workflow.md` | Bez dopadu na datová schémata, renderer, testgen a approval kontrakt; změna upravuje instrukce a historii integrace, nikoli tyto API. |
| CLI příklady | Bez dopadu na CLI syntaxi tohoto knihovního inkrementu; ověřeny architecture CLI a init-preservation. Delivery CLI je kontraktem S06. |
| Stavová matice | `docs/production-analysis-progress.md` obsahuje odkaz na tento konkrétní krok a odděluje předání od výsledku ověření. |
| Acceptance | `docs/acceptance-inventory.md` odkazuje na tento záznam; acceptance rozsah T046 se nemění. |
| Registr/zadání | Identita a závislosti beze změny; S06 aktualizuje revizi T046 v existujícím souboru a řádku registru. |

### Skutečné ověření a omezení

Nad novou integrací S06: plný dostupný pytest **1577 PASS /1056 SKIP**, 60 subtests PASS (57,49 s); cíleně včetně init/scanner **251 PASS /10 SKIP**, 51 subtests PASS (13,36 s). Nejde o rerun celé compiler/build/Windows matice; tyto SKIP nejsou PASS. Vlastní cílený výsledek tohoto inkrementu a semantic/graf/diff kontroly jsou doplněny níže po dokončení. Nové testy kopírující text pravidel nebyly přidány. GH CI se zaznamenává odděleně dle T045 revize 2.

Stav při předání této revize: **PR_OPEN**; ověření Python kontraktu **VERIFIED_IN_SCOPE**, nepřipravených toolchainů **NOT_RUN/SKIP**. Nové exact-pair review, případný merge a další posun main jsou samostatné skutečné události v PR; tento záznam je nepředjímá. Zbývá dokončit toto review a standardní merge bez bypassu.


### Dokončené kontroly této integrační revize

`python -m pytest -q tests/test_provenance.py tests/test_artifact_templates.py tests/test_delivery.py tests/test_workflow.py tests/test_templates.py tests/test_t019_add_architecture_json_cli.py tests/test_init.py tests/test_scanner.py` → **99 passed, 1 warning, 21 subtests passed in 8.25s**. Použito `PYTHONPATH=/workspace/test-deps:src`; prostředí s pytest9.2/jsonschema4.26, vlastní projekt bez runtime dependencies. `semantic update --base HEAD`, scoped apply, validate, scan, check a `git diff --check` jsou samostatné požadované kontroly; přesné nové výsledky se vážou k níže ověřovanému tree v PR review. Čerstvý init a ochrana uživatelských změn jsou součástí skutečně provedených test_init/test_scanner, nikoli textového testu nových pravidel.

## T048-S02 / T046-S03 — integrace main 766c08f, 2026-11-07

T048-AC02; T046-AC01–AC08 v rozsahu tohoto inkrementu. Výchozí head `792cf3ec302dab4b6f2ead816ab1911fe4b36022`, integrovaný předchůdce `aad84009df0b27f70b0a3cc90061c4128794a149`. Merge zachovává audit PR89 a kumulativní záznamy všech předchozích etap. Konflikty README zachovávají vlastní popis kroku i aktuální merged status remote mapping; semantic metadata zachovávají sjednocené koncepty/vazby/epizody, grafy jsou regenerovány příkazem. Žádný runtime algoritmus, JSON kontrakt, runtime ID či výchozí policy se nemění.

PASS: `/workspace/venv/bin/python -m pytest -q tests/test_provenance.py tests/test_artifact_templates.py tests/test_delivery.py tests/test_workflow.py tests/test_templates.py tests/test_t019_add_architecture_json_cli.py tests/test_init.py tests/test_scanner.py` → **99 passed, 21 subtests passed**. Python 3.12, pytest 9.2.0. Semantic apply/validate, scan/check a diff check se ověřují před commitem; případné selhání blokuje předání. NOT_RUN: nové GH CI, nezávislé review a nepřipravené compiler/build/Windows toolchainy. Historické výsledky výše nejsou novým PASS.

README řeší současnou dokumentaci; `docs/delivery-workflow.md`, API/CLI příklady bez dopadu, protože se nemění implementace ani příkazy. Stavový a acceptance inventář aktualizují tento integrační výsledek; registr a zadání bez změny identity/revize/dependencies. Delivery PR_OPEN, cílený Python kontrakt VERIFIED_IN_SCOPE, širší acceptance NOT_RUN. Zbývá review aktuálního head/base, merge oprávněným workflow a navazující etapy podle T048. Žádný merge do main ani aktivace schvalovací policy.

### Oprava evidence inventáře T048-S02, S03

Řádky etap mají nyní každý svůj skutečný cílený výsledek; výsledky dalších etap v této větvi zůstávají NOT_RUN. Opravena nesprávně přenesená věta o 80 testech ze S01. Převzata odpovídající oprava předchůdce a jeho change note. Bez změny runtime, testů, README/API/CLI či acceptance; jde o přesné přiřazení evidence v existujícím stavovém inventáři. Ověření dokumentu, semantic apply/validate, scan/check a diff check se provádí před předáním; původní testové běhy zůstávají platné pouze pro nezměněný runtime tree.

## T048-S02 / T046-S03 — integrace sloučeného S02, 2026-11-11

Integrovaný předchůdce je head S02 `351a661641b8a8f619b389c20a7cf32641c23f5a`
(merge `8aae58c0ca280c13ce19ccb6a7c4e3cd46005f10`). S03 zachovává jeho opravy
kanonických exportních cest, transakční instalace, S01 journalu i aktuální README.
Vlastní testgen runtime se při integraci nezměnil. Cílená sada prošla jako
**106 passed, 37 subtests passed in 5.80s**; full jako **1625 passed, 1055 skipped,
59 subtests passed in 44.03s**. Semantic vrstva sjednocuje všechny epizody obou
větví; nové exact-pair review a GitHub CI jsou do provedení **NOT_RUN**.

### Opravy nezávislého review PR #43

Review baseline `15dc323447fee0399eca84930e8317499006d402` odhalil tři AC01/AC07
hrany. `prepare` nyní odmítá boolean a přijímá jen nezáporný integer CAS revize.
`export` validuje původní `data_dir` bez normalizace `rstrip`, takže koncové `/`
je nekanonické. Při pozdní chybě zápisu odstraňuje také všechny nově vytvořené
adresáře. Přímé regrese sledují celý strom a injektují selhání druhého výstupu.
Po opravě cíleně **106 passed + 37 subtests**, full **1625 passed /1055 skipped
+ 59 subtests**; nové exact-pair review je NOT_RUN do skutečného provedení.


## T046-S03/S04 — navazující oprava 2026-11-20

[Issue #91](https://github.com/p-rum/kgmaker/issues/91) je reprodukované na
sloučeném zdroji. [Change140](140_validateAdditionalDatasetFields.md) eviduje
rekurzivní validaci schématu dodatečných vlastností, původní RED a 103 cílených
PASS. Starší výsledky výše patří jejich původním revizím.
