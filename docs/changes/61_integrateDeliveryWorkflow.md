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


## Integrace f115 a oprava kumulativní dokumentace — 2026-11-06

- Task/Step/Acceptance: T046 / T046-S06 / T046-AC01–AC08.
- Výchozí main: `f115aa4a1c37683f3be9e4607111d51d9c1301c1`; předchozí publikovaný head tohoto kroku: `92914facd3f79c7ee19abaf4f205f28cbc15ac82`.
- Problém: main nově vyžaduje evidenci každého kroku; pozdější části stacku vracely staré verze dodatků předchozích change notes.
- Skutečná změna: nové `AGENTS.md`, `src/kgmaker/agent_rules.py`, governance části `src/kgmaker/agents.py` a spravované `.github`/`.junie` instrukce jsou sloučeny s existujícími T046 delivery instrukcemi v Python templates i spravovaných kopiích. Žádný T046 runtime algoritmus, JSON kontrakt nebo compiler/build adaptér se nemění.
- Historie: note56 až note61 obsahují kumulativní plné dodatky předchozích kroků včetně datumů, SHA a skutečných výsledků. Kontrola zachování všech 21 původních verzí v šesti stage snapshots prošla před zápisem; staré výsledky nejsou přeznačeny na nové PASS.
- Dotčené evidenční soubory: kumulativní `docs/changes/56_addDeliveryReferences.md`, `docs/changes/57_addArtifactTemplates.md`, `docs/changes/58_addExistingFunctionTests.md`, `docs/changes/59_verifySyntheticTestData.md`, `docs/changes/60_enforceOptionalLocalApprovals.md`, `docs/changes/61_integrateDeliveryWorkflow.md`, `README.md`, `docs/production-analysis-progress.md`, `docs/acceptance-inventory.md`, registr a v S06 revize zadání T046. `.kgmaker/semantic.json` a GRAPH se obnovují podporovanými příkazy; všechny publikované epizody zůstávají zachovány.
- Kompatibilita: v1/v2 workflow ID, append-only journal, template/testgen/trace příkazy, default-off policy i LOCAL_DECLARED identita zůstávají stejné. Standardní init dále chrání uživatelské úpravy; žádný `--force` není použit.

### Dopad dokumentačních ploch

| Plocha | Aktualizace nebo konkrétní bez dopadu |
|---|---|
| README | Zachována nová main governance i existující T046 návod; příkazy a limity offline režimu se nemění. |
| Capability/API: `docs/delivery-workflow.md` | Bez dopadu na datová schémata, renderer, testgen a approval kontrakt; změna upravuje instrukce a historii integrace, nikoli tyto API. |
| CLI příklady | Bez dopadu na syntaxi parametrů; původní template/testgen/trace a architecture dispatch byly ověřeny subprocess testy. |
| Stavová matice | `docs/production-analysis-progress.md` obsahuje odkaz na tento konkrétní krok a odděluje předání od výsledku ověření. |
| Acceptance | `docs/acceptance-inventory.md` odkazuje na tento záznam; acceptance rozsah T046 se nemění. |
| Registr/zadání | Identita a závislosti beze změny; S06 aktualizuje revizi T046 v existujícím souboru a řádku registru. |

### Skutečné ověření a omezení

Nad novou integrací S06: plný dostupný pytest **1577 PASS /1056 SKIP**, 60 subtests PASS (57,49 s); cíleně včetně init/scanner **251 PASS /10 SKIP**, 51 subtests PASS (13,36 s). Nejde o rerun celé compiler/build/Windows matice; tyto SKIP nejsou PASS. Vlastní cílený výsledek tohoto inkrementu a semantic/graf/diff kontroly jsou doplněny níže po dokončení. Nové testy kopírující text pravidel nebyly přidány. GH CI se zaznamenává odděleně dle T045 revize 2.

Stav při předání této revize: **PR_OPEN**; ověření Python kontraktu **VERIFIED_IN_SCOPE**, nepřipravených toolchainů **NOT_RUN/SKIP**. Nové exact-pair review, případný merge a další posun main jsou samostatné skutečné události v PR; tento záznam je nepředjímá. Zbývá dokončit toto review a standardní merge bez bypassu.


### Dokončené kontroly této integrační revize

`python -m pytest -q tests/test_provenance.py tests/test_delivery.py tests/test_synthetic_data.py tests/test_artifact_templates.py tests/test_workflow.py tests/test_templates.py tests/test_context_roles.py tests/test_feature.py tests/test_feature_fixture.py tests/test_workspace.py tests/test_cross_service_contract_mapping.py tests/test_t019_add_architecture_json_cli.py tests/test_init.py tests/test_scanner.py` → **251 passed, 10 skipped, 1 warning, 51 subtests passed in 13.36s**. Použito `PYTHONPATH=/workspace/test-deps:src`; prostředí s pytest9.2/jsonschema4.26, vlastní projekt bez runtime dependencies. `semantic update --base HEAD`, scoped apply, validate, scan, check a `git diff --check` jsou samostatné požadované kontroly; přesné nové výsledky se vážou k níže ověřovanému tree v PR review. Čerstvý init a ochrana uživatelských změn jsou součástí skutečně provedených test_init/test_scanner, nikoli textového testu nových pravidel.
