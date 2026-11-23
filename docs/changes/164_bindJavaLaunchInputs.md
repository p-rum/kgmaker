# 164 — Doplnění otisku spuštění Javac

- Zadání [T003-S10-W01](../tasks/T003-S10-01-stageContentCache.md),
  AC01–AC04, nadřazené T003-AC10, [#116](https://github.com/p-rum/kgmaker/issues/116).
- Výchozí revize `0dbe9a754f06cf67f5fe40db0aaa31944497fe19`.

## Zjištění

Se skutečným Javac 21.0.6 a `--java-release 17` měla inspekce držící stejný
zdroj a stejnou cestu `Žluťoučký.java` shodný otisk při `LC_ALL=C` a
`LC_ALL=C.utf8`. První proces odmítl cestu s nepřevoditelnými znaky.
Druhý dokončil analýzu bez diagnostik. Na stejném izolovaném JDK a ASCII
fixture měl běh s přítomným i dočasně odebraným `lib/ct.sym` shodný launch
otisk. Pozorování souborových otevření při `analyze` potvrdilo čtení
`ct.sym`. Po odebrání souboru skutečný Javac odmítl release 17. Obě ověření
proběhla bez publikace grafu a soubor v izolované kopii byl obnoven.

## Změna

`launch_inputs` započítává `lib/ct.sym` do otisku Java a na POSIX
započítává přesné bajty `LANG`, `LC_ALL` a `LC_CTYPE`, včetně hodnot mimo
UTF-8. Otisk rozlišuje prázdnou a nepřítomnou hodnotu. Uložená metadata
obsahují SHA-256 prostředí.
Chybějící či nečitelný JDK vstup vyřadí kandidáta z ukládání. Úspěšná živá
analýza v takovém případě vrátí `BYPASS/INCOMPLETE_INPUT_CLOSURE`.
Při dostupném otisku a stabilních vstupech zůstává `BYPASS/UNVERIFIED_REPLAY`.
Stávající kontroly otisku odmítnou zjištěnou změnu při analýze nebo publikaci
jako `STALE`. Atomický store vrátí své již vyměněné výstupy.

Veřejné grafy a graph v1/v2/v3 zůstávají čitelné. Interní envelope v1
zachovává stejná pole. Běžný launcher nadále dědí procesové prostředí.
[Příklad s release 17 a locale](../stage-content-cache.md#použití) a
[compiler kontrakt](../compiler-inspection.md#obsahová-cache-inspekčních-stupňů-t003-s10-w01)
uvádějí chování. [Inventář](../acceptance-inventory.md) a
[stavová matice](../production-analysis-progress.md) evidují dílčí rozsah.

## Ověření

Cloud Environment, POSIX, CPython 3.12 a JDK 21.0.6. Na výchozím kódu
skončil cílený výběr `-k 'capture_binds or locale_drift'` v obou níže uvedených
souborech šesti očekávanými selháními a kódem 1. Tři varianty locale měly
shodný klíč, `ct.sym` chyběl v klíči a dvě skutečné změny během běhu
nevyvolaly `STALE`.

Po opravě cílený výběr skončil **7 PASS / 0 SKIP**, exit 0. Obsahuje dva
běhy se skutečným Javacem a kontrolu locale hodnot mimo UTF-8. Manifest 856
souborů se před testem a po něm shoduje. SHA-256 JUnit na výchozím kódu
je `6d5661460d852e3426b3a05f239fe3ba05c80af5430ad13f79aecbf463449e9c` a po
opravě `1c4bc0ad461e6d324145feef5eb8225af232b455c05175e7a40ba37808980bb5`.
Samostatný běh Javac potvrdil rollback i po výměně skutečně odlišného
`GRAPH.mmd` s novým importem mezi dvěma zdroji. Po `STALE` se všechny
tři původní výstupy shodovaly bajt po bajtu.

Úplný výběr W01 se skutečnými backendy Javac/K1, K2 a TypeScript skončil
**62 PASS / 0 SKIP**, exit 0. Oba konce běhu mají stejný 856souborový
manifest jako cílená sada. SHA-256 native JUnit je
`017f3560e7ea90ffe1aee0dbcd82b6231fab65d30a1aacd7745aeb1ad60ccd97`.

```bash
KGMAKER_REQUIRE_WORKERS=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData python -m pytest -q \
  tests/test_stage_content_cache.py tests/test_stage_content_cache_actual.py
python3.13 -m pytest -q
```

Úplná standardní sada v CPython 3.13.18 skončila **2 421 PASS, 1 297 SKIP,
1 očekávaný strict XFAIL**, bez selhání a chyb, exit 0. XFAIL je T047-S02
`test_comment_does_not_change_logical_identity`. Standardní profil používá
jiný výběr dostupných toolchainů než výše uvedený přísný běh W01. SHA-256
JUnit je `ed623bf5b14410058e33cb12649182765741802c0959c2b46531f76d6cd58e3e`.
Předchozí pokus v CPython 3.13.5 měl osm chyb instalačních fixture kvůli
chybějícímu `pip`. V opraveném prostředí měl cílený výběr instalačních a
verifikačních testů 54 PASS a 7 SKIP, exit 0. Hostované GitHub Actions mají
stav `NOT_RUN`.

## Zbývající rozsah

W01 a T003-AC10 zůstávají `PARTIAL`. Persistentní warm `HIT` stále
vyžaduje nezávisle chráněného vydavatele compiler důkazu a úplné vymezení
běhu. Analýza otevřela také dynamické knihovny JDK. Úplný runtime a
prostředí launcheru zůstávají samostatným předpokladem #116.
