# Počet průchodů přes hrany při omezení zdrojového CFG

Datum 2026-11-26. Výchozí `main` `538d61d80ba991cbff5413973d92e7c6ec79e2aa`.
[T043 a kritéria](../tasks/T-043_bound-view-performance.md) ·
[Ověření](../acceptance-inventory.md#t043--limity-velikosti-a-výkonu-pohledů)

## T043-S02 / T043-AC01, T043-AC02 a T043-AC05

Když měl zdrojový graf toku řízení více uzlů než dovoluje `--max-nodes`,
`flow.py` kontroloval postupně kratší prefixy. Každá kontrola četla všechny
hrany. Silně větvený vstup opakoval stejnou práci před tím, než vytvořil
jedinou hranici za vynechaný kořen.

`src/kgmaker/flow.py` vytvoří index odchozích hran a rozšiřuje stejný
kanonický prefix o jeden uzel. Udržuje množinu různých cílových uzlů mimo
prefix. Přidání uzlu odebere nanejvýš jeho vlastní hranici a může přidat
další hranice. Součet uzlů a hranic proto po prvním překročení limitu
neklesne. Výpočet kandidátního prefixu projde indexované hrany nanejvýš
jednou a vykreslení použije dosavadní strukturu grafu.

Při rozpočtu, který nepokryje ani první uzel a jeho hranice, se zachová
uzel vynechaného kořene. Vybrané uzly, hrany, původní ID, cykly,
provenance, `NOT_OBSERVED` a `UNKNOWN` zachovávají dosavadní význam.
Formáty výstupu a grafu ani parametry CLI nevyžadují migraci.

## T043-S04 / T043-AC01, T043-AC02, T043-AC04 a T043-AC05

Dva nové případy v `tests/test_unified_flow_views.py` počítají návštěvy
hran na skutečné cestě sestavení reportu. Tři další ověřují přesné prefixy,
sdílené hraniční cíle, větvení a hustý cyklus při třech rozpočtech. Testy
porovnávají vstup před a po sestavení reportu.

- **2 očekávané FAIL a 3 PASS** — stejná testovací fixture nad zdrojovým
  archivem výchozí revize. Počítadla zachytila opakované návštěvy hran.
  `python -m pytest -q -p no:cacheprovider tests/test_unified_flow_views.py -k 'fanout_edges or shared_frontier'`.
  SHA-256 JUnit `15e1e93869166283b0698e16411651ce1b55495a3bc4ab00fe2d09807c1ab9b0`.
- **254 PASS, 0 SKIP, 7 deselected** — opravené CFG, process-path, topology
  a cache regrese. Příkaz je uveden níže. SHA-256 JUnit
  `33981f3af0c0c0a92b02f70deba8a41712c44beb587145224e66908b58668105`.
- **PASS** — 51 bajtově shodných výstupů JSON, Markdown a Mermaid před
  opravou a po ní. Pokrývají 17 kombinací větveného nebo cyklického modelu
  a rozpočtu. SHA-256 obou seznamů velikostí a otisků
  `1ad9dc7a133602709c8db86e478349df200dff371fb4ab9baf443e3bc616998e`.

```sh
python -m pytest -q -p no:cacheprovider \
  tests/test_unified_flow_views.py tests/test_t025_build_local_process_path.py \
  tests/test_t017_filter_topology_scope.py tests/test_t037_invalidate_derived_views.py \
  -k 'not actual and not real'
```

Lokální sonda v Cloud Environment na Linuxu x86-64 a CPython 3.12.14
měřila návštěvy hran při sestavení reportu. Výstupní JSON měl v každém
páru shodný SHA-256. Čas je medián tří místních běhů bez počítadla.

| Koncové větve | Uzlový rozpočet | Návštěvy před | Návštěvy po | Sekundy před | Sekundy po |
|---|---|---|---|---|---|
| 64 | 32 | 4 608 | 640 | 0,001510 | 0,000786 |
| 128 | 64 | 17 408 | 1 280 | 0,003466 | 0,001542 |
| 800 | 400 | 646 400 | 8 000 | 0,034201 | 0,008259 |
| 1 600 | 800 | 2 572 800 | 16 000 | 0,126309 | 0,028471 |

SHA-256 záznamu výchozí sondy
`1c429f66372ebd03d09d11498290363a1c73f3178eac011deea7592bc0926b54`
a opravené sondy
`6de4319fbadecbe2975f9f6e6bac0054620305c894db384ead5c87164673acd4`.

## T043-S05 / T043-AC06

Rozsah opravy a příklad CLI jsou v [README](../../README.md#unified-flow-reports),
[popisu CFG](../unified-flow-views.md) a [stavové matici](../production-analysis-progress.md).
Stav ověření T043 zůstává PARTIAL.

## T043-S01 a T043-S03 / T043-AC03

Opt-in `tests/benchmarks/t043_view_performance.py` používá stávající
fixture T017 a veřejné producenty `filter_topology`, `flow.build_report`
a `flow.render`. Generuje 100 služeb s 10 000 samostatnými vazbami a CFG
s 1 600 větvemi a 1 600 zpětnými hranami. Topologie měří rozpočet pěti uzlů
a pěti skoků. CFG měří rozpočet 800 uzlů. [Příkaz a metodika](../unified-flow-views.md#t043-scale-benchmark)

Na stejném Cloud runneru použil benchmark Linux 6.18.57 x86-64, CPython
3.12.14 a pět logických CPU. Tři čerstvé procesy na variantu střídaly
výchozí zdroj `346536495db749a6a1d79f89b388b55f9db3da83` a kandidáta
`aa3f7c17a246613d805e2d6a6e0cede892dae507`. Cold znamená první report
v každém procesu a warm medián tří navazujících reportů. Samostatný
průchod měří špičku alokací Pythonu. Otisky vstupních fixture a výstupů
se shodují. Benchmark vrátil **0** a všechny metriky prošly hranicí 25 %.

| Případ | Cold před a po v ms | Warm před a po v ms | Špička před a po v bajtech |
|---|---|---|---|
| Topologie | 1 187,5 → 953,5 | 990,6 → 993,0 | 32 679 566 → 32 679 566 |
| Cyklický CFG | 121,9 → 18,4 | 120,4 → 17,0 | 995 600 → 995 640 |

Jde o místní relativní měření. SHA-256 úplné zprávy se vzorky
`549ef6d19d9256d2af69d4e0d86ff433803989237e38dc60afdd7abfc1a05962`.
Opakování ze samostatného archivu stejné výchozí revize prošlo všemi
šesti kontrolami. SHA-256 druhé zprávy
`24cf941f8f641a92968facb2a13dc4d866fb6dbc4d9310f736a089e0d60bb2f5`.

## Rozsah testů benchmarku a zbývající ověření

**4 PASS** v `tests/test_t043_bound_view_performance.py` dokládají úplný
inventář všech 10 000 ID, omezení uzlů a skoků topologie, explicitní hranici
velkého cyklického CFG, přesné místo hloubkového omezení v procesu a výpočet
relativní hranice 25 %. Negativní případy ověřují odmítnutí neplatného
rozpočtu a neporovnatelných vstupních nebo výstupních otisků. SHA-256 JUnit
`c470c849db3c53e95bb353968d5e545d8056dd8e1bc9ebb33384fb650645b86d`.

Samostatná sonda zachovala v reportu s jediným uzlem 1 024 zdrojových
diagnostik a 1 026 položek coverage. Společná mez diagnostiky pro CFG
a ostatní pohledy má zbývající rozsah T043-S02. SHA-256 sondy
`245f9f1b07a9dbf9335631ab703faa001371d5089e6d6ef4fe617f52ab50a928`.
Úplná pytest sada, hostované CI a nové spuštění compiler workeru či Mermaid
parseru mají v tomto doplnění stav NOT_RUN. [PR #173](https://github.com/p-rum/kgmaker/pull/173)
