"""Tests for immutable M5 uploads to the GCS landing zone."""

from pathlib import Path

import pytest

from retailops_ai.ingestion.gcs_landing import (
    LandingObjectConflictError,
    sha256_file,
    upload_immutable_file,
)


class FakeBlob:
    def __init__(self, exists: bool, metadata: dict[str, str] | None = None) -> None:
        self._exists = exists
        self.metadata = metadata
        self.uploads: list[dict[str, object]] = []

    def exists(self, client: object = None) -> bool:
        return self._exists

    def reload(self, client: object = None) -> None:
        return None

    def upload_from_filename(
        self,
        filename: str,
        *,
        content_type: str,
        if_generation_match: int,
    ) -> None:
        self.uploads.append(
            {
                "filename": filename,
                "content_type": content_type,
                "if_generation_match": if_generation_match,
            }
        )
        self._exists = True


class FakeBucket:
    def __init__(self, blob: FakeBlob) -> None:
        self._blob = blob

    def blob(self, blob_name: str) -> FakeBlob:
        return self._blob


class FakeClient:
    def __init__(self, blob: FakeBlob) -> None:
        self._bucket = FakeBucket(blob)

    def bucket(self, bucket_name: str) -> FakeBucket:
        return self._bucket


def _source_file(tmp_path: Path) -> Path:
    path = tmp_path / "calendar.csv"
    path.write_text("date,d\n2011-01-29,d_1\n", encoding="utf-8")
    return path


def test_uploads_new_object_with_create_only_precondition(tmp_path: Path) -> None:
    path = _source_file(tmp_path)
    blob = FakeBlob(exists=False)

    result = upload_immutable_file(
        client=FakeClient(blob),
        bucket_name="retailops-test",
        local_path=path,
        object_name="landing/m5/v1/calendar.csv",
    )

    assert result.status == "uploaded"
    assert blob.metadata is not None
    assert blob.metadata["source_sha256"] == sha256_file(path)
    assert blob.uploads[0]["if_generation_match"] == 0
    assert blob.uploads[0]["content_type"] == "text/csv"


def test_skips_existing_object_when_sha256_matches(tmp_path: Path) -> None:
    path = _source_file(tmp_path)
    digest = sha256_file(path)
    blob = FakeBlob(exists=True, metadata={"source_sha256": digest})

    result = upload_immutable_file(
        client=FakeClient(blob),
        bucket_name="retailops-test",
        local_path=path,
        object_name="landing/m5/v1/calendar.csv",
    )

    assert result.status == "skipped"
    assert blob.uploads == []


def test_rejects_existing_object_with_different_content(tmp_path: Path) -> None:
    path = _source_file(tmp_path)
    blob = FakeBlob(exists=True, metadata={"source_sha256": "different"})

    with pytest.raises(LandingObjectConflictError):
        upload_immutable_file(
            client=FakeClient(blob),
            bucket_name="retailops-test",
            local_path=path,
            object_name="landing/m5/v1/calendar.csv",
        )

    assert blob.uploads == []
