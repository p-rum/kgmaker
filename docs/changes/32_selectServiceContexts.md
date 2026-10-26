# T006: výběr kontextů pro více služeb

Vyšší pohled potřebuje zvolit uložený compiler kontext pro každou explicitně
zadanou službu, repozitář a modul. Bez toho může smíchat varianty nebo chybně
odvodit, že shodný profil znamená stejné nasazení.

`kgmaker.views.select_service_contexts` nyní vrací deterministickou projekci
service/repo/module → context ID a content fingerprint. Při více profilech
vyžaduje výslovné `context_id`. Stale kontext odmítne s diagnostikou a příkazem
pro obnovu; volitelně ověří zdrojové a classpath hashe přes existující provider.
SOURCE_ONLY vyžaduje explicitní pokrytí repozitáře a zůstává PARTIAL; module-level
coverage zůstává UNKNOWN. Workspace
release mapping se přijímá pouze jako CONTENT_VERIFIED vztah artefaktu k
classpath; deployment a environment compatibility zůstávají UNKNOWN. Přidala se
jen knihovní projekce a příklady. CLI, discovery, renderery, nový store a
deployment inference zůstávají mimo tento task. Graph schema v1/v2/v3 a jeho
serializace se nemění; migrace není potřeba.

Review opravila čtyři mezery před vydáním: context bez `repo_id` se už neváže na
libovolný request; workspace `@repo/path` snapshoty se pro single-repo provider
ověří přes lokální relpaths na kopii contextu; producer BuildManifest selector
se páruje s vybraným contextem podle `repo_id + build_context_id`; release report
musí odpovídat deklarovaným repo ID/hash i graph `supplies_classpath` důkazu.
Duplicitní, stale nebo neshodný report zůstává unresolved. Classpath položka
může být v externím Maven/Gradle cache; report je i tak svázán s přesnou
vybranou položkou kontextu, hashem a pravidly pro běžný soubor bez symlinku.
Regrese ověřuje přijetí skutečné externí cesty i odmítnutí jiné cesty se stejnými
byty.

Vazby na zadání: T006-S01–S05, T006-AC01–AC06. Test mapování je v
[`docs/acceptance-inventory.md`](../acceptance-inventory.md).

## Kontroly

| Příkaz | Výsledek |
|---|---|
| `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_t006_select_service_contexts.py tests/test_cross_repo_artifacts.py tests/test_workspace.py tests/test_inspection_contract.py tests/test_binary_xls.py` | 59 passed in 4.38 s |
| `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q -rs` | 292 passed, 23 skipped in 21.75 s on merged main `3503309`; skips are Maven/JDK/exporter, Gradle 8.13, Kotlin cache, and JVM/TypeScript worker gates |
| `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_t006_select_service_contexts.py tests/test_cross_repo_artifacts.py tests/test_workspace.py tests/test_exporter_distribution.py -rs` | 50 passed, 2 skipped in 5.49 s after integrating exporter main `e656b8e`; the skips require live Maven/JDK and Gradle/JDK exporter builds |
| `git diff --check` | PASS |
| Worker/compiler a Mermaid render | NOT_RUN; tato změna neupravuje compiler ani renderer |

Omezení: content-verified release mapping potvrzuje jen shodu deklarovaných
build výstupů a consumer classpath. Nepotvrzuje společné deployment prostředí
ani runtime dostupnost. SOURCE_ONLY service musí dodat callerem ověřené source
coverage. Nebyl přidán CLI příkaz ani cross-service discovery. Actual compiler,
Gradle, Maven, worker install and Mermaid render gates were not run because this
change only projects saved contexts; full-suite skips are recorded above and are
not reported as passing worker evidence. The branch includes PR #8 via rebase onto
`3503309` and exporter main `e656b8e` were integrated with merge commits to
preserve T006 and upstream history. `semantic prepare` was rerun; it lists the
README extraction workflow at line 122, and `semantic update` retained the
concept and relationship evidence at that exact `semantic prepare` bullet.
Remote PR and CI are NOT_RUN here; the
parent agent coordinates external publication and review.
