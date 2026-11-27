# Čtecí Markdown výkaz dodaného procesu

27. listopadu 2026. [T036](../tasks/T-036_render-business-process-report.md)
navazuje na sloučené T033 a T035. Výchozí `main`
`f7015b61473a0700d979157eeba271c480c21cb8` už dodával `ProcessView` a
technický Mermaid diagram. Pro dodaný model chyběl veřejný technický výkaz.

## T036-S01 a T036-AC01/03 — výkaz a diagram z jediného pohledu

`src/kgmaker/process_render.py` přidává `render_process_markdown(view)`. Z jedné
normalizace dodaného `ProcessView` schema 1 sestaví tabulky a stávající
technický diagram T035. Výkaz nese identitu, revizi, fingerprint pohledu a
baseline, scope, vybrané kontexty, triggery, vstupy, výstupy a výsledky. Každý
krok a orientovaný přechod má vlastní řádek. Paralelní přechody mají samostatná
ID a tabulky se řadí podle ID. Původní veřejné Mermaid funkce zachovávají
stávající chování i bajty diagramů.

## T036-S02 a T036-AC05 — technické hranice

Výkaz zachovává technické stavy, coverage, důvod nevyřešené hranice, lokální
truncation, doložená vynechání, diagnostiku a omezení. Nedoložený účel a
dostupnost dat mají `UNKNOWN`. Kontrola aktuálních zdrojů a runtime zůstává
`NOT_CHECKED`. Vložený diagram používá čistou technickou cestu T035. Schválené
business popisky a skutečné konfliktní či zastaralé schválení patří k T036-AC02.

## T036-S03 a T036-AC04/05 — původ a meze čtení

U citovaného důkazu výkaz zobrazuje zachycený druh, polaritu, freshness a kontext.
Zachycený locator vyžaduje výslovnou cestu v repozitáři kvalifikovaného zdroje,
vybraný kontext a hash obsahu. Když záznam nese platný rozsah nebo řádek, zobrazí
ho jako text. Bez této vazby zobrazí `SOURCE_LOCATOR_UNAVAILABLE`.

Vstup, stávající artefakty i zdrojový checkout zůstávají shodné. Python funkce
nevykonává čtení souborů, práci s katalogem, čtení review ani extrakci. Při
chybě vstupu, nebezpečném výstupu nebo překročení rozpočtu vyvolá
`ProcessMarkdownError` a nevydá neúplný výkaz. Rozpočet 4 000 000 bajtů UTF-8
platí pro výkaz včetně diagramu se stávajícími limity Mermaid. Migrace není potřeba.

## T036-S04 a T036-AC01/03/04/05 — cílené ověření

- `test_checkout_report_uses_one_snapshot_and_fixed_mermaid` porovnává parserem
  skutečné hodnoty tabulek, počet normalizací a revizi. Jediný blok Mermaid má
  golden SHA-256 `55881e998d92ad88d42a03e3f28f259256827b9429ed1ce1c8be4f3833de57fa`.
- `test_partial_report_preserves_every_occurrence_and_manual_handoff` ověřuje
  sedm uzlů, devět orientovaných hran, paralelní výskyt, nevyřešený ruční přechod
  bez důkazu, `STALE`, omezený locator, `PARTIAL` a vynechání.
- `test_report_escapes_cells_and_delimits_the_exact_mermaid` ověřuje zachycené
  backticky, rouru, text HTML a podobu odkazu při zachování struktury Markdownu.
- `test_invalid_or_over_budget_report_preserves_last_valid_artifact` ověřuje
  neplatný typ, scope, kontext a reference důkazu, nebezpečný obsah a rozpočet
  Mermaid i celého výkazu, včetně shody vstupu a posledního uloženého artefaktu.

Na původním zdroji selhalo všech deset nových případů kvůli chybějícímu API.
Raw exit 1, JUnit SHA-256 `2ba509568fddc979da8f1a24cf80a0dfc1bbd4fe74d96c47c3aee25b311f5f70`.
První připravený zdrojový strom `38623fb80cd6860d66cc6bd32b7cb876e3372d87`
měl 120 PASS, 0 SKIP, 0 FAIL, raw exit 0. JUnit SHA-256
`3b6e0af06b9136de98d8fe673b0c10408795a33bb0073a3f22b4ad668b620420`.

## T036-S01, T036-S02 a T036-S04 · AC01/05 — přesná ID a lokální truncation

První strom v Markdown tabulce sléval některá rozdílná ID a lokální truncation
zůstával pouze v metadatech diagramu. `test_report_keeps_whitespace_and_literal_escape_occurrence_ids_distinct`
prověřuje řízené páry s ASCII mezerou, řídicími znaky, NBSP, oddělovačem Unicode
a doslovným escapem. ID a jejich reference se zobrazují reverzibilním zápisem
JSON, diagram dál obsahuje původní ID. `test_report_exposes_captured_occurrence_truncation_independently_of_coverage`
prověřuje booleovské `true` u kroku i hrany při celkovém `false`. Chybějící či
neplatná lokální hodnota má `UNKNOWN`.

Oba nové případy na prvním stromu selhaly na příslušných asercích, raw exit 1.
JUnit SHA-256 `ab9f18e350433722ee664def4b6384a45d2e6566581b3f39740672159c5b43d1`.
Opravený zdrojový strom `4808276cf5d936809641cb2c3695a6bd53684d26` nad výchozím
`f7015b6` má v cíleném běhu T020, T032, T035 a T036 **122 PASS, 0 SKIP, 0 FAIL**,
raw exit 0. JUnit SHA-256 `96e76123d3581a485b8a33bd9149172b918492d00c97097d44891fdd8e00a491`.
Běh použil CPython 3.13.18, markdown-it-py 3.0.0, Mermaid 11.4.1, jsdom 26.0.0
a skutečný Javac 21.0.6 ve stávající fixture retry a DLT. Výstup parseru a SVG,
regrese obou Mermaid funkcí i kontrola shody vstupů jsou součástí tohoto běhu.

## T036-S05 a T036-AC06 — rozsah předání

Po sloučení [#189](https://github.com/p-rum/kgmaker/pull/189) je základem tohoto
výřezu commit `c8b77a35c4e4255d2606f6bb8317435d69c6c885` z větve `main`.
Přenesený zdrojový strom `936bab8e441f45d720e3d0a7a30d9924da3073a8` obsahuje
shodný renderer a test. Příklad a meze rozhraní uvádí
[README](../../README.md#local-technical-process-paths-t025) a
[návod k výkazu](../process-paths.md#markdown-report-for-a-supplied-processview-t036).
[Acceptance](../acceptance-inventory.md#t036--markdown-výkaz-dodaného-procesu)
a [stavová matice](../production-analysis-progress.md) zaznamenávají místní
ověření `IN_PROGRESS / PARTIAL`. Příkaz `process render` nadále vydává JSON.

AC02, ověření aktuálního source locatoru a širší CLI mají samostatný rozsah.
Úplná sada, nezávislá recenze integrovaného výřezu a hostované CI měly při
uvedeném přípravném ověření stav `NOT_RUN`.

## Integrace po #165 — T036-S05 a T036-AC06

Po sloučení [#165](https://github.com/p-rum/kgmaker/pull/165) je základem
integrace `0e0c49120281e73ae131777e6f342f39407644e6` z větve `main`.
Větev výkazu navazuje na `27619782d2856d9aa16c9ae3c9379cb73f56edaa` z
[#190](https://github.com/p-rum/kgmaker/pull/190). Lokální sloučení zachovalo
úpravy obou větví v README, inventáři akceptace a stavové matici. Zdroj
rendereru a jeho test mají shodný obsah jako v předchozím commitu #190.

Na přesném commitu `0e0c491` skončil příkaz `kgmaker semantic validate`
s raw exit 2. Pět řádků přidaných do README posunulo důkaz existujícího
konceptu volitelné sémantické vrstvy a jedné vazby z řádku 232 na 237.
Důkaz druhé vazby se posunul z řádku 234 na 239. Omezená aktualizace
obnovila tyto tři kotvy při zachování obsahu konceptu a vztahů. Srovnávací
graf vychází z izolovaného stromu `0e0c491` a zachovává 511 přijatých epizod.
Zápis nové epizody pokrývá pouze sedm souborů T036.

Na předchozí dvojici `27619782` a `c8b77a35` prošel cílený nativní běh
se 122 PASS, 0 SKIP a raw exit 0. První pokus o úplnou standardní sadu
měl 2692 PASS, 1414 SKIP, 1 očekávaný XFAIL a 6 chyb při přípravě fixture.
Vnořené `ensurepip` selhalo kvůli `No space left on device` a běh měl raw exit 1.
JUnit SHA-256 `6b4deec3e82a33b5ffab5b2d248fd6d226d06c38da78074a471dda5dbb400fd3`.
Po uvolnění místa opakování na stejné dvojici a se shodným manifestem
vstupů skončilo s 2694 PASS, 1418 SKIP, 1 očekávaným XFAIL a raw exit 0.
JUnit SHA-256 `68b9a670031f02bba9edd785a05b454c01ddea568acb51df5b5ed9c5809fef5a`.
Výsledky se vztahují k předchozí dvojici. Cílený nativní běh, úplná sada,
nezávislá recenze a hostované CI mají pro nový základ při této místní
integraci stav `NOT_RUN`.
