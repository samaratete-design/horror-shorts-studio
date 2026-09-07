import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared_types.visual_asset import VisualAsset

from app.infrastructure.repositories.visual_asset_repository import VisualAssetRepository
from app.infrastructure.asset_storage.local_filesystem import LocalFilesystemAssetStorage
from app.models.story import Story as SQLStory
from app.models.story import StoryStatus as SQLStoryStatus


@pytest.fixture
def asset_storage(tmp_path):
    return LocalFilesystemAssetStorage(base_dir=tmp_path)


async def make_story(db_session: AsyncSession) -> uuid.UUID:
    story_id = uuid.uuid4()
    db_story = SQLStory(
        id=story_id,
        title="Test Horror Short",
        status=SQLStoryStatus.DRAFT,
        original_idea="A haunted house",
        language="ar",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(db_story)
    await db_session.commit()
    return story_id


@pytest.mark.asyncio
async def test_upsert_creates_visual_asset_and_stores_bytes_via_asset_storage(
    db_session: AsyncSession, asset_storage
):
    story_id = await make_story(db_session)
    repo = VisualAssetRepository(db_session, asset_storage)

    asset = VisualAsset(
        story_id=str(story_id), scene_number=1, shot_number=1,
        asset_type="video", asset=b"exact-video-bytes", actual_duration=9.5,
    )
    result = await repo.upsert(story_id, asset)

    assert result is not None
    assert result.story_id == story_id
    assert result.scene_number == 1
    assert result.shot_number == 1
    assert result.asset_type == "video"
    assert result.actual_duration == pytest.approx(9.5)
    # DB row never holds raw bytes — only a storage_key
    assert isinstance(result.storage_key, str) and result.storage_key
    # AssetStorage actually has the bytes, addressable by that key
    assert await asset_storage.load(result.storage_key) == b"exact-video-bytes"


@pytest.mark.asyncio
async def test_upsert_regenerating_same_shot_replaces_row_not_duplicates(
    db_session: AsyncSession, asset_storage
):
    story_id = await make_story(db_session)
    repo = VisualAssetRepository(db_session, asset_storage)

    first = VisualAsset(
        story_id=str(story_id), scene_number=1, shot_number=1,
        asset_type="video", asset=b"first-take", actual_duration=8.0,
    )
    await repo.upsert(story_id, first)

    second = VisualAsset(
        story_id=str(story_id), scene_number=1, shot_number=1,
        asset_type="video", asset=b"regenerated-take", actual_duration=9.2,
    )
    result = await repo.upsert(story_id, second)

    all_rows = await repo.list_by_story(story_id)
    assert len(all_rows) == 1  # NOT 2 — same natural key upserts in place
    assert result.actual_duration == pytest.approx(9.2)
    assert await asset_storage.load(result.storage_key) == b"regenerated-take"


@pytest.mark.asyncio
async def test_get_returns_none_for_nonexistent_shot(db_session: AsyncSession, asset_storage):
    story_id = await make_story(db_session)
    repo = VisualAssetRepository(db_session, asset_storage)

    result = await repo.get(story_id, scene_number=1, shot_number=1, asset_type="image")
    assert result is None


@pytest.mark.asyncio
async def test_list_by_story_returns_all_shots_across_scenes(db_session: AsyncSession, asset_storage):
    story_id = await make_story(db_session)
    repo = VisualAssetRepository(db_session, asset_storage)

    await repo.upsert(story_id, VisualAsset(
        story_id=str(story_id), scene_number=1, shot_number=1,
        asset_type="video", asset=b"a", actual_duration=5.0,
    ))
    await repo.upsert(story_id, VisualAsset(
        story_id=str(story_id), scene_number=2, shot_number=1,
        asset_type="image", asset=b"b", actual_duration=None,
    ))

    all_rows = await repo.list_by_story(story_id)
    assert len(all_rows) == 2


@pytest.mark.asyncio
async def test_list_by_scene_filters_correctly(db_session: AsyncSession, asset_storage):
    story_id = await make_story(db_session)
    repo = VisualAssetRepository(db_session, asset_storage)

    await repo.upsert(story_id, VisualAsset(
        story_id=str(story_id), scene_number=1, shot_number=1,
        asset_type="video", asset=b"a", actual_duration=5.0,
    ))
    await repo.upsert(story_id, VisualAsset(
        story_id=str(story_id), scene_number=1, shot_number=2,
        asset_type="image", asset=b"b", actual_duration=None,
    ))
    await repo.upsert(story_id, VisualAsset(
        story_id=str(story_id), scene_number=2, shot_number=1,
        asset_type="video", asset=b"c", actual_duration=4.0,
    ))

    scene_1_rows = await repo.list_by_scene(story_id, scene_number=1)
    assert len(scene_1_rows) == 2
    assert all(r.scene_number == 1 for r in scene_1_rows)


@pytest.mark.asyncio
async def test_get_by_id_found_matching_story(db_session: AsyncSession, asset_storage):
    story_id = await make_story(db_session)
    repo = VisualAssetRepository(db_session, asset_storage)

    created = await repo.upsert(story_id, VisualAsset(
        story_id=str(story_id), scene_number=1, shot_number=1,
        asset_type="video", asset=b"exact-bytes", actual_duration=5.0,
    ))

    result = await repo.get_by_id(story_id, created.id)

    assert result is not None
    assert result.id == created.id
    assert result.story_id == story_id
    assert result.scene_number == 1
    assert result.shot_number == 1
    assert result.asset_type == "video"
    assert result.storage_key == created.storage_key


@pytest.mark.asyncio
async def test_get_by_id_wrong_story_returns_none(db_session: AsyncSession, asset_storage):
    story_id = await make_story(db_session)
    other_story_id = await make_story(db_session)
    repo = VisualAssetRepository(db_session, asset_storage)

    created = await repo.upsert(story_id, VisualAsset(
        story_id=str(story_id), scene_number=1, shot_number=1,
        asset_type="video", asset=b"exact-bytes", actual_duration=5.0,
    ))

    result = await repo.get_by_id(other_story_id, created.id)

    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_not_found_returns_none(db_session: AsyncSession, asset_storage):
    story_id = await make_story(db_session)
    repo = VisualAssetRepository(db_session, asset_storage)

    result = await repo.get_by_id(story_id, uuid.uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_accepts_string_story_id_and_asset_id(db_session: AsyncSession, asset_storage):
    story_id = await make_story(db_session)
    repo = VisualAssetRepository(db_session, asset_storage)

    created = await repo.upsert(story_id, VisualAsset(
        story_id=str(story_id), scene_number=1, shot_number=1,
        asset_type="video", asset=b"exact-bytes", actual_duration=5.0,
    ))

    result = await repo.get_by_id(str(story_id), str(created.id))

    assert result is not None
    assert result.id == created.id
