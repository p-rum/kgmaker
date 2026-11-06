# Actual HTTP API fixture

Pinned Spring6.2.2, Reactor3.7.2 and Spring Cloud OpenFeign4.2.0 API JARs are
read from an explicitly prepared Maven cache. The lock pins JAR and published
POM bytes plus the POM's declared license name. Dependencies are not vendored.
Explicit `mvn -B -ntp -f fixtures/http-client-execution/pom.xml compile` prepares
the APIs; tests only analyze source with Javac/K1/K2 and never instantiate an
application, create a Spring context or send an HTTP request.
