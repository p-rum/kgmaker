# T048 — skutečný post-merge stav a integrační ověření

- Krok `T048-S01 / T048-AC01`, doplňující `T048-S03 / T048-AC03`;
  příslušná dodávka `T003-S06-W05 / AC01–AC04`, sousední delivery T051.
- Výchozí SHA dokumentačního kroku: `2bebab00c2ca368e3e5a6a4d7daa47fce2addcea`.
- Baseline jsou skutečné git objekty a jejich rodiče, nikoli pouze
  `base_sha` z normalizovaného PR snapshotu. Identita/revize zadání se nemění.

## Problém a přesná historie

PR97 je MERGED; aktuální matice přesto ponechávala PR_OPEN. Do main byly také
samostatně sloučeny T050 a T051. [PR99](https://github.com/p-rum/kgmaker/pull/99)
je MERGED jako `6eb755ec1d4e777abe8d34dea7bee9477c90692f`; jeho stav v matici byl také zastaralý.

Před merge PR97 vrátil PR konektor `base_sha=193c89b`, přestože skutečný head
main už byl `6eb755ec1d4e777abe8d34dea7bee9477c90692f`. Pre-merge ověření cílové větve se opřelo o tento
zastaralý údaj a nesplnilo T045 base gate pro skutečnou integrační dvojici.
Reviewer [veřejně opravil záznam](https://github.com/p-rum/kgmaker/pull/97#pullrequestreview-5910459277).
Tuto chybu procesu nepřepisujeme tvrzením, že dodatečný PASS proběhl před merge.

Skuteční rodiče merge `2bebab00c2ca368e3e5a6a4d7daa47fce2addcea` jsou `6eb755ec1d4e777abe8d34dea7bee9477c90692f` a `ff31433eba0e180deb1df2b5f4aa8b76f3e690e0`.
Původní full **2264 PASS /481 SKIP** platí pouze pro head `ff31433eba0e180deb1df2b5f4aa8b76f3e690e0`, nikoli
pro celý výsledný main. Kvůli tomu byl proveden nový celý běh nad přesným
sloučeným main `2bebab00c2ca368e3e5a6a4d7daa47fce2addcea`, včetně nových workflow/skills změn.
Aktuální revize větve se při dalších kontrolách čte z git ref/fetch_commit,
nikoli jen z PR snapshotu.

## T048-S01 / AC01, dílčí S03 / AC03 — stav a integrační evidence

Výchozí SHA: `2bebab00c2ca368e3e5a6a4d7daa47fce2addcea`. Problémem byly
zastaralé delivery stavy a chybějící důkaz skutečné sloučené kombinace.

- `docs/production-analysis-progress.md`: W05 MERGED s merge SHA, oprava součtů
  atomických řádků, T051-S01–S03 MERGED bez povýšení jejich verification scope.
- `docs/acceptance-inventory.md`: aktuální merge/evidence oddělené od původních
  lokálních checkpointů; podporované varianty a zbývající SKIP zůstávají explicitní.
- `docs/changes/116_parseExtendedJpqlHql.md`: dřívější pending text výslovně
  označen jako historický a odkazuje na tento post-merge záznam.
- Generovaný index a existující sémantické evidence se obnovují příkazy,
  nikoli ručním přepisem grafu. Žádná produkční logika ani data schema se nemění.

### Provedené kontroly T048

- Cílený skutečný příkaz nad merged main:
  `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q
  tests/test_workflow_profiles.py tests/test_skills.py` — **54 PASS**, 1.49 s.
- Čerstvá úplná sada na `2bebab00c2ca368e3e5a6a4d7daa47fce2addcea`: **2318 PASS /481 SKIP /0 FAIL /0 ERROR**, 828.51 s.
  Log `/tmp/kgmaker-pr97-combined-main.log`; JUnit
  `/tmp/kgmaker-pr97-combined-main.xml`, SHA256 `f2de5006bba57bc71477d6da1fb0d25d6faa38dec684a23a7d9deac8faf37b42`.
  Příkaz:
  `PATH=/tmp/kgmaker-test-venv/bin:/tmp/apache-maven-3.9.9/apache-maven-3.9.9/bin:/tmp/gradle-8.13/bin:/tmp:/usr/lib/jvm/java-21-openjdk-amd64/bin:/usr/local/bin:/usr/bin:/bin
  JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
  KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers
  KGMAKER_REQUIRE_MARKDOWN_PARSER=1 GRADLE_USER_HOME=/tmp/kgmaker-gradle-home
  PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q -ra --durations=10
  --junitxml=/tmp/kgmaker-pr97-combined-main.xml`.
- Obsahové guardy před/po: všechny sledované zdrojové soubory merged main
  a 178 trusted worker/exporter artefaktů shodné; žádné sčítání přes různé snapshoty.
- Dokumentační krok: nulový rozdíl produkčních/test/build a instalovaných instruction vstupů
  proti `2bebab00c2ca368e3e5a6a4d7daa47fce2addcea`, `git diff --check`, lokální odkazy
  změněných dokumentů a součty **119 řádků =69 MERGED +50 PLANNED — PASS**.
  Semantic refresh zachovává původních 42 konceptů a 135 vztahů, přepočítává
  pouze aktuální citace/IDs. `semantic validate`, `memory capture` a generovaný
  `scan/check` — **PASS** po obnově; původní stale kontrola byla explicitní FAIL
  kvůli přesunům README/architecture/CLI ze souběžných PR, nikoli ignorovaná.
  Úplný pytest se neopakuje kvůli samotným delivery metadata změnám.

### Kompatibilita a nedokončený rozsah T048

README, capability/API/CLI příklady, instalační instrukce a Python templates:
bez dopadu, protože tento krok pouze opravuje delivery metadata a zaznamenává
provedené post-merge kontroly. Registry identity/revize/dependencies beze změny.
Schémata graph/store/worker, IDs i ochrana upravených souborů jsou beze změny.

SKIP stále nejsou PASS; širší Kafka/TypeScript/React/mixed-fixture, coroutine,
opt-in Gradle, Windows a second-JDK varianty nejsou tímto plošně certifikované.
GH CI je oddělená doplňující evidence a nebyla vydávána za PASS. Runtime/data
availability, dokončení T003/T004/T049 ani živí hostitelé T050/T051 z těchto
statických a testovacích výsledků neplynou. Další bounded rozsah W06/W07 zůstává
podle registru plánovaný. Příklad: MERGED W05 neznamená runtime SQL execution.

## T045-S02 / S03, R01–R04 / AC02–AC04 — skutečný cílový ref

Výchozí SHA: `2bebab00c2ca368e3e5a6a4d7daa47fce2addcea`. Příčinou chybné
pre-merge kontroly byl zastaralý `base_sha` PR snapshotu. Projektový profil
`.codex/agents/code-review.toml` a jeho registr `.codex/agents/README.md`
proto konkretizují již existující požadavek T045: přečíst cílovou větev přímo
z git ref/primárního commit lookupu, při rozdílu obnovit integraci a review,
po merge porovnat oba skutečné rodiče s oběma schválenými SHA.

Příklad: snapshot s base `193c89b` neprokazuje, že main stále ukazuje na tutéž
SHA; `git ls-remote … refs/heads/main` zde doložil skutečný main `2bebab00`.
Neshoda musí být zveřejněná a dodatečně ověřená, nikoli skrytá starým PASS.

Kontroly: `tomllib` syntaktické načtení profilu a zachování
`model=gpt-6.1-sol`, `model_reasoning_effort=high` — **PASS**.
Skuteční rodiče merge ověřené `git show -s --format=%H%n%P` a aktuální cílový
ref přes SSH `git ls-remote` — **PASS**.
`codex debug prompt-input` — **PASS** po opakování mimo read-only sandbox;
výstup je platný JSON a registr obsahuje `code_review` i správný model.
První pokus v sandboxu skončil **BLOCKED** na read-only filesystemu.
Vykonání všech nových instrukcí v nově spuštěné session z tohoto statického
výpisu neplyne; současný reviewer dostává guard výslovně v předání.
Nový profil sám neprokazuje budoucí merge.

Kompatibilita: oprávnění, model, reasoning effort i GH CI politika beze změny;
projektový profil se neinstaluje přes `kgmaker init`, proto jsou Python templates
a spravované host instrukce bez dopadu. AGENTS a T045 již vyžadují aktuální SHA;
identita/revize registru zadání se nemění. Stavové plochy a acceptance výše
odkazují na tuto opravu. Zbývá nezávislé review tohoto PR a použití guardu při
dalším skutečném merge; automatický revert ani bypass se nezavádí.
