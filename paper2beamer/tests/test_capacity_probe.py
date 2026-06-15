"""Capacity probe. Heavy: drives real XeLaTeX builds; skipped in CI by default.

Run explicitly with:  uv run pytest tests/test_capacity_probe.py -m heavy
"""
import pytest

from scripts.capacity_probe import measure, _fits, _bullets


@pytest.mark.heavy
def test_measure_returns_a_plausible_bullet_capacity():
    n = measure("Simple", "bullets_per_frame", "normal")
    # A 16:9 frame holds several representative bullets but not dozens.
    assert 3 <= n <= 16


@pytest.mark.heavy
def test_a_single_bullet_always_fits_but_many_overflow():
    assert _fits("Simple", "normal", _bullets(1)) is True
    assert _fits("Simple", "normal", _bullets(40)) is False
