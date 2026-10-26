# T003-S05-W03 — Typovaná Spring condition matice

## Problém a skutečné změny

Původní pravidla četla jen první vytištěný argument anotace. Tím ztrácela
seznamy profilů/klíčů/tříd, ignorovala property prefix a část aliasů a negovaný
profil znovu filtrovala jako obyčejné jméno při injection. Řetězcový tisk také
ztrácel rozdíl mezi skutečným booleanem a chybným stringem matchIfMissing.

Nový čistý `spring_conditions.py` zachová typované compiler members vedle
kompatibilního display stringu. Přesné kanonické identity přijímají bounded
profile výrazy/OR arrays, property alias/prefix/všechny klíče/ASCII ignore-case
havingValue/boolean matchIfMissing a všechny přesné třídy v deklarovaném
context inventory. Prázdný známý class inventory znamená absence; chybějící
inventory UNKNOWN. Oba směry class podmínky odmítají nevyřešený compiler class
literal. Custom/unsupported podmínky se nespouštějí a zůstávají UNKNOWN.

Framework wrapper zachovává stávající class/method/import/component-scan
reachability. Injection používá již vypočtený condition_status bez druhého
literal-profile filtru. Evidence zůstává FRAMEWORK_DERIVED; nic se neprohlašuje
za spuštěnou aplikaci, deployment nebo dostupná data.

JVM pravidla v6 a hash profile/property/class vstupů vážou cache na zvolený
snapshot; změna uložených hodnot vyžaduje reinspection. Starší graph schémata
zůstávají čitelná, ale staré framework rules nejsou vydávány za čerstvou v6.
Explicitní variantové project.input_files a classpath hashe invalidují jen
svůj kontext; nezužuje se konzervativní snapshot sdílených source/build vstupů.
TypeScript/React metadata a selector compatibility zůstávají beze změny.

Skutečná API fixture pinne Spring6.2.2/Boot3.4.2 SHA-256 a license entries.
Maven preparation je explicitní CI krok, stejně jako instalace workerů;
negativní prerequisite testy zakazují subprocess a požadované chybějící/změněné
API končí FAIL, volitelný lokální běh SKIP. Nejde o Spring aplikaci ani context.

## Zadání a acceptance

[T003-S05-W03](../tasks/T003-S05-03-springConditionMatrix.md), T003-S05/T003-AC05.
Normativní dependencies S03-W04 a S04-W01 jsou sloučené. Rekognoskace ověřila,
že W01 K2 nemodeluje Kotlin třídy; Kotlin-class varianty fixture proto používají
S06-W01 compiler facts jako explicitní závislost PR32, nikoli kopii jeho implementace.
Kvůli uživatelem pozastavenému CI/fakturaci je PR navazující Draft s base větví
`feat/t003-s06-01-kotlin-jpa-access`, konkrétně heade71c622. Po sloučení PR32
se retargetuje na main a znovu ověří aktuální integrace.
Výchozí main ff26; průběžná integrace obsahuje main33dc a SourceMapping/CI změny.

| AC | Konkrétní test |
|---|---|
| AC01 | `test_profile_expressions`, `test_default_property_matches_strings_except_false`, `test_property_alias_prefix_all_names_and_case_insensitive_value`, `test_all_class_names_required_and_missing_inventory_unknown`, skutečný `test_actual_pinned_conditions_and_negated_profile_injection`, skutečný `test_actual_variant_input_and_classpath_freshness_are_isolated` |
| AC02 | `test_legacy_spring_rules_remain_readable_but_require_reinspection`, existing graph v1/v2/v3 loader regrese; aditivní context hash, žádné nové store schéma |
| AC03 | `test_unresolved_and_foreign_conditions_never_gain_activation`, `test_unresolved_compiler_class_literal_never_proves_presence_or_absence`, missing-class/typed malformed/tampered snapshot testy; required API chybí/změněno před procesem |
| AC04 | Pinned reálná API a přesně popsaná matice; final full/CI outcome níže musí být dokončen před ready |

## Skutečné kontroly

- Baseline skutečná K1 API fixture: **1 FAIL v7.01s**, reprodukované špatné
  profile/property/multiple-class výsledky. K2 baseline neměla class facts;
  nepovažuje se za pozitivní podporu Kotlin anotací.
- Čistá matice po opravách revize: **34 PASS**; profile/property/class grammar,
  malformed/unknown, snapshot tamper/legacy a required API negativní případy.
- Čisté a skutečné variant config/classpath testy: **36 PASS,2 deselected
  v34.50s**. Běh používá skutečné připravené K1/K2 workery a API; mění pouze
  explicitní A input/JAR, B context a graph store bytes zůstávají stejné.
- Finální cílená skutečná K1/K2 condition + TS-context sada po explicitní
  integraci PR32: **40 PASS v46.43s**. Včetně Kotlin-class anotací, negated
  profile injection a config/classpath isolation. Počáteční24 PASS/1 FAIL
  vzniklo kvůli chybějícím K2 class facts v baselineW01 a nepovažuje se za PASS.
- Nezávislá revize odhalila UNRESOLVED_CLASS_LITERAL jako falešnou známou
  absenci; opraveno a oba class-condition směry mají regresi. Python Unicode
  casefold se nepoužívá pro Java ignore-case důkaz; rozšíření ß/ss je UNKNOWN.
- První isolation test zachytil správné STALE, ale očekával přesnější text
  než existing provider wrapper; assertion nyní ověřuje classpath diagnostiku
  a status STALE, bez změny stávajícího provider error kontraktu.
- Finální full suite a semantic/memory/scan/check: **pending** před dokončením
  lokálního review. GitHub Actions: **NOT_RUN/BLOCKED**, všechny joby odmítá
  account billing/spendinglimit před spuštěním runneru; uživatel výslovně
  pozastavil tuto část a požaduje pokračovat další lokální implementací.
  Tento Draft není prohlášení celé T003-S05 za hotovou.

## Kompatibilita, příklad a omezení

Příklad explicitní API: `inspect_jvm(root, build_context={"spring_profiles":
["qa"], "spring_properties":{"feature.enabled":"true"},
"spring_available_classes":["java.lang.String"],
"spring_component_packages":["example"]}, publish=False)` s připraveným
classpath. Stávající CLI syntaxe se nemění; příklady a scope jsou v README a
compiler-inspection. Neexistuje automatické načítání konfigurace z prostředí.

Běžný default profil je podporován, custom default-profile policy nikoli.
Výrazy mají rozpočty256 tokenů/64 zanoření; mix operátorů potřebuje závorky.
Ne-ASCII case equivalence, dynamické placeholders, nested/collection property
values, custom/unsupported Boot conditions zůstávají UNKNOWN. Vstupní inventory
je explicitní deklarace kontextu, nikoli runtime classloader evidence. Další
registrar/factory/proxy/async rozsah se implementuje samostatně.
