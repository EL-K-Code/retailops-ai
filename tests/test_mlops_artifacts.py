"""Tests for MLOps artifact URI helpers."""

import pytest

from retailops_ai.mlops.artifacts import split_gcs_uri


@pytest.mark.parametrize(
    ("uri", "expected"),
    [
        ("gs://retailops-models", ("retailops-models", "")),
        (
            "gs://retailops-models/vertex-training/run-001/model/",
            ("retailops-models", "vertex-training/run-001/model"),
        ),
    ],
)
def test_split_gcs_uri(uri: str, expected: tuple[str, str]) -> None:
    assert split_gcs_uri(uri) == expected


def test_split_gcs_uri_rejects_non_gcs_uri() -> None:
    with pytest.raises(ValueError, match="gs://"):
        split_gcs_uri("local-model-path")
