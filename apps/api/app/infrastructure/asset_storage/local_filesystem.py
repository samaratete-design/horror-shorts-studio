import uuid
from pathlib import Path

from .base import AssetStorage


class AssetNotFoundError(Exception):
    """Raised when load()/delete() is given a storage_key with no backing file."""


class LocalFilesystemAssetStorage(AssetStorage):
    """
    Local/filesystem AssetStorage implementation.

    storage_key is a flat filename (uuid4 hex, no extension — asset_type
    already lives in the DB row, so the file itself doesn't need one).
    Swappable later for a cloud-backed AssetStorage without any
    repository code changes, since callers only ever see storage_key.
    """

    def __init__(self, base_dir: str | Path):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, data: bytes) -> str:
        storage_key = uuid.uuid4().hex
        (self._base_dir / storage_key).write_bytes(data)
        return storage_key

    async def load(self, storage_key: str) -> bytes:
        path = self._base_dir / storage_key
        if not path.exists():
            raise AssetNotFoundError(f"No asset found for storage_key {storage_key!r}")
        return path.read_bytes()

    async def delete(self, storage_key: str) -> None:
        path = self._base_dir / storage_key
        if path.exists():
            path.unlink()
