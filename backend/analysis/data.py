import csv
from datetime import datetime
from pathlib import Path

from .rules import Sample


def load_samples(path):
    samples = []
    with Path(path).open(newline="") as f:
        for row in csv.DictReader(f):
            samples.append(Sample(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                it_load_kw=float(row["it_load_kw"]),
                inlet_temp_c=float(row["inlet_temp_c"]),
                cooling_power_kw=float(row["cooling_power_kw"]),
            ))
    if any(s.cooling_power_kw <= 0 or s.it_load_kw <= 0 for s in samples):
        raise ValueError("cooling and IT load must be positive for every sample")
    return samples

