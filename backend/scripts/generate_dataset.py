"""Generate the synthetic CoolOps AI cooling dataset.

All values are synthetic. The output is deterministic (fixed seed), so the
same file is produced every time.
"""
import csv
import datetime as dt
import math
import random
from pathlib import Path

SEED = 42
START = dt.datetime(2026, 10, 4, 0, 0)
INTERVAL_MIN = 15
DAYS = 14
SAMPLES = DAYS * 24 * 60 // INTERVAL_MIN  # 1344

# Planted anomaly: cooling power is raised while IT load stays stable.
ANOMALY_START = dt.datetime(2026, 10, 12, 10, 0)
ANOMALY_END = dt.datetime(2026, 10, 12, 18, 0)
ANOMALY_UPLIFT = 1.30  # cooling is 30% above its normal relationship to IT load

BASE_COOLING_RATIO = 0.35  # cooling kW per IT kW in normal operation

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic_cooling.csv"


def generate():
    rng = random.Random(SEED)
    rows = []
    for i in range(SAMPLES):
        ts = START + dt.timedelta(minutes=INTERVAL_MIN * i)
        hour = ts.hour + ts.minute / 60.0

        # IT load: daily cycle plus small noise. Stable across the anomaly window.
        it_kw = 1000 + 80 * math.sin(2 * math.pi * (hour - 6) / 24) + rng.gauss(0, 12)

        # Inlet temperature: mild daily cycle plus noise.
        inlet_c = 22.0 + 1.2 * math.sin(2 * math.pi * (hour - 14) / 24) + rng.gauss(0, 0.25)

        # Cooling power follows IT load in normal operation.
        cooling_kw = it_kw * BASE_COOLING_RATIO + rng.gauss(0, 8)
        flagged_period = ANOMALY_START <= ts < ANOMALY_END
        if flagged_period:
            cooling_kw *= ANOMALY_UPLIFT

        rows.append({
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S"),
            "it_load_kw": round(it_kw, 1),
            "inlet_temp_c": round(inlet_c, 2),
            "cooling_power_kw": round(cooling_kw, 1),
        })
    return rows


def main():
    rows = generate()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "it_load_kw", "inlet_temp_c", "cooling_power_kw"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT_PATH}")
    print(f"Planted anomaly window: {ANOMALY_START} to {ANOMALY_END} (SYNTHETIC)")


if __name__ == "__main__":
    main()
