"""Deterministic bilingual reports; never upgrade agent inference into a fact."""
from __future__ import annotations

import json

from .feature import REPORT_MARKER

HEADINGS = {
    "cs": ["Business cíl a rozsah", "Stav analýzy, baseline a pokrytí", "Existující schopnosti a omezení",
           "Požadovaná data", "Co dodat a kdo rozhoduje", "Navržené změny podle vrstev", "Cesty dopadu a nejistoty",
           "Varianty a předpoklady", "Akceptační kritéria a plán testů", "Otevřené otázky", "Evidence a pending práce"],
    "en": ["Business goal and scope", "Analysis status, baseline and coverage", "Existing capabilities and limitations",
           "Required data", "Data delivery and decisions", "Proposed changes by layer", "Impact paths and uncertainty",
           "Alternatives and assumptions", "Acceptance criteria and test plan", "Open questions", "Evidence and pending work"],
}


def cell(value):
    if value is None or value == []:
        return "UNKNOWN"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("\n", " / ").replace("\r", "")


def render_report(candidate: dict, packet: dict, stale: list[str], applied: bool = True, *, data_audit: dict | None = None) -> str:
    cs = candidate["language"] == "cs"
    headings = HEADINGS[candidate["language"]]
    lines = [REPORT_MARKER, f"# Feature: {cell(candidate['analysis_id'])}", ""]
    if stale:
        lines += ["> STALE — " + ("Závěry nejsou aktuálně ověřené. Historické stavy dostupnosti nejsou platným potvrzením." if cs else "Conclusions are not currently verified. Historical availability is not a current confirmation."), ""]
    if not applied:
        lines += ["> " + ("Návrh analýzy dosud nebyl aplikován." if cs else "Analysis candidate has not been applied."), ""]
    def section(index):
        lines.extend([f"## {index + 1}. {headings[index]}", ""])
    def objects(items):
        if not items:
            lines.extend(["—", ""])
        for item in items:
            lines.extend([f"- **{cell(item.get('id', ''))}**: " + "; ".join(f"{cell(k)}: {cell(v)}" for k, v in sorted(item.items()) if k != "id"), ""])
    section(0)
    lines += [cell(packet["requirement"]), ""]
    objects(candidate["requirements"])
    section(1)
    lines += [f"- Revision: {candidate['revision']}", f"- Packet: `{candidate['packet_id']}`",
              f"- Processing: {candidate['completion']['processing_status']}",
              f"- Decision readiness: {candidate['completion']['decision_readiness']}",
              f"- Git: `{candidate['baseline']['git_commit'] or 'UNAVAILABLE'}`",
              f"- Working tree: `{candidate['baseline']['working_tree_fingerprint']}`",
              f"- Graph: `{candidate['baseline']['graph_fingerprint']}`", ""]
    for key, value in sorted(candidate["coverage"].items()):
        lines += [f"- {key}: {cell(value)}"]
    lines += [""]
    for reason in stale:
        lines += [f"- STALE: {cell(reason)}"]
    section(2)
    objects(candidate["capability_matches"])
    section(3)
    lines += [("| Vstup | Definice | Typ / jednotka | Granularita / čas | Dostupnost | Zdroj | Transformace | Evidence | Další krok |" if cs else
               "| Input | Definition | Type / unit | Granularity / time | Availability | Source | Transformation | Evidence | Next step |"),
              "|---|---|---|---|---|---|---|---|---|"]
    for item in candidate["input_requirements"]:
        values = [item["name"], item["definition"], [item["data_type"], item["unit"], item["currency"]],
                  [item["granularity"], item["as_of"], item["horizon"], item["freshness"]],
                  "STALE (historical: " + item["availability"] + ")" if stale else item["availability"],
                  item["source_ids"], item["transformation"], item["evidence_ids"], item["next_step"]]
        lines += ["| " + " | ".join(cell(v) for v in values) + " |"]
    lines += [""]
    section(4)
    lines += ["| " + ("Položka | Konkrétní zadání / rozhodnutí | Role |" if cs else "Item | Delivery / decision | Role |"), "|---|---|---|"]
    for item in candidate["input_requirements"]:
        detail = {key: item[key] for key in ("definition", "keys", "unit", "as_of", "freshness", "verification_scope", "next_step")}
        lines += [f"| {cell(item['name'])} | {cell(detail)} | {cell(item['owner_role'])} |"]
    for q in candidate["questions"]:
        lines += [f"| {cell(q['id'])} | {cell(q['text'])} | {cell(q['owner_role'])} |"]
    lines += [""]
    if data_audit is not None or candidate['input_requirements']:
        lines += ["### " + ("Co zatím nelze ověřit nástrojem" if cs else "What the tool cannot verify yet"), "",
                  ("| Vstup / rozsah | Omezení nástroje | Důvod |" if cs else "| Input / scope | Tool limitation | Reason |"),
                  "|---|---|---|"]
        gaps = data_audit['coverage_gaps'] if data_audit is not None else [
            {'kind': 'PARSER_ACCESS', 'reason': reason} for reason in candidate['coverage']['limitations']]
        if data_audit is None:
            gaps += [{'input_id': item['id'], 'kind': 'UNVERIFIED_AVAILABILITY',
                      'reason': 'UNKNOWN is not proof of a missing or populated business value.'}
                     for item in candidate['input_requirements'] if item['availability'] == 'UNKNOWN']
        for gap in gaps:
            lines += ["| " + " | ".join(cell(v) for v in (
                gap.get("input_id"), gap["kind"], gap.get("reason", gap.get("details")))) + " |"]
        lines += ["", ("Nejistota nástroje neprokazuje chybějící business data." if cs else
                       "Tool uncertainty does not prove missing business data."), ""]
    section(5)
    objects(candidate["changes"])
    objects(candidate["proposal"]["nodes"])
    objects(candidate["proposal"]["edges"])
    section(6)
    objects(candidate["impact_paths"])
    lines += ["Paths cover supported static dependencies only; missing paths do not prove absence." if not cs else "Cesty pokrývají jen podporované statické závislosti; nenalezená cesta neprokazuje neexistenci.", ""]
    section(7)
    objects(candidate["alternatives"])
    objects(candidate["assumptions"])
    section(8)
    objects(candidate["acceptance_criteria"])
    objects(candidate["test_plan"])
    section(9)
    objects(candidate["questions"])
    section(10)
    for item in candidate["evidence"]:
        location = item.get("location", {})
        label = item.get("path", item.get("decision_id", "requirement"))
        if location.get("type") == "lines":
            label += f":{location['start']}"
        elif location.get("type") == "json_pointer":
            label += "#" + location["pointer"]
        lines += [f"- `{cell(item['id'])}` — `{cell(label)}` — SHA-256 `{item.get('sha256', 'N/A')}` — {cell(item['supports'])} — {item['method']}/{('STALE' if stale else item['validity'])}"]
    lines += [""] + ["- " + cell(p) for p in candidate["completion"]["pending"]] + [""]
    return "\n".join(lines)
