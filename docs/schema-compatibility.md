# Offline ORM/schema compatibility — W08 bounded scope

Delivery status (2026-11-07): T003-S06-W08 is MERGED in [PR64](https://github.com/p-rum/kgmaker/pull/64) (`3bef611`).
Current full acceptance is NOT_RUN in this documentation audit. Historical
checkpoint results and pre-merge review gates below describe their stated SHA.
Use the [current delivery inventory](production-analysis-progress.md) and
[change111](changes/111_reconcileDeliveryStatus.md) for present status.

This work began as a draft stack on W04 checkpoint7dc1016. Dependency PR62 is
now merged. The bounded implementation has strict full1591PASS/10optionalSKIP on ced9717 and current Return-parent174PASS/0SKIP on67b8341; final independent exact-pair review remains separate. It does not establish T003-S06
completion or deployed/populated data.

`kgmaker schema compatibility --root /path/to/repo --config flyway.json --database money --stream main --target 1 --context CONTEXT_ID`

The command uses the existing current-graph provider, offline Replay and framework
projection. It does not run workers, builds, migrations, applications or a DB.
A matching content-verified compiler context must already exist from an explicit
inspection. A different selected target/context cannot borrow its proof.
`--workspace workspace.json --repo app --database money --stream main` selects an
explicit declared workspace realm; the workspace manifest's replay selection must
match the chosen target. Existing inspect/diff commands remain available.

Python: `schema_compatibility(schema, graph, context_id=...)`, imported from
`kgmaker.schema_replay`, returns versioned per-attribute/per-dimension results:
COMPATIBLE, CONFLICT or UNKNOWN, with original IDs and evidence references. Inputs
are immutable explicit snapshots; provider/current-input responsibility remains
with the caller. This pure function neither authenticates a live database nor
claims current filesystem state beyond the supplied validated content binding.

The bounded positive subset is compiler-owned FIELD/PROPERTY and supported inherited FIELD attributes with exact JVM
primitive/official java.lang.Long/Integer/String or java.math.BigDecimal descriptor,
explicit effective Column mapping, selected physical table/column in the same
realm/target, declared nullability/decimal dimensions and single-column PK/UK.
Custom classes with the same simple names do not acquire these mappings. SQL
normalization has an explicit scalar-family whitelist; unsupported UDT/domain
forms are UNKNOWN. Nullability is checked in persistence direction; compiler
@Id requires a nonnullable key. Missing decimal dimensions are UNKNOWN. A composite
identifier or unsupported unique-index expression cannot prove single-column key
equivalence. Missing explicit columns remain visible; absence is CONFLICT only
against a COMPLETE selected-table replay with current explicit mapping proof.

PROPERTY/inherited declaration witnesses are exact compiler-backed graph relations;
physical columns are linked by the same selected-realm matcher as declared FIELD mappings.
The expanded subset passed the actual grouped matrix and strict full; see note78 for exact source attribution. Unsupported
or missing canonical bindings remain UNKNOWN. XML effective constraints without
typed proof, naming strategies, inferred mapping, converters and unsupported FK
association tuples remain UNKNOWN. The narrow FIELD ManyToOne FK dimension reuses compiler→association and
existing owner/target table proofs, checks the target against the canonical field
descriptor, and compares explicit single JoinColumn name/referencedColumnName
with structured Replay FK tuples and target PK/UK. Exact matches are COMPATIBLE;
a different proven tuple is CONFLICT; missing FK without an explicit policy stays
UNKNOWN. XML/mappedBy/collections/composite/defaulted references remain UNKNOWN.
FK replay records exact ordered referenced columns when explicit and never
invents omitted columns from a display name.
Referenced-column/table renames update this tuple; unsupported drop/cascade effects
fail closed. Replay remains MIGRATION_DERIVED and never deployed/populated evidence.

Each physical graph node carries schema_snapshot_fingerprint of deterministic
config, objects, inventory, replay status, parser version, diagnostics and
initial-snapshot provenance. Every ancestor migration path/SHA must be captured,
even when last_change only records a later rename. These
are all replay inputs used by the compatibility report, including active column
nullability/type and constraint/key contents. History is not read by this report;
checkpoint/cache statistics and subsequently added reporting metadata are excluded.
Legacy physical nodes without this binding stay readable but produce UNKNOWN.
Compiler→ORM declaration edges bind exact field/getter identity, scope/context,
source SHA and canonical descriptor; proof tuple/digest is checked, including
canonical repository qualification in workspace snapshots.

The same projection is included in existing schema coverage and analysis reports.
Compatibility adds no value-path edge and never sets AVAILABLE, FIT or deployment
verified. Existing supplied-observation availability gates remain separate.

Parser postgres-ddl-4-creation-identity / compatibility orm-schema-2-creation-identity
add structured creation name components, kind, realm, origin and optional
incarnation. Stable IDs are validated from that creation metadata; current
schema_object components remain the only names used to match mappings. No opaque
ID splitting or previous_names lookup is used. Rename preserves object identity;
drop/recreate uses a new incarnation when the creation name collides with history.
Legacy metadata remains readable but cannot silently gain a new binding.

Consumed annotation members must agree with canonical captured Node values and
the owning Entity/MappedSuperclass javax/jakarta namespace. Other annotation
metadata does not define schema compatibility. Exit0 means a report was generated,
not that every dimension is compatible; invalid replay retains inspect-style exit2.
