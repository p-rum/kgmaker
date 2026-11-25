# Menší náklady živé compiler inspekce

Související zadání [T003-S10-W01](../tasks/T003-S10-01-stageContentCache.md),
kroky 1–5, AC01–AC04, T003-AC10 a [#116](https://github.com/p-rum/kgmaker/issues/116).
Výchozí integrační revize je `0c834c8b2c06ca80d76f1aaf09f6f49b968e8aa3`.

## Krok 1 — výchozí náklady a hranice důvěry

Každá kontrola otisku launcheru načítala do paměti celý vybraný soubor.
JDK 21.0.6+7 použitý v Cloud Environment má `lib/modules` o velikosti
141 965 153 bajtů. Každý živý grafový stupeň znovu sestavoval stejný objekt
z již validovaného payloadu.

Vydavatel autentizovaného compiler výsledku zůstává předpokladem warm HIT.
Současný envelope ukládá payload a jeho SHA-256 do jednoho zapisovatelného
graph store. Běh compiler workeru dál dědí prostředí procesu, včetně
částí mimo stávající otisk launcheru. Například ELF launcher daného JDK
má závislost na `libjli.so`. Otisk dílčích souborů a živé ověření
zdůvodňují současný BYPASS. [Kontrakt cache](../stage-content-cache.md).

## Kroky 2 a 3 — živé ověření a kompatibilita

- `src/kgmaker/extraction_cache.py` průběžně hashuje stejné soubory
  launcheru při každé dosavadní kontrole. Při potížích se čtením vrací
  existující stav nedostupného otisku.
- `src/kgmaker/inspection.py` přebírá výsledek jediného ověření každého
  právě vypočítaného grafového stupně. Worker analyze, TypeScript project
  preflight, lokální projekce a kontroly přípravy i publikace mají své
  stávající role. Cache nadále publikuje původní serializovaný payload
  pod stávajícím klíčem kandidáta.
- Graph/store v1–v3, interní envelope v1 a odpověď CLI zachovávají
  své formáty. Aktuální inspekce vrací BYPASS i při opakovaném příkazu.

## Krok 4 — ověření

RED v Cloud Environment s Javacem 21.0.6, K1/K2 a TypeScriptem 5.7.3
na `3a6b97fc9c44941e68bb390772a5eb13906bf1ff` měl **4 FAIL** za 57,26 s,
exit 1. Jedna zkouška zachytila hromadné čtení souboru a tři nativní
případy zachytily dvojité ověření grafových payloadů. Oba produkční
soubory, worker transport a předchozí testové bloby jsou na integračním
základu `0c834c8b` strojově ověřené jako shodné.
JUnit SHA-256 `0416aea7f65638685075dbc3fe1b857d88ba26ea1982ab02a83e00916ee089a4`.

```bash
python -m pytest -n 2 --dist load -p no:cacheprovider -q --tb=short -ra \
  tests/test_stage_content_cache.py tests/test_stage_content_cache_actual.py \
  -k 'launch_capture_hashes_without_materializing or actual_jvm_cold_warm or actual_typescript_preflight'
```

Na stejném projektu, se stejnou cestou a skutečným Javacem, měly výchozí
i opravená inspekce shodný hash launcheru a publikovaných grafových faktů
bez času generování a cache. Obě provedly jeden handshake, jeden analyze
a 13 záznamů otisku launcheru. Počet kontrol živého grafového stupně
klesl ze čtyř na dvě. Všechny stupně hlásily
`BYPASS/UNVERIFIED_REPLAY`. `tracemalloc` naměřil pro samotný výpočet
otisku launcheru a platformy 141 971 317 bajtů špičkové Python alokace
na výchozím kódu a 269 244 bajtů po opravě. Jde o měření této operace.

GREEN na integračním základu `0c834c8b` má **89 PASS / 0 SKIP** za
183,01 s, exit 0. Zahrnuje změny classpath, TypeScript konfigurace, locale
a symlinku na launcher, odmítnutí neplatného živého compiler a framework
grafu, odmítnutí podvržených uložených kandidátů, souběh a rollback
publikace. Testy použily JDK 21.0.6+7, K1/K2 a TypeScript 5.7.3 s
`KGMAKER_REQUIRE_WORKERS=1` a `KGMAKER_REQUIRE_K2=1`.
JUnit SHA-256 `b79ee831edfe8cb92b07db6227a414e2f58b0628678cf4eb37e21c02cb60c55b`.
Oba manifesty 447 souborů mají shodný SHA-256
`5433a99b3382ff81b9d6a92b4f6e09fa6dc1c000d983bef5b2fdee35189f044d`.

```bash
python -m pytest -n 2 --dist load -p no:cacheprovider -q --tb=short -ra \
  tests/test_stage_content_cache.py tests/test_stage_content_cache_actual.py \
  tests/test_graph_publication_concurrency.py
```

## Krok 5 — příkazy a zbývající práce

```bash
kgmaker inspect code --root ./service --repo-id service --module core --source-set main --scope production
```

Použití a rozsah uvádí [README](../../README.md#obsahová-cache-explicitní-inspekce-t003-s10-w01),
[compiler capability](../compiler-inspection.md#obsahová-cache-inspekčních-stupňů-t003-s10-w01),
[kontrakt cache](../stage-content-cache.md), [stav](../production-analysis-progress.md)
a [acceptance inventář](../acceptance-inventory.md#t003-s10-w01--obsahová-cache-explicitních-inspekčních-stupňů).
Registr zadání používá existující T003-S10-W01 a jeho závislosti.
Pro warm HIT zůstává potřeba nezávisle ověřitelný doklad o vydání pro
konkrétní požadavek a přesný výsledek. Dalším předpokladem je úplný otisk
běhových vstupů. T003-S10-W01 je částečně ověřený.
V původním nativním předání měly úplná projektová sada, Windows a GitHub
Actions stav NOT_RUN.

## Přenos po sloučení #160 — kroky 4 a 5

Prvním rodičem je ověřený kandidát `d9aca195058a5ac876225dd32882a8d6baf092c6`,
druhým skutečný `main` `61cd97d90d7a342396da79e7c3c7401c3df2560e` se
stromem `1b64d5e3e7f730582d5fab38920b6bfa4d042dbe`.
Oba zdrojové soubory a oba testy W01 mají přesné bajty prvního rodiče.
Zdroj, testy a deklarace ověřené závislosti z #160 mají přesné bajty
druhého rodiče. Stav W02 je `MERGED/PARTIAL` a W03 se z plánovače
nevybírá. Kontrolní běh v dočasné kopii plánu uvolnil W03 po změně
jediného stavu W02 na `VERIFIED_IN_SCOPE`. [Rozsah #160](175_requireVerifiedDependencies.md).
Přenos uchoval všech 420 předchozích epizod obou rodičů a znovu vytvořil graf.

Historická úplná standardní sada patří k samostatnému `d9aca19` se
stromem `6a3bac80627c1962b767c5b03d0d82ce67af7280`. V CPython 3.13.18
prošlo **2 589 PASS, 1 345 SKIP a 1 očekávaný strict XFAIL** za 100,83 s,
exit 0. XFAIL je T047-S02
`test_comment_does_not_change_logical_identity`. JUnit SHA-256
`7ffe766136fcf674935a5832da4cf67a7725de74aa636b6496f209fd6ad6c1b1`.
Oba manifesty 900 sledovaných souborů mají SHA-256
`24ea93515c543bd81d1011ad412d0a7ec853217c84dad67f0a61431b34b84449`.

Čerstvý cílený běh společného stromu v Cloud Environment měl
**27 PASS / 0 SKIP** za 132,72 s. Použil JDK 21.0.6+7, K1/K2
a TypeScript 5.7.3. Pokryl grafovou shodu, živé odmítnutí neplatného
výstupu, cyklický launcher, locale, souběžnou publikaci a ověření
závislosti #160. Pytest, vytvoření manifestu a porovnání mají exit 0.
JUnit SHA-256 `e69062e54c0c8cbb916d49bf96d8d2e2449b06c75c99ffa21895ac4dcfb7496c`.
Shodné manifesty 564 souborů mají SHA-256
`556354012fb083b9bf348e0fa5c9487ce194d8677ee9b15b8b57606e0b7d2661`.
Samostatná kontrola skutečného inventáře a jedné změny v dočasné kopii
má exit 0 a SHA-256 výsledku
`895c4c708b80bf84f14a5eba7891e16530fe5dd33f4d72c35d1e0d546f19fbdf`.

```bash
python -m pytest -n 2 --dist load -p no:cacheprovider -q --tb=short -ra \
  tests/test_stage_content_cache.py tests/test_stage_content_cache_actual.py \
  tests/test_completion.py \
  -k 'test_completion or launch_capture_hashes_without_materializing or invalid_live_graph_stage or rehashed_cached_graph or late_source_mutation or actual_jvm_cold_warm or actual_typescript_preflight or actual_jvm_cyclic_launcher or actual_jvm_locale_drift or overlapping_real_workers'
```

Úplná sada společného stromu, Windows a GitHub Actions mají v tomto
předání stav NOT_RUN.
