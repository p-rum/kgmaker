# Oprava rozlišení volitelného compiler toolchainu v test fixtures

Souvisí s T003-S04-W03/T003-S06-W03 a jejich kompatibilitou v Python unittest jobu.
Nejde o rozšíření podpory produkčního parseru ani změnu GH CI merge pravidel.

## Problém a změna

Skutečný GitHub job125784544330 na c055f196 skončil20FAIL/50setupERROR:
ORM XML fixture nechytala TOOLCHAIN_UNAVAILABLE při starším JDK; coroutine
fixture považovala jinou PATH knihovnu coroutines za assertion chybu, přestože
optional job nepřipravuje pinned compiler. Compiler-workers job stejného commitu
prošel. Záznam jobu není nahrazen tvrzením o chybě billing; novější joby mají
oddělený billing blocker a žádné vykonané kroky.

Coroutine fixture nadále vyžaduje přesný původní SHA. Při nedostupné připnuté
knihovně optional job uvádí SKIP; KGMAKER_REQUIRE_WORKERS=1 uvádí FAIL před
spuštěním kompilátoru. ORM helper chytá pouze WorkerError.status
TOOLCHAIN_UNAVAILABLE se stejnou politikou. Ostatní WorkerError a runtime chyby
se propagují. ORM strict zůstává přepínač validace/publikace, nikoli náhrada
povinného toolchainu. Runtime, worker sources, workflows a veřejné CLI se nemění.

## Ověření, příklad a omezení

Nová rozhodovací matice používá chybějící i skutečné nesprávné testové bytes,
optional/required režim, oba ORM strict režimy a původní instance protocol/runtime
výjimek. RED6FAIL6PASS0.20s před opravou; GREEN12PASS0.21s po opravě. Matice není
vydávána za skutečný compiler běh. Příklad: optional unittest na stroji bez JDK21
zaznamená ORM SKIP; mandatory compiler job bez JDK21 selže, nikdy PASS.

Přesný Python3.12 optional full a skutečné strict K1/K2 coroutine/XML moduly
zůstávají pending. Podporovaný pinned compiler kontrakt se nemění, žádná migrace.
Nová runtime dostupnost, whole T003/T004 completion ani úspěch GH CI se netvrdí.
