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

## Přenos po sloučení #147

Přenos spojuje opravu otisku z `31f43e7ef13848bd311460f926bf84a37b6ef306`
s `main` na `2db5c4931bfd832908158900b2823b6c122bc3a7`. Zdrojové a testovací
změny obou rodičů jsou v přesném znění. Společná dokumentace zachovává
rozsah W01 i [ověření publikace importu W02](163_revalidateRuntimeImportPublication.md).
Konflikty ve dvou souborech grafu vyřešilo sloučení 371 historických
epizod a regenerace grafu.

Cílený běh v Cloud Environment s JDK 21.0.6+7 skončil **14 PASS / 0 SKIP**,
exit 0. Zahrnul změny locale při analýze pro `--java-release 17` a při
publikaci grafu, vazbu `ct.sym`, jediné úplné ověření runtime manifestu,
rollback po změně zdroje, workeru či bytecode a kontroly uložené generace.
JUnit SHA-256 je `832ae55300c9f61dd89b0a059ba5ee6619b254121cfe7994a7499843142ac8d7`.
SHA-256 shodného manifestu 269 zdrojových a testovacích vstupů před i po
běhu je `ea1d48c243b541e6e2eb28b11e457a6322edc522d9c84c3058e08ce987a7db85`.

## Oprava po nezávislém review #149

Na revizi `8dbe48a85539fff5f8eca250859bf7c73b4227de` dvě nezávislá review
prokázala dvě chyby. Při `bin/java → java-real` chyběly v otisku platformní
soubory i locale. Spustitelná binárka bez práva čtení ukončila inspekci
výjimkou `PermissionError` po úspěšném handshake.

`launch_inputs` rozpozná jméno `java` nebo `java.exe` v požadované i
rozřešené cestě. Otisk zahrnuje bajty rozřešené binárky a soubory jejího
JDK. Chyba `OSError` při rozřešení nebo čtení binárky označí otisk jako
nedostupný. Živá inspekce pak může proběhnout s `BYPASS/INCOMPLETE_INPUT_CLOSURE`.
[Příkazy a význam výstupu](../stage-content-cache.md) platí i pro tyto případy.

Obě nové regrese nad původním kódem selhaly (**2 FAIL**, exit 1), JUnit
`275628fb4300d20b6a8bea4d29f1170f17e73c54267f0aa1bafb6d12aaf2ac98`.
Po opravě prošly (**2 PASS / 0 SKIP**, exit 0), JUnit
`f2cf537760650048bd0166d898cd6911cf8a383adf52dc7e339df8283b2c9145`.
`tests/test_stage_content_cache.py` a oba případy skutečného Javac driftu z
`tests/test_stage_content_cache_actual.py` daly **59 PASS / 0 SKIP**, exit 0,
JUnit `1ec9a849637116964ed91761f01b0c8686d8b043898d898e0548ec7b7e40540b`.

Dvě izolované kopie Temurinu 21.0.6+7 potvrdily výsledek bez náhrady workeru.
U aliasu změna `LC_ALL` po skutečném `analyze` vrátila `STALE` a všechny
uložené výstupy zachovaly původní bajty. Druhý běh s právem `0111` dokončil
analýzu, vyřešil jedno volání a uložil graf s prázdnými cache metadaty.
Všechny tři fáze hlásily `BYPASS/INCOMPLETE_INPUT_CLOSURE`. SHA-256 obou
dokladů je `1ed82101e21ca9655539d35f858e0a69922a99ef7989eda96795cdee877a9207`
a `ee06f28b3cc608fc11e2984f47a8b371ed9c1337eb8c08807c4834bbb9518456`.

## Přenos po sloučení #148

Prvním rodičem je oprava po review `4a361ae5f16a0c8ef5662635b3304d69f9dec270`.
Druhým je `main` na `385943e48d2d2e60cec541f1f0db78beda83de22`. Společný strom
obsahuje šest souborů zdrojových a testovacích změn obou rodičů v původním
znění. Historické ověření [předání konfigurace](165_forwardBuildConfiguration.md)
patří své původní revizi a zůstává v samostatném dokladu. Konflikty ve dvou
generovaných souborech grafu řeší regenerace se zachováním 375 epizod rodičů.

Cloud Environment s JDK 21.0.6+7 a offline Mavenem 3.9.9 dal **21 PASS / 0 SKIP**,
exit 0. Výběr pokryl alias a nedostupný otisk, skutečný locale drift při
analýze i publikaci a veřejný přenos deklarované konfigurace vybrané Maven
varianty včetně odmítnutí chybných hodnot. JUnit SHA-256 je
`d202349dc7b39f3e112169c530157d2c22aca861e28845accfbb2bc81fee7c78` a shodný
manifest 269 zdrojových, testovacích a nástrojových souborů má SHA-256
`c05903e80f35ba5433d8563bc28d533774da6d793fdd16db50ef1b567f4d733f`.
Dva nativní pokusy nad společným kódem znovu ověřily `STALE` a původní výstupy
u reálného aliasu a jedno vyřešené volání s `BYPASS/INCOMPLETE_INPUT_CLOSURE`
a prázdnými cache metadaty při právu `0111`. SHA-256 dokladů je
`cccf36d972fab1bb94c494e5cdd9d09fb3d595be8dea7ac609dfce96cf143654`
a `ee06f28b3cc608fc11e2984f47a8b371ed9c1337eb8c08807c4834bbb9518456`.
