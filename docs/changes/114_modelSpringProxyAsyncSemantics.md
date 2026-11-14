# T003-S05-W04 — Spring proxy, weaving a async semantika

## Zadání a hranice

- Work package: [T003-S05-W04](../tasks/T003-S05-04-springProxyAsyncSemantics.md),
  T003-S05 / T003-AC05; navazuje na sloučené W01–W03 a S04-W03.
- Výchozí main: `a8e75be2fcf7678526579a6607e1977de2f0bd45`.
- PR [#95](https://github.com/p-rum/kgmaker/pull/95); první implementační head
  `d310122e757e881875eb4d498c968af4fe91434d`, tree
  `461df3b78a9214f8a3be63d94de0979dd963905a`.
- Review-fix implementační head `276886c55f16cf09746970342cb2b80ab814745d`,
  tree `ba5660a300bdccf3a3ace52c91868f7bff955b25`.
- Cíl: oddělit declaration, proxy eligibility a runtime execution; self-call,
  Async/event/reactive boundary nesmějí vytvořit smyšlený synchronní execution.

## Skutečná změna

Spring rules `annotation-source-v9-proxy-provenance` přidávají versioned
`spring_proxy_policy`, `spring_proxy_path`, async/event/reactive boundary a
lokalizované UNKNOWN diagnostiky. `may_apply_advice` vznikne pouze pro externí
compiler call s přesnou FIELD receiver identitou shodnou s právě jednou explicitně
anotovanou `@Autowired`/`@Inject`/`@Resource` ACTIVE injection, ACTIVE
specializovanou policy a
podporovanou interceptable JDK/CGLIB deklarací. Všechny pozitivní cesty zůstávají
`execution=NOT_OBSERVED`, `availability=UNKNOWN`.

Transaction, Async, Cache a method-security advice vyžadují odpovídající
`EnableTransactionManagement`, `EnableAsync`, `EnableCaching` nebo
`EnableMethodSecurity`; samotné `EnableAspectJAutoProxy` je jen obecná policy.
AspectJ mode bez weaving artefaktu je UNKNOWN. Same-owner volání má synchronní
`bypasses_proxy` a `@Async` self-call netvrdí scheduling. Process view označí
Async target jako samostatnou boundary jen přes doložený proxy path;
`bypasses_proxy` self-call rozvine synchronně pouze s compiler `THIS`/`SUPER`
receiverem; stejný owner přes parametr nebo jinou instanci zůstává UNKNOWN.
Coroutine/reactive target zůstává
samostatnou boundary a tělo se nerozvine.
EventListener zůstává event-delivery declaration, nikoli přímá call edge.

Veřejná CLI syntaxe a graph/store schema v1/v2/v3 se nemění. Starší Spring rule
stamps jsou čitelné, ale provider vyžádá explicitní reinspection; scan, hook,
view ani offline validace nespouštějí worker, build, aplikaci nebo Spring context.

## Acceptance evidence

| AC | Přímá evidence |
|---|---|
| AC01 | `test_jdk_proxy_async_event_and_self_invocation_are_bounded`, `test_cglib_path_requires_interceptable_concrete_method`, `test_process_stops_at_async_boundary_without_claiming_execution`, `test_process_expands_async_self_invocation_synchronously` |
| AC02 | `test_legacy_spring_rules_remain_readable_but_require_reinspection`; graph v1/v2/v3 zůstává beze změny a framework round-trip validuje každý výsledek |
| AC03 | `test_aspectj_declaration_without_weaving_proof_stays_unknown`, `test_ambiguous_interface_injection_never_creates_stronger_proxy_evidence`, `test_local_or_non_injected_field_never_reuses_injected_proxy_evidence`, `test_same_owner_parameter_receiver_is_not_self_invocation`, CGLIB/JDK incompatible receiver assertions |
| AC04 | README, compiler-inspection, acceptance inventář a stavová matice odkazují na přesnou v9 matici a nepovyšují T003-S05 nad PARTIAL |

## Skutečné kontroly a omezení

- Cílená Spring/proxy/condition/import/build-aware/compiler sada: **54 passed,
  39 skipped**; skipy jsou existující volitelné worker/API prerequisite matice.
- Full `python -m pytest -q`: **1646 passed, 1057 skipped, 76 subtests passed**
  za 43.40 s na druhém review-fix tree.
- Dva parametrické actual-javac případy jsou lokálně **SKIP** s explicitním
  `TOOLCHAIN_UNAVAILABLE`, protože JVM worker není připraven. Explicitní Maven
  příprava workeru byla přerušena zvenčí před publikací artefaktu; nejde o PASS.
- `compileall` a `git diff --check`: PASS; semantic validate **321 concepts /
  30 575 relationships**; scan/check **544 files / 6153 nodes / 43 947
  relationships**.
- CI na původním review headu `cbe4a0e42ed97a51ac1c11c980f91d4c5b92fb4d`
  má u všech sedmi jobů `steps=null` a `logs_url=null`, tedy administrativní
  NOT_RUN podle T045. Nezávislé review `PRR_kwDOUyD9Wc8AAAABX94H6w` našlo dva
  P1: Async self-call v process view a chybějící receiver provenance. Oba jsou
  opravené FIELD bindingem, proxy-evidence gate a přímými negativními testy;
  opravný head vyžaduje nové exact-pair review. Jeho CI run `43635104440` má
  stejný administrativní NOT_RUN stav: všech sedm jobů bez kroků a logů.
- Druhé nezávislé review `PRR_kwDOUyD9Wc8AAAABYBNa9Q` na headu
  `0de66dde234d7725d06073ed81095c3abca18556` našlo další dva P1: neanotované
  pole se nesmělo stát injection a shodný method owner nebyl důkaz `this` callu.
  Oprava vyžaduje kanonickou explicitní injection anotaci a compiler
  `receiver_binding_kind=THIS|SUPER`; ručně inicializované pole i parametr jiné
  instance mají přímé negativní regrese a čekají na nové exact-pair review.

Neověřený runtime dispatch, skutečné advice execution, task scheduling, event
delivery, reactive subscription, AspectJ weaving a širší meta/class-level
varianty zůstávají UNKNOWN. T003-S05 i celý T003 proto zůstávají PARTIAL.
