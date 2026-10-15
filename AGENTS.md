# Pravidla projektu KGMAKER pro agenty

## Autorita a rozsah

Před prací čti tento soubor, `.github/copilot-instructions.md`, `docs/tasks/README.md`
a relevantní zadání. Kód a testy dokládají současné chování; zadání stanovuje cílové
chování. Zelené CI malé fixture není důkaz podpory libovolného produkčního projektu.
Aktuální stav a mezery udržuj v `docs/production-analysis-progress.md`.
Před významnou implementací proveď architektonickou rekognoskaci dle instrukcí
`kgmaker-architect`; při nedostupné delegaci proveď stejnou kontrolu přímo.

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
- Dokud není T003-S02 implementováno, scan/hook přepisují compiler index; nevydávej jejich výsledek za zachovaný compiler kontext. Při inspekci nejprve ověř existující index a zdroje, neobnovuj jej automaticky jen kvůli čtení compiler dat.
- Každá změna veřejného chování současně upraví README, příslušnou capability dokumentaci, CLI příklady a stavovou matici. Specifikace musí být označena jako cíl, nikoli hotová funkce.
- Instrukce dodávané `kgmaker init` musí zůstat konzistentní s jejich Python templates. Zachovej ochranu upravených uživatelských souborů; nepoužívej automaticky `--force`.
- Ověř relevantní existující testy, nulovou mutaci při chybě a čistotu diffu. Worker testy hlásí chybějící toolchain jako SKIP/blocked, ne PASS. Dokumentační změna nepotřebuje nové testy kopírující text pravidel.
- Generované grafy obnov příkazem, neupravuj je ručně. Sémantický patch vytvářej pouze s doloženými vazbami pro aktuální packet; pokud takové změny nejsou, nic nevymýšlej.
- Předej reviewovatelný PR s odkazem na zadání a dokument změn. Bez explicitního pokynu nemerguj PR.
