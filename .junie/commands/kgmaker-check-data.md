# KGMAKER data prerequisite audit

For the intent `/kgmaker check-data`, follow
`.github/agents/kgmaker-data-auditor.agent.md`.

Use feature prepare/data-check/validate/apply/report/revise. Check the supplied
workspace baselines and Flyway targets. Limit model work to requirement meaning
and returned business ambiguities. Never invent observations or approvals.
Separate tool coverage from scoped data gaps; do not edit application code or
execute migrations/tests. If the host does not discover this command, explicitly
open the agent file.
