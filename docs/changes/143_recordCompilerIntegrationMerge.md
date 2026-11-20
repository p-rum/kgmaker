# Záznam sloučení čtyř oprav compiler evidence

Tento dokument zaznamenává skutečné sloučení [#127](https://github.com/p-rum/kgmaker/pull/127).
Výchozí revize této dokumentační aktualizace je merge
`7a89e2868791eb7a061572de7527172e3b1ceb6a`. Rodiči jsou
`8ff2529ffb50b42ed2209d97478ea3e4cbf46042` a
`e059260b678e84b9d61df49619d0c0df4b367b6c`. Sloučený tree
`5072f113d766a3967dd841ea1ea4b6a6e90c9061` odpovídá testovanému kandidátu.
[T045 APPROVE](https://github.com/p-rum/kgmaker/pull/127#issuecomment-7050008640)
je vázán na přesný pár. Zdrojové drafty #119, #122, #124 a #126 byly uzavřeny
jako nahrazené společnou integrací.

- **T003-S10-W01 kroky 1–5, AC01–04.** Ochrana compiler evidence je sloučená.
  Výkonový HIT zůstává otevřený v [#116](https://github.com/p-rum/kgmaker/issues/116).
  [Rozsah opravy](135_bindCachedCompilerEvidence.md).
- **T025-S04/S05/S07 a AC04/05/06/08/09.** Oprava vadných CFG referencí
  je sloučená. Širší T025 zůstává PARTIAL. [Rozsah opravy](136_preserveMalformedCfgEvidence.md).
- **T003-S05-W04 kroky 4–5, AC01/03/04.** Kanonické Spring fixture a
  negativní kontroly jsou sloučené. [Rozsah opravy](139_validateCanonicalInjectionFixture.md).
- **T003-S07-W05 AC01/03/04.** Oprava typu context owner a testové pokrytí
  retry/DLT jsou sloučené. Aktivace a dostupnost zůstávají nedoložené.
  [Rozsah opravy](141_handleInvalidKafkaPolicyContext.md).

Přesný společný kandidát měl v jediném lokálním běhu **3644 PASS, 1 SKIP,
0 FAIL, 0 ERROR**, exit 0. SKIP je explicitní neadmin Windows smoke na Linuxu.
Čtyři původní regrese samostatně zopakoval T045 s výsledkem 4 PASS / 0 SKIP.
Graf, diff a obsahové piny prošly. U GitHub Actions chybí ověřitelný běh
runneru. Předchozí výsledek je evidencí #127 a neopakuje se jako nový full.
[Přehled přesné integrace](142_integrateCompilerEvidenceRepairs.md).

Dokumentační aktualizace opravuje stav v [matici](../production-analysis-progress.md)
a [inventáři acceptance](../acceptance-inventory.md). V příkazu
`kgmaker completion plan --jobs 4` je stav těchto oprav MERGED.
Širší ověření má samostatný stav. README, capability, API, CLI příklady,
registr zadání a init šablony nemění kontrakt. Produktový kód,
formáty evidence ani kompatibilita se tímto záznamem nemění.

Doprovodné ověření dokumentace má **7 PASS / 0 SKIP** z
`python -m pytest -p no:cacheprovider -q tests/test_completion.py`.
`kgmaker completion plan --jobs 4` načetl 119 položek a všechny čtyři řádky
spojil s #127. Ověření grafu používá `kgmaker semantic validate`,
`kgmaker scan`, `kgmaker status` a `kgmaker check`. Tato změna
samostatný úplný běh znovu nespouští.
