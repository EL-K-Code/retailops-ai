"""Immutable Google Cloud Storage landing-zone uploads for M5 source files."""

from __future__ import annotations

import argparse
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from retailops_ai.ingestion.m5 import EXPECTED_M5_FILES, validate_m5_source_dir

DEFAULT_LANDING_PREFIX = "landing/m5/v1"
DATASET_NAME = "m5-forecasting-accuracy"
CONTRACT_VERSION = "1"


class LandingObjectConflictError(RuntimeError):
    """Raised when an immutable landing object already exists with different content."""


class BlobLike(Protocol):
    """Minimal blob interface used by the landing uploader."""

    metadata: dict[str, str] | None

    def exists(self, client: Any = None) -> bool: ...

    def reload(self, client: Any = None) -> None: ...

    def upload_from_filename(
        self,
        filename: str,
        *,
        content_type: str,
        if_generation_match: int,
    ) -> None: ...


class BucketLike(Protocol):
    """Minimal bucket interface used by the landing uploader."""

    def blob(self, blob_name: str) -> BlobLike: ...


class StorageClientLike(Protocol):
    """Minimal storage-client interface used by the landing uploader."""

    def bucket(self, bucket_name: str) -> BucketLike: ...


@dataclass(frozen=True)
class UploadResult:
    """Outcome for a single immutable landing upload."""

    local_file: str
    object_name: str
    sha256: str
    status: str


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 digest of a file without loading it fully into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def upload_immutable_file(
    client: StorageClientLike,
    bucket_name: str,
    local_path: Path,
    object_name: str,
) -> UploadResult:
    """Upload one file exactly once, or skip it when identical content already exists."""
    if not local_path.is_file():
        raise FileNotFoundError(f"Local source file does not exist: {local_path}")

    local_sha256 = sha256_file(local_path)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    if blob.exists(client=client):
        blob.reload(client=client)
        remote_sha256 = (blob.metadata or {}).get("source_sha256")
        if remote_sha256 == local_sha256:
            return UploadResult(
                local_file=str(local_path),
                object_name=object_name,
                sha256=local_sha256,
                status="skipped",
            )

        raise LandingObjectConflictError(
            "Immutable landing object already exists with different or missing "
            f"source_sha256 metadata: gs://{bucket_name}/{object_name}"
        )

    blob.metadata = {
        "source_dataset": DATASET_NAME,
        "source_file": local_path.name,
        "source_sha256": local_sha256,
        "source_contract_version": CONTRACT_VERSION,
    }
    blob.upload_from_filename(
        str(local_path),
        content_type="text/csv",
        if_generation_match=0,
    )

    return UploadResult(
        local_file=str(local_path),
        object_name=object_name,
        sha256=local_sha256,
        status="uploaded",
    )


def upload_m5_landing(
    client: StorageClientLike,
    bucket_name: str,
    data_dir: Path,
    prefix: str = DEFAULT_LANDING_PREFIX,
) -> list[UploadResult]:
    """Upload the validated M5 source contract into the immutable GCS landing prefix."""
    errors = validate_m5_source_dir(data_dir)
    if errors:
        rendered = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"M5 source validation failed:\n{rendered}")

    normalized_prefix = prefix.strip("/")
    return [
        upload_immutable_file(
            client=client,
            bucket_name=bucket_name,
            local_path=data_dir / filename,
            object_name=f"{normalized_prefix}/{filename}",
        )
        for filename in EXPECTED_M5_FILES
    ]


def build_storage_client(project: str | None = None) -> StorageClientLike:
    """Build the real Google Cloud Storage client using Application Default Credentials."""
    try:
        from google.cloud import storage
    except ImportError as exc:
        raise RuntimeError(
            "google-cloud-storage is not installed. Run `uv sync` before this command."
        ) from exc

    return storage.Client(project=project)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload M5 source files to immutable GCS landing.")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--bucket", default=os.getenv("GCS_BUCKET"))
    parser.add_argument("--prefix", default=os.getenv("GCS_LANDING_PREFIX", DEFAULT_LANDING_PREFIX))
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    args = parser.parse_args(argv)

    if not args.bucket:
        parser.error("--bucket or GCS_BUCKET is required")

    return args


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for immutable M5 landing uploads."""
    args = _parse_args(argv)
    client = build_storage_client(args.project)
    results = upload_m5_landing(
        client=client,
        bucket_name=args.bucket,
        data_dir=args.data_dir,
        prefix=args.prefix,
    )

    for result in results:
        print(f"{result.status.upper():8} gs://{args.bucket}/{result.object_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
