# Otisk nativních knihoven JDK na Linuxu

[T003-S10-W01](../tasks/T003-S10-01-stageContentCache.md), kroky 1–5,
AC01–AC04, T003-AC10 a [#116](https://github.com/p-rum/kgmaker/issues/116).
Výchozí `main` `ec95f1ee1c3400cf90e79c45950a4da339a4998a` po #162.

## Krok 1 — skutečné běhové vstupy

Explicitní inspekce v Cloud Environment s Linuxem a JDK 21.0.6+7
při `--java-release 17` vrátila jednu hranu s `JAVAC_ATTRIBUTED_SYMBOL`,
tři fáze `BYPASS/UNVERIFIED_REPLAY` a exit 0. Diagnostika glibc
`LD_DEBUG=libs,files` zachytila inicializaci `lib/libjli.so` a dynamické
načtení a inicializaci `lib/server/libjvm.so` v Java procesech inspekce.
SHA-256 výřezu loaderu je
`eb627bda3566dba5867277a88e9c3d08e895fe4dff91c85a1e89b23363ac439e`.
Při změně bajtů každé knihovny v samostatné nespustitelné kopii zůstal
původní otisk shodný. Kontrola měla exit 1 a JSON SHA-256
`eef670464a8b8b1dee7d75c8dec57b69520620198bb2c63f8a8eb2ab39db17fa`.

## Kroky 2 a 3 — vazba otisku a publikace

`src/kgmaker/extraction_cache.py` používá pro obě knihovny na Linuxu
stávající průběžné SHA-256. Cesty vycházejí z adresáře skutečného Java
launcheru po rozlišení symbolického odkazu. Obsah knihovny vstupuje do
existující mapy `launch.files`. Jiné platformy používají svůj dosavadní
seznam. Graph/store v1–v3, interní envelope v1 a odpověď CLI zachovávají
stejné formáty. Stávající offline cesty a pravidla publikace se používají
i s rozšířenou mapou souborů.

Chybějící nebo nečitelná knihovna znamená
`BYPASS/INCOMPLETE_INPUT_CLOSURE`, pokud živá inspekce uspěje. Zjištěná
změna dříve známého otisku při inspekci vyvolá `STALE` se zachováním
posledního platného grafu. Stabilní dostupný otisk ponechává živou inspekci
v režimu `BYPASS/UNVERIFIED_REPLAY`.

## Krok 4 — ověření

Na výchozím kódu mělo 9 cílených regresí očekávané **FAIL** a 2
kontroly **PASS**, exit 1 za 14,79 s. Dvě varianty se skutečným Javacem
dokončily kontrolu locale a zachování grafu a selhaly až na chybějící
knihovně v uloženém otisku. Ostatní regrese zjistily, že původní kód
použil `UNVERIFIED_REPLAY` při chybějícím nebo nečitelném vstupu a po
změně knihovny dokončil publikaci.
JUnit SHA-256 `4f3e7a9b39debb8148552960a710e1f1234584f39dfee45e90a6af7c9324eb7c`.

Po opravě stejná kontrola izolovaných kopií potvrdila změnu otisku
pro oba soubory a obnovu stejného otisku po vrácení stejných bajtů.
Exit 0, SHA-256 JSON
`3c67a67646937882e8fcffd0f4a57fda0d1512d6ecbe62dc7e6a5612c05dd952`.
Změněné kopie se nepouštěly. Širší sada W01 a souběžné publikace měla
**96 PASS / 0 SKIP** za 79,85 s v CPython 3.13 se skutečným Javacem,
K1, K2 a TypeScriptem. Zahrnula reálné uložené otisky obou knihoven,
`STALE` po změně inertního vstupu, zachování publikovaných bajtů,
chybějící i nečitelný vstup a simulaci mapy souborů platformy mimo Linux.
Pytest, vytvoření manifestu a jeho porovnání mají exit 0.
JUnit SHA-256 `c8a80c9f402e7fb6cac4417f3c0bb2c0f4e6475b058854ce0225e4720019d377`.
Shodné 452řádkové manifesty zdrojů a nástrojů mají SHA-256
`06b3a7b9f0c60459cdb879ca31b4620286962a787d8fb08fddecc748da2d877a`.

```bash
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData \
  python -m pytest -n 2 --dist load -q --tb=short -ra -p no:cacheprovider \
    -o tmp_path_retention_policy=failed tests/test_stage_content_cache.py \
    tests/test_stage_content_cache_actual.py tests/test_graph_publication_concurrency.py
```

## Krok 5 — použití a hranice

```bash
PATH="/opt/jdk-21/bin:$PATH" kgmaker inspect code --root ./service --java-release 17
```

[README](../../README.md#obsahová-cache-explicitní-inspekce-t003-s10-w01),
[compiler capability](../compiler-inspection.md#obsahová-cache-inspekčních-stupňů-t003-s10-w01),
[kontrakt cache](../stage-content-cache.md), [inventář](../acceptance-inventory.md#t003-s10-w01--obsahová-cache-explicitních-inspekčních-stupňů)
a [stav](../production-analysis-progress.md) uvádějí ověřený rozsah.
Identita zadání a jeho závislosti zůstávají v existujícím registru.
Úplná standardní sada, skutečný běh mimo Linux a GitHub Actions mají při
předání stav `NOT_RUN`. T003-S10-W01 zůstává `PARTIAL`. Persistentní warm HIT
vyžaduje nezávisle ověřitelný doklad vydavatele a úplné vymezení běhových
vstupů. Toto ověření pokrývá dvě knihovny standardního rozložení JDK na Linuxu.

## Přenos po sloučení #158 — kroky 4 a 5

První rodič je `f70b5b4449887fa49bd6ee74d2d34e4f46a879eb` se stromem
`b991e32a07b85b02272b3ba0c081521874081e93`. Druhý je skutečný `main`
`e55bff02774aeee8f10d43c9e59895915311376e` se stromem
`54033f542d824b01b8800766d84fc994c1d76281`. Všechny soubory zdrojů, testů,
fixtures a workerů mají shodné bajty s prvním rodičem, včetně tří souborů
ověřených v předchozí sadě s 96 PASS. Rozsah a záznam #158 mají shodné
bajty s druhým rodičem. Jeho stavová matice a acceptance inventář přidávají
jen odkazy a výsledky W01 v tomto rozsahu. Regenerace uchovala všech 437
historických epizod obou rodičů. [Změny inventáře #158](174_reconcileMergedDelivery.md).

Čerstvá cílená sada společného stromu má **27 PASS / 0 SKIP** za 88,99 s.
Použila skutečné Javac 21.0.6+7, K1, K2 a TypeScript. Pokryla obsah nativních
knihoven, nedostupný otisk, `STALE` se zachováním uložených bajtů, živou
opakovanou inspekci s BYPASS a skutečný plánovač. Pytest, vytvoření
manifestu a porovnání mají exit 0. JUnit SHA-256
`91cb35dc3feb32ba88b8c9fec559951f6e956b6777c3ec32480403ce78031d25`.
Shodné 572řádkové manifesty zdrojů, nástrojů a vstupů plánovače mají SHA-256
`b0dfde39035fc732f545e71b74020b3f293cf8c9a9a2a79a16067e913b46ed8f`.
Samostatná kontrola plánu má exit 0 a SHA-256
`39edc3e9ef326dabdea5fa2fb02f83f5273bd58dd633688c07c07721bc0c1f16`.
Načetla 119 položek, z toho 90 `MERGED` a 29 `PLANNED`. W01, W02,
T047-S02 a import runtime T003-S13-W02 zůstávají `MERGED/PARTIAL`.
W03 stále čeká na `VERIFIED_IN_SCOPE` pro T003-S10-W02.

```bash
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData \
  python -m pytest -n 2 --dist load -q --tb=short -ra -p no:cacheprovider \
    -o tmp_path_retention_policy=failed tests/test_stage_content_cache.py \
    tests/test_stage_content_cache_actual.py tests/test_completion.py \
    -k 'test_completion or launch_capture_hashes_without_materializing or launch_capture_binds_linux_native_library or non_linux_java_launch or unavailable_java_launch_input or java_native_library_change_after_analysis or actual_jvm_locale_drift_preserves_published_generation or actual_jvm_cold_warm or actual_typescript_preflight'
```

Úplná standardní sada společného stromu, skutečný běh mimo Linux a GitHub
Actions mají v tomto předání stav `NOT_RUN`. Warm HIT zůstává otevřený v #116.

## Přenos po sloučení #163 — kroky 4 a 5

První rodič je publikovaný kandidát `0b3d4807a1b945ce6c6b187114ae46e4d6b8705b`,
druhý skutečný `main` `68e53af6587ce3535612234b0d78aa999a4e68ad` se stromem
`f2b6bde185f087531d562f11906c7b1fdfa4aaac`. Otisk W01 a jeho dva testovací
soubory mají shodné bajty s prvním rodičem. Implementace, testy a dokumentace
Kafka katalogu z #163 mají bajty druhého rodiče. Společné README a oba
inventáře obsahují přesné sloučení obou rodičů. Zachovali jsme 441 historických
epizod před regenerací grafu. [Change179](179_validateKafkaProjectModelFiles.md).

Cílená sada společného stromu má **29 PASS / 0 SKIP** za 69,19 s.
Použila skutečné Javac 21.0.6+7, K1, K2 a TypeScript a připravené Spring a Kafka
závislosti s kontrolovanými JAR/POM otisky. Vedle obsahu nativních knihoven,
`STALE`, `BYPASS`, nedostupných vstupů a plánování pokryla Kafka katalog
s Kotlin aliasem a odmítnutí změny LF→CRLF při ověřování vybraného file node.
Pytest, vytvoření manifestu, porovnání a samostatná kontrola plánu mají exit 0.
JUnit SHA-256 `1b697b670a15ede36dcd19ad929747aba4c72b7e58a6eba7da02a1a556efd833`.
Shodné 597řádkové manifesty mají SHA-256
`0133aecb54d71ee8de570dc12c503826e215728102cae7edd9405b289ef40108`.
Plán zachovává 119 položek, z toho 90 `MERGED` a 29 `PLANNED`.
W01, W02, T047-S02, import runtime T003-S13-W02 a T012 zůstávají `MERGED/PARTIAL`.
W03 čeká na ověření W02. SHA-256 výřezu plánu je
`770e86e82e7dfde49bb40cae1ddffd2719aad238a75b6e054343ba7772a83676`.

```bash
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData \
  python -m pytest -n 2 --dist load -q --tb=short -ra -p no:cacheprovider \
    -o tmp_path_retention_policy=failed tests/test_stage_content_cache.py \
    tests/test_stage_content_cache_actual.py tests/test_completion.py \
    tests/test_t012_catalog_kafka_interfaces.py \
    -k 'test_completion or launch_capture_hashes_without_materializing or launch_capture_binds_linux_native_library or non_linux_java_launch or unavailable_java_launch_input or java_native_library_change_after_analysis or actual_jvm_locale_drift_preserves_published_generation or actual_jvm_cold_warm or actual_typescript_preflight or actual_kafka_catalogue_preserves_kotlin_compiler_symbol_alias or actual_kafka_catalogue_preserves_file_mirror_for_selected_project_model'
```

Úplná standardní sada společného stromu, skutečný běh mimo Linux a GitHub
Actions mají při tomto předání stav `NOT_RUN`. Warm HIT sleduje #116.

## Přenos po sloučení #161 a #159 — kroky 4 a 5

První rodič je publikovaný kandidát `6be6d60e3f17affed38c4a7029dedf5fcf2032bc`,
druhý skutečný `main` `5ff2c0846056353605ccb9ab271bd86847c6e661` se stromem
`aa395d1ebe8dcf55b4173a520a6f4e43e26780ab`. Zdroje a testy W01 mají bajty
prvního rodiče. Produktové soubory, testy a dokumentace Excelu mají bajty
druhého rodiče. Přenos zachoval oba publikované dokumenty Change178,
implementaci a testy Kafka z #163 a 442 historických epizod obou rodičů.
Společné README a oba inventáře jsou přesným sloučením obou rodičů.
[Change176](176_readVmlLineBreaks.md), [Change177](177_extractExcelBehavior.md),
[Excel Change178](178_fixExcelBehaviorLineage.md),
[Compiler Change178](178_reduceLiveInspectionOverhead.md).

Úplná standardní sada původního kandidáta `6be6d60` v CPython 3.13.18 má
**2 604 PASS, 1 359 SKIP a 1 očekávaný XFAIL** za 105,79 s, exit 0.
XFAIL patří testu T047-S02 `test_comment_does_not_change_logical_identity`.
JUnit SHA-256 `31f7a8f279ec613184bfd9c43ab18372e4feeb959228bf7757b92cd3c306172e`.
Shodné manifesty mají SHA-256
`aef4c08b6dbdc3aadfc0931a2cb0e5f4b88805f6f91fca2b217f5ff640482ee2`.

Čerstvá cílená sada společného stromu má **35 PASS / 0 SKIP** za 75,02 s.
Skutečné Javac 21.0.6+7, K1, K2 a TypeScript ověřily otisky nativních
knihoven, změnu cesty launcheru na cyklický odkaz, `STALE` s obnovou
výstupů a živý BYPASS. Sada znovu ověřila Kotlin alias a řízenou změnu
LF→CRLF v Kafka katalogu. Přidala tři Pythonové kontroly extrakce chování
a toku hodnot a kontrolu instalovaného Excel skillu. Pytest, vytvoření a
porovnání manifestu a samostatná kontrola plánu mají exit 0. JUnit SHA-256
`2807a6c8ba5e81d30cc6a408beeed6ec5ed5d06ddcb845fb4bb63f8ca20afacf`.
Shodné 604řádkové manifesty zdrojů, plánovacích vstupů a nástrojů mají SHA-256
`d7b5849280774864d30ca3210354daef9bed07d0e4f1caf1a70da42d18cc8828`.
W01, W02, T047-S02, runtime T003-S13-W02 a T012 zůstávají `MERGED/PARTIAL`.
W03 čeká na ověření W02. SHA-256 výřezu plánu
`770e86e82e7dfde49bb40cae1ddffd2719aad238a75b6e054343ba7772a83676`.

```bash
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData \
  python -m pytest -n 2 --dist load -q --tb=short -ra -p no:cacheprovider \
    -o tmp_path_retention_policy=failed tests/test_stage_content_cache.py \
    tests/test_stage_content_cache_actual.py tests/test_completion.py \
    tests/test_t012_catalog_kafka_interfaces.py tests/test_excel_migration.py \
    tests/test_skills.py \
    -k 'test_completion or launch_capture_hashes_without_materializing or launch_capture_binds_linux_native_library or non_linux_java_launch or unavailable_java_launch_input or java_native_library_change_after_analysis or actual_jvm_locale_drift_preserves_published_generation or actual_jvm_cold_warm or actual_typescript_preflight or actual_kafka_catalogue_preserves_kotlin_compiler_symbol_alias or actual_kafka_catalogue_preserves_file_mirror_for_selected_project_model or actual_jvm_cyclic_launcher or test_vba_behavior_tracks_http_response_calculation_and_alternative_assignments or test_vba_function_lineage_follows_returns_instead_of_unrelated_effects or test_vba_non_mutating_intrinsic_preserves_definition_for_later_write or test_init_installs_complete_skills_and_local_references'
```

Úplná standardní sada nového společného stromu, nativní Excel worker,
skutečný běh mimo Linux a GitHub Actions mají v tomto předání stav `NOT_RUN`.
Warm HIT sleduje #116.
