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

Fresh Python public audit regression: původní source RED1FAIL0.54s (PURE_PROJECTION_IO:open), opravená source GREEN se stávajícím Path-denial případem2PASS0.57s. Celý T014 module25PASS0SKIP0.69s. Affected-case a celkové source-attributed coverage zatím NOT_RUN.
Předchozí kompletní případy lze převést pouze s nezávisle ověřenou nezměněností;
89 W07 a 13 dříve dokončených T014 se mají konzervativně zopakovat. Chybějící
pokračování, SVG15+4 a current-main/pair review zatím nejsou splněny. Nejde o nový
samostatný full PASS ani dokončení celého T003/T004.
