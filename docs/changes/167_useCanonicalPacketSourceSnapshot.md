# Shodná zdrojová inventura pro kontextové pakety

**T051-S02 / T051-AC02, T052-S02 / T052-AC02**, base
`fad4fc63c76f0f9ef5a1a292e279d1269bd84540`.

Review packety #121, #123 a #130 hlásily `stale`, přestože kontrola grafu
uspěla. Přímé srovnání ukázalo stejný hash všech společných cest. Uložený
graf navíc obsahoval `fixtures/workbooks/legacy-biff2.xls` z offline
vrstvy sešitů.

`src/kgmaker/context.py` doplňuje do kontroly zdrojových hashů existující
výběr souborů a streaming SHA-256 sešitů z `src/kgmaker/workbooks.py`.
Test doložil, že první varianta s parsováním sešitu mohla po změně jeho
XML kódování shodit přípravu paketu. Kontrola proto používá hash místo
parsování struktury sešitu. Streaming čtení ověřuje otevřený deskriptor
běžného souboru a využívá dostupné no-follow a neblokující příznaky.
Packet `graph_status` vyjadřuje shodu zdrojových hashů hodnotami
`current`, `stale` a `missing`.

Příklad `kgmaker task context TASK_ID --role architect` nad čerstvým
grafem s legacy XLS uvádí `current`. Po změně evidovaných bajtů uvádí
`stale`. Test ověřuje také shodný uložený `graph.json`, preview bez zápisu
a nulové spuštění procesů.

- RED `python -m pytest -p no:cacheprovider -q tests/test_workflow.py -k same_workbook_inputs`, 1 FAIL na `stale` namísto `current`.
- RED `python -m pytest -p no:cacheprovider -q tests/test_workflow.py -k unparseable_workbook_edit`, 1 FAIL na `LookupError` v první opravě.
- GREEN `python -m pytest -p no:cacheprovider -q tests/test_workflow.py tests/test_workflow_profiles.py tests/test_completion_handoff.py tests/test_completion.py tests/test_feature.py tests/test_feature_fixture.py tests/test_workbooks.py tests/test_xlsx_references.py -o pythonpath=src`, 149 PASS / 0 SKIP.
- Přímý read-only probe nad přesným `main` porovnal stejný graph index se
  649 soubory. Starý indikátor vrátil `stale`, opravený `current`. Hash
  indexu před a po obou pokusech je `5e2d8e56fc9704e3992ad7f5e32745dff615903a999a855acfa88dafd1ce24d5`.
  Probe blokoval spuštění subprocessu.
- Úplná sada, GitHub Actions a T045 jsou NOT_RUN.

[README](../../README.md), [CLI průchod](../project-workflows.md),
[stav](../production-analysis-progress.md) a [acceptance](../acceptance-inventory.md)
popisují tuto opravu.

## T051-S02 / T052-S02 — ověření po integraci #145

Výchozí SHA `1569d5d1f3133360bb0c29d9cedf9b7cd1778ae4`. Nad stejným
uloženým snapshotem s 676 soubory vrátil původní kód `stale` a
opravený `current`. Oba read-only průchody blokovaly `subprocess.Popen`.
Index měl před a po bězích SHA-256 `5e741d9365da150a49d3eab9cfacffb974f4d93953f208d25b525faf52e72034`.
Cílený příkaz výše na tomto základu má 149 PASS / 0 SKIP, JUnit SHA-256
`a217d97423bad03454acf2bbcb2af4697783bec3b702ba72dff3c993f44aa954`. Mění se pouze shoda indikátoru s inventurou scanu.
Úplná sada, GitHub Actions a T045 jsou pro tento krok NOT_RUN.
