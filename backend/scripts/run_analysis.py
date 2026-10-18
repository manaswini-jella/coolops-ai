"""Run the deterministic rules and cost estimate on the synthetic dataset."""
from pathlib import Path

from analysis.cost import baseline_ratio, cost_for_window
from analysis.data import load_samples
from analysis.rules import run_all

DATA = Path(__file__).resolve().parent.parent / "data" / "synthetic_cooling.csv"
TARIFF = 0.15  # currency per kWh, synthetic assumption
REFERENCE_START = "2026-10-04T00:00:00"
REFERENCE_END = "2026-10-11T23:59:59"


def main():
    samples = load_samples(DATA)
    print(f"Loaded {len(samples)} samples from {DATA.name} (SYNTHETIC)")

    flags = run_all(samples)
    print(f"\nFlags: {len(flags)}")
    for f in flags:
        print(f"  {f.rule}  {f.start.isoformat()} -> {f.end.isoformat()}")
        for k, v in f.evidence.items():
            print(f"      {k}: {v}")

    reference = [s for s in samples
                 if REFERENCE_START <= s.timestamp.isoformat() <= REFERENCE_END]
    ratio = baseline_ratio(reference)
    print(f"\nBaseline (reference period 2026-10-04 to 2026-10-11): ratio = {ratio:.3f}")

    r1 = [f for f in flags if f.rule == "R1"]
    if r1:
        window = [s for s in samples if r1[0].start <= s.timestamp < r1[0].end]
        cost = cost_for_window(window, ratio, TARIFF)
        print(f"\nCost estimate for first R1 window at tariff {TARIFF}/kWh:")
        for k, v in cost.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
