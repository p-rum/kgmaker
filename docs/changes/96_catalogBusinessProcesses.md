# T033 — explicitní read-only katalog procesů

T033-S01–S05/AC01–AC06. Stack T0324fea, source APPROVE, full závislostí pending.
Rev2 upřesňuje current/history, stable ID, one-hop explicit alias a oddělené T032
review status. Žádný archive/index ani implicitní discovery/zápis.

Alokace96 ověřena přes všechny worktrees/main/registr a všech7 openPR file lists;
maximum95 T016, integrate8 potvrdil žádnou96. Implementace/testy zatím NOT_RUN.

## Skutečné změny a testy

Nový process_catalog.py používá existující T023/T024/T032: bounded read-only snapshot
projection, exact ID/scope, explicitní current/history a one-hop aliasy s úplnými
member/revision/trigger/review states. Není fuzzy merge ani přenos approval mezi
členy; technická evidence/runtime UNKNOWN se nezvyšuje. Technical/diagnostic prose
omitted+hash, fixed safe errors. T026 business_process a všechny parent moduly/testy
zůstávají beze změny. Python příklad/limity: ../process-catalog.md.

Veřejný RED6FAIL0.49s před implementací; inicializační fixturechyba coverage counts
zachována6FAIL0.43s. Rozšířený audit30PASS4FAIL2.10s zachoval3test-fixturechyby
(trigger entry/technical status) a skutečnou typed ViewDocument compatibility gap;
opraven bounded shallow inspection před serializerem, původní modelové guards beze
změny. Current37PASS1.62s. Coalesced10modules306PASS94SKIP9.48s;94compiler SKIP
nejsou nový toolchain důkaz. Full/review/publication NOT_RUN, source checkpoint
požadován před jakýmkoli heavy/full. Žádný nový persistent formát/migrace/nativebuild.

## Integrace aktuálního main2026-11-05

Zdrojový refresh T030a12a8b8→T031361684e→T032af76ff1→T033708685e má explicitní
main3e5ef0f (230 immutable episodes). Všechny původní procesní moduly/testy a27workers
zachovány byte-exact, T03032AST+prefix zachovány. Obě připravené parent fixture sady
871hashů a626externích pinů zůstaly přesné; nebyl nový build/native/tool/M2 zápis.
All-suite kolekce (nikoli test run)1990⊆2066⊆2102⊆2139, exact76/36/37nových cases;
staré1758/1762/1838kolekce zůstávají podmnožinami. Bounded current-parent regrese
315PASS94SKIP6.19s zahrnuje navíc současné schema/Kafka API-negatives.

T0323652 a T0333b24 mají oddělené nezávislé SOURCE APPROVE; nový integrační exact-pair
review a full důkaz zůstávají PENDING. Jediný starý T030/T031 fulla359 skončil na
kapacitním preflightu5,062,799,360<5GiB,0testů; není FAIL testů ani PASS, bez retry.
Případný společný descendant full řídí koordinátor po source/superset/native proof.
