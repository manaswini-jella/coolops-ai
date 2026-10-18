"""Generate the synthetic CoolOps AI cooling dataset.

All values are synthetic. The output is deterministic (fixed seed), so the
same file is produced every time.

Three planted scenarios, each designed to exercise one rule:
  R1: cooling rises while IT load stays flat (12 Oct, 10:00-18:00)
  R2: inlet air stays above 27 C for about 2 hours (6 Oct, 13:00-15:30)
  R3: short, sharp cooling spike of about 45 minutes (8 Oct, 15:00-15:45)
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

BASE_COOLING_RATIO = 0.35  # cooling kW per IT kW in normal operation

# Planted scenarios (SYNTHETIC)
R1_START = dt.datetime(2026, 10, 12, 10, 0)
R1_END = dt.datetime(2026, 10, 12, 18, 0)
R1_UPLIFT = 1.30           # cooling 30% higher, IT load unchanged

R2_START = dt.datetime(2026, 10, 6, 13, 0)
R2_END = dt.datetime(2026, 10, 6, 15, 30)
R2_INLET_OFFSET_C = 5.0    # pushes inlet air above 27 C for the window

R3_START = dt.datetime(2026, 10, 8, 15, 0)
R3_END = dt.datetime(2026, 10, 8, 15, 45)
R3_UPLIFT = 1.45           # short sharp jump in cooling power

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic_cooling.csv"


def generate():
    rng = random.Random(SEED)
    rows = []
    for i in range(SAMPLES):
        ts = START + dt.timedelta(minutes=INTERVAL_MIN * i)
        hour = ts.hour + ts.minute / 60.0

        # IT load: daily cycle plus small noise.
        it_kw = 1000 + 80 * math.sin(2 * math.pi * (hour - 6) / 24) + rng.gauss(0, 12)

        # Inlet temperature: mild daily cycle plus noise.
        inlet_c = 22.0 + 1.2 * math.sin(2 * math.pi * (hour - 14) / 24) + rng.gauss(0, 0.25)

        # Cooling power follows IT load in normal operation.
        cooling_kw = it_kw * BASE_COOLING_RATIO + rng.gauss(0, 8)

        if R1_START <= ts < R1_END:
            cooling_kw *= R1_UPLIFT
        if R2_START <= ts < R2_END:
            inlet_c += R2_INLET_OFFSET_C
        if R3_START <= ts < R3_END:
            cooling_kw *= R3_UPLIFT

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
    print("Planted scenarios (SYNTHETIC):")
    print(f"  R1 {R1_START} to {R1_END}")
    print(f"  R2 {R2_START} to {R2_END}")
    print(f"  R3 {R3_START} to {R3_END}")


if __name__ == "__main__":
    main()
