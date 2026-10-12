# Offline multirepository fixture

Tests copy these sources into three local Git repositories with identical
`src/model.ts` paths and `Client.balance` names. No network clone is used.

Hand-specified schema: `public.exposure` has `id bigint NOT NULL` and
`decline numeric(18,4) NOT NULL`; `old_decline` is renamed and `obsolete` dropped.
Latest clean bootstrap includes `exposure_view`, historical target 2 does not
claim current repeatable contents. The contract links ExposureOutput.decline to
the field used in a single-response UI and explicit assertions. These static
links include INFERRED steps and do not claim runtime PASS or business equivalence.
