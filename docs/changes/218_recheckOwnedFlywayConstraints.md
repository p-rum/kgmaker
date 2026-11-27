# Výběr omezení vlastní tabulky po změně migrace Flyway

Zadání [T003-S10-W02](../tasks/T003-S10-02-reverseDependencyIndexes.md), AC01–AC04. Přípravný zdroj a testy vznikly na `e7391ea58bb4d6e519a1886c309710752d8472e4`, strom `31a22963555e154b642f5030b85e2a98ab6bf663`. Dokumentační podklad po [#200](https://github.com/p-rum/kgmaker/pull/200) vychází ze sloučeného `eaf6dce8f0914fb0da8ac4d727c1e67672fe8ac5`, strom `39430e0aa583b3445b2435512e2e00e075e61b53`.

## Krok 1 — skutečná chybějící závislost (AC01)

`kgmaker schema inspect` vrací `COMPLETE`. `kgmaker scan --no-docs` uloží
`CREATE TABLE customer` ve V1, vazbu `contains_constraint` na samostatný
`UNIQUE(id)` ve V2 a doklad pro existující `VIEW customer_ids`. Druhá tabulka
`supplier` má své vlastní stejnojmenné omezení. Po změně založení `customer`
na `customer_v2` a nezávislé změně `SET DEFAULT` u `supplier` uváděl veřejný
čtecí report pouze pole view. Test na původním blobu provideru
`e3a926ae03f183caf142754e9ce5ab79003058fb` skončil kódem 1. Selhal přesně na
chybějícím `public.customer.unique_id` a pět negativních kontrol prošlo.
SHA-256 JUnit je `b9587db8e4cf9fe75b00827f503e897254fd383deb58f5995274cd1bf8f5d9c6`.

## Krok 2 — původní CREATE a samostatná deklarace (AC01–AC03)

[`graph_provider.py`](../../src/kgmaker/graph_provider.py) používá stávající
`contains_constraint` a `operation_targets` z úplného lokálního Flyway
replaye. Sváže tabulku, omezení i operaci s příslušnou konfigurací, streamem
a cílem. Tabulka s omezením musí mít stejný otisk snapshotu. Jmenný prostor
omezení musí patřit tabulce a zdroj a řádek hrany musí odpovídat uložené
deklaraci v samostatné migraci. Původní `CREATE` odpovídá zachycené identitě
tabulky, jejímu původnímu řádku, pořadí příkazu a obsahu. Historický bajtový
otisk replaye musí souhlasit s uloženým grafovým otiskem. Výstup přidává
důvod `contains_constraint` s identitou tabulky, identitou a řádkem CREATE
operace a předchozím hashem souboru. Používá stejný JSON kontrakt a tutéž
uloženou generaci. Jestliže doklad chybí, závislost zůstane neprokázaná.

Přípravný kandidát zachytil také omezení ze stejného migračního souboru.
Dvě existující kontroly FK odhalily širší dosah. Po zúžení na samostatnou
migraci prošly. Dřívější důvody pro cizí klíč, view a použitou feature
revizi zůstávají dostupné. Pro změny operace `RENAME TABLE` je zvlášť
zachycená sonda s kódem 1. Ověřený výsek pokrývá původní `CREATE TABLE`,
samostatnou deklaraci omezení a podklady se shodnými historickými otisky.

## Krok 3 — lokální testy (AC01–AC04)

Přípravný běh použil CPython 3.13.18 z lokálního prostředí. Příkazy s toutéž
verzí Pythonu na kořeni checkoutu:

```bash
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" GIT_OPTIONAL_LOCKS=0
python3 -B -m pytest -p no:cacheprovider -q --tb=short \
  tests/test_reverse_dependency_index.py::test_public_impact_requires_proven_owned_flyway_constraint
python3 -B -m pytest -p no:cacheprovider -q --tb=short -rs \
  tests/test_reverse_dependency_index.py tests/test_graph_provider.py tests/test_completion.py \
  -k 'not actual_jvm and not actual_javac and not malformed_stored_compiler_graph_keys'
python3 -B -m kgmaker completion plan --root "$PWD"
git diff --check
```

První příkaz nad původním produkčním blobem zaznamenal 1 FAIL a 5 PASS,
kód 1. Na přípravném opraveném zdroji druhý příkaz vrátil kód 0 s 65 PASS,
0 SKIP a 34 explicitně nevybranými případy. SHA-256 JUnit je
`25a5b7e1925b4f97336ba88fc8a0649fe0ed23e89712bacdb3fad6a198f49fa6`.
Širší přípravný výběr testů bez posledního filtru má 65 PASS, 1 SKIP a
kód 0. Přeskočení patří samostatnému nativnímu případu vyžadujícímu JDK 21+.
Šest variant nové regrese zahrnuje přesný kladný výstup a vyloučení
nesouhlasného snapshotu, cizího vlastníka, odlišného historického hashe,
nesprávné operace a grafu bez uložené identity vzniku. Testy zachovaly
bajty store a ověřily, že report nespouští scan, replay ani subprocess.

Původní veřejná sonda zavolala `schema inspect`, `scan --no-docs` a po
změně dvou zachycených migrací následující příkaz:

```bash
kgmaker impact --root ./service --evidence-only --format json \
  src/main/resources/db/migration/V1__customer.sql \
  src/main/resources/db/migration/V5__supplier_column.sql
```

Na opraveném zdroji vrátila kód 0. Report zachytil obě změněné cesty a
označil očekávané `SCHEMA_DEPENDENT / RECHECK` pro `public.customer.unique_id`
a dosavadní view pole. Samostatné omezení `supplier` vynechal. Všechny bajty
fixture zůstaly po reportu shodné. SHA-256 strojového důkazu je
`20ef10a8d68f7f1e4053a944d3e0a8e4560b54a528d347c8d02ed4936bc8bac1`.
`git diff --check` a plánovač skončily kódem 0. Plánovač zachoval W02
`MERGED/PARTIAL` a vyžaduje pro W03 `VERIFIED_IN_SCOPE`.

## Krok 4 — nezávislý nález a oprava dokladu deklarace (AC01–AC03)

Nezávislá sonda nad přípravným zdrojem našla tři falešné výběry při změně
proof hashe, původního SHA nebo jména uložené identity omezení. Přípravná
rozšířená regrese na provideru
`8edf6577e95aa0d2050436f3ea2f6d9251bec9b9` skončila kódem 1 s 5 FAIL a 6 PASS.
Zahrnuje také neodpovídající pořadí operace a skutečné CRLF, kdy se bajtový
otisk deklarace liší od grafového otisku normalizovaného textu. SHA-256
JUnit je `6777fb91ac3f50ceff408c30ff3e94a305e0642a5932e1935dcfb669d1983d27`.

Výběr používá společné ověření uložené identity vzniku, inkarnace a přesné
první cílené operace pro tabulku i omezení. Pro omezení vyžaduje zachycené
`ALTER` z jeho samostatné migrace. Její řádek musí souhlasit s uloženou
deklarací a historický bajtový otisk s uloženým grafovým otiskem. Pokud se
otisky pro CREATE nebo deklaraci liší, nová revalidace se nevybere. Běžný
grafový otisk normalizovaného textu dokládá raw obsah jen při jejich shodě.

Samostatná kontrola našla ještě jiný `ALTER` platně cílený na totéž omezení
na stejném SQL řádku. Přepsaný pořadový identifikátor starší deklarace na
novější operaci měl dříve falešný výběr. Samostatný mezikrok vrátil 1 FAIL
a 1 PASS, kód 1. Finální test zachovává skutečnou první deklaraci a odmítá
záměnu. Zůstává `RECHECK` z původního CREATE. Samotná změna migrace
`RENAME TABLE` zůstává samostatným případem mimo tento krok.

Na upravených zdrojích
`fbef2ba9dc67c3984cf22a30b1bdabc523c933a2` a
`912c47c3775847c0efa652ea8221948a91a17f8f` se stejným druhým příkazem
z kroku 3 prošlo 71 testů bez přeskočení, kód 0. SHA-256 JUnit
`fbcafb21b8392ef2883dc0b5115e0688d0fccb47efc3041ff168d34932e73261`.
Nezměněná původní nezávislá sonda má 8 z 8 úspěšných případů s kódem 0
a se shodnými bajty fixture i store. SHA-256 výstupu implementačního běhu je
`4e17fe7694e514acf7eac8a1fe2820561966b68e797bd9e9daf7e46c8b61301f`.
Nezávislý agent stejnou sondu zopakoval nad oběma uvedenými bloby. Ověřil
8 PASS bez přeskočení a nulovou mutaci fixture. SHA-256 jeho výstupu je
`3f79ec70930f08e5cdd26cd0e87545bcaa8043fb6d665339a723a98557d73517`
a dokladu `d442c90e11e5d0698ec69f2dd2f8347a6e0599b27cb0045ce4021e369d5c2bd6`.
Původní veřejný příklad má kód 0 a zachované bajty všech souborů,
SHA-256 `1f2f6df1c70d12aae22ce9cbce0416ac9bfaec6bfbe533966a39883e28dd9847`.
Samostatná zkouška rozhodnutí podle pořadí sdíleného řádku má kód 0.
Nativní a standardní sada se tímto přípravným během neověřují.

## Krok 5 — návod a stav (AC04)

Rozsah dopadu uvádí [README](../../README.md#selektivní-dopad-změněných-souborů-t003-s10-w02),
[výstup CLI](../stage-content-cache.md#selektivní-dopad-změn),
[acceptance inventář](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy)
a [stavová matice](../production-analysis-progress.md). Syntaxe ani
identita zadání se nemění. W02-AC01 a širší W02 zůstávají `PARTIAL`.
Úplný standardní pytest a nativní JVM zkoušky v přípravném běhu mají
`NOT_RUN`. Nezávislý posudek a přesné ověření výsledného integračního
stromu čekají na konečnou zdrojovou revizi.


## Krok 6 — přenos po sloučení #201 (AC02, AC04)

Základ přenosu je skutečný `8fba8bbd51a85e60eabd378b83439eb95413822b`,
potvrzený po sloučení [#201](https://github.com/p-rum/kgmaker/pull/201)
27. listopadu 2026 v 17:50:06 UTC. Strom
`1f4493dc5e8496d2f4740cb85c85060689571b95` má rodiče v pořadí
`eaf6dce8f0914fb0da8ac4d727c1e67672fe8ac5` a
`99c661000d2f6d32e7bdf09b0389cc41f90c4dbe`. Přenos zdrojového a
dokumentačního patche před doplněním tohoto záznamu měl strom
`e3cfed31f0e21c7f2ead49a6fe493c932eedb3c5`. Oba zdrojové bloby souhlasí
s krokem 4 a obsah S13 z #201 zůstává zachován.

Přípravná kompozice před doplněním naměřených hodnot měla běžný strom
f5315fb9bdcd55a7bf27b06795dd8f18cdbf4788 a epizodu episode:e2c2f975cf1b4988f9831798ef7043c1c28cab179347517ba32cc4c504557b6c. SHA-256 jejího
strojového grafu je ce48e1194c3195f500bfaa0ba162bf979b8dca469b1c343790054791cadc3ab4. Plánovač prošel 13 testy bez
přeskočení, raw exit 0. Logicky zachoval 135 položek a všech 32 pozic
dispatch včetně podmínky VERIFIED_IN_SCOPE pro W03. SHA-256 JUnit je
e1035eb0af6e533b12ae91abc955cdd744723f2377b82cdbeb5464251de4eaba.

Přípravná sémantická aplikace nejprve vrátila kód 2 při použití čísla
řádku AST definice jako identifikátoru grafu. Skutečný čerstvý strukturální
scan odlišil identifikátor dependency_impact s lokátorem 992 od definice
na řádku 994. Po svázání se scannerem a ověření skutečných volání přes AST
obě sémantické kontroly, aplikace, opakované zachycení, scan, status a check
skončily kódem 0. Všech 60 konceptů a 222 vztahů se zachovalo, z toho pět
vztahů má přesně doložený lokátor. Záznamy Rates.xlsx zachovaly tři uzly
a 275 vztahů. Všech 523 přijatých epizod zůstalo doslova shodných, Mermaid
zůstala stejná a přípravný strojový graf vykázal 35 přidaných a
25 odebraných uzlů. Vztahy importů se zachovaly, kontextový otisk a evidence
se podle zdrojů přepočítaly.

Příkazy integrace se spouštějí v pracovním stromu po aplikaci běžných změn
s přijatým lokálním strojovým grafem a sémantikou z uvedeného základu.
Přijatý archiv má SHA-256 2079f65140a6a63587582ed001a35135b1c14168050ab86eea7362524d6f9985,
dekomprimovaný vstup 9f6583a35a39c67d07887d5e10c8c2bd38ae501c88239ac715022a773a2fbae1.
Verzovanou sémantiku lze přečíst přes git show "$BASE":.kgmaker/semantic.json.
Čerstvá projekce ze samotných Git zdrojů může mít jiné bajty strojového
grafu než přijatá generace.

    BASE=8fba8bbd51a85e60eabd378b83439eb95413822b
    export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" GIT_OPTIONAL_LOCKS=0 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
    python3 -B -m kgmaker completion plan --root "$PWD" --jobs 32
    python3 -B -m pytest -q --assert=plain -p no:cacheprovider tests/test_completion.py
    python3 -B -m kgmaker semantic update --base "$BASE" --root "$PWD"
    python3 -B -m kgmaker semantic apply --root "$PWD"
    python3 -B -m kgmaker semantic validate --root "$PWD"
    python3 -B -m kgmaker memory capture --base "$BASE" --root "$PWD" \
      --validation planner=passed --validation source-diff=passed \
      --validation semantic-before-capture=passed \
      --validation historical-offline=passed --validation historical-independent-replay=passed \
      --validation exact-native=unknown --validation standard=unknown
    python3 -B -m kgmaker scan --root "$PWD"
    python3 -B -m kgmaker semantic validate --root "$PWD"
    python3 -B -m kgmaker status --root "$PWD"
    python3 -B -m kgmaker check --root "$PWD"

Před semantic apply se připraví scoped patch pro hodnotu update_id
z příkazu semantic update. Postup zachová existující tvrzení a použije
čerstvé strukturální identifikátory a doložené řádky. Přípravná epizoda se
po uzavření tohoto textu znovu zachytí z téže přijaté historie a s přesným
otiskem výsledného dokumentu. Uvedené otisky přípravné kompozice proto
patří předchozímu stromu. Přesný integrační a nativní test zůstávají
samostatným následujícím krokem.
