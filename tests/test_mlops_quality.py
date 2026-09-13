"""Tests for model promotion quality gates."""

import pytest

from retailops_ai.mlops.quality import evaluate_mean_rmsse_gate


def test_mean_rmsse_gate_passes_when_candidate_beats_baseline() -> None:
    result = evaluate_mean_rmsse_gate(0.771130, 0.952306197699721)

    assert result.passed is True
    assert result.improvement_fraction > 0


def test_mean_rmsse_gate_fails_when_candidate_does_not_beat_baseline() -> None:
    result = evaluate_mean_rmsse_gate(1.0, 0.952306197699721)

    assert result.passed is False
    assert result.improvement_fraction < 0


def test_mean_rmsse_gate_rejects_invalid_threshold() -> None:
    with pytest.raises(ValueError, match="positive"):
        evaluate_mean_rmsse_gate(0.8, 0.0)
