# Oddělení production scope a důkazní model v2

## Kontext PR

- Branch: `feat/evidence-production-scope`; cílová větev `main`.
- Baseline: `8ac80ca30f6f680539deb7fb3590519d3a5c1460`.
- Datum: 13. 10. 2026. PR je první částečný inkrement rozsáhlého zadání.
- Číslo dokumentu 1 bylo vybráno po kontrole lokální větve, `origin/main`
  a aktuálního GitHub tree `main`: žádné číslované change documents.

## Problém a výsledné chování

Globální name-match index dovoloval testovacím deklaracím změnit produkční
kandidáty. Scanner nyní odděluje scope před symbolovým indexem, persistence a
dataflow extrakcí i slučováním sdílených doménových uzlů. Produkční importy
se rovněž hledají ve vybraném scope. Syntaktická volání zůstávají kandidáty;
nová evidence jim nedává compiler resolution. Dokumentace nedodává doménové
execution vztahy z příkladů. Testy a dokumentace neovlivňují execution ranking.

Výchozí query, hook a generované architecture Markdown/Mermaid používají
production, unknown scope je viditelně vynechán. Samostatný inventory dovoluje
ověřit classification důvody a konflikty. SOURCE_ONLY reporty jsou PARTIAL.
Žádný nový příkaz nespouští build, aplikaci, test, migraci nebo DB spojení.

## Rozsah milníků a acceptance

Žádný P0–P9 není tímto PR prohlášen za plně dokončený. P1 a P8/P9 mají funkční
vertikální řez, P0 má inventuru. [Gap matrix a progress](../production-analysis-progress.md)
uvádí celý zbývající rozsah a vazbu na původní M0–M5.

Test evidence:

- CL-01/CL-02: stejnojmenná testovací deklarace, 500 testů a 500 dokumentů
  nemění produkční JSON projekci, kandidáty, ranking ani Mermaid.
- CL-03: dodané custom roots, více memberships, integrationTest a explicitně
  zahrnuté generated source roots; effective build model stále chybí.
- CL-04: colocated TS test a podezřelý production vstup mají konflikt;
  TypeScript Program/exclude resolution ještě není implementovaná.
- CL-05: YAML/config, SQL/migration a Kotlin executable role jsou oddělené;
  symbolový Spring @Bean adaptér stále chybí.
- RK-01–04: nulový execution příspěvek type references, zachovaná enum metoda
  v ručně sestaveném grafu, nezávislost test overlay a deterministické skóre.
  Toto není compiler evidence enum fixture nebo úplný ranking milník.
- EV-01: v1 migrace nepovyšuje confidence/scope, zachová mapování legacy IDs.
- EV-02: neexistující evidence ID nebo povýšení syntaktické evidence je odmítnuté.
- EV-04: změna zdroje během čtení odmítne mixed snapshot.
- BC-03: simulované selhání atomického replace ponechá poslední validní index.
- Dosavadní availability, Flyway, workspace a feature regrese zůstávají PASS.

## Kód, CLI a schéma

Schema v2 rozšiřuje Node/Edge a graph envelope o klasifikaci, evidence inventory,
content contexts a diagnostiku. Každá scanner hrana nese source hash/location,
scope context a evidence ID. Freshness popisuje captured obsah, origin trust
se odděluje od integrity. Supplied source-set model zůstává unverified.

Classifier podporuje `.kgmaker/classification.json` s povinným důvodem, samostatné
osy a source-set memberships. Konflikt override/model nebo production/test
konvence je viditelný; strict režim jej odmítne. Explicitně uvedené generated
source roots lze číst i pod jinak vynechaným build adresářem, bez spuštění buildu.

Nové příkazy: `project inspect`, `project classify`, `graph view`, `graph rank`,
`graph migrate`, `coverage report`. Query dostává `--scope`. Přesné JSON/CLI
kontrakty a příklady jsou v [production scope](../production-scope.md) a
[graph-v2 schema](../schemas/graph-v2.schema.json).

Workspace zachovává repo-qualified IDs, nově kvalifikuje také context/evidence
references a cache key zahrnuje classification fingerprint. Feature baseline
nese nový parser version; semantic packet nese contexts a nepřijme starý patch
po jejich změně. Availability nepřebírá call/build fakta jako AVAILABLE.

## Kompatibilita a migrace

V1 zůstává čitelná; její scope/origin/role nemají nový důkaz. `graph migrate`
udělá explicitní konzervativní v2 převod se scope unknown, legacy ID mapping,
SYNTAX_CANDIDATE, trust/freshness unknown. Duplicitní legacy IDs odmítne.
Path-owned dataflow IDs a feature v1 path proof kontrakt zůstávají stejné.
Sdílené doménové uzly neprodukčních scopes získávají scope-qualified IDs;
neplatné staré semantic odkazy se nepřipojí k jiným symbolům. Regenerování
semantic packetu je potřeba při změně analysis context.

## Spuštěné kontroly

Prostředí: Python 3.12.14; OpenJDK runtime 21.0.12.1 (JRE bez javac),
Node 24.19.0, npm 11.9.0. Žádná compiler/framework matice není prohlášena za
ověřenou.

```bash
PYTHONPATH=src python -m unittest discover -s tests -q
git diff --check
PYTHONPATH=src python -m kgmaker project inspect --root /workspace/kgmaker --format json
PYTHONPATH=src python -m kgmaker graph rank --root /workspace/kgmaker --profile execution --explain
PYTHONPATH=src python -m kgmaker coverage report --root /workspace/kgmaker --format json
```

Baseline: 98 testů PASS. Po implementaci: 110 testů PASS. `git diff --check`
PASS. Nové CLI výstupy byly vytvořeny jako validní JSON se stavem PARTIAL;
coverage odlišuje missing/stale/fresh uložený index od aktuální in-memory analýzy.

Spuštěno také `PYTHONPATH=src python -m kgmaker scan`, `status` a `check`: PASS;
`PYTHONPATH=src python -m kgmaker semantic update --base 8ac80ca30f6f680539deb7fb3590519d3a5c1460 --token-budget 8000`
vytvořilo lokální scoped packet. Žádné agent-authored vztahy nejsou přidány;
semantic artifact nebyl vytvořen ani přepsán. CLI help pro project/graph je funkční.

## Nespuštěné kontroly a omezení

JVM mixed build, TypeScript compiler spike, Maven/Gradle, Spring/Hibernate/
Kafka/REST integrační fixtures, CFG a Mermaid parser/render nejsou ověřené.
Prostředí nemá javac/kotlinc/Maven/Gradle ani TypeScript dependency. Pokus
získat připnutý TypeScript 5.7.3 přes npm skončil přerušením před dokončením
tool execution; instalace ani compiler run nejsou tvrzené. `npm view` pouze
ověřilo dostupnost názvu/verze, nikoli kompatibilitu.

Povinné P0–P9 zůstávají částečné podle progress dokumentu. Nedodáváme resolved
JVM/TS call sites, bytecode, CHA, Spring wiring, plný ORM/query model, nové
integrační adaptéry, UI binding, CFG/process flowchart, benchmark ani build
execution/import. Dodaný source-set model není autoritativní Maven/Gradle export.
Architecture Mermaid není CFG. P10 je samostatná volitelná etapa.

## Ověřitelný příklad

```bash
PYTHONPATH=src python -m unittest discover -s tests -p test_production_scope.py -v
PYTHONPATH=src python -m kgmaker project classify --root . --explain --format json
PYTHONPATH=src python -m kgmaker graph view --root . --scope production --view calls
PYTHONPATH=src python -m kgmaker graph rank --root . --profile execution --explain
```

V tomto SOURCE_ONLY indexu mají legacy `calls` nulový execution příspěvek.
Reference na DTO/enum se mohou objevit v impact dimension, ale nepovyšují
syntaktický nález na skutečné volání nebo business důležitost.
