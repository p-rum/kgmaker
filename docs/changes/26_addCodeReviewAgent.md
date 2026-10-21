# Projektový agent pro review a merge pull requestů

- Change note: 26
- Datum: 2026-10-21
- Zadání: `T045`, kroky `T045-S01` až `T045-S03`, požadavky `T045-R01` až
  `T045-R04`, acceptance `T045-AC01` až `T045-AC04`.

## Problém

Implementační profily T003 končí vytvořením samostatných PR. Chyběl trvalý
projektový profil, který zreviduje skutečný aktuální PR diff, vrátí opravy a po
schválení merguje ověřený commit.

## Skutečné změny

- `.codex/agents/code-review.toml` přidává `code_review` s modelem
  `gpt-6.1-sol` a reasoning effort `high` pro PR review. Agent rozlišuje
  `APPROVE`, `REQUEST_CHANGES` a `BLOCKED`, uvádí reprodukci nálezu a váže
  verdikt na aktuální base/head SHA dvojici.
- Merge následuje po novém ověření PR stavu, required checks, závislostí a
  mergeability; používá `expected_head_sha`. Změna base nebo HEAD vyžaduje nové
  review a potřebné testy. Draft si agent sám nepřepíná na ready.
- AGENTS, registr úloh, registr agentů, README a stavová matice popisují
  předání PR. Interní Copilot `kgmaker-review` zůstává reviewerem task artifactu,
  nikoli GitHub PR.
- Implementační profily dál vytvářejí PR ve vlastních větvích a samy je
  nemergují. Projektový profil se neinstaluje přes `kgmaker init`.

## Kompatibilita a migrace

Python API/CLI, store v1/v2/v3, worker protocol a stávající runtime zůstávají
beze změny. Stávající PR nejsou pouhou instalací profilu schválená. Pro nový
profil je třeba načíst aktualizovaný projektový registr agentů v nové Codex
session.

## Příklad

```text
Předej konkrétní vytvořený PR agentovi code_review; po schválení jej merguj.
```

Agent ověří konkrétní base/head dvojici, vrátí případné blokující nálezy a po `APPROVE`
znovu načte kontroly. Pokud je PR draft nebo GitHub nepovolí review/merge,
uvede přesný stav a neprovede obcházející zápis.

## Provedené kontroly

- Read-only kontrola otevřených GitHub PR pro `p-rum/kgmaker`: #8 a #4 jsou
  draft; #8 míří do `feat/impl`. Dne 2026-10-21 byly navíc otevřené ready PR
  #11 a #12 do `main`; žádné z těchto PR nemá schválení pouze instalací profilu.
- Číslo nepublikovaného zadání bylo před externím zápisem změněno z T004 na
  T045, protože `main` mezitím používá T004 a T005–T044. Profil a jeho scope
  zůstaly stejné; nová kontrola odkazů a sémantiky proběhla po přečíslování.
- `codex debug models --bundled` potvrdil dostupnost `gpt-6.1-sol` a effort
  `high`.
- `python3` `tomllib` audit: 61 profilů, 61 unikátních jmen; model, effort a
  povinné stavy/HEAD/merge guard v novém profilu — PASS.
- `codex debug prompt-input 'Ověření registru projektového code-review agenta.'`
  — exit 0 po spuštění mimo read-only izolaci CLI. První pokus v izolaci selhal
  na read-only souborovém systému, nikoli na TOML parseru.
- Kontrola Markdown odkazů v sedmi dotčených souborech — 0 rozbitých odkazů.
- `PYTHONPATH=src python3 -m pytest -q --basetemp=/tmp/kgmaker-review-profile-pytest`
  — 182 passed, 15 skipped (volitelné workery nebyly ve worktree připraveny).
- Po explicitním lokálním zpřístupnění existujících worker artefaktů a offline
  sestavení Maven exporteru proběhla plná sada s `KGMAKER_REQUIRE_WORKERS=1`,
  Gradle 8.13 a JDK21/22 — 197 passed za 42,47 s, bez SKIP.
- `kgmaker semantic update --base b947fc3201161eacf71aaae050bcab0ba5f752eb`
  vymezil 6 změněných indexovaných cest; patch zachoval doložený koncept README
  a čtyři jeho vazby. `kgmaker semantic apply` — PASS (3 koncepty, 7 vztahů
  celkem); `kgmaker semantic validate` — PASS.
- `kgmaker memory capture --base b947fc3201161eacf71aaae050bcab0ba5f752eb`
  s doloženými validacemi — PASS.
- `kgmaker scan` — 215 souborů, 1654 deklarací/sekcí, 14341 vztahů;
  `kgmaker semantic validate`, `kgmaker status`, `kgmaker check` a
  `git diff --check` — PASS.
- Po sloučení s přesným stromem cílové větve `feat/impl`
  (`11576c09a94522a1bee24a736850c8426ac9417d`) byla sémantika i graf
  regenerována příkazy. Integrovaný běh `PYTHONPATH=src python3 -m pytest -q`
  — **184 PASS, 16 SKIP** kvůli volitelným worker fixture.
- Po explicitním offline sestavení Maven fixture a zpřístupnění existujících
  JVM/TypeScript workerů, React typings, Gradle 8.13 a JDK 21/22:
  `KGMAKER_REQUIRE_WORKERS=1 ... PYTHONPATH=src python3 -m pytest -q -rs`
  — **200 PASS, 0 SKIP za 38,12 s**. První přísný pokus bez Maven fixture
  hlásil 14 setup errors; další pokus bez React typings měl 1 FAIL. Oba
  chybějící testovací vstupy byly doplněny před finálním během.
- Po sloučení Gradle PR #14 a #15 byl T045 znovu integrován nad přesný strom
  #15. Obsahové sloučení zachovalo všech 29 sémantických epizod; regenerovaný
  graf a `kgmaker check` prošly. První full běh měl 218 PASS, 1 FAIL a 2 SKIP
  kvůli chybějícím React typings a Maven exporteru v čistém worktree.
  Po připojení existujících lokálních testovacích závislostí stejná přísná
  sada se skutečnými workery, Gradlem 8.13 a JDK21/22 dosáhla
  **221 PASS, 0 SKIP za 48,24 s**. Dočasné symlinky byly po testu odstraněny.

## Neprovedené kontroly

PR #13 do `feat/impl` byl vytvořen, ale živý merge zatím neproběhl. Po posunu
base o #14 a #15 vyžaduje nový vzdálený HEAD, aktuální review a zelené CI;
vytvoření profilu to nedokládá.

## Zbývající práce

Koordinátor předá vytvořené PR agentovi `code_review`. Každé PR musí projít
vlastní acceptance a review; stav T003 tím automaticky nepřechází na dokončeno.
