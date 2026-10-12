# Implementační zadání pro agenta: graf volání, inspekce kódu a build JVM projektů

**Stav:** závazné implementační zadání pro agenta; popsané nové schopnosti je nutné implementovat a ověřit.  
**Datum:** 2026-10-12.  
**Ověřený baseline:** `0eaf0c44149971f4174faeed5475b1f5ae2140d6` na `p-rum/kgmaker`.  
**Rozsah:** Java/Kotlin JVM, Maven, Spring Boot, Hibernate/JPA; návaznost na multirepo, Flyway a feature/data analýzu. TypeScript zůstává ve stávajícím režimu; toto zadání nepožaduje jeho compiler-resolved graf.

## 1. Úkol agenta a požadovaný výsledek

Implementuj rozšíření kgmakeru z navigace pomocí zdrojových vzorů na inspekci opřenou o skutečné symboly, typy, těla metod a artefakty konkrétního buildu. Agent má umět doložit cestu od vstupního endpointu přes aplikační služby a persistence vrstvu až k databázovému objektu, ukázat nejistá místa a po změně ověřit kompilaci i vybrané testy.

Zachovej Python CLI a stávající offline scanner. Implementuj volitelný JVM worker, verzovaný build manifest, typovaný graf volání a adaptéry Spring/Hibernate. Interpretace požadavku zůstává na agentovi. Rozlišení symbolů, build výsledky a platnost důkazů musí určovat nástroje.

„Skutečný graf“ neznamená univerzálně přesný seznam všech volání za běhu. Přímé volání lze staticky rozlišit; u polymorfismu často vzniká množina možných cílů. Reflexe, runtime proxy a dynamická konfigurace mohou zůstat nerozlišené. Pozorovaný běh potvrzuje pouze konkrétní zachycená volání. Tyto kategorie nesmějí splynout.

Tvým výstupem musí být funkční implementace, automatizované testy, aktualizovaná uživatelská a architektonická dokumentace a dokument změn pro každý implementační PR podle kapitoly 14. Samotná analýza, návrh, prompt pro jiného agenta, prázdné adaptéry ani CLI vracející předpřipravená data nejsou splněním zadání.

Implementuj M0–M5 jako povinný základ. M0 je krátké ověření technologie zakončené rozhodnutím a pokračováním implementace, nikoli konečný výstup. M6 je navazující rozšíření: neblokuje dokončení základu, ale vždy ho vykazuj odděleně jako hotové, částečné nebo neimplementované. Neoznačuj základ za úplný runtime graf.

Kapitoly 3–10 jsou implementační požadavky. Konkrétní rozdělení souborů můžeš přizpůsobit aktuální architektuře; požadované chování, důkazní kontrakt a kompatibilitu zachovej. Technologickou odchylku dolož výsledkem spike a popiš v dokumentu změn.

## 2. Ověřený současný stav

Tabulka zachycuje stav ověřený na uvedeném baseline; relativní odkazy slouží k navigaci a odkazy na baseline pod tabulkou k historickému ověření. Před implementací ověř aktuální větev, kód a testy. Již dokončené části znovu neimplementuj.

| Oblast | Doložené chování | Chybějící schopnost |
|---|---|---|
| [scanner.py](../src/kgmaker/scanner.py) — `_extract_symbols`, `CALL_TOKEN`, `scan_repository` | Regulární výrazy; `calls` z file uzlu na jedinou stejně pojmenovanou deklaraci v jiném souboru; confidence INFERRED | Caller metoda, typ receiveru, overload resolution, lokální volání a přesné call sites |
| [model.py](../src/kgmaker/model.py) | Schema v1; Node a Edge, textové evidence, line, confidence | Build ID, plná identita JVM metody, varianty, strukturované resolution a provenance |
| [cli.py](../src/kgmaker/cli.py) — `build_parser` | `build` a `update` jsou full-scan aliasy pro tvorbu grafu | Kompilace projektu a sběr diagnostiky |
| [domain.py](../src/kgmaker/domain.py) | Základní JPA Entity/Table/Column, Spring Data generika, Spring HTTP anotace, Kafka a klientské vzory | Skutečný model Spring kontextu a Hibernate metamodel; rozlišení dotazů |
| [scanner.py](../src/kgmaker/scanner.py) — `EXTENSIONS`, `SKIP_DIRS` | Obecný scanner nezahrnuje XML; vynechává target/build | Obecná analýza POM a řízený import čerstvého bytecode |
| [flyway-workspace-proofs.md](flyway-workspace-proofs.md) | Samostatné čtení Flyway Maven XML, offline replay migrací | Maven build model; Flyway XML čtení není obecná podpora Mavenu |
| [workspace.py](../src/kgmaker/workspace.py) | Repo-qualified IDs, obsahové baseline, manifest a cache | Build varianty, reactor moduly a vazba workspace artefaktů na classpath |
| [availability.py](../src/kgmaker/availability.py), [analysis_validation.py](../src/kgmaker/analysis_validation.py) | Přísné validování omezených pozitivních důkazů a computed paths | Import build/runtime evidence se zachováním dosavadních omezení |

[Zdrojový strom baseline](https://github.com/p-rum/kgmaker/tree/0eaf0c44149971f4174faeed5475b1f5ae2140d6/src/kgmaker) a [architektura baseline](https://github.com/p-rum/kgmaker/blob/0eaf0c44149971f4174faeed5475b1f5ae2140d6/docs/architecture.md).

Stávající [zadání](implementation-feature-analysis.md) výslovně drží analytické příkazy offline a zakazuje automatické build/test operace. Nový režim musí být výslovnou, oddělenou schopností; obyčejné scan, feature prepare, data-check ani session hook build nespustí. Při implementaci se doplní tento režim do původního zadání a dokumentace, aniž by se změnil význam současných příkazů.

## 3. Režimy a důkazní kontrakt

| Režim | Vstup a činnost | Co výsledek dokládá |
|---|---|---|
| SOURCE_ONLY | Zdrojové soubory a lokální konfigurace; bez spuštění projektu | Deklarace, syntaktické nálezy a výslovné kandidáty |
| BUILD_IMPORT | Import existujícího manifestu, classpath a artefaktů; kontrola hashů | Fakta o dodaném buildu; důvěryhodnost původu evidovat zvlášť |
| BUILD_EXECUTE | Izolovaný build přes předem sestavený plán | Výsledek konkrétní kompilace/testu a jeho rozsah |
| RUNTIME_IMPORT | Import instrumentovaného běhu či exportu kontextu | Pozorování pro konkrétní artefakty, konfiguraci a scénář |

Model nesmí používat jedinou stupnici confidence jako náhradu za povahu důkazu:

- `SYNTAX_CANDIDATE`: shoda zdrojového vzoru.
- `SYMBOL_RESOLVED`: identifikovaný deklarovaný cíl s typy/signaturou.
- `DISPATCH_CANDIDATE`: možná implementace polymorfního volání.
- `FRAMEWORK_DERIVED`: vztah odvozený z podporovaného pravidla a konfigurace.
- `RUNTIME_OBSERVED`: zachycená hrana konkrétního běhu.
- `UNRESOLVED`: důvod a hranice analýzy.

K tomu nezávisle: `freshness`, `coverage`, `origin_trust` a build/config scope. Hash zajišťuje integritu a vazbu na obsah, nikoli pravdivost či autenticitu dodaného manifestu.

BUILD_PASS neznamená TEST_PASS, dostupná data, funkční aplikaci ani shodu nasazené databáze. Nepřítomnost runtime hrany neznamená nedosažitelnost. Ani konzervativní statická cesta není důkaz, že existuje vstup, který ji vykoná.

## 4. Pipeline a členění implementace

1. Načíst workspace a pořídit koherentní snapshot zdrojů, konfigurace a lokálních změn.
2. Detekovat Maven rooty, moduly a deklarované varianty.
3. Připravit build plán nebo importovat existující výsledky.
4. Získat skutečné compiler vstupy, výstupy a classpath jednotlivých modulů.
5. V JVM workeru rozlišit symboly, přečíst bytecode, vybudovat call sites a dispatch kandidáty.
6. Aplikovat samostatná Spring a ORM pravidla.
7. Zvalidovat provenance, konzistenci a pokrytí; atomicky uložit výsledek.
8. Zpřístupnit graf query/impact/feature analýze s vysvětlením důkazů a mezer.

Požadované odpovědnosti komponent; názvy nových modulů přizpůsob stávající struktuře bez ztráty odpovědností:

| Komponenta | Odpovědnost |
|---|---|
| `build_model.py` | Schémata BuildPlan/BuildResult/BuildManifest, fingerprinty |
| `build_maven.py` | Detekce POM, reactor, import/export Maven modelu |
| `build_runner.py` | Izolace, proces, timeout, zrušení, logy a stav modulů |
| `inspection.py` | Orchestrace a ověření výsledků workeru |
| `callgraph.py` | Typované dotazy, dispatch, dopady a coverage |
| `jvm-worker/` | Java/Kotlin/bytecode adaptéry a framework analyzéry |
| `runtime_evidence.py` | Import pozorování s identitou artefaktů |
| `tests/fixtures/jvm-inspection/` | Skutečně sestavitelné projekty pro akceptaci |

Worker běží jako samostatný proces přes verzované JSON soubory nebo JSONL. Není potřeba MCP ani API klíč. Python instalace zůstane použitelná bez JDK; při chybějícím workeru skončí pouze pokročilý režim s přesnou diagnostikou. JDK workeru a JDK cílového buildu jsou oddělené položky manifestu.

## 5. Maven: od POM k reprodukovatelnému build kontextu

### 5.1 Detekce a model

Samostatný XML parser bez externích entit detekuje root/child POM, parent, modules, GAV, packaging, závislosti a pluginy. Samotné čtení XML se označí jako deklarovaný, ne effective model.

Pro úplný kontext získat Maven effective POM s aktivními profily [S1], dependency resolution a skutečné source/output roots. Evidovat parent/BOM původ, dependencyManagement, exclusions, scopes, classifiers, optional dependencies, plugin executions, resources, generated sources, compiler release/target, encoding, annotation processors, Kotlin plugin a toolchain.

`dependency:build-classpath` [S2] je pomocný podklad: neobsahuje automaticky celý aplikační model včetně správných reactor outputů. Worker dostane per-module classpath v původním pořadí, odděleně main/test, modulové výstupy a případný JPMS module path. Duplicity tříd se vyhodnotí podle skutečného pořadí; nesmějí se tiše sloučit.

Preferovat doložený Maven Wrapper projektu, na Windows `mvnw.cmd`; jinak explicitně zvolenou instalaci. Zaznamenat verzi wrapperu/Mavenu, JDK vendor/verzi, compiler/plugin verze a checksumy artefaktů. Nevnucovat aplikacím „nejnovější“ závislosti. Podporované kombinace Maven/JDK/Kotlin/Spring/Hibernate budou testovaná matice; neověřená kombinace má explicitní stav UNSUPPORTED nebo PARTIAL.

### 5.2 Build plán a provedení

Plán obsahuje root POM, moduly, profily, properties, prostředí, fázi, příkazy jako argv, důvod každého kroku, očekávané výstupy a povolené síťové/externí prostředky.

- `compile`: hlavní kód a generování navázané na předchozí fáze.
- `test-compile`: kompilace testů, nikoli důkaz jejich spuštění.
- `test`: sběr skutečných výsledků test runneru.
- `verify`: volitelná širší verifikace podle plugin bindings; může zahrnovat integrační testy [S3].

Žádné automatické install/deploy ani spring-boot:run. Fáze může spustit libovolný připojený plugin, stejně jako Maven extensions a annotation processors. Skip flags nejsou bezpečnostní izolace. I získání effective modelu je při spuštění Mavenu vykonávání projektové konfigurace.

Build provádět v oddělené kopii obsahového snapshotu, se samostatným Maven local repository a dočasným target. Původní workspace zůstává read-only. Kopie sama není sandbox: runner musí umět omezit proces, filesystem a síť; bez takového prostředí nabídne BUILD_IMPORT nebo explicitní lokální execution policy. Zaznamenat povolené registry/proxy a soukromé dependency zdroje, ale ne hesla. Chybějící knihovna vede k DEPENDENCY_UNAVAILABLE, ne k odstranění závislosti z modelu.

BuildResult eviduje exit code, stav každého modulu/fáze, začátek/konec, normalizovanou diagnostiku, raw log digest, seznam čerstvých výstupů a test reporty. Stav FAILED/TIMED_OUT/CANCELLED/PARTIAL se nesmí změnit na úspěch jen proto, že v target zůstal starý JAR. Nula testů nebo skipped tests není PASS požadovaného scénáře.

### 5.3 Build manifest a cache

Povinné údaje:

- repo ID, commit a content manifest včetně dirty/untracked analyzovaných vstupů;
- reactor/module ID, GAV a source set;
- POM/parent/config/profiles/toolchain fingerprint;
- seřazené classpath entries s checksumem a původem;
- compiler inputs/options, generated roots a digest výstupů;
- build execution ID, result a trust původu;
- diagnostika, omezení a verze extraktoru.

Cache key zahrnuje uvedené vstupy, framework konfiguraci, algoritmus a worker verzi. Stejné GAV nestačí zejména pro SNAPSHOT. Změna API/hierarchie invaliduje závislé moduly, změna bean konfigurace framework hrany a změna staré migrace ORM/schema porovnání. První implementace smí přepočítat celý dotčený modul; nesmí předstírat jemnou inkrementalitu.

## 6. Graf volání a skutečná inspekce těl metod

### 6.1 Identita a fakta

Identita metody: repo/module/source-set + owner binary name + method name + JVM descriptor. Zdrojové symboly mají také package, lexical owner, generické typy, Kotlin receiver a mapování na JVM symboly. Řádek je lokalizace, nikoli dlouhodobá identita. Pro lokální/anonymní konstrukce je stabilita pouze v rámci obsahového snapshotu.

CallSite eviduje caller, source range, případně bytecode offset, declared target, invocation kind, receiver type, dispatch candidates a důvod resolution. Hrany:

| Hrana | Význam |
|---|---|
| `declares_call` | Metoda obsahuje konkrétní call site |
| `resolves_to` | Typově rozlišený deklarovaný cíl |
| `may_dispatch_to` | Možná runtime implementace |
| `observed_dispatch_to` | Pozorovaná implementace v daném běhu |
| `overrides`, `implements` | Typová hierarchie |
| `reads_field`, `writes_field` | Rozlišený přístup k poli |
| `argument_to_parameter`, `returns_to` | Podporované value-flow vztahy |

Zachovat přímou rekurzi, overloads, constructors, static/private/super calls, interface/default methods, lambdy a method references. Invokedynamic má vlastní resolver; neznámý bootstrap zůstává hranicí.

### 6.2 Volba technologie

| Varianta | Přínos | Rozhodnutí |
|---|---|---|
| Další regex/tree-sitter vrstva | Syntaktická navigace bez buildu | Fallback; nenahradí typovou resolution |
| Java compiler API | Parse/analyze skutečných Java symbolů [S4] | Preferovaný Java source adaptér |
| Kotlin compiler/Analysis API | Kotlin overloads, extensions, typy a zdrojové vazby | Samostatný feasibility spike, připnout ověřenou kompatibilní verzi |
| JVM bytecode engine | Společný pohled na zkompilovanou Javu a Kotlin | Povinná vrstva; pilot SootUp, alternativně vlastní reader + resolver |
| SootUp CHA/RTA | Hierarchie a množiny dispatch cílů [S5] | CHA jako počáteční konzervativní režim; RTA až s doloženými roots/allocation modely |
| Runtime instrumentace | Pozorovaná volání a framework dispatch | Doplňková evidence, nikoli náhrada statické analýzy |

Rozhodnutí o konkrétní knihovně uzavře spike na fixtures, včetně licence, distribuce, JDK/bytecode kompatibility a paměti. Nepředpokládat, že samotná instalace SootUp vyřeší Spring nebo Kotlin source mapping.

U Kotlinu otestovat suspend/coroutines, extension functions, default arguments, inline functions, generované bridges, data classes a Java interoperabilitu. Část zdrojových volání po inliningu nemá vlastní bytecode invoke; zdrojový a bytecode graf proto zůstávají rozlišeny. Debug info, SMAP a Kotlin metadata použít jen pokud existují; chybějící lokalizaci nevymýšlet.

### 6.3 Inspekce nad rámec seznamu volání

Přidat body/AST/IR reprezentaci, základní control-flow a lokální def-use. Interprocedurální propagaci budovat přes explicitní argument/parameter/return vazby. Větvení a výjimky mají vlastní podmínky, které analýza nemusí umět rozhodnout.

První pravidla: rozlišené callers/callees, nepokryté hranice, přímé čtení/zápis dat, compiler diagnostics, transakční self-invocation kandidát a ORM/schema nesoulad. N+1, lazy přístup mimo transakci či nedosažitelnost jsou při neúplném kontextu upozornění s předpoklady; nikoli kategoricky prokázané chyby. Arbitrární business správnost a úplná path feasibility nejsou cílem.

## 7. Spring Boot

Podpora musí pracovat s konkrétní framework verzí a variantou aplikace:

1. Rozlišit anotace podle plně kvalifikovaných symbolů včetně meta-anotací; samotný název Service není důkaz Spring beanu.
2. Modelovat component scan, imports, Configuration/Bean, constructor/field/setter injection, Primary, Qualifier a kolekce/provider injection.
3. Vyhodnotit podporované Profile/Conditional podmínky proti doloženým properties a classpath. Neznámá externí property/custom condition zůstává UNKNOWN.
4. Spojit injection point s bean definition a cílovou metodou. Při více kandidátech uvést všechny a příčinu, nevybrat podle názvu.
5. Rozlišit přímé volání objektu a průchod proxy. Transakce, Async, Cacheable a security interceptory jsou framework vztahy; anotace sama nepotvrzuje vykonání advice. Spring proxy self-invocation má jinou sémantiku než průchod proxy [S6].
6. Doplnit HTTP handler method, Kafka listener, scheduled/event listener a command/application runner jako typované entrypointy. Async/event vztah není běžné synchronní volání.
7. Verze/config specifická auto-konfigurace je samostatná vrstva; nerozpoznaný registrar, BeanPostProcessor nebo factory vytváří mezeru pokrytí.

Volitelně importovat sanitizovaný export beans/conditions/mappings z konkrétního běhu [S7]. Export není method trace a neprokazuje vykonání volání. kgmaker sám nezpřístupňuje Actuator ani nespouští aplikaci. Import musí obsahovat artefakt/config fingerprint; startup může provést migrace, schedulery a externí komunikaci, takže případný runtime capture má oddělený plán.

## 8. Hibernate, JPA a Spring Data

První scope: Java i Kotlin, javax/jakarta identita podle skutečných dependencies, explicitní Entity/Table/Column, field/property access, Id/EmbeddedId, Embedded/Embeddable a AttributeOverride; následně vztahy, inheritance a XML mapping.

Požadované modely:

- entity → persistent attribute → logical/physical table/column;
- association → join column/join table a owning/inverse side;
- repository method → entity/projection/query;
- query → čtené/zapisované entity/attributes a doložené DB objekty;
- persistence unit/datasource → zvolený Flyway stream, dialect a target.

Hibernate naming má logickou a fyzickou vrstvu [S8]. Neodvozovat univerzálně camelCase → snake_case. U custom naming strategy/converteru použít ověřený adaptér či import metadat; neznámé chování označit jako unresolved. XML overrides a access strategie musí mít doloženou prioritu.

Spring Data derived methods parsovat nad skutečným entity modelem; podporovat @Query JPQL/HQL, named queries a explicitně odlišené native SQL [S9]. Parametry a projection mapovat podle typů. Dynamicky skládáné Criteria/Specifications/QueryDSL a custom repository fragmenty mohou být PARTIAL. Runtime-generated repository implementace dostane framework edge, nikoli fiktivní zdrojové tělo metody.

Porovnání s Flyway kontroluje existenci vybraných tabulek/sloupců, podporovanou typovou kompatibilitu, nullability, precision/scale, keys a relations. Db identita musí zahrnout datasource/persistence unit, schema a stream. Typové konverze závisejí na dialectu a converteru.

Neprovádět DDL ani automatický Hibernate bootstrap v offline režimu. Případný metadata exporter běží odděleně s vlastní execution policy a bez schema update. `save()` neznamená okamžitý INSERT ani potvrzený commit: ORM side effects se vykreslí jako persistence intent. Migrační model a ORM mapping nadále nedokazují nasazené či naplněné schéma.

## 9. Integrace s existujícím kgmakerem

### Schéma a kompatibilita

Implementuj graph schema v2 se strukturovanými evidence/build references, call sites, symbol IDs a coverage. Implementuj převod dat v1 do v2; staré calls se převedou na SYNTAX_CANDIDATE bez zvýšení důkazní síly. Současný reader v1 jiné verze odmítá, takže zavedení vyžaduje souběžnou úpravu serializerů, cache, semantic packetů, query, renderů a validátorů.

Při migraci zachovat vazbu old ID → new ID pouze při jednoznačném matchi. Nejednoznačné semantic reference zneplatnit a připravit nový packet; neaplikovat starý patch na nové IDs.

### Multirepo

Repo-qualified identita zůstává. Maven reactor není totéž co workspace: jeden repo obsahuje více modulů a více repo může dodávat knihovny. Cross-repo JVM hrana vznikne jen při doloženém mapování classpath artefaktu na konkrétní obsah zdrojového repo. Stejné GAV ani název třídy nestačí.

HTTP/Kafka spojení mezi službami zůstává kontraktní/integrací odvozená hrana, nikoli lokální JVM call. Verze analyzovaných služeb musí mít explicitní release mapping; společný workspace neprokazuje společné nasazení.

### Feature, availability a agent

Feature packet dostane inspection/build baseline a seznam relevantních evidence IDs. Validátor přijme pouze deterministicky vypočtené cesty a ověřené build/run references. Agent nesmí vytvořit SYMBOL_RESOLVED nebo TEST_PASS tvrzení vlastní confidence hodnotou.

Call reachability a data availability jsou dva různé důkazy. Do `availability.py` nevkládat pravidlo „existuje call path ⇒ AVAILABLE“. Runtime pozorování musí splnit samostatný důkazní kontrakt pro konkrétní hodnotu, cestu a scope.

Implementační agent: analyzuje baseline → ukáže relevantní call/data paths → upraví kód → připraví/spustí povolený build plán → importuje výsledky → přepočítá dotčený graf → oznámí výsledek i mezery. Běžný analytický agent pouze čte/importuje.

## 10. Implementuj CLI a výstupy

Implementuj následující příkazy včetně nápovědy, validace vstupů, strojově čitelného výstupu a integračních testů. V uvedeném baseline neexistují. `runtime import` patří do M6:

```bash
kgmaker project inspect --workspace kgmaker.workspace.json --repo backend
kgmaker project build-plan --workspace kgmaker.workspace.json --repo backend --phase test-compile
kgmaker project build-run --plan build-plan.json
kgmaker project build-import --manifest build-manifest.json
kgmaker inspect code --workspace kgmaker.workspace.json --repo backend --build-id <id>
kgmaker callgraph callers --symbol <id> --resolution resolved
kgmaker callgraph callees --symbol <id> --include-dispatch-candidates
kgmaker callgraph path --from <symbol-id> --to <symbol-id>
kgmaker runtime import --manifest runtime-manifest.json
```

`kgmaker build` zachovat jako tvorbu grafu, aby upgrade náhle nespouštěl projekt. U execution se používá schválená policy host prostředí a obsahově svázaný plán; nedoplňovat potvrzování pro každý již povolený krok.

JSON je primární kontrakt; Markdown vysvětluje cestu s file/line, declared target, candidates, build/profile a nejslabší hranicí. Coverage uvádí počty analyzovaných/neanalyzovaných modulů, metod, call sites, nerozlišených symbolů, unsupported constructs a neúplných dependencies. Procento resolution musí mít jmenovatel a nepokrývá automaticky nenalezené konstrukce. Truncation/depth limit je vždy viditelný.

## 11. Implementační kroky a předávací podmínky

| Milník | Dodávka | Podmínka dokončení |
|---|---|---|
| M0 | Feasibility spike Java/Kotlin bytecode + compiler source resolution | Sestavitelná mixed fixture, přesné overloads, zdrojové mapování a popsané limity; uzavřená volba worker knihoven |
| M1 | Manifesty, Maven discovery/import/runner | Fresh/stale rozlišení, reactor a failed-module diagnostika; offline workflow beze změny |
| M2 | Schema v2, method/call-site graf, direct calls + CHA | Žádné name-only calls označené jako resolved; validovaná migrace v1 |
| M3 | Spring bean/entrypoint/proxy adaptér | Profile/Qualifier/Primary fixtures, ambiguous i unresolved scénáře |
| M4 | Hibernate + Spring Data + Flyway vazby | Entity/query/DB cesty s konkrétním stream scope a negativními fixtures |
| M5 | Query/impact/feature integrace a inspection rules | Agent doloží cestu i mezery; build/test stav oddělen od availability |
| M6 | Runtime import a rozšíření RTA/value flow | Ověřený scope pozorování, invalidace a explicitní async/reflective hranice |

Závislosti: M0 → M1/M2 → M3/M4 → M5; M6 navazuje na stabilní evidence kontrakt. M1 a M2 lze vyvíjet souběžně až po dohodě manifestu. Povinný rozsah tohoto zadání je M0–M5 pro doloženou testovanou matici. M6 je oddělený navazující rozsah; bez něj se produkt nesmí označovat za úplný runtime graf.

V M0 ověř zejména Kotlin source/bytecode mapping, generovaný kód a Spring dynamiku na reprezentativní fixture. Výsledek promítni do implementace a matice podpory. Samotné rozšíření regexů není alternativní splnění tohoto zadání.

## 12. Akceptační a regresní scénáře

| ID | Scénář | Očekávaný výsledek |
|---|---|---|
| CG-01 | Stejný název metody ve dvou třídách, overloads a lokální volání | Správný owner/descriptor/caller; žádná shoda jen podle názvu |
| CG-02 | Interface má dvě implementace | Declared target + oba relevantní CHA kandidáti; žádné tvrzení runtime výběru |
| CG-03 | Rekurze, constructor, lambda, method reference | Call sites zachované; cyklus nezacyklí traversal |
| CG-04 | Kotlin extension/default/suspend/inline + Java caller | Rozlišení nebo přesný unsupported důvod, žádná vymyšlená source line |
| CG-05 | Reflexe/dynamic classloading | Viditelná unresolved hranice; coverage není COMPLETE |
| MV-01 | Parent/BOM/profil mění dependency a generovaný kód | Odlišný manifest a správná per-module classpath |
| MV-02 | Reactor používá sourozenecký modul, v local repo je starší JAR | Použit správný výstup, nikoli starý artefakt podle GAV |
| MV-03 | Build selže a existuje starý target | FAILED/PARTIAL; starý bytecode není čerstvý důkaz |
| MV-04 | test-compile / skipped / nula testů / failing test | Čtyři odlišné výsledky; žádný falešný TEST_PASS |
| MV-05 | Maven/JDK chybí, offline cache není úplná | Použitelný SOURCE_ONLY, explicitní mezera |
| SP-01 | Dva beany, Qualifier/Primary, dva profily | Variant-specific resolution; ambiguity zůstává při neúplných properties |
| SP-02 | Proxy volání versus this.transactionalMethod() | Rozlišený průchod advice, včetně konfigurace weaving režimu |
| SP-03 | Custom registrar/factory a async listener | Framework boundary; async není synchronní call |
| HB-01 | Java/Kotlin explicitní mapping, embedded ID, property access | Správné persistent attributes a lokalizace |
| HB-02 | Custom naming, více datasource a stejná table name | Žádné tiché sloučení a žádný univerzální snake_case předpoklad |
| HB-03 | Derived query, JPQL projection a native SQL | Oddělený query jazyk, entity/column resolution nebo explicitní PARTIAL |
| HB-04 | Rename/drop ve Flyway a nullable/type mismatch | Diagnostika pro zvolený stream/target; žádný deployment claim |
| WS-01 | Změna jen v závislém repo nebo classpath JAR | Invalidace affected grafu i feature packetu |
| EV-01 | Ručně pozměněný manifest, stale trace či vymyšlená hrana | Odmítnutí důkazu; origin trust není nahrazen hashem |
| EV-02 | Build PASS a existence call path, ale žádná datová observation | Availability zůstane UNKNOWN |
| BC-01 | Starý scan/build/hook a graph v1 migrace | Žádné spuštění projektu; staré heuristiky nepovýšené |
| EX-01 | Timeout/cancel a plugin zapisující mimo kopii | Proces ukončen; izolace/policy ověřena, artefakty označeny nekompletní |

Testovat na skutečných malých Maven projektech, nejen na textových úryvcích: Java Spring JPA, mixed Kotlin/Java, multi-module a multi-repo fixture. Golden expectations pro každou call site a resolution důvod; negativní testy mají stejnou prioritu jako pozitivní. CI oddělit na Python regresní suite, JVM worker testy a integrační build matrix s pinovanými dependencies. Měřit cold/warm čas, paměť a resolution coverage; limity určit z pilotních dat, nevydávat neověřené benchmarky.

## 13. Primární technické podklady

Zdroje ověřeny při přípravě analýzy. Vysvětlují schopnosti podkladových technologií, nikoli hotovou implementaci kgmakeru. Architektura, CLI, stavy a milníky tvoří implementační kontrakt tohoto zadání.

- [S1 — Maven effective POM](https://maven.apache.org/plugins/maven-help-plugin/effective-pom-mojo.html): effective model s aktivními profily a původem položek.
- [S2 — Maven dependency classpath](https://maven.apache.org/plugins/maven-dependency-plugin/build-classpath-mojo.html): export classpath závislostí.
- [S3 — Maven lifecycle](https://maven.apache.org/guides/introduction/introduction-to-the-lifecycle.html): fáze a připojené plugin goals.
- [S4 — JDK JavacTask](https://docs.oracle.com/en/java/javase/21/docs/api/jdk.compiler/com/sun/source/util/JavacTask.html): parse/analyze rozhraní.
- [S5 — SootUp call graphs](https://soot-oss.github.io/SootUp/latest/callgraphs/): CHA/RTA; konkrétní release a kompatibilitu musí ověřit spike.
- [S6 — Spring proxying](https://docs.spring.io/spring-framework/reference/core/aop/proxying.html): proxy mechanismy a self-invocation.
- [S7 — Spring Boot Actuator endpoints](https://docs.spring.io/spring-boot/reference/actuator/endpoints.html): export informací běžícího kontextu.
- [S8 — Hibernate ORM 6.6 user guide](https://docs.hibernate.org/orm/6.6/userguide/html_single/): mapování a naming; další framework verze ověřovat proti jejich dokumentaci.
- [S9 — Spring Data JPA query methods](https://docs.spring.io/spring-data/jpa/reference/jpa/query-methods.html): deklarované a odvozené repository queries.

V M0 ověř aktuální primární dokumentaci a kompatibilitu konkrétního Kotlin source adaptéru. Původní průzkum ji nepotvrdil. Připni ověřenou verzi, vytvoř integrační fixture a dolož skutečné výsledky; kompatibilitu nepředpokládej.


## 14. Povinný Markdown dokument změn pro každý PR

Pro každý PR vytvoř a commitni jeden dokument v `docs/changes/`. Dokument je povinnou součástí implementace, nikoli jen textem popisu PR. Adresář vytvoř, pokud dosud neexistuje.

### 14.1 Formát názvu

Použij přesně:

```text
{inkrementalneNarustajiciCislo}_zkracenyNazevPullRequestu.md
```

Příklady:

```text
docs/changes/1_addBuildIntrospection.md
docs/changes/2_addJvmCallGraph.md
docs/changes/3_addSpringHibernateInspection.md
```

Pravidla:

1. Číslování je společné pro celé repository v `docs/changes/`, nikoli zvlášť pro milník, agenta nebo větev. Není to číslo GitHub PR.
2. Pokud žádný očíslovaný dokument dosud neexistuje, začni číslem `1`. Jinak použij nejvyšší existující číselný prefix + 1. Porovnávej čísla numericky, ne lexikograficky.
3. Při výběru čísla zkontroluj aktuální cílovou větev i svou pracovní větev. Existující dokumenty nemaž, nepřepisuj ani nepřečíslovávej kvůli získání čísla. Mezery po historicky odstraněných dokumentech nevyplňuj.
4. Zkrácený název odvoď z účelu PR: stručný anglický lowerCamelCase, bez mezer, diakritiky a interpunkce. Prefix nemá úvodní nuly. Celý název musí odpovídat `^[1-9][0-9]*_[a-z][a-zA-Z0-9]*\.md$`.
5. Jeden PR má jeden dokument. Při dalších commitech do téhož PR aktualizuj tento dokument; nezvyšuj číslo pro každý commit. Nový PR dostane nové číslo.
6. Před dokončením PR znovu ověř cílovou větev. Pokud souběžný PR obsadil stejné číslo, přejmenuj pouze svůj dosud nesloučený dokument na aktuální maximum + 1 a oprav odkazy. Před sloučením nesmí dva různé dokumenty sdílet číselný prefix.
7. Pokud nelze aktuální cílovou větev ověřit, uveď to jako blokované ověření číslování; netvrď, že jedinečnost byla potvrzena.
8. Po sloučení název zachovej. PR description i závěrečná odpověď agenta musí obsahovat odkaz na dokument.

### 14.2 Povinný obsah

Vyplň dokument česky a konkrétně podle skutečného diffu. Uveď:

- název/účel PR, větev, baseline a URL/číslo PR, jakmile existuje;
- problém a výsledné chování;
- implementované změny a důležité dotčené soubory/moduly;
- změny CLI, konfigurace, schémat a datových kontraktů;
- kompatibilitu, migraci a případný postup návratu;
- skutečně provedené buildy/testy: přesný příkaz, prostředí/verze, výsledek a rozsah;
- nespuštěné nebo blokované kontroly s důvodem; oddělit je od PASS;
- vazbu na milníky M0–M6 a akceptační ID z kapitoly 12;
- omezení, nerozlišené případy a zbývající práci;
- ověřitelný příklad použití nové schopnosti.

Nepopisuj budoucí funkce jako implementované. Neuváděj obecné „testy prošly“, pokud neexistuje skutečný výsledek. Dokument nesmí obsahovat secrets, přístupové tokeny ani citlivé build logy. Seznam souborů není náhradou vysvětlení chování.

Použij například tuto strukturu; všechny položky vyplň, nebo výslovně označ jako nerelevantní:

```markdown
# Add build introspection

## Kontext PR
- PR:
- Větev:
- Výchozí commit:
- Milníky a akceptační ID:

## Problém a výsledné chování

## Implementované změny

## CLI, konfigurace a datové kontrakty

## Kompatibilita a migrace

## Ověření
| Příkaz / kontrola | Prostředí | Výsledek | Rozsah a omezení |
|---|---|---|---|

## Příklad použití

## Omezení a zbývající práce
```

Dokument má pokrývat i samotné zavedení pravidla, pokud je tento krok součástí implementačního PR. Nevytvářej prázdné dokumenty předem pro budoucí milníky.

## 15. Pracovní postup implementačního agenta

1. Přečti repository instructions, aktuální architekturu, toto zadání a relevantní zdroje/testy. Ověř baseline, workspace a Flyway scope. Respektuj požadovanou architektonickou rekognoskaci repository.
2. Rozděl M0–M5 na proveditelné kroky. Udržuj stav hotovo/rozpracováno/blokováno s vazbou na acceptance ID. M6 eviduj zvlášť.
3. Začni M0, proveď ověření zvolených knihoven, commitni fixture a zdokumentuj rozhodnutí. Poté pokračuj implementací; nezastav se u dalšího návrhu.
4. Implementuj vertikální řezy od reálných vstupů po CLI a validovaný výstup. Zachovej existující offline chování a důkazní kontrakty.
5. Pro každý krok doplň smysluplné unit/integration testy. JVM podporu ověř na sestavitelných projektech a skutečném bytecode. Mocks použij pro cílené chyby, nikoli jako jediný důkaz funkčnosti workeru.
6. Spusť relevantní regresní testy, build workeru a příslušnou integrační matici. Nedostupné prostředí popiš jako blokované ověření, ne jako úspěch.
7. Aktualizuj README, architekturu, CLI příklady, podporovanou matici a původní zadání v místech, kde je nutné vysvětlit nový explicitní execution režim. Generované grafy a semantic metadata obnov podle repository workflow pouze tam, kde se jich změna týká.
8. Vytvoř či aktualizuj dokument `docs/changes/<N>_<shortPrName>.md` podle kapitoly 14 a zkontroluj shodu s diffem.
9. Před předáním proveď kontrolu diffu, čistoty artefaktů, číslování dokumentu a acceptance checklistu. Odstraň dočasné soubory; záměrné fixtures zachovej.
10. Předlož PR s konkrétním shrnutím změn, skutečnými výsledky a odkazem na dokument změn. Neprováděj automatický merge. Pokud je dodávka rozdělena do více PR, každý obsahuje vlastní očíslovaný dokument a přehled zbývajících kroků.

Technologickou překážku nejprve zkus vyřešit podporovanou alternativou, která zachová kontrakt. Pokud požadavek zůstává blokovaný, uveď přesnou příčinu a dopad; nepřeznačuj ho jako hotový ani ho neodstraňuj ze zadání.

## 16. Definition of Done a závěrečné předání

Povinný základ M0–M5 je dokončen pouze tehdy, když:

- [ ] Maven kontext a build/import pipeline pracují s reálným projektem a čerstvými artefakty.
- [ ] Java i Kotlin mají doloženou podporu v testované matici; unsupported konstrukce jsou viditelné.
- [ ] Graf obsahuje caller metody, call sites, přesné symboly a oddělené dispatch kandidáty.
- [ ] Spring a Hibernate adaptéry poskytují skutečné framework/ORM vazby podle kapitol 7–8.
- [ ] Query, impact a feature workflow využívají nový graf a ověřují provenance.
- [ ] Build/test výsledky nezvyšují automaticky data availability.
- [ ] Migrace v1 a dosavadní offline příkazy jsou regresně ověřeny.
- [ ] Povinné scénáře kapitoly 12 mají testy a doložené výsledky; runtime-only část EV-01 se vykáže u M6.
- [ ] README, architektura, CLI help a příklady odpovídají implementaci.
- [ ] Každý implementační PR obsahuje vyplněný správně očíslovaný Markdown dokument změn a odkaz na něj.
- [ ] V PR nejsou vydávány stuby, simulované výstupy ani neprovedené kontroly za funkční implementaci.

Závěrečná odpověď musí obsahovat odkazy na PR a dokument změn, seznam dokončených milníků, stručné skutečné výsledky testů/buildu a zbývající omezení. Pokud část povinného rozsahu není hotová, označ výstup jako částečný a přesně vyjmenuj, co chybí.
