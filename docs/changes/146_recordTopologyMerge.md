# Záznam ověřené integrace Mermaid topologie

T021-S05 / T021-AC06. Výchozí `main`
`61a554174b1c23257878fffae0e125f146223d79`.

Po integraci [#123](https://github.com/p-rum/kgmaker/pull/123) potřeboval
plánovač, aby evidence zachycená v PR byla dohledatelná ve stavové matici.
Záznam označuje T021 jako `MERGED / VERIFIED_IN_SCOPE` v
[aktualizovaném stavu](../production-analysis-progress.md) a doplňuje
[T021-AC06](../acceptance-inventory.md#t021--topology-mermaid-pr-123-merged).
Původní [change 132](132_renderTopologyMermaid.md) a
[change 138](138_rejectForeignTopologyEvidence.md) nadále evidují své revize.

Schválený pár je `17e9e7368e6cc2d6550983c3039eb39debd65424` →
`c5c73a844f46ba9b458e4aa850a7d3ef3e78ed2b`. Merge zachoval oba rodiče v
tomto pořadí a stejný tree `c4f03c843e613655bbfbf2f0d5ce04e203e355bc`.
[T045 APPROVE](https://github.com/p-rum/kgmaker/pull/123#issuecomment-7052064245).

- 194 PASS / 0 SKIP v cíleném běhu, včetně grafového loaderu v1/v2/v3.
- `bash .kgmaker/workflow/run-t021-full.sh c4f03c843e613655bbfbf2f0d5ce04e203e355bc`
  má exit 0, 3672 PASS / 1 SKIP / 0 FAIL / 0 ERROR, 2648,81 s.
  Skutečný Windows non-admin instalační smoke vyžaduje samostatný runner
  a nespadá do T021. JUnit SHA-256
  `0c3c40101d2a3a844cbedfd797283155b5b5d06e200c06eda8a528cb1ece0466`.
- Nezávislé T045 má 28 PASS / 0 SKIP se skutečným Mermaid 11.4.1.
- GitHub Actions hlásily failure/cancelled a neměly zaznamenané kroky.
  U ověřených logů skončilo stažení 404. Příčina zůstala neověřená.

Dopad je omezený na záznam integrace a lokální plán. Uživatelský postup
Mermaid je v [README](../../README.md#t021-topology-mermaid) a
[CLI příručce](../architecture-json-cli.md). Příklad kontroly T052 má tvar
`kgmaker completion plan --jobs 12`. T022 je následný renderer.

`python -m pytest -p no:cacheprovider -q tests/test_completion.py` má
7 PASS / 0 SKIP pro záznam integrace. Plán obsahuje 119 položek, vyřadí T021
z dispatch a zařadí T022 mezi připravené. Nová úplná sada dokumentační
revize samostatně neproběhla.
