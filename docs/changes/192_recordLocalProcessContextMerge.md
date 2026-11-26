# Záznam sloučení výběru kontextu a omezení toku

Datum 2026-11-26. [T048-S01 / T048-AC01](../tasks/48_completeImplementationHandoff.md#3-první-krok-t048-s01--sjednotit-stav-a-vytvořit-pracovní-seznam),
[T025](../tasks/T-025_build-local-process-path.md),
[T030](../tasks/T-030_prepare-process-label-packet.md),
[T043](../tasks/T-043_bound-view-performance.md).

## T048-S01 / T048-AC01

Kanonický řádek T025 po sloučení stále označoval #174 jako draft. GitHub
potvrdil sloučení do `main` v 19:25:20 UTC. Výchozí commit dokumentační
změny je `cb9848520b056518d028ceb8010ec6a6f9a43a2f`, strom
`833ec83af3495311aafabb25a0f5de87181d1c62`. Rodiče jsou
`346536495db749a6a1d79f89b388b55f9db3da83` a schválený head
`7e36de47dce06c44157c1080cc1a304af0e47239`. Matice uvádí nový merge, zachovává
dřívější merge `7a89e2868791eb7a061572de7527172e3b1ceb6a` i původní seznam PR.
[Sloučený #174](https://github.com/p-rum/kgmaker/pull/174) · [Stavová matice](../production-analysis-progress.md).

Nezávislé T045 vydalo `APPROVE` pro uvedený base, head a strom. Výsledek je
zaznamenaný komentářem. GitHub API odmítlo formální schválení účtem autora
kódem 422. V době merge běžely dva hostované `Test` běhy na headu a jeden na
`main`. Doklad o sloučení má SHA-256
`76c08c796135298a2f09af25feaf333a7e30e13d10452a7a3efd1210d8729aec`.
[Přesný verdikt T045](https://github.com/p-rum/kgmaker/pull/174#issuecomment-7201558053).

## T025-AC04/05/09 a vazba na T030-AC01/04/05

Sloučený `main` má samostatný cílený běh s Temurin JDK 21.0.6+7. Prošlo
19 testů za 16,89 s, 0 SKIP, 0 FAIL a 0 ERROR, raw exit 0. Běh ověřil
lokální proces v Javacu a Kotlin K1, skutečný výběr ze dvou repozitářů,
odmítnutí nepodporované obálky T030, starší grafy v1/v2 a plánovač.
Manifest 923 souborů a identita workerů před a po běhu souhlasí. SHA-256
JUnit `4e533abaae73b25e0fde3e3804d36972c1fb3a739ec61be336f059dddf0def2c`.
SHA-256 shodných manifestů
`4c966b422af0c9e4450ce5a08615a65a773feb0c7c9c6e6ebf1425ba084c8ee9`.
[Testy](../../tests/test_t025_build_local_process_path.py) · [Acceptance](../acceptance-inventory.md#t025--local-technical-process-path).

Před sloučením proběhla na headu `7e36de47` standardní sada s výsledkem
2625 PASS, 1382 SKIP, 1 očekávaný XFAIL a raw exit 0. To je samostatný
historický doklad, SHA-256 JUnit
`939a3327c79f6f612707541d3860b9969a8dc90611fb00abde75d2e8d22c55be`.
[Implementace a její původní kontroly](190_bindLocalProcessContext.md).

T025 a T030 mají dodání MERGED a ověření PARTIAL. T034 zůstává PLANNED /
NOT_RUN. Pro použití lokálního výběru platí stávající příklady v příručce API
a README. [Výběr kontextu](../process-paths.md) · [Příprava packetu](../process-label-packets.md)
· [README](../../README.md#local-technical-process-paths-t025).

## Historické ověření první revize #176

Následující počty, porovnání plánů a JUnit patří prvnímu headu #176
`7b24eff22d74160376234911a552836cb1db1d78` na base
`cb9848520b056518d028ceb8010ec6a6f9a43a2f`.

```sh
kgmaker completion plan --root "$PWD" --jobs 32
python -m pytest --assert=plain -q -p no:cacheprovider tests/test_completion.py
```

- PASS — plán má 135 položek, 106 MERGED a 29 PLANNED. Změnil se jen
  doklad v řádku T025. Ostatních 134 položek a všech 32 pozic pro delegování
  je shodných. SHA-256 výsledného plánu
  `041fd9091026f8cbaa7e1aeaa46b682cf44579124bd6b5afa73a67f9f5c48351`.
- PASS — 13 testů plánovače, 0 SKIP. SHA-256 JUnit
  `dae2f4dc6ba6188311db97a4b15973e063fd5d54bb5872b2ff8e4b47df08db1e`.

Počáteční kontroly zahrnovaly `semantic update`, `semantic apply`,
`semantic validate`, `memory capture`, `scan`, `status`, `check` a
`git diff --cached --check`. Při pozdějším přezkumu headu
`e8f42482377f733acc6730e4d12ee293ca3aac27` proti base
`0b922c00bfe7ebe57f07bf7dfdee7e8ab746318a` dala T045 verdikt `REQUEST_CHANGES`
kvůli chybějícímu označení historického rozsahu dokladů. [Verdikt T045](https://github.com/p-rum/kgmaker/pull/176#issuecomment-7202753732).

## T043 — sloučené omezení toku a diagnostiky

[PR #173](https://github.com/p-rum/kgmaker/pull/173) je sloučené do `main`
jako `8290606eace7d7c94497cca143fa8e70c0042d38`. Rodiče merge jsou v pořadí
`0b922c00bfe7ebe57f07bf7dfdee7e8ab746318a` a
`c5069e03ef4d81c48683f2225108f4f2fc497795`. Strom
`0864c5eacd0a574c4e5a6efb02ef658a95d71874` odpovídá přesně testovanému headu.
SHA-256 ověřeného dokladu o sloučení
`97241ac483183016548d1d5f95b9f47f4309534aec147e72275fd621eba18128`.

Nezávislá T045 na uvedeném headu vydala `APPROVE` pro T043-S02 a T043-AC04.
Její cílený běh měl **26 PASS / 0 SKIP**, 42 nezvolených případů. SHA-256 JUnit
`6c27477567580ee910f02e08b72bdd1c08541c451a850c807e0759595f4512ac`.
Další přesný běh na schváleném headu ověřil čtyři výstupy parserem Mermaid 11.4.1.
SHA-256 dokladu `fe7e3d250cb5b4c9312221b8aab400216051f1a3e71f37b70fe522932a632837`.
[Nezávislý verdikt](https://github.com/p-rum/kgmaker/pull/173#issuecomment-7202991032).

Po sloučení prošlo na `8290606` **33 PASS / 0 SKIP** za 3,42 s, raw exit 0.
Cíleně se ověřil plánovač, limity průchodu a diagnostiky, zachování posledního
platného reportu a kontrolní test pojmenovaných cizích klíčů. Otisky sledovaných
souborů před a po běhu souhlasí. SHA-256 JUnit
`c3a2eb77432f37d5e1621f61267ff2f60447beda8d5b546851a78bc172e0f75e`.

Kanonický T043 má stav MERGED / PARTIAL. Celkový bajtový rozpočet reportu,
strukturální mezery a diagnostika vztahových pohledů zůstávají mimo ověřený
rozsah. [Kritéria T043](../acceptance-inventory.md#t043--limity-velikosti-a-výkonu-pohledů)
· [Implementace a hranice](189_reduceBoundedCfgTraversal.md).

## Ověření doplnění inventáře po #173

Toto dokumentační doplnění vychází z headu #176
`e8f42482377f733acc6730e4d12ee293ca3aac27` a skutečného `main`
`8290606eace7d7c94497cca143fa8e70c0042d38`. Lokální plán má 135 položek,
z toho 107 MERGED, 27 PLANNED a jednu IN_PROGRESS. Změnil se doklad T025,
dodání T043 a odvozený seznam blokací T044. Z 32 položek k delegování
uvolnil sloučený T043 místo pro ověření T003-S10-W02. Zbývajících 31 položek
má stejné pořadí jako na uvedeném `main`. SHA-256 plánu
`c59e9ed7dd3acc3ddf754dd19e6d03607858c68136353ef8f01a83cb85cb6cc1`.

Cílená sada plánovače podle uvedeného příkazu má **13 PASS / 0 SKIP**.
SHA-256 JUnit `207a9f6449cf63cce596d64214299aa52554a506ddc8b54356a94e90e110dfbf`.
Úplná sada má v tomto místním dokumentačním běhu stav NOT_RUN.
