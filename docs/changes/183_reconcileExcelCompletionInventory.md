# Doplnění kroků Excelu do plánovače T052

Datum 2026-11-26. Výchozí `main` `5ff2c0846056353605ccb9ab271bd86847c6e661`.
[T052](../tasks/52_addCompletionOrchestrator.md) · [T048](../tasks/48_completeImplementationHandoff.md).

## T052-S01 a T052-S04 / T052-AC01, T052-AC04

`kgmaker completion plan` četl 119 kanonických řádků. Kroky T054, T055 a
T056 měly zdrojové doklady, ale jejich stav byl popsán v próze mimo tabulku,
kterou plánovač čte. Tabulkové závislosti v jejich zadáních navíc potřebovaly
pojmenované sekce `### Txxx-Syy — …` s řádkem `- Závislosti:`. Změna doplňuje
deset atomických řádků do jediné existující stavové matice. Zachovává původní
119 položek, jejich stav i pořadí 32 kandidátů pro dispatch. Součet podle
skutečných řádků je 129 položek, 100 MERGED a 29 PLANNED. Dřívější souhrn
85 MERGED, 32 PLANNED a 2 PR_OPEN zaostával za stavem 90 MERGED a 29 PLANNED
na výchozím `main`. Původní audit T048-S01 zůstává samostatným checkpointem.
[Aktuální matice](../production-analysis-progress.md#aktuální-pracovní-inventář-t048-s01--2026-11-07) ·
[Registr a zadání](../tasks/README.md).

Jména kroků, požadavky a acceptance jsou zachované. T055-S03 eviduje přípravu
a export a zachovává deklarované předpoklady T050-S01 pro skilly a T053-S01
a T053-S02 pro instalaci a upgrade. Tyto tři předpoklady v dosavadním
kanonickém inventáři chybí. Plán je vypíše mezi závislostmi již dodaného
T055-S03. Tento krok nepotřebuje dispatch další implementace. Pro pět kroků
s PARTIAL plán uvádí akci `verify`. Dřívější záznamy `178_fixExcelBehaviorLineage.md`
a `178_reduceLiveInspectionOverhead.md` se používají podle jména souboru.

Parser, CLI argumenty a schéma plánovacího JSON jsou beze změny. Stávající
příklad `kgmaker completion plan --root /repo/kgmaker --jobs 3` platí stejně.
README a návod k Excelu nevyžadují změnu postupu. Doklady k chování zůstávají
v příslušném change note a v aktualizovaném acceptance inventáři.
[Návod T052](../completion-orchestrator.md) · [Acceptance](../acceptance-inventory.md).

## Podklad pro T054-S01 až S04, T055-S01 až S03 a T056-S01 až S03

- T054-AC01 až AC03 používají ověřený místní rozsah T054-S01 a S02 z [#155](https://github.com/p-rum/kgmaker/pull/155).
  T054-S03 a S04 zůstávají PARTIAL kvůli živému Jira importu a omezené
  distribuční matici. Oprava VML z [#159](https://github.com/p-rum/kgmaker/pull/159)
  obsahuje vlastní doklad o obou tvarech zlomu řádku se stejnými vstupními byty.
  [Doklad integrace](174_reconcileMergedDelivery.md) · [Regrese VML](176_readVmlLineBreaks.md).
- T055-AC01 až AC03 mají doloženou lokální přípravu, export a distribuci
  skillu z [#156](https://github.com/p-rum/kgmaker/pull/156). Živý Copilot
  a Jira import mají samostatné ověření a stav NOT_RUN.
  [Doklady po krocích](172_automateExcelMigration.md).
- T056-AC01 až AC03 mají stav PARTIAL. Dodání [#161](https://github.com/p-rum/kgmaker/pull/161)
  v merge `cb02463098c6cd3145b5b269154daf07586687a0` má doložený syntetický
  15listý sešit se třemi cestami, query tabulkou a regresní VBA fixture.
  Na výchozím `main` s nepoužitým definovaným názvem nad koncovou buňkou
  zmizela jedna dříve vykázaná cesta při nulovém počtu čtení tohoto názvu.
  Filtrovaný report `Worksheet_Change` vykázal obsluhu a řízený zápis,
  ale vynechal jeho `If`. Filtrovaný report druhého scénáře zahrnul zdroj
  nesouvisejícího sešitu při nulovém počtu mezisešitových hran, včetně
  syntetické identity po výslovné volbě `--include-source`. Reprodukce
  mají SHA-256
  `e127ae67975d5d6b4ef3e6deb89d574b1a628bdeafbefff09d7a3ccb54a2af25`
  a `1d884170177644d2301c2fefc15e616c323d7e454b2cefc662031d685d2b46c8`.
  Živý Copilot a produkční sešit zůstávají NOT_RUN. Opravy chování mají
  vlastní implementační rozsah. [Dříve ověřená fixture](177_extractExcelBehavior.md) ·
  [Dřívější regrese VBA a rozsahů](178_fixExcelBehaviorLineage.md).

## Skutečné ověření

```bash
kgmaker completion plan --root "$PWD" --jobs 32
python -m pytest -p no:cacheprovider -q --tb=short \
  tests/test_completion.py tests/test_completion_handoff.py
```

- RED — CLI před změnou skončilo kódem 0, ale kontrola seznamu deseti kroků
  skončila kódem 1 kvůli chybějícím položkám. SHA-256 plánu
  `cc591177c054a8b9203432433f223c8bc13f32957266469ca82d62a5fbecd294`.
- PASS — stejná kontrola po změně našla 129 řádků, deklarované závislosti,
  správné stupně ověření, 119 shodných původních položek a stejný dispatch.
  SHA-256 plánu `68eced9878f17b4ca9676ac942ab144cd77e14992701cf75769276c1d03145ac`.
- PASS — 42 cílených testů, 0 SKIP. SHA-256 JUnit
  `b0130af3d61b16ac90d9d87e3a4555fbe6f05fb953adf97396b93e0e26164939`.

Strukturu nových sekcí a graf ověřují `kgmaker semantic update --base 5ff2c08`,
`kgmaker semantic apply`, `kgmaker semantic validate`, `kgmaker memory capture`,
`kgmaker scan`, `kgmaker status`, `kgmaker check` a `git diff --cached --check`.

Úplná sada, nový běh Excel workeru a wheelu, hostovaná CI a nezávislé review
mají v této dokumentační změně stav NOT_RUN.

## T052-S01 a T052-S04 po integraci #164

Kanonické řádky jsou ověřené také na `main`
`49bab32c50436782a2009455a36ada41c06be42f` se stromem
`117ad84524a9c18ef1832471e3651f8bb41094b6`. Zdrojové soubory, testy a
dokumentace pro #164 jsou ve výsledku zachované. [Sloučená změna](https://github.com/p-rum/kgmaker/pull/164).

- RED — nad novým `main` před přidáním řádků kontrola znovu našla deset
  chybějících kroků. SHA-256 plánu s 119 položkami
  `6d1d5b8526845c2aef33864dadf407e9389003e90e8b32b54db1bf0d816ead09`.
- PASS — po přenosu má plán 129 položek, 100 MERGED a 29 PLANNED. Všech
  119 původních položek a pořadí 32 kandidátů na této bázi zůstalo shodných.
  Všechny tři kroky T056 mají MERGED/PARTIAL. SHA-256 plánu
  `b0b928c5a5dccfba1a6afedc84e964246ab5a1844c675ebcae957347fd8c602f`.
- PASS — oba cílené moduly výše mají 42 PASS, 0 SKIP za 3,08 s. SHA-256
  JUnit `0a651af35965fb4c2fbcd556015d485b0560d541e69de9a57f75dcd8e8aeefcd`.
