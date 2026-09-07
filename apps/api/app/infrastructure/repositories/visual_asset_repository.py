from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.story import VisualAssetModel
from app.infrastructure.asset_storage.base import AssetStorage
from shared_types.visual_asset import VisualAsset


class VisualAssetRepository:
    """
    Repository for VisualAsset persistence.

    Unlike EditPlan/VoiceTrack (one row per story), a story has MANY
    visual assets. The natural key is (story_id, scene_number,
    shot_number, asset_type) — upsert() replaces the row for that key
    instead of inserting a duplicate. Media bytes never touch the DB:
    they're written to AssetStorage first, and only the resulting
    storage_key is persisted.
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
        asset: VisualAsset,
    ) -> VisualAssetModel:
        """
        Create or update a VisualAsset row for (story_id, scene_number,
        shot_number, asset_type). The asset's bytes are written to
        AssetStorage BEFORE the DB write, so a DB row is never committed
        pointing at a storage_key that doesn't exist.
        """
        story_uuid = self._to_uuid(story_id)

        storage_key = await self._asset_storage.save(asset.asset)

        result = await self.session.execute(
            select(VisualAssetModel).where(
                VisualAssetModel.story_id == story_uuid,
                VisualAssetModel.scene_number == asset.scene_number,
                VisualAssetModel.shot_number == asset.shot_number,
                VisualAssetModel.asset_type == asset.asset_type,
            )
        )
        db_asset = result.scalar_one_or_none()

        if db_asset is None:
            db_asset = VisualAssetModel(
                story_id=story_uuid,
                scene_number=asset.scene_number,
                shot_number=asset.shot_number,
                asset_type=asset.asset_type,
            )
            self.session.add(db_asset)

        db_asset.storage_key = storage_key
        db_asset.actual_duration = asset.actual_duration

        await self.session.commit()
        await self.session.refresh(db_asset)

        return db_asset

    async def get(
        self,
        story_id: str | UUID,
        scene_number: int,
        shot_number: int,
        asset_type: str,
    ) -> VisualAssetModel | None:
        story_uuid = self._to_uuid(story_id)

        result = await self.session.execute(
            select(VisualAssetModel).where(
                VisualAssetModel.story_id == story_uuid,
                VisualAssetModel.scene_number == scene_number,
                VisualAssetModel.shot_number == shot_number,
                VisualAssetModel.asset_type == asset_type,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_story(self, story_id: str | UUID) -> list[VisualAssetModel]:
        story_uuid = self._to_uuid(story_id)

        result = await self.session.execute(
            select(VisualAssetModel).where(VisualAssetModel.story_id == story_uuid)
        )
        return list(result.scalars().all())

    async def list_by_scene(
        self, story_id: str | UUID, scene_number: int
    ) -> list[VisualAssetModel]:
        story_uuid = self._to_uuid(story_id)

        result = await self.session.execute(
            select(VisualAssetModel).where(
                VisualAssetModel.story_id == story_uuid,
                VisualAssetModel.scene_number == scene_number,
            )
        )
        return list(result.scalars().all())

    async def get_by_id(
        self, story_id: str | UUID, asset_id: str | UUID
    ) -> VisualAssetModel | None:
        story_uuid = self._to_uuid(story_id)
        asset_uuid = self._to_uuid(asset_id)

        result = await self.session.execute(
            select(VisualAssetModel).where(
                VisualAssetModel.id == asset_uuid,
                VisualAssetModel.story_id == story_uuid,
            )
        )
        return result.scalar_one_or_none()
