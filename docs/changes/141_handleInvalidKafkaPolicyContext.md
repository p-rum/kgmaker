# Neplatný kontext Kafka retry/DLT politiky ve výběru grafu

[T003-S07-W05](../tasks/T003-S07-05-kafkaRetryDlt.md), T003-AC07 a
T003-S07-W05-AC01/AC03. Výchozí GitHub main
`1532f1725f2cbe0d76685c273adc32c2e0d239e0`, Git tree
`3f840cd64bcfad9ed049aa274f1b46f76b16ea3a`.

## T003-S07-W05 / AC01, AC03 — omezený výběr

[`views.project`](../../src/kgmaker/views.py) při explicitním výběru kontextu
testovala členství `node.metadata.context_id` v mapě i pro pole nebo objekt.
Takový vstup vyvolal TypeError před publikací process reportu. Výběr nyní
vyloučí uzel s nenulovou neřetězcovou identitou i v případě, že se jeho ID objevilo mezi
symboly vybraného kontextu. Původní úplný graf dál poskytuje podklady
validátoru Kafka policy. Caller zůstane v projekci a relevantní chybná
policy se vrátí v neprázdné hranici UNKNOWN bez evidence odkazů.
Vstupní graf se obsahově nemění. Datové formáty a CLI argumenty zůstávají
kompatibilní. Neznámý řetězec a null mají dosavadní pravidla výběru.

Příklad `kgmaker flow render --entry METHOD_ID --context CONTEXT_ID --view process --format json --strict`
vrátí PARTIAL a exit 4, pokud aktuální CFG používá metodu se spornou deklarací.

## T003-S07-W05 / AC04 — regresní a přesná CLI ověření

[Testy](../../tests/test_kafka_retry_dlt.py) čtou strukturovaný Kafka JSON
blok z Markdownu, ověřují kontrolované odmítnutí cizího kontextu a používají
skutečný CLI parser. Původní očekávání textu a neúplný ruční namespace
pocházely z verze před W09. Ověření zachovává testy statických statusů,
původního kontextu, strict exitu a nulové mutace.

[README](../../README.md), [compiler capability](../compiler-inspection.md),
[CLI](../kafka-retry-dlt.md), [acceptance](../acceptance-inventory.md) a
[stav](../production-analysis-progress.md) odkazují na aktuální důkaz.
Init a spravované instrukce nemají dopad.

- Skutečný JDK21, K1/K2 a lock-aware Maven vstupy. Původní zdroj bez oprav
  reprodukoval 10 FAIL / 2 PASS v cíleném výběru, včetně 4 TypeError
  při neplatné identitě kontextu. 188 případů bylo deselected.
- Zaměřené regresní ověření W05 po opravě: 66 PASS, 134 deselected.
- `pytest -p no:cacheprovider -q --tb=short tests/test_kafka_retry_dlt.py tests/test_http_client_execution.py`
  s `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1` a 34 ověřenými
  artifact/POM vstupy — 240 PASS / 0 SKIP, 87.81 s.
- `git diff --check` PASS. Úplná sada a externí T045 review pro tuto
  revizi jsou NOT_RUN. Kafka delivery a runtime zůstávají nepozorované.

## Integrace worktree proti main po #120

Přenesený zdroj vychází z ověřeného main
`8ff2529ffb50b42ed2209d97478ea3e4cbf46042` s tree
`c869302cdc2a7d9982d64058b6267ae603382e06`. Zachovává schválené W05 chování
a nový T052 workflow. Stejná striktní Java/Kotlin a HTTP sada v tomto
integrovaném checkoutu má **240 PASS / 0 SKIP**, 92.03 s.
Obě kontroly diffu prošly. Úplná sada a T045 review nového publikovaného páru
jsou před integrací stále povinné.
`kgmaker semantic apply`, `semantic validate`, `scan`, `status` a `check`
prošly. Generovaný graf je součástí integrované revize.
