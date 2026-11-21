# Doložený merge čtení normalizovaného kontextu procesu

## T032-S01 až T032-S05 / T032-AC01 až T032-AC06

Výchozí SHA dokumentačního kroku je
`4011825b15e4b65e1f57576a0986ca05b3cf810e`.
GitHub zaznamenal merge do `main` dne 2026-11-21 v 17:06:31 UTC. Vrátil
`merged=true`, základ `c2885a6f8daf0281967e3bc5386a69f1647718e0` a head
`4dc5da64b62edf31ceff0e340febba59ce913e95`. Oba commity jsou v tomto
pořadí skutečnými rodiči merge. Tree
`d8021d4f2eefe3b1576c75ed66e7e5f71d642fbd` je shodný s tree ověřeného
kandidáta. [PR #132](https://github.com/p-rum/kgmaker/pull/132),
[merge commit](https://github.com/p-rum/kgmaker/commit/4011825b15e4b65e1f57576a0986ca05b3cf810e)

- **T032-S01 a T032-S03 / AC01, AC03, AC05.** Uložená revize zachovává
  normalizované hashe pokrytí a diagnostiky. T032 znovu odvodí přesný
  packet a kontroluje vazby na aktuální explicitní snapshot. Historie
  zůstává čitelná po změně vstupů a technická provenance zůstává oddělená
  od rozhodnutí lokálního review. Doklad zachycuje schválení a idempotentní
  opakování nad uloženým kontextem Javac 21.0.6/K1.
- **T032-S02 / AC02, AC04.** Neplatný kandidát nebo konflikt prvního
  očekávaného headu je odmítnut před inicializací koordinace. Platný zápis
  stále používá POSIX zámek a CAS. Původní packet, formát historie a API
  zůstávají kompatibilní a nevyžadují migraci.
- **T032-S04 / AC01–AC05.** Úplná lokální sada zahrnuje všech 43 PASS
  z `tests/test_t032_persist_process_review.py`. Starší výsledky
  předslučovací reprodukce, 272 cílených PASS a uložený kontext Javac
  zůstávají dohledatelné s původními SHA. [Change147](147_replayNormalizedProcessContext.md)
- **T032-S05 / AC06.** Tento dokumentační krok srovnává stav dodání,
  ověření a odkazy s merge. Rozhraní, příklady volání, instalované instrukce,
  identita zadání a datové schema zůstávají beze změny. Technický kontext i
  hranice pro lokální review jsou uvedeny v příslušných uživatelských
  dokumentech. [README](../../README.md#explicit-local-process-review-t032-merged-pr78),
  [API T032](../process-review-store.md), [acceptance](../acceptance-inventory.md),
  [stavová matice](../production-analysis-progress.md)

### Důkazy pro sloučený kandidát

- **Úplná lokální sada.** 3698 PASS / 2 SKIP / 0 FAIL / 0 ERROR, exit 0,
  1901,34 s. Použit byl příkaz níže s JDK 21.0.6, Kotlin K1/K2, TypeScriptem,
  skutečným Mavenem 3.9.9, Gradle 8.13 a skutečným Markdown parserem.
  Proměnné `KGMAKER_REQUIRE_WORKERS`, `KGMAKER_REQUIRE_K2`,
  `KGMAKER_REQUIRE_EXPORTERS` a `KGMAKER_REQUIRE_MARKDOWN_PARSER` měly
  hodnotu `1`. Vstupní a výstupní manifest 838 souborů se shodují.
  `workers/build/exporters.json` byl v izolovaném testovacím checkoutu
  připraven pro skutečný exporter a je zahrnutý v obou manifestech.
  Ostatní sledované soubory odpovídaly revizi head.
- **Přeskočené kontroly.** `test_external_toolchain_two_real_jdks` vyžaduje
  JDK v očekávaném systémovém umístění.
  `test_actual_windows_smoke_uses_restricted_token_and_paths_with_spaces`
  vyžaduje skutečný neadministrátorský Windows. Oba případy jsou mimo
  ověřenou opravu POSIX review.
- **Obsahové hashe.** JUnit SHA-256
  `ba4f3a4600321f181f24170d21f67d37730fffa598944bc2ff0415c66449f8f1`.
  Log SHA-256 `8ee6c1486483cdb6e91ba1629122869a0b3568a32887489170c3532eb52e3769`.
  Oba manifesty SHA-256
  `b28164481e4d86f4d1b4cc722a537098582a41ddb7a9024930a081b8f5adb132`.
- **Review a integrace.** Dvě lokální nezávislé role schválily společný
  packet na aktuálním kandidátu. Projektový T045 zveřejnil svůj APPROVE pro
  přesný pár. GitHub odmítl formální self-review s HTTP 422, protože
  připojený účet byl autorem PR. Verdikt samostatného review agenta je
  doložen komentářem a formální stav GitHub review zůstal beze změny.
  Merge následoval po kontrole ready stavu, mergeability a aktuálních
  revizí. [T045 záznam](https://github.com/p-rum/kgmaker/pull/132#issuecomment-7066210715)
- **GitHub Actions NEOVĚŘENO.** Běhy `44922298898`, `44922292753` a
  `44922298959` mají celkem patnáct jobů bez přiřazeného runnera a bez
  zaznamenaných kroků. Vzorkované logy vrátily 404. Důvod ukončení z dostupných
  dokladů nevyplývá. [T045 záznam](https://github.com/p-rum/kgmaker/pull/132#issuecomment-7066210715)

```bash
PYTHONPATH=src python -m pytest -n 3 --dist loadfile \
  --basetemp "$RECEIPT_DIR/pr132-full-ready-config-tmp" \
  -o tmp_path_retention_policy=failed -p no:cacheprovider -q --tb=short -ra \
  --junitxml="$RECEIPT_DIR/pr132-full-ready-config.xml"
```

### Zbývající rozsah T034

Sloučená oprava odblokovala vyzkoušené čtení uloženého normalizovaného
kontextu. První čtecí JSON průchod T034 může použít přesný trigger T024,
ProcessView T025 a katalog explicitně dodaných snapshotů T033. Pro zápis
čeká samostatný kontrakt neměnné revize PROPOSED a předání původního packetu,
kandidáta a přesných CAS tokenů. T032 dnes zaznamenává rozhodnutí APPROVE
a REJECT. Reprodukce v paměti nad aktuálním kódem také ukázala, že validní ProcessView
s dalším service kontextem mimo deklarované kontexty procesu dostane při
přípravě packetu `SELECTION_CONTEXT_MISMATCH`. Širší výběr proto čeká na
ověření se skutečnými vstupy více repozitářů. [T034](../tasks/T-034_add-process-cli.md)

### Kontroly dokumentačního kroku

- PASS — `PYTHONPATH=src python -m pytest -p no:cacheprovider --assert=plain -q --tb=short tests/test_completion.py tests/test_t032_persist_process_review.py`.
  50 PASS / 0 SKIP za 1,38 s.
- PASS — `kgmaker completion plan --jobs 3` vrací u T032
  `MERGED / VERIFIED_IN_SCOPE` s akcí `none`. T034 je
  `PLANNED / NOT_RUN` s akcí `implement` pro čtecí práci.
- PASS — obsahové srovnání testovacího manifestu proti merge tree potvrdilo
  shodu 837 sledovaných souborů. Jediným rozdílem byla připravená konfigurace exporteru.
- PASS — `semantic update --base 4011825`, scoped `semantic apply`,
  `semantic validate`, `memory capture --base 4011825`, `scan`, `status`, `check`,
  `git diff --check` a `git diff --cached --check`.
- Úplná sada pro samotnou dokumentační změnu je NOT_RUN. Zdroj, testy,
  schémata a nainstalované instrukce odpovídají sloučenému #132.

### Přenos #137 po integraci oprav CI

Dokumentační revize `1705305922c48551fd780139fd3cf8414920b2db` přebírá
nový `main` `024334a22f4269fa5cbc720b73e429688069464c` s tree
`f877aecde09278020ab2a8b507360486fc699c55`. Tento základ obsahuje opravy CI
ze společné integrace. Přenos zachovává doklady obou větví a znovu ověřuje
inventář T032 a návaznost T034. [Sloučené #142](https://github.com/p-rum/kgmaker/pull/142)

- PASS — `PYTHONPATH=src python -m pytest -p no:cacheprovider --assert=plain -q --tb=short tests/test_completion.py tests/test_t032_persist_process_review.py`.
  50 PASS / 0 SKIP. Ověřený kontrakt T032 zahrnuje explicitní POSIX review.
- PASS — `kgmaker completion plan --jobs 3` vrací pro T032 stav
  `MERGED / VERIFIED_IN_SCOPE` a akci `none`. Čtecí krok T034 má stav
  `PLANNED / NOT_RUN` a akci `implement`.
