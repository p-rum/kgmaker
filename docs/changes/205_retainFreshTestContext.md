# Zachování nezávislého testovacího JVM kontextu

27. listopadu 2026. [T003-S10-W02](../tasks/T003-S10-02-reverseDependencyIndexes.md),
kroky 1–5, W02-AC01 až AC04 a T003-AC10. Výchozí `main` pro nativní
ověření `675887aade744579a36e58b0f90822427afb4fde`. Oprava navazuje na
izolované změny vstupů z [#184](https://github.com/p-rum/kgmaker/pull/184).

## Krok 1 — reprodukce (AC01)

Ve fixture mají dva produkční moduly a třetí kontrolní modul vlastní
compiler kontext. Po změně signatury ve starém produkčním modulu ukáže
read-only report jediného doloženého historického volajícího. Explicitní
`inspect_jvm(..., publish=False)` úspěšně rozřeší nové volání ve vybraném
modulu. Při publikaci na výchozím kódu vyvolal nezávislý ověřený kontext
ve scope `test` výsledek `STALE` už před výměnou prvního výstupu.
Výchozí regrese měla 1 FAIL / 4 PASS / 0 SKIP, raw exit 1, JUnit SHA-256
`88aa5d74c3e76fb923afaff71288498292de3f18686532b6e37c297428d0e9c5`.

## Krok 2 — kompatibilita (AC02)

`src/kgmaker/graph_provider.py` používá stávající raw snapshot, model
zdrojových sad, compiler důkazy a atomickou publikaci s revizí CAS.
Formát graph/store i čtecí JSON report mají stejné schéma. Migrace
není potřeba.

## Krok 3 — kvalifikace testovacího kontextu (AC01, AC03)

Vybraný a vyřazovaný kontext musí být `production`. Zachovaný `test` musí
mít vlastní deklarovaný modul a výhradně vlastněné zdroje. Před publikací
se kontroluje shoda projektu, modelu, distribuce, třídní cesty a raw
vstupů, včetně nezávislosti zachované vrstvy na staré a nové vybrané vrstvě
i na vyřazovaném kontextu. Oprava podporuje explicitní publikující volání
Python API s `project_model` bez `build_context`, vlastního výběru `sources`
a bytecode výstupů. Stejný scope používá dosavadní pravidla.

Kontroly `scope`, workeru a neprázdného textového `id` probíhají před
použitím uložených údajů k rozhodnutí o oddělení kontextů. Tři cílené běhy
na předchozích rozpracovaných variantách samostatně reprodukovaly
`KeyError` pro chybějící `scope`, `AttributeError` pro `worker: null` a
`KeyError` pro chybějící `id`. Každý měl 1 FAIL / 0 SKIP a raw exit 1.
Oprava vrací typovaný `STALE` a zachovává uložený graf i revizi CAS.

## Krok 4 — nativní kontrola (AC01–AC03)

`test_actual_javac_preserves_fresh_control_during_production_peer_retirement`
porovnává zachované důkazy se stejným produkčním a s odlišným testovacím
scope. Ověřuje fyzickou změnu LF→CRLF po výměně prvního výstupu a obnovu
všech uložených bajtů. `test_actual_javac_rejects_unqualified_test_control_during_peer_retirement`
ověřuje změnu bajtů v `test` vstupu, společný modul, sdílený důkaz
s původní vybranou vrstvou, neznámého vlastníka a tři neúplné tvary
aktivního testovacího kontextu.

```sh
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 PYTHONPATH=src \
  python -m pytest -n 2 --dist load --maxschedchunk=1 -q --tb=short \
  -p no:cacheprovider -o tmp_path_retention_policy=failed \
  tests/test_reverse_dependency_index.py tests/test_graph_provider.py \
  -k 'fresh_control_during_production_peer_retirement or unqualified_test_control_during_peer_retirement or actual_jvm_isolated_stale_peer_publication_and_guards or retirement_after_mixed_owned_peer_changes or actual_jvm_overlapping_stale_peer_still_aborts or test_graph_provider'
```

**25 PASS / 0 SKIP / 0 FAIL**, raw exit 0, JUnit SHA-256
`e2b2c06d32e7dad1fa5e10a5d644ecc2241bfc545f7b6cdf12d91b94597e1b06`.
Cílený běh používá Linux, CPython 3.12.14, Temurin JDK 21.0.6+7, skutečný
Javac a připnuté K1/K2 workery. Manifesty 164 zdrojových a testovacích souborů
a 33 artefaktů JDK a JVM distribucí souhlasily. Běh patří zdrojovému stromu
`bccf449ddc01d3c395e31c0f442f4645f67bdb5e` nad `675887a`. Přenos na
`f7015b61473a0700d979157eeba271c480c21cb8` zachoval oba změněné soubory,
dotčené inspekční a store moduly i zdroje workerů bajtově shodné.
Úplná sada a nezávislé review přeneseného kandidáta mají při této přípravě
stav `NOT_RUN`.

## Krok 5 — použití a zbývající ověření (AC04)

Před změnou zachyťte všechny tři moduly pod stejným `project_model`. Po
změně `orders/src/main/java/Orders.java` spusťte
`kgmaker impact --evidence-only --format json orders/src/main/java/Orders.java`.
Vybraný produkční modul `shipping` pak obnovte explicitním voláním
`inspect_jvm`; oddělený testovací modul `qa` může zůstat zachovaný.

[README](../../README.md#selektivní-dopad-změněných-souborů-t003-s10-w02) ·
[Příklad Python API](../compiler-inspection.md#obnova-izolovaného-jvm-kontextu) ·
[Čtecí CLI](../stage-content-cache.md#selektivní-dopad-změn) ·
[Acceptance](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy) ·
[Stav](../production-analysis-progress.md).

W02-AC01 zůstává `PARTIAL`. Širší selektivní publikace do grafu a revizí,
sdílené moduly a publikační CLI s manifestem mají vlastní rozsah. Zahájení
W03 dál vyžaduje `VERIFIED_IN_SCOPE` pro W02.
