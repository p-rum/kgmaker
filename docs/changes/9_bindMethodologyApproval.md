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
