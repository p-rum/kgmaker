# Omezení HTTP přílohy vztahových pohledů

Výchozí strom pro první cílené ověření této dílčí změny T043 je
`e63a82176623af8f6cd768868c282ac272749a6d` (tree
`baf5f1269478db19d591a97d75391d2342caa159`). Dříve sloučené meze
CFG a zdrojových diagnostik mají vlastní doklad v [Change189](189_reduceBoundedCfgTraversal.md)
a [záznamu sloučení #173](192_recordLocalProcessContextMerge.md#t043--sloučené-omezení-toku-a-diagnostiky).
[Zadání T043](../tasks/T-043_bound-view-performance.md)

Přenos vychází ze skutečného sloučení [#202](https://github.com/p-rum/kgmaker/pull/202)
`b9ad22ed558412c017eb35000ac6b6b4a04f7eb1`, strom
`2ae272a66516e8c6a22d1ec5cc3c0802b1d316ac`. Ověřený zdroj a test mají
v přenosu stejné Git bloby jako při cílených kontrolách.

## T043-S02 — meze vztahového reportu

V pohledech `integrations` a `data-flow` mohl `http.requests`
překročit 256 položek i při nízkém limitu viditelných uzlů. Společná
finalizace v [flow_report.py](../../src/kgmaker/flow_report.py) uchová
prvních 256 položek v dosavadním kanonickém pořadí identifikátorů
vybraného scope a kontextu. Ponechané řádky mají původní hodnoty
a původní odkazy na důkazy.

Při překročení přidá finalizace do `coverage.gaps` jednu položku
`FLOW_HTTP_ANNEX_LIMIT` s hodnotou `max_requests` 256, počtem
`omitted_requests` a polem `omitted_request_ids_sha256`. Otisk je
SHA-256 kanonického UTF-8 pole JSON s vynechanými ID v původním pořadí.
Stejná mezera je v metadatech JSON, Mermaid i Markdownu a přetrvá po
opakované finalizaci. U nejvýše 256 položek zůstává výstup bajtově
shodný. Meze `--max-nodes` a příznak `truncated` si zachovávají
význam pro uzly a hloubku. Existující vztahové pořadí
`RELATIONSHIP_ONLY` a dostupné důkazy mají původní význam.

Finalizace ověří strukturu vynechaného řádku i jeho serializovatelnost
před zveřejněním. Neplatný řádek za limitem přeruší publikaci a uložený
platný report zůstane zachovaný. Změna se týká výstupního reportu.
Dosavadní úložiště, verze schématu i čtení starších grafů zůstávají
použitelné bez migrace.

## T043-S04 — cílené ověření

Testovací fixture je syntetický graf schema 3 s HTTP záznamy v obráceném
pořadí a se záznamem mimo zvolený scope. Původní přímá kontrola se
256 a 257 položkami v každém pohledu skončila s raw exit 1. Při
257 položkách zůstalo v obou pohledech všech 257 řádků. Po změně prošly
všechny čtyři kombinace, raw exit 0. Oba pohledy mají při 257 položkách
stejnou očekávanou stopu pro jediné vynechané ID. Všech šest
srovnávaných výstupů na hranici 256 položek má stejné bajty před a
po změně. SHA-256 výsledného JSON měření
`3d416c3a0ff9d41b712ab831da6013671e6da0e452b15aaf6f9bf333b3057b38`.

Na výchozím stromu s přidanými testy a původním produkčním zdrojem měla
cílená regrese **6 očekávaných FAIL / 3 PASS / 0 SKIP**, raw exit 1.
Selhaly kontroly prefixu v obou pohledech, samostatného omezení přílohy
a odmítnutí neplatného záznamu ve všech třech formátech. Kontroly
hodnoty NaN už původně procházely. SHA-256 JUnit
`49cb81260f10ab7a51c66ac22d44861e524c8b8897bcb99167043b247170a41a`.

Poté v CPythonu 3.13.18 prošlo **126 cílených testů / 0 SKIP**,
raw exit 0. Dvě nativní kontroly zůstaly nezvolené. Otisky 964
sledovaných souborů před a po každém pytest běhu byly shodné.
Kontrola `git diff --check` prošla. SHA-256 zeleného JUnit
`99de3ecc021c43135f97230420783ff3fc11c0d462c8cd6aca3a4b5bce940b37`.

Samostatná pozdější kontrola zmrazeného zdroje použila skutečný Mermaid
11.4.1 a jsdom 26.0.0. Z fixture s 257 záznamy a `max_nodes=1`
ověřila v obou pohledech 256 řádků a očekávaný počet i otisk jediného
vynechaného ID. Parser načetl oba diagramy a renderer vytvořil oba
SVG, každý s jedním vrcholem. Node skončil s raw exit 0. Vnější
spouštěč oznámil exit 1. Samostatná kontrola ověřila raw exit, oba
SVG, deset SHA-256 položek manifestu a shodné otisky zdroje před a po.
SHA-256 dokladu je
`0ab9b0a24965b5d85a534560617e1680b4b9a6b095231778caafb0611410f43d`.

| Kritérium | Výsledek v tomto výřezu |
|---|---|
| T043-AC01 | PARTIAL. `test_t043_bounds_http_annex_in_all_relation_formats` ověřuje prefix a limit 256, samostatný očekávaný otisk dvou vynechaných ID a shodná metadata tří formátů. `test_t043_http_annex_overflow_is_not_node_truncation` ověřuje limit přílohy při 258 zobrazených uzlech. |
| T043-AC02 a AC03 | Výkonnostní ověření této přílohy má stav NOT_RUN. Dřívější případy a relativní benchmark topologie a CFG zůstávají doložené v [Change189](189_reduceBoundedCfgTraversal.md). |
| T043-AC04 | PARTIAL. `test_t043_http_annex_cannot_hide_invalid_omitted_rows` kontroluje neplatný řádek i hodnotu NaN za limitem ve všech třech formátech a zachování vstupu, adresáře a posledního platného souboru. |
| T043-AC05 | PARTIAL. `test_t043_bounds_http_annex_in_all_relation_formats` ověřuje přesný obsah ponechaných řádků, vyloučení cizího scope, zachování stavu pokrytí a shodu opakované finalizace. |
| T043-AC06 | PARTIAL. Cílené zdrojové ověření a dokumentace jsou doložené. Samostatný zdrojový test parseru a SVG má výsledek 2 PASS. Úplná sada a nativní případy Javac a frontend mají pro tento zdrojový výřez stav NOT_RUN. |

### Reprodukce pytest

Spusť z kořene checkoutu s místními testovacími závislostmi. První příkaz
je záporná kontrola na výchozím zdroji pouze s testovací změnou. Druhý
spusť se zdrojovou i testovací změnou.

```bash
export PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export PYTHONPATH="$PWD/src"
t043_http_tmp=$(mktemp -d)
python -B -m pytest -q --assert=plain -p no:cacheprovider \
  tests/test_t043_bound_view_performance.py -k http_annex \
  --basetemp="$t043_http_tmp/red" --junitxml="$t043_http_tmp/red.xml"
python -B -m pytest -q --assert=plain -p no:cacheprovider \
  tests/test_t043_bound_view_performance.py tests/test_unified_flow_views.py \
  -k 'not actual' \
  --basetemp="$t043_http_tmp/green" --junitxml="$t043_http_tmp/green.xml"
git diff --check
```

## T043-S05 — dokumentace a stav

[Návod k pohledům](../unified-flow-views.md) a [README](../../README.md#unified-flow-reports)
popisují hranici reportu a pole počtu a otisku. [Acceptance](../acceptance-inventory.md#t043--limity-velikosti-a-výkonu-pohledů)
a [stavová matice](../production-analysis-progress.md) ponechávají T043
ve stavu PARTIAL. Zbývá ověření limitu vazeb návratové hodnoty, širších
strukturálních mezer a diagnostiky a souhrnného rozpočtu bajtů reportu.

Při složení na výchozím stromu po #202 prošlo 13 testů plánovače bez
přeskočení, raw exit 0. Plán zachoval 135 položek, všech 32 pozic výběru
a přísnou závislost S10-W03 na ověřeném S10-W02. Kontroly sémantiky,
opakovaného zachycení a grafu vrátily raw exit 0. Graf zachoval
524 doslovných epizod a přidal jednu epizodu tohoto kroku. Ve dvou
existujících vztazích se posunuly lokátory `finalize` a `publish`
podle jejich identit v novém scanneru. Obsah 60 kurátorovaných konceptů
a 222 vztahů zůstal doložený. Kontrola zachovala také 674 importních
vztahů, 3 uzly a 275 vztahů sešitu Rates i bajty repozitářového diagramu.
Nativní zkoušky přesného kandidáta a úplná sada mají v této fázi stav
NOT_RUN.
