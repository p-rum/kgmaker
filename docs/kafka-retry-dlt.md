# Kafka retry/DLT policy declarations — W05 draft

T003-S07-W05 adds a bounded Python adapter `kafka-retry-1` to the existing JVM
inspection pipeline. It consumes captured canonical Kafka listener methods and
compiler annotations, preserving their original IDs. It never starts Spring,
application code, a broker or an annotation processor.

The supported declared subset is an explicit `RetryableTopic` with literal
`attempts`, `retryTopicSuffix` and `dltTopicSuffix`, plus one canonical matching
`DltHandler` in the same owner and selected context/scope. Only the selected
Spring Kafka3.3.2 whole-JAR SHA and annotation resource hashes are admitted.
Duplicate resources, manifest classpath indirection, protected multi-release
resources and source-shadowed API declarations remain UNKNOWN. Official3.2.0 is
explicitly unsupported even though its annotation class bytes match3.3.2.

Java and Kotlin K1 actual inputs are the supported capture matrix under test.
Kotlin K2 annotation limitations stay UNKNOWN; no source-text fallback is added.
Custom error handlers/factories, expressions, nondefault backoff/strategy,
ambiguous DLT handlers and unknown APIs do not create a declared DLT edge.
Default nested annotations are not parsed or executed. No concrete retry schedule
or derived topic/destination list is produced.

`flow render --view process` JSON has a separate `kafka_policy_boundaries` list;
policy relations are not executable CFG edges. Markdown lists the same static
policy boundaries separately. Example after explicit inspection of a prepared
project, using its existing canonical method ID:

```sh
PYTHONPATH=src python -m kgmaker flow render --root /path/to/project \
  --entry 'CANONICAL_METHOD_ID' --view process --format json
```

A policy declaration is FRAMEWORK_DERIVED only for the supported API. Unknown API
candidates use SYNTAX_CANDIDATE. Execution and delivery remain NOT_OBSERVED;
activation, runtime and data availability, scheduling and destinations remain
UNKNOWN. These facts do not certify compensation, retry success or transport.

Each boundary rechecks canonical public Node/symbol/selected realm/source hashes,
original compiler annotation/containment proof, W04 listener identity and proof,
DLT's own declaration proof, and exact policy edge/proof tuples. A relevant forged
edge produces a local unresolved policy boundary; unrelated policies remain valid.
Legacy graphs without policy facts gain no inferred retry policy. Version and
ordered-classpath stamps participate in context identity/freshness checks.

Validation is in `tests/test_kafka_retry_dlt.py`; current draft results and
remaining mandatory runs are recorded in [note87](changes/87_captureKafkaRetryDlt.md).
The Kafka revision2 parent is an explicit draft dependency. W05 is not ready until
its required actual matrix, frozen full suite and independent source review pass.
