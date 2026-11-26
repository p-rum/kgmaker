# Vazby cizích klíčů na pojmenované sloupce Flyway

[T003-S10-W02](../tasks/T003-S10-02-reverseDependencyIndexes.md),
T003-S10-W02-AC01 až AC04 a T003-AC10. Výchozí `main` je
`346536495db749a6a1d79f89b388b55f9db3da83`.

## Krok 1 — reprodukce chybějícího důvodu

Úplný lokální Flyway replay už rozlišil obě strany složeného cizího klíče.
Uložený graf vedl jen vazbu na tabulku. Po změně dvou dříve zachycených
operací nad skutečnými cílovými sloupci report chybně vrátil `affected: []`.
Fixture mění také jiný sloupec ve stejné tabulce a stejnojmenný sloupec
v jiné tabulce. Nezávislé kontroly a kontrola bajtů grafu prošly před
selháním požadovaného výstupu. Výchozí pytest exit 1 reprodukuje jednu
regresi. SHA-256 JUnit je
`089875dd9e8f86845f6a155c05e188ea8c48d39634997183f48848f7c283fe93`.

## Krok 2 — uložená vazba a kompatibilita

`schema_replay.py` při publikaci úplného lokálního přehrání verzovaných
migrací uloží `foreign_key_references_column` pro každý přesně doložený
pojmenovaný sloupec explicitního cizího klíče. Constraint drží identitu
tabulky a seznam identit sloupců v pořadí `REFERENCES`. Používá identitu
objektu z již provedeného replaye. Migrační operace cílená na některý
z těchto sloupců nese stejný otisk replaye. Implicitní odkaz na tabulku,
neúplná skupina a dodaný snapshot používají dosavadní deklarované vazby.
Starší graf se načte se svými vazbami a další `scan` využije nový projektor.

## Krok 3 — historický report bez zápisu

`graph_provider.py` při `impact --evidence-only` ověří identitu cizího klíče,
rodičovské tabulky, přesného sloupce a uložené migrační operace v jednom
streamu a otisku replaye. Vracejí se původní identita cizího klíče, cesta
změněné migrace, identita sloupce a identita a řádek operace. Důvod je
`SCHEMA_DEPENDENT / RECHECK`. Report zachová bajty uložené generace a
neopakuje replay zdrojů. Nový `scan` přehraje změněné zdroje a publikuje
graf pro další výpočet dopadu.

Kontrola provizorního kandidáta s přesměrovanou hranou opět vyvolala exit 1.
Stejná tabulka a historický otisk dovolily použít jiný sloupec, přestože
patřil druhému cizímu klíči. Kontrola uloženého seznamu identit odmítá
přesměrovanou vazbu. SHA-256 JUnit je
`022dade77e5ea3d907e56e10557f9f0da6d3fc3e8cb77e50744d26814071a272`.

Lokální projekce používá existující `feature.current_graph` a `attach_schema`.
Workspace s dvěma explicitními databázovými streamy zachovává kvalifikované
tabulkové vazby. Ověření provizorního kandidáta reprodukovalo mimo lokální
rozsah nové hrany, exit 1. Oddělení lokálního projektoru zachovává původní
výsledek workspace. SHA-256 JUnit je
`ac738601b795a9059977b2a3db823c98dd8360b3e3eb6848a7a8d6b5d8fe014f`.

## Krok 4 — ověření

Cílená sada v Linux Cloud Environment má **118 PASS / 0 SKIP** za
135,93 s. Pokrývá skutečný Flyway replay, přesný složený klíč, neúplné
vstupy, změnu identity po opětovném vytvoření, starší tabulkové vazby,
shodné názvy v různých tabulkách, nesouvisející sloupce stejné tabulky,
neshodný replay či migrační cestu a workspace. Skutečné JDK 21.0.6+7 s K1
a K2 ověřilo stávající ORM kompatibilitu. Pytest, sestavení manifestu a
porovnání jeho bajtů mají exit 0. SHA-256 JUnit je `2768b7fb07e1dfb34e8fc0c7ce549e73e0c42c9e893cbc7d5bfd986740610467`. Shodné
578řádkové manifesty mají SHA-256 `357fa09a08d9af6a7795e02aeef22d96cd9000cb3bace1207d72bd565d97abaa`.

```bash
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData \
  python -m pytest -n 2 --dist load --maxschedchunk=1 -q --tb=short -ra \
    -p no:cacheprovider -o tmp_path_retention_policy=failed \
    tests/test_reverse_dependency_index.py tests/test_flyway.py \
    tests/test_schema_compatibility.py tests/test_persistence_realms.py \
    tests/test_completion.py tests/test_workspace.py \
    -k '(test_flyway or test_persistence_realms or test_workspace or test_completion or test_schema_compatibility or test_explicit_composite_fk or test_explicit_fk_column or test_fk_column_projection or test_replayed_schema_and_openapi or test_schema_dependency_follows_prior_migration_operations or test_legacy_and_unproven_name_matches) and not test_actual_selected_realm_without_physical_binding_stays_unknown'
```

## Krok 5 — použití a zbývající rozsah

```bash
kgmaker scan --root ./service
# Po změně uložené migrace před dalším scanem:
kgmaker impact --root ./service --evidence-only --format json \
  src/main/resources/db/migration/V3__alter.sql
```

Skutečný příkaz `impact` v lokální fixture vypsal pouze cizí klíč s přesným
sloupcem a operací, zatímco se změnil i soubor s jiným sloupcem. Všechny
trvalé soubory grafu mají před a po reportu totožné otisky. SHA-256 JSON je
`b46f1f59110de50486051f7cb92a0404229da0f36db961dee17fd52d1104ca52`. Vyhodnocení W02-AC01 je `PARTIAL`. Plánovač má 135 položek, 106
`MERGED` a 29 `PLANNED`, všech 32 kandidátů má stejné pořadí jako na výchozím
`main`. Zahájení W03 čeká na stav W02 `VERIFIED_IN_SCOPE`. SHA-256 výřezu
plánu je `8d7601445fe45cc9f2bfdb4411433c23cabe0f65dd7b5970d2aa1972d5cece51`.

[Příklad a výstup](../stage-content-cache.md#selektivní-dopad-změn),
[acceptance](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy)
a [stavová matice](../production-analysis-progress.md) uvádějí aktuální
rozsah. Příklad `impact` v [README](../../README.md#selektivní-dopad-změněných-souborů-t003-s10-w02)
popisuje zachycení pojmenovaných sloupců. Pravidla zadání pokrývají tento
rozsah. Širší automatická změna grafových nebo feature závěrů má další
acceptance. Úplná standardní sada této revize, běh mimo Linux a GitHub
Actions mají při lokálním předání stav `NOT_RUN`.

## Oprava po nezávislém review #175 — kroky 2 až 5

Výchozí publikovaný head je `1eab5cff9c52cf50e90b901eea0e03f0387de71b`.
Skutečný lokální replay složeného FK uložil otisk operace ve společném
replayi. Objekt operace postrádal vlastní seznam zasažených sloupců.
Regrese nad nezměněným zdrojem má očekávaný exit 1 a SHA-256 JUnit
`d223550d291933f199398172e61690682f9e2e823aa18d6d3662254fa0de5b17`.

`schema_replay.py` odvodí z již zachycených cílů operace jen sloupce použitých
cizích klíčů. K cílovým identitám uloží identitu operace, zdrojový soubor,
řádek a otisk replaye. `graph_provider.py` vyžaduje shodu záznamu s uloženou
operací a přesnou identitu dotčeného sloupce. Pokud záznam chybí nebo je
neplatný, report vynechá důvod pro FK sloupec. Běžný `scan` poskytne nový
doklad. Starší tabulkové a view důvody se vyhodnocují dosavadní cestou.
Jednotkové kontroly ověřují typy a souřadnice záznamu. Skutečný lokální replay
SQL fixture ověřuje uložení důkazu, čtení obou složek cizího klíče a zachování
výstupů grafu při reportu. Workspace používá původní tabulkovou projekci.

[Příklad](../stage-content-cache.md#selektivní-dopad-změn),
[acceptance](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy)
a [stavová matice](../production-analysis-progress.md) uvádějí podmínku
dokladu. Vstupy příkazu v README a revize zadání dál odpovídají postupu
`scan`, úprava zdroje a `impact`. W02 je `MERGED/PARTIAL` a W03 čeká na
`VERIFIED_IN_SCOPE`.

Cílená sada má **31 PASS / 0 SKIP** za 0,78 s, včetně skutečného
lokálního replaye, typovaných záznamů operace, běžných tabulkových a view
vazeb, workspace a plánovače. Pytest a sestavení a porovnání manifestů mají
exit 0. SHA-256 JUnit je `c3ae9e642f5ce5fa1ccd3d8cf8c6d3eda333dea02485855f445486ce73ac9087`. Shodné 539řádkové manifesty mají
SHA-256 `a6ff89b12d8e692519bb1deec25d4d6c81989a0dee915b7aa0865af73d91c782`.

```bash
python -m pytest -q --tb=short -ra -p no:cacheprovider \
  tests/test_reverse_dependency_index.py tests/test_flyway.py \
  tests/test_persistence_realms.py tests/test_completion.py \
  -k 'test_flyway or test_completion or test_explicit_composite_fk_columns or test_fk_operation_column_witness or test_foreign_key_column_gate or test_fk_column_projection_retains_renamed_identity or test_workspace_keeps_table_level_foreign_keys_for_two_explicit_realms'
```

Skutečný `scan` a `impact --evidence-only --format json` mají exit 0.
Report potvrdil jediný očekávaný důvod a shodu se záznamem operace.
Před a po reportu jsou shodné bajty všech uložených výstupů. SHA-256
JSON je `72139f381a3de9b4bc60f2146fab638b0a99b052e1a71ea73887c93b2d8b2a5d`. Plán má 135 shodných položek a stejné pořadí 32 úloh.
Záznam má SHA-256 `32abf9cc00c07154068bc7ad5d5a999f89ef863357007c07d0427b82e93c74ab`.

Úplná standardní sada této opravy, běh mimo Linux a GitHub Actions mají
při lokálním předání stav `NOT_RUN`.

## Přenos opravy po sloučení #174 — kroky 4 a 5

První rodič je `bc6ed2156524ab15295cc12f6be31f12715b736b` se stromem
`46953afe386067c1c119793dd1f0e0d891b869d7`. Druhý je skutečný `main`
`cb9848520b056518d028ceb8010ec6a6f9a43a2f` se stromem
`833ec83af3495311aafabb25a0f5de87181d1c62`. Soubory FK a jejich testy
mají přesné bajty prvního rodiče. Implementace, testy a příručky T025
mají přesné bajty druhého rodiče. Společný README, acceptance a stavová
matice odpovídají nezávislému třícestnému sloučení. Graf zachovává všech
464 historických epizod obou rodičů. [Change190](190_bindLocalProcessContext.md).

Cílená sada uvedená výše má na společném vstupu **31 PASS / 0 SKIP** za
0,63 s. Skutečný lokální replay, starší tabulkové a view důvody, workspace
a plánovač prošly. Pytest, sestavení manifestu a jeho porovnání mají exit 0.
SHA-256 JUnit je `428ad83fb806ba1f3c30579981d5b05e1ddbc9f4d59fd283b921fa868090f9fe`
a shodného manifestu `53243b4213d910b0ac91ecb553731d165a91538913c3631a7c5ae8cfc01bb45e`.

Čerstvý lokální běh `scan` a `impact --evidence-only --format json` má
exit 0. Jeden přesný důvod odkazuje na vlastní cílový sloupec operace.
Uložené soubory mají před reportem i po něm shodné bajty. SHA-256 JSON
je `e4f4d700712e5202d4b02cd02c83ac1cf6095224afa71060d23ca69f63c72ee9`.
Plán má proti `main` shodu 134 ostatních položek a pořadí všech 32 úloh.
T025 včetně odkazu na #174 odpovídá druhému rodiči. W02 uvádí #130 a #175
ve stavu `MERGED/PARTIAL` a W03 čeká na W02 `VERIFIED_IN_SCOPE`. SHA-256
výřezu plánu je `6adb6cec0942028d7843d0c24637a5a6cf3f36c6bb5886e64e5766785016eae5`.

Úplná standardní sada společného stromu, běh mimo Linux a GitHub Actions
mají při lokálním předání stav `NOT_RUN`.
