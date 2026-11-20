# Testgen candidate v1

Start from the returned candidate_template; copy the current suite_id/packet_id.
This illustrates structure, not verified values:

```json
{
  "schema_version": 1,
  "suite_id": "current-suite-id",
  "packet_id": "copied-from-packet",
  "cases": [{
    "id": "positive", "title": "Observed positive behavior",
    "target_ids": ["packet.target.id"], "requirement_refs": [],
    "category": "characterization", "preconditions": "module can be imported",
    "steps": ["call with the synthetic input"],
    "expected": {"text": "source-backed result", "basis": "CODE_CHARACTERIZATION",
      "citations": [{"path": "src/example.py", "sha256": "packet source hash",
                     "start": 1, "end": 2, "quote": "exact source excerpt"}]},
    "dataset_ids": ["inputs"]
  }],
  "datasets": [{
    "id": "inputs", "purpose": "synthetic input",
    "schema": {"type": "array", "items": {"type": "integer"}},
    "data": [2, 0], "negative": false, "expected_violations": [],
    "citations": [{"path": "src/example.py", "sha256": "packet source hash",
                   "start": 1, "end": 2, "quote": "exact source excerpt"}],
    "foreign_keys": []
  }],
  "files": [],
  "questions": []
}
```

Cases use positive, negative, boundary or characterization category. Expected basis
is CODE_CHARACTERIZATION, CONTRACT or ANALYSIS. CONTRACT needs cited contract
evidence; ANALYSIS needs the applied attached analysis. requirement_refs reference
existing requirement identities in the trace journal.

When proposing code, files entries have path, content and case_ids. Respect target
framework and existing file conventions; exports do not overwrite existing files.
Supported proposal frameworks are unittest, pytest, junit, jest, vitest and
playwright. Detected configuration does not prove a runner is installed.

Supported dataset schema keywords: type, properties, required, items, enum,
minimum, maximum, minLength, maxLength, nullable, and additionalProperties.
For object schemas, use true to allow extra values, false to reject them, or
a supported typed schema to validate each extra value recursively.
Unknown keywords remain unchecked_constraints. Negative datasets must declare
the exact expected violations (for example `$[0].amount:type`); positive datasets
must pass checked constraints. Foreign keys use field, dataset_id and target_field
and compare actual values. Constraints still need cited domain justification.
