# Záznam sloučení technického Markdown výkazu T036

Datum 2026-11-27. Výchozí `main` `71ace79093f853c385566dd90c25e0178cec8fca`,
strom `17b6856043015d916616b32b06d50a4fe13f4fe5`.
[T048-S01 / T048-AC01](../tasks/48_completeImplementationHandoff.md)
· [T036-S05 / T036-AC06](../tasks/T-036_render-business-process-report.md)
· [Stav dodání](../production-analysis-progress.md).

## Krok 1 — sjednocení stavu T036 s důkazy na main

[#190](https://github.com/p-rum/kgmaker/pull/190) byl 2026-11-27 v 11:56:04 UTC
sloučen do `main` jako [`71ace79093f853c385566dd90c25e0178cec8fca`](https://github.com/p-rum/kgmaker/commit/71ace79093f853c385566dd90c25e0178cec8fca).
Rodiče jsou v pořadí `0e0c49120281e73ae131777e6f342f39407644e6` a
`6a8b9145f0278dec93ce50bd07dcd0ffef61b521`. Výsledný strom je shodný se
schváleným headem. Nezávislá projektová revize T045 ověřila danou dvojici
SHA a uzavření připomínky k reprodukovatelnosti v Change206. Doklad o sloučení
má SHA-256 `517c2b90b5c39b2867d2f6f171735ba11da4fe7d88a5ae50b6b4901edf518831`.
[Záznam T045](https://github.com/p-rum/kgmaker/pull/190#issuecomment-7217628289).

- Přímý cílený nativní běh na skutečném `71ace79` měl **122 PASS / 0 SKIP**,
  raw exit 0. Použil CPython 3.13.18, markdown-it-py 3.0.0, Mermaid 11.4.1,
  jsdom 26.0.0 a Javac 21.0.6. Manifest vstupů a toolchainu se před a po běhu
  shodoval. SHA-256 JUnit
  `a879152d1d83a4f7471bf37fc3a543bda557feb09b2e21e3aa77e548a1c5f4ab`.
- Před sloučením měla úplná standardní sada na schváleném headu `6a8b914`
  nad `0e0c491` **2 694 PASS / 1 418 SKIP / 1 očekávaný XFAIL**, raw exit 0.
  SHA-256 JUnit `48d1c4106b0f593496270c502f34e362a82c9820583f7f3992753ac3e1d365db`.
  Úplná sada přímo na `71ace79` má v tomto záznamu stav NOT_RUN. Přesný
  výběr testů, prostředí, piny a původní výsledky jsou v
  [Change206](206_renderBusinessProcessReport.md).

Kanonický řádek T036 nyní uvádí `MERGED / PARTIAL` a odkaz na [#190](https://github.com/p-rum/kgmaker/pull/190).
[T036-AC06](../acceptance-inventory.md#t036--markdown-výkaz-dodaného-procesu)
zůstává PARTIAL a má přímý doklad z merge. T036-AC02 má stav NOT_RUN.
Příklad v [návodu](../process-paths.md#markdown-report-for-a-supplied-processview-t036)
a odkazy v [README](../../README.md#local-technical-process-paths-t025) dál
popisují stejné čisté Python API `render_process_markdown(view)`. Povely
CLI ani registry se nemění, `kgmaker process render` poskytuje čtecí JSON
podle T034. Aktuálnost zachyceného source locatoru a runtime pozorování
se v tomto kroku neověřují. Migrace není potřeba.

## Kontrola záznamu a navazující úkoly

Pro porovnání se použila pracovní kopie dokumentace z `git archive` nad
výchozím SHA a zdroj stejné revize. Příkaz `kgmaker completion plan --root
"$PWD" --jobs 32` měl raw exit 0 před a po úpravě. Plán má 135 položek,
z toho 111 MERGED, 23 PLANNED a jednu IN_PROGRESS. T036 přechází na akci
`verify`. T038 a T040 se podle deklarovaných závislostí uvolní pro
implementaci. T042 dál čeká na T038 a T040. S10-W03 dál vyžaduje
`VERIFIED_IN_SCOPE` u S10-W02, který zůstává `MERGED / PARTIAL`.

`git apply --check --whitespace=error` a `git diff --check` ověřily záplatu
v pracovní kopii. Přípravný cílený běh z kořene kopie měl 13 PASS / 0 SKIP,
raw exit 0. Výstupy byly mimo kopii v zapisovatelném `$PROOF`.

```bash
python -m pytest --assert=plain -q -p no:cacheprovider tests/test_completion.py \
  --basetemp "$PROOF/planner-tmp" --junitxml="$PROOF/planner.xml"
```

Úplná sada, sémantická aktualizace a nezávislé review měly v této první
přípravné kopii stav NOT_RUN.

## Krok 2 — přenos na main po sloučení #191

Výchozí `main` pro přenos je `3dc249ec66855671f6b78fd6fc86e02603521553`,
strom `20ddb36177a390f0b8e315edaba0e2f66f1e69fb` po
[#191](https://github.com/p-rum/kgmaker/pull/191). Čistá pracovní větev přijala
základ pomocí `git merge --ff-only "$BASE"`. Původní záplata `$PATCH` se
poté aplikovala čistě a zasáhla pouze řádek T036, důkaz T036-AC06 a tento
záznam. Kontrola `git diff --cached --check "$BASE"` měla raw exit 0.

Před aplikací se v kořeni větve načetl strojový graf přijatý s #191
do `.kgmaker/graph.json`. Jeho SHA-256 je
`03d2d2e9c4e37899af7420c724c50fd5b0757f95302477847f85fefe772a4793`.
Příkazy `kgmaker semantic validate --root "$PWD"` a
`kgmaker check --root "$PWD"` měly na tomto základu raw exit 0.

Přenos a jeho přípravné kontroly proběhly z kořene téže větve s `BASE`
nastaveným na uvedené plné SHA a `PROOF` jako zapisovatelným adresářem mimo větev.
`PYTHON` a `KGMAKER` označují binárky stejného místního prostředí.

```bash
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1
git apply --index --check --whitespace=error "$PATCH"
git apply --index --whitespace=error "$PATCH"
git diff --cached --check "$BASE"
"$KGMAKER" completion plan --root "$PWD" --jobs 32
"$PYTHON" -m pytest --assert=plain -q -p no:cacheprovider tests/test_completion.py \
  --basetemp "$PROOF/post191-preflight-planner-tmp" \
  --junitxml="$PROOF/post191-preflight-planner.xml"
"$KGMAKER" semantic update --base "$BASE" --root "$PWD"
# Z packetu převzít update_id do semantic-patch.json schématu 1 s prázdnými nodes a edges.
"$KGMAKER" semantic apply --root "$PWD"
"$KGMAKER" semantic validate --root "$PWD"
```

Příkazy měly raw exit 0 a testy plánovače **13 PASS / 0 SKIP**.
SHA-256 JUnit `9d069adbe4419626dd0db146f0abdb708c034d9c435eaec07d08b4d8baea5a9b`.
Aktualizace omezila packet na tři dokumenty, bez dotčených kurátorovaných
záznamů. Ověření záplaty zachovalo všech 60 konceptů, 222 vazeb a 513
přijatých epizod. Plán znovu vybral T038 a T040. T042 čeká na oba a
podmínka `VERIFIED_IN_SCOPE` pro S10-W02 dál blokuje S10-W03.

Na přípravném zdrojovém stromu `0889156b61554095bcf2225e6d17ff32b4d38626`
pak prošla celá následující posloupnost. Příkazy se spustily pod stejným
`BASE` z kořene pracovní větve po omezené aktualizaci a validaci sémantiky.

```bash
capture=(memory capture --base "$BASE" --validation planner=passed
  --validation source-diff=passed --validation semantic-before-capture=passed)
"$KGMAKER" "${capture[@]}" --root "$PWD"
"$KGMAKER" "${capture[@]}" --root "$PWD"
"$KGMAKER" semantic validate --root "$PWD"
"$KGMAKER" scan --root "$PWD"
"$KGMAKER" status --root "$PWD"
"$KGMAKER" check --root "$PWD"
```

Oba příkazy `memory capture` měly raw exit 0. První zapsal jedinou epizodu
`episode:54158eae85a55f0c6a3f759c719b2f1a919ef4387521f6131c883b4012e2ef7b`
pro tři soubory T048. Druhý nalezl tutéž epizodu a zachoval bajty sémantiky
i vstupního strojového grafu. `semantic validate`, `scan`, `status`, `check`
a následné `git diff --cached --check "$BASE"` měly raw exit 0. Výsledný
strom byl `72b40b11de75ef08d760508ee613761f17c12340`. Jeho strojový graf měl
SHA-256 `047e997d5a9eb2d69fa2e070268222cd9a26226835c42ab197510a6c39eea24d`.
Opakovaný běh plánovače měl 13 PASS / 0 SKIP, raw exit 0 a JUnit SHA-256
`d14bd214e531effa0ed92f638a523f1328b39dadcb614367e420389c05f03ba3`.

Přípravný strom a jeho doklady se archivovaly. Pro tento text se před
novým záznamem epizody obnoví přijatý základ #191 s jeho 513 epizodami.
Nová epizoda T048 tak odkazuje na otisky všech tří dokumentů finálního
výřezu.

### Samostatné zopakování finálního výřezu

`CANDIDATE` je SHA staženého commitu T048 a `BASE` je výchozí SHA výše.
Ve staženém repozitáři lze odvodit `$PATCH` pro nový čistý checkout
základu. Při původním přenosu se použila dříve uložená záplata, takže
výstup tohoto příkazu obsahuje navíc finální znění Change208.

```bash
git diff --binary "$BASE" "$CANDIDATE" -- \
  docs/acceptance-inventory.md docs/changes/208_recordBusinessProcessReportMerge.md \
  docs/production-analysis-progress.md > "$PATCH"
```

Otisk strojového grafu při přípravném ověření patří dodanému archivu
`candidate-graph.json.gz` z ověření #191. `$BASE_GRAPH` označuje jeho místní
kopii. Po kontrole SHA-256 archivu
`8d6e4ed62c64e1e67a8ec3cbfbda28963323e3645b8e536306a71380d240f3e2`
se rozbalí pomocí `gzip -dc "$BASE_GRAPH" > .kgmaker/graph.json` v kořeni
čistého checkoutu základu. SHA-256 rozbaleného grafu je uvedeno výše.
Samostatný čistý replay z `git archive "$BASE"` spustil
`kgmaker scan --no-docs --root "$PWD"` s raw exit 0 a vytvořil graf se
SHA-256 `9c684dd4ebee46fedb54e9e863aec801f33ea86a90f70bf0a0d9bb3476897f8b`.
Tento běh je samostatný doklad reprodukce ze zdrojů. Výše uvedené přesné
porovnání a záznam epizody vycházejí z dodaného archivu #191.

Při přípravě tohoto záznamu jsou úplná standardní sada a nezávislé review
finálního kandidáta NOT_RUN.
