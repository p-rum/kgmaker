# Use assigned task IDs in installed agent instructions

Datum 2026-11-26. Výchozí SHA `5ff2c0846056353605ccb9ab271bd86847c6e661`.
Související zadání [T053](../tasks/53_manageProjectInstallation.md),
instalace T053-S01 / T053-AC01 a upgrade T053-S02 / T053-AC02.

Sdílené instrukce dříve přenášely do cílových projektů vývojová pravidla
KGMAKERu pro výběr dalšího čísla, formát ID a číslování dokumentů změn.
`src/kgmaker/agent_rules.py` teď vede agenty k převzetí přiděleného ID
doslova a připojení pomlčky a výstižného anglického názvu. Například z
`ABC-007` vznikne název `ABC-007-fix-empty-input` a soubor zadání
`ABC-007-fix-empty-input.md`. Chybějící ID si agent vyžádá.

`src/kgmaker/agents.py` a odpovídající instrukce implementačního agenta
odkazují na konvence cílového projektu pro dokument změn. Aktualizovány jsou
spravované kopie instrukcí v `.github/` a příkazy Junie v `.junie/commands/`.
Uživatelské příklady jsou v [README](../../README.md) a
[návodu k instalaci](../project-installation.md). Stav a důkazy jsou ve
[stavové matici](../production-analysis-progress.md#t053--správa-instalace-v-cílovém-projektu-2026-11-24)
a [inventáři acceptance](../acceptance-inventory.md#t053--upgrade-a-uninstall-2026-11-24).
Jde o text instalovaných instrukcí. CLI/API pro ukládání tasků a obecné
šablony souborů proto nevyžadují změnu. Existující projekt načte nové
instrukce přes `kgmaker upgrade` po instalaci nové distribuce.

- PASS `python -m pytest -q tests/test_init.py tests/test_installation.py tests/test_installation_distribution.py`.
  Prošlo 61 testů bez přeskočení včetně instalace z wheelu.
- PASS Izolovaná kontrola `init` a `upgrade` přes Python API. Všech osm
  instalovaných souborů se sdíleným pravidlem obsahuje nový příklad a upgrade
  z výchozí SHA je aktualizoval s manifestem i bez manifestu. Opakovaný
  `init` a konfliktní `upgrade` místně upraveného agenta zachovaly obsah
  a časy změn souborů.
- PASS `git diff --check`.
- NOT_RUN Živé ověření odpovědi Copilot a Junie a úplná sada testů.
