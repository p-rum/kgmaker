# Pinned Spring import API fixture

This fixture prepares Spring Framework 6.2.2 APIs for the actual Javac selector
tests. It does not start Spring or execute an ImportSelector. Prepare explicitly:

```bash
mvn -B -ntp -f fixtures/spring-imports/pom.xml compile
```

Maven resources 3.3.1 and compiler 3.13.0 are pinned. CI runs this preparation
before the mandatory worker tests. The tests never invoke Maven, install APIs,
or download dependencies. Set `KGMAKER_TEST_MAVEN_REPOSITORY` when the prepared
repository is outside `~/.m2/repository`.

`dependencies.lock.json` binds the six API/classpath JARs to SHA-256, coordinates,
worker protocol v1 and the Apache-2.0 license entry inside each JAR. Tests verify
these entries before inspection. Missing or altered inputs fail under
`KGMAKER_REQUIRE_WORKERS=1` or `KGMAKER_REQUIRE_SPRING_IMPORTS=1`; otherwise the
actual toolchain test is explicitly skipped. Hashes establish content identity,
not an additional claim of publisher authentication or network availability.

Spring JARs are external test inputs and are not redistributed in the kgmaker
worker wheel. No Spring runtime, selector result or application build is inferred
from their presence. The temporary test projects exercise the static import,
literal/direct/inherited/deferred selector, filter/group and unsupported paths.
