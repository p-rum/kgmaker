# T045 — Projektový code-review agent pro PR

- Task ID: `T045`
- Revision: 2
- Datum: 2026-11-03
- Stav: SPECIFICATION; popisuje cílový proces, nikoli důkaz, že již proběhlo review nebo merge všech PR.
- Baseline: `feat/impl` na commitu `b947fc3201161eacf71aaae050bcab0ba5f752eb`; cílová větev při publikaci `a39a24dde36ab104cf3d3f7dd07ef3a19f9d04cf`. T004–T044 jsou již obsazeny na `main`, proto má toto dosud nepublikované zadání T045.
- Závislosti: registr a profily 60 work packages z T003; jednotlivé PR musí splnit vlastní zadání a acceptance.

## Problém, rozsah a hranice

Implementační agenti vytvářejí samostatná PR, ale chybí trvalý agent, který by
zrevidoval aktuální PR diff, vrátil opravy a po schválení jej bezpečně sloučil.
T045 přidává projektový Codex profil `.codex/agents/code-review.toml` a proces
předání z implementačních profilů. Reuse existující GitHub PR a kontrol; nevytváří
nový store, automatický daemon ani paralelní implementační katalog.

Non-goals: obejití branch protection, merge draftu či stale HEAD, nahrazení
testů review verdiktem, přepsání interního `kgmaker task review` a automatické
vyhlášení T003 za dokončené. Profil sám nespouští ani neinstaluje projekt.

## Kontrakt a kroky

- `T045-R01`: Review čte skutečné PR, aktuální base/head SHA, zadání, change note,
  zdroj, testy, kontroly, závislosti a platné review. Nález uvádí konkrétní
  reprodukci a prioritu.
- `T045-R02`: Verdikt `APPROVE`, `REQUEST_CHANGES` nebo `BLOCKED` je vázaný na
  přesnou base/head SHA dvojici. Změna kterékoli SHA vyžaduje nové review a
  potřebné testy proti aktuální integraci.
- `T045-R03`: Merge smí následovat pouze po `APPROVE`, úspěchu všech ostatních povinných
  kontrol včetně lokálních acceptance/toolchain testů pro tentýž SHA, vyřešení blokujících review, splnění závislostí,
  ready stavu a ověření mergeability. Draft může přepnout jen autor,
  implementační workflow nebo samostatný explicitní pokyn. Merge používá
  `expected_head_sha` a před zápisem znovu ověří obě SHA. GH CI není povinný
  merge gate, pokud všechny ostatní kontroly prošly. Stav GH CI a důvod jeho
  neprovedení či selhání zůstává zveřejněný; konkrétní nález správnosti z CI
  nadále blokuje merge, dokud není vyřešen. Serverová pravidla se neobcházejí.
- `T045-R04`: Agent zveřejní review a po merge znovu ověří PR i cílovou větev;
  při nedostupné autorizaci nebo odmítnutí GitHubem uvede důvod a nic neobchází.

1. `T045-S01`: Přidat profil oddělený od implementačních a od interního
   `.github/agents/kgmaker-review.agent.md`.
2. `T045-S02`: Zapsat pravidla review/merge a použití do registru agentů,
   AGENTS a uživatelské dokumentace.
3. `T045-S03`: Ověřit syntaxi profilu, registr, odkazy a reálný read-only stav
   otevřených PR; spustit relevantní testy a kontrolu diffu.

## Akceptace a ověření

- `T045-AC01`: Codex načte jedinečný profil `code_review`; implementační
  profily dál vytvářejí vlastní PR bez vlastního merge.
- `T045-AC02`: Profil vrací blokující nálezy s konkrétní evidencí a nevyhodnotí
  změněnou base/head dvojici jako dříve schválenou.
- `T045-AC03`: Merge je omezený na schválený, ready, aktuální HEAD s úspěšnými ostatními povinnými
  lokálními kontrolami pro aktuální integraci a splněnými závislostmi; výsledek je
  ověřený z PR stavu. Draft zůstává blokovaný.
- `T045-AC04`: Dokumentace rozlišuje připravenou konfiguraci od skutečně
  provedeného review/merge a uvádí případné nedostupné kontroly.

Ověř `tomllib`, `codex debug prompt-input`, aktuální read-only PR stav,
relevantní testy, `git diff --check`, odkazy, semantic/memory/scan. Živý merge
ověř až na skutečně schváleném PR; nevytvářej testovací PR jen kvůli demonstraci.

## Kompatibilita, DoD a zbývající práce

Změna nezasahuje Python CLI, API, worker protocol ani graph/store v1/v2/v3.
Projektový profil se neinstaluje přes `kgmaker init`. DoD je validní profil,
aktualizované instrukce a český change note s přesnou evidencí, samostatná
větev a reviewovatelný PR do ověřené cílové větve. Dokud nejsou nové PR
publikovány a schváleny, jejich merge zůstává samostatnou následující prací.

## Uživatelská změna revize 2

Dne 2026-11-03 uživatel výslovně požádal, aby GH CI nebylo povinné, pokud projde
vše ostatní. Tato revize mění procesní merge gate; nemaže existující workflows,
nesnižuje acceptance ani požadavky na skutečný toolchain a nedovoluje zatajit
chybu z CI. Starší CI-only BLOCKED/CI_PENDING poznámky jsou historický stav
kontrol, nikoli samostatný důvod blokovat jinak ověřený merge. T045-R01–R04 a
AC01–AC04 zůstávají ve stejném zadání; nejde o nový Task ID.
