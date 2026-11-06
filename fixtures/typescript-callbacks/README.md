# Pinned TypeScript callback evidence fixture

Actual TypeScript5.7.3 is supplied by the explicit trusted worker, not installed by
inspection. `src/api.ts` provides a generic higher-order API and ordinary/ higher-order
overloads; nested barrel aliases expose it to `src/app.ts`. Named/inline callbacks,
const aliases, union callbacks, mutable aliases/properties and any provide positive
and ambiguous ground truth. No JS emission or application execution is needed.

`tests/test_typescript_callbacks.py` checks declaration/signature/binding/candidate
identity and offline navigation; the separate project and limit test modules verify
owner-checker isolation, bounded partial output and atomic failure publication.
These static candidates never prove runtime callback execution or complete dispatch.
