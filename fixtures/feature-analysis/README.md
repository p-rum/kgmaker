# Analytical-core fixture (milestone A foundation)

This is intentionally a partial backend/contract fixture. UI, PDF, workbook,
field mappings and approved methodology are absent, and must remain uncovered.
No code equates account balance and available liquidity.

`expected/candidate-valid.json` is a prepared agent response. The fixture harness
copies the packet envelope (`revision`, `packet_id`, `requirement_hash`, `baseline`,
`coverage`) and the actual cited file hash into its explicit placeholders. It does
not change conclusions or locations. `candidate-invalid.json` cites line 999 and
must fail without mutation. Neither is a ready-to-apply candidate for another root.

Run the reproducible CLI scenario from a checkout:

```bash
python -m unittest discover -s tests -p test_feature_fixture.py -v
```

The scenario covers prepare → validate → rejected apply → valid apply → report →
compare → revise → validate/apply revised candidate. There is no live LLM.
A reviewed example report is committed at
`docs/generated/features/additional-hedge-example.md` in the repository root.
Its baseline belongs to the test fixture snapshot, not the kgmaker implementation.
