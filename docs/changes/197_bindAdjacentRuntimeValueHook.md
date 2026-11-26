# Přítomnost hodnoty s voláním SDK na následujícím řádku

26. listopadu 2026. [T003-S13-W03](../tasks/T003-S13-03-runtimeValueFlow.md),
kroky 1–5, AC01–AC04 a T003-AC13. Výchozí `main`
`044c461dc1c63367a50522261df70a375cccb492`, strom
`b5d1249df20e40ea81ad41561ace96c05636aa77`.

## Krok 1 — reprodukce

Dvě izolované kompilace skutečné Javac fixture se lišily jen řádkem volání SDK.
`javap` zachytil stejné instrukce ve stejném pořadí. SHA-256 výpisu instrukcí
`906569eef5032cb01e95e7c6fe172b26b3b97f6e4f5d99eeff9ed621cc204407`.
Původní kód prošel s oběma výrazy na stejném řádku. Na dvou řádcích
`produce_manifest` skončil `RUNTIME_VALUE_BINDING`, protože hledal zápis na řádku
SDK. Nativní regrese měla 1 PASS, 1 FAIL, 0 SKIP a raw exit 1. SHA-256 JUnit
`37adddd96d7a3d15cecd52a72d396fa441bfcceff3bdb85fa167b792b22436bc`.

První příprava vložila obě přiřazení do jedné třídy. Projekce totožných
vazeb mezi poli je sloučila a test skončil před požadovanou kontrolou.
Samostatně kompilované varianty potvrzují skutečný výsledek stejných
statických polí a stejné logiky aplikace.

## Krok 2 — zdrojová vazba

`runtime_value.py` zachovává původní výběr jediného zápisu na řádku hooku.
Teprve bez kandidáta na tomto řádku zkontroluje řádek bezprostředně před ním.
Zdrojový rozsah zápisu musí předcházet
hooku ve stejné metodě a souboru. Nadále se ověřuje přesná metoda SDK,
pořadí operací a pět operandů ze stejného bytecode artefaktu. Formáty v1–v4,
uložená identita dokladu i zdrojový řádek v SDK payloadu jsou kompatibilní.

## Krok 3 — import a živé čtení

Živý `data-check` odvodí řádek z přesného uloženého compiler hooku a stejnou
validací potvrdí původní zápis i argumenty. Import používá stávající CAS.
Schválené mapování a platný čas umožní nejvýš `PARTIAL/UNASSESSED` pro jeden
běh. `ABSENT`, obyčejný call nebo prošlá evidence ponechají `UNKNOWN`.

## Krok 4 — kontroly

Samostatně kompilované varianty obou umístění SDK prověřily běžnou v4 capture,
offline import, `data-check`, call-only/ABSENT a poslední platné výstupy po
pozdní změně zdroje. Další případy ověřily kompatibilitu runtime v1, v2 a v3
a původní pravidla živé dostupnosti.

```sh
KGMAKER_REQUIRE_WORKERS=1 python -m pytest -q --assert=plain -p no:cacheprovider --tb=short \
  tests/test_runtime_value_presence.py tests/test_availability.py \
  tests/test_runtime_trace_producer.py::test_actual_jdk21_application_observes_all_four_kinds_and_no_values \
  'tests/test_runtime_trace_producer.py::test_jdk21_interface_dispatch_binds_concrete_receiver_and_call_site[alpha]' \
  tests/test_runtime_trace_producer.py::test_runtime_keeps_callable_and_framework_observations_and_legacy_import
```

Cílený běh měl **23 PASS / 0 SKIP / 0 FAIL**, raw exit 0 a 122,96 s.
Použil CPython 3.12.14, Temurin JDK 21.0.6+7, Javac 21.0.6 a připnutou
distribuci workeru. Otisky zdrojů, fixture a workerů se během běhu nezměnily.
SHA-256 JUnit `1869cb788cc49e1e443b9fb25f2a1b35190eb856abcc707f77d32fa7c195cddc`.
SHA-256 manifestu vstupů `18012930446c46e900ed8af5442c29e708416e01f0bd226bd9e3cf9bd288cd97`.
Úplná sada, hostované CI a Windows mají pro tento místní běh stav `NOT_RUN`.

## Krok 5 — použití a hranice

[README](../../README.md), [příklad capture](../runtime-trace.md#přítomnost-hodnoty-po-přímém-přiřazení-v-javě),
[živá kontrola](../feature-analysis.md#runtime-presence-in-data-check),
[acceptance](../acceptance-inventory.md) a [stav](../production-analysis-progress.md)
zaznamenávají omezený rozsah. CLI přepínače i parametry zůstávají beze změny.
W03 je nadále `IN_PROGRESS / PARTIAL`. Další instrukce, typy, instanční pole,
vícekrokové cesty a trvalé business závěry mají vlastní acceptance.

## Krok 6 — integrace po #180

První rodič `18d46e8d1cee1b7d669b62bd953574809f4a6fe3` se skládá s `main`
`c4a1edb59f140faeafba0d5e979023bba185f3f1`. Validátor, fixture a komentář
SDK mají stejné bajty jako první rodič. Kanonické záznamy [T025 a T043 po #176](192_recordLocalProcessContextMerge.md),
[T034 po #180](196_recordProcessRenderMerge.md) a W02 po #178 pocházejí z `main`.
Stav S13-W03 zůstává `IN_PROGRESS / PARTIAL`. Výsledky z kroku 4 patří
prvnímu rodiči. Opakované nativní ověření a úplná sada nad složeným stromem
mají při této přípravě stav `NOT_RUN`.
