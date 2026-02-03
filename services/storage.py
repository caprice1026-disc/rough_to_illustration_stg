from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from flask import current_app
from google.api_core.exceptions import NotFound
from google.cloud import storage


@dataclass(frozen=True)
class StoredObject:
    """ストレージへ保存したオブジェクトの情報。"""

    storage_backend: str
    bucket: str | None
    object_name: str
    byte_size: int
    sha256: str


def _normalize_backend(value: str | None) -> str:
    if not value:
        return "local"
    return value.strip().lower()


def _local_base_dir(config_key: str, default_dir: str) -> Path:
    configured = current_app.config.get(config_key) or default_dir
    base = Path(configured)
    if base.is_absolute():
        base.mkdir(parents=True, exist_ok=True)
        return base
    base = Path(current_app.instance_path) / base
    base.mkdir(parents=True, exist_ok=True)
    return base


def _gcs_bucket(bucket_name: str) -> storage.Bucket:
    client = storage.Client()
    return client.bucket(bucket_name)


def _hash_bytes(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def _build_object_name(prefix: str, extension: str) -> str:
    safe_prefix = prefix.strip("/")
    image_id = f"{uuid4().hex}{extension}"
    if safe_prefix:
        return f"{safe_prefix}/{image_id}"
    return image_id


def save_bytes(
    *,
    raw_bytes: bytes,
    extension: str,
    storage_backend: str,
    bucket_name: str | None,
    local_dir_key: str,
    default_local_dir: str,
    object_prefix: str,
    content_type: str | None = None,
) -> StoredObject:
    """バイト列をストレージへ保存して情報を返す。"""

    backend = _normalize_backend(storage_backend)
    object_name = _build_object_name(object_prefix, extension)
    sha256 = _hash_bytes(raw_bytes)

    if backend == "gcs":
        if not bucket_name:
            raise ValueError("GCSバケット名が未設定です。")
        bucket = _gcs_bucket(bucket_name)
        blob = bucket.blob(object_name)
        if content_type:
            blob.upload_from_string(raw_bytes, content_type=content_type)
        else:
            blob.upload_from_string(raw_bytes)
        return StoredObject(
            storage_backend=backend,
            bucket=bucket_name,
            object_name=object_name,
            byte_size=len(raw_bytes),
            sha256=sha256,
        )

    base_dir = _local_base_dir(local_dir_key, default_local_dir)
    path = base_dir / object_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw_bytes)
    return StoredObject(
        storage_backend=backend,
        bucket=None,
        object_name=object_name,
        byte_size=len(raw_bytes),
        sha256=sha256,
    )


def load_bytes(
    *,
    storage_backend: str,
    bucket_name: str | None,
    object_name: str,
    local_dir_key: str,
    default_local_dir: str,
) -> bytes | None:
    """保存済みオブジェクトのバイト列を取得する。"""

    backend = _normalize_backend(storage_backend)
    if backend == "gcs":
        if not bucket_name:
            return None
        bucket = _gcs_bucket(bucket_name)
        blob = bucket.blob(object_name)
        try:
            return blob.download_as_bytes()
        except NotFound:
            return None

    base_dir = _local_base_dir(local_dir_key, default_local_dir)
    path = base_dir / object_name
    if not path.exists():
        return None
    return path.read_bytes()
