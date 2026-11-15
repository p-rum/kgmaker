# T027 — HTTP hranice mezi procesy

Výchozí SHA: `14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8` (`main`, PR #100).
Změna je kandidát T027; neprohlašuje dokončení T004. Závislosti ověřeny v tomto
base: T014 je merged a jeho `project_remote_interfaces` poskytuje release/contract
ověřený HTTP binding a target context; T025 je merged a jeho `ProcessView`
zachovává lokální callsite a pokračování. Obě upstream acceptance zůstávají
v progress matrix PARTIAL.

## T027-S01 — přesné napojení callsite na remote binding

`src/kgmaker/business_process.py` přidává veřejné čisté API
`project_http_process_boundary(local_process, remote_interfaces, *,
target_processes=())`. Callsite se páruje podle `origin_call_site` proti T025
call/transition ID. Remote expanze vyžaduje resolved HTTP edge, přesný target
service/context a jediný trigger s handler ID provider interface; target process
musí mít danou službu/context ve svém výběru. Napojené cílové kroky se přidají
s namespaced ID a atributy zdrojového process/revision; evidence se zachová.

Dotčené soubory: `src/kgmaker/business_process.py`,
`tests/test_t027_cross_http_process_boundary.py`.
Kompatibilita: T023/T025 ProcessView a T014 ViewDocument zůstávají beze změny;
nevzniká nový uložený formát. `workspace.py` a CLI beze změny: kontrakt je
explicitní snapshot Python API a samostatný CLI krok není v T027 zadán.

## T027-S02 — HTTP request/response a error hranice

Výsledek zachovává `HTTP_REQUEST_RESPONSE` a označí chyby
`TRANSPORT_BOUNDARY_ONLY`; nevytváří business failure outcome. Nové hrany
zůstávají UNRESOLVED / UNKNOWN / SOURCE_ONLY a proces PARTIAL. Runtime execution
zůstává `NOT_OBSERVED`, dostupnost `UNKNOWN`.

Omezení: jde o statické propojení explicitně dodaných snapshots, ne HTTP runtime
pozorování, ověření dostupnosti nebo business interpretaci response/error.

## T027-S03 — unresolved selector a lokální pokračování

Nekompatibilní/nezkompletní T014 binding, ambiguity, chybějící target ProcessView
nebo target CFG a chybějící callsite se neexpandují jako vzdálený handler. T014
unresolved selector se zachová jako external service boundary. Původní lokální
transition se ponechává, včetně continuation za callsite.

## T027-S04 — veřejná matice a ověření

Přidán `tests/test_t027_cross_http_process_boundary.py`: validní cross-repo
T014 projection s kvalifikovaným client callsite a target handler/context,
release-incompatible T014 selector bez edge, ambiguita, target bez CFG, chybějící
target, chybějící callsite, cizí scope/context, transport/error hranice,
nemutace inputů a rejection invalidního dokumentu.

Rekognoskace příkazy po obnovení indexu:

```text
PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker status --root .
PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker query --root . "project_http_process_boundary remote_interfaces process_paths"
PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker memory recall --root . "T027 HTTP process boundary remote binding local continuation"
```

Přesné test příkazy:

```text
ln -s /tmp/kgmaker-pr97-reconciled/workers/jvm/target workers/jvm/target
ln -s /tmp/kgmaker-pr97-reconciled/workers/jvm/target-k2 workers/jvm/target-k2
env JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q -rs tests/test_t027_cross_http_process_boundary.py tests/test_t014_bind_remote_interfaces.py tests/test_t025_build_local_process_path.py tests/test_t026_collapse_business_steps.py
env JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q -rs tests/test_t026_collapse_business_steps.py -k k2
rm workers/jvm/target workers/jvm/target-k2
git diff --check
```

Finální public T027 suite po doplnění explicitního foreign scope/context negativního
případu: `PYTHONPATH=src python3 -m pytest -q tests/test_t027_cross_http_process_boundary.py` — **8 PASS / 0 SKIP, 0.17 s**.

První cílený běh bez nastaveného worker PATH: **74 PASS / 96 SKIP, 1.85 s**
(historický diagnostický běh; všechna SKIP byla JDK/PATH/worker umístění).
Připravený JDK21, `KGMAKER_WORKERS_HOME` a explicitní symlink k ověřenému
`workers/jvm/target` odstranily Javac blokaci. Přesný běh cílené T027/T014/T025/T026
sady skončil **123 PASS / 47 SKIP, 8.62 s**. Zbylých 47 byly pouze T026 K2
varianty bez symlinku do připraveného `target-k2`; druhý úzký běh
`tests/test_t026_collapse_business_steps.py -k k2` s tímto připraveným artifactem
skončil **47 PASS / 0 SKIP, 2.79 s**. Jde o dvě oddělené komplementární části,
ne jeden 170-case běh. Dodatečný finální T027 rerun výše pokryl rozšířené foreign scope/context negativy.

Pro oba actual běhy: `JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64`, PATH s
`$JAVA_HOME/bin`, `KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers`,
`PYTHONPATH=src`, `/tmp/kgmaker-test-venv/bin/python`; dočasné symlinky
`workers/jvm/target` a `workers/jvm/target-k2` byly po ověření odstraněny.
`git diff --check` — PASS, bez whitespace/chyb patchu.

`python3 -m pytest -q` — NOT_RUN podle úzkého cíleného validačního rozsahu
zadaného rodičovskou orchestrací; celý suite není tvrzen. Skutečné HTTP runtime
observation — NOT_RUN; T027 jej neprovádí. První pokusy o sémantickou údržbu
neprošly validací zachování původních entries; původní tvrzení
`semantic update/apply/validate PASS` bylo nepodložené a je tímto opraveno.
Před závěrečnou údržbou byly semantic.json i generated views vráceny přesně na
baseline. Skutečné výsledky nového source-backed preservation postupu jsou
uvedeny v samostatném záznamu T027-S05 níže. První memory recall před změnami skončil NOT_RUN, protože v izolovaném worktree
nebyl čitelný index. Po `kgmaker scan` byl recall proveden; vrátil pouze staré
removed T003 merge episodes a aktuální T027 concept/test paths, bez relevantní
předchozí implementation epizody. Source `kgmaker query` vrátil nový API symbol a
T014/T025 datové kontrakty. Workflow task context/analysis/plan byly zaznamenány
přes runtime workflow task, bez přidávání task artefaktů do PR.

## T027-S05 — dokumentace a stav

Aktualizovány `README.md`, `docs/process-paths.md`,
`docs/acceptance-inventory.md` a `docs/production-analysis-progress.md`.
Příklady odpovídají veřejné API; explicitně uvádějí, že nová CLI cesta ani
persistent migrace nevznikají. Registr tasků ani T004 plán se nemění.

AC mapping:

| AC | Test / dokument | Stav |
|---|---|---|
| T027-AC01 | `test_ac01_resolved_binding_expands_exact_remote_service_context_and_keeps_evidence`, `test_public_t014_projection_links_cross_repository_client_callsite_to_target_process` | VERIFIED_IN_SCOPE; T027 testy PASS v cílené sadě |
| T027-AC02 | `test_ac02_incompatible_or_nonresolved_release_stays_external`, `test_ac05_other_scope_context_ambiguity_and_missing_callsite_never_choose_target`, `test_public_t014_incompatible_release_without_candidate_edge_remains_external` | VERIFIED_IN_SCOPE; T027 testy PASS v cílené sadě |
| T027-AC03 | `test_ac03_missing_target_cfg_retains_external_boundary_and_local_continuation` | VERIFIED_IN_SCOPE; T027 testy PASS v cílené sadě |
| T027-AC04 | `test_ac04_bad_input_and_failure_boundary_do_not_mutate_inputs`, `test_ac06_invalid_remote_binding_rejects_without_input_mutation` | VERIFIED_IN_SCOPE; T027 testy PASS v cílené sadě |
| T027-AC05 | `test_ac05_other_scope_context_ambiguity_and_missing_callsite_never_choose_target` | VERIFIED_IN_SCOPE; T027 testy PASS v cílené sadě |
| T027-AC06 | README, capability, inventář, progress a tento change note | PARTIAL; docs a lokální kontroly dodány, opakované review a PR/publication zbývá |

Zbývá: finální `git diff --check`, případná oprava nálezů, nezávislé review a
předání lokálního commitu rodičovské orchestraci. PR/remote CI řeší parent agent. T028, T029, T034 a celý T004 zůstávají mimo tento rozsah.


## T027-S05 — závěrečná údržba sémantické evidence a předání

Výchozí SHA: `14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8`. Problém: první
preservation patch odmítl validator kvůli neexistujícím/reanchorovaným koncovým
IDs; vynechání dotčených konceptů by odstranilo i nadále platné vazby z dalších
souborů. Historický PASS v tomto change note proto neprokazoval zachování dat.

Původní rozsah převzetí tohoto údržbového kroku: pouze `.kgmaker/semantic.json`, příkazy generované
`.kgmaker/GRAPH.md` / GRAPH.mmd a tento change note. Při prvním převzetí byly funkční zdroje, testy a dokumentace zmrazené.
Následné nezávislé REQUEST_CHANGES rozšířilo pověření na funkční opravy níže;
původní zmrazení již pro tyto výslovné opravy neplatí. SHA-256 finální funkční
verze se před samotnou sémantickou údržbou zaznamenají a při předání porovnají. Nevzniká nová feature, verze modelu ani číslo
zadání. Nový scoped patch musí zachovat všech 42 baseline concept IDs, 135
původních vztahů včetně confidence a 286 historických episodes. Posun symbolových
ID smí pouze reanchorovat tutéž aktuální deklaraci; nic nesmí být odstraněno jen
kvůli posunu zdrojové lokace.

Rekognoskace dle kgmaker-context byla read-only: status ohlásil stale semantic
zdroje README/process-paths a 10 vztahů s chybějícími/stale endpointy, zdroje
`business_process.project_http_process_boundary`, process-paths kontrakt a
veřejné T027 testy byly ověřeny přímo. Aktualizace používá kgmaker-semantic:
čerstvý packet, explicitní zachování/reanchor všech dotčených entries, následné
apply/validate a command-generated scan. Jediný nový koncept popisuje doloženou
snapshot HTTP hranici; jeho tři vazby lze přidat pouze k reálnému API, existujícímu
ProcessView kontraktu a konkrétnímu veřejnému integračnímu testu.

Dokumentační plochy pro tento údržbový krok: README, capability/API příklad,
progress a acceptance již odkazují na change123; bez dalšího funkčního dopadu.
CLI, task registry a instalované instrukce/templates: bez dopadu, nejsou měněny.
První implementační test výsledky výše zůstávají přiřazeny svým skutečným běhům.
Tento krok neprovádí nový full pytest ani nezvyšuje runtime/HTTP availability
support. Nové review, PR a remote CI zajišťuje nadřazená orchestrace.


## Oprava review 1 — T027-S02/S04/S05, AC03/AC04/AC05: návratové větve

Výchozí SHA `14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8`, původní lokální T027
kandidát bez commitu. Reviewer doložil kartézské propojení každého target exit s
každou lokální continuation, včetně `exceptional_exit` → normálního výstupu.
`business_process.project_http_process_boundary` nyní spojuje pouze normální
`exit` s normálním původním caller transition, případně s přesným `returns_to`
witness stejného caller block. ID/atributy původní continuation se zachovají.
Target exceptional exit neprokazuje mapování na klientskou chybu: zůstává v
importovaném grafu s `HTTP_TARGET_ERROR_BOUNDARY`; lokální exception hrany se
nemění. Samotné entry/exit/exceptional_exit neposkytují target CFG body.

Dotčené soubory: `src/kgmaker/business_process.py`,
`tests/test_t027_cross_http_process_boundary.py`. Public testy
`test_normal_and_exceptional_http_continuations_do_not_cross`,
`test_normal_response_retains_original_witness_without_mapping_server_errors` a
`test_terminal_only_target_does_not_supply_a_cfg_body`: PASS. Kompatibilita:
stejné API/model schema, odstraněny nesprávně domyšlené RESPONSE vazby; statické
request/response nezaručuje runtime transport. Bez důkazu normální continuation
se nová response hrana nepřidá, původní lokální topology zůstává zachována.

## Oprava review 2 — T027-S01/S04/S05, AC01/AC02/AC04/AC05: binding a scope

Stejná výchozí SHA a kandidát. Generic ViewDocument validace nezaručovala T014
kontrakt: neznámá rules_version, STALE edge či provider jiné kind/direction/scope/
resolution stále dovolily import target procesu. Funkce nyní ověřuje přesný
`remote_interfaces.VERSION`, HTTP provider s podporovanou `PROVIDED`/`PROVIDER`
direction, resolved stav, kompatibilní scope/context a non-STALE edge i endpoints.
UNKNOWN freshness z T014 je zachována. Target service i vybraný context musí mít
scope lokálního procesu; explicitní stale context není způsobilý. Neznámá verze
se odmítne bez mutace, neplatný candidate nezíská handler expanzi.

Dotčené soubory: stejné jako oprava 1. Public negativní matice
`test_invalid_remote_endpoint_or_binding_cannot_authorize_expansion`,
`test_target_selection_must_match_boundary_scope` a
`test_remote_stale_or_foreign_binding_preserves_external_boundary`: PASS.
Pozitivní `test_public_t014_projection_links_cross_repository_client_callsite_to_target_process`
zachovává skutečný `project_remote_interfaces` handoff. Kompatibilita: API/schema
beze změny, přísnější kontrola invalidních supplied snapshots. T027 neověřuje
živý checkout ani neautentizuje libovolné přepsané JSON; release/contract authority
zůstává T014. Do ProcessDefinition se nezavádí smyšlené release pole.

## Oprava review 3 — T027-S03/S04/S05, AC05/AC06: převzatá omezení

Stejná výchozí SHA a kandidát. Import původně přenesl target nodes/edges/provenance,
ale ztratil target diagnostics, limits a coverage.truncated. Oprava zachová
původní diagnostický code spolu se source process/revision, kombinuje lokální,
remote a target limits a nastaví truncation jako OR všech použitých vstupů.
Plná remote/target coverage se ukládá do `coverage.http_upstream_coverage` s
fingerprintem dokumentu. Lokální counters se nevydávají za součet všech služeb.

Dotčené soubory: stejné jako oprava 1. Public testy
`test_imported_target_truncation_and_limits_remain_visible` a
`test_local_and_remote_and_imported_coverage_are_preserved`: PASS; ověřují také
nemutaci původních dokumentů. Model schema a evidence kind beze změny; nový
metadata blok používá existující coverage/attributes extensibility.

Pro všechny tři opravy jsou ve stejném kroku aktualizovány README, capability/API
příklad `docs/process-paths.md`, acceptance inventory a production progress s
odkazem na change123. CLI syntax je bez dopadu (stále Python snapshot API),
registr tasků/installed templates bez dopadu. Nový task ani číslování nevzniká.

### Skutečné kontroly oprav

- `PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider /tmp/t027_review_repros.py`: před opravou **FAIL, 8 failed in 0.18s**.
  Reprodukce jsou následně převzaty do versionovaného public T027 modulu.
- První guard iterace (stejný příkaz + `tests/test_t027_cross_http_process_boundary.py`): **FAIL, 1 failed / 15 passed in 0.25s**, protože opomněla upstream direction `PROVIDED`. Opraveno podle skutečného T014 resolveru, který připouští `PROVIDED` i `PROVIDER`.
- `PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider tests/test_t027_cross_http_process_boundary.py /tmp/t027_review_repros.py`: **PASS, 33 passed in 0.43s** před posledním terminal-only případem.
- Přesný čtyřmodulový příkaz s JDK21/PATH/KGMAKER_WORKERS_HOME z T027-S04, tentokrát s oběma připravenými symlinky již od začátku: **PASS, 187 passed in 11.05s, 0 skipped**. Spuštěny skutečné Javac/K1/K2 fixture; neproběhl nový worker build ani package install. Oba symlinky byly po běhu odstraněny.
- Po finálním vyloučení terminal-only target body byl opakován pouze dotčený poslední příkaz T027 + reviewer reprodukcí: **PASS, 34 passed in 0.45s, 0 skipped** (26 versionovaných případů + 8 samostatných reprodukcí). Širší cílená sada se bez potřeby neopakovala.

Full `python3 -m pytest -q`, HTTP runtime observation a remote CI: **NOT_RUN**.
Opakované independent review/PR/publication zbývá. Výsledky původních běhů výše
jsou historické; původní 8 PASS neodhalilo tři později nalezené blokující vady.


## Oprava navazujícího review — T027-S01/S02/S04/S05, AC01/AC04/AC05: původ REQUEST

Výchozí SHA `14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8`, kandidát po prvních
opravách výše. Nový P1 doložil skutečný tvar T025 `flow.process` expanze:
`call` z caller block do child entry, `returns_to` z child normal exit a
`exception` z child exceptional exit sdílejí call_site/caller_block metadata.
Předchozí request loop proto přidával HTTP request i z child exceptional exit;
přes správnou normal RESPONSE pak vznikla nepřípustná celá cesta do local exit.

Oprava v `business_process.py` odvozuje začátek z jediného matching call uzlu,
nikoli ze source každé call-site transition. Resolved, ambiguous i unresolved
selector větev vytváří přesně jeden REQUEST ze stejného lokálního call uzlu.
Lokální returns_to/exception hrany zůstávají beze změn a neautorizují nový request.
Namespaced target response stále vyžaduje normální exit a přesnou normální caller
continuation. Schéma/API beze změny, odstraněny falešné průchody.

`tests/test_t027_cross_http_process_boundary.py` přebírá reviewer reprodukci
`test_expanded_local_callee_exception_cannot_start_remote_request_and_return_normally`
a parametrizuje všechny tři binding větve. Ověřuje přesně jeden request z
`local-call` a prochází úplnou dosažitelnost grafu: z `callee-error` zůstává
`failure` dosažitelná, ale normální `exit` není. Jde o vztahy z doloženého T025
flow kontraktu, nikoli pouze kontrolu přímých RESPONSE hran.

Nezávislý reviewer nad předchozí iterací: **8 PASS / 1 FAIL, 0.20s** (reported;
nová BFS reprodukce). Po opravě byly lokálně provedeny tyto skutečné kontroly:

```text
PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider tests/test_t027_cross_http_process_boundary.py /tmp/t027_review_repros.py
```

Nejprve **PASS, 36 passed in 0.51s**; po rozšíření stejného BFS testu o všechny tři
binding větve **PASS, 38 passed in 0.54s, 0 skipped** (29 versionovaných T027
případů + 9 samostatných reviewer reprodukcí). Dřívější 187-case běh je historicky
přiřazen předchozímu kódu, finální úzký běh pokrývá celé změněné T027 chování.
`git diff --check`: PASS. Full suite zůstává NOT_RUN podle výslovného pokynu.

Dokumentace tohoto kroku: README, `docs/process-paths.md`, production progress,
AC04 a tento záznam aktualizovány; odkazují na change123. CLI/task registry/init
instrukce bez dopadu. Sémantický reanchor následuje až po této stabilní funkční
verzi a zachová všech 42 původních konceptů, 135 vztahů a 286 episodes.


### Sémantické předání po finální funkční opravě

Reviewer nad zmrazenými blobs `business_process.py`
`c1351651681dc17428d1595f8b5ced131402012b` a T027 testem
`112d5651963e51fd2e8e3075c99841ad3f8450b2` zopakoval **38 PASS in 0.52s** a
potvrdil, že žádné funkční findings nezůstávají otevřené. Jde o source review;
finální PR review nad novým commit SHA zůstává samostatné.

`./kgmaker semantic update --base 14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8
--note docs/changes/123_crossHttpProcessBoundary.md` — **PASS**, 7 changed paths,
300 nearby nodes. `./kgmaker scan --no-docs` obnovil aktuální symbolová IDs před
reanchorem; jeho dočasné stale-semantic warning odpovídalo ještě neaplikovanému
patchi. Scoped patch zachoval všechny dotčené entries: 5 concepts / 13 edges,
žádné removals (4 původní koncepty/10 vazeb + nový doložený T027 koncept/3 vazby).
`./kgmaker semantic apply` — **PASS**, výsledná source-authored vrstva má
43 concepts / 138 relationships. `./kgmaker semantic validate` — **PASS**.

Preservation audit **PASS**: všech 42 baseline concept IDs, všech 135 původních
vztahů včetně confidence (povolena jen změna koncového řádku stejného symbolu) a
všech 286 historických episodes jako nezměněné záznamy zůstává zachováno. Kontrola
SHA-256 všech šesti finálních source/test/docs cest před/po samotné údržbě je
**PASS**; funkční blobs stále odpovídají nezávislému review výše.

Reprodukce preservation auditu:

```sh
python3 - <<'PYCODE'
import json, re, subprocess
from pathlib import Path
old = json.loads(subprocess.check_output(['git', 'show', '14d7f7c:.kgmaker/semantic.json']))
new = json.loads(Path('.kgmaker/semantic.json').read_text())
def key(edge):
    return (re.sub(r'::\d+$', '', edge['source']), re.sub(r'::\d+$', '', edge['target']),
            edge['kind'], edge['confidence'], edge['confidence_score'])
assert {n['id'] for n in old['nodes']} <= {n['id'] for n in new['nodes']}
assert {key(e) for e in old['edges']} <= {key(e) for e in new['edges']}
assert all(episode in new['episodes'] for episode in old['episodes'])
print('PASS: baseline semantic evidence and historical episodes preserved')
PYCODE
```


Závěrečné skutečné výsledky údržby (2026-11-15):

- `./kgmaker memory capture --base 14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8 --validation t027-review-repros=passed --validation semantic-preservation=passed --validation diff-check=passed --validation full-suite=skipped`: **PASS**, episode `0eb16126b0d8391369a38f50aebd3a8c125bb2d43849242e972c3b8f2b1bd59a`. Celkem 287 episodes, všech 286 původních zachováno beze změn.
- `./kgmaker scan`: **PASS**, 561 files / 5812 declarations/sections / 44025 relationships; semantic layer 330 concepts / 30264 relationships včetně historických a nové episode. Generated Markdown a Mermaid změněny výhradně tímto příkazem.
- `./kgmaker check`: **PASS**, graph documentation current (561 files / 6373 nodes / 44025 relationships).
- Preservation audit a kontrola šesti zmrazených funkčních cest po údržbě: **PASS**. Source/test blobs odpovídají review hodnotám výše.
- `git diff --check`: **PASS**. Worker symlinky jsou odstraněny. Full suite / HTTP runtime / remote CI: **NOT_RUN**; publikaci a finální review SHA zajišťuje parent.

Po tomto závěrečném textovém záznamu jsou generated views znovu obnoveny a
zkontrolovány stejnými příkazy; funkční source/test se již nemění. Tento lokální
krok neprohlašuje dokončení T004 ani merge/PR approval.


## Integrace po PR104 — T027-S01/S04/S05, AC01–AC06 (2026-11-15)

Výchozí schválený HEAD PR105 `82eef329261d8b65596cbb95ffd135f41fc4c685`;
skutečný main `ec05a329fe2e51dbfe0eb47888bed037a251b8bf` je potvrzený dvourodičový
merge PR104, shodný tree s reviewovaným W03 `1f2acec0`. PR101–104 jsou MERGED.
Příkaz `git merge --no-ff --no-commit ec05a329fe2e51dbfe0eb47888bed037a251b8bf`
zachovává historii bez rebase/force. Dodání T027 je PR_OPEN; samostatné review
nového integračního HEAD a autorizovaný merge zůstávají předáním reviewerovi.

Přímá rekognoskace dle kgmaker-context ověřila status/query/memory a skutečné
T027 guardy. Mezi větvemi není sdílený změněný funkční source soubor. Merge
nemění žádný funkční kód: T027 business_process.py a test jsou byte-identické
se schváleným rodičem, všech 28 main source/test/fixture souborů s main.
Zachovány jsou přesný caller REQUEST, normální RESPONSE, T014 version/stale/scope
kontroly i imported diagnostics/limits/truncation. Konflikt acceptance zachovává
obě T027/W06 sekce; semantic/generated konflikt řeší samostatný krok níže.

Aktualizovány change123, production progress a acceptance: W03/PR104 MERGED,
T027/PR105 PR_OPEN. README se sloučil automaticky; process-paths API, compiler,
runtime, cache a field-mapping příručky/CLI příklady jsou bez nové změny veřejného
chování a zachovávají své limity. Task registry/revize, schémata, worker protocol,
installed templates a absence nového T027 CLI jsou bez dopadu. Žádná cizí
rozpracovaná BE→FE/ranking změna nebyla převzata.

Přesný nový cílený běh (191 veřejných T027/T014/T025/T026 případů + 9 nezávislých
reviewer reprodukcí; poslední jsou již pokryté i versionovanými negativy):

```sh
ln -s /tmp/kgmaker-pr97-reconciled/workers/jvm/target workers/jvm/target
ln -s /tmp/kgmaker-pr97-reconciled/workers/jvm/target-k2 workers/jvm/target-k2
env JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
  PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH \
  KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 \
  KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers \
  PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 \
  /tmp/kgmaker-test-venv/bin/python -B -m pytest -q -rs -p no:cacheprovider \
  tests/test_t027_cross_http_process_boundary.py tests/test_t014_bind_remote_interfaces.py \
  tests/test_t025_build_local_process_path.py tests/test_t026_collapse_business_steps.py \
  /tmp/t027_review_repros.py
rm workers/jvm/target workers/jvm/target-k2
```

**PASS: 200 passed / 0 skipped, 10.76 s**. Skutečné Javac/K1/K2 fixture,
připravené worker artefakty, žádný nový worker build ani package install. Oba
nově vytvořené dočasné symlinky byly po běhu odstraněny. Source identity **PASS**.
Full suite, HTTP runtime observation a GH CI **NOT_RUN** dle pověření. Předchozí
běhy 187/38/200 zůstávají historické, nový výsledek se vztahuje k této integraci.

## Údržba evidence po integraci — T027-S05 / AC06 (2026-11-15)

Výchozí SHA jsou T027 `82eef329261d8b65596cbb95ffd135f41fc4c685` a main
`ec05a329fe2e51dbfe0eb47888bed037a251b8bf`. Konflikt semantic.json zachovává
aktuální main entries a existující doložený T027 koncept/tři vztahy. Episode
union kontroluje shodné objekty pod stejným ID; nic se nemaže. Aktuální scoped
patch obsahoval pět konceptů a 13 vztahů, bez removals, s reanchorem podle
source hashů správného rodiče a aktuálních jednoznačných graph declarations.
Generated GRAPH.md/mmd se řeší výhradně příkazem scan.

```sh
./kgmaker semantic update --base ec05a329fe2e51dbfe0eb47888bed037a251b8bf --note docs/changes/123_crossHttpProcessBoundary.md
./kgmaker scan --no-docs
# Source-backed patch používá aktuální update_id, remove_nodes/remove_edges prázdné.
./kgmaker semantic apply
./kgmaker semantic validate
python3 /tmp/t027-integration-preservation.py
./kgmaker memory capture --base ec05a329fe2e51dbfe0eb47888bed037a251b8bf --validation t027-integration200=passed --validation semantic-preservation=passed --validation source-identity=passed --validation full-suite=skipped
./kgmaker scan
./kgmaker check
git diff --check ec05a329fe2e51dbfe0eb47888bed037a251b8bf
git diff --check 82eef329261d8b65596cbb95ffd135f41fc4c685
```

Semantic apply/validate, preservation, source identity, capture a scan/check
**PASS**. První scan před reanchorem pravdivě hlásil 13 stale vztahů; finální
scan již žádné semantic entries nevynechává. Audit stejným algoritmem uvedeným
výše zachoval všechny koncepty, vztahy včetně confidence a přesné původní episode
objekty: baseline **42/135/286**, T027 **43/138/287**, main **44/141/297**.
Union před capture je **45/144/298**, po skutečné nové integrační epizodě
`5268f9476295d4ca07dd109437c0389cb7bc2cfb07b880c7ce382cd0ad522347`
celkem **45/144/299**. Všech 30 source/test/fixture souborů zachovává byte identity
vůči příslušnému rodiči. První diff check před dokončením generování hlásil
**FAIL** kvůli dosud nevyřešeným markerům v generated graphs; po command-generated
obnově a označení konfliktů za vyřešené jsou závěrečné oba diff checky **PASS**.

Po tomto textu jsou grafy znovu generovány a checknuty. README/API/CLI mají stejný
nulový funkční dopad jako integrační krok; aktuální progress/acceptance a tento
záznam uvádějí stav i skutečné výsledky. Full suite, HTTP runtime a GH CI
**NOT_RUN**. Nové review/merge PR105 zůstává nezávislým krokem nad přesným HEAD;
žádné vlastní APPROVE ani dokončení T004 se netvrdí.
