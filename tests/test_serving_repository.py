from datetime import date

import pytest

from retailops_ai.serving.repository import ServingRepositoryConfig, seed_window_for_split


def test_serving_repository_table_name() -> None:
    config = ServingRepositoryConfig(
        project="retailops-ai-2026",
        location="us-central1",
        dbt_dataset="retailops",
    )
    assert config.table("ml_forecast_covariates") == (
        "retailops-ai-2026.retailops_ml.ml_forecast_covariates"
    )


def test_validation_seed_window_uses_final_train_28_days() -> None:
    split, start, end = seed_window_for_split("validation")
    assert split == "train"
    assert start == date(2016, 2, 29)
    assert end == date(2016, 3, 27)
    assert (end - start).days + 1 == 28


def test_test_seed_window_uses_validation_observations() -> None:
    split, start, end = seed_window_for_split("test")
    assert split == "validation"
    assert start == date(2016, 3, 28)
    assert end == date(2016, 4, 24)
    assert (end - start).days + 1 == 28


def test_seed_window_rejects_unknown_split() -> None:
    with pytest.raises(ValueError, match="validation or test"):
        seed_window_for_split("future")
