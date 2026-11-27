# Atomický export technického pohledu procesu

Datum 2026-11-27. Základ `d759fa907aa7b17e08bc3c8db42cd3194b42f2dc`
na `main`, strom `eda3ab15a0a932eb64f355c50cfcdb92ef167d3f`.
Ve výchozím stromu byly dostupné dodávky T022 (`fd8d5e9`),
T036 (`71ace79`) a T037 (`b1a8ba1`). [Zadání T038](../tasks/T-038_publish-view-artifacts-atomically.md).

## T038-S01 a S04 — explicitní příkaz a společný snapshot

Na výchozím stromu platný `fixtures/process-model/checkout.json` vyvolal
v `kgmaker process export` diagnostiku `INVALID_ARGUMENTS`, raw exit 2 a prázdný
stdout. Vstup měl shodné bajty a adresář pro výstup nevznikl. První izolovaný
regresní test `test_public_export_publishes_three_artifacts_for_one_snapshot`
selhal s raw exit 1 na stejném chování.

`src/kgmaker/process_cli.py` přijímá `--snapshot` a `--output` pro explicitní
`ProcessView` pod lokálním kořenem. `src/kgmaker/process_render.py` používá
kanonický JSON a stávající technické renderery T035 a T036 nad jedním
normalizovaným dokumentem. Markdown obsahuje bajtově shodný Mermaid diagram.
Publikace nespouští kontrolu checkoutu, proces aplikace, worker ani síťový
dotaz. Dodané důkazy a hranice zůstávají v technickém rozsahu zachyceného
pohledu. Použití je popsáno v [README](../../README.md#local-technical-process-paths-t025)
a [návodu](../process-paths.md#atomic-process-export-t038).

## T038-S02 a S03 — omezené cesty, CAS a konzistentní čtení

`src/kgmaker/view_store.py` připraví tři soubory v nové generační složce.
Před výměnou jediného `manifest.json` ověří snapshot i publikační základ
pod zámkem cílového adresáře. Manifest odkazuje na stejné neměnné generační
ID a nese SHA-256 všech tří souborů. Čtenář dokončí načtení podle jednoho
manifestu i během další publikace. Shodný aktivní export vrátí stávající
manifest a pozdější návrat k dřívějšímu obsahu dostane nové ID. Při chybě před
přepnutím se uklidí vlastní připravená sada. Historické generace se ponechají.

Nezávislá kontrola našla při přípravě další reprodukované chyby. CLI mohlo
přijmout cestu přesměrovanou během jejího ověření a mohlo publikovat po
pozdním deadline, zrušení nebo změně vstupu. Regresní test cesty měl raw
exit 1 a CLI 0. Dva testy pozdního deadline a zrušení měly raw exit 1 a CLI 0.
Test pozdní změny vstupu měl raw exit 1 a CLI 0. Test změny připraveného
diagramu během posledního úplného čtení vstupu měl raw exit 1 a CLI 0.
Export nyní předá deskriptorové kontrole původní relativní cestu. Po úplné
kontrole vstupu a publikačního základu ověří identitu připravených souborů,
stav vstupu, manifestu a cíle a zkontroluje deadline a případné zrušení.
Po výměně je směrodatný uložený manifest. Zachycené přerušení zápisu stdout
hlásí `EXPORT_RECEIPT_INTERRUPTED` a ponechá publikovanou generaci.

Při další kontrole oba testy přerušení úklidu po výměně skončily raw exit 1
a CLI 130, přestože byl manifest uložen. Po potvrzeném přejmenování už export
neprovádí úklid spotřebovaného dočasného manifestu. Zachycené přerušení při
uvolnění deskriptoru po potvrzené publikaci vrátí známý výsledek.

Export používá relativní operace nad deskriptory, zákaz následování
symlinků a adresářový zámek POSIX. Ověřené prostředí je Linux. Na
platformě bez požadovaných operací je export nedostupný. `process render`
nadále poskytuje čtecí JSON. Nový manifest je samostatný verzovaný formát
odvozeného exportu, existující graf ani workspace k migraci nepotřebuje.

## T038-S04 — acceptance a přímé kontroly

Testy jsou v `tests/test_t038_publish_view_artifacts_atomically.py`.

| AC | Testy a lokální výsledky |
|---|---|
| T038-AC01 | `test_public_export_publishes_three_artifacts_for_one_snapshot` a `test_reader_keeps_one_generation_and_repeating_active_export_is_idempotent` mají PASS. Ověřují přesný fingerprint a hashe, kontext, idempotenci a čtenáře před a po výměně manifestu. |
| T038-AC02 | `test_failures_preserve_previous_generation`, `test_cancel_before_first_switch_leaves_no_artifact_paths`, `test_interrupt_after_switch_reports_the_committed_manifest`, `test_post_commit_cleanup_does_not_cancel_published_export` a `test_interrupt_during_receipt_leaves_committed_manifest` mají PASS. Pokrývají selhání rendereru, zápisu a přepnutí, deadline, zrušení i přerušení u výměny, úklidu a výpisu. |
| T038-AC03 | `test_two_processes_cannot_switch_from_the_same_manifest`, `test_aba_cannot_revive_a_stale_writer`, `test_invalid_scope_and_untrusted_output_paths_fail_before_writes`, `test_output_symlink_substitution_cannot_escape_after_render` a `test_output_path_cannot_be_rebound_during_validation` mají PASS. |
| T038-AC04 | `test_failures_preserve_previous_generation`, `test_invalid_scope_and_untrusted_output_paths_fail_before_writes`, `test_unknown_manifest_is_not_replaced` a `test_staged_artifact_change_during_final_input_read_preserves_active` mají PASS. Testy kontrolují vstup, uložené bajty a jejich časy změn. Odmítají časnou i pozdní změnu vstupu a změnu připraveného diagramu během kontroly. |
| T038-AC05 | `test_native_export_preserves_partial_boundaries_in_all_artifacts` má PASS. Skutečné parsování Markdown a Mermaid s výstupem SVG ověřilo stejný diagram, `PARTIAL`, `TRUNCATED` a nerozřešenou hranici. Test také hlídá, že produktová cesta neotevírá socket ani proces. |
| T038-AC06 | PARTIAL. Cílené ověření technického exportu je doložené. Zbývá úplná sada, architektonický export a formální nezávislé review přesného base/head před PR merge. |

První běh nového testovacího souboru měl 14 PASS a 1 SKIP, raw exit 0.
SKIP byl chybějící lokální Mermaid/jsdom. První běh se zapojenými parsery
měl 27 PASS a 1 FAIL, raw exit 1. Test s úmyslně přejmenovaným výstupem
chybně porovnal absolutní cesty. Opravený test porovnává relativní jména
a hodnoty souborů.

Opravené běhy T038/T036 před poslední kontrolou úklidu měly 32 a 34 PASS,
oba 0 SKIP a raw exit 0. Po ošetření přerušení po publikaci měl konečný
cílený T038/T036 běh nad kandidátem **36 PASS /
0 SKIP**, raw exit 0. Použil CPython 3.13.18, markdown-it-py 3.0.0,
Mermaid 11.4.1 a jsdom 26.0.0 podle lockfile v `tests/rendering`.
SHA-256 JUnit `3a8bfc92d4fea49feefbdd43e00e35179f88be0443d1ba6011fce2dd5d0cd852`.
Cílený příkaz z kořene repozitáře s připnutými testovacími závislostmi má
tento tvar. `PROOF` je existující zapisovatelný adresář mimo checkout.

```bash
KGMAKER_REQUIRE_MARKDOWN_PARSER=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python -m pytest -q -p no:cacheprovider --tb=short \
  --basetemp "$PROOF/implementation-cleanup-green-pytest" \
  --junitxml "$PROOF/implementation-cleanup-green.xml" \
  tests/test_t038_publish_view_artifacts_atomically.py \
  tests/test_t036_render_business_process_report.py
```

Samostatný proces CLI na kandidátovi měl raw exit 0 a prázdný stderr.
`cmp` potvrdil totožný stdout a uložený manifest i shodné bajty fixture.
Kontrola SHA-256 potvrdila všechny tři cesty z manifestu. Stejný příkaz na
výchozím SHA reprodukuje chybějící export. Pro každý běh použij čerstvý adresář.

```bash
mkdir "$PROOF/cli"
cp fixtures/process-model/checkout.json "$PROOF/cli/process.json"
PYTHONPATH=src python -m kgmaker.cli process export --root "$PROOF/cli" \
  --snapshot process.json --output reports/process
```

## T038-S05 — stav a zbývající práce

[Stav dodání](../production-analysis-progress.md) a
[acceptance matice](../acceptance-inventory.md#t038--atomická-publikace-dodaného-processview)
zaznamenávají `IN_PROGRESS / PARTIAL`. Úplný příkaz `python -m pytest -q`,
GitHub Actions, formální T045 review finální dvojice SHA a semantické
ověření kandidáta mají v této fázi stav NOT_RUN. V tomto kroku zůstává
strojový graf mimo rozsah. Projektový `memory recall` neměl v této
izolované kopii čitelný strojový graf. Architektonický export a navazující
úplné acceptance ověření zůstávají v T038, T041 a T042.

## T038-S05 — přenos po #193 a ověření grafu

Aktuálním základem přenosu je [sloučení #193](https://github.com/p-rum/kgmaker/pull/193)
`be63bc34b6f766761c39d5b9e8cde0d2389e3962`, strom
`29f864138c49815d01351df78df6385af5f322cc`. Příkazy `git merge --ff-only`,
`git apply --check --index`, `git apply --index` a kontrola diffu měly raw 0.
Původní lokální záplata má SHA-256
`33ce4658a9d984e2e675cd0c30fbeda71640579a0216debfdadb70fd1c23307b`.
Všechny tři produktové soubory a test mají po přenosu shodné bajty
s výřezem, na kterém proběhlo uvedených 36 testů. Kontrola GitHubu
na tomto základu našla nejvyšší číslo 209 v `main` a žádný Change210 ve
třech otevřených PR. Stav jiných úloh v inventáři se úpravou nemění.

Přijatý strojový graf #193 prošel kontrolami `semantic validate` a `check`
s raw 0. `memory recall` nad touto kopií proběhl s raw 0. Přípravný
integrační strom před přidáním tohoto záznamu má ID
`63305f325b337698ded4d1deb04651e4962d91ab`. Plán na něm eviduje 135
položek a stejných 32 kandidátů. T038 se posunulo z třetí na druhou
pozici s akcí `resume`. T039, T041 a T042 dál čekají na dodání T038.
Další pořadí zůstalo stejné. W03 dál vyžaduje `VERIFIED_IN_SCOPE`
u W02. Cílený běh plánovače měl **13 PASS / 0 SKIP**, raw 0, JUnit
SHA-256 `b0d9b230c098043e46effdb6ef9bf9ae0d2f51f0c70308ecba889d299897386d`.

Na stejném přípravném stromu měly `semantic update`, `semantic apply`,
`semantic validate`, obě zachycení `memory capture`, `scan`, `status`
a `check` raw 0. Kurátorovaná sémantika zachovala 60 konceptů a 222
vztahů. Přesunulo se 12 odkazů na sedm zdrojových lokátorů a znovu se
svázala jedna existující Markdown sekce pod stejným nadpisem. Všech
515 přijatých epizod zůstalo bajtově shodných. Přípravný záznam
`episode:4fa3ca924b1fffddd7142dadaf4a5c93f043652e77fa94985760b5f0bf9e6063`
byl idempotentní. Graf přípravného stromu
`f03e44ace11ee0a766877b653aa23c5ad719ee55` má SHA-256
`ea3a6e4c57a7e0d1f35caccf78d14cc2f042fc10505162f56a6e28b51904211d`.
Z 461 dotčených uzlů patří každý devíti souborům T038. Všechny tři
uzly Rates a jejich 275 vztahů zůstaly shodné. Strojový graf zachoval
654 importů a přidal pět importů z dotčených souborů. Po převodu
generovaných značek na skutečná jména zachovává `GRAPH.mmd` celou původní
topologii a přidává jeden modul se třemi zobrazenými importy.

Přípravný graf a epizoda jsou uchovány v odděleném dokladu. Finální
zachycení vychází z přijaté kopie #193 a pokrývá obsah tohoto záznamu.
Jeho vlastní identifikátor a hash výsledného grafu patří do dokladu mimo
zachycované soubory. Kontroly fyzické aktuálnosti source locatoru a
schválených popisů mají samostatný rozsah.

### Reprodukce přenosu a grafových kontrol

`CANDIDATE` označuje výslednou Git revizi T038, `PROOF` zapisovatelný
adresář mimo checkout a `KGMAKER` a `PYTHON` binárky z prostředí s
CPythonem 3.13.18. `BASE_GRAPH` je přijatý archiv grafu #193. Samostatný
`scan --no-docs` čistého archivu `BASE` vytvořil s raw 0 graf SHA-256
`4a4e8738413abd2374906c8b014297cb30e5006028eee181f355ab8bd685481e`.
Pro přesné zachycení se použil přijatý strojový graf s vlastním
otiskem, ověřeným v následujícím postupu.

```bash
set -euo pipefail
BASE=be63bc34b6f766761c39d5b9e8cde0d2389e3962
git diff --binary "$BASE" "$CANDIDATE" -- README.md \
  docs/acceptance-inventory.md docs/changes/210_publishProcessViewAtomically.md \
  docs/process-paths.md docs/production-analysis-progress.md \
  src/kgmaker/process_cli.py src/kgmaker/process_render.py src/kgmaker/view_store.py \
  tests/test_t038_publish_view_artifacts_atomically.py > "$PROOF/t038.patch"
mkdir "$PROOF/clean-source"
git archive "$BASE" | tar -x -C "$PROOF/clean-source"
(
  cd "$PROOF/clean-source"
  PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 "$KGMAKER" scan --no-docs --root "$PWD"
  sha256sum .kgmaker/graph.json
)
```

V čisté izolované pracovní větvi s `HEAD` na `BASE` z předchozího bloku
načtěte a ověřte přijatý graf. Záplata odvozená z finální revize obsahuje
jen devět běžných souborů a žádný generovaný grafový výstup.

```bash
set -euo pipefail
test "$(git rev-parse HEAD)" = "$BASE"
test -z "$(git status --porcelain)"
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1
printf '%s  %s\n' 225377f9ba1f452b7c9b299aafcd13cabbfbf64920d6b7ab06d35cf226499609 \
  "$BASE_GRAPH" | sha256sum -c
gzip -dc "$BASE_GRAPH" > .kgmaker/graph.json
printf '%s  %s\n' 76f0cec90b9364626c00519ce0c162f22e0188f14bfa4141db5f53ee5de3a2b8 \
  .kgmaker/graph.json | sha256sum -c
"$KGMAKER" semantic validate --root "$PWD"
"$KGMAKER" check --root "$PWD"
"$KGMAKER" memory recall 'T038 manifest publication atomic process export' --root "$PWD" --limit 3
git apply --check --index --whitespace=error "$PROOF/t038.patch"
git apply --index --whitespace=error "$PROOF/t038.patch"
git diff --cached --check "$BASE"
"$KGMAKER" completion plan --root "$PWD" --jobs 32
"$PYTHON" -m pytest --assert=plain -q -p no:cacheprovider tests/test_completion.py \
  --basetemp "$PROOF/planner-tmp" --junitxml "$PROOF/planner.xml"
"$KGMAKER" semantic update --base "$BASE" --root "$PWD"
"$PYTHON" - "$BASE" <<'PATCH'
import json
from pathlib import Path
import sys

update = json.loads(Path(".kgmaker/semantic-update.json").read_bytes())
assert update["base_commit"] == sys.argv[1]
assert len(update["changed_files"]) == 9
paths = "docs/process-paths.md"
anchors = {
    paths: {245: 289, 247: 291, 291: 335, 333: 377, 400: 444, 508: 552},
    "src/kgmaker/process_cli.py": {84: 97},
}
section = f"section:{paths}:Static failure projection (T029)"
old_endpoint, new_endpoint = f"{section}::506", f"{section}::550"
patch = {"schema_version": 1, "update_id": update["update_id"]}
for kind in ("nodes", "edges"):
    patch[kind] = update[f"affected_semantic_{kind}"]
    for row in patch[kind]:
        line = row["source_line"]
        row["source_line"] = anchors.get(row["source_file"], {}).get(line, line)
        for key in ("source", "target"):
            if row.get(key) == old_endpoint:
                row[key] = new_endpoint
Path(".kgmaker/semantic-patch.json").write_text(json.dumps(patch, indent=2, ensure_ascii=False) + "\n")
PATCH
"$KGMAKER" semantic apply --root "$PWD"
"$KGMAKER" semantic validate --root "$PWD"
capture=(memory capture --base "$BASE" --validation exact-head-native=unknown
  --validation standard=unknown --validation planner=passed
  --validation source-diff=passed --validation semantic-before-capture=passed)
"$KGMAKER" "${capture[@]}" --root "$PWD"
sha256sum .kgmaker/semantic.json .kgmaker/graph.json > "$PROOF/first-capture.sha256"
"$KGMAKER" "${capture[@]}" --root "$PWD"
sha256sum -c "$PROOF/first-capture.sha256"
"$KGMAKER" semantic validate --root "$PWD"
"$KGMAKER" scan --root "$PWD"
"$KGMAKER" status --root "$PWD"
"$KGMAKER" check --root "$PWD"
```

## T038-S03 a S04 — předání potvrzené publikace po nezávislé kontrole

Na původním headu [#194](https://github.com/p-rum/kgmaker/pull/194)
`378e8d53e24276d1dda0a28ffa55e373543b4504` odhalila kontrola T045 dva
případy pro T038-AC02 a T038-AC04. Přerušení mezi atomickým pomocníkem
a příkazem i přerušení před stdout vrátilo `CANCELLED` s exit 130.
V obou případech už nový manifest odkazoval na tři platné soubory.
Doklad nezávislé kontroly řádkových událostí má SHA-256
`0b6446624bcbdb3a2699d7796134ac7b614395125f25c28dbd972b45247b185e`.
Archiv přesného původního headu se stejným novým regresním testem měl
**2 FAIL / 0 SKIP**, raw 1, JUnit SHA-256
`e37a9d8d1515157dcb4cd4813c8068a5ed698ff14131e4e21709f7433b1e5195`.

`src/kgmaker/view_store.py` předává potvrzený manifest přímo v okamžiku
výměny nebo po ověření inode po výjimce. Tentýž stav čte úklid a
`src/kgmaker/process_cli.py`. Přerušení při předání z atomického
pomocníka může zachovat běžný výpis a exit 0. Při zachyceném přerušení
na hranici CLI se zachová publikovaný manifest a příkaz vrátí
`EXPORT_RECEIPT_INTERRUPTED` s exit 1. Před potvrzením výměny zůstávají
v platnosti dřívější kontroly chyb a zrušení.

`test_interrupt_after_publication_handoff_preserves_replacement` ověřuje
obě cesty po výměně dřívější generace. Ověřil hashe obou sad souborů
a shodu bajtů obou vstupů. Přímá injekce na řádcích před vrácením
potvrzeného výsledku a před stdout na opraveném zdroji zopakovala exit 0
a exit 1 v uvedeném pořadí. Její ověřovací příkaz měl raw 0.
SHA-256 dokladu `4c53f0255172ae27d4221ef97d9f540fa68826fbced0ad90f2da069325540b39`.

Cílená sada stejného opraveného zdroje měla **38 PASS / 0 SKIP**, raw 0
(26 T038 a 12 T036). JUnit SHA-256
`b2081fd9b3dc881ea1f81e5d5a82822988d7b2cd8cf432fac9b85edc330c84a6`.
Prošly připnutý markdown-it-py 3.0.0 a Mermaid 11.4.1 se SVG a jsdom 26.0.0
pod CPythonem 3.13.18. Samostatné `python -m kgmaker.cli process export`
vrátilo raw 0 se shodným stdout a manifestem, třemi ověřenými hashi
a nezměněným vstupem. Původní úplný běh (2 730 PASS, 1 409 SKIP,
1 očekávaný XFAIL, raw 0) patří k headu `378e8d5`. Úplný běh
a formální T045 review nového headu mají při přípravě stav NOT_RUN.

Pro reprodukci použijte `CANDIDATE` s opravenými testy, `PYTHON`
ze stejného místního prostředí a `PROOF` mimo checkout. Selhání
má být ve dvou asercích návratového kódu až po ověření manifestu a souborů.

```bash
set -euo pipefail
original=378e8d53e24276d1dda0a28ffa55e373543b4504
test_path=tests/test_t038_publish_view_artifacts_atomically.py
mkdir "$PROOF/retry-red"
git archive "$original" src tests fixtures pyproject.toml | tar -x -C "$PROOF/retry-red"
git show "$CANDIDATE:$test_path" > "$PROOF/retry-red/$test_path"
(
  cd "$PROOF/retry-red"
  raw=0
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src "$PYTHON" -m pytest -q -p no:cacheprovider \
    --tb=short --basetemp "$PROOF/retry-red-pytest" --junitxml "$PROOF/archive-red.xml" \
    "$test_path" -k interrupt_after_publication_handoff || raw=$?
  test "$raw" = 1
)
KGMAKER_REQUIRE_MARKDOWN_PARSER=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  "$PYTHON" -m pytest -q -p no:cacheprovider --tb=short \
  --basetemp "$PROOF/retry-focused-pytest" --junitxml "$PROOF/retry-focused.xml" \
  "$test_path" tests/test_t036_render_business_process_report.py
```

### Graf a plán po opravě předání

Základem nového zachycení zůstal přijatý [#193](https://github.com/p-rum/kgmaker/pull/193)
`be63bc34b6f766761c39d5b9e8cde0d2389e3962` v samostatné pracovní kopii.
Původní head `378e8d5` a jeho grafový doklad zůstávají v historii tohoto PR.
Obnova před zachycením ověřila obsah strojového grafu a sémantiky #193.
Postup a otisky pro přijatý archiv jsou v oddílu
[Reprodukce přenosu a grafových kontrol](#reprodukce-přenosu-a-grafových-kontrol).
Recept opět přeložil původní lokátor `process_cli.py:84` na `97`
a ověřil stejných sedm lokátorů celkem.

Na přípravném stromu `e1148f2e59bc9dc431f5aef2e20038c467292114` měly
plán, sémantické příkazy, opakované zachycení, `scan`, `status`
a `check` raw 0. Plán zůstal bajtově shodný s přípravným přenosem po #193.
Testy plánovače měly **13 PASS / 0 SKIP**, raw 0, JUnit SHA-256
`5b31d0ca407a20e68dfe5419d024a49f8c47e814afd2f5113f514fe9d64ec427`.
Přípravná epizoda
`episode:595d54ba0a737d7dc3e0bc5223aa4bd4f1bd4566f9ba0408a9ccbfdc9dcf45a5`
a graf stromu `1a74ed26780bc0632343289bfbbca5206751ee11` s SHA-256
`787920b0691fc24b3afcb17fd77c33ef6cdef50fe0fd15364e87c1ab0c1512c9`
jsou v odděleném dokladu. Čistý zdrojový replay základu měl raw 0 a SHA-256
`4a4e8738413abd2374906c8b014297cb30e5006028eee181f355ab8bd685481e`.

Kontrola zdrojových cest ověřila 466 dotčených uzlů z devíti souborů T038.
Shodné zůstaly 515 dříve přijatých epizod, 60 konceptů a 222 vztahů
kurátorované sémantiky s ověřenými přesuny lokátorů, uzly a vztahy Rates
i původní topologie Mermaid. Základ finálního zachycení opět tvoří
přijatých 515 epizod a obsah tohoto doplněného záznamu. Finální otisk
je v dokladu mimo zachycované soubory.

### T038-AC02 a AC04 — potvrzení patří jedné publikaci

Další kontrola ověřila předání stejného objektu s již potvrzeným
manifestem do druhého exportu. Před opravou mohl záznam první publikace
překrýt skutečnou chybu zápisu druhého exportu a vrátit exit 0.
`test_confirmed_holder_cannot_authorize_a_second_export` selhal s raw 1.
SHA-256 JUnit `1ab647e7347eaaa0050360ca0d431e9db341a8ba2f0161ac9c5fe43676046e06`.
Kontrola na vstupu do store nyní přijímá prázdný stav pro novou publikaci.
Stav s potvrzeným manifestem odmítne před přípravou výstupu jako
`EXPORT_RECEIPT_ALREADY_SET` s exit 2. Test ověřuje nulový počet zápisů
a shodu manifestu, souborů i seznamu cest po odmítnutí.

Na opraveném zdroji proběhlo **39 PASS / 0 SKIP**, raw 0 při stejném
výběru a pinech z předchozího příkladu, z toho 27 případů T038 a 12 T036.
SHA-256 JUnit `387e1824ee4d779bd09fd9379023ab0ddf2d32afa203bf1f34dd2d601b8ec428`.
Obě přímé zkoušky přerušení po publikaci i samostatný CLI běh prošly
znovu. Doklad řádkových událostí má SHA-256
`cfc49e5be3fb318fba8b9df3e372a26f2bf3fc976ea87f59d6d53a0538ed4b6e`.
Graf průběžného kandidáta `f852f98ec008b0e7551e72aeaed748fbf2facf18`
zůstal v samostatném archivu. Pro finální zachycení se znovu načetl
přijatý základ #193 a ověřil se zde uvedený sémantický postup.
