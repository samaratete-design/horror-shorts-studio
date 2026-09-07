from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.story import MusicAssetModel
from app.infrastructure.asset_storage.base import AssetStorage
from shared_types.music_asset import MusicAsset


class MusicAssetRepository:
    """
    Repository for MusicAsset persistence.

    A story has MANY music assets — one per cue_number. upsert()
    replaces the row for (story_id, cue_number) instead of inserting a
    duplicate. Media bytes never touch the DB: written to AssetStorage
    first, only storage_key is persisted.
    """

    def __init__(self, session: AsyncSession, asset_storage: AssetStorage) -> None:
        self.session = session
        self._asset_storage = asset_storage

    @staticmethod
    def _to_uuid(story_id: str | UUID) -> UUID:
        return story_id if isinstance(story_id, UUID) else UUID(str(story_id))

    async def upsert(
        self,
        story_id: str | UUID,
        asset: MusicAsset,
    ) -> MusicAssetModel:
        story_uuid = self._to_uuid(story_id)

        storage_key = await self._asset_storage.save(asset.asset)

        result = await self.session.execute(
            select(MusicAssetModel).where(
                MusicAssetModel.story_id == story_uuid,
                MusicAssetModel.cue_number == asset.cue_number,
            )
        )
        db_asset = result.scalar_one_or_none()

        if db_asset is None:
            db_asset = MusicAssetModel(
                story_id=story_uuid,
                cue_number=asset.cue_number,
            )
            self.session.add(db_asset)

        db_asset.storage_key = storage_key
        db_asset.actual_duration = asset.actual_duration

        await self.session.commit()
        await self.session.refresh(db_asset)

        return db_asset

    async def get(
        self, story_id: str | UUID, cue_number: int
    ) -> MusicAssetModel | None:
        story_uuid = self._to_uuid(story_id)

        result = await self.session.execute(
            select(MusicAssetModel).where(
                MusicAssetModel.story_id == story_uuid,
                MusicAssetModel.cue_number == cue_number,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_story(self, story_id: str | UUID) -> list[MusicAssetModel]:
        story_uuid = self._to_uuid(story_id)

        result = await self.session.execute(
            select(MusicAssetModel).where(MusicAssetModel.story_id == story_uuid)
        )
        return list(result.scalars().all())

    async def get_by_id(
        self, story_id: str | UUID, asset_id: str | UUID
    ) -> MusicAssetModel | None:
        story_uuid = self._to_uuid(story_id)
        asset_uuid = self._to_uuid(asset_id)

        result = await self.session.execute(
            select(MusicAssetModel).where(
                MusicAssetModel.id == asset_uuid,
                MusicAssetModel.story_id == story_uuid,
            )
        )
        return result.scalar_one_or_none()
