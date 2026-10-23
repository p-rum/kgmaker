# Konfigurace agentů gpt-6-luna pro T005–T044

## Problém

Po PR #10 je potřeba připravit samostatný projektový Codex profil pro každý ze 40 tasků T005–T044, aniž by samotná konfigurace byla zaměněna za spuštění nebo dokončení implementace.

## Změny

- Přidáno 40 TOML profilů do .codex/agents, po jednom na task, podle existujícího schématu.
- Všechny profily nastavují gpt-6-luna a reasoning effort medium, vyžadují izolovanou větev, kontrolu dependencies, testování, change note a samostatný PR bez automatického merge.
- Přidán dispatch report s dependency gates, READY/BLOCKED pravidly a výslovným rozlišením konfigurace od živého běhu.

## Ověření

- Task metadata, branch names a dependencies převzaty z T005–T044 v PR #10.
- TOML parse, počet/unikátnost profilů, model a dependency DAG se ověří před publikací.
- Runtime/build/pytest: NOT_RUN; jde pouze o agentní konfiguraci a dokumentaci.

## Omezení

Stav SPECIFICATION zůstává beze změny. Konfigurace vyžaduje novou session pro načtení registru a sama nespouští agenty. Žádný PR není tímto dokumentem automaticky mergován.

