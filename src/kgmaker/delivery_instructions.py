"""Shared instructions for installed and repository agent profiles (T046)."""
DELIVERY_INSTRUCTIONS = '''

## Templates, tests and delivery evidence

Use `kgmaker template list` and project `.kgmaker/templates/defaults.json` when
creating requirements, analyses, implementation tasks, tests or filenames.
`kgmaker template render` is data-only; keep its returned template provenance.
Templates never replace structured validators or authorize approval.

For tests of existing functionality, use `kgmaker testgen prepare --id <suite>
--target <existing-entity-id-or-file>`. Carry scope/context/workspace consistently.
Select an explicit target or evidenced framework if discovery is ambiguous.
Read the returned packet and existing source/graph/analysis tools. The host agent
writes a candidate conforming to docs/delivery-workflow.md, including cases,
synthetic datasets, test-code proposals and exact source citations for expected
results. Code-derived expectations are CODE_CHARACTERIZATION, not business truth.
Never invent source evidence, constraints, execution results or approvers.
Run `testgen validate`, `testgen apply`, then explicitly `testgen export` only when
writing tests is requested. Test execution is separate and uses the project's
existing runner. Import actual results as a workflow test artifact; NOT_RUN is
never PASS. Unsupported constraints and missing tools remain explicit gaps.

Use `kgmaker trace sync-task --id <runtime-task-id>`, `trace sync-analysis --id
<analysis-id>`, `trace sync-testgen --id <suite>` and explicit `trace link` to
retain requirement → analysis → task → change → test evidence. Capture changes
with `trace capture-change --task <id> --base <ref> [--head <ref>]`; review with
`trace show` and `trace check`. IDs in documents never replace runtime task IDs.
Local actors have LOCAL_DECLARED trust. Human decisions require explicit human
instruction and the exact reference revision. Agents cannot approve for a human.
Approval gates are optional project policy, disabled by default. An enabled gate
requires current requirement/plan approval before implementation and current
review approval before completion; changed content needs a new decision.
'''
