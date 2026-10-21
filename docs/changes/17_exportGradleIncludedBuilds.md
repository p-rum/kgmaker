# Repo identita a závislosti Gradle included builds

## Problém a skutečné změny

T003-S03-W03, kroky1–5, acceptance AC01–AC04. Root exporter dříve hlásil pouze
INCLUDED_BUILDS_NOT_EXPORTED a runner přepisoval repo_id na local. Nyní explicitní
Gradle export koordinuje samostatné fragmenty included builds uvnitř snapshotu,
zachovává deterministickou build-root-qualified repo/context identitu a spojí
jejich SourceSet modely. Shodná jména modulů se nesloučí. Jar ownership čte ze
skutečného archive task modelu. Závislosti používají existující classpath.realm;
nový paralelní katalog nevzniká. Při nejednoznačném vlastníkovi výstupu se realm
nezvolí. Gradle dependency substitution zvolí aktuální included output místo stale
repository artefaktu a runner zachová přesné resolved pořadí včetně jiných závislostí.

## Kompatibilita a příklad

Volitelné build_root v manifestu se validuje proti repo identitě. Staré manifesty
bez tohoto pole zůstávají podporované; graph/store v1/v2/v3 a worker transport se
nemění. Explicitní `kgmaker project build-plan --build-system gradle --offline
--output /tmp/plan.json` a `kgmaker project build-run --plan /tmp/plan.json`
exportují composite model; inspect volí explicitní context z výsledného manifestu.
SOURCE_ONLY, scan, hook a feature Gradle nespouštějí.

## Provedené kontroly

- Před implementací skutečný Gradle8.13 acceptance FAILED: očekávané dva lib
  contexty, exportován jen jeden (1 failed in3.83s).
- Po implementaci skutečný composite acceptance: 1 passed in4.51s.
- `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_TEST_OTHER_JAVA_HOME=/home/petra/.jdks/openjdk-22.0.1 KGMAKER_TEST_GRADLE=/home/petra/.gradle/wrapper/dists/gradle-8.13-bin/5xuhj0ry160q40clulazy9h7d/gradle-8.13/bin/gradle PYTHONPATH=src python3 -m pytest -q`:
  **209 passed in51.11s**, bez skips; skutečné JVM/TS/Maven/JDK21+22/Gradle workers.
- Po rozšíření fixture o další externí souborovou závislost targeted
  `tests/test_gradle_included.py`: **3 passed in4.07s**. Test porovnává pořadí
  manifestu přímo se skutečným Gradle exportem. Negativní testy ověřují nejednoznačný
  output realm bez procesu a neplatnou repo identitu bez vytvoření store.
- Worker outputs byly převzaty z existující trusted lokální distribuce, nikoli
  implicitně instalovány nebo sestaveny analytical příkazem.
- Finální semantic/update/apply/validate, memory, scan/status a diff check: viz níže.

## Neprovedené kontroly a zbývající hranice

Included build mimo zachycený snapshot zůstává UNBOUND_INCLUDED_BUILD/PARTIAL;
chybějící exportní fragment INCLUDED_BUILD_EXPORT_UNAVAILABLE/PARTIAL. Nejsou
povyšovány na úplné source coverage. Libovolné Android/KMP modely nejsou Java
SourceSetContainer; aggregatory bez něj zachovají konkrétní unsupported diagnostiku.
Vlastní compile task included projektu nemusí být v dané explicitní build fázi
spuštěn; export modelu není jeho TEST_PASS. Celý T003-S03 není dokončen.

S03-W02 byl sloučen v PR #14. Navazující PR #15 je po integraci do aktuálního
`feat/impl` podmíněn novým CI a review nad aktuální base/head dvojicí.

## Závěrečná evidence

Po finální úpravě qualified diagnostik a rozšíření order fixture stejný mandatory
full-suite příkaz: **209 passed in55.63s**, bez skips. Scoped semantic
update/apply/validate, memory capture nad `8e13f82`, následný scan/status a
`git diff --check`: PASS. Patch zachoval jeden dotčený koncept a čtyři již doložené
vztahy; nové nepodložené vazby nebyly přidány.

## Revize po nezávislém CR

W03 nyní vychází ze schválené opravy W02 (`8b094d0`), která zachovává
source-set freshness a odmítá podvržený `GRADLE_CONVENTION`. Manifest
odmítne každý `classpath.realm`, pro který není právě jeden output producent
se stejnou cestou, hashem, execution-bound freshness a přesnou
`repo_id/module/source_set/scope` identitou. Deklarovaná cesta Jar tasku sama
o sobě realm neudělí; exporter ji přidá do outputů jen tehdy, když aktuálně
existuje, a runner nepřiřazuje realm z neúspěšného nebo smíšeného buildu.
Negativní fixture zkouší ghost artefakt, cizího producenta a dva producenty
jednoho outputu; všechny odmítá před vytvořením build store. Přímý cílený
běh skutečné Gradle composite fixture a negativních případů měl 6 PASS.
Plná sada po rebase a opravě s povinnými workery, Gradle 8.13 a JDK21/22:
**221 PASS, 0 SKIP** za 48,58 s.
`kgmaker semantic update --base 8b094d0` označil jeden dříve doložený koncept
a čtyři vztahy dotčené hashem README. Packet-bound patch je znovu ověřil,
`semantic apply` a `semantic validate` prošly; ostatní vztahy zůstaly zachovány.
`memory capture --base 8b094d0` zachytil epizodu této rebased změny.

Po sloučení W02 v PR #14 byl PR #15 znovu integrován nad jeho přesný strom.
Konfliktní sémantické epizody byly obsahově sloučeny (27 zachovaných epizod),
graf obnoven příkazem a `kgmaker check` prošel. První lokální full suite pod
omezeným sandboxem měla 218 PASS a 3 FAIL pouze při startu Gradlu
(`libnative-platform.so`); build se v těchto případech nespustil. Opakovaný
stejný strict běh s lokálním nativním přístupem k Gradlu a JDK21/22:
**221 PASS, 0 SKIP za 48,42 s**. Tato integrační revize vyžaduje nové CI a CR
nad aktualizovaným vzdáleným HEAD.
