# DataRequirementSet v1

Use exact requirement text and hashes from the current packet. For example:

```json
{
  "schema_version": 1,
  "analysis_id": "the-current-analysis-id",
  "requirement_hash": "copied-from-packet",
  "requirements": [
    {"id": "analysis:the-current-analysis-id:requirement:r1", "text": "exact requirement text", "kind": "Goal", "source_quote": "exact source quote"}
  ],
  "inputs": [
    {"id": "analysis:the-current-analysis-id:input:i1", "name": "requested input", "requirement_ids": ["analysis:the-current-analysis-id:requirement:r1"],
     "definition": null, "data_type": null, "unit": null, "currency": null,
     "granularity": null, "keys": null, "as_of": null, "validity_interval": null,
     "horizon": null, "freshness": null, "nullable": null, "quality": null,
     "fallbacks": null}
  ]
}
```

Replace example values with the user's actual meaning and analysis ID. Requirement
IDs use `analysis:<analysis-id>:requirement:<name>` and input IDs use
`analysis:<analysis-id>:input:<name>`. Optional
`candidate_entity_ids` use packet IDs as navigation hints, not business-equivalence
proof. Preserve explicit business metadata; ask about consequential ambiguity.
Do not repeatedly ask to approve unchanged mappings.

Positive OBSERVED_VALUE_PATH proof requires fresh cited supplied observations,
current path hashes, supported EXTRACTED dependencies and an approved exact
business metadata mapping. DTOs, schema declarations or inferred field links alone
cannot establish availability. CLOSED_CONTRACT_ABSENCE and APPROVED_MISSING are
scoped absence proofs. Never infer organization-wide absence from a local search.
Never fabricate observations, freshness or owner approval. Supplied observations
are not authenticated production access. Unsupported evidence stays UNKNOWN/pending.
