# Obnova předání při dlouhém kontextu

**T052-S02 / T052-R02 / T052-AC02**, base
`fad4fc63c76f0f9ef5a1a292e279d1269bd84540`.

Při obnově T047-S01 měl uložený `existing-feature` profil rozpočet 4000
tokenů. `kgmaker completion handoff --apply` odmítl přípravu test packetu
s `token budget cannot fit required workflow context`. Kvůli obnovení
bylo nutné použít samostatné `task advance` a `task context --token-budget`.

`src/kgmaker/completion_handoff.py` přijímá pro nový role packet stejnou
volitelnou hodnotu jako `task context`. Preview, validace před přechodem a
zápis používají stejný rozpočet. Výchozí profil, uložený snapshot, retry limit
a platný sdílený review packet se zachovávají. Workflow a packet schémata
jsou stejná. Instalované instrukce mají stejné vstupní příkazy.

```bash
kgmaker completion handoff "$KGMAKER_TASK_ID" --apply --token-budget 12000
```

`tests/test_completion_handoff.py` ověřuje neúspěšný výchozí rozpočet bez
zápisu, read-only návrh s 8000, shodný uložený packet a zachování profilu.
Test se sdíleným review packetem pokrývá opakování s větším rozpočtem.

- RED `python -m pytest -p no:cacheprovider -q tests/test_completion_handoff.py -k packet_budget_failure`, 1 FAIL, protože CLI argument odmítlo.
- GREEN `python -m pytest -p no:cacheprovider -q tests/test_completion.py tests/test_completion_handoff.py tests/test_workflow_profiles.py tests/test_workflow.py tests/test_context_roles.py`, 99 PASS / 0 SKIP po přenosu na aktuální base.
- Při zkoušce na skutečné historii T047-S01 ponechal menší rozpočet úlohu
  beze změny. Explicitní rozpočet 12000 vytvořil shodný preview a uložený
  test packet. Podrobnost o živém tasku uchovává lokální checkpoint.
- Úplná sada, GitHub CI a T045 jsou NOT_RUN.

[README](../../README.md), [příručka](../completion-orchestrator.md),
[acceptance](../acceptance-inventory.md) a [stav](../production-analysis-progress.md)
popisují předání, omezení a zbývající ověření.

## Ověření po integraci W06 a jeho evidence

Base `d5a0b236716fd31dc1db11d9e6ae3c4f692f2d7e` obsahuje #129 i #134.
Zdroj a testy této opravy mají shodný diff s dříve recenzovaným krokem.
Stejný cílený příkaz výše má 99 PASS / 0 SKIP na novém základu.
Graf, sémantika a diff prošly po přepočtu. Stav #129 i jeho přesný doklad
zůstávají v existujícím inventáři.

### Doplnění po nezávislém review T052-S02 / AC02

Inventář a stavová matice uvádějí 99 zaměřených PASS / 0 SKIP a stav
úplné sady NOT_RUN. [Specifikace T052](../tasks/52_addCompletionOrchestrator.md)
pro tento krok vyžaduje zaměřené testy a obnovu workflow. Příkaz z prvního
ověření i graph/status a diff kontroly prošly po doplnění evidenčních textů.
