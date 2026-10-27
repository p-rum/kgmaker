# Return výraz a call-result do consumer použití

T003-S07-W02 AC01–AC04, explicitní stack na PR47
`e1487098632cd90892be3760f30676560e15d062`. Implementační plán, nikoli hotový S07.
Před implementací source/graph/native recon ověřil stávající W01 value argument
nodes a žádné typed return-consumer facts. Java/K1/TS mají return/assign/call IR,
ale chybí binding/projection identities. K2 Kotlin nemá source CFG a zůstane UNKNOWN.

Reuse model/store/context/evidence a graph1/2/3, optional typed IR/protocol metadata;
žádný parallel catalog, source-label inference ani runtime value observations.
Actual branching/nullable/chained/destructure RED, skutečné toolchain positives
plus ambiguity/ref/void/opaque/recursive negatives, focused/full, scoped semantic,
memory a přesné výsledky budou doplněny podle skutečně dodaného kódu. Note66 je
rezervována rootem; žádné CI retries, merge nebo externí publikace autorem.

## Dodaná implementace a dosavadní ověření

Optional `return-consumer-ir-v1` používá skutečné Javac/K1/TS typy, declaration
bindings a source ranges; existující model/value nodes a versioned `returns_to`
evidence propojují assignment, argument, receiver a deklarovaný návrat. Branch
alternativy, nullable safe-chain a jednotlivé zápisy zůstávají oddělené. K1 generated
data-class components a přímé TS tuple/object literal bodies mají projection proof;
custom component/opaque dispatch, recursive/async/callable/void/any/unsupported CFG
zůstávají UNKNOWN. K2 Kotlin bez source CFG nevymýšlí bindings.

Process JSON/Markdown, data-flow a impact přenášejí static proof; workspace kvalifikuje
identity. Legacy graph/store1/2/3 se čtou, explicitně stará verze pravidel je STALE
offline. Invalidní IR se odmítá před publikací a bez změny store. Nevzniká runtime
value ani execution observation; aplikace, síť a instalace se nespouštějí.

Skutečná RED sada: 4 FAIL za 28.40s před implementací. Aktuální vlastní toolchain
build: K1 PASS22.14s, K2 PASS13.52s; sequential build logs v
`/workspace/return-consumer-proof`. Nový modul: 25 PASS50.15s; průběžná integrace
67 PASS63.94s a protocol/control/mandatory-CI35 PASS2.01s. Plná aktuální sada je
zařazena pod sdíleným flock; výsledek bude doplněn, dosud není tvrzen PASS.

Příklad: po explicitní inspekci `kgmaker flow render --root . --entry '<method-id>'
--view process --format json` vrací call blocks s `return_consumer_bindings`.
Fixture `fixtures/return-consumer` a `tests/test_return_consumer_flow.py` dokládají
AC01–04 v této omezené matici. S07/T003 jako celek nejsou dokončeny; remote CI je
pozastaveno kvůli billing limitu a autor neprovádí publish/merge.
