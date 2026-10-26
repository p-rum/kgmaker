# T003-S11-W03 — Windows instalace bez admin práv

- Work package ID: `T003-S11-W03`
- Milník: `T003-S11`
- Revision: 1
- Datum: 2026-10-16
- Stav: VERIFIED_IN_SCOPE / REVIEW_PENDING; skutečný Windows důkaz níže, PR24 není touto evidencí prohlášen za merged.
- Baseline: pracovní větev nad `8ac80ca30f6f680539deb7fb3590519d3a5c1460`; před zahájením ověř aktuální cílovou větev a otevřené PR.
- Závislosti: T003-S11-W01 a T003-S11-W02; průřezové požadavky `T003-R01–R10`.
- Nadřazená acceptance: `T003-AC11`.

## Cíl

Zdokumentovat a ověřit podporovanou Windows instalaci/prerequisites bez admin oprávnění.

## Rozsah a konkrétní kontrakty

- Primární místa změny: `packaging/CI/docs`.
- Reuse existující model/store/provider/workspace/evidence vrstvy; nevytvářej paralelní katalog ani odlišnou identitu entity.
- Zachovej SOURCE_ONLY, nulové implicitní spouštění buildů, instalací, migrací a aplikace a atomickou publikaci poslední validní generace.
- Výsledek s neúplnou evidencí musí být PARTIAL/UNKNOWN s konkrétním důvodem; confidence nesmí nahrazovat chybějící důkaz.
- Veřejnou změnu současně promítni do README, capability dokumentace, CLI příkladů a stavové/acceptance matice.

## Implementační kroky

1. Před kódem ověř současný kontrakt ve zdroji, testech a knowledge graphu; zapiš přesnou podporovanou matici a failing acceptance.
2. Rozšiř stávající datový model a versioned protocol pouze o pole nutná pro tento work package; popiš migraci a kompatibilitu v1/v2/v3.
3. Implementuj pozitivní cestu, lokalizovanou diagnostiku a nulovou mutaci při invalidním vstupu, timeoutu nebo zrušení.
4. Přidej produkčně věrnou fixture a negativní/ambiguous variantu: Windows CI smoke test v user-space paths včetně mezer.
5. Aktualizuj acceptance inventář, `docs/production-analysis-progress.md` a nový český `docs/changes/<N>_<shortName>.md` skutečnými výsledky.

## Požadavky na testování

- Test musí ověřit: Windows CI smoke test v user-space paths včetně mezer.
- Spusť nejmenší relevantní testy, potom celý `python3 -m pytest -q`; worker/build task navíc spustí příslušný skutečný toolchain test.
- Ověř `git diff --check`, nulové implicitní procesy v offline cestách a nulovou mutaci store při chybě.
- Chybějící povinný toolchain je FAIL/BLOCKED/SKIP dle matice, nikdy PASS. Do change note napiš přesné příkazy, výsledky a neprovedené kontroly.

## Akceptační kritéria

- **T003-S11-W03-AC01:** Core a deklarované workery projdou smoke testem; unsupported prerequisite je explicitní.
- **T003-S11-W03-AC02:** Staré podporované vstupy a graph/store schema zůstávají čitelné nebo mají výslovně otestovanou migraci.
- **T003-S11-W03-AC03:** Negativní a nejednoznačný případ nevytvoří silnější evidence ani dostupnost, než dovolují vstupy.
- **T003-S11-W03-AC04:** Stavová matice odkazuje na konkrétní test/fixture/verzi a nepovýší celý milník nad skutečně ověřený scope.

## Větev, PR a Definition of Done

- Implementuj výhradně v samostatné větvi, doporučeně `feat/t003-s11-03-windows-no-admin-install`; do stejné větve nepřidávej jiný work package.
- Na konci vytvoř samostatný pull request do aktuálně určené cílové větve. PR musí odkázat na tento soubor, `T003-S11`, nadřazenou acceptance a nový change note; bez explicitního pokynu jej nemerguj.
- Hotovo znamená implementovaný omezený kontrakt, zelené požadované kontroly, aktualizované docs, validní sémantický patch/scan podle projektových instrukcí a zdokumentované zbývající hranice.


## Implementační evidence (2026-10-26)

Runtime/harness `d311231ed4e199ee0c19d9d5037ccfcdcdce199b`, base
`eff0d3d5d7620b017fe42a65a54f672af8068667`: skutečný
[Windows run40351407076/job121672139333](https://github.com/p-rum/kgmaker/actions/runs/40351407076/job/121672139333)
**43 PASS / 2 scoped SKIP**, 50.23s; všech sedm CI jobů SUCCESS.
Core/Java/K1 Kotlin/TypeScript installed wheel smoke proběhl pod ověřeným
non-admin tokenem v user-space cestách s mezerami, včetně protocol cleanup a
negative/no-mutation kontrol. AC01–AC04 jsou VERIFIED_IN_SCOPE této matice.
K2 Windows a Windows BUILD_EXECUTE nejsou podporou tohoto důkazu tvrzeny;
POSIX-only setup a nepřipravený K2 artefakt tvoří dva explicitní SKIP.
Přesné verze/příkazy a historické diagnózy jsou v
[change note40](../changes/40_supportWindowsUserInstall.md).
Durable task zůstává v review do nezávislého přijetí a merge. Metadata-only HEAD
musí znovu projít požadovanými CI checks; celý T003-S11 zůstává PARTIAL.
