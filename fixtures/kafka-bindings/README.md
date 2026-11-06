# Declared Kafka binding fixture

Three local checkouts and two logical cluster IDs exercise source-only Cloud
Stream `.properties` configuration. The active `blue` override changes `orders`
to `orders-blue`. Producer and consumer match cluster-a, topic, exact Order.json
SHA, release r1 and production scope. No broker endpoint, credential, application,
or transport is needed. IDs and release/payload labels are explicit declarations.

```bash
kgmaker query --root . --workspace fixtures/kafka-bindings/workspace.json orders-blue
```

Change only the consumer `.binder=alpha` to `.binder=beta`: the same topic in
cluster-b does not match cluster-a. Change its release to r2: it no longer matches
r1. `${missing.topic}` or a partially dynamic topic stays UNKNOWN. This fixture
does not prove delivery, deployment, schema compatibility, or source code binding.
