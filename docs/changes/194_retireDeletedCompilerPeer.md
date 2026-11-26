# Vyřazení izolovaného JVM kontextu po smazání vstupu

26. listopadu 2026. [T003-S10-W02](../tasks/T003-S10-02-reverseDependencyIndexes.md),
kroky 1–5, W02-AC01 až AC04 a T003-AC10. Výchozí `main`
`0b922c00bfe7ebe57f07bf7dfdee7e8ab746318a`, strom
`9abca3e7bb81c79b17e1a035a0790794b2b6aa78`.

## Krok 1 — reprodukce

Tři explicitní zdrojové sady mají platný compiler kontext. Po smazání
zachyceného `edited/src/main/kotlin/Example.kt` report uvádí pouze dříve
doložený volající `Caller.kt`. `inspect_jvm(..., publish=False)` rozřeší
nové volání ve vybraném modulu. Publikace na výchozí revizi vrátí `STALE`
a zachová původní generaci. Obě nativní regrese nad výchozím produkčním
kódem selhaly očekávaným předčasným `STALE` před výměnou výstupů. Kontrola
překryvu v témže běhu prošla. SHA-256 JUnit je
`c8f03c597be6310a1a0e179e523624cce91a1bdbb84e134e53b9d49d69a843b4`.
Opakovaná sonda na přesných zdrojích `0b922c0`, s aktuálními worker buildy
a Temurin JDK 21.0.6+7, potvrdila jeden nový rozřešený call site v obou
backendových variantách a `STALE` při publikaci se shodným store. SHA-256
sond je `3e90ff35fa065515c60394ec26c82526e9a60d9d78614d087879dfc8ba632b20`
pro K1 a `11ccd0f37d901d4dc5832e465618eede33011d8e1d5a751eda4e352c0cd98752`
pro K2.

## Kroky 2 a 3 — vlastnictví a atomická publikace

`graph_provider.py` připustí zmenšený raw snapshot, pokud všechny změny
tohoto modulu tvoří výhradně fyzicky chybějící původní compiler vstupy.
Každá cesta musí být stále přímo uvedená v `files` nezměněného modelu,
mít jediného vlastníka a v uložené generaci souhlasit s výhradní
klasifikací souboru a otiskem zachyceného vstupu. Větev používá dosavadní
kontroly oddělené classpath, kontextů a důkazů. Odebere staré compiler fakty
a cache daného modulu. Jeho záznam `STALE` uvede smazané cesty.

`inspection.py` znovu ověří fyzickou nepřítomnost při stávající CAS
publikaci a při návratu vstupu obnoví předchozí výstupy. Překryv,
nedostupná nebo symlinková cesta, přidání vstupu nebo současná změna
konfigurace neposkytnou doklad odstranění. Totéž platí pro nově přidaný
deklarovaný soubor, který scanner vynechal kvůli neplatnému kódování.
Původní pravidla pro samotnou změnu bajtů a formáty graph/store zůstávají
kompatibilní.

## Krok 4 — kontroly

V Cloud Environment prošlo **53 PASS / 0 SKIP** za 184,01 s s CPython
3.12.14 a skutečnými Javacem, Kotlin K1 a K2 na Temurin JDK 21.0.6+7.
Oba Kotlin běhy ověřily čtecí report bez procesu, shodný store po odmítnutí,
nové rozřešené volání, vyřazení starých symbolů a důkazů a shodu celé
compiler vrstvy kontrolního modulu. Znovuvytvoření vstupu po první výměně
Mermaid vyvolalo rollback a zachovalo SHA i revizi autoritativního grafu.
Zůstaly pokryté starší kontroly změny bajtů, oddělených classpath, souběžné
publikace a existujících čtecích cest.

Běh odmítl jak neplatné kódování v původní cestě, tak nový deklarovaný
nečitelný vstup, běžné přidání a novou konfiguraci. Doplňkové kontroly
fyzické nepřítomnosti nepřijaly chybu oprávnění ani neplatné symbolické
odkazy. K1 sonda před doplněním kontroly vynechaného nového vstupu dříve
publikovala (SHA-256 `b70dd3c9813baf4531762b47164968cddfe85f3bfc36ae7d5fdbb79fe5bc1dd8`).

Pytest má raw exit 0 a SHA-256 JUnit
`881ef89b3ffefe2afdcd8b928aa1264b4f2e5c4016ed0f8951933cd21a077627`.
Produkční zdroje, testy a ověřené worker binárky souhlasí před a po běhu.
Plánovač zachoval 135 položek a všech 32 rozhodnutí. Celá standardní sada,
hostované GitHub Actions a nativní testy mimo Linux jsou při tomto předání
`NOT_RUN`.

```bash
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData \
  python -m pytest -n 2 --dist load --maxschedchunk=1 -v --tb=short -ra \
    -p no:cacheprovider -o tmp_path_retention_policy=failed \
    tests/test_reverse_dependency_index.py tests/test_graph_provider.py \
    tests/test_completion.py tests/test_graph_publication_concurrency.py \
    -k 'input_absence or retirement_of_deleted_owned_peer_input or overlapping_deleted_peer_input_still_aborts or actual_jvm_isolated_stale_peer_publication_and_guards or actual_jvm_overlapping_stale_peer_still_aborts or actual_jvm_uncaptured_eol_drift_during_peer_publication or actual_javac_signature_change or test_graph_provider or test_completion or test_graph_publication_concurrency'
```

## Krok 5 — použití a zbývající rozsah

Na uložené generaci spustit `kgmaker impact --evidence-only --format json
edited/src/main/kotlin/Example.kt`, poté ve stejném checkoutu použít
[explicitní Python API](../compiler-inspection.md#obnova-izolovaného-jvm-kontextu)
s nezměněným modelem. Platný vybraný modul a nezávislý kontrolní důkaz zůstanou
v publikovaném grafu. [Režim CLI](../stage-content-cache.md#selektivní-dopad-změn) ·
[Acceptance](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy) ·
[Stavová matice](../production-analysis-progress.md).

W02-AC01 zůstává `PARTIAL`. W03 dále vyžaduje `VERIFIED_IN_SCOPE` pro W02.
Selektivní přenos vnitřních compiler faktů, publikace feature revizí,
sdílené rozsahy a CLI s build manifestem mají vlastní ověření.
