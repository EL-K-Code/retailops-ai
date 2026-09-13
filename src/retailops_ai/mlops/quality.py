"""Model quality gates used before Vertex Model Registry promotion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualityGateResult:
    passed: bool
    observed_mean_rmsse: float
    maximum_mean_rmsse: float
    improvement_fraction: float


def evaluate_mean_rmsse_gate(
    observed_mean_rmsse: float,
    maximum_mean_rmsse: float,
) -> QualityGateResult:
    """Require a candidate model to beat the configured RMSSE ceiling."""
    if observed_mean_rmsse < 0:
        raise ValueError("observed_mean_rmsse must be non-negative")
    if maximum_mean_rmsse <= 0:
        raise ValueError("maximum_mean_rmsse must be positive")

    improvement_fraction = (
        maximum_mean_rmsse - observed_mean_rmsse
    ) / maximum_mean_rmsse
    return QualityGateResult(
        passed=observed_mean_rmsse < maximum_mean_rmsse,
        observed_mean_rmsse=observed_mean_rmsse,
        maximum_mean_rmsse=maximum_mean_rmsse,
        improvement_fraction=improvement_fraction,
    )
