# Shodná projekce grafu pro záznam implementační epizody

26. listopadu 2026. [T052-S04 / T052-AC04](../tasks/52_addCompletionOrchestrator.md),
výchozí commit `fd8d5e958bf45b67775c04f78e817cc7d41ebfe9` a strom
`96da6d28602a9cc2aeb9a17441448468eb0710b8`.

Po běžném `kgmaker scan` uložil strojový graf uzly workbooku a šablony.
`kgmaker memory capture` porovnal tento graf pouze se strukturou a
sémantickou vrstvou. Po nesouvisející změně Python souboru proto vykázal
odebrání tří uzlů `Rates.xlsx` a dvou uzlů šablony, přestože vstupy zůstaly
stejné. Reprodukce přes veřejné příkazy má 1 FAIL, 0 SKIP, exit 1. SHA-256 JUnit
`b6edab2733a0ed72560bba10bdc6cefa0eb49eebe5257dff51075c42448d26ee`.

`feature.py` sdílí stávající lokální projekci mezi scanem a capture. Capture
znovu použije svůj strukturální scan, v paměti doplní šablony, workbooky,
uchované compiler kontexty, sémantickou vrstvu a lokální Flyway replay a teprve
pak porovná uzly. Capture přísně ověří původní sémantický artefakt proti
strukturálnímu grafu. Včetně migrace z v1 nebo v2 promítne stejná data v3,
která použije i při opakování. Diagnostika obohacené projekce capture
odmítne. Epizody mají nadále formát v3 a dřívější záznamy se nepřepočítávají.
Capture nepublikuje graf a nespouští compiler ani build.

Před potvrzením duplikátu nebo atomickou výměnou capture ověří původní
bajty pod existujícím publikačním zámkem checkoutu. `semantic apply`
používá stejný zámek od načtení uloženého artefaktu do jeho výměny.
Příkaz, který narazí na obsazený zámek, vrátí kód 3 a lze ho zopakovat.
Capture při zjištěné změně původních bajtů vrátí kód 2. Zámek koordinuje
příkazy, které ho používají. Ruční zápisy mimo tento postup nemají tuto
garanci.

Regrese s reálným `Rates.xlsx` ověřuje běžný scan, nesouvisející změnu Pythonu,
opakovaný capture, skutečné odstranění workbooku a shodné bajty uloženého
grafu i jeho Markdown a Mermaid výstupů. Samostatná zkouška zachovává původní
strukturální kontrakt v1, převádí artefakt na v3 a po změně citovaného zdroje
ověřuje odmítnutí zastaralého artefaktu bez zápisu.
Kontroly po první úpravě doložily dva očekávané FAIL pro přepsání mezitím
změněného artefaktu a ignorovanou diagnostiku, exit 1. SHA-256 JUnit
`621aabc00d24a9b90e984ba5e3b0ac980664a34ee122494c161575f53e0741c1`.
Výsledná regrese chrání mezitím změněný, poškozený, odebraný i nečitelný
artefakt a ověřuje odmítnutí diagnostiky projekce.

```sh
PYTHONPATH=src python -m pytest -q -p no:cacheprovider --tb=short \
  tests/test_memory.py tests/test_graph_provider.py tests/test_completion.py tests/test_scanner.py
```

CPython 3.13.18 v Cloud Environment má 60 PASS, 0 SKIP, 0 FAIL, exit 0.
SHA-256 JUnit `7cea8cf41933e0ebac4940110b6ac457a3b562bbd21a2ea9d9c4831f390a0a7e`.
Po sloučení [#185](https://github.com/p-rum/kgmaker/pull/185) bylo v prvním
pracovním běhu
devět souborů opravy přeneseno na `90af07888582222c579af9b6fa269704dbb30a46`,
strom `349c484008754917e06b90a300823ec7ea6653ed`. Stejný výběr má nad
tímto základem 60 PASS, 0 SKIP, 0 FAIL, exit 0. SHA-256 JUnit
`948720257ffcd669fafc657f81f7c550dc1f496a5184aa0d9cd6f2aef6a4e3a8`.

V návrhu `d7ba43206438911fba5d31b7f2ed5c9101b2bd44` zapsal první capture
v1 jednu epizodu a opakování bez změny druhou. Nezávislá reprodukce přes
veřejný příkaz má exit 1, SHA-256 souhrnu
`53352c5751b10b48b784eaed5a138b9f707158656ac986eb3280418623e950bc`.
Samostatná reprodukce dvou souběžných capture se stejným checkoutem doložila
dva úspěšné návratové kódy a ztrátu jedné epizody. Sériová kontrola zachovala
obě epizody. SHA-256 souhrnu
`e90bef72a02922f53dd62e7ab05ed5df46bdee28d77334e83ed5e41bfaeb5dc7`.

Handoff dalšího kola zachoval tento základ a přidal tři regrese. Ověřují
opakování v1 nad obohaceným grafem s reálným workbookem, dva různé platné
Git základy stejného stromu a střet s právě načteným skutečným
`semantic apply` patchem. Oba odložené zápisy po opakování zachovají
důkaz prvního příkazu. Nad návrhem regrese vykázaly 3 FAIL, exit 1, SHA-256
JUnit `4017838d10e81e16c6375f930b7e12f3827d366473db3a53e37d77c9ad96d495`.
Po opravě mají 3 PASS, 0 SKIP, exit 0, SHA-256 JUnit
`0833583dfa84d8bbb9009b3955e3b1d14cb4ef4b3392be9b34a0ed304f0c581d`.
Výběr výše doplněný o `tests/test_graph_publication_concurrency.py` má
80 PASS, 0 SKIP, exit 0, SHA-256 JUnit
`8ab7010223946eafa2eb8c007a88f5e2b22a65eea6584084d81592c07755b6db`.

Výchozí a následný graf se v tomto rozsahu opírají o `kgmaker scan` bez
externího overlaye. Graf s Confluence a odlišná workspace projekce zůstávají
mimo ověřený rozsah. V popsaném pracovním běhu po opravě byla úplná sada i
nové formální review `NOT_RUN`. Ověření při integraci dokládají výsledky
v příslušném PR vázané na jeho přesný base a head.
[Postup](../completion-orchestrator.md#záznam-implementační-epizody) ·
[Přehled ověření](../acceptance-inventory.md#t052--completion-orchestration-2026-11-19).
