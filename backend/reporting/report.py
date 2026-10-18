"""Evidence-grounded report generation: prompt, Gemini call, and validation."""
import json
import re

PROMPT_VERSION = "v3"
REQUIRED_KEYS = {"observed_pattern", "supporting_evidence", "hypotheses",
                 "recommended_checks", "limitations"}
BANNED_PHRASES = ["confirmed fault", "confirmed failure", "will save", "guarantee",
                  "definitely", "predicts failure", "proven waste"]
SAFE_INTEGERS = set(range(0, 32)) | {2026}   # days, hours, minutes, year
SAFE_DECIMALS = {0.25, 0.5}                  # interval hours, half-unit
NUMBER_RE = re.compile(r"(?<![\d.])-?\d+(?:\.\d+)?")
TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?|\b\d{1,2}:\d{2}(?::\d{2})?\b")
RULE_CAVEATS = {
    "R1": "Window includes samples before the change; the cost covers only this detected window.",
    "R3": "Single or short spikes can be sensor or load noise. Treat as weak evidence unless repeated.",
    "R2": "Inlet temperature threshold is illustrative, not a facility standard.",
}

PROMPT = """You are writing an investigation note for a data-center facility operator.
Rules:
- Use ONLY the facts and numbers in the EVIDENCE below. Do not invent sensor values, costs, savings, or times.
- Separate observations (what the data shows) from hypotheses (possible explanations). Never state a cause as confirmed.
- Refer to flags by their evidence_id (F1, F2, ...).
- The flag window is the window the rule detected. It may start before the first changed reading.
- Describe the cost as an estimate under the stated baseline, not measured waste.
- The data is synthetic. Say so in limitations.
- Do not use the words "confirmed fault", "will save", "guarantee", or "definitely".
- Quote only numbers that appear in EVIDENCE. Do not calculate durations, totals, or percentages. Use the provided fields such as duration_minutes.
- Each supporting_evidence item must use an evidence_id from the flags (F1, F2, ...), or COST for statements about cost, tariff, or baseline.
- The limitations list must include every caveat given in the EVIDENCE, and must say which flags are weaker evidence.
Return ONLY a JSON object with exactly these keys:
observed_pattern (string),
supporting_evidence (list of {"evidence_id": string, "statement": string}),
hypotheses (list of {"explanation": string, "what_would_distinguish_it": string}),
recommended_checks (list of strings),
limitations (list of strings).

EVIDENCE:
"""


class ReportError(Exception):
    pass

def caveat_for(rule, duration_minutes):
    if rule == "R3" and duration_minutes > 30:
        return "Sustained step rather than a single spike, so less likely to be one noisy sample."
    return RULE_CAVEATS.get(rule, "")

def build_evidence(sample_count, flags, ratio, cost, tariff):
    flag_items = []
    for i, f in enumerate(flags, start=1):
        duration = int((f.end - f.start).total_seconds() // 60)
        flag_items.append({
            "evidence_id": f"F{i}",
            "rule": f.rule,
            "start": f.start.isoformat(),
            "end": f.end.isoformat(),
            "values": {
                **f.evidence,
                "duration_minutes": duration,
                "caveat": caveat_for(f.rule, duration),
            },
        })

    return {
        "dataset": "synthetic_cooling.csv (SYNTHETIC)",
        "samples": sample_count,
        "baseline_ratio": round(ratio, 3),
        "baseline_period": "2026-10-04 to 2026-10-11",
        "tariff_per_kwh": tariff,
        "cost": cost,
        "flags": flag_items,
    }


def _collect_numbers(obj, out):
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.append(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_numbers(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect_numbers(v, out)
    return out


def _is_allowed(n, allowed_values):
    if n in SAFE_DECIMALS or (n == int(n) and int(n) in SAFE_INTEGERS):
        return True
    # Allow rounding to the nearest unit (e.g. "34" for 34.2).
    return any(abs(n - v) <= 0.55 for v in allowed_values)


def validate_report(report, evidence_ids, allowed_values):
    if not isinstance(report, dict):
        return ["report is not a JSON object"]
    missing = REQUIRED_KEYS - report.keys()
    if missing:
        return [f"missing keys: {sorted(missing)}"]

    errors = []
    if not isinstance(report["supporting_evidence"], list):
        errors.append("supporting_evidence must be a list")
    else:
        for item in report["supporting_evidence"]:
            if not isinstance(item, dict) or item.get("evidence_id") not in evidence_ids:
                errors.append(f"unknown evidence_id in {item}")

    text = json.dumps(report, ensure_ascii=False)
    lower = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lower:
            errors.append(f"banned phrase: {phrase}")
    text = TIMESTAMP_RE.sub(" ", text)  # times copied from the evidence are not new numbers
    for m in NUMBER_RE.finditer(text):
        n = m.group()
        if not _is_allowed(float(n), allowed_values):
            ctx = text[max(0, m.start() - 40): m.end() + 20]
            errors.append(f"number {n} not in evidence, near: ...{ctx}...")

    return errors[:5]


def generate_report(client, model, evidence):
    """Call Gemini, validate the output, retry once with the validation errors."""
    evidence_ids = {f["evidence_id"] for f in evidence["flags"]} | {"COST"}
    allowed_values = _collect_numbers(evidence, [])
    base_prompt = PROMPT + json.dumps(evidence, indent=2)
    last_error = "no attempt made"

    for attempt in range(2):
        prompt = base_prompt
        if attempt == 1:
            prompt += (f"\n\nYour previous answer failed validation: {last_error}. "
                       "Fix these issues and return only the JSON object.")
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"response_mime_type": "application/json", "temperature": 0.2},
        )
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", (response.text or "").strip())
        try:
            report = json.loads(raw)
        except json.JSONDecodeError as exc:
            last_error = f"invalid JSON: {exc}"
            continue
        errors = validate_report(report, evidence_ids, allowed_values)
        if not errors:
            return report
        last_error = "; ".join(errors)

    raise ReportError(last_error)
