# T046-S01 — Verzované reference a kompatibilní workflow

## Problém a skutečná změna

Uživatel požaduje projektové šablony, generování testů/dat pro existující
funkcionalitu a dohledatelný řetězec požadavek–analýza–task–změna–test s osobami.
Nový provenance journal, append-only lokální události, v1/v2 bindings a CAS zápisy. Runtime ID ani historické artefakty se nepřejmenovávají.

Zadání: [T046](../tasks/46_addTemplatesTestsAndTraceability.md), Revision 1.
Krok: T046-S01; požadavky T046-R01–R05; acceptance T046-AC05, AC07.
Baseline balíku: `33dc239a6d2eca2f42364a7b314aeb377e4b441a`.
Závislé PR výslovně používají předchozí větev balíku jako base; po merge se
retargetují a znovu ověří integrace. Žádný z těchto PR se automaticky nemerguje.

## Kompatibilita a příklad

V1 task se čte bez změny identity, implementace/review doplní v2 content bindings.
Starší klient musí být aktualizován před čtením v2. Šablony jsou projektové;
workflow journal a testgen state jsou lokální. LLM pracuje v hostiteli bez API klíče.
Příklad celého postupu a přesné JSON kontrakty: [delivery workflow](../delivery-workflow.md).

## Ověření

- PASS: test_provenance.py (3 případy), test_workflow.py (10 případů).
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

CAS vytvoření a neměnná historie. Create-or-load probíhá pod společným lockem; opožděný creator nevrátí analyze na intake. Přímé změny tasku vyžadují expected_revision, artefakty jsou neměnný prefix a bindings historických artefaktů se nepřepisují.

Vztah k T046 revizi 2, AC01/AC04/AC06/AC07. Cílená sada tohoto inkrementu
má 16 testů; finální integrovaná stdlib sada má 209 případů, 5 explicitních
skips. Přesné nové výsledky CI a nové base/head jsou v PR; původní SHA ani
staré CI výsledky nejsou vydávány za schválení oprav. Python compile a diff
whitespace check jsou součástí ověření. Lokální pytest se nepodařilo nainstalovat
z dostupného indexu; úplnou pytest/worker matici ověřuje skutečné GitHub CI.

Druhá read-only kontrola oprav navíc ověřila, že nové implement/review bindings
se pod lockem odvozují od skutečného HEAD a source inventory. Dodaný rozdílný
binding se odmítne bez mutace; chybějící binding se doplní při v1→v2 migraci,
aniž by se změnila task/artifact ID.

CI dodatečně odhalilo zastaralé generované snapshoty v dílčích PR. Každý
inkrement nyní zvlášť obnovuje semantic metadata a GRAPH.md/GRAPH.mmd příkazy
semantic update/apply/validate a scan/check. Neoslabuje se CI ani validátor;
chybný snapshot se nahrazuje výstupem nad přesným zdrojem daného inkrementu.


## Integrace aktuálního main (2026-11-05)

Zachovává main `9eec41a403b4e6601fe3addac168bf39d37f31b6`, jeho nové capabilities, pravidla T045 revize 2 a sémantickou historii. Zdrojové změny T046 sloučeny bez konfliktů; společné dokumenty zachovávají obě rozšíření. Výsledky kontrol této nové revize následují po jejich skutečném provedení.


Aktualizovaný integrační baseline: `5ffe09952930a5a3e7a5d7b88a08560b7775ee9d` (zahrnuje remote contract mapping). Vlastní dostupná Python sada tohoto inkrementu: 24 passed, 1 warning, 5 subtests passed in 0.59s. Žádné nové worker/toolchain tvrzení. Semantic/grafy se znovu obnovují pro tento zdrojový snapshot.


## Integrace 2026-11-06 přes GitHub plugin

Baseline `250e7c16250a97b9f8df5256b9894c8119dc64d9`. Zachovává nové main capabilities včetně architecture CLI; vlastní cílené pytest ověření tohoto inkrementu: 58 passed, 1 warning, 5 subtests passed in 6.79s. Semantic a grafy se obnovují pro tento snapshot. Historické výsledky výše nejsou vydávány za nová head review.


## Integrace f115 a oprava kumulativní dokumentace — 2026-11-06

- Task/Step/Acceptance: T046 / T046-S01 / T046-AC05/AC07/AC08.
- Výchozí main: `f115aa4a1c37683f3be9e4607111d51d9c1301c1`; předchozí publikovaný head tohoto kroku: `b424336d4719e8f3225ad840713316d828f20f25`.
- Problém: main nově vyžaduje evidenci každého kroku; pozdější části stacku vracely staré verze dodatků předchozích change notes.
- Skutečná změna: nové `AGENTS.md`, `src/kgmaker/agent_rules.py`, governance části `src/kgmaker/agents.py` a spravované `.github`/`.junie` instrukce jsou převzaty z main. Tento inkrement nemění delivery instrukce přidávané v S06. Žádný T046 runtime algoritmus, JSON kontrakt nebo compiler/build adaptér se nemění.
- Historie: note56 až note56 obsahují kumulativní plné dodatky předchozích kroků včetně datumů, SHA a skutečných výsledků. Kontrola zachování všech 21 původních verzí v šesti stage snapshots prošla před zápisem; staré výsledky nejsou přeznačeny na nové PASS.
- Dotčené evidenční soubory: kumulativní `docs/changes/56_addDeliveryReferences.md`, `README.md`, `docs/production-analysis-progress.md`, `docs/acceptance-inventory.md`, registr a v S06 revize zadání T046. `.kgmaker/semantic.json` a GRAPH se obnovují podporovanými příkazy; všechny publikované epizody zůstávají zachovány.
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

`python -m pytest -q tests/test_provenance.py tests/test_workflow.py tests/test_templates.py tests/test_t019_add_architecture_json_cli.py tests/test_init.py tests/test_scanner.py` → **80 passed, 1 warning, 5 subtests passed in 6.82s**. Použito `PYTHONPATH=/workspace/test-deps:src`; prostředí s pytest9.2/jsonschema4.26, vlastní projekt bez runtime dependencies. `semantic update --base HEAD`, scoped apply, validate, scan, check a `git diff --check` jsou samostatné požadované kontroly; přesné nové výsledky se vážou k níže ověřovanému tree v PR review. Čerstvý init a ochrana uživatelských změn jsou součástí skutečně provedených test_init/test_scanner, nikoli textového testu nových pravidel.

## T048-S02 / T046-S01 — integrace main 766c08f, 2026-11-07

Baseline main `766c08f`, head před integrací `e780e32`. T048-AC02, T046-AC05/AC07/AC08. Merge zachovává dokumentační audit PR89 i knihovní provenance/workflow. Konflikt README řešen zachováním reference kontraktu a opraveného merged statusu remote mapping; sémantické koncepty/vazby a epizody obou větví zachovány bez duplicit. Runtime algoritmy ani v1/v2 ID se nemění.

PASS: `/workspace/venv/bin/python -m pytest -q tests/test_provenance.py tests/test_workflow.py tests/test_templates.py tests/test_t019_add_architecture_json_cli.py tests/test_init.py tests/test_scanner.py`: **80 passed, 5 subtests passed**. Python 3.12, pytest 9.2.0. Graph/semantic/diff kontrola se zaznamená po dokončení. GH CI, nové nezávislé review a skutečný JVM/K2/TypeScript/Windows toolchain NOT_RUN.

README upraven při řešení konfliktu; capability/API/CLI příklady v delivery-workflow beze změny, protože knihovní kontrakt a argumenty jsou stejné. Stavový i acceptance inventář doplněn aktuálním výsledkem; registr/zadání beze změny identity, revize a dependencies. Delivery PR_OPEN, ověření cíleného Python kontraktu VERIFIED_IN_SCOPE. Zbývá nezávislé review a následná integrace etap S02–S06; žádný merge do main.

Dokončené integrační kontroly: semantic apply/validate, scan/check a oba `git diff --check` (working tree i index) PASS. Potvrzeno 253 zachovaných historických epizod z obou větví, 40 konceptů /122 sémantických vazeb; aktualizovány pouze zdrojové snapshots a generované pohledy.

### Oprava evidence inventáře T048-S02

Opravena hromadně přenesená věta o 80 testech v řádcích S02–S06. Výsledek patří pouze S01; pozdější etapy v této větvi zůstávají NOT_RUN. Runtime a jeho ověřený tree beze změny; jde výhradně o opravu stavového dokumentu, bez dopadu na README/API/CLI. Kontrola šesti řádků proti skutečným výsledkům, semantic/scan/check a diff check se provedou před commitem. Původní SHA a historické běhy zachovány.

## Oprava nezávislého review: neměnná auditní historie — 2026-11-07

- Task/Step/Acceptance: T046 / T046-S01 / T046-AC07; integrační baseline
  `766c08fb47458220fb037c2ee278607247b721e1`, reviewovaný head před opravou
  `cd8dcc2c44037b105176b48b5c883f9259dd92c5`.
- Nález: veřejná `provenance.transaction()` po načtení ověřila journal, ale před
  zápisem neověřila změněnou in-memory hodnotu ani neměnný prefix událostí. Přímé
  odstranění poslední `revoked` události proto vytvořilo nový platný envelope a
  obnovilo staré schválení, v rozporu s append-only kontraktem.
- Skutečná změna: `src/kgmaker/provenance.py` sdílí validaci načtených a nově
  zapisovaných dat a před zápisem odmítne odstranění, přepis či přeskládání
  existujícího prefixu `events`. Odmítnutí proběhne před atomickým zápisem a lock
  se uvolní původní cestou. `tests/test_provenance.py` ověřuje odstranění i přepis,
  nulovou mutaci souborů a zachování odvolaného schválení.
- Kompatibilita: platné append-only zápisy, CAS, runtime ID, v1/v2 bindings,
  LOCAL_DECLARED identita i default-off policy zůstávají stejné. Dříve přijímaná
  destruktivní změna historie je nyní odmítnuta `AnalysisError`.
- PASS: `/workspace/venv/bin/python -m pytest -q tests/test_provenance.py
  tests/test_workflow.py tests/test_templates.py
  tests/test_t019_add_architecture_json_cli.py tests/test_init.py
  tests/test_scanner.py` — **81 passed, 7 subtests passed in 3.88 s**.
- PASS: semantic apply/validate, memory capture
  `episode:522de97549f69a3a5d8ebca9721dae9f5a29e9cb3eaf28100b0f19d481e52879`,
  scan/check a `git diff --check`; generovaný graf obsahuje 527 souborů, 5908
  uzlů a 41812 vztahů. První memory capture před vytvořením lokálního machine
  graphu skončil očekávaně bez zápisu; po příkazovém scan následoval úspěšný
  capture a finální scan.
- NOT_RUN: nový GitHub CI, nové exact-pair review opraveného headu a širší
  compiler/build/Windows toolchain.

Dokumentační dopad: README a `docs/delivery-workflow.md` již slibují append-only
historii, takže jejich veřejný kontrakt se nemění. Stavový a acceptance inventář
odkazují na tuto opravu a nový cílený výsledek. Registr/zadání, CLI syntaxe,
příklady a init templates jsou bez dopadu. PR zůstává PR_OPEN do nového review
aktuální base/head dvojice; žádný starý review verdikt se nepřenáší.
