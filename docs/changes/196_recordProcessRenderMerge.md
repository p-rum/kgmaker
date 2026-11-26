# Záznam sloučení čtecího vykreslení procesu

Datum 2026-11-26. [T048-S01 / T048-AC01](../tasks/48_completeImplementationHandoff.md#3-první-krok-t048-s01--sjednotit-stav-a-vytvořit-pracovní-seznam)
· [T034-S01/S02 a T034-AC01 až AC06](../tasks/T-034_add-process-cli.md).

## Ověřený merge #177

[PR #177](https://github.com/p-rum/kgmaker/pull/177) je sloučené do `main`
jako `a2adbe2e8666fbc76bf87b0aa2fd2be288bdf6bc`. Rodiče jsou v pořadí
`8290606eace7d7c94497cca143fa8e70c0042d38` a schválený head
`9d2feda17755f26d7fe40f96b416cd910431ca69`. Strom merge
`49817c0ab1c8de3a46675cd832ce1496113e84ca` odpovídá přímo schválenému headu.
SHA-256 dokladu o sloučení
`c7c236e711fa35e957551b0dd740d6334979039f6ef36debbf404a6035e455c4`.

Nezávislá T045 vydala `APPROVE` pro přesnou dvojici base/head. Opakovaný běh
s připnutými fixture z offline Maven adresáře má **51 PASS / 0 SKIP** a raw exit
0 na CPythonu 3.13.18 a Temurin JDK 21.0.6+7. Bylo zachováno 934 sledovaných
souborů i otisky workerů. Před tímto během chyběl ukazatel k připnutým JAR
a dva případy skončily při přípravě fixture. SHA-256 zeleného JUnit
`775d90c2d1a4a2037bab370f3449d1bbdb181c5aa10c3fd151812b3802a207bf`.
[Přesný verdikt T045](https://github.com/p-rum/kgmaker/pull/177#issuecomment-7203281429).

Na přesném `main` `a2adbe2` prošlo po sloučení **16 PASS / 0 SKIP** za 26,04 s,
raw exit 0. Běh zahrnuje Javac 21 se dvěma původními indexy workspace, oba
selektory T034, kontroly omezeného toku a plánovač. SHA-256 JUnit
`3677d1f2f1d3f9fa2f7fd16148c70707b10dbec1f645e4b670888f6fd333f998`.
Shodné manifesty 934 souborů před a po mají SHA-256
`9ff14f7046c6fa3b461e16e88ed795fdd1f58e713317df459010e32842e9adea`.

## Rozsah a navazující práce

Kanonický T034 má stav MERGED / PARTIAL. `kgmaker process render --format json`
přijímá přesný T024 trigger nebo explicitně dodaný jedno-triggerový T025
`ProcessView`. V obou cestách používá stejný provider, úplný kanonický přepočet,
vybraný scope a kontext. Legacy `flow render --view process` má vlastní CFG
formát. Dohledání uložené revize, obecný víceslužbový výběr, další formáty a
životní cyklus `prepare`, `validate`, `apply` a `review` mají vlastní rozsah.
T034-AC02 zůstává NOT_RUN. [Příkazy](../process-paths.md#read-only-process-render-t034)
· [Kritéria](../acceptance-inventory.md#t034--lokální-technický-json-render).

T035 může začít čistým Mermaid rendererem nad explicitně předaným typovaným
`ProcessView`. Tento výřez zachovává původní ID, provenance a viditelné hranice
PARTIAL/UNKNOWN. T036 nadále závisí na T035. V plánu T040 stále blokuje T036.
Plný krok T040-S01 navíc potřebuje existující příkazy `process prepare`,
`validate`, `apply` a `review`, které čtecí dodávka T034 zatím neposkytuje.
[T035](../tasks/T-035_render-business-process-mermaid.md)
· [T040](../tasks/T-040_add-agent-process-instructions.md).

## Lokální ověření této aktualizace

Na výchozím `main` `a2adbe2e8666fbc76bf87b0aa2fd2be288bdf6bc` a s touto
dokumentační změnou obsahuje plán 135 položek. Z nich je 107 MERGED, 26 PLANNED,
jedna PR_OPEN a jedna IN_PROGRESS. Mění se pouze T034 a odvozené blokace
T035/T040. Z 32 položek delegace se odstraní T034 na druhé pozici, T035 se
přidá na pátou pozici a ostatních 31 položek zachová relativní pořadí.
SHA-256 plánu `fda1d22d17e8db1b521ad342bd1d60ad3d4470ffbe14ac87e8f7fb6e30f1d6bc`.

```sh
kgmaker completion plan --root "$PWD" --jobs 32
python -m pytest --assert=plain -q -p no:cacheprovider tests/test_completion.py
```

Cílená sada má **13 PASS / 0 SKIP**. SHA-256 JUnit
`b49c936e04216a5ecc33ff19d68dde86d7742887dadc1acc859936bd2f037b79`.
Úplná sada má pro tuto dokumentační revizi stav NOT_RUN.
