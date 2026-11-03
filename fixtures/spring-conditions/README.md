# Explicit Spring condition API inputs

This fixture pins Spring6.2.2 and Spring Boot3.4.2, with artifact SHA-256 and
in-JAR Apache-2.0 license entries in dependencies.lock.json. Preparation is an
explicit action: `mvn -B -ntp -f fixtures/spring-conditions/pom.xml compile`.
Tests only read these API/compiler inputs. They never construct a Spring
application context, execute user beans, fetch packages or discover services.

`tests/test_spring_conditions.py` creates labelled Java/Kotlin source fixtures
against these actual annotations. Set `KGMAKER_TEST_MAVEN_REPOSITORY` for an
explicit prepared Maven repository and `KGMAKER_REQUIRE_SPRING_CONDITIONS=1`
to turn absent/changed prerequisites into FAIL. Optional local runs SKIP them.
The class inventory is an explicit selected-context input; it is not a runtime
classpath probe or deployment/availability proof.
