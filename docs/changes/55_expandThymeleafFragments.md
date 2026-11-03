# Omezené statické Thymeleaf fragmenty

T003-S09-W03 rozšiřuje dosavadní Thymeleaf extrakci o statické deklarace fragmentů, odkazy `th:replace`/`th:insert` a předání literálních modelových cest do deklarovaných parametrů. Dřívější implementace zachycovala placeholdery a přímé literální backendové vazby, ale fragmentové hranice a parametry nerozlišovala. Jde o SOURCE_ONLY syntaktickou evidenci; parser šablony nespouští a Spring MVC handler z literálního `return` nedokazuje.

Parser nyní vytváří `template_fragment` a fragmentově scoped `template_variable` uzly. Atributy na samotném elementu deklarace už patří tomuto fragmentu; různé fragmenty mohou bezpečně používat stejná formální jména. Fragmentový odkaz se propojí pouze při jedinečném cíli ve stejném scope a přesném počtu parametrů. Literální `${model.path}` argument předává hodnotu z přesného caller-scoped variable uzlu do uzlu deklarovaného parametru; vnořené fragmenty procházejí stejnou cestou bez globální alias proměnné. Duplicate `th:replace` nebo smíšené reference aliasy jsou ambiguous a nevytvářejí include ani argument edges. Dynamický, nejednoznačný nebo aritou chybný odkaz nedostane resolved include edge a zanechá diagnostiku. Podmínky zůstávají PARTIAL/UNKNOWN a nejsou vyhodnocovány; nepodporované výrazy také zůstávají UNKNOWN. `th:each`, `th:with` a jejich `data-th-*` aliasy uvádějí lokální jména, která tento subset nemodeluje; jejich obsah ani vnořené fragmentové argumenty se proto nevážou na globální backendový model a zůstávají UNKNOWN s diagnostikou. PDF renderer zůstává explicitní externí hranicí. Žádné schéma graph/store ani worker protokol se nemění.

Příklad:

```html
<!-- templates/index.html -->
<section th:replace="~{fragments/card :: card(account=${order.customer})}"></section>
<!-- templates/fragments/card.html -->
<div th:fragment="card(account)"><span th:text="${account.balance}"></span></div>
```

Ověření: cílená template/feature/data-check/scanner/workbook sada `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_templates.py tests/test_feature.py tests/test_data_check.py tests/test_scanner.py tests/test_workbooks.py` — 65 PASS. Celá core sada `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q -rs` — 475 PASS, 114 SKIP. SKIP jsou nepřipravený JDK/JVM/K1/K2, Maven/exporter, Gradle 8.13/Kotlin cache, TypeScript/Node workery a skutečný Windows CI gate; žádný z nich se neuvádí jako PASS. Parser používá standard-library HTMLParser, nové template změny nevyžadují worker/JVM běh. Integrace proti PR34 head `78d7968ea7408adea3ec9ce783769bb799522470` přidala jeho dokumentaci a sémantická metadata; původní S09 source/test změny byly při integraci byte-identické a následné review opravy zůstaly omezené na S09 parser a jeho testy. Review opravil ownership atributů na fragment-declaration elementu, odmítnutí opakovaných reference atributů/aliasů a přesný scoped caller-variable → parameter tok vnořených fragmentů; regresní tests kontrolují i shodná formální jména napříč fragmenty. Nový regression test ověřuje, že nepodporované `th:each`/`th:with` lokální proměnné (včetně data aliasů) nezpůsobí falešnou backendovou vazbu. Po finálním scan: 326 souborů, 2 821 deklarací/sekcí a 21 845 vztahů ve výsledném grafu. `kgmaker semantic validate`, `kgmaker check` a `git diff --check` PASS. Sémantické epizody PR34 (115 záznamů) zůstávají přesným prefixem, následovaným S09 implementační epizodou. T003-S09/AC09 zůstává PARTIAL; nepokryté zůstávají jiné templating dialecty, vyhodnocení podmínek, MVC handler resolution a runtime/rendering.

## Integrace současné hlavní větve

Závislost conditions PR34 již byla sloučena. Nová kompozice obsahuje main
`081d69ca69d14b4d131cc305e4e5c873960e71a3` se zachováním HTTP/XML/React a
ostatních parent funkcí. Žádný runtime konflikt nevznikl; vlastní parser,
feature capability a store renderer změny zůstaly beze změny. Dřívější full
475PASS114SKIP je historická core evidence vlastního parseru, nikoli výsledek
aktuálních workerů. Nové cílené kontroly budou uvedeny až po běhu.
Main195 immutable episodes jsou exact prefix, dvě původní child captures
zůstávají beze změny. Sémantické odkazy na posunuté funkce byly přepojeny pouze
podle jednoznačných IDs z čerstvého CLI scanu; duplicitní parent fakta zachována
jednou. GH CI je volitelné dle uživatelské revize T045, ostatní kontroly povinné.

Aktuální cílený běh: **156 PASS, 0 SKIP v2.45s** v template/feature/data-check/
scanner/workbook a společných T005/T023 model testech. XML je uložené mimo checkout
v `/workspace/template-current-validation/focus.xml`. Skutečné worker fixture
nejsou pro neměněný SOURCE_ONLY parser potřeba; původní skips se neproměňují v PASS.
Následná metadata oprava přepojila vlastní Thymeleaf a posunuté HTTP doc citations
na ověřené aktuální řádky1023/1043, bez změny runtime či test source.
