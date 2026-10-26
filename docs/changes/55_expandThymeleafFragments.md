# Omezené statické Thymeleaf fragmenty

T003-S09-W03 rozšiřuje dosavadní Thymeleaf extrakci o statické deklarace fragmentů, odkazy `th:replace`/`th:insert` a předání literálních modelových cest do deklarovaných parametrů. Dřívější implementace zachycovala placeholdery a přímé literální backendové vazby, ale fragmentové hranice a parametry nerozlišovala. Jde o SOURCE_ONLY syntaktickou evidenci; parser šablony nespouští a Spring MVC handler z literálního `return` nedokazuje.

Parser nyní vytváří `template_fragment` a fragmentově scoped `template_variable` uzly. Fragmentový odkaz se propojí pouze při jedinečném cíli ve stejném scope a přesném počtu parametrů. Literální `${model.path}` argument předává hodnotu do uzlu deklarovaného parametru, jehož použití ve fragmentu je samostatně označeno. Dynamický, nejednoznačný nebo aritou chybný odkaz nedostane resolved include edge a zanechá diagnostiku. Podmínky zůstávají PARTIAL/UNKNOWN a nejsou vyhodnocovány; nepodporované výrazy také zůstávají UNKNOWN. PDF renderer zůstává explicitní externí hranicí. Žádné schéma graph/store ani worker protokol se nemění.

Příklad:

```html
<!-- templates/index.html -->
<section th:replace="~{fragments/card :: card(account=${order.customer})}"></section>
<!-- templates/fragments/card.html -->
<div th:fragment="card(account)"><span th:text="${account.balance}"></span></div>
```

Ověření: cílená template/feature/data-check/scanner/workbook sada `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_templates.py tests/test_feature.py tests/test_data_check.py tests/test_scanner.py tests/test_workbooks.py` — 62 PASS. Celá core sada `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q -rs` — 472 PASS, 114 SKIP. SKIP jsou nepřipravený JDK/JVM/K1/K2, Maven/exporter, Gradle 8.13/Kotlin cache, TypeScript/Node workery a skutečný Windows CI gate; žádný z nich se neuvádí jako PASS. Parser používá standard-library HTMLParser, nové template změny nevyžadují worker/JVM běh. Finální integrace proti PR34 head `78d7968ea7408adea3ec9ce783769bb799522470` přidala jeho dokumentaci a sémantické metadata; vlastní S09 source/test soubory jsou byte-identical k předchozímu schválenému base `09816b7d0b1fb5874684ac2c539387483afd8a35`. Po integraci: `kgmaker semantic validate`, `kgmaker check` a `git diff --check` PASS; scan pokryl 326 souborů, 2 816 deklarací/sekcí a 21 736 vztahů. Sémantické epizody PR34 (115 záznamů) zůstaly přesným prefixem a přibyla jedna S09 implementační epizoda. T003-S09/AC09 zůstává PARTIAL; nepokryté zůstávají jiné templating dialecty, vyhodnocení podmínek, MVC handler resolution a runtime/rendering.
