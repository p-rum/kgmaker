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

Vazby na zadání: T006-S01–S05, T006-AC01–AC06. Test mapování je v
[`docs/acceptance-inventory.md`](../acceptance-inventory.md).

## Kontroly

| Příkaz | Výsledek |
|---|---|
| `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_t006_select_service_contexts.py tests/test_t005_add_view_model.py tests/test_workspace.py` | 44 passed in 1.27 s on `aa9e64b` |
| `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q -rs` | 265 passed, 23 skipped in 18.76 s on `aa9e64b`; skips: Maven/JDK/exporter unavailable (16), Gradle 8.13 unavailable (3), JVM/TypeScript workers unavailable (2), Kotlin Gradle cache unavailable (1), plus one two-JDK Maven gate |
| `git diff --check` | PASS on final T006 diff |
| Worker/compiler a Mermaid render | NOT_RUN; tato změna neupravuje compiler ani renderer |

Omezení: content-verified release mapping potvrzuje jen shodu deklarovaných
build výstupů a consumer classpath. Nepotvrzuje společné deployment prostředí
ani runtime dostupnost. SOURCE_ONLY service musí dodat callerem ověřené source
coverage. Nebyl přidán CLI příkaz ani cross-service discovery. Actual compiler,
Gradle, Maven, worker install and Mermaid render gates were not run because this
change only projects saved contexts; full-suite skips are recorded above and are
not reported as passing worker evidence. The branch includes PR #8 via rebase onto
`aa9e64b`. Remote PR and CI are NOT_RUN here; the
parent agent coordinates external publication and review.
