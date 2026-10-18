import os
from fastapi import FastAPI
from google.cloud import firestore
from google import genai

app = FastAPI()

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "project-ad30097f-eac9-431b-a0f")
db = firestore.Client(project=PROJECT_ID, database="first2002")

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "coolops-api", "region": os.environ.get("GCP_REGION", "unset")}

@app.get("/api/firestore-test")
def firestore_test():
    doc_ref = db.collection("healthchecks").document("latest")
    doc_ref.set({"message": "hello from cloud run"})
    snapshot = doc_ref.get()
    return {"read_back": snapshot.to_dict()}

LOCATION = os.environ.get("GCP_REGION", "us-central1")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
gemini = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

@app.get("/api/gemini-test")
def gemini_test():
    response = gemini.models.generate_content(
        model=GEMINI_MODEL,
        contents="In one sentence, what is a cooling-to-IT load ratio?",
    )
    return {"model": GEMINI_MODEL, "text": response.text}
