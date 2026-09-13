"""Artifact storage helpers used by training and serving workloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google.cloud import storage


def split_gcs_uri(uri: str) -> tuple[str, str]:
    """Split a ``gs://bucket/prefix`` URI into bucket name and object prefix."""
    if not uri.startswith("gs://"):
        raise ValueError(f"Expected a gs:// URI, got: {uri!r}")

    remainder = uri[5:]
    bucket_name, separator, prefix = remainder.partition("/")
    if not bucket_name:
        raise ValueError("GCS URI must include a bucket name")

    return bucket_name, prefix.rstrip("/") if separator else ""


def load_json_from_gcs(
    gcs_uri: str,
    *,
    client: storage.Client | None = None,
) -> dict[str, Any]:
    """Load one JSON object from a GCS URI."""
    bucket_name, object_name = split_gcs_uri(gcs_uri)
    if not object_name:
        raise ValueError("JSON GCS URI must include an object path")

    storage_client = client or storage.Client()
    text = storage_client.bucket(bucket_name).blob(object_name).download_as_text()
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object at {gcs_uri}")
    return payload


def upload_directory_to_gcs(
    local_dir: str | Path,
    gcs_uri: str,
    *,
    client: storage.Client | None = None,
) -> list[str]:
    """Upload every file below ``local_dir`` to ``gcs_uri`` preserving subpaths."""
    source = Path(local_dir)
    if not source.is_dir():
        raise ValueError(f"Artifact directory does not exist: {source}")

    bucket_name, prefix = split_gcs_uri(gcs_uri)
    storage_client = client or storage.Client()
    bucket = storage_client.bucket(bucket_name)

    uploaded: list[str] = []
    for path in sorted(item for item in source.rglob("*") if item.is_file()):
        relative_path = path.relative_to(source).as_posix()
        object_name = f"{prefix}/{relative_path}" if prefix else relative_path
        blob = bucket.blob(object_name)
        blob.upload_from_filename(str(path))
        uploaded.append(f"gs://{bucket_name}/{object_name}")

    return uploaded


def download_directory_from_gcs(
    gcs_uri: str,
    local_dir: str | Path,
    *,
    client: storage.Client | None = None,
) -> list[Path]:
    """Download all objects under ``gcs_uri`` into ``local_dir``."""
    bucket_name, prefix = split_gcs_uri(gcs_uri)
    destination = Path(local_dir)
    destination.mkdir(parents=True, exist_ok=True)

    storage_client = client or storage.Client()
    blobs = storage_client.list_blobs(bucket_name, prefix=prefix)

    downloaded: list[Path] = []
    normalized_prefix = f"{prefix}/" if prefix else ""
    for blob in blobs:
        if blob.name.endswith("/"):
            continue
        relative_name = (
            blob.name[len(normalized_prefix) :]
            if normalized_prefix and blob.name.startswith(normalized_prefix)
            else blob.name
        )
        if not relative_name:
            continue

        local_path = destination / relative_name
        local_path.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(local_path))
        downloaded.append(local_path)

    return downloaded
