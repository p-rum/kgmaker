# 179 — Ověření zdrojových uzlů Kafka katalogu s modelem buildu

Rozsah T012-S04 a T012-S05, acceptance T012-AC04, T012-AC05 a T012-AC06.
Reprodukce běžela na `9f07bf742a85204760b61bbaf1ae4c360437ead9` po #150.
Implementace vychází z `5d067f152522442fa4cff22c2e69e1b9b6fcef86` po #157,
který zachoval produktový kód a worker zdroje dotčené tímto případem.

## T012-S04 — Oprava porovnání File uzlu

Explicitní model vybraného source setu uvádí u File uzlu soukromého
compiler snímku členství `root:main` a původ `handwritten`. Při offline
načtení má stejný File uzel ve veřejném grafu klasifikaci zdrojového
skeneru. Dřívější přímé porovnání těchto uzlů odmítlo platný compiler
důkaz při sestavování katalogu.

`src/kgmaker/interfaces.py` pro tento typ důkazu ověřuje oba File uzly.
Vyžaduje zvolený vstup raw JVM kontextu, platný otisk v soukromém
i kvalifikovaném veřejném inventáři, jedinečný veřejný uzel a stejný scope
i roli. Soukromý uzel musí přesně odpovídat File klasifikovanému jeho
modelem. Veřejný uzel musí přesně odpovídat výsledku běžného skeneru.
Původní kontrola deklarací, symbolů, call sites, vazeb a důkazů zůstává
stejně přísná.

Katalog ověřuje uložené indexy a zdroje čtecí cestou. Spuštění workeru
patří k samostatné explicitní inspekci. Katalog funguje s dosavadními
snímky, jejich uloženým formátem i identifikátory.

```sh
kgmaker architecture interfaces --catalog kafka --capture-local --workspace workspace.json
```

Příklad předpokládá aktuální soukromé compiler indexy. Výsledek zachovává
statické bindingy a `delivery=NOT_OBSERVED`. Rozsah parserů, Kafka K2
anotací a runtime evidence popisuje [kontrakt Kafka katalogu](../kafka-interfaces.md).

## T012-S05 — Skutečné ověření

Nový `test_actual_kafka_catalogue_preserves_file_mirror_for_selected_project_model`
spustil skutečný K1 worker na připnutých Spring/Kafka artefaktech a JDK 21
v Cloud Environment.

- RED nad `9f07bf7` má 1 FAIL, 0 SKIP a exit 1. Katalog odmítl File
  jako `Original public compiler Node is missing or changed` při porovnání
  endpointu compiler důkazu. JUnit SHA-256
  `d38efec861334f962447b89ae9a5d6d510f3a3d4db5833a70cdedf69b7a2d112`.
- GREEN nad opraveným `5d067f1` má 1 PASS, 0 SKIP a exit 0. Test ověřuje
  dvě statické skupiny, `NOT_OBSERVED`, chybějící, duplicitní a pozměněný
  veřejný File i pozměněný soukromý File. Při čtení zakazuje procesy a síť
  a porovnává vstupní hodnoty a soubory před a po volání. JUnit SHA-256
  `f92b8e1a8f8c469c359e7a63f9286a5124197b21380d57a4307075fc1a2a58af`.

```sh
python -m pytest -n 3 --dist loadfile -p no:cacheprovider \
  tests/test_t012_catalog_kafka_interfaces.py tests/test_kafka_bindings.py \
  tests/test_t019_add_architecture_json_cli.py tests/test_workspace.py
```

Výběr má 242 PASS, 0 SKIP a exit 0 se skutečnými K1 a K2. Pokrývá
108 případů T012, 83 upstream Kafka bindingů, 34 testů T019 a 17
workspace případů. Mezi kontrolami jsou původní repo alias, Javac LF a
CRLF, chybějící vstup, výběr mezi compiler kontexty a pozměněné důkazy.
JUnit SHA-256
`d6834873c9341801aa28e0ea1ebaac54a4f9e87fa140cb5e349bf27a70f04358`.
Produktový manifest před a po testech má SHA-256
`1a9a228a4d610ab5720f7d2afba955cdd8ae54a641aeafec41a45c497dfe2ac4`.
Sémantická aktualizace zachovala všech 427 předchozích epizod,
56 konceptů a 206 vztahů.

Uživatelský příklad je v [T019 CLI](../architecture-json-cli.md) a rozsah
ověření v [inventáři](../acceptance-inventory.md#t012--kafka-interface-catalogue-verified-bounded-scope).
Celé T012 zůstává PARTIAL. Úplná standardní sada, Windows, GitHub Actions
a nezávislé review mají při lokálním předání stav NOT_RUN.

## Přenos po #162 a oprava po nezávislém review

První rodič `8d962d38f1c535b1c1cb0797a982a53f0a5290ae` zachovává výše
uvedenou opravu a jejích 242 PASS. Druhý rodič
`ec95f1ee1c3400cf90e79c45950a4da339a4998a` je sloučený [#162](https://github.com/p-rum/kgmaker/pull/162).
Přenos zachovává [živou inspekci W01](178_reduceLiveInspectionOverhead.md)
a [změnu ověření Excel skillu z #157](173_removeRepositorySelfCheck.md).
Verdikty nad prvním rodičem vyžádaly porovnání skutečných bajtů přečtených
při druhém skenu. Při změně LF na CRLF mezi ověřením capture a načtením
veřejné reprezentace zůstal normalizovaný otisk stejný a katalog dříve
přijal zastaralý důkaz.

`project_kafka_interfaces` nyní porovná i bajtový otisk z téhož omezeného
skenu. Kontrola využívá jeho existující `raw_file_hashes` a zachovává
oddělené ověření normalizovaného otisku a klasifikace. Katalog odmítne
změnu bajtů, i když se normalizovaný text shoduje. Stejné bajty CRLF
zůstávají přípustné při odpovídající aktuální inspekci.

Před opravou selhal nový řízený LF→CRLF případ na společném základu
se skutečným K1. Katalog přijal důkaz původního snímku i při změně bajtů
a test hlásil `DID NOT RAISE`. JUnit má 1 FAIL, 0 SKIP a SHA-256
`0884868691be0f4be78a35c51608952b624fc058300d5a325d60bbc8b070f29e`.

Na opraveném společném stromu má cílený běh v Cloud Environment 76 PASS,
0 SKIP a exit 0. Pokryl nový LF→CRLF případ, repo alias, Javac LF/CRLF
v T019 a aktuální Kafka bindingy. Skutečné K1 a K2 ověřily studenou
a opakovanou inspekci W01. Změna classpath vedla k novému kontextu.
Regrese locale a cyklu odkazu na spouštěč zachovaly předchozí publikovaný graf.
Ověření zahrnulo také tři případy instalace skillů a scanu.
JUnit SHA-256
`efb03d49e2d355293de2652355db1035ab972b570581f4bda0ddc28f64ec8569`.
Produktový manifest před testy a po nich má SHA-256
`63e034c72b0b0d2d55fdc133a5bd3ba7c69d2875480a7496e0d2cdb425bfa9cb`.
Samostatná kontrola platného CRLF souboru s explicitním modelem produkčního
source setu potvrdila u skutečných K1 i K2 obě deklarované skupiny ve stavu
`VERIFIED_STATIC` a nezměněné vstupy i uložené soubory.
Otisk JSON důkazu je
`45c8a533ddcce3a4f43609b52be873461e320d4feff90ab4fcce1f0e4635d489`.

Z 428 sledovaných produktových cest má 426 shodné bajty s druhým
rodičem. Odlišnosti tvoří pouze Kafka projekce a její regresní test.
Sémantická aktualizace zachovala 431 historických epizod obou rodičů,
56 konceptů a 206 vztahů. T012 zůstává PARTIAL. Úplná standardní sada,
Windows, GitHub Actions a nezávislé review tohoto stromu mají při
lokálním předání stav NOT_RUN.
