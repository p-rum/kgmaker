# TypeScript callback a generic evidence

Worker4 / TypeScript5.7.3 / Node24.19.0 používá skutečný Program/TypeChecker.
Re-export aliases a vybrané overload signatures zůstávají compiler-proven declared
targety; instantiated call signature je metadata konkrétního caller checkeru.
Declaration, CFG a parameter IDs pocházejí z owner Programu daného projektu,
včetně odlišných strictNullChecks nastavení consumeru. Repo-qualified identity
nedovolí sloučení stejně pojmenovaných funkcí různých repositories/projects.

## Podporovaný omezený kontrakt

- Přímé funkce, arrows a const alias řetězy mohou doložit konkrétní callable.
  Selected overload signature zůstává zachována; nemění se svévolně na první body.
- Generic higher-order API přes barrel exports zachovává named i inline callback
  argument-to-parameter vazby. Overload symbol s právě jedním implementation body
  mapuje pevné parameter positions do tohoto body; rest param mapping se neodhaduje.
- Invocation callback parametru má `declared_target: null`, reason
  `CALLBACK_PARAMETER_OPEN_WORLD` a případné `dispatch_candidates` z explicitních
  lokálních bindings. Vždy `dispatch_complete: false`: jeden pozorovaný caller ani
  jedna candidate funkce nejsou důkaz jediného runtime targetu.
- Union callback je `AMBIGUOUS_CALLBACK`; známé function větve mohou být candidates.
  Union argument do higher-order API má candidate binding evidence pro každou větev.
  Mutable alias/property je `MUTABLE_CALLBACK`; `any`/unknown je `DYNAMIC_ANY`.
  Tyto větve nevytvoří resolved target z náhodné první signature nebo initializeru.
- Ambient compiler call signatures, např. `StringConstructor`, zachovávají declared
  contract resolution. To není důkaz konkrétní runtime implementace.

Depth alias/expression proof je nejvýše16 a nejvýše64 candidates na local callback
parameter. Nad limit se zachová bounded PARTIAL graf s `CALLBACK_TARGET_LIMIT` a
incomplete dispatch. Dependency-only callback parametry, jejichž body se neanalyzuje,
nespotřebují tento local budget. Stávající symbol/call/input/response limity platí dál.

Heap/value-flow, returned functions, default/rest/destructured callback inference,
interprocedural parameter forwarding a úplná runtime dispatch množina nejsou odvozeny.
Samostatná overload signature a implementation body nemají nově vytvořený navigation
bridge. Selected signature i body parameter bindings jsou doložené odděleně;
callgraph path přes tuto hranici může zůstat UNKNOWN/PARTIAL. Nepřidává se fiktivní
runtime dispatch candidate pouze proto, aby byla cesta dosažitelná.
Neznámá binding může zůstat bez candidates. Framework UI/BE–FE flow, persistent
compiler cache a celý T003-S08 nejsou tímto dokončeny. Source IR neprokazuje runtime
pořadí, provedení callbacku ani dostupnost dat.

## Offline čtení a kompatibilita

Protocol1 a graph/store v1/v2/v3 se nemění. Candidate evidence používá existující
`may_dispatch_to`/`DISPATCH_CANDIDATE`; graph model ani callgraph nepotřebují nový
katalog. V3 roundtrip zachová call sites, candidate metadata a evidence. Legacy
schema čtení a scoped W02 freshness zachovávají původní kontrakt. Neplatný/dangling
candidate je odmítnut před publikací a poslední validní store zůstane byte-identický.
Offline provider a call navigation nespouštějí Node, buildy, instalace ani aplikaci.

```sh
kgmaker inspect frontend --root ./frontend --tsconfig tsconfig.json
kgmaker callgraph callees --root ./frontend --symbol "$CALLER_ID"
kgmaker callgraph callees --root ./frontend --symbol "$CALLER_ID" --include-dispatch-candidates
```

Druhý příkaz vrací declared calls; třetí výslovně zahrne i možné dispatch targety.
ID vyber z konkrétního indexed symbolu, nevymýšlej ho z názvu. Skutečná fixture je
`fixtures/typescript-callbacks`; testy a pravdivý local/full/CI stav jsou v
[note53](changes/53_resolveBoundedTypeScriptCallbacks.md). CI je samostatný acceptance
gate a lokální důkaz jej nenahrazuje.

Lokální Linux source-final matice: actual15PASS61.69s a full582PASS/10SKIP641.43s
s vlastním workerem, pinned toolchain a mandatory workers/K2/Spring prerequisites.
Required CI zůstává PENDING kvůli GitHub Actions billing/quota; nový Windows
callback proof ani merge acceptance nejsou tvrzeny. Přesné příkazy/skips: note53.
