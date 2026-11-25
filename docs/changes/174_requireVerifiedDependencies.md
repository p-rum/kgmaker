# 174 — Povinně ověřené závislosti při plánování

- Rozsah T052-S01, T052-R01, T052-AC01 a závislost T003-S10-W03 na W02-AC01.
- Výchozí main `5809e84932b1910bfc3f17c72e2a2005283389b1`.

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

W02-AC01 zůstává `PARTIAL`. Úplná sada, samostatný Windows běh, aktuální
GitHub Actions a nezávislé review mají při lokálním předání samostatný stav.
