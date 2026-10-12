<!-- kgmaker-feature-report:v1 -->
# Feature: additional-hedge

## 1. Business cíl a rozsah

Doporuč klientovi dodatečné FX zajištění tak, aby očekávaná expozice v pesimistickém scénáři nepřesáhla 20 % disponibilních prostředků. Zohledni externí bankovní pozice a zobraz doporučení v UI i PDF. / 

- **analysis:additional-hedge:requirement:goal**: kind: Goal; source_quote: Doporuč klientovi dodatečné FX zajištění tak, aby očekávaná expozice v pesimistickém scénáři nepřesáhla 20 % disponibilních prostředků. Zohledni externí bankovní pozice a zobraz doporučení v UI i PDF. / ; status: OPEN_QUESTION; text: Doporuč klientovi dodatečné FX zajištění tak, aby očekávaná expozice v pesimistickém scénáři nepřesáhla 20 % disponibilních prostředků. Zohledni externí bankovní pozice a zobraz doporučení v UI i PDF.

## 2. Stav analýzy, baseline a pokrytí

- Revision: 1
- Packet: `43ae329381d2eb32a1a9e40fef4ec804b237952bd0743506dd2ab41e666bca71`
- Processing: PARTIAL
- Decision readiness: BLOCKED
- Git: `UNAVAILABLE`
- Working tree: `e4a17fda1a206a5faf6bcf84db33462bf194d84335d29a6084ce250079c729f1`
- Graph: `6441d6adb6858694a35665f390b947a99601c17584a6a491b2e7a49a778394a0`

- artifacts: ["README.md", "backend/ExposureService.kt", "backend/ScenarioCalculator.kt", "contracts/positions-event.json", "expected/analysis-invariants.json", "expected/candidate-invalid.json", "expected/candidate-valid.json", "requirements/additional-hedge-answers.json", "requirements/additional-hedge.md"]
- dataflow_diagnostics: UNKNOWN
- excluded_directories: [".git", ".gradle", ".hg", ".idea", ".kgmaker", ".next", ".nuxt", ".svn", ".venv", ".vscode", "__pycache__", "build", "coverage", "dist", "env", "node_modules", "out", "target", "vendor", "venv", "hidden directories", "docs/generated/features/"]
- exclusions: UNKNOWN
- included_sources: ["README.md", "backend/ExposureService.kt", "backend/ScenarioCalculator.kt", "contracts/positions-event.json", "expected/analysis-invariants.json", "expected/candidate-invalid.json", "expected/candidate-valid.json", "requirements/additional-hedge-answers.json", "requirements/additional-hedge.md"]
- limitations: ["Structural fields and supported local Kotlin dependencies; no runtime availability proof.", "No XLSX, template data-flow, or complete interprocedural parser in this milestone.", "Only the supplied repository root is covered; external systems are not inspected."]
- omitted_sources: UNKNOWN
- parser_capabilities: {"data_flow": {"fields": ["Kotlin primary constructor val/var", "Java records and simple fields", "TypeScript interface/type properties", "JSON Schema/OpenAPI JSON properties"], "unsupported": ["overloaded/interprocedural calls", "control-flow-dependent mappings", "dynamic SQL", "OpenAPI YAML fields", "Kafka payload resolution", "frontend binding", "template binding"], "value_flow": ["Kotlin expression functions with explicit parameter/return types", "local numeric/property expressions", "unambiguous Kotlin constructor mapping"], "version": "dataflow-1"}, "structural": "feature-inventory-2", "workbooks": false}
- pending: UNKNOWN
- roots: ["."]
- unsupported_sources: UNKNOWN

## 3. Existující schopnosti a omezení

—

## 4. Požadovaná data

| Vstup | Definice | Typ / jednotka | Granularita / čas | Dostupnost | Zdroj | Transformace | Evidence | Další krok |
|---|---|---|---|---|---|---|---|---|
| Disponibilní prostředky | UNKNOWN | [null, null, null] | [null, null, null, null] | UNKNOWN | UNKNOWN | UNKNOWN | ["analysis:additional-hedge:evidence:balance"] | Definovat rezervované prostředky, klíč klienta, měnu a časový okamžik; dodat zdroj a cestu naplnění. |

## 5. Co dodat a kdo rozhoduje

| Položka | Konkrétní zadání / rozhodnutí | Role |
|---|---|---|
| Disponibilní prostředky | {"as_of": null, "definition": null, "freshness": null, "keys": null, "next_step": "Definovat rezervované prostředky, klíč klienta, měnu a časový okamžik; dodat zdroj a cestu naplnění.", "unit": null, "verification_scope": "Dodaný backend a kontrakt externích pozic. Frontend, PDF a zdroj rezervací nebyly dodány."} | Business analytik |
| analysis:additional-hedge:question:liquidity | Co zahrnují disponibilní prostředky a odkud přicházejí rezervace? | Business analytik |

## 6. Navržené změny podle vrstev

- **analysis:additional-hedge:change:recommendation**: dependency_ids: ["analysis:additional-hedge:question:liquidity"]; entity_ids: ["proposal:additional-hedge:recommendation"]; inputs: Definovaná likvidita a externí pozice včetně potřebné splatnosti.; layer: backend; outputs: Doporučené zajištění; navrhovaný kontrakt pro UI a PDF je nutné upřesnit.; reason: Nový požadavek na doporučení dodatečného zajištění.; requirement_ids: ["analysis:additional-hedge:requirement:goal"]; state: TO_BE; test_impact: Navrhnout akceptační scénáře po schválení definic.

- **proposal:additional-hedge:recommendation**: description: Navržená metrika; výpočet není implementovaný ani businessově schválený.; kind: Calculation; name: Doporučení zajištění; state: TO_BE

- ****: kind: requires_input; source: proposal:additional-hedge:recommendation; state: TO_BE; target: analysis:additional-hedge:input:liquidity

## 7. Cesty dopadu a nejistoty

- **analysis:additional-hedge:impact:scenario-report**: edges: [{"confidence": "EXTRACTED", "confidence_score": 1.0, "evidence": "input.pessimisticDecline / 2", "kind": "derived_from", "source": "local_value:backend/ScenarioCalculator.kt:ScenarioCalculator.calculate(input: ScenarioInput):midDecline", "source_file": "backend/ScenarioCalculator.kt", "source_line": 5, "target": "data_field:backend/ScenarioCalculator.kt:ScenarioInput.pessimisticDecline"}, {"confidence": "EXTRACTED", "confidence_score": 1.0, "evidence": "ScenarioReport(midDecline)", "kind": "maps_to", "source": "local_value:backend/ScenarioCalculator.kt:ScenarioCalculator.calculate(input: ScenarioInput):midDecline", "source_file": "backend/ScenarioCalculator.kt", "source_line": 6, "target": "data_field:backend/ScenarioCalculator.kt:ScenarioReport.midDecline"}]; entity_ids: ["data_field:backend/ScenarioCalculator.kt:ScenarioInput.pessimisticDecline", "local_value:backend/ScenarioCalculator.kt:ScenarioCalculator.calculate(input: ScenarioInput):midDecline", "data_field:backend/ScenarioCalculator.kt:ScenarioReport.midDecline"]; evidence_ids: ["analysis:additional-hedge:evidence:scenario"]; unresolved_boundary: UNKNOWN; weakest_confidence: EXTRACTED

Cesty pokrývají jen podporované statické závislosti; nenalezená cesta neprokazuje neexistenci.

## 8. Varianty a předpoklady

- **analysis:additional-hedge:alternative:no-new-api**: constraints: Bez nového externího API; klientské zadání dat je pouze návrh.; limitations: Existence současného zdroje rezervací ani splatností není ověřena.; name: no-new-api; proposal_ids: ["proposal:additional-hedge:recommendation"]; question_ids: ["analysis:additional-hedge:question:liquidity"]; requirement_ids: ["analysis:additional-hedge:requirement:goal"]

—

## 9. Akceptační kritéria a plán testů

- **analysis:additional-hedge:acceptance:boundaries**: requirement_ids: ["analysis:additional-hedge:requirement:goal"]; text: Chybějící definice a nepokryté systémy se zobrazí jako neověřené vstupy.

- **analysis:additional-hedge:test:unknown**: entity_ids: UNKNOWN; evidence_ids: UNKNOWN; requirement_ids: ["analysis:additional-hedge:requirement:goal"]; state: TO_BE; text: Nový test odmítne doporučení bez definované likvidity.

## 10. Otevřené otázky

- **analysis:additional-hedge:question:liquidity**: blocking: True; owner_role: Business analytik; requirement_ids: ["analysis:additional-hedge:requirement:goal"]; status: OPEN; text: Co zahrnují disponibilní prostředky a odkud přicházejí rezervace?

## 11. Evidence a pending práce

- `analysis:additional-hedge:evidence:balance` — `backend/ExposureService.kt:3` — SHA-256 `e4c0a3bce8d0c85697bc6ff569ad912df33a739f1b71b963d27de04ef53adc43` — Deklarace zůstatku účtu; neprokazuje shodnou definici disponibilních prostředků. — EXTRACTED/VALID
- `analysis:additional-hedge:evidence:scenario` — `backend/ScenarioCalculator.kt:5` — SHA-256 `56dc0419deb5b2ef99aec251fa7f584ee9c1aba0d0d857d77a1b60792e9e67bd` — Explicitní statická závislost a mapování do reportového pole, nikoli důkaz finanční správnosti. — EXTRACTED/VALID

- Ověřit datové cesty; doplnit frontend a PDF kontrakty.
