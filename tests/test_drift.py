from retailops_ai.monitoring.drift import demand_distribution_drift


def test_drift_report_flags_large_shift() -> None:
    reference = [10.0, 11.0, 9.0, 10.0, 12.0, 8.0, 10.0, 11.0, 9.0, 10.0]
    current = [30.0, 31.0, 29.0, 32.0, 28.0, 30.0, 31.0, 29.0, 30.0, 32.0]

    report = demand_distribution_drift(reference, current)

    assert report["psi"] > 0.25
    assert report["status"] == "shifted"


def test_drift_report_is_stable_for_identical_samples() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0] * 3

    report = demand_distribution_drift(values, values)

    assert report["psi"] == 0.0
    assert report["status"] == "stable"
