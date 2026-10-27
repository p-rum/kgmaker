# Actual data-resource projection APIs

T015 compiler integration reuses API dependencies already prepared by the existing
`fixtures/build-inspection/maven/pom.xml` build: Jakarta Persistence3.1.0,
Spring Data JPA/Commons3.4.2 and Spring6.2.2. The lock records actual JAR/POM
SHA-256 and published POM license names; no dependencies are redistributed.

The test writes a temporary source repository and migration, performs actual
Javac-backed inspection, then calls the existing workspace/Flyway projection.
It never starts a Spring context, application or database. Capture is explicit;
subsequent resource projection prohibits child processes and preserves inputs.
