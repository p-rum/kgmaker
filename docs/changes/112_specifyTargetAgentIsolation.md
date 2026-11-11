# Zadání pro oddělení cílových agentů (T049, revize 1)

Baseline `8aae58c0ca280c13ce19ccb6a7c4e3cd46005f10`, 2026-11-11. Distribuovaná review role dnes obsahuje pravidlo interní evidence kroků. Dosavadní init načítá pevně dané obsahy a obecné nástroje mohou obejít textový zákaz Git operace.

V [T049](../tasks/49_separateTargetAgents.md) je sedm plánovaných kroků T049-S01 až T049-S07, sedm požadavků a dvanáct akceptačních scénářů T049-AC01 až T049-AC12. Přidány odkazy do registru, inventáře acceptance a stavové matice. Příklad cílového použití je `kgmaker init --agent-template ./team-agent.json`. Jde o specifikaci budoucí volby.

Kontroly specifikace: PASS pro přítomnost unikátních R/S/AC ID ve správném počtu, platné lokální odkazy v zadání, návaznost na pracovní baseline, samostatné číslování zadání a change note a kontrolu pěti očekávaných změněných cest. Porovnány cli.init, zdroje rolí, test_init, pyproject a T046-S02 s návrhem. Registr, cílová větev a otevřené PR byly prověřeny před publikací.

Kompatibilita a dokumentace: žádná změna Python API, CLI, hostitelských oprávnění či fungování stávající instalace. README, aktuální příklady, distribuované profily a generovaný graf jsou bez dopadu, protože PR přidává jen zadání. Testy implementace a skuteční hostitelé NOT_RUN. Zbývá realizovat a ověřit všechny kroky podle nové specifikace.
