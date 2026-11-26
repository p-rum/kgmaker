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
