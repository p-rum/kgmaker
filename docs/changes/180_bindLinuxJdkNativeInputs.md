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
