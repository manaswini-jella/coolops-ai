"""Energy, excess-energy, and cost estimates under an explicit baseline."""
from .rules import INTERVAL

INTERVAL_HOURS = INTERVAL.total_seconds() / 3600
MAX_TARIFF = 10.0  # sanity cap, currency per kWh


def validate_tariff(tariff):
    if not 0 < tariff <= MAX_TARIFF:
        raise ValueError(f"tariff must be greater than 0 and at most {MAX_TARIFF}")


def baseline_ratio(reference):
    """Cooling kW per IT kW over a reference period believed to be normal."""
    if not reference:
        raise ValueError("reference period is empty")
    it_total = sum(s.it_load_kw for s in reference)
    if it_total <= 0:
        raise ValueError("reference period has no IT load")
    return sum(s.cooling_power_kw for s in reference) / it_total


def cost_for_window(window, ratio, tariff):
    validate_tariff(tariff)
    energy = sum(s.cooling_power_kw for s in window) * INTERVAL_HOURS
    excess = sum(
        max(0.0, s.cooling_power_kw - ratio * s.it_load_kw) for s in window
    ) * INTERVAL_HOURS
    return {
        "samples": len(window),
        "energy_kwh": round(energy, 1),
        "excess_kwh": round(excess, 1),
        "estimated_cost": round(excess * tariff, 2),
        "baseline_ratio": round(ratio, 3),
        "tariff_per_kwh": tariff,
        "formula": "excess = sum(max(0, cooling_kw - baseline_ratio * it_kw)) * 0.25 h",
    }
