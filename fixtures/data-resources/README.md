# Actual data-resource projection APIs

T015 compiler integration reuses API dependencies explicitly prepared by
`mvn -B -ntp -f fixtures/data-resources/pom.xml compile`: Jakarta Persistence3.1.0,
Spring Data JPA/Commons3.4.2 and Spring6.2.2. The lock records actual JAR/POM
SHA-256 and published POM license names; no dependencies are redistributed.
The dedicated POM pins all ten API artifacts and excludes transitives; it has no
application source or database/bootstrap execution. Preparation is an explicit CI
step, while projection never fetches missing APIs.

The test writes a temporary source repository and migration, performs actual
Javac-backed inspection, then calls the existing workspace/Flyway projection.
It never starts a Spring context, application or database. Capture is explicit;
subsequent resource projection prohibits child processes and preserves inputs.
