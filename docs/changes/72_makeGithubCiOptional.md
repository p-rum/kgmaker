# Volitelné GitHub CI při splnění ostatních kontrol

T045 revize 2, R01–R04, S02–S03, AC01–AC04.

## Problém a změna

Fakturací zablokované GitHub Actions bránily merge i po úspěšných lokálních
kontrolách. Na výslovný pokyn uživatele je GH CI doplňující evidence.
AGENTS, profil code_review, README, registr a stavový přehled zachovávají všechny
ostatní povinné kontroly: aktuální base/head review, lokální acceptance a skutečný
toolchain, závislosti, ready stav, mergeability a kontrolu výsledku merge.
Konkrétní chyba správnosti z CI nadále vyžaduje opravu. Neprovedené CI není PASS.

## Kompatibilita a příklad

Workflows, Python API a worker protokoly se nemění. Například schválené ready PR
s úspěšnými lokálními acceptance může být sloučeno i při billing-only blokaci CI.
Chybějící lokální compiler test nebo platný REQUEST_CHANGES merge stále blokuje.
Serverová pravidla se neobcházejí; merge používá expected_head_sha.

## Ověření a hranice

Syntaxe všech 101 TOML profilů a jedinečnost názvů prošly. Lokální odkazy a
čistota diffu se kontrolují před publikací. Nezávislé obsahové review neobjevilo
blokující nález; opravilo se datum revize. Jde o dokumentační/profilovou změnu:
nový runtime/full pytest ani živý testovací merge se nespouští. GH CI není
vykázáno jako PASS. Skutečný merge a stav cílové větve se ověří až po schválení
finálního commitu. Dokončení T003/T004 z této změny nevyplývá.
