# Kafka interface catalogue

`kgmaker.interfaces.project_kafka_interfaces` reads the explicit workspace and
its content-bound public snapshot. The same workspace checkouts and private
saved compiler indexes must remain available: this is not a portable graph-only
API. The adapter reuses upstream canonical Kafka validation and read-only binding
replay; it never inspects, builds, writes a cache, starts an application or contacts
a broker. Inspection is a separate explicit prerequisite.

```python
from kgmaker.workspace import load_workspace, snapshot_workspace
from kgmaker.interfaces import project_kafka_interfaces

workspace = load_workspace(manifest)
_, coverage, _, graph, _ = snapshot_workspace(manifest)
view = project_kafka_interfaces(workspace, graph, scope="production",
                                source_coverage=coverage)
print(view.to_json())
```

T019 exposes the same catalogue through an explicit local capture:

```bash
kgmaker architecture interfaces --catalog kafka --capture-local --workspace workspace.json
```

For Javac LF and CRLF sources, the catalogue validates the private compiler
capture against the local scanner inventory, then checks the original byte hash
against the qualified workspace inventory. A line-ending edit requires explicit
inspection before reusing those Kafka facts. [Verified scope](changes/160_bindJvmSourceBytes.md).

The shared `interfaces` ViewDocument contains `kafka_interface` occurrences with
`direction=PRODUCER/CONSUMER`, original call/listener IDs, broker realm, exact topic
or regex selector, consumer group, and explicit message contract references when
proved. Distinct realms and groups retain the original upstream subscription
logical ID and capture revision identity. URL, name, payload or DTO similarity is
never a join. A regex remains a candidate without expansion or a producer match.

Configuration-only/schema1 entries remain visible declarations with
`code_binding=UNPROVEN` and unresolved status. NewTopic/ProducerRecord construction
alone creates no publisher. A canonical code declaration without an explicit
binding retains UNKNOWN broker/contract. A missing private authority or malformed
relevant tuple raises `InterfaceProjectionError`; no fact is rebuilt from mirrored
Node/symbol fields. Unselected contexts cannot supply current code evidence.

Supported upstream subset: Java listeners with explicit group and canonical
annotation in both JVM backends; Kotlin K1 listeners; Java canonical
KafkaTemplate/KafkaOperations `send(String,Object)` with a direct ASCII literal
topic. Kotlin K2 method annotations remain UNKNOWN, without source parsing fallback.
Repeatable/meta annotations, SpEL, default-group inference, wrappers and wider
producer overloads remain upstream boundaries.

Evidence kinds and supporting/contradicting/unknown buckets remain separate.
Static declarations do not prove listener activation or transport delivery:
`delivery=NOT_OBSERVED`, activation/data/runtime/deployment availability UNKNOWN.
Coverage is at most PARTIAL. No new CLI, store or persistent format is introduced;
existing HTTP provider and consumer APIs and identities remain unchanged.
