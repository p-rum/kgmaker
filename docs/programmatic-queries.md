# Programmatic persistence query intent — T003-S06-W07

`inspect code` projects a bounded Java/Javac query subset into the existing ORM
graph. The JPA rule is `annotation-source-v10-programmatic-queries`, and saved
intent uses `programmatic-query-2`. [Change129](changes/129_criteriaSpecificationQuerydsl.md)
records delivery and executed checks. This does not complete the wider S06 milestone.

| API | Verified source shape | Explicit boundary |
|---|---|---|
| Jakarta Persistence3.1 Criteria | `getCriteriaBuilder`, `createQuery(Class)`, `from(Class)`, optional `select(root)`, `where(equal(root.get("field"), value))`, `getResultList` | One root and local straight-line builder; class/string literals or their direct local aliases; dynamic class, attribute or predicate is UNKNOWN/PARTIAL |
| Spring Data JPA3.4.2 Specification | A directly typed `Specification<Entity>` lambda or an explicit direct implementation of `toPredicate`, returning `equal(root.get("field"), value)` | Javac must prove the actual dependency interface method override with the matching descriptor; `@Override` is optional. Same-name overloads have no Specification authority; arbitrary factories, composition, control flow and custom helpers are unsupported |
| QueryDSL5.1 Jakarta JPA | `JPAQueryFactory.selectFrom(root).where(root.field.eq(value)).fetch()` | Exact compiler `EntityPathBase<Entity>` type, **final** source member initialized through dependency `BeanPath.createString/createNumber`; source Q-types generated with actual APT in tests. Mutable members, dynamic Expressions paths and predicates remain partial without attribute authority |
| Custom repository fragment | One source interface method shared by a compiler-qualified repository and one directly implementing concrete class, whose method contains the bounded query | Identity and descriptor must match; multiple implementations retain the local query but create no repository binding; no bean-selection or runtime dispatch claim |

Criteria `where` replaces previous restrictions; an empty call clears them. QueryDSL
`where` accumulates restrictions. Direct local aliases share this bounded builder
state. Passing query state to an unknown source or dependency helper, capturing it
in a lambda, hiding it in an unsupported expression/cast, or escaping into a field
leaves UNKNOWN without root/filter edges.

`EntityManager.createQuery(criteria)` captures the executable definition; subsequent
Criteria builder changes cannot modify that snapshot's filters. QueryDSL `fetch`
captures the definition at that call. Multiple executable snapshots in one method
are retained as separate UNKNOWN intents (`MULTIPLE_QUERIES_UNSUPPORTED`) without
root/filter edges; the bounded analyzer does not combine them into one final query.

Only consumed `where`/Specification predicate attributes produce `filters_by`.
An unused `root.get(...)`, unused predicate, or projection-only selector does not
become a filter. Scalar projections produce `PROJECTION_UNSUPPORTED`; joins,
subqueries, bulk updates/deletes, provider extensions, loops, builder reassignment,
multiple roots/queries, arbitrary interprocedural composition and Kotlin source
are outside this matrix. Other predicate operators and terminal methods are
explicitly unsupported. The Javax namespace branch has no separate actual corpus
in this delivery and is not a verified API-version claim.

Each `orm_query` has `query_language` CRITERIA, SPECIFICATION or QUERYDSL,
`query: null`, `method`, `entity`, `operations`, `analysis_status`, `validated`
and concrete `gaps`. It also retains `compiler_witnesses` with original call-site,
resolved target, source range and SHA. `declares_query`, `query_reads` and
`filters_by` reuse the existing model. `repository_uses_fragment` describes a
unique declaration composition. FRAMEWORK_DERIVED is the evidence layer;
compiler resolution proves the attributed calls, not framework execution.
`COMPLETE` means this bounded static pattern, never a complete SQL plan.
`execution` is always NOT_OBSERVED and `availability` is UNKNOWN.

Any Javac error in the selected source set leaves programmatic query IR
UNAVAILABLE and the projected intent UNKNOWN. This includes duplicate qualified
entity definitions even when the query method itself has no local diagnostic.

Resolution uses exact compiler entity owners and the final effective ORM mapping
inside the selected context. FIELD/PROPERTY, inherited attributes, XML overrides
and persistence-unit exclusion retain their existing rules. A conflicting access
strategy or unmapped attribute cannot acquire filter evidence. Same-simple-name
entities do not compete through a name lookup. Source classes shadowing official
API names cannot provide dependency authority. Replay checks current source
hashes, context freshness, original call sites and dependency provenance again.
The last valid store remains unchanged on invalid protocol, strict rejection,
cancellation or timeout; scan/hook use the validated saved context without workers.

Explicit usage after preparing the trusted worker and real classpath:

```bash
kgmaker inspect code --root . --classpath /path/jakarta.persistence-api-3.1.0.jar --classpath /path/spring-data-jpa-3.4.2.jar --classpath /path/querydsl-core-5.1.0.jar --classpath /path/querydsl-jpa-5.1.0-jakarta.jar
kgmaker query "CRITERIA" --root .
```

Supply the complete compile classpath, including transitive APIs and existing
QueryDSL generated sources. Explicit build/exporter workflows can provide a
content-bound compiler context; `inspect` itself uses `-proc:none` and does not
run annotation processors. The fixture README describes its separate, authorized
APT setup. No command here starts an application, connects to a database, runs
migrations, installs packages or synthesizes SQL.

Worker payload fields are additive with strict version/shape/source validation
whenever present. Omission of a version marker cannot bypass validation of a new
payload. Historical workers without these fields and graph/store v1/v2/v3 remain
readable, with no invented programmatic query proof.
Saved programmatic intent version1 is readable but is rejected for ORM replay;
explicit reinspection produces version2 snapshots and override proof. The additive
Javac query IR remains version1; `query_override` references the compiler-resolved
dependency method, is validated on import, and is checked again on replay.
