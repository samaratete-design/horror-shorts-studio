from abc import ABC, abstractmethod


class AssetStorage(ABC):
    """
    Abstraction over where generated media bytes physically live.

    The database (VisualAssetModel/MusicAssetModel) never stores raw
    bytes — only the storage_key this class returns from save(). This
    keeps the DB layer swappable from local filesystem to any future
    backend (S3, GCS, ...) without touching repository code.
    """

    @abstractmethod
    async def save(self, data: bytes) -> str:
        """Persist bytes, returning an opaque storage_key that load()/delete() can use later."""
        raise NotImplementedError

    @abstractmethod
    async def load(self, storage_key: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, storage_key: str) -> None:
        raise NotImplementedError
