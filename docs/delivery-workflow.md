# Šablony, testovací návrhy a dohledatelnost (T046)

Python standard-library rozšíření nabízí příkazy `template`, `testgen` a `trace`.
LLM práci provádí hostitelský agent. Kgmaker nevolá model API, neinstaluje závislosti
a nespouští navržené testy. Jedinými child processes v přípravě jsou existující
read-only Git metadata operace provideru. Compiler/data availability limity platí dál.

## Projektové šablony

`kgmaker init` nebo `kgmaker template init` vytvoří `.kgmaker/templates/` a zachová
uživatelské soubory. Verzujte tento adresář v Gitu. Druhy: `requirement`, `analysis`,
`implementation_task`, `test_case`, `test_data`, `test_code`, `filename`.

Manifest `<id>.json`:

```json
{
  "schema_version": 1,
  "id": "businessRequest",
  "kind": "requirement",
  "revision": 1,
  "description": "Business požadavek",
  "variables": ["title", "body"],
  "content": "business-request.txt"
}
```

Obsah například `# ${title}` následovaný `${body}`. Proměnné jsou doslovné texty;
shell, Python ani template expressions se nevyhodnocují. Projektový výběr lze nastavit
v `defaults.json`, například `{"requirement":"businessRequest"}`. Priorita je
`--template`, projektový výběr, dodaný default. Chybná volba nebo proměnná je chyba.
Názvy souborů používají standardně `${id}_${slug}.${extension}`. Custom manifest
může pojmenovat jiné proměnné pro obecné `template render`; testgen předává u
obsahových šablon `title`/`body`, u názvů `id`/`slug`/`extension`.

```bash
kgmaker template list
# vars.json: {"title":"Přepočet expozice","body":"Požadované chování…"}
kgmaker template render --kind requirement --variables vars.json --output-dir requirements --filename exposure.md
# names.json: {"id":"REQ1","slug":"exposure","extension":"md"}
kgmaker template render --kind requirement --variables vars.json --filename-variables names.json --output-dir requirements
```

Při zápisu vzniká ve workflow journalu reference s hashem výsledku a použitých
šablon. Bez `--output-dir` příkaz vrací pouze návrh na stdout. Kolize se nepřepisují.
Požadavek nebo implementační task vytvořený rendererem je dokument; runtime task
zakládejte existujícím `kgmaker task add`, následně dokument explicitně propojte.
Analytické šablony formátují zadání pro host agenta, nenahrazují feature JSON schema.

## Testování existující funkcionality

```bash
kgmaker testgen prepare --id exposure-tests --target src/calculator.py --scope all --framework unittest
# --target přijímá přesné existující entity ID, soubor nebo jednoznačný textový výběr.
# Volitelně --analysis <id>, --workspace <manifest>, --context <id>.
```

Výstup obsahuje `packet` a `candidate_template`. Packet zahrnuje target, skutečné
zdroje s hashi a omezenými výřezy, související grafové uzly/hrany, existující testy,
framework evidence, baseline, kontext a template provenance. Při víceznačnosti
příkaz vypíše kandidáty a nic nepublikuje. `--token-budget` omezuje packet; při
nedostatečném prostoru pro cílový zdroj skončí příprava chybou. Pro více kontextu
použijte existující query/impact/feature nástroje.

Frameworky návrhu: unittest, pytest, junit, jest, vitest, playwright. Detekce je
konzervativní vyhledání konfigurace a současných testů, nikoli důkaz instalace.
Více kandidátů vyžaduje `--framework`. Bez frameworku lze vytvořit cases/data,
ale files musí být prázdné a `code_status` je BLOCKED. Explicitní výběr bez
nalezené konfigurace je uživatelská volba návrhu, nikoli ověřená runtime podpora.

Host agent vytvoří JSON kandidáta tohoto tvaru; citaci doplní přesným hashem/řádky:

```json
{
  "schema_version": 1,
  "suite_id": "exposure-tests",
  "packet_id": "<z packetu>",
  "cases": [{
    "id": "positive",
    "title": "Přepočet kladného vstupu",
    "target_ids": ["<packet.target.id>"],
    "requirement_refs": [],
    "category": "characterization",
    "preconditions": "Modul lze importovat",
    "steps": ["Zavolat funkci se vstupem 2"],
    "expected": {
      "text": "Výsledek je 4",
      "basis": "CODE_CHARACTERIZATION",
      "citations": [{"path":"src/calculator.py","sha256":"<hash>","start":1,"end":2,"quote":"return value * 2"}]
    },
    "dataset_ids": ["numbers"]
  }],
  "datasets": [{
    "id": "numbers",
    "purpose": "Kladný a nulový vstup",
    "schema": {"type":"array","items":{"type":"integer"}},
    "data": [2,0],
    "negative": false,
    "expected_violations": [],
    "citations": [{"path":"src/calculator.py","sha256":"<hash>","start":1,"end":2,"quote":"return value * 2"}],
    "foreign_keys": []
  }],
  "files": [{"path":"tests/test_generated.py","content":"<testovací kód>","case_ids":["positive"]}],
  "questions": []
}
```

Kategorie: positive, negative, boundary, characterization. Basis:
CODE_CHARACTERIZATION, CONTRACT, ANALYSIS. Citace musí být v připraveném packetu,
hash a citované řádky odpovídají skutečnému souboru. Analytické očekávání cituje
připojenou aplikovanou analýzu; samotná shoda textu není důkaz business správnosti.
`requirement_refs` jsou existující reference druhu requirement z trace journalu.

```bash
kgmaker testgen validate --id exposure-tests --candidate candidate.json
kgmaker testgen apply --id exposure-tests --candidate candidate.json
kgmaker testgen report --id exposure-tests --format markdown
kgmaker testgen export --id exposure-tests --data-dir tests/fixtures/kgmaker --data-format json
# Teprve nyní explicitně použít existující projektový runner, například:
python -m unittest discover -s tests
```

Apply ukládá neměnné revize s validační receipt; stejný kandidát je idempotentní.
Export používá přesně navržené test-code paths, názvy datasetů řídí přesná
filename šablona uložená v packetu (pozdější změna defaults ji nepřepíše). JSON podporuje strukturovaná data, CSV vyžaduje neprázdné ploché
objektové řádky. Preflight kontroluje kolize všech souborů, při chybě zápisu se
již zapsané soubory odstraní. Existující soubory se nikdy nepřepíší.

Data jsou SYNTHETIC. Podporovaný schema subset: type (object/array/string/integer/
number/boolean/null), properties, required, items, enum, minimum, maximum,
minLength, maxLength, nullable a additionalProperties. Hodnota `true` nebo
vynechaný klíč povolí další vlastnosti, `false` je odmítne. Objekt s podporovaným
`type` rekurzivně ověří každou další hodnotu stejným subsetem. Například s
`"additionalProperties":{"type":"integer","minimum":1}` vytvoří `{"extra":0}`
důkaz `$.extra:minimum`. Nestandardní název mapy se ve vnořené cestě uvozuje
jako `$["metrics.v2"][0].count:minimum`. Uvnitř typované dodatečné hodnoty se
tento zápis používá pro všechny segmenty cesty, včetně rodičů před typovanou
hodnotou. Ostatní diagnostiky ve starších větvích zachovávají dosavadní formát.
Tvar `additionalProperties` a bezprostřední typ jeho schématu
se kontrolují i u objektu bez dalších hodnot. Vnořené podsložky se kontrolují
tam, kde mají odpovídající datovou hodnotu.
Foreign keys mají
`field`, `dataset_id`, `target_field` a porovnávají skutečné hodnoty v řádcích.
Neznámé keywords jsou `unchecked_constraints`. Negativní dataset musí uvést
přesně nalezené violations, např. `$[0].amount:type`. Pozitivní dataset nesmí mít
zjištěné porušení. Vztah constraints a citované domény stále posuzuje člověk/agent.
Opakovatelnost zajišťují uložené bajty/hash, nikoli příslib stejného LLM výstupu.

Každá změna zdrojů, grafu, compiler/workspace baseline nebo připojené analýzy
zneplatní packet konzervativně. Export nových testů rovněž mění zdrojový snapshot;
historický report pak může být STALE, ale receipt a historie zůstávají čitelné.
Kód se syntakticky validuje pro Python; u jiných jazyků je syntax check explicitně
neověřený. Existence návrhu ani statická validace nejsou PASS skutečného běhu.

## Dohledatelnost a lokální rozhodnutí

```bash
kgmaker trace identity --actor alice --kind human
kgmaker trace register --kind requirement --id REQ-1 --revision 1 --path requirements/exposure.md
# Příkaz vrací ref:<hash>; používejte přesné vrácené klíče:
kgmaker trace decide --subject <requirement-ref> --action requested --reason 'Zadáno produktovým vlastníkem'
kgmaker trace sync-analysis --id exposure
kgmaker trace sync-task --id <runtime-task-id>
kgmaker trace sync-testgen --id exposure-tests
kgmaker trace link --source <analysis-ref> --target <requirement-ref> --relation analyzes
kgmaker trace link --source <task-ref> --target <analysis-ref> --relation implements
kgmaker trace capture-change --task <runtime-task-id> --base <base-ref> --head <commit-ref>
kgmaker trace link --source <test-suite-ref> --target <change-ref> --relation verifies
kgmaker trace show <requirement-ref> --format markdown
kgmaker trace check
```

Reference obsahuje druh, ID, revizi, repo ID, obsahový hash a snapshot. Journal
`.kgmaker/workflow/lineage.json` je obnovitelným indexem explicitních vazeb a místem
lokální auditní historie; nenahrazuje runtime task katalog. Importy jsou explicitní,
pro nové revize znovu spusťte sync. Source graph se nemění a neodvozuje žádnou vazbu
pouze z podobnosti jmen. `capture-change` s `--head` dokládá commit diff; bez něj
zachytí Git diff pracovního stromu jako WORKTREE, bez tvrzení o commitnutí.
Nezahrnuje neversionované untracked soubory: před evidencí je přidejte do Gitu.

Relace: analyzes, implements, verifies, uses_dataset, depends_on, supersedes.
Události: requested, submitted, approved, rejected, revoked. Historie se nepřepisuje;
opravy jsou nové události. U každé jsou aktér, UTC čas, důvod a přesná reference.
Příkaz identity je pouze deklarace, **LOCAL_DECLARED není autentizovaná identita**.
Hash řetězce dokládá lokální integritu, není podpis ani ochrana proti přepsání celého
úložiště jeho vlastníkem. Agent nesmí vytvářet lidská schválení.

`trace show` prochází oběma směry. `trace check` odhaluje neaktuální evidence,
osiřelé objekty, chybějící zadavatele a neúplný řetězec tasku. Zastaralá/odvolaná
schválení se nezobrazují jako platná. Běh testu evidujte odděleně přes stávající
`task record --role test_expert`: testgen report zůstává návrhem NOT_RUN.

## Volitelné brány a kompatibilita

```bash
# Standardně je obojí off. Nastavení může projekt kdykoliv změnit:
kgmaker trace policy --before-implement on --before-done on
kgmaker trace decide --subject <current-plan-ref> --action approved --reason 'Plán posouzen'
kgmaker trace decide --subject <task-request-ref> --action approved --reason 'Požadavek schválen'
kgmaker trace decide --subject <current-review-ref> --action approved --reason 'Výsledek review přijat'
kgmaker trace policy --before-implement off --before-done off
```

Brána před implementací vyžaduje schválení přesného task request a posledního plánu.
Brána před done navíc vyžaduje poslední review s overall=approve, zaznamenané po
poslední implementaci, obsahově svázané s aktuálními zdroji. Změněný plán, zdroje,
nové review nebo revoked/rejected vyžadují nové rozhodnutí. Brány kontroluje i
knihovní save_task, nikoli jen CLI. Neudělují oprávnění k merge.

V1 workflow identity se nemění. Záznam implementace/review doplní v2 metadata
`delivery.bindings[artifact_id] = {head_commit, source_fingerprint}`; historické
artefakty a jejich ID zůstávají. Starší čtečky v2 odmítnou: upgradujte všechny
spolupracující klienty. Nové mutace tasku používají optimistic CAS; journal/testgen
mají exclusive writer lock a atomickou výměnu JSON state. Pokud zůstane lock po
pádu procesu, ověřte, že žádný writer neběží, a odstraňte pouze příslušný `.lock`.
Zdrojové změny probíhající současně s generováním vyžadují novou přípravu.

## Opravy review — revize 2

Výstupní cesta musí být kanonická: bez `./`, zdvojených oddělovačů nebo
chráněného segmentu `.git`, `.github`, `.kgmaker` (case-insensitive). Stejná
kontrola platí pro kód i JSON/CSV data před jakýmkoliv zápisem. Nekanonické
aliasy se odmítají; nepoužívají se k obcházení deduplikace a zákazu metadat.

JSON enum a FK rozlišují boolean od number i uvnitř polí/objektů; 1 a 1.0
jsou číselně ekvivalentní. Chybějící FK target key není null. Explicitní null
se může spárovat pouze s explicitním null v cílovém klíči, pokud to schema
dovoluje; nepoužívá se implicitní SQL-null nebo fallback na chybějící sloupec.

`save_task` vyžaduje při změně existujícího záznamu `expected_revision=digest(task)`;
uložení zcela stejného záznamu zůstává idempotentní. Založení tasku je atomické
create-or-load pod stejným workflow lockem. Artefakty jsou neměnný prefix,
staré bindings se nesmějí přepsat ani doplnit zpětně a nové artefakty musí mít
aktuální fázi i iteraci. Přímý save nesmí přeskočit povolený přechod workflow.

Všechny mutující `trace` příkazy předávají `--expected-revision N` do skutečné
zapisující transakce. Nepřítomná volba zachová dosavadní chování; neplatné typy,
záporné nebo zastaralé revize skončí chybou bez změny souborů. `show` a `check`
volbu nepřijímají, protože nic nezapisují.

Nový implement/review binding se při uložení vypočítá pod workflow lockem.
Pokud caller dodá jiné hodnoty než skutečný HEAD a source inventory, zápis
se odmítne. Chybějící binding nízkoúrovňového v1 save se doplní se schématem v2;
identita tasku a artefaktu zůstane stejná. U legacy tasků v1/v2 se top-level
source observations aktualizují pouze s novým implement/review artefaktem.
Profilované v3 tasky zachovávají verzi 3 a přidávají obsahovou vazbu také při
test artefaktu.

## Propojené projektové workflow (T051)

Konfigurace rolí, povinné testové příkazy a neměnný snapshot v task v3 jsou
popsané v [projektových workflows](project-workflows.md). Používají existující
trace/approval kontrakty této příručky; synchronizace zůstává explicitní.
[Záznam změny](changes/118_connectProjectWorkflows.md).
