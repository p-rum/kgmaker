# Čtení normalizovaného výběru kontextu v review procesu

Tento předslučovací záznam z 2026-11-21 zachovává výchozí reprodukce, přenos
a jejich ověření. [Záznam merge a výsledků úplné sady](152_recordNormalizedProcessReviewMerge.md).

Výchozí reprodukce používá `main` `17e9e7368e6cc2d6550983c3039eb39debd65424`
s tree `dfb0a247ec329196190a3db182b5d1e8c549b3db`. Aktuální kandidát vychází
z `main` `fad4fc63c76f0f9ef5a1a292e279d1269bd84540` s tree
`999b5ef61989bf91ce3df58e4d3bcc84c074eb31`. Zdrojové a testové změny odpovídají
posouzenému kandidátu `2801ddc0a5ce03e86d99e0a9a9a79e76f04379b9`. Integrace
zachovala sloučený T021. Tento výchozí kandidát navazuje na sloučené
[T030](../tasks/T-030_prepare-process-label-packet.md) a
[T032](../tasks/T-032_persist-process-review.md). Přenos tehdy otevřeného [PR #132](https://github.com/p-rum/kgmaker/pull/132) je zaznamenán níže.

## T032-S01 a T032-S03 · AC01, AC03, AC05

T030 u výběru kontextu převede pokrytí a diagnostiku na hashe. T032 při ukládání
používal stejnou validaci jako před převodem. Příprava nad skutečným Javac/JDK21
grafem prošla, ale zápis rozhodnutí po složení T024/T025/T027–T029 skončil
`UNSUPPORTED_SELECTION_SHAPE`. První pokus vytvořil koordinační soubor. Tento
případ zastavil pozitivní průchod [T034](../tasks/T-034_add-process-cli.md).

`src/kgmaker/process_semantics.py` má pro čtení normalizovaných výběrů vlastní
přesný vstupní kontrakt. Zachová původní čitelná ID, scope a hashované vazby.
Při přípravě nového packetu povoluje T030 původní raw zachycené hodnoty.
`src/kgmaker/process_store.py` ověřuje normalizovaný výběr a před aktivací
schválených popisů porovnává pro shodný packet také uloženou identitu a hash
vstupů s aktuálním přepočtem. Změněný packet dál vyžaduje revalidaci a původní
historie zůstává čitelná.

Přímé opakování nad stejným uloženým Javac grafem vrátilo `COMMITTED` pro revizi 1
a `APPROVED` při čtení. Integrační běh nad `fad4fc6` znovu vytvořil graf se
skutečným Javac/JDK21 a kontextem `CONTENT_VERIFIED`. Uložení i čtení schválené
revize daly stejný výsledek. Formáty packetu a review store se nemění. Migrace není
potřeba.

## T032-S02 · AC02, AC04

`src/kgmaker/process_store.py` ověřuje připravený záznam před otevřením zámku.
Očekávaný neprázdný head proti chybějícímu úložišti vrací `CAS_CONFLICT` před
vytvořením koordinačních cest. Platný zápis a opakování nad existujícím stavem
zachovávají POSIX zámek, kontrolu pod zámkem a stávající CAS.

## T032-S04 · AC01–05

`tests/test_t032_persist_process_review.py` doložil šest nových neúspěšných případů
na výchozím zdroji. Ověření po opravě má **272 PASS, 0 SKIP**:

```bash
PYTHONPATH=src python -m pytest -p no:cacheprovider --assert=plain -q --tb=short \
  tests/test_t0{23_define_business_process_model,30_prepare_process_label_packet,31_validate_process_annotations,32_persist_process_review,33_catalog_business_processes}.py
```

`test_public_persists_normalized_capture_and_rechecks_raw_binding` ověřuje uložené
hashe, idempotenci a změnu vstupů. `test_review_store_rejects_modified_normalized_context_bindings`
zkouší čtyři varianty včetně platného tvaru se změněným hashem a přepočtenou
historií. `test_invalid_candidate_and_stale_initial_head_leave_no_coordination_state`
ověřuje nulovou mutaci adresáře. `test_forged_hash_binding_is_not_a_raw_context_capture`
ověřuje odmítnutí odvozeného hashe jako náhrady za přímý capture v T030. Stejná
sada ověřuje existující CAS dvou procesů a dvou vláken.

První kombinovaný běh měl 270 PASS a selhal na importu modulu během testu T031,
který v daném místě blokuje `open`. Samostatný běh tohoto testu na výchozím
SHA selhal stejně. Výše uvedený běh s `--assert=plain` prošel bez přeskočení.
Samostatný širší běh s defaultním pytest assertion rewrite a T026 měl 273 PASS,
94 SKIP bez aktivovaných compiler fixtures. Z tohoto širšího běhu se výsledky
pro přeskočené případy neodvozují.

## T032-S05 · AC06

[README](../../README.md#explicit-local-process-review-t032-merged-pr78),
[T030 packet](../process-label-packets.md), [T032 store](../process-review-store.md),
[acceptance](../acceptance-inventory.md) a [stav](../production-analysis-progress.md)
popisují přesný kontrakt. Registr a instalované instrukce mají stejnou identitu,
závislosti a workflow. CLI příklady se tímto krokem nemění.

Při opakování standardního příkladu T032 použijte packet z aktuálního ProcessView
a původní `operation_id` s původním `expected_head`. Vrácený receipt zachová stejnou
revizi i head. V této předslučovací fázi ještě čekaly T034, Windows podpora,
plná sada, GitHub Actions, nezávislé review této změny a merge gate.

## T032-S05 · AC06 — přenos #132 na main `c2885a6` dne 2026-11-21

Místní přenos spojuje původní PR head
`2a5921a5f4fc95e8343a510f5604e4c7988a00db` a cílový
`c2885a6f8daf0281967e3bc5386a69f1647718e0`. Zachovává obsah
`src/kgmaker/process_semantics.py`, `src/kgmaker/process_store.py` a
`tests/test_t032_persist_process_review.py` beze změny proti původnímu PR.
Dokumentační sloučení zachovává i doklady T021, W06 a T052 z cílové větve.
[Inventář acceptance](../acceptance-inventory.md) a
[stavová matice](../production-analysis-progress.md) odkazují na #132 a nové
zaměřené ověření. [README](../../README.md#explicit-local-process-review-t032-merged-pr78),
[T030 packet](../process-label-packets.md) a [T032 store](../process-review-store.md)
zachovávají popis opravy. Kontrakt API, formát úložiště, CLI a registr zadání nemají
dopad z přenosu.

- PASS — Příkaz s `--assert=plain` z T032-S04 v Pythonu 3.12.14 a pytest 8.3.4
  vykázal 272 PASS / 0 SKIP za 4,11 s. JUnit byl zapsán mimo checkout.
- PASS — Místní doplňkový pytest scénář spustil stejný uložený workspace fixture
  z `tests/test_local_operation_proofs.py` s reálným Javac 21.0.6 a JVM workerem K1.
  Spouštěcí výběr `-k k1` vykázal 1 PASS a 1 DESELECTED (K2), 7,08 s. Vstupní
  závislosti odpovídají kontrolním součtům `fixtures/process-triggers/dependencies.lock.json`.
  Výsledný uložený kontext měl `CONTENT_VERIFIED` a nesl normalizované vazby.
  Zápis vrátil `COMMITTED` pro revizi 1, čtení vrátilo `APPROVED`, opakování
  zachovalo stejné rozhodnutí a soubory testovaného repository zůstaly shodné.
- RED — Stejné regresní případy v `tests/test_t032_persist_process_review.py`
  proti archivovanému `src` z `c2885a6` vykázaly 6 FAIL / 1 PASS, 36 DESELECTED.
  Pět případů skončilo `UNSUPPORTED_SELECTION_SHAPE` a jeden vytvořil
  koordinační stav po konfliktu prvního headu. Použit byl samostatný
  `PYTHONPATH`, `pytest -c /dev/null -p no:cacheprovider --assert=plain -q --tb=short`
  a výběr `-k 'public_persists_normalized_capture or review_store_rejects_modified_normalized_context_bindings or invalid_candidate_and_stale_initial_head or forged_hash_binding_is_not_a_raw_context_capture'`.
- PASS — `semantic update --base c2885a6`, `semantic apply`, `semantic validate`,
  `memory capture --base c2885a6`, `scan`, `status`, `check`,
  `git diff --check c2885a6` a `git diff --cached --check`. Sémantika zachovala
  všech 336 epizod z obou výchozích revizí a přidala doklad tohoto přenosu.
- NOT_RUN v této fázi — úplná sada, nové nezávislé review T045, GitHub Actions
  a Windows. Doplněk sloužil jako lokální podklad pro review před integrací.
  T034 zůstává samostatná dodávka.
