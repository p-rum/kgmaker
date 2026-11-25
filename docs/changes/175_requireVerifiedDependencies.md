# 175 — Povinně ověřené závislosti při plánování

- Rozsah T052-S01, T052-R01, T052-AC01 a závislost T003-S10-W03 na W02-AC01.
- Výchozí main `5809e84932b1910bfc3f17c72e2a2005283389b1`. Přenos na skutečný
  `main` po #156 používá `3a6b97fc9c44941e68bb390772a5eb13906bf1ff`
  a zachovává potvrzenou čerstvost paketů z #151 i Excel skill z #156.

Doložený čtecí report W02 lze sloučit jako ověřený dílčí rozsah. V izolované
kopii skutečného inventáře tento stav `MERGED/PARTIAL` uvolnil W03,
přestože selektivní zápis chyběl. Cílený test spustil stejný případ
před opravou. Neuspěl při ověření explicitní závislosti, protože ji
výstup neobsahoval.

`src/kgmaker/completion.py` dovoluje vybrat z existujících přímých
závislostí ty, jejichž ověření je podmínkou dispatch. Výsledek uvádí
`verification_dependencies` a při částečném ověření vrací blocker
`VERIFIED_IN_SCOPE required`. Zápis, který odkazuje mimo deklarované
přímé závislosti, se odmítne. Výchozí chování ostatních položek zůstává
kompatibilní a chybějící nebo neúspěšné závislosti dál blokují práci.
V zadání W03 revize 2 je povinně ověřená W02 včetně selektivního zápisu
podle W02-AC01. Planner zůstává offline a čistě čtecí.

Příklad `kgmaker completion plan --root . --jobs 4` ponechá W03
v backlogu, dokud W02 splní slíbený zápis a má `VERIFIED_IN_SCOPE`.
Návod je v [completion-orchestrator](../completion-orchestrator.md),
[README](../../README.md#repository-completion-workflow) a
[acceptance inventáři](../acceptance-inventory.md#t052--completion-orchestration-2026-11-19).

Ověření v Cloud Environment na CPythonu 3.12.

- RED — `test_explicit_verified_dependency_blocks_only_when_proof_is_missing`
  selhal před implementací s chybějícím `verification_dependencies`.
  JUnit SHA-256 `b01d3ab16ed44f905b1e6e69158201a7d6ba9589ec777e30da913557ee98b85a`.
- GREEN — `python -m pytest -p no:cacheprovider -q tests/test_completion.py tests/test_workflow.py tests/test_workflow_profiles.py`
  **49 PASS / 0 SKIP**. JUnit SHA-256
  `2bd540c0c5d43c9a7345737ff56a20fe4954675871c01643f3cf81053133d55c`.
  Regrese ověřují i zachování běžné závislosti, uvolnění po ověření a
  odmítnutí neplatné specifikace s odkazem mimo deklarované závislosti.

Na společném kódu s #156 prošla i cílená sada completion, workflow,
profilů a skills, **76 PASS / 0 SKIP**, exit 0. JUnit SHA-256
`76da3cf4fa2f405adcc1987df9227827613a1beb7085c67d7bd3f46866d033c5`.
V oddělené kopii skutečného inventáře zůstal W03 blokovaný při
`MERGED/PARTIAL` a po změně na `MERGED/VERIFIED_IN_SCOPE`
se objevil mezi kandidáty. Otisk výsledku je
`8294a2cf2f264006193484d108095776b0fa5c4924815a8052fc70839e5d67f7`.

### Oprava parseru po nezávislém review

V revizi `13e50c8` vyhodnocoval parser pouze první rozpoznaný řádek.
Druhý řádek mohl skrýt neověřenou nebo nedeklarovanou závislost.
Prázdná deklarace bez mezery za dvojtečkou se tiše ignorovala.
Parser nyní povoluje v sekci jediný neprázdný řádek. Chybnou specifikaci
odmítne před výběrem kandidátů. Ostatní závislosti mají původní rozsah.

- RED — tři nové regresní varianty selhaly, jedna dříve odmítnutá
  kontrola prošla. JUnit SHA-256
  `6c91713320197418998cf73c1cac18c6724312ab3445728ee0e4fce04ccb1c69`.
- GREEN — čtyři nové případy a související completion, handoff, workflow
  a skills: **109 PASS / 0 SKIP**, exit 0. JUnit SHA-256
  `5ba4b5d935f398d7813655e03a305c0a43bc9b2f573d59a82db9233fa0d116da`.

W02-AC01 zůstává `PARTIAL`. Úplná sada, samostatný Windows běh, aktuální
GitHub Actions a nezávislé review mají při lokálním předání samostatný stav.
