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


## T051-S02 / T052-S02 — kontrola po sloučení #149

Výchozí SHA `16f2ba8c4d109957edc295feea80db86da7093f1`. Zkouška XLSX
používá stávající fixture s listem a buňkami. Po úvodním scanu mění pouze
deklaraci kódování ve vlastní části sešitu. Výstup role packetu zůstává
`stale`, uložený graf zůstává beze změny. Produkční implementace opravy
se při tomto přenosu nemění.

Cílený příkaz výše má 149 PASS / 0 SKIP, JUnit SHA-256
`72dbf9ac5eae5ac6a949e4c8f550c13dc27f34b456757bd373535278c34f901e`.
Read-only probe nad 677 cestami ve stejném grafu vrací `stale` před
opravou a `current` po opravě při blokovaných procesech. SHA-256 grafu
před i po je
`fae9c724ac36b5dcb83fd6619a6634baeb56e079e0951d9f03ec5a6be914b1b2`.

Windows, úplná sada, GitHub Actions a nové T045 zůstávají NOT_RUN.


## T051-S02 / T052-S02 — kontrola po sloučení #152

Výchozí SHA `edb65e57ca4de1743c810689c78e069cd86b2b41`. Tentýž cílený
příkaz má 149 PASS / 0 SKIP, JUnit SHA-256
`536c659f4034b0d84dbbe6e73a8cf3f30a3dafe167bea7af1b4815f5aeb8fdd2`.
Znovu ověřený read-only probe nad 678 cestami vrací `stale` před opravou a
`current` po opravě při blokovaných procesech. SHA-256 grafu před i po
je `a517a440cfbbb4fe88cbddb6414e5cb03006864c811ab1c6eae2c47a7079749c`. Windows, úplná standardní sada, GitHub Actions a nové
T045 pro tento pár zůstávají NOT_RUN. T051-AC02 je doloženo v rozsahu
čerstvosti paketu.


## T051-S02 / T052-S02 — ověření po sloučení #154 a #155

Základ `782ac6ac0287550084e9afadbd6182756fdd2730` a původní head
`6dc5d6888114b43f15bbde7ea19d343c8e93d55a`. Sjednocení zachovává původní
zdrojové změny v `context.py`, `workbooks.py` a `test_workflow.py`. Dokumentace
upřesňuje rozsah zdrojových hashů a regenerované grafy zahrnují nový instalátor,
migraci Excelu a jejich testovací vstupy. Životní cyklus packetů ani schémata
výstupů se nemění.

- Původní cílené moduly výše a `tests/test_installation.py` pod CPythonem
  3.12 mají 208 PASS a 0 SKIP. JUnit SHA-256
  `e0482894a0f3e2ead98063f6e853431f194db34cd4a0886d22ead7f947746220`.
  Otisky zdrojů, testů, dokumentace a fixture se během běhu nezměnily.
- Samostatná zkouška vložila do dočasného projektu `Rates.xlsx`,
  `encrypted.xlsx`, `legacy.xls` a `migration.xlsm` z T054. Scan a packet
  shodně zahrnují první tři sešity. Změna kteréhokoli z těchto tří vstupů
  vrací `stale`; po obnovení bajtů je výsledek `current`. Změna `.xlsm`
  nemění stav, protože jeho explicitní analýza patří do T054. Packet
  zkouška blokovala parser i procesy, zachovala uložený graf a sama
  neuložila výstup. SHA-256 výsledku
  `823f33a5cf233153a158b9c36221d3ce2ff2d56da18d5b11096a29e960bc2e07`.
- Nový úplný běh, Windows, GitHub Actions a T045 pro tento pár jsou
  NOT_RUN. Výsledek dokládá zdrojovou čerstvost T051-AC02 a T052-AC02.


## T051-S02 / T052-S02 — ověření po sloučení #136

Základ `5809e84932b1910bfc3f17c72e2a2005283389b1` a předchozí head
`babade34660110a62b4b88db0e902f2ba61488a5`. Přenos zachovává shodné
`context.py`, `workbooks.py` a `test_workflow.py` z předchozího headu.
Kód, testy a rozsah runtime importu z #136 jsou shodné s novým `main`.
Příkazy a výstupní formáty se nemění. Součástí přenosu je obnovení
generovaných grafů při zachování sémantických epizod z obou rodičů.

- Stejný cílený výběr jako po #154 a #155 má 208 PASS, 0 SKIP a 0 FAIL
  pod CPythonem 3.12. JUnit SHA-256
  `5e4f31eea01523d8004711865704472a77ccfb7ddb31f49694f40048feee3ee0`.
  Otisky zdrojů, testů, workerů a fixture se před a po shodují.
- Opakovaná zkouška nad skutečnými sešity T054 potvrdila stejný seznam
  zdrojů a indikátory `current` a `stale`. Přitom neproběhl parser ani
  proces a původní graf zůstal stejný. SHA-256 výsledku
  `f751b834055e22c98a5d69f0ee449326d1c7356d4822b3918d06420df3190ebc`.
- Úplný běh, Windows, GitHub Actions a nové T045 zůstávají NOT_RUN.
  Starší schválení patří předchozímu základu.
