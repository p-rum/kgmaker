# Pravidla projektu KGMAKER pro agenty

## Autorita a rozsah

Před prací čti tento soubor, `.github/copilot-instructions.md`, `docs/tasks/README.md`
a relevantní zadání. Kód a testy dokládají současné chování; zadání stanovuje cílové
chování. Zelené CI malé fixture není důkaz podpory libovolného produkčního projektu.
Aktuální stav a mezery udržuj v `docs/production-analysis-progress.md`.
Před významnou implementací proveď rekognoskaci přímým čtením zdrojů, testů,
zadání a Git diffu. Používej běžné vyhledávání (`rg`) a projektový test runner.

## Vývoj bez vlastního KGMAKERu — pokyn uživatele 2026-11-24

Tento repozitář nepoužívá KGMAKER k vlastní analýze ani řízení vývoje.
Nespouštěj nad jeho checkoutem init, scan, status/check, query, semantic, memory,
feature/testgen/trace ani task/workflow/completion jako vývojový postup.
Nevytvářej vlastní graf, sémantické patche ani runtime workflow artefakty.
Vývoj nesmí záviset na funkčnosti nástroje, který právě opravujeme.

Toto pravidlo nahrazuje starší pokyny k self-use v zadáních, historických
change notes a již načtených profilech/skills. Úlohy, výsledky testů a review
dokládej přímo v zadání, change note a PR. Nativní hostitelské agenty a T045
review lze používat bez KGMAKER runtime. Při integraci starší větve neobnovuj
odstraněné hooky, aktivní skilly, cílové agenty ani verzovaný `.kgmaker/` obsah.

Vývoj a testování samotných funkcí KGMAKERu zůstává povolené: CLI a Python API
ověřuj na oddělených fixture/dočasných cílových projektech. Distribuované
templates v `src/kgmaker/` patří cílovým projektům; neinstaluj je do tohoto
checkoutu. Lokální historické `.kgmaker/` soubory nejsou vývojovým podkladem.
Podrobnosti: [T049-S08](docs/tasks/49_separateTargetAgents.md#t049-s08--vývoj-bez-vlastního-kgmakeru).

## Povinné názvy a číslování

1. Nová feature či rozšíření musí mít nové nebo explicitně rozšířené existující zadání v registru. Zachovej formát `docs/tasks/<N>_<shortName>.md`, např. `4_addSpringResolution.md`; N je kladné celé číslo bez počátečních nul, shortName je ASCII lowerCamelCase. Formát je závazný i pro budoucí features.
2. Novému zadání přiděl stabilní Task ID `T` + číslo s minimálně třemi číslicemi (soubor 4 → `T004`). Kroky mají ID `T004-S01`, požadavky `T004-R01`, acceptance `T004-AC01`. Používej explicitní závislosti, nezaváděj další souběžné řady A/M/P.
3. Číslo vybírej jako max + 1 po kontrole registru, cílové větve a otevřených PR. Před publikací zopakuj kontrolu. Nepřepisuj cizí zadání, nerecykluj čísla ani mezery. Již publikovaná ID neměň; další revize stejného zadání zůstává ve stejném souboru.
4. Zadání musí obsahovat Task ID, Revision, datum, stav SPECIFICATION, baseline, závislosti, rozsah/non-goals, konkrétní moduly/kontrakty, kroky, acceptance, způsob ověření, migrační dopady, DoD a zbývající omezení. Přidej řádek do `docs/tasks/README.md`.
5. Každý implementační nebo dokumentační PR obsahuje český `docs/changes/<N>_<shortPrName>.md`, např. `3_unifyImplementationTasks.md`. Tato řada je nezávislá na Task ID a PR number; formát N/lowerCamelCase se nemění při přidávání features. Číslo přiděl stejnou kontrolou max + 1 a kolizí.
6. Dokument změn obsahuje problém, skutečné změny, související Task/Step/Acceptance ID, kompatibilitu, přesné provedené kontroly a výsledky, neprovedené kontroly, příklad a zbývající práci. Název ani obsah nesmí naznačovat dokončení nedodaného rozsahu.
7. Zachovej historické dokumenty změn. Při přesunu zadání ponech kompatibilní rozcestník, aktualizuj aktivní odkazy a udržuj mapu starých milníků. `analysis_id` a packet/revision ve feature runtime nejsou Task ID: neměň je ani uživatelské názvy existujících funkcí kvůli této konvenci.

## Implementace, evidence a předání

- Reuse existující model/store/Flyway/workspace/availability; nevytvářej paralelní katalog.
- SOURCE_ONLY, compiler resolution, framework inference, build/test a runtime/data availability jsou odlišné důkazy. Nezvyšuj confidence nebo dostupnost pouhým přejmenováním.
- Scan, hook, feature a data-check nespouštějí projekt, package installation, migrace ani DB. Build musí být explicitní, content-bound workflow.
- Scan/hook zachovávají obsahově validované compiler kontexty a zastaralé označují STALE. Při inspekci nejprve ověř existující index a zdroje; neobnovuj jej automaticky jen kvůli čtení compiler dat. Podporovaný rozsah dolož aktuálními testy a stavovou maticí.
- Každá změna veřejného chování současně upraví README, příslušnou capability dokumentaci, CLI příklady a stavovou matici. Specifikace musí být označena jako cíl, nikoli hotová funkce.
- Instrukce dodávané `kgmaker init` musí zůstat konzistentní s jejich Python templates. Zachovej ochranu upravených uživatelských souborů; nepoužívej automaticky `--force`.
- Ověř relevantní existující testy, nulovou mutaci při chybě a čistotu diffu. Worker testy hlásí chybějící toolchain jako SKIP/blocked, ne PASS. Dokumentační změna nepotřebuje nové testy kopírující text pravidel.
- Testovací grafy a sémantické patche vytvářej pouze v oddělených fixture. Vlastní graf ani implementační paměť tohoto repozitáře se neudržuje.
- Předej reviewovatelný PR s odkazem na zadání a dokument změn. Implementační agent PR nemerguje. Uživatelský pokyn pro [T045](docs/tasks/45_addCodeReviewAgent.md) výslovně pověřuje projektového `code_review` agenta mergováním po jeho review APPROVE nad aktuálním HEAD a splnění kontrol; pro ostatní PR platí zákaz merge bez explicitního pokynu.

## Merge kontroly — uživatelská revize 2026-11-03

GitHub Actions/CI není povinnou podmínkou merge, pokud pro aktuální base/head
projdou všechny ostatní povinné kontroly: acceptance zadání, relevantní lokální
testy a skutečný vyžadovaný toolchain, čistota diffu, nezávislé review APPROVE,
závislosti, ready stav a mergeability. Nepřítomné, neprovedené nebo fakturací
zablokované GH CI se uvede pravdivě jako neověřené; nenahrazuje se tvrzením PASS.
Konkrétní chyba kódu či testů z CI se musí vyřešit jako každý blokující nález.
Chybějící jiný povinný důkaz nebo platný REQUEST_CHANGES nadále blokuje merge.

Tato výslovná změna uživatele má přednost před staršími formulacemi vyžadujícími
zelené GH CI v zadáních a profilech. Workflow a jejich testy zůstávají zachovány.
Respektuj skutečná serverová pravidla GitHubu; nepoužívej force/admin bypass.
Před merge znovu ověř obě SHA, použij expected_head_sha a potom ověř merged=true,
merge commit i cílovou větev. Viz T045 revize 2.

## Povinná dokumentace každého implementačního kroku

Každý implementační krok (včetně opravy, refaktoringu, integrace a dílčího work
package) musí mít před předáním vlastní dohledatelný záznam. Dokumentace je součást
kroku, ne následná volitelná práce. Krok není dokončený, pokud dokumentace popisuje
jiné chování než dodaný kód.

- V českém `docs/changes/<N>_<shortPrName>.md` uveď pro každý krok zvlášť
  Task/Step/AC ID, výchozí SHA, problém, skutečné změny a dotčené soubory,
  kompatibilitu, omezení, přesné kontroly a výsledky PASS/FAIL/SKIP/NOT_RUN,
  neprovedené kontroly a zbývající práci. Jeden PR může mít jeden change note,
  ale jednotlivé kroky v něm nesmějí být sloučeny do neurčitého shrnutí.
- Ve stejném PR aktualizuj relevantní README, capability/API/CLI dokumentaci,
  příklady, `docs/production-analysis-progress.md` a dotčené řádky
  `docs/acceptance-inventory.md`. Registr zadání aktualizuj při změně identity,
  revize, závislostí či odkazů; SPECIFICATION je stav dokumentu, ne stav dodání.
- U každé relevantní dokumentační plochy uveď odkaz na změnu, nebo konkrétní
  zdůvodnění „bez dopadu“. Pouhá existence change note nenahrazuje aktualizaci
  uživatelského návodu. Odstraň aktuálně nepravdivé věty „není implementováno“,
  „draft“ a „review pending“; historické výsledky zachovej s datem a SHA.
- Odděluj dodání (PLANNED/IN_PROGRESS/PR_OPEN/MERGED/DEFERRED/BLOCKED)
  od ověření (VERIFIED_IN_SCOPE/PARTIAL/NOT_RUN/FAIL). Merge ani starý PASS
  neprokazuje všechny acceptance nad aktuálním kódem.
- Při změně instalovaných instrukcí uprav také jejich Python template a
  odpovídající spravované kopie; zachovej ochranu uživatelských úprav při init.
- Před ready/review porovnej dokumentované příkazy, parametry, schémata,
  podporované varianty a limity se zdrojem a relevantními testy. Reviewer
  odmítne dokončení při chybějícím záznamu kroku nebo rozporu dokumentace s kódem.
  Výjimka „doplníme dokumentaci později“ není splněním Definition of Done.
