# Actual manual and generated field mappings

T003-S07-W03 fixture, [`field-mapping-1` matrix](../../docs/field-mapping.md),
[change124](../../docs/changes/124_fieldAndMappingFlow.md).

`tests/test_field_mapping_flow.py` copies these inputs into an isolated temp root,
explicitly runs JDK21 `javac` with local MapStruct1.6.3 processor, then calls public
`inspect_jvm` on handwritten and actual generated Java source. Generated output
is not hand-maintained or inferred from the `@Mapper` annotation.

Ground truth: `Manual.copy` and generated `map` transfer `Source.publicName` to
`Target.publicName` and source private `name` through final getter/identity helper
and final setter. `Boundaries.overloaded` selects the second String argument.
`transformed`, `ambiguous`, `unknown`, `overwritten`, `loop`, and `vararg` must not produce
field-to-field mappings. These cases cover unknown business transformation,
ambiguous branch definitions, virtual dispatch/recursion, overwritten locals and vararg packing.
Fields are declaration identities, not object instances. This fixture proves no
runtime execution, persisted value or business equivalence.
