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
