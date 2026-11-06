# Explicit Kafka code API fixture

Reuse Spring Kafka3.3.2 and Spring6.2.2 JAR/POM/license pins from
`fixtures/process-triggers/dependencies.lock.json`. This POM explicitly adds only
Kafka Clients3.8.1 and Spring Retry2.0.11 signature APIs from Spring Kafka3.3.2's
published POM, with no transitive fetch. The lock records actual cached artifact
and license hashes; tests require them and never download or start a broker.

Prepare both API-only POMs explicitly before required compiler acceptance:

```bash
mvn -B -ntp -f fixtures/process-triggers/pom.xml compile
mvn -B -ntp -f fixtures/kafka-code-bindings/pom.xml compile
```

This contains no application, Spring context, topic administration or transport.
Direct Java source calls are examined by the shared Javac frontend in both worker
backends; Kotlin producer bodies stay UNKNOWN in this bounded matrix.

Listener declarations require the exact captured KafkaListener method annotation,
explicit groupId and exact topics or a regex candidate. Java annotations are
available in both worker backends; Kotlin K1 supplies annotations. The pinned K2
source model omits method annotations, so Kotlin K2 listeners remain UNKNOWN.
Java producer support is the exact two-argument send(String,Object) API with a
direct ASCII string literal topic. Constants, escaped literals, wrappers,
ProducerRecord/NewTopic and Kotlin producer bodies remain unsupported.
