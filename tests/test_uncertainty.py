from retailops_ai.decision.uncertainty import poisson_predictive_band


def test_poisson_band_contains_point_forecast() -> None:
    result = poisson_predictive_band(
        [
            {"horizon": 1, "prediction": 4.0},
            {"horizon": 2, "prediction": 9.0},
        ]
    )

    assert result["total_lower"] <= result["total_prediction"]
    assert result["total_prediction"] <= result["total_upper"]
    assert len(result["points"]) == 2
    for point in result["points"]:
        assert point["lower"] <= point["prediction"] <= point["upper"]
