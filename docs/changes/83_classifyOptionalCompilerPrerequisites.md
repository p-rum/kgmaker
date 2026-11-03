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

## Doplnění po skutečném Python3.12 full běhu

První optional full skončil389PASS230SKIP1FAIL24.37s, se zachovanými vstupy.
Strict actual krok se proto nespustil. Další ORM test obcházel graph helper a
volal inspect_jvm přímo. Nyní všech osm takových volání používá společný
_inspect_worker; jediné raw volání má tentýž úzký TOOLCHAIN_UNAVAILABLE guard.
Chybové kódy produktu ani strict publication assertions se nemění. Regrese nyní
ověřuje i přímou worker entry cestu. Python3.12 cíleně31PASS/20 skutečných
prerequisite SKIP0.33s; tyto SKIP se nevydávají za compiler PASS. Nový complete
optional full a strict actual moduly zůstávají pending, starý log/XML zachován.

## Aktuální rodič před jediným opravným během

Po mergePR65 integrován main32a3bca; původní opravná fronta na5c4e byla
zrušena před startem, bez child procesu/pytest, s auditem. První skutečný
neúspěšný full389/230/1 zůstává zachován. Následující běh ověří aktuálního
rodiče. Všech15trackedJVM souborů bylo byte-exact porovnáno s vlastními
PR65workery;132JAR/license artefaktů ověřeno proti původnímu build receipt
a zkopírováno bez buildu. Python3.12 samostatná rozhodovací sada16PASS0.11s.
Nový optional full/strict actual nadále pending. Nejde o důkaz jejich úspěchu.

Následně integrován také main9442114 (T026); žádné další JVM producer změny.
Obě předchozí lokální fronty skončily před pytest, skutečný opravný běh dosud
neproběhl. Aktuální kompletní sada bude obsahovat i T025/T026 nové testy.

## Další skutečný prerequisite nález v instalovaném smoke testu

Current-parent3476optional full: **868PASS640SKIP1FAIL45.96s**, všech
599source+618tool/cache+132native inputs beze změny. Strict actual krok znovu
NOT_RUN. InstalledWorkerTests kontroloval pouze java aJAR, zatímco produkt
správně odmítl runtime-onlyJRE bezjavac. Nejde o selhání podpory JDK21.

Tři host prerequisite guards (Java/Kotlin/K2 instalovaný smoke) nyní reuse
stávající inspection.command bez spuštění procesu. Pouze host
TOOLCHAIN_UNAVAILABLE vede optionalSKIP/requiredFAIL (workers neboK2flag).
Chyby z již instalovaného balíčku se nadále nechytají a zůstávají FAIL; licence,
obsah distribuce, skutečný compiler a store assertions zůstávají stejné.
Žádná produktová či workflow změna. Pure RED9FAIL0.29s; po opravě
celá rozhodovací matice **25PASS0.28s**. Nový opravený optional full a strict
actualCoro/ORM/packaging jsou pending, oba starší FAIL logy/XML zachovány.
