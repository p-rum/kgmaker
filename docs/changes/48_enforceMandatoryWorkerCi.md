# T003-S11-W04 — Povinné worker CI a negativní prerequisite matice

## Problém a skutečná změna

Pozitivní compiler/build CI již vzniklo v předchozích samostatných dodávkách,
ale obecný compiler setup a K2 fixture neměly negativní regresi dokazující,
že chybějící worker skutečně shodí povinnou matici. Nejde o nový runtime
resolver ani zavedení implicitního buildu.

`tests/test_mandatory_worker_ci.py` volá skutečné existující setup gates a
skutečné `inspection.command` proti prázdnému worker home. Patnáct případů
kombinuje nepřítomný K1, TypeScript, K2, JDK nebo Maven mixed-fixture s příznakem
unset/0/1. Povinné vstupy vyvolají failure, volitelné SKIP. Dřívější prerequisite
se pouze uzná pro dosažení konkrétní negativní větve; tento test není pozitivní
důkaz fungujícího workeru. Discovery-only cesty JDK/Node se nikdy nespouštějí;
`subprocess.Popen` je zakázán assertion. Graph-byte sentinel i neexistující worker home zůstávají nezměněné.
Setup sentinel jako publikační cíl nepřebírá; jde o kontrolu absence vedlejší
mutace, nikoli nový důkaz reálné atomické publikace. Class setup atributy se obnoví.

Povinný `compiler-workers` job nyní explicitně zahrnuje tuto negativní sadu.
Zachovává skutečné K1/K2/TS/mixed Maven/Spring6.2.2 testy a bootstrap pinned
vstupů. Oddělený instalovaný exporter job nadále vyžaduje Maven/Gradle;
negativní Spring/exporter kontroly se zachovávají. Exploratorní druhé JDK
zůstává volitelné. README, capability a acceptance/stavová matice popisují tento
omezený kontrakt.

## Zadání a acceptance

[T003-S11-W04](../tasks/T003-S11-04-mandatoryWorkerCi.md), T003-S11, T003-AC11.
Závislosti worker distribution PR18 a exporter distribution PR22 jsou v main;
výchozí main `4113a7975451a8313321fd521252485c959908e3` již obsahuje i K2,
Windows a Spring selektory.

| AC | Konkrétní důkaz |
|---|---|
| AC01 | `test_missing_prerequisite_fails_required_but_skips_optional`: 15 případů FAIL/SKIP nad existujícími setup gates; pozitivní skutečné compiler/exporter CI zůstává zachováno |
| AC02 | Žádná změna product/schema; stávající graph v1/v2/v3 regrese v plné sadě |
| AC03 | Negativní matice zakazuje proces a zachovává store bytes i absenci worker home |
| AC04 | Přesná matice a oddělené volitelné druhé JDK v README/capability/inventáři |

## Ověření

- `PYTHONPATH=src python -m pytest -q tests/test_mandatory_worker_ci.py`: **15 PASS**.
- Počáteční běh negativní sady odhalil závislost očekávaného textu na JRE místo
  JDK hostitele a jiný text volitelného K2 SKIP. Opraveno deterministickými
  discovery-only tool cestami a oddělenou kontrolou povinné/volitelné diagnostiky.
- `git diff --check`: PASS před finálním semantic/scan.
- Plná sada se skutečnými připravenými workery a povinnými K1/K2/Spring flags:
  běží/čeká na sdílený testovací lock; finální výsledek bude doplněn před PR ready.
- Nové CI této větve: NOT_RUN před publikací. Předchozí main PR30 měl všech sedm
  jobů SUCCESS (40370755215); to nenahrazuje CI nového HEAD.

## Kompatibilita, příklad a hranice

Produktové příkazy, IDs, worker protokol a graph/store v1/v2/v3 se nemění.
Příklad: `KGMAKER_REQUIRE_K2=1 python -m pytest -q tests/test_k2_backend.py`
selže při chybějícím K2 workeru; bez povinného flagu tato skutečná integrační
fixture hlásí SKIP, nikoli PASS. Samotné testy nic nestahují ani nesestavují.

Tato dodávka neuzavírá benchmarky, regression budgets, úplnou end-to-end
acceptance ani release dokumentaci. Negativní absence vstupu není důkaz podpory
libovolné aplikace nebo toolchain verze. Nativní Windows rozsah je samostatná
již sloučená dodávka; tento PR do jeho runtime nezasahuje.
