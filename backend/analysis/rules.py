"""Deterministic anomaly rules for cooling telemetry.

Pure Python, no AI. Thresholds are illustrative defaults for this demo,
not calibrated values.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

INTERVAL = timedelta(minutes=15)

R1_WINDOW = 16              # 4 hours of 15-minute samples
R1_COOLING_RISE_PCT = 15.0
R1_IT_STABLE_PCT = 5.0

R2_TEMP_C = 27.0
R2_MIN_SPAN = timedelta(minutes=30)

R3_WINDOW = 24              # 6 hours of 15-minute samples
R3_MAD_MULTIPLIER = 5.0
MAD_SCALE = 1.4826          # makes MAD comparable to a standard deviation



@dataclass(frozen=True)
class Sample:
    timestamp: datetime
    it_load_kw: float
    inlet_temp_c: float
    cooling_power_kw: float


@dataclass(frozen=True)
class Flag:
    rule: str
    start: datetime
    end: datetime
    evidence: dict


def _mean(values):
    return sum(values) / len(values)


def _pct_change(new, old):
    return (new - old) / old * 100.0


def _consecutive_runs(indices):
    runs = []
    for i in indices:
        if runs and i == runs[-1][-1] + 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    return runs


def rule_r1(samples):
    """Cooling up by at least 15% versus the previous 4 hours, while IT load moves less than 5%.

    Sample i is evaluated using the 16 samples before it (current window)
    and the 16 samples before that (previous window).
    """
    w = R1_WINDOW
    hits = {}
    for i in range(2 * w, len(samples)):
        cur = samples[i - w:i]
        prev = samples[i - 2 * w:i - w]
        cool_cur = _mean([s.cooling_power_kw for s in cur])
        cool_prev = _mean([s.cooling_power_kw for s in prev])
        it_cur = _mean([s.it_load_kw for s in cur])
        it_prev = _mean([s.it_load_kw for s in prev])
        cool_pct = _pct_change(cool_cur, cool_prev)
        it_pct = _pct_change(it_cur, it_prev)
        if cool_pct >= R1_COOLING_RISE_PCT and abs(it_pct) < R1_IT_STABLE_PCT:
            hits[i] = {
                "window_start": cur[0].timestamp.isoformat(),
                "window_end": (cur[-1].timestamp + INTERVAL).isoformat(),
                "mean_cooling_kw_current": round(cool_cur, 1),
                "mean_cooling_kw_previous": round(cool_prev, 1),
                "cooling_change_pct": round(cool_pct, 1),
                "mean_it_kw_current": round(it_cur, 1),
                "mean_it_kw_previous": round(it_prev, 1),
                "it_change_pct": round(it_pct, 1),
            }

    flags = []
    for run in _consecutive_runs(sorted(hits)):
        peak = max((hits[i] for i in run), key=lambda e: e["cooling_change_pct"])
        flags.append(Flag(
            rule="R1",
            start=samples[run[0]-w].timestamp,
            end=samples[run[-1]-1].timestamp + INTERVAL,
            evidence={
                **peak,
                "window_hours": 4,
                "threshold_cooling_pct": R1_COOLING_RISE_PCT,
                "threshold_it_pct": R1_IT_STABLE_PCT,
            },
        ))
    return flags


def rule_r2(samples):
    """Inlet temperature above 27 °C for at least 30 minutes between the first and last breaching sample."""
    breach = [i for i, s in enumerate(samples) if s.inlet_temp_c > R2_TEMP_C]
    flags = []
    for run in _consecutive_runs(breach):
        first, last = run[0], run[-1]
        span = samples[last].timestamp - samples[first].timestamp
        if span < R2_MIN_SPAN:
            continue
        temps = [samples[i].inlet_temp_c for i in run]
        flags.append(Flag(
            rule="R2",
            start=samples[first].timestamp,
            end=samples[last].timestamp + INTERVAL,
            evidence={
                "max_inlet_temp_c": round(max(temps), 2),
                "breaching_samples": len(run),
                "duration_minutes": len(run) * 15,
                "threshold_c": R2_TEMP_C,
            },
        ))
    return flags


def rule_r3(samples):
    """Cooling power above median + 5 x scaled MAD of the previous 6 hours (spike detector)."""
    w = R3_WINDOW
    hits = {}
    for i in range(w, len(samples)):
        window = [s.cooling_power_kw for s in samples[i - w:i]]
        med = median(window)
        mad_scaled = median([abs(x - med) for x in window]) * MAD_SCALE
        if mad_scaled == 0:
            continue
        threshold = med + R3_MAD_MULTIPLIER * mad_scaled
        value = samples[i].cooling_power_kw
        if value > threshold:
            hits[i] = {
                "value_kw": round(value, 1),
                "baseline_median_kw": round(med, 1),
                "scaled_mad_kw": round(mad_scaled, 2),
                "threshold_kw": round(threshold, 1),
            }

    flags = []
    for run in _consecutive_runs(sorted(hits)):
        peak = max((hits[i] for i in run), key=lambda e: e["value_kw"])
        flags.append(Flag(
            rule="R3",
            start=samples[run[0]].timestamp,
            end=samples[run[-1]].timestamp + INTERVAL,
            evidence={**peak, "multiplier": R3_MAD_MULTIPLIER},
        ))
    return flags


def run_all(samples):
    return sorted(rule_r1(samples) + rule_r2(samples) + rule_r3(samples), key=lambda f: f.start)
