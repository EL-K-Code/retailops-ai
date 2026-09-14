"""Tests for quality-gated registration of existing training artifacts."""

import pytest

import vertex.promote_artifact as promotion


class _FakeModel:
    resource_name = "projects/test/locations/us-central1/models/retailops-lightgbm-global"
    version_id = "2"


def test_promote_artifact_registers_passing_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        promotion,
        "load_json_from_gcs",
        lambda _: {"mean_rmsse": 0.771129690525957, "mae": 1.0767822649602548},
    )
    captured: dict[str, object] = {}

    def fake_register_model(**kwargs: object) -> _FakeModel:
        captured.update(kwargs)
        return _FakeModel()

    monkeypatch.setattr(promotion, "register_model", fake_register_model)

    result = promotion.promote_artifact(
        project="retailops-ai-2026",
        region="us-central1",
        artifact_uri="gs://models/cloudrun-training/run/model",
        display_name="retailops-lightgbm-global",
        model_id="retailops-lightgbm-global",
        version_alias="candidate",
        run_name="lightgbm-v1-test",
        serving_image_uri="us-central1-docker.pkg.dev/test/repo/serving:v1",
        maximum_mean_rmsse=0.952306197699721,
    )

    assert result["mean_rmsse"] == pytest.approx(0.771129690525957)
    assert result["quality_gate_improvement_fraction"] > 0
    assert result["model_version"] == "2"
    assert captured["artifact_uri"] == "gs://models/cloudrun-training/run/model"
    assert captured["run_name"] == "lightgbm-v1-test"


def test_promote_artifact_does_not_register_failing_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        promotion,
        "load_json_from_gcs",
        lambda _: {"mean_rmsse": 1.1321411419251513},
    )
    registered = False

    def fake_register_model(**_: object) -> _FakeModel:
        nonlocal registered
        registered = True
        return _FakeModel()

    monkeypatch.setattr(promotion, "register_model", fake_register_model)

    with pytest.raises(promotion.PromotionRejectedError, match="did not beat"):
        promotion.promote_artifact(
            project="retailops-ai-2026",
            region="us-central1",
            artifact_uri="gs://models/cloudrun-training/smoke/model",
            display_name="retailops-lightgbm-global",
            model_id="retailops-lightgbm-global",
            version_alias="candidate",
            run_name="lightgbm-v1-smoke",
            serving_image_uri="us-central1-docker.pkg.dev/test/repo/serving:v1",
            maximum_mean_rmsse=0.952306197699721,
        )

    assert registered is False


def test_evaluate_artifact_quality_requires_mean_rmsse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(promotion, "load_json_from_gcs", lambda _: {"mae": 1.0})

    with pytest.raises(ValueError, match="missing mean_rmsse"):
        promotion.evaluate_artifact_quality(
            artifact_uri="gs://models/cloudrun-training/run/model",
            maximum_mean_rmsse=0.952306197699721,
        )
