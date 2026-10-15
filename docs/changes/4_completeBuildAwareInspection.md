# Dokončení build-aware inspection v ověřené matici

## Kontext PR

- PR: lokální větev `feat/impl`, PR číslo zatím není přiděleno.
- Výchozí commit: `d9a89fe951157fe58d2592fa96631b21f3698301`.
- Datum: 15. 10. 2026.
- Související zadání: T002, kroky T002-S01 až T002-S06; navazující T002-S07.
- Akceptační vazby: CG-01 až CG-04, MV-01 až MV-05, SP-01 až SP-03,
  HB-01 až HB-04, EV-01 až EV-02, BC-01 a EX-01 v rozsahu skutečně ověřené
  matice. Úplná acceptance bank zadání tímto dokumentem není prohlášena za
  splněnou.

## Problém a výsledné chování

Compiler worker uměl vytvořit přesné JVM/TypeScript symboly, call sites a CFG,
ale projektová inspekce neměla čitelný Maven declared model ani frameworkovou
vrstvu nad compiler symboly. Runtime pozorování také neměla samostatný importní
kontrakt.

`project inspect` nyní vrací read-only Maven reactor model se závislostmi,
pluginy, properties, fingerprintem a diagnostikou chybějících modulů.
Explicitní JVM inspection zachovává přesné compiler důkazy a přidává oddělené
`FRAMEWORK_DERIVED` Spring/JPA/Spring Data vazby. `runtime import` přijímá jen
hashově svázané pozorování pro konkrétní compiler context, build a konfiguraci;
aplikaci nespouští.

## Implementované změny

- `build_maven.py` čte XML namespace-safe POMy, prochází reactor moduly,
  interpoluje lokální properties a explicitně označuje effective model jako
  nedostupný bez build exportu.
- `inspection.py` zachovává compiler metadata potřebná pro FQ annotation
  resolution; `framework.py` modeluje stereotype/`@Bean`, injection, typové
  kandidáty s `@Qualifier`/`@Primary`, profile boundary, HTTP/listener/
  scheduler entrypointy, advice, self-invocation proxy boundary, entity/table/
  column, association, repository a omezené derived/annotated query vazby.
- `runtime_evidence.py` validuje identity context/build/config, source hashe,
  worker distribuci, známé graph symboly a bounded observations. Imported edges
  používají `RUNTIME_OBSERVED` a jsou dostupné v callgraph navigaci.
- `views.py`, `inspection_cli.py` a README rozlišují framework configuration,
  data-flow, integrations a generated entrypoints. Graph-v3 schema nyní
  připouští sanitizovaná compiler metadata.
- Přidán `tests/test_build_aware.py` pro Maven discovery, framework evidence,
  runtime import a odmítnutí stale source.

## CLI, konfigurace a datové kontrakty

```bash
./kgmaker project inspect --root fixtures/build-inspection/maven --format json
./kgmaker inspect code --root fixtures/build-inspection/maven \
  --repo-id fixture --module core \
  --classpath fixtures/build-inspection/maven/target/classes \
  --classpath workers/jvm/target/lib/kotlin-stdlib.jar
./kgmaker entrypoints --root fixtures/build-inspection/maven --format json
./kgmaker runtime import --root <compiler-checkout> --manifest runtime-manifest.json
```

Maven discovery zůstává `SOURCE_ONLY_DECLARED_MODEL`; effective classpath a
čerstvé outputs vznikají pouze přes explicitní build-plan/build-run/build-import.
Frameworkové hrany mají context/evidence IDs a runtime hrany mají build/config/
runtime identity v evidence záznamu. Absence runtime pozorování není negativní
důkaz.

## Kompatibilita a migrace

V1/V2 grafy zůstávají čitelné a historické syntaktické calls se nepovyšují.
Graph-v3 pouze rozšiřuje Node metadata; atomický store a existující scan/build/
feature/workspace/availability workflow se nemění. Runtime import vyžaduje
schema-v3 compiler graph a platný context s build identity. Návrat spočívá v
obnovení posledního validního `.kgmaker/graph.json`; nové framework/runtime
vazby se tím odstraní, zdrojové soubory se nemění.

## Ověření

| Příkaz / kontrola | Prostředí | Výsledek | Rozsah a omezení |
|---|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 python3.12 -m pytest -q` | Python 3.12.0, pytest 8.3.4 | PASS, 164 testů | Lokální regresní sada; neprokazuje nepokryté framework varianty |
| `mvn -q -DskipTests package` v `workers/jvm` | JDK 21.0.12.1, Maven | PASS | JVM worker distribuce; samostatný worker build |
| `mvn -q -U test` ve `fixtures/build-inspection/maven` | JDK 21.0.12.1, Maven | PASS, 1 test, 0 failures/errors/skipped | Malá mixed Java/Kotlin fixture |
| `./kgmaker project inspect ...` | lokální Maven fixture | PASS, `SOURCE_ONLY_DECLARED_MODEL` | Effective profiles/BOM nejsou deklarovaným modelem |
| `./kgmaker inspect code ...` | JVM worker 2.1.10/Javac 21 | PASS, 2 files, 5 methods, 5/5 calls resolved | Ground truth obsahuje pět přímých call sites |
| `./kgmaker inspect frontend ...` | Node 24.19.0, TypeScript 5.7.3 | PASS, 1 file, 3 methods, 3/3 calls resolved | React fixture bez multi-project acceptance |
| `tests/rendering/generate.py` + `node tests/rendering/validate.mjs` | Node 24.19.0, Mermaid 11.4.1, jsdom 26.0.0 | PASS pro TypeScript i JVM CFG | Ověření renderovaných CFG endpointů a vrcholů |
| `./kgmaker semantic validate --root .` | Python 3.12 | PASS, 3 concepts, 7 relationships | Existing affected semantic evidence was revalidated with a scoped patch; no new unsupported relationships were added |
| `./kgmaker scan --root .` and `./kgmaker check --root .` | Python 3.12 | PASS, 137 files, 1,153 nodes, 2,853 relationships | Generated graph and Mermaid/Markdown views are current |
| `git diff --check` | Git | PASS | No whitespace errors in the reviewable diff |

## Příklad

Po `inspect code` lze `entrypoints` číst jako generated Spring endpointy s
`FRAMEWORK_DERIVED`; `graph view --view configuration` ukáže bean/injection/advice
vazby a `graph view --view data-flow` entity/table/column vazby. Runtime manifest
musí uvést `runtime_id`, `context_id`, `build_id`, `config_fingerprint`, přesné
`source_hashes`, `worker_distribution` a cíle, které už existují v uloženém graphu.

## Omezení a zbývající práce

Dodávka pokrývá doloženou matici T002 M0–M5 a oddělený importní základ M6;
nepředstavuje úplnou Spring/Hibernate platformu. Chybí plný K2/coroutines model,
effective Maven profile/BOM/toolchain/variant matrix, custom registrars and
conditions, complete XML/access/naming/dialect/association/query semantics,
multi-context lifecycle provider, runtime trace producer/RTA/value-flow a živá
deployment/data availability. T003-S02 a širší T003 acceptance proto zůstávají
PARTIAL podle [progress matice](../production-analysis-progress.md). Kontrola
cílové větve a otevřených PR pro další publication kolizi nebyla lokálně
dostupná; číslo change note 4 je volné po kontrole pracovního tree.
