# Actual Criteria / Specification / QueryDSL fixture

The source uses real Jakarta Persistence3.1, Spring Data JPA3.4.2 and QueryDSL5.1
APIs. `tests/test_criteria_queries.py` declares exact Maven coordinates and fails
when required dependencies are absent with `KGMAKER_REQUIRE_WORKERS=1`.
Dependencies must be prepared explicitly outside scan/inspect. For the Jakarta
QueryDSL JPA artifact, for example:

```bash
mvn dependency:get -Dartifact=com.querydsl:querydsl-jpa:5.1.0:jar:jakarta -Dtransitive=false
```

The test's explicit fixture setup runs JDK21 `javac --release 21 -proc:only
-processor com.querydsl.apt.QuerydslAnnotationProcessor` against the genuine
`@QueryEntity`/JPA entity, with the declared processor dependency classpath. It
writes QOrder under `src/generated/java`, then the ordinary inspect workflow uses
Javac attribution with `-proc:none`. No hand-written replacement QueryDSL API or
Q-type is used for positive acceptance. The deliberate generated-member negative
changes its actual factory literal to an unmapped property.

Positive patterns are bounded entity selection and equality predicates in
Criteria, Specification lambda/explicit implementation, QueryDSL String/Number
paths and a repository fragment. Negative cases include dynamic root/attribute/
predicate, ambiguous fragments, official API source shadowing, unused selectors,
unsupported projections, access conflicts, stale context and invalid IR.
See [capabilities](../../docs/programmatic-queries.md) and
[change129](../../docs/changes/129_criteriaSpecificationQuerydsl.md).

Actual compilation and APT establish static fixture facts only. No JPA provider,
Spring context, SQL execution, database availability, or Kotlin support is proved.
