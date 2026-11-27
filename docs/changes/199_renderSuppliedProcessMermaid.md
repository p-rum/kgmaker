# Čtecí Mermaid diagram dodaného procesu

26. listopadu 2026. [T035](../tasks/T-035_render-business-process-mermaid.md),
první výřez nad `main` `c4a1edb59f140faeafba0d5e979023bba185f3f1` se sloučeným
JSON rozsahem T034. Výchozí `ProcessView` obsahoval původní technické uzly a
přechody. Pro tento model chyběl veřejný Mermaid renderer.

## T035-S01 a AC01 — výskyty a služby

`kgmaker.process_render.render_process_mermaid(view)` přijímá existující typovaný
`ProcessView` schema 1. Podgrafy používají jen výslovně uvedené `service:` owner
ID, ostatní uzly zůstávají mimo service lanes. Renderer zachovává každý původní
uzel a orientovanou hranu včetně paralelních výskytů. Vazby `async` mají tečkovanou
šipku. Komentáře mapují výskyty zpět na stejný dodaný model.

## T035-S02 a AC01/05 — podmínky, cykly a hranice

Podmínky, retry, výjimky a smyčky vycházejí z technických popisků, relací a
atributů `ProcessView`. U fan-outu renderer nevkládá pořadí mezi konzumenty.
Viditelné hranice přebírají doložený stav a freshness. Diagram zachovává
rozsah, kontext, provenance, mezery a explicitní `PARTIAL` či `TRUNCATED`.
Výsledek neodvozuje runtime pozorování ani úspěšné doručení.

## T035-S03 a AC03/04/05 — stabilita, escaping a limity

ID jsou deterministická podle výskytu v modelu. Nový modul přímo používá
stávající bezpečný textový a JSON encoder Mermaid, kontrolu bezpečnosti výstupu
a sdílený ohraničený průchod vstupem. Při neplatném typu, scope nebo kontextu,
nebezpečném obsahu či překročené velikosti skončí `ProcessMermaidError` bez
výstupu. Schéma modelu, úložiště, architektonické renderery a obě existující
CLI cesty se nemění. Migrace není potřeba.

## T035-S04 a AC01/03–05 — skutečné testy

Na baseline validní `checkout.json` narazil na chybějící modul
`kgmaker.process_render`, **1 FAIL**, raw exit 1. Další cílená regrese zachytila
neescapovaný text scope v titulku návrhu. Titulek, uzly a hrany nyní používají
stejný textový encoder. JSON metadata chrání odpovídající sdílený encoder.

`tests/test_t035_render_business_process_mermaid.py` prověřuje:

- `test_t023_checked_in_branch_cycle_and_origins_are_deterministic` a
  `test_t023_golden_parses_and_renders_branch_cycle` pro podmínky, cyklus,
  7 uzlů, 8 hran, původní důkazy, nulové I/O a shodu kanonických bajtů.
- `test_t028_projection_places_service_lanes_without_ordering_fanout` pro
  stávající projekci T028 se dvěma explicitními vlastníky, 13 uzly a 12 hranami.
- `test_real_t029_javac_retry_dlt_keeps_static_boundary_and_exception_path`
  pro skutečný Javac 21.0.6, 22 uzlů a 24 hran. Zachová výjimku, retry, DLT
  a doložené `NOT_OBSERVED` i soubory a JSON vstupu.
- `test_truncated_parallel_edges_escaped_text_and_no_unverified_business_label`
  pro bezpečný text v popiscích i titulku, `TRUNCATED`, 7 uzlů a 9 hran, včetně
  dvou shodně orientovaných výskytů. Dodaný příznak `APPROVED` sám nezmění popisek.
- `test_invalid_input_and_limits_leave_supplied_and_last_valid_artifact_unchanged`
  a `test_output_bound_refuses_the_whole_diagram` pro odmítnutí bez vedlejších
  účinků.

Čtyři diagramy zpracoval připnutý Mermaid 11.4.1 s jsdom 26.0.0 a Node 24.22.3
z existujícího locku. `tests/rendering/validate_t035_process.mjs` porovnal vrcholy,
orientované hrany a lanes přímo z parseru. V SVG ověřil počty vrcholů a hran
a absenci aktivních prvků a odkazů z dodaného textu. Reálný cílený běh skončil
**109 PASS / 0 SKIP / 0 FAIL** za 14,06 s. Zahrnul 11 případů T035 a regrese
T021 (28), T023 (69) a jednu původní kontrolu fan-outu T028. SHA-256 JUnit
`4dc00fea63063eca471d577114de3a6d0c912c0795442677d85caac10f4f09d0`.

Tento místní doklad patří stromu `437cc36b71520e601b194d88f9b614e7303d8558`,
který byl zveřejněn při otevření [draftu #183](https://github.com/p-rum/kgmaker/pull/183)
jako head `ab02b75d254ce52b224086953fd59d22f817eec3` nad `c4a1edb5`.

## T035-S05 a AC06 — dokumentace a předání

[README](../../README.md#local-technical-process-paths-t025) a
[Python příklad](../process-paths.md#mermaid-for-a-supplied-processview-t035)
ukazují cílové použití čistého rendereru. [Revize zadání](../tasks/T-035_render-business-process-mermaid.md),
[acceptance](../acceptance-inventory.md#t035--mermaid-nad-dodaným-typovaným-processview)
a [stavová matice](../production-analysis-progress.md) vedou otevřený výřez
ve stavu `PR_OPEN / PARTIAL`. Úplná sada, nezávislé review a hostované CI
měly v uvedeném místním ověření stav NOT_RUN. T036 stále čeká na dodání T035.
Zbývá připojení CLI, autorita schválených popisků z T032 (AC02) a navazující
vysvětlení a export.

## T035-S05 a T035-AC06 — přenos kandidáta po #184

27. listopadu 2026. Přenos spojuje dosavadní head [#183](https://github.com/p-rum/kgmaker/pull/183)
`e8d737f80115b7475fe806b2cd83ad0d1cebedfe` jako prvního rodiče se skutečným
`main` `1841553b2f2923f9342a1674cacc1ea36b8e9092` jako druhým rodičem.
Po sloučení [#184](https://github.com/p-rum/kgmaker/pull/184) měl `main` strom
`99da626c7ad5a17d9e25902f4113d37b98599128`. Přenos zahrnuje mezitím sloučené
změny T022, orchestrátoru a compiler evidence W01 a W02.

V původní zdrojové přípravě před opravou limitů měly renderer
`src/kgmaker/process_render.py` a oba soubory jeho testů stejné bajty jako
na dosavadním headu. Společné Mermaid encodery T021 a příprava
Markdownu T022 zůstávají součástí stávajícího architektonického rendereru.
Veřejné použití čisté funkce a kontrakt JSON příkazu T034 jsou beze změny.
Přenos upřesňuje odkazy na #183 v acceptance a stavové matici a zachovává
T035 `PR_OPEN / PARTIAL`. Řádek AC05 popisuje ověřené diagramy `PARTIAL`
včetně `TRUNCATED` a hodnoty `UNKNOWN` v metadatech hranic. T036 při tomto
stavu čeká na dodání T035.
Autorita schválených popisků (AC02), širší CLI a export mají vlastní rozsah.

Předchozí archivovaný nativní běh nad headem `e8d737f80115b7475fe806b2cd83ad0d1cebedfe`,
základem `7919c283c4ea7b58eb99bfcfbc3971903984f438` a stromem
`e6403da4f04d8f5594e535449fd0be4fb4c5f807` měl **109 PASS / 0 SKIP**, raw exit 0.
JUnit SHA-256 `f23b2a8d9238ca4f2156d61ee9cf6ef4f4d3ae3c99fa455234e445d203a7174b`.
Při této zdrojové přípravě prošly `git diff --cached --check` pro běžné cesty
(raw exit 0) a `kgmaker completion plan --jobs 32` nad oběma inventáři
(raw exit 0). Plán zachoval 135 položek a stejných 32 kandidátů k delegování.
Jedinou změnou stavu je řádek T035, odvozené blokace se upravily u T036 a T042.

Generované soubory se změnily na obou stranách. Dosavadní nesloučená epizoda
`42bafeac9a4e1941616921fde6569036888303946919af586ea8d3c2956ea485` obsahuje
chybný záznam o odebrání tří existujících uzlů `Rates.xlsx`. Při nové
aktualizaci se použije stejná lokální projekce grafu pro základ i přenesené
soubory a zachová se historie skutečného `main`. V této zdrojové fázi měly
regenerace grafu, nativní a úplný běh nového páru, nezávislé review a hostované
CI stav `NOT_RUN`.

## T035-S03 a T035-S04 — limity Mermaid (T035-AC03, T035-AC04)

27. listopadu 2026. Při kontrole přeneseného kandidáta nad `main`
`1841553b2f2923f9342a1674cacc1ea36b8e9092` se ukázala mezera mezi limity
`ProcessView` a výchozím Mermaid 11.4.1. Parser odmítne 501. hranu a vykreslení
příliš dlouhého těla nahradí vlastním varovným diagramem. Dvě platné projekce
před opravou nevyvolaly očekávaný `ProcessMermaidError`. Cílená reprodukce měla
**2 FAIL / 0 SKIP**, raw exit 1, JUnit SHA-256
`02f3121608fc1e3d9243ad84382dd0ca0baeb7a3ce44d947906679ef54f7e111`.
Nezávislý archivovaný běh nad `e8d737f80115b7475fe806b2cd83ad0d1cebedfe`
potvrdil chybu parseru u 501 hran a náhradní SVG s jedním vrcholem a bez hran
u delšího těla. Kontrolní scénáře uspěly s raw exit 0 a SHA-256 dokladu
`8061764b812473c2c9e66078aaa5804e590af2d3dc492f0e61f09111627bb154`.

`src/kgmaker/process_render.py` omezuje celý diagram na 500 orientovaných
výskytů hran a 50 000 jednotek UTF-16 vlastního těla flowchartu. Mermaid před
měřením odstraňuje YAML hlavičku a komentáře s metadaty. Tato metadata se
nadále počítají do samostatného limitu 4 000 000 bajtů UTF-8. Překročení
kteréhokoliv limitu vrátí `PROCESS_MERMAID_LIMIT`. Výstup podporovaných
diagramů zachovává původní výskyty a formát metadat. Příklad a hranice uvádí
[čisté Python API](../process-paths.md#mermaid-for-a-supplied-processview-t035).

`test_default_mermaid_host_limits_refuse_the_whole_diagram` ověřuje platný
vstup s 501 hranami a tělo s 54 179 jednotkami UTF-16, shodu dodaného
`ProcessView` a původní bajty uloženého artefaktu. Kladný
`test_mermaid_host_text_budget_excludes_evidence_comments` má 59 556 znaků
včetně metadat a 47 779 jednotek UTF-16 ve vlastním těle. Skutečný Mermaid
vykreslí všech sedm vrcholů a osm hran do SVG.

Po opravě měly cílené Python kontroly **9 PASS / 0 SKIP**, raw exit 0,
JUnit SHA-256 `fa75ca9c1889a9ffa4c32ab000675b3267f122dc547b74e4658e4edc813c2b0a`.
Připnutý Mermaid 11.4.1 s jsdom 26.0.0 a Node 24.22.3 ověřil také původní
golden diagram, fan-out, zkrácený diagram a kladný případ s delšími metadaty.
Výběr `tests/test_t035_render_business_process_mermaid.py -k 'not real_t029_javac'`
měl **13 PASS / 0 SKIP**, jeden nezvolený případ a raw exit 0. JUnit SHA-256
`dfa06bba9c71a38f493282c01554842ca02a38925e84b8c3c9c9111c75c7a6f6`.
Kontrolované vstupy měly před a po běhu shodné bajty. Úplná sada, společný
nativní běh přeneseného headu a nezávislé review měly při této zdrojové
přípravě stav `NOT_RUN`. Schválené popisky a širší CLI zůstávají samostatným
rozsahem.
