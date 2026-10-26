# Omezené statické Thymeleaf fragmenty

T003-S09-W03 rozšiřuje dosavadní Thymeleaf extrakci o statické deklarace fragmentů, odkazy `th:replace`/`th:insert` a předání literálních modelových cest do deklarovaných parametrů. Dřívější implementace zachycovala placeholdery a přímé literální backendové vazby, ale fragmentové hranice a parametry nerozlišovala. Jde o SOURCE_ONLY syntaktickou evidenci; parser šablony nespouští a Spring MVC handler z literálního `return` nedokazuje.

Parser nyní vytváří `template_fragment` a fragmentově scoped `template_variable` uzly. Atributy na samotném elementu deklarace už patří tomuto fragmentu; různé fragmenty mohou bezpečně používat stejná formální jména. Fragmentový odkaz se propojí pouze při jedinečném cíli ve stejném scope a přesném počtu parametrů. Literální `${model.path}` argument předává hodnotu z přesného caller-scoped variable uzlu do uzlu deklarovaného parametru; vnořené fragmenty procházejí stejnou cestou bez globální alias proměnné. Duplicate `th:replace` nebo smíšené reference aliasy jsou ambiguous a nevytvářejí include ani argument edges. Dynamický, nejednoznačný nebo aritou chybný odkaz nedostane resolved include edge a zanechá diagnostiku. Podmínky zůstávají PARTIAL/UNKNOWN a nejsou vyhodnocovány; nepodporované výrazy také zůstávají UNKNOWN. PDF renderer zůstává explicitní externí hranicí. Žádné schéma graph/store ani worker protokol se nemění.

Příklad:

```html
<!-- templates/index.html -->
<section th:replace="~{fragments/card :: card(account=${order.customer})}"></section>
<!-- templates/fragments/card.html -->
<div th:fragment="card(account)"><span th:text="${account.balance}"></span></div>
```

Ověření: cílená template/feature/data-check/scanner/workbook sada `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_templates.py tests/test_feature.py tests/test_data_check.py tests/test_scanner.py tests/test_workbooks.py` — 64 PASS. Celá core sada `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q -rs` — 474 PASS, 114 SKIP. SKIP jsou nepřipravený JDK/JVM/K1/K2, Maven/exporter, Gradle 8.13/Kotlin cache, TypeScript/Node workery a skutečný Windows CI gate; žádný z nich se neuvádí jako PASS. Parser používá standard-library HTMLParser, nové template změny nevyžadují worker/JVM běh. Integrace proti PR34 head `78d7968ea7408adea3ec9ce783769bb799522470` přidala jeho dokumentaci a sémantická metadata; původní S09 source/test změny byly při integraci byte-identické a následné review opravy zůstaly omezené na S09 parser a jeho testy. Review opravil ownership atributů na fragment-declaration elementu, odmítnutí opakovaných reference atributů/aliasů a přesný scoped caller-variable → parameter tok vnořených fragmentů; regresní tests kontrolují i shodná formální jména napříč fragmenty. Po finálním scan: 326 souborů a 2 818 deklarací/sekcí. `kgmaker semantic validate`, `kgmaker check` a `git diff --check` PASS. Sémantické epizody PR34 (115 záznamů) zůstávají přesným prefixem, následovaným S09 implementační epizodou. T003-S09/AC09 zůstává PARTIAL; nepokryté zůstávají jiné templating dialecty, vyhodnocení podmínek, MVC handler resolution a runtime/rendering.
