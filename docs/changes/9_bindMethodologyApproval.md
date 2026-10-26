# Vazba schválené metodiky na aktuální export

## Problém a skutečná změna

T003-S09-W04, acceptance AC01–AC04: feature packet přebíral schválený konflikt
z uloženého indexu i po změně HTML nebo rozhodnutí. Nyní před přenosem konfliktů
ověří SHA-256 stránek, příloh a sidecaru. Zastaralý/legacy index vynechá s explicitním
omezením a doporučením `kgmaker docs check`. Rozpor IMPLEMENTATION proti
APPROVED_REQUIREMENT nadále zachovává obě autority a decision/hash provenance.
Duplicitní rozhodnutí stejného tvrzení jsou odmítnuta; nedoložené tvrzení se odmítne
před publikací cache. Neprovádí se automatická oprava dokumentu ani kódu.

## Kompatibilita a příklad

Graph/store v1/v2/v3 ani worker protokol se nemění. Index verze 1 získává volitelné
pole `approvals_sha256`; starý index je čitelný, ale jeho konflikty je nutné obnovit.
`kgmaker docs check --confluence-dir export` a následné
`kgmaker feature prepare --requirement requirement.md --id routing` přenesou pouze
aktuální konflikty. Po změně exportu packet hlásí stale omezení bez approval.

## Kontroly

- Před opravou: nové cílené testy pro stale stránku, stale sidecar a duplicitu:
  3 failed; doložené failing acceptance.
- `PYTHONPATH=src python3 -m pytest -q tests/test_methodology_conflicts.py tests/test_scanner.py`:
  27 passed in 0.37 s.
- `PYTHONPATH=src python3 -m pytest -q`: 188 passed, 15 skipped in 6.43 s.
  Skips jsou nedostupné volitelné compiler workers v izolovaném checkoutu, nikoli PASS.
- Po zkopírování existujících ignorovaných build outputs z parent checkoutu (JVM/TypeScript workers, Maven exporter a fixture targets):
  `KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src python3 -m pytest -q`: **203 passed in 39.44 s**, bez skips.
- `git diff --check`: PASS.
- Kontroly nulové mutace cache při chybě i při stale feature čtení jsou v nových testech.
- Zdrojové změny nepřidávají žádné procesy, instalace, buildy ani DB.

## Neprovedené kontroly a meze

Live Confluence, autentizace schvalovatele a libovolná business ekvivalence nejsou
součástí tohoto offline kontraktu. Samostatný rebuild toolchainů nebyl proveden; skutečné workers byly ověřeny v povinném full-suite běhu. Celý T003-S09 není dokončen.

Scoped semantic update/apply/validate a memory capture nad `b947fc3`, následný scan/status: PASS. Dotčený existující koncept a pět doložených vztahů zachovány; nevznikly vymyšlené vztahy.

## Integrace proti main (2026-10-26)

PR byl znovu integrován proti `0c0902896c4803be7e7c1246aa0ba5da45f8ebe2`.
Konflikty dokumentace zachovávají novější upstream popis Gradle/Kotlin/workspace
i tento work package. Sémantická vrstva zachovává všechny unikátní historické
epizody z obou větví; pět dotčených existujících vztahů bylo ověřeno ve zdroji
a znovu aplikováno scoped patchem. Nevznikají nové tvrzené business vazby.

- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_methodology_conflicts.py tests/test_feature.py tests/test_scanner.py`: **56 PASS**.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q`: **229 PASS, 21 SKIP** (10.87 s), Python 3.12.14 bez připravených checkout worker/build artefaktů.
- Dvě nové parametrizované varianty mění/mažou skutečnou SVG přílohu:
  původní aktuální approval je zachován, po mutaci se konflikt nepřenese;
  index zůstane byte-identický a samostatná freshness kontrola nespustí proces.
- `semantic apply` a `semantic validate`: PASS; všechny původní graph/store
  kontrakty zůstávají beze změn.

Tato integrační evidence nenahrazuje historický worker běh uvedený výše.
Live Confluence a autentizace zůstávají NOT_RUN; T003-S09 je PARTIAL.

Review integrace navíc odhalilo a opravilo P1: změna exportu mimo checkout po
`feature prepare` nebyla v source manifestu, takže starý packet mohl projít
freshness kontrolou s dříve schváleným konfliktem. `feature.freshness` nyní porovná
uložené konflikty s právě ověřeným documentation coverage. Tři skutečné externí
varianty (HTML, sidecar, smazaná příloha) invalidují připravený packet bez změny
packet/index souboru. Round-trip nezměněného externího exportu zůstává fresh.
Veřejná schema i formát starého packetu zůstávají čitelné; chybějící seznam
konfliktů se porovnává jako prázdný seznam.

Finální lokální full suite po opravě external-packet freshness:
`PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q` —
**232 PASS, 21 SKIP** (5.00 s). Strict pokus s připravenými JVM/TS worker
artefakty bez skutečné Maven fixture: 229 PASS, 7 SKIP, 14 setup ERROR
(`Actual Maven fixture build is required`), tedy nikoli PASS; změna nezakrývá
chybějící toolchain/fixture. Nový vzdálený compiler CI musí tuto hranici ověřit.

Po dokončení skutečné Maven fixture v koordinujícím checkoutu (BUILD SUCCESS,
JUnit 1 PASS) byly její ignorované `target` artefakty přeneseny do tohoto worktree
a strict kontrola zopakována:

```bash
KGMAKER_REQUIRE_WORKERS=1 JAVA_HOME=/workspace/tools/jdk-21.0.6+7 \
PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/kgmaker-venv/bin:$PATH \
PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q
```

Výsledek: **246 PASS, 7 SKIP** v 84.81 s (Temurin 21.0.6, Kotlin 2.1.10,
TypeScript 5.7.3, Python 3.12.14). Oba skutečné compiler workery a všechny
compiler acceptance testy prošly. SKIP jsou skutečné Maven/Gradle build-runner
varianty bez executable na PATH a druhé JDK; nejde o nedostupné workery.
Předchozí failed strict pokus zůstává výše jako historická evidence přípravy.

Integrace po merge T005 / PR11 proti main
`c0a10261c2ff1f83291125ec838bbaeea8723532`: methodology/feature/scanner +
`tests/test_t005_add_view_model.py` **77 PASS** (1.12 s). Čistý model pohledu
nemění compiler/provenance cestu; předchozí skutečný strict běh zůstává výše.
Konflikty semantic historie opět zachovaly všechny unikátní identity obou větví
a novější upstream provenance stejné identity.
