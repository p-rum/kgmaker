# Oprava čistoty prvního vzdáleného přechodu

Stav: ROZPRACOVÁNO; T003-S07-W07-AC01/03/04 a T014 pure projection.

Při samostatném prvním volání provádí resolver vnořený import normalizátoru cest.
Čtení modulu porušuje zákaz I/O uvnitř čisté projekce. Původní warm full tento
průchod neodhalil. Renderer004 skončil chybou externího zapisovače; opravený
renderer005 skončil skutečným cold-purity FAIL. Oba záznamy zůstávají zachované.

Oprava přesouvá existující import na úroveň modulu. Nemění normalizaci,
verzi pravidel, evidence, runtime dostupnost ani formát capture. Nový test spustí
ve fresh Python procesu veřejnou T014 projekci s předem načteným protocol vstupem
pod audit zákazem file/process/network I/O. Hand-labelled vstup není native důkaz.

Fresh Python public audit regression: původní source RED1FAIL0.54s
(PURE_PROJECTION_IO:open), opravená source869ab GREEN se stávajícím Path-denial
případem2PASS0.57s. Celý T014 module25PASS0SKIP0.69s je pure protocol důkaz,
nikoli native/runtime pozorování. Autor opravy je Root; publikace na main je
mechanický přenos stejného runtime/test obsahu bez rendererových features.

## Terminální source-corrected coverage (2026-11-06)

Pokračování006 na source91ca skončilo1176PASS a1povoleným typovaným WindowsSKIP
(1177unikátníchID; XML575.90s/runner618.34s). Všech102 dříve dokončených
affected W07/T014 případů bylo vyloučeno z reuse a provedeno znovu. S nezávisle
ověřenými1561PASS/9SKIP ze source304 vznikl source-corrected agregát2747ID:
2737PASS/10přesně povolených typovaných SKIP, žádný FAIL/ERROR/NOT_RUN.
Nejde o nový samostatný full na91ca ani na publikačním commitu.

Přesný publikační subset2598ID je2588PASS/10SKIP:1561PASS/9SKIP provedeno na304,
1027PASS/1SKIP na91ca. Každý řádek zachovává skutečný executed_source_head,
původní XML, kompletní fáze a typ/message optional skipu. Runtime a testy zde
odpovídají source91ca; jedinými očekávanými rozdíly proti ní jsou původní main
CLI formatter dispatch a main CI (renderer additions nejsou součástí této větve).
Helper normalizace/VERSION2 jsou nezměněné; původních24 testů zůstalo prefixem.

Root terminálně ověřil1364kindroots/94333entries a80637fresh hashů s nulovou
pre/post chybou; všechny sources/pins beze změny. V externím agregátu jsou skutečné
SVG15+4 PASS se třemi fázemi/raw důkazy; rendererové149ID nejsou v tomto PR.
Původní failed/capacity pokusy zůstávají zachované a nejsou wholesale PASS.

Publikační evidence: `/workspace/cold-remote-publication-proof/terminal-recording/`.
Soubor publication2598-source-corrected-statuses.json má SHA256
05f393cb1646370041e8098abfd50540199ee4e4265a66d01f5616ea89bd435a.
Historická Root epizoda je neměnná; její původní unknown validace nejsou přepsány.
Main248epizod zůstává přesným prefixem +jediná Rootcold epizoda. Rootův task16ee
zůstává na validační větvi beze změny budgetu. Nové exact-pair FINAL review od
architect a resume_t010 jsou PENDING; Root je autor a merge guard, nikoli reviewer.
Tato metadata aktualizace nespouštěla testy/collection/preflight/build/actual/frontu.
