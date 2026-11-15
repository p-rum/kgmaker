# NamedQueries a named native queries

Datum: 2026-11-15; Task `T003-S06-W06`, kroky `T003-S06-W06-S01` až `S03`, acceptance `T003-S06-W06-AC01` až `AC04`.
Výchozí SHA: `14d7f7cefab2fa5c9cf8c6d939d3b92e838faea8`.

## S01 — XML deklarace a společný katalog

Problémem byla absence deklarací `named-query` a `named-native-query` z ORM XML
v existujícím katalogu JPA named queries. `src/kgmaker/framework.py` nyní čte
kořenové XML deklarace v omezeném, hashovaném vstupu, zachovává jazyk JPQL nebo
NATIVE_SQL a jejich původ. Deklarace se připojují ke stejnému katalogu jako
anotační `@NamedQuery`; nevytváří se paralelní model ani se nespouští provider.

## S02 — fail-closed duplicity a neúplné vstupy

Prázdné jméno nebo tělo vytváří `ORM_XML_NAMED_QUERY_UNRESOLVED`. Duplicitní XML
jména a kolize s anotační deklarací vytvářejí `ORM_XML_NAMED_QUERY_AMBIGUOUS` a
nevyberou jednu definici. Tím se zachovává UNKNOWN/PARTIAL důkazní vrstva a
nulová mutace při chybě.

## S03 — testy a dokumentace

`tests/test_named_query_containers.py` pokrývá oba jazyky, provenance, duplicitu
a chybějící tělo. `docs/acceptance-inventory.md` a
`docs/production-analysis-progress.md` uvádějí přesný rozsah. README, CLI a
capability API nemají dopad: jde o interní compiler projection bez nového příkazu.

Kontroly:

- `PYTHONPATH=src pytest -q tests/test_named_query_containers.py tests/test_orm_xml_overrides.py`: **PASS, 17 passed, 20 skipped**; skip jsou existující toolchain-dependent XML worker scénáře.
- `python -m compileall -q src/kgmaker/framework.py`: **PASS**.
- `git diff --check`: **PASS**.
- Skutečný JVM/compiler provider fixture: **NOT_RUN** (worker/toolchain není v tomto izolovaném běhu připraven); není vydáván za PASS.

Kompatibilita: staré anotační named queries, v1/v2/v3 graph identity a XML
precedence zůstávají čitelné. Omezení: XML named query se zatím nepropojuje na
entity bez jednoznačného compiler důkazu; runtime SQL/provider semantics,
Criteria/Specification/QueryDSL a plná produkční matice zůstávají mimo rozsah.
