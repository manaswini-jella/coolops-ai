from datetime import datetime, timedelta

import pytest

from analysis.rules import INTERVAL, Sample, rule_r1, rule_r2, rule_r3

START = datetime(2026, 10, 12, 0, 0)


def build(cooling, it=None, inlet=None):
    n = len(cooling)
    it = it or [1000.0] * n
    inlet = inlet or [22.0] * n
    return [
        Sample(START + i * INTERVAL, it[i], inlet[i], cooling[i])
        for i in range(n)
    ]


# R1: cooling rises while IT load is stable
def test_r1_flat_data_has_no_flags():
    assert rule_r1(build([100.0] * 48)) == []


def test_r1_flags_cooling_step_with_stable_it():
    # Cooling steps from 100 to 150 at index 32 (+50%); IT stays at 1000 kW.
    cooling = [100.0] * 32 + [150.0] * 16
    samples = build(cooling)
    flags = rule_r1(samples)
    # Hand check: the first window with >= 15% rise is indices 21-36 (+15.6%),
    # so the first triggered comparison is index 37. Every later comparison also triggers.
    assert len(flags) == 1
    assert flags[0].rule == "R1"
    assert flags[0].start == samples[21].timestamp
    assert flags[0].end == samples[47].timestamp


def test_r1_ignores_rise_when_it_load_also_rises():
    # Same cooling step, but IT load rises from 1000 to 1200 kW at index 32.
    cooling = [100.0] * 32 + [150.0] * 16
    it = [1000.0] * 32 + [1200.0] * 16
    assert rule_r1(build(cooling, it=it)) == []


# R2: inlet temperature above 27 °C for at least 30 minutes
def test_r2_flags_sustained_breach():
    inlet = [22.0] * 48
    for i in range(10, 15):  # 5 samples = 60 minutes
        inlet[i] = 28.0
    samples = build([100.0] * 48, inlet=inlet)
    flags = rule_r2(samples)
    assert len(flags) == 1
    assert flags[0].start == samples[10].timestamp
    assert flags[0].end == samples[14].timestamp + INTERVAL


def test_r2_ignores_short_breach():
    inlet = [22.0] * 48
    inlet[20] = 28.0
    inlet[21] = 28.0  # 2 samples = 15 minutes between first and last
    assert rule_r2(build([100.0] * 48, inlet=inlet)) == []


# R3: single-sample spike
def test_r3_flags_single_spike():
    pattern = [100.0, 101.0, 99.0, 100.0, 102.0, 98.0, 100.0, 101.0]
    cooling = [pattern[i % 8] for i in range(40)]
    cooling[24] = 200.0
    samples = build(cooling)
    flags = rule_r3(samples)
    assert len(flags) == 1
    assert flags[0].start == samples[24].timestamp
    assert flags[0].end == samples[24].timestamp + INTERVAL
