# Kanonická reference na kontext v Kafka testu

## T003-S07-W04, kroky 1, 4 a 5, AC03 a AC04

Výchozí main je `16f2ba8c4d109957edc295feea80db86da7093f1`. Kafka test
porovnával neenkódovaný sufix původního compiler ID s kvalifikovanou
referencí ve workspace grafu. Verze raw JVM snapshotu používá ID
`jvm-raw-1:<otisk>`. Workspace publikuje kanonickou referenci tvaru
`repo:producer:jvm-raw-1%3A<otisk>`.

`tests/test_kafka_bindings.py` při ověření živého K1 i K2 kontextu volá
existující `workspace.split_id`. Test porovnává přesný repozitář a původní
ID. Parser současně ověří kanonický zápis. Kontroly redakce, nezměněných
bajtů uloženého producer grafu při projekci a stárnutí bez spuštění
workeru zůstávají součástí stejného testu.

Upravené [acceptance](../acceptance-inventory.md) a
[stavová matice](../production-analysis-progress.md) odkazují na cílené
ověření a zachovávají PARTIAL pro celý work package. Pro README,
Kafka capability návod, příklady CLI a registr zadání je dopad nulový.
Veřejné příkazy, schémata, rezervované znaky a význam důkazů zachovávají
dosavadní kontrakt.

### Kontroly

- RED na uvedeném main se skutečným OpenJDK 21 a K1/K2
  **2 FAIL / 0 SKIP**, exit 1. Obě selhání jsou na původním porovnání sufixu.
  JUnit SHA-256 `7c56b13c9c6523fc6020778292fb64ea1425a920842699cbd8542d30fdc15ad4`.

  ```bash
  KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 python -m pytest -p no:cacheprovider -q \
    tests/test_kafka_bindings.py::test_actual_captured_context_properties_and_offline_staleness
  ```

- GREEN pro stejné dva případy **2 PASS / 0 SKIP**, exit 0. JUnit SHA-256
  `1e56862b021aeac396ee557ad07c5c268e39d0102b718767cf0264b8afe309f9`.
- Zaměřená nativní sada **216 PASS / 0 SKIP**, exit 0 za 225,923 s.
  JUnit SHA-256 `f287c7020ea5d6f37ccca4912bb2d0156e80848d22751df87730a620ff7095c6`.

  ```bash
  KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 python -m pytest -p no:cacheprovider -q \
    tests/test_kafka_bindings.py tests/test_jvm_raw_source_snapshot.py \
    tests/test_workspace.py tests/test_t012_catalog_kafka_interfaces.py
  ```

- `kgmaker semantic update --base 16f2ba8c4d109957edc295feea80db86da7093f1`,
  `kgmaker semantic validate`, `kgmaker memory capture --base 16f2ba8c4d109957edc295feea80db86da7093f1`,
  `kgmaker scan`, `kgmaker status`, `kgmaker check` a `git diff --cached --check` prošly.
  Původní sémantické vazby zůstaly shodné. Graf byl obnoven příkazem.
- Kapacita runtime Kafka a produkční dostupnost zůstávají mimo rozsah.
  Úplná sada W02, Windows a GitHub Actions zde zůstávají NOT_RUN. Úplná
  brána W02 se spustí znovu po integraci proti aktuální dvojici base/head.
