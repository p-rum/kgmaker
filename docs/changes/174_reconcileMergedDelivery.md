# 174 — Doručení runtime importu, instalace a migrace Excelu

Výchozí `main` `5809e84932b1910bfc3f17c72e2a2005283389b1`.
Stavová matice a acceptance inventář evidovaly některé sloučené změny jako
otevřená PR. V [matici](../production-analysis-progress.md) a
[inventáři](../acceptance-inventory.md) je nyní skutečná revize dodání
oddělená od ověřeného rozsahu. Historické change notes zůstávají zachované.

## T003-S13-W02, kroky 2–5 a AC01–AC04

[#136](https://github.com/p-rum/kgmaker/pull/136) je sloučené jako
`5809e84932b1910bfc3f17c72e2a2005283389b1` se shodným stromem
`83becb8cf202fd89cc6e31d9e5e53772934b710b` proti schválenému headu
`3d4860136ded9be86d171de2ecdc653b9facc49b`. Nezávislé T045 schválilo tuto
dvojici před sloučením. Výsledek W02 je `MERGED / PARTIAL`. Uložené
pozorování dokládá ověřené dodané hodnoty v kontextu a variantě služby.
Přesné místo volání, původní typ receiveru a širší T003-AC13 zůstávají
neuzavřené. [Import a hranice](../runtime-trace.md) ·
[Záznam implementace](151_preserveRuntimeObservationEvidence.md) ·
[Schválení T045](https://github.com/p-rum/kgmaker/pull/136#issuecomment-7162583059)

Ověření schváleného stromu se skutečným JDK 21, Mavenem a workery Kotlin
K1/K2 mělo **173 PASS / 0 SKIP**. Standardní CPython 3.13.18 měl
**2 561 PASS / 1 332 SKIP / 1 očekávaný strict XFAIL**, exit 0.
Po ověření sloučeného `main` prošlo **104 PASS / 0 SKIP**, exit 0,
v níže uvedených modulech se skutečným JDK 21 a Mavenem. Shodný manifest
892 sledovaných cest má SHA-256
`09428f40b5e5a703f97b4f67240452dc16aed291efd208301f53678b711cdc7e`,
JUnit SHA-256
`115547ab360be40daa1e76ecf1cd0b751e081602d30c42221faa6d3d177045a1`.
Hostovaný compiler job ještě běžel při sloučení. Rozsah receiveru ani
přesné vazby na call site se tím neověřily.

```bash
KGMAKER_REQUIRE_WORKERS=1 python -m pytest -n 2 -p no:cacheprovider -q \
  tests/test_runtime_trace_producer.py tests/test_graph_publication_concurrency.py
```

## T053-S01–S04, AC01–AC04

[#154](https://github.com/p-rum/kgmaker/pull/154) je sloučené jako
`1e782a119e5ae54d22bfc8d7c22c565ed651815a`. Doložený lokální rozsah
zůstává `VERIFIED_IN_SCOPE`. Opravená větev a nezávislé T045 evidují
**133 PASS / 0 SKIP** včetně reálného instalovaného Linux wheelu.
Windows upgrade a uninstall, živý reload hostitelů a výpadek v průběhu
publikace souborů zůstávají NOT_RUN. Obecný Windows instalační smoke
pokrývá svůj vlastní rozsah.
[Instalační návod](../project-installation.md) ·
[Záznam implementace](170_manageProjectInstallation.md) ·
[Schválení T045](https://github.com/p-rum/kgmaker/pull/154#issuecomment-7141212040)

## T054-S01–S04, AC01–AC05

[#155](https://github.com/p-rum/kgmaker/pull/155) je sloučené jako
`782ac6ac0287550084e9afadbd6182756fdd2730`. Ověření před sloučením
zahrnovalo **137 cílených PASS** a skutečný Linux wheel s JDK 17.
Živé Jira Cloud a Windows v tomto ověření zůstaly NOT_RUN. Na následném
headu #136 `3d4860136ded9be86d171de2ecdc653b9facc49b` jsou workflow,
zdroje, testy, fixture a worker Excelu shodné s merge #155. Hostovaný
Windows job s povinným workerem a wheelem úspěšně sestavil worker Mavenem,
ověřil distribuci a dokončil `tests/test_excel_migration.py`.
T054-AC04 a AC05 zůstávají `PARTIAL`. Živé Jira Cloud je stále NOT_RUN a
Windows PASS dokládá testované fixture a distribuci.
[Návod k migraci](../excel-migration.md) ·
[Záznam implementace](171_addExcelMigration.md) ·
[Schválení T045](https://github.com/p-rum/kgmaker/pull/155#issuecomment-7161936197) ·
[Windows CI](https://github.com/p-rum/kgmaker/actions/runs/45613808138/job/139203894219)

## T003-S10-W01, AC01 a AC03

Dílčí oprava otisku Java launcheru a ochrany před jeho změnou je
sloučena v [#149](https://github.com/p-rum/kgmaker/pull/149) jako
`16f2ba8c4d109957edc295feea80db86da7093f1`. Ověřený POSIX běh zahrnuje
locale, `ct.sym` a zachování publikovaných výstupů při zjištěné změně.
W01 zachovává `PARTIAL`. Výkonový warm HIT zůstává otevřený v
[#116](https://github.com/p-rum/kgmaker/issues/116).
[Chování cache](../stage-content-cache.md) ·
[Oprava a testy](164_bindJavaLaunchInputs.md)

## T003 — historický inkrement P1/P8/P9

Úprava úvodu [production scope](../production-scope.md) potvrzuje, že
zdrojové commity [#4](https://github.com/p-rum/kgmaker/pull/4) jsou v
historii `main`. Dva navazující merge commity na historické větvi mají
shodný strom `0e999bbaf7390dd69bc3e63f879f8fb2165b77d7` s dostupným
`d9a89fe951157fe58d2592fa96631b21f3698301`.
Na `5809e84` prošlo **45 cílených PASS / 0 SKIP**, exit 0, pro produkční
klasifikaci a důkazní vrstvy. JUnit SHA-256
`bba85dd3ebe1ff3f3a91f6e615647bafdb5d105f3285751470b2d81e264a3043`.
Širší acceptance P1/P8/P9 sleduje aktuální zadání T003 a stavová matice.
[Historický záznam implementace](1_addProductionScope.md)

## T051-S02 a T052-S02, zdrojová čerstvost role packetu

Dopředný přenos inventáře vychází z `main`
`b04d064a6147436adc751f5fffa4a219b8f8c16e`. [#151](https://github.com/p-rum/kgmaker/pull/151)
je v něm skutečně sloučené se schváleným headem
`473841773a708e259bda33e93568581b5d03464d` a výsledným stromem
`b60ff57a1ae03ed7920bf4a23b3e88dcd54a5273`. Schválený strom má
**208 cílených PASS / 0 SKIP**, JUnit SHA-256
`5e4f31eea01523d8004711865704472a77ccfb7ddb31f49694f40048feee3ee0`.
Kontrola doložila stejnou zdrojovou inventuru i reakci na změnu bajtů
skutečných XLSX, šifrovaných XLSX a legacy XLS. Ověření proběhlo bez
parsování sešitů, spuštění procesu či přepsání grafu. Explicitní XLSM
má vlastní workflow T054. Ostatní ověřovací stavy T051 a T052 zůstávají
v dosavadním rozsahu.
[Návod a příklad packetu](../project-workflows.md#role-context-freshness) ·
[Záznam implementace](167_useCanonicalPacketSourceSnapshot.md)

## T055-S01–S03 a AC01–AC03

Dopředný přenos inventáře po [#156](https://github.com/p-rum/kgmaker/pull/156)
vychází z `main` `3a6b97fc9c44941e68bb390772a5eb13906bf1ff`. Merge má stejný
strom `d0398fbb8b41c72e09f5fc242e1b7f255a4eecb8` jako head
`3aae558631ac0f2e994b98b3b4a917dd2a20ef8b`. Change174 používá nové číslo,
protože publikovaný #157 již používá Change173.

Doručený rozsah je lokální příprava ze sešitů, výstup Markdown a Jira CSV
a distribuovaný skill. Opravené zdroje a testy T055 jsou ve sloučeném stromu
shodné s dříve ověřeným `1ab93541d89f1cfce3e873fab4fe26230e07fd1a`.
V místním scope je doloženo **172 cílených PASS** se skutečným Java 17
workerem a instalovaným Linux wheelem. Živý Copilot a živý Jira Cloud
import zůstávají NOT_RUN. Na dřívějším běhu #156 uspěly samostatné
Excel joby na Linuxu a Windows včetně balení workeru, ověření distribuce
a Excel pytest. Tento běh měl současně zelený pytest a selhání následného
`kgmaker check` v Python jobu 3.13. Souhrnný CI PASS pro #156 se nedokládá.
[Záznam implementace](172_automateExcelMigration.md) ·
[Excel Linux](https://github.com/p-rum/kgmaker/actions/runs/45617722148/job/139217362508) ·
[Excel Windows](https://github.com/p-rum/kgmaker/actions/runs/45617722148/job/139217362452) ·
[Python 3.13](https://github.com/p-rum/kgmaker/actions/runs/45617722148/job/139217362565)

## Ověření inventáře a kompatibilita

```bash
PYTHONPATH=src python -m pytest -p no:cacheprovider -q tests/test_completion.py
PYTHONPATH=src python -m kgmaker.cli completion plan --root .
```

- Cílené testy plánovače **7 PASS / 0 SKIP**, exit 0. JUnit SHA-256
  `6b61c3c3aa108bb86770ca04b0dce1b8bc30db5b962a45b6679ee8968561c469`.
- Přímý běh plánovače načetl všech 119 existujících řádků. Po změně má
  88 MERGED a 31 PLANNED. T003-S13-W02 zůstává dostupné pro další
  ověření, doporučený první úkol je T003-S10-W02.
- Úplná testovací sada a GitHub Actions pro tuto dokumentační změnu jsou
  NOT_RUN. Veřejné API, příklady CLI, README, ostatní capability návody a registr
  zadání mají nulový dopad, protože publikované chování, schémata a
  identita zadání zůstávají stejné.
