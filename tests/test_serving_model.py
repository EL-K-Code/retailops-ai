from retailops_ai.serving.model import LoadedForecastModel


class DummyBooster:
    pass


def test_model_summary_only_exposes_selected_metadata() -> None:
    model = LoadedForecastModel(
        booster=DummyBooster(),  # type: ignore[arg-type]
        category_levels={},
        metadata={
            "model_name": "lightgbm_global",
            "model_version": "v1",
            "run_name": "run-1",
            "mean_rmsse": 0.77,
            "artifact_uri": "gs://private-bucket/path",
            "category_levels": {"item_id": ["A"]},
        },
    )
    summary = model.summary()
    assert summary["run_name"] == "run-1"
    assert "artifact_uri" not in summary
    assert "category_levels" not in summary
