# T003-S13-W01 — sanitizovaný runtime trace producer

## Krok T003-S13-W01-S01 / AC01–AC04

Výchozí SHA: `14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8`.

Přidána je funkce `produce_manifest` a příkaz `kgmaker runtime produce`. Příkaz
jako jediný smí spustit callerem dodaný producent. Jednoznačný JSON výstup se
kontroluje proti čerstvému schema-3 compiler contextu; facts jsou omezeny na
`call`, `bean`, `condition`, `mapping`, a envelope nese build/config/service/version
fingerprinty, source identity, status a diagnostiku. Hesla, tokeny, authorization,
API/private keys a citlivé query parametry se redigují. Zápis je atomický až po
validaci; timeout, nenulový exit, nevalidní JSON nebo neznámý fact nemění artefakt.

Dotčené soubory: `src/kgmaker/runtime_evidence.py`, `src/kgmaker/inspection_cli.py`,
`tests/test_runtime_trace_producer.py`, `README.md`, `docs/architecture.md`,
`docs/acceptance-inventory.md` a `docs/production-analysis-progress.md`.

Kompatibilita: import přijímá schema v1 i v2; graph/store schema se nemění.
Facts nejsou tímto work package importovány jako RTA/value-flow ani nepovyšují
availability.

Kontroly:

- PASS — `PYTHONPATH=src python3 -m pytest -q tests/test_runtime_trace_producer.py tests/test_build_aware.py` (7 passed).
- PASS — `PYTHONPATH=src python3 -m kgmaker --help`.
- NOT_RUN — skutečný JVM/Spring application toolchain; fixture je bounded Python producer a neprokazuje startup/deployment.
- SKIP/BLOCKED — `kgmaker status/query/memory recall`; executable hlásil `ModuleNotFoundError: No module named 'kgmaker'`, proto nebyl obnoven graf ani tvrzen semantic graph PASS.
- NOT_RUN — full pytest a `git diff --check` jsou release-gate kontroly koordinátora.

Zbývá: T003-S13-W02–W04 řeší RTA import, value-flow a async/reflection. Tento
krok nepřidává runtime availability ani data proof a nespouští aplikaci při
scan/hook/feature/import.
