# Katalog používaných HTTP rozhraní

T011, S01–S05, AC01–AC06. Baseline75d448ee7791cffb3dc9f4cceff5136402a8f5e0:
T008/T009 a W06 PR49 jsou sloučené. Root schválil nezávislý architektonický brief;
implementace je samostatně v feat/t011-catalog-http-consumers.

## Problém a skutečná změna

Chyběla čistá consumer projekce nad skutečnými W06 request/execution fakty.
Append-only project_http_consumers v existujícím interfaces.py reuse společný
ViewDocument/http_interface, ownership/context inventory a T009 evidence buckets.
Provider function a jeho IDs se nemění. Nepřidává se resolver, store ani CLI.

Consumer zachovává caller/origin/terminal a method/path/provenance. Dvě volání
stejné route ani dva terminály jednoho publisheru se neslévají. Feign declaration
nenahrazuje skutečného consuming caller. Lazy request a statický trigger nejsou
pozorované síťové volání. Dynamická route zůstává None s důvodem/source reference.
Request/response contract refs a remote service binding zůstávají None, protože
W06 takový důkaz neposkytuje. Runtime/data/deployment jsou UNKNOWN/NOT_OBSERVED.

Validace kontroluje canonical source/caller/node, request/call-site identity,
range, scope/context/SHA, chain/terminal vlastníka a původní edge/proof tuple.
Selected kontexty se vybírají před validací historických siblingů. Invalidní vstup
nemění caller snapshot ani zdroje; URI provenance má allowlist, bez privátních
volných payloadů. Evidence polarity se přenáší společnými T009 buckety.

## Ověření a hranice evidence

- Durable task94fa8375cfcfc9cb3589649226833ad9ec15dda4e27976e5f7f2cfb219d9fbc7:
  analyze/plan z approved brief a bounded packets, memory recall proveden.
- Existující actual-built W06/JPA/coroutine JVM source/builders/locks a dependency
  receipts byly porovnány před kopií workerů. K1SHA50cf8376/K2SHA2eb240a5 jsou
  skutečné fresh PR49 builds, nikoli domněnka ze shody nově mergnutých zdrojů.
  Záznam /workspace/t011-worker-copy.json; žádný implicitní install/build.
- RED po skutečném pinned W06 K1 compiler/snapshot capture:1FAIL2.73s na chybějícím
  public API. Následná shape oprava sladila Graph.symbols, publisher ID contract a
  existující coverage counts schéma; nejde o rozšíření upstream resolveru.
- Captured route-mirror negative reprodukoval přijetí cizí route metadata; guard
  srovnává canonical Node.name. Primitivní URI/path a provenance shapes mají
  fail-closed kontrolu.22 actual-capture K1 public/negative replay checks PASS;
  čerstvá společná K1/K2 suite je zatím PENDING. Žádný full není vykázán jako PASS.
- Přesné finální source/focus/full výsledky se doplní před ready. GH CI je podle
  uživatelské revize T045 volitelné, ostatní lokální acceptance/review zůstávají.

AC01 pokrývá lazy/static intent test; AC02 dynamický URI a zachované origin IDs;
AC03 actual Feign dva callers, dva same-path requests a dva shared terminals;
AC04 offline/no-mutation; AC05 source/edge/owner/scope/hash malformed matrix a
stale sibling, podporované polarity; AC06 README/capability/status/AC a tento note.

Příklad a hranice: [HTTP consumers](../http-consumers.md). SOURCE_ONLY/legacy hints
se nepovyšují na typed execution, nepodporovaný rule version je boundary. Skutečný
aplikační/runtime HTTP test NOT_RUN; statický compiler fixture není runtime PASS.
T012, remote bindings, architecture CLI/rendering a celý T004 zůstávají mimo scope.

## První skutečný grouped proof a current UI parent

K1/K2 captured public suite je **52PASS,0SKIP,11.78s**, včetně16 malformed
variant/back end, evidence polarity, CONFIG provenance, same-path/Feign
callers a shared publisher terminals. Oba source/test hashes před/po jsou shodné;
persistent grouped.log/XML a source manifest jsou v /workspace/t011-validation.
Root earlysourceclosure APPROVE nad2acee91 nezjistilo blocker.

Před jediným full je integrován UI-only main081d69ca69d14b4d131cc305e4e5c873960e71a3.
Own interfaces.py a test file zůstávají přesné approved/focus source;17 JVM
source/artifact hashes stále odpovídá actual-built50cf/2eb receipt, žádný rebuild.
TypeScript package/lock porovnány s actual-tested UI checkoutem a dependencies
explicitně zkopírovány; tracked worker/UI adapter pochází přímo z parenta.
URI status behavior se nerozšiřuje: jen DECLARED_LITERAL může resolve; ostatní
budoucí/neznámé nonempty statusy jsou dokumentované UNKNOWN. Relevantní current
focus a nový full outcome jsou zatím PENDING, nikoli PASS.

## Skutečné provenance nálezy po early closure

Captured read-only replay odhalil2defekty: non-Feign metadata declaration se
neověřeně kopírovalo do declaration_id; a CONFIG provenance dovolila cizí key
při správném fileSHA, bez vazby na canonical context record. Root je potvrdil.
První ownfull nad82dd790 byl proto šetrně přerušen pouze SIGINT vlastníhopytest
(159843) a jeho worker strom byl ověřen pryč před editací. Zachovaný partial je
**340PASS,7SKIP,634.79s,exit2**, XML347tests/0errors/0failures; není to fullPASS.
Log/XML/process snapshot jsou interrupted-82dd790.* a všech242frozenhashů bylo
po ukončení totožných. Cizí queues ani procesy nebyly zasaženy.

Oprava emituje declaration_id jen pro ověřený FEIGN; extra pole jiných families
se ignoruje. CONFIG key/status/profiles/source_file/SHA musí přesně odpovídat
jedinému existujícímu hash-bound context.http_config_provenance recordu. Žádný
parser ani resolver se nepřidává. Captured negatives pokrývají neověřený ref
(str/object/list) i cizí key/profiles a input immutability; původní CONFIG/Feign
pozitivní případy zůstávají. Nový grouped proof a corrected full zatím PENDING.

## Jednorázový current parent refresh pro corrected source

Po zastavení neplatného sourcefull je integrován1915/aktuální mainc6950e9
(T025 je navíc čistý process-path/flow adapter). Žádný runtime konflikt vlastní
projekce; zachované jsou Arg, Template i UI parent moduly a všechny CI gates.
Všech27 tracked worker inputs bylo ověřeno přímo proti actual-built source
receipt63d3dbb970933751ac74e093f8aac0073de27a94. Všech30 JAR/dependency hashů
z built-jars.json odpovídá donor bytes před kopií; nové K1 2bf6cbde/K2 24461c43
jsou skutečné aktuální Arg buildy, ne staré artefakty přeznačené podle HEAD.
Persistent doklad /workspace/t011-validation/argument-worker-copy.json.
Corrected grouped/full zůstávají PENDING do skutečného výsledku.
