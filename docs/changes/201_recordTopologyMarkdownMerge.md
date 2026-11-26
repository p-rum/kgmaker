# Záznam sloučení Markdown topologie a dílčího důkazu S13-W03

Datum 2026-11-26. Výchozí `main` `fd8d5e958bf45b67775c04f78e817cc7d41ebfe9`.
[T048-S01 / T048-AC01](../tasks/48_completeImplementationHandoff.md#3-první-krok-t048-s01--sjednotit-stav-a-vytvořit-pracovní-seznam)
· [T022-AC06](../tasks/T-022_render-topology-markdown.md#acceptance-criteria)
· [T003-S13-W03-AC04](../tasks/T003-S13-03-runtimeValueFlow.md#akceptační-kritéria).

Stavová matice po sloučení #179 stále uváděla T022 jako PR_OPEN a u #181 držela
příznak draft z doby otevření. T022 je nyní v [matici dodání](../production-analysis-progress.md)
MERGED / PARTIAL. [T022-AC06 v evidenci](../acceptance-inventory.md#t022--markdown-report-topologie)
zůstává PARTIAL a odkazuje na skutečné sloučení. U T003-S13-W03 matice eviduje
obě dílčí sloučení a ponechává celek IN_PROGRESS / PARTIAL.

## T022 / #179

GitHub a lokální Git potvrdily sloučení #179 do `main` dne 2026-11-26 v 22:43:20 UTC.
Merge má SHA `fd8d5e958bf45b67775c04f78e817cc7d41ebfe9` a rodiče v pořadí
`7919c283c4ea7b58eb99bfcfbc3971903984f438` a
`47b49012cae3be172c28668fbf3ad1026c77c2d5`. Strom
`96da6d28602a9cc2aeb9a17441448468eb0710b8` je totožný se schváleným headem.
SHA-256 dokladu o sloučení `3ec0c90edc01208fd74d57c46398056d53335b9f543c949000e8740c7ca86227`.
[PR #179](https://github.com/p-rum/kgmaker/pull/179)
· [nezávislé APPROVE T045](https://github.com/p-rum/kgmaker/pull/179#issuecomment-7204923594).

- Přímý běh po sloučení na `fd8d5e9` s připnutými Mermaid 11.4.1, Markdown-it
  a Javacem 21 dal **26 PASS / 0 SKIP**, raw exit 0. JUnit SHA-256
  `3f5039bc1df2d11846b1c194edd22e494a81a97f57733e7dd264523664ae43f1`.
  Kontroly potvrdily 940 souborů beze změny a 39 položek nástrojů a workerů.
  SHA-256 manifestů je `c8e10c3d4b57aef6553e441a28f1e339be6528fa1cc95adf9ca048eb0ac27ef9`
  a `e26bc01f1acb2d3f62220bfacac01e5d5822ec471e8cbac87c43ea7b9a21a785`.
- T045 na přesné předschvalovací dvojici `7919c28` / `47b4901` prokázala
  **26 PASS / 0 SKIP**, raw exit 0, a bajtovou shodu výstupů původních příkazů.
  JUnit SHA-256 `1292256c1c84544c1fbdcd6ab32952bf87ac14310f905c3a1cdb90c2ddae5b1c`.
  Nezávislá kontrola correctness T052 na stejné dvojici má **25 PASS / 0 SKIP**,
  raw exit 0, JUnit SHA-256 `1b1c6c0b33d74d5ea4a83a55bac4f346f6691cc865b2d1483d50a42d609dfe57`.
- Autorův předschvalovací běh s reálnými parsery a Javacem na `47b4901` nad
  `7919c28` měl **26 PASS / 0 SKIP**, raw exit 0, JUnit SHA-256
  `5cc86f46f2114fe32f3927ef3a0c52ccdcaf060b7c7159f4e24a3c03b75d5bcb`.
  Standardní sada na stejném headu měla **2 662 PASS / 1 398 SKIP /
  1 očekávaný XFAIL**, raw exit 0, JUnit SHA-256
  `667c55057fbaa798c537dc3589625b85e2af1c64674b30f86d221006ca155543`.
  Dřívější dvojice revizí a doklady zůstávají ve [Change195](195_renderTopologyMarkdown.md).

Příklad příkazu nad zachycenou topologií je
`kgmaker architecture topology --root /repo --capture-snapshot topology-inputs.json --max-nodes 50 --format markdown`.
Report sdílí model
a diagram s T021. Při chybějícím zdrojovém lokátoru výslovně uvede
`SOURCE_LOCATOR_UNAVAILABLE` a stav `NOT_CHECKED`.
Širší provozní prostředí má stav NOT_RUN.
[CLI a jeho argumenty](../architecture-json-cli.md)
· [podporovaný rozsah](../service-topology.md).

## T003-S13-W03 / #181

Dílčí #181 je sloučené jako `7919c283c4ea7b58eb99bfcfbc3971903984f438`.
Rodiče jsou v pořadí `c4a1edb59f140faeafba0d5e979023bba185f3f1` a
`72ac18fcc26cc27070b0965f977838553061d2a3`. Strom
`f4326e2f9f8ecd84648ecfc598d7a4056ccb6960` odpovídá schválenému headu.
Otevírací head `1f6d909a612633fafbc70b15b3f6597445bce30d` a jeho strom
`e63e1a405da899fd1638b48a43727e3f7327fdb3` jsou historický snímek.
Dřívější dílčí #171 se sloučilo jako `7e9fa691417706562c875a01a40606350ae058ea`.
[PR #171](https://github.com/p-rum/kgmaker/pull/171)
· [PR #181](https://github.com/p-rum/kgmaker/pull/181)
· [nezávislé APPROVE T045](https://github.com/p-rum/kgmaker/pull/181#issuecomment-7204655390).

T045 na schváleném headu `72ac18f` zaznamenala **16 PASS / 0 SKIP**, raw exit 0,
JUnit SHA-256 `a06a0748d5d2922b1f189d005b5b9699b7a7359791efef5d53129a35dc9f366f`.
Samostatný Javac 21 běh po sloučení na `7919c28` má **23 PASS / 0 SKIP**, raw exit 0,
JUnit SHA-256 `2da5255696a97d4aa4adda912c293f6b9e12bd2fa92b888678e82ce5c29f6407`
a shodné manifesty 938 sledovaných vstupů před a po, SHA-256
`f994f655a6ab9af392782683ada9c6805a0fb792624da46349df5479ac935c60`.

Platí ověřený případ jednoho přímého přiřazení mezi statickými Java `String` poli
s hookem na stejném nebo následujícím řádku, v4 grafovým dokladem a aktuálním
`data-check`. Výsledek pro jeden běh zůstává `PARTIAL/UNASSESSED`. Instanční pole,
vícekrokové vazby a obecné hodnotové důkazy mají vlastní ověření.
[Výřez původního důkazu](187_bindRuntimeValuePresence.md)
· [výřez sousedního řádku](197_bindAdjacentRuntimeValueHook.md).

## Kompatibilita a další práce

Úprava eviduje stav dvou existujících dodávek. Veřejný kontrakt a příklady popisují
[README](../../README.md), [CLI](../architecture-json-cli.md) a [capability](../service-topology.md).
Tato evidenční změna používá dosavadní schémata a registr úkolů. Úplná sada
pro tento dokumentační krok má stav NOT_RUN.

## Ověření stavové matice

Nad základem `fd8d5e9` prošla cílená místní kontrola plánovače **13 PASS / 0 SKIP**,
raw exit 0. Příkaz byl `python -m pytest --assert=plain -q -p no:cacheprovider tests/test_completion.py`.
SHA-256 JUnit z kontroly matice
`6d8018f79d581a83f6b6a3790929b495e600ca1bc8515280da62b45c6fa1bb51`.

`kgmaker completion plan --root "$PWD" --jobs 32` načetl 135 položek, z toho
109 MERGED, 25 PLANNED a jednu IN_PROGRESS. Z prvních 32 vystoupil T022,
který přešel na `verify`, a na konec přibyl T003-S11-W02. Ostatních 31 položek
zachovalo pořadí. T038 stále čeká na T036, T041 na T038. T003-S10-W03 dál
vyžaduje, aby T003-S10-W02 mělo stav VERIFIED_IN_SCOPE.
SHA-256 plánu `1e3f6e12a6ab154000396bc8ca5fcd3e41cb38d78eb38cd6799a0d1342bd743b`.
