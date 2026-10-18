# CoolOps AI

### Find cooling that rises when the workload doesn't.

**An AI-assisted investigation tool for data-center cooling inefficiencies.**

CoolOps AI helps data-center teams identify unusual cooling-energy patterns, investigate potential operational issues, and prioritize what to check next.

It compares cooling power, IT workload, and server inlet temperature to flag suspicious periods, estimate potential excess cooling-energy costs, and generate evidence-based investigation checklists using Gemini.

> **Demo notice:** This prototype uses synthetic telemetry. Its alerts identify patterns worth investigating; they do not establish a confirmed fault or prove energy waste.

---

## Live Demo

- **Dashboard:** https://project-ad30097f-eac9-431b-a0f.web.app
- **Backend health:** https://coolops-api-699274313636.us-central1.run.app/api/health

The dashboard demonstrates the complete investigation workflow using simulated data.

---

## The Problem

Data centers depend on cooling systems to maintain safe operating conditions for servers. However, an increase in cooling-energy consumption does not always correspond to an increase in computing workload.

Identifying these mismatches can require teams to inspect multiple telemetry signals, locate unusual time periods, and determine what to investigate first.

CoolOps AI brings these steps into one workflow: **detect a suspicious pattern, inspect its evidence, estimate its potential energy cost, and generate a checklist for further investigation.**

## What CoolOps AI Does

### 1. Monitor operational signals

Explore 14 days of simulated telemetry, including:

- Cooling-system power consumption
- IT load, representing computing workload
- Server inlet-air temperature

Interactive time-series charts help users compare signals and investigate specific time windows.

### 2. Detect patterns worth investigating

CoolOps AI applies three deterministic checks:

| Rule | What it looks for |
|---|---|
| **R1 — Cooling/workload mismatch** | Cooling power increases by at least 15% over a four-hour comparison while IT load changes by less than 5%. |
| **R2 — High inlet temperature** | Inlet temperature exceeds 27°C for at least 30 minutes. |
| **R3 — Cooling-power spike** | Cooling power rises substantially above its recent baseline, using a median-and-MAD-based threshold. |

These are configurable starting assumptions for the prototype, not universal operating limits.

### 3. Estimate potential energy cost

For a detected cooling/workload mismatch, the dashboard estimates excess cooling energy relative to a reference baseline and translates it into an illustrative electricity cost.

The estimate depends on the selected period, baseline assumptions, and electricity tariff. It is an analytical estimate—not a measurement of verified energy waste or achievable savings.

### 4. Generate an AI-assisted investigation checklist

Gemini turns the computed findings into a structured report containing:

- Observed patterns
- Supporting evidence
- Possible explanations to investigate
- Recommended checks for the operations team
- Limitations and uncertainty

The backend validates the generated response before saving it. The AI is intended to help interpret the evidence, not independently establish a fault or invent measured savings.

### 5. Save and revisit reports

Generated investigation reports are stored in Cloud Firestore so they can be retrieved later.

---

## How It Works

CoolOps AI separates numerical analysis from AI-generated interpretation.

1. **Telemetry analysis:** Python applies the detection rules to the simulated readings.
2. **Energy estimation:** Deterministic calculations estimate excess cooling energy and cost against the chosen baseline.
3. **AI interpretation:** Gemini receives the calculated findings and supporting evidence to draft an investigation checklist.
4. **Report validation:** The backend checks the generated response before accepting it.
5. **Report storage:** Firestore stores reports for later retrieval.

This separation makes the numerical results easier to inspect and verify independently of the AI-generated recommendations.

## Built with Google Cloud

| Technology | Role in the project |
|---|---|
| **Gemini via Vertex AI** | Generates evidence-based investigation checklists. |
| **Cloud Run** | Hosts the Python backend and analysis API. |
| **Cloud Firestore** | Stores and retrieves investigation reports. |
| **Firebase Hosting** | Serves the dashboard and routes API requests to the backend. |

### Architecture

```text
                 User
                  |
                  v
          Firebase Hosting
          Dashboard + API routing
                  |
                  v
             Cloud Run
            Python backend
                  |
          +-------+--------+
          |       |        |
          v       v        v
       Analysis  Gemini  Firestore
       & energy  report  Saved reports
       estimates generation
```

## Project Structure

```text
coolops-ai/
├── backend/
│   ├── analysis/      # Detection rules and energy calculations
│   ├── reporting/    # Gemini integration and response validation
│   ├── data/         # Synthetic telemetry dataset
│   ├── scripts/      # Dataset generation and analysis
│   ├── tests/        # Automated tests
│   └── main.py       # API entry point
├── frontend/
│   └── public/       # Dashboard assets
└── README.md
```

## Run the Tests

The backend tests cover the detection logic and energy calculations.

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install pytest
PYTHONPATH=. python -m pytest -v
```

Install the project's full backend dependencies as specified in its dependency file before running the application or integration tests.

## Rebuild the Demo Dataset

From the repository root:

```bash
cd backend
PYTHONPATH=. python3 scripts/generate_dataset.py
PYTHONPATH=. python3 scripts/run_analysis.py
```

These scripts regenerate the synthetic telemetry and run the analysis pipeline.

## Deployment

The application uses Firebase Hosting for the frontend and Cloud Run for the backend.

Prerequisites include:

- A Google Cloud project with billing enabled
- The required Google Cloud APIs and Vertex AI access
- Firebase configured for the project
- Google Cloud CLI and Firebase CLI installed and authenticated

Deploy the backend from the `backend/` directory:

```bash
gcloud run deploy coolops-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --max-instances=2 \
  --set-env-vars GCP_REGION=us-central1,GEMINI_MODEL=gemini-2.5-flash
```

Deploy the frontend from the directory containing `firebase.json`:

```bash
firebase deploy --only hosting
```

The backend uses environment variables for project configuration, region, model selection, and electricity tariff. Keep credentials out of source control and configure service-account permissions according to the deployment requirements.

**Note:** These commands describe the deployment setup; successful deployment depends on the project's actual configuration, IAM permissions, enabled APIs, and dependency files.

## Limitations

- **Synthetic telemetry:** The current demonstration does not use live data from a real data center.
- **Uncalibrated thresholds:** Detection thresholds require validation against real facility operating conditions.
- **Baseline-dependent estimates:** Excess energy and cost depend on the chosen reference period and electricity tariff.
- **No confirmed diagnosis:** A flag indicates an unusual pattern, not a proven equipment fault or verified energy loss.
- **Potential noisy detections:** An isolated cooling spike may reflect noise or a transient event.
- **No water-use analysis:** The current prototype focuses on cooling electricity.
- **AI uncertainty:** Generated explanations are suggestions for investigation and require operational verification.

## Future Directions

- Integrate live telemetry from data-center monitoring systems.
- Validate detection rules against real operational datasets.
- Allow operators to configure thresholds, baselines, and electricity tariffs.
- Support CSV uploads and facility-specific analysis.
- Add notifications and investigation-history workflows.
- Extend analysis to water consumption where suitable measurements are available.
