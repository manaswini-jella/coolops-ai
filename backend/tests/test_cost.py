from datetime import datetime, timedelta

import pytest

from analysis.cost import baseline_ratio, cost_for_window
from analysis.rules import Sample

T0 = datetime(2026, 10, 12)


def build(cooling, it=1000.0):
    return [Sample(T0 + timedelta(minutes=15 * i), it, 22.0, c) for i, c in enumerate(cooling)]


def test_cost_matches_hand_calculation():
    # Reference: 4 samples at 350 kW cooling with 1000 kW IT, so ratio = 0.35.
    # Flagged: 4 samples at 455 kW cooling (1 hour total at 0.25 h each).
    # Energy = 455 kW * 0.25 h * 4 = 455 kWh.
    # Excess per sample = 455 - 350 = 105 kW, so excess = 105 * 0.25 * 4 = 105 kWh.
    # Cost at 0.10 per kWh = 10.50.
    ratio = baseline_ratio(build([350.0] * 4))
    result = cost_for_window(build([455.0] * 4), ratio, tariff=0.10)
    assert result["baseline_ratio"] == pytest.approx(0.35)
    assert result["energy_kwh"] == pytest.approx(455.0)
    assert result["excess_kwh"] == pytest.approx(105.0)
    assert result["estimated_cost"] == pytest.approx(10.5)


def test_tariff_must_be_positive():
    with pytest.raises(ValueError):
        cost_for_window(build([350.0]), 0.35, tariff=0)
