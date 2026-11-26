# T053 — Upgrade a odstranění instalace v cílovém projektu

Task ID: T053 · Revision: 1 · Datum: 2026-11-24 · Stav: SPECIFICATION.
Baseline: `edb65e57ca4de1743c810689c78e069cd86b2b41`.
Závislosti: existující init a T050 skilly; návaznost na migrační návrh T049-S06,
bez tvrzení dokončení jeho hostitelských profilů a Git autorizace.

## Rozsah a kontrakty

- T053-R01: Jeden inventář Python templates pro init a upgrade; verzovaný
  `.kgmaker/install-manifest.json` s otisky skutečně instalovaných souborů.
- T053-R02: `kgmaker upgrade [--root PATH] [--dry-run] [--force]` aktualizuje
  integraci na instalovanou distribuci, přidá nové výstupy a odstraní vysloužilé.
  Neinstaluje Python balíček. Upravené soubory blokují celý plán bez force.
- T053-R03: `kgmaker uninstall` se stejnými volbami odstraní vlastněné výstupy,
  vlastní ignore pravidla a celý `.kgmaker/`, včetně uživatelských poznámek,
  konfigurace a historie. Cizí soubory a pravidla zachová.
- T053-R04: Bez manifestu rozpozná známé historické otisky, ne pouhá jména.
  Neznámá verze/poškozený manifest, nebezpečná cesta či konflikt znamenají
  nulovou mutaci. Zachytitelná chyba publikace vrátí původní soubory.

Moduly: `cli.py`, nový `installation.py`, historické otisky, stávající
`skills.py` a `artifact_templates.defaults`; žádný nový graf ani store.
Non-goals: odinstalace globálního Python balíčku, spuštění aplikace/toolchainu,
mazání uživatelských exportů mimo `.kgmaker`, hostitelský reload či souběžné
editování instalace. Obsah distribuovaných instrukcí se nemění.

## Kroky a acceptance

### T053-S01 — Společný inventář a vlastnictví

- Závislosti: T050-S01.

T053-AC01. Init eviduje vlastnictví, zachová cizí soubory a opakovaný běh
zachová obsah i mtime.

### T053-S02 — Upgrade

- Závislosti: T053-S01.

T053-AC02. Simulovaná změna distribuce upgraduje agenty, hooky, skilly,
reference i templates. Kontrola zahrnuje chybějící a vysloužilé cesty i legacy migraci.

### T053-S03 — Uninstall

- Závislosti: T053-S01.

T053-AC03. Uninstall odstraní integraci a data, zachová aplikaci, cizí
instrukce, skilly a ignore pravidla. Opakování je idempotentní.

### T053-S04 — Chybové scénáře a distribuce

- Závislosti: T053-S02 a T053-S03.

T053-AC04. Dry-run, konflikty, invalidní manifest, symlinky a chyba publikace
mají nulovou mutaci. Kontrola zahrnuje CLI z jiného pracovního adresáře a instalovaný wheel.

## Migrace a dokončení

Migrace: staré projekty nemají manifest. Použijí se přesné známé otisky;
neznámé/upravené integrace vyžadují ruční sloučení nebo explicitní force.
Existující `init` zachovává soubory a editovatelné template páry.
DoD: cílené regrese, příklady, český change note, README, capability návod,
stavová matice, acceptance inventář a reviewovatelný PR. Přerušení procesu
či výpadek napájení během publikace a živý reload hostitelů nejsou garantované.
