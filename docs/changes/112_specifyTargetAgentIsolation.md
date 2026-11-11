# Zadání pro oddělení cílových agentů (T049, revize 1)

Baseline `8aae58c0ca280c13ce19ccb6a7c4e3cd46005f10`, 2026-11-11. Distribuovaná review role dnes obsahuje pravidlo interní evidence kroků. Dosavadní init načítá pevně dané obsahy a obecné nástroje mohou obejít textový zákaz Git operace.

V [T049](../tasks/49_separateTargetAgents.md) je sedm plánovaných kroků T049-S01 až T049-S07, sedm požadavků a dvanáct akceptačních scénářů T049-AC01 až T049-AC12. Přidány odkazy do registru, inventáře acceptance a stavové matice. Příklad cílového použití je `kgmaker init --agent-template ./team-agent.json`. Jde o specifikaci budoucí volby.

Kontroly specifikace: PASS pro přítomnost unikátních R/S/AC ID ve správném počtu, platné lokální odkazy v zadání, návaznost na pracovní baseline, samostatné číslování zadání a change note a kontrolu pěti očekávaných změněných cest. Porovnány cli.init, zdroje rolí, test_init, pyproject a T046-S02 s návrhem. Registr, cílová větev a otevřené PR byly prověřeny před publikací.

Kompatibilita a dokumentace: žádná změna Python API, CLI, hostitelských oprávnění či fungování stávající instalace. README, aktuální příklady, distribuované profily a generovaný graf jsou bez dopadu, protože PR přidává jen zadání. Testy implementace a skuteční hostitelé NOT_RUN. Zbývá realizovat a ověřit všechny kroky podle nové specifikace.

## Oprava po nezávislém review — 2026-11-11

- Task/step/AC: T049, specifikace před implementací, T049-AC12 (dokumentační kontrola); výchozí head PR #92 `042d3d6c3400b538ef609dfdd082ca1eab859e8b`, base `8aae58c0ca280c13ce19ccb6a7c4e3cd46005f10`.
- Problém: registr `docs/tasks/README.md` nesprávně uváděl otevřený PR #41 a absenci T046 v `main`. Opraveny pouze dva stavové odstavce; ID, odkazy na zadání, Python API, CLI, distribuované šablony ani runtime se nemění.
- Skutečně provedená ruční kontrola: GitHub read stavu PR #41 a #42 (MERGED), otevřených #43/#44/#45/#40; přečten obsah registru na aktuální větvi; samostatné načtení `docs/tasks/49_separateTargetAgents.md` a kontrola unikátních ID výrazy `T049-R\d{2}`, `T049-S\d{2}`, `T049-AC\d{2}`: 7 R, 7 S a 12 AC, všechny sekvence bez mezer. Jde o čtení přes GitHub konektor, nikoli lokální běh nástrojů.
- Neprovedeno (NOT_RUN): lokální test runner, instalace wheelu, ověření Copilot/Junie hostitele, změny runtime či implementace T049. GitHub Actions aktuálního původního SHA vykázaly failure; bez diagnostiky kroků se netvrdí žádný PASS ani skutečné selhání aplikačních testů.
- Dopad dokumentace: stavový registr opraven, existující T049 specifikace a inventář acceptance se nemění; README/CLI navenek bez dopadu, protože nové chování dosud nebylo implementováno. Zbývá nezávislé review aktuálního base/head a implementace T049-S01–S07.
