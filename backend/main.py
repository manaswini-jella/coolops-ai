import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from google.cloud import firestore
from google import genai

from analysis.cost import baseline_ratio, cost_for_window
from analysis.data import load_samples
from analysis.rules import run_all
from datetime import datetime, timezone
from reporting.report import ReportError, PROMPT_VERSION, build_evidence, generate_report

app = FastAPI()

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "project-ad30097f-eac9-431b-a0f")
LOCATION = os.environ.get("GCP_REGION", "us-central1")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
TARIFF = float(os.environ.get("TARIFF_PER_KWH", "0.15"))

DATA_PATH = Path(__file__).resolve().parent / "data" / "synthetic_cooling.csv"
REFERENCE_START = "2026-10-04T00:00:00"
REFERENCE_END = "2026-10-11T23:59:59"

db = firestore.Client(project=PROJECT_ID, database="first2002")
gemini = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "coolops-api", "region": LOCATION}


@app.get("/api/firestore-test")
def firestore_test():
    doc_ref = db.collection("healthchecks").document("latest")
    doc_ref.set({"message": "hello from cloud run"})
    return {"read_back": doc_ref.get().to_dict()}


@app.get("/api/gemini-test")
def gemini_test():
    response = gemini.models.generate_content(
        model=GEMINI_MODEL,
        contents="In one sentence, what is a cooling-to-IT load ratio?",
    )
    return {"model": GEMINI_MODEL, "text": response.text}


@app.get("/api/analysis")
def analysis():
    try:
        samples = load_samples(DATA_PATH)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"Dataset error: {exc}")

    flags = run_all(samples)
    reference = [s for s in samples
                 if REFERENCE_START <= s.timestamp.isoformat() <= REFERENCE_END]
    ratio = baseline_ratio(reference)

    result = {
        "dataset": "synthetic_cooling.csv (SYNTHETIC)",
        "samples": len(samples),
        "baseline_ratio": round(ratio, 3),
        "tariff_per_kwh": TARIFF,
        "flags": [
            {
                "rule": f.rule,
                "start": f.start.isoformat(),
                "end": f.end.isoformat(),
                "evidence": f.evidence,
            }
            for f in flags
        ],
        "cost": None,
    }

    r1 = [f for f in flags if f.rule == "R1"]
    if r1:
        window = [s for s in samples if r1[0].start <= s.timestamp < r1[0].end]
        result["cost"] = cost_for_window(window, ratio, TARIFF)
    return result

@app.get("/api/telemetry")
def telemetry():
    samples = load_samples(DATA_PATH)
    return {
        "dataset": "synthetic_cooling.csv (SYNTHETIC)",
        "points": [
            {
                "t": s.timestamp.isoformat(),
                "it_kw": s.it_load_kw,
                "cooling_kw": s.cooling_power_kw,
                "inlet_c": s.inlet_temp_c,
            }
            for s in samples
        ],
    }

def _run_analysis():
    samples = load_samples(DATA_PATH)
    flags = run_all(samples)
    reference = [s for s in samples
                 if REFERENCE_START <= s.timestamp.isoformat() <= REFERENCE_END]
    ratio = baseline_ratio(reference)
    cost = None
    r1 = [f for f in flags if f.rule == "R1"]
    if r1:
        window = [s for s in samples if r1[0].start <= s.timestamp < r1[0].end]
        cost = cost_for_window(window, ratio, TARIFF)
    return samples, flags, ratio, cost


@app.post("/api/reports")
def create_report():
    try:
        samples, flags, ratio, cost = _run_analysis()
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"Analysis error: {exc}")

    evidence = build_evidence(len(samples), flags, ratio, cost, TARIFF)

    try:
        report = generate_report(gemini, GEMINI_MODEL, evidence)
    except ReportError as exc:
        raise HTTPException(status_code=502, detail={
            "error": "AI report rejected by validation",
            "reason": str(exc),
            "note": "Nothing was saved. Deterministic results remain at /api/analysis.",
        })
    except Exception as exc:
        raise HTTPException(status_code=502, detail={
            "error": "Gemini request failed",
            "reason": type(exc).__name__,
            "note": "Nothing was saved.",
        })

    doc = {
        "createdAt": datetime.now(timezone.utc),
        "datasetId": "synthetic-cooling-v1",
        "model": GEMINI_MODEL,
        "promptVersion": PROMPT_VERSION,
        "status": "ok",
        "evidence": evidence,
        "report": report,
    }
    _, ref = db.collection("reports").add(doc)
    return {"id": ref.id, "saved": True, "report": report}


@app.get("/api/reports")
def list_reports():
    docs = (db.collection("reports")
            .order_by("createdAt", direction=firestore.Query.DESCENDING)
            .limit(20).stream())
    return {"reports": [
        {"id": d.id, "createdAt": d.get("createdAt").isoformat(),
         "model": d.get("model"), "status": d.get("status")}
        for d in docs
    ]}


@app.get("/api/reports/{report_id}")
def get_report(report_id: str):
    snap = db.collection("reports").document(report_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Report not found")
    data = snap.to_dict()
    data["createdAt"] = data["createdAt"].isoformat()
    return {"id": snap.id, **data}
