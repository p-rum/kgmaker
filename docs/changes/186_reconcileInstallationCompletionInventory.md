# Doplnění instalace a skillů do plánovače T052

Datum 2026-11-26. Výchozí `main` `d9379b210d6d4e245c958024484bc864ddb1105a`.
[T052](../tasks/52_addCompletionOrchestrator.md) · [T048](../tasks/48_completeImplementationHandoff.md).

## T052-S01 a T052-S04 / T052-AC01, T052-AC04

Plán na výchozí bázi četl 129 položek. T055-S03 deklaroval předpoklady
T050-S01, T053-S01 a T053-S02, jejichž stav měl zdrojové doklady mimo
kanonickou tabulku. Do téže tabulky nyní patří všech šest existujících kroků
T050 a T053. Jejich zadání používají pojmenované sekce s řádky `- Závislosti:`
a zachovávají dosavadní požadavky a acceptance. Plánovač má 135 položek,
z toho 106 MERGED a 29 PLANNED. Kontrola porovnala původních 129 položek
po hodnotách a zachovala pořadí všech 32 kandidátů pro dispatch. Závislosti
T055-S03 nyní všechny míří na položky tabulky. [Stavová matice](../production-analysis-progress.md) ·
[Registr](../tasks/README.md).

T050-S01 používá příkazy testgen z T046-S03 a kontrakt syntetických dat z
T046-S04. T053-S01 používá distribuované skilly T050-S01 ve společném
instalačním katalogu. Upgrade a uninstall používají vlastnictví z T053-S01.
Distribuční a chybové ověření T053-S04 navazuje na oba příkazy. Související
T049 má vlastní acceptance. [Specifikace T050](../tasks/50_addTargetProjectSkills.md) ·
[Specifikace T053](../tasks/53_manageProjectInstallation.md) ·
[Instalační katalog](../../src/kgmaker/installation.py#L26).

Oprava používá stávající formát stavové matice, parser a výstup CLI. Příkaz
`kgmaker completion plan --root /repo/kgmaker --jobs 3` platí i pro tento
inventář. README a příručky k instalaci popisují dosavadní příkazy a chování.
Doklad Excel kroků z #167 zachovává svůj historický výstup.
[Návod T052](../completion-orchestrator.md) · [Historický doklad #167](183_reconcileExcelCompletionInventory.md).

## T050-S01 a S02 / T050-AC01 až AC05

Dodání [#98](https://github.com/p-rum/kgmaker/pull/98) je v merge
`31a69bcf5b72c5f1f3be4ed699cc6b5672bcdcde`. Po starším BLOCKED pro stejný
pár následoval nezávislý verdikt T045 APPROVE pro head
`5cd3f78076171d4b955234b54cb030cce4c74bd7` a strom
`cbe737d266a4b33e9c67521319cd548cd872c68e`. Ověřující agent provedl
83 a 35 testů v oddělených výběrech, pět formátových validací, 21 lokálních
CLI volání a čistou instalaci wheelu. Verdikt se zaznamenal komentářem.
Formální GitHub schválení připojeného účtu odmítlo pravidlo pro self-review.
Hostovaný Test měl FAILURE/CANCELLED a dostupné logy neposkytly ověřitelný
doklad výsledků ani příčiny. [Přesný T045 verdikt](https://github.com/p-rum/kgmaker/pull/98#issuecomment-6892872266).

Aktuální kontrola T050-S01 dokládá osm původních prostředků včetně tří
referencí. Obsah spravovaných souborů odpovídá distribuovaným šablonám.
`AGENTS.md` vývojového repozitáře zůstává mimo distribuční katalog.
Distribuce navíc dodává Excel skill z T055. T050-S02 je PARTIAL, protože
kontextový skill a reference testgen se od #98 změnily. Úplný průchod
příkladů nad dnešními šablonami a živá discovery mají NOT_RUN.
[Distribuované šablony](../../src/kgmaker/skills.py) · [Acceptance](../acceptance-inventory.md).

## T053-S01 až S04 / T053-AC01 až AC04

Dodání [#154](https://github.com/p-rum/kgmaker/pull/154) je v merge
`1e782a119e5ae54d22bfc8d7c22c565ed651815a`. Doložený lokální
rozsah zahrnuje vlastnictví, opakovaný init, upgrade, uninstall a kontrolu
chybové publikace. T045 na opraveném headu
`960c7a0525b66dba559f8b054d6adac75c3ee0aa` a stromu
`29ac3341c5cdccea8740afe8f8c0877e1f41452a` ověřilo 133 PASS, včetně skutečného
offline Linux wheelu. Windows lifecycle, živý reload a nezachytitelný výpadek
zůstávají mimo doložený rozsah. [T045 pro #154](https://github.com/p-rum/kgmaker/pull/154#issuecomment-7141212040) ·
[Doklad sloučení](174_reconcileMergedDelivery.md).

Otevřené [#153](https://github.com/p-rum/kgmaker/pull/153) a [#165](https://github.com/p-rum/kgmaker/pull/165)
mají samostatné posouzení své revize. Stavy T050 a T053 vycházejí z
doložených merge #98 a #154 a z ověření aktuálního katalogu.

## Skutečné ověření

```bash
kgmaker completion plan --root "$PWD" --jobs 32
python -m pytest -p no:cacheprovider -q --tb=short \
  tests/test_completion.py tests/test_completion_handoff.py \
  tests/test_skills.py tests/test_installation.py
```

- RED — výchozí CLI skončilo kódem 0. Kontrola šesti očekávaných řádků
  skončila kódem 1. SHA-256 výchozího plánu
  `b0b928c5a5dccfba1a6afedc84e964246ab5a1844c675ebcae957347fd8c602f`.
- PASS — stejná kontrola ověřila nové položky, vyřešené odkazy T055-S03,
  129 shodných dosavadních položek a stejný dispatch. SHA-256 plánu
  `a7bfa042a889930fa909298835357c82ac4848eecb87e2611673558b4c68ad49`.
- PASS — 125 cílených testů, 0 SKIP za 6,24 s. SHA-256 JUnit
  `4747d0c5e5125d09f53b817e989915119d625ee3238da77fc76244e5c9d73c3c`.
- PASS — přímé porovnání katalogu `bundled_files()` s osmi verzovanými
  prostředky T050 a kontrola hranice Excel skillu. SHA-256 dokladu
  `67c6d16efe00f01776c78e9accea9b293d3e387162080e182b7eb514249b8d50`.

Strukturu sekcí a graf ověřují `kgmaker semantic update --base d9379b2`,
`kgmaker semantic apply`, `kgmaker semantic validate`, `kgmaker memory capture`,
`kgmaker scan`, `kgmaker status`, `kgmaker check` a `git diff --cached --check`.

Pro tuto změnu mají úplná sada, nový wheel, Windows, živý hostitel, hostovaná
CI a nové nezávislé review stav NOT_RUN.

### Přenesení po #166

Aktuální základ `main` je `80db9cb63b07ca653c53801406823eb5fb61e339`.
Přenos zachoval rozsah runtime evidence, zdroje, doklady i historii #166.
[Doklad #166](182_bindRuntimeInterfaceDispatch.md).

- RED — CLI nad tímto základem skončilo kódem 0. Kontrola opět našla šest
  chybějících řádků a skončila kódem 1. SHA-256 plánu
  `269d3a96e1d7326f693445e944412f8e07a7cd0e310692d0cae215fadf0df53f`.
- PASS — přenesený plán zachoval 129 dosavadních položek a všech 32 pozic
  dispatch. Výsledek má 135 položek, z nich 106 MERGED a 29 PLANNED.
  T050-S02 zůstává PARTIAL. SHA-256 plánu
  `06b597dc81c4ace94a7c6813a36f539e02740977c0fe3159f4e9a3bfe05d7704`.
- PASS — stejné čtyři cílené sady daly na přeneseném stromu 125 PASS a
  0 SKIP za 3,51 s. SHA-256 JUnit
  `6dd0634dc929bdfd5503bc7d2a61c793255ba5bdfec93c28318e83d7b82c01c3`.

### Ověření po #168

Výchozí `main` `4dc8f657b891f1716f7d134f97c1e6098cbb50b5` zahrnuje opravu
T056 se stavem PARTIAL v doloženém rozsahu.
[Doklad #168](184_preserveScopedExcelBehavior.md).

- RED — kontrola plánu nad `main` znovu našla šest chybějících řádků.
  SHA-256 `7985e2050f85125069b8a7fde4288cedcd8ddbf732aae875e6375614b776fe72`.
- PASS — plán změny má 135 položek, 106 MERGED a 29 PLANNED. Hodnoty
  původních 129 položek a pořadí 32 pozic dispatch zůstaly shodné.
  SHA-256 `c18ff64bcfd564c23d99df6e7741a8b7fa5aa38475f8c351814009da7b593559`.
- PASS — čtyři cílené sady daly 125 PASS a 0 SKIP za 6,70 s. SHA-256 JUnit
  `b03f612baa96a87064f31adf6ebf5a456028fcb5ec25d335adc20923cc6c9ff9`.
