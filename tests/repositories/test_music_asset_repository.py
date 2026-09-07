import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared_types.music_asset import MusicAsset

from app.infrastructure.repositories.music_asset_repository import MusicAssetRepository
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
async def test_upsert_creates_music_asset_and_stores_bytes_via_asset_storage(
    db_session: AsyncSession, asset_storage
):
    story_id = await make_story(db_session)
    repo = MusicAssetRepository(db_session, asset_storage)

    asset = MusicAsset(
        story_id=str(story_id), cue_number=1, asset=b"exact-audio-bytes", actual_duration=6.8,
    )
    result = await repo.upsert(story_id, asset)

    assert result.story_id == story_id
    assert result.cue_number == 1
    assert result.actual_duration == pytest.approx(6.8)
    assert isinstance(result.storage_key, str) and result.storage_key
    assert await asset_storage.load(result.storage_key) == b"exact-audio-bytes"


@pytest.mark.asyncio
async def test_upsert_regenerating_same_cue_replaces_row_not_duplicates(
    db_session: AsyncSession, asset_storage
):
    story_id = await make_story(db_session)
    repo = MusicAssetRepository(db_session, asset_storage)

    await repo.upsert(story_id, MusicAsset(
        story_id=str(story_id), cue_number=1, asset=b"first", actual_duration=5.0,
    ))
    result = await repo.upsert(story_id, MusicAsset(
        story_id=str(story_id), cue_number=1, asset=b"regenerated", actual_duration=7.1,
    ))

    all_rows = await repo.list_by_story(story_id)
    assert len(all_rows) == 1
    assert result.actual_duration == pytest.approx(7.1)
    assert await asset_storage.load(result.storage_key) == b"regenerated"


@pytest.mark.asyncio
async def test_get_returns_none_for_nonexistent_cue(db_session: AsyncSession, asset_storage):
    story_id = await make_story(db_session)
    repo = MusicAssetRepository(db_session, asset_storage)

    result = await repo.get(story_id, cue_number=1)
    assert result is None


@pytest.mark.asyncio
async def test_list_by_story_returns_all_cues(db_session: AsyncSession, asset_storage):
    story_id = await make_story(db_session)
    repo = MusicAssetRepository(db_session, asset_storage)

    await repo.upsert(story_id, MusicAsset(
        story_id=str(story_id), cue_number=1, asset=b"a", actual_duration=5.0,
    ))
    await repo.upsert(story_id, MusicAsset(
        story_id=str(story_id), cue_number=2, asset=b"b", actual_duration=6.0,
    ))

    all_rows = await repo.list_by_story(story_id)
    assert len(all_rows) == 2


@pytest.mark.asyncio
async def test_get_by_id_found_matching_story(db_session: AsyncSession, asset_storage):
    story_id = await make_story(db_session)
    repo = MusicAssetRepository(db_session, asset_storage)

    created = await repo.upsert(story_id, MusicAsset(
        story_id=str(story_id), cue_number=1, asset=b"exact-audio", actual_duration=6.0,
    ))

    result = await repo.get_by_id(story_id, created.id)

    assert result is not None
    assert result.id == created.id
    assert result.story_id == story_id
    assert result.cue_number == 1
    assert result.storage_key == created.storage_key


@pytest.mark.asyncio
async def test_get_by_id_wrong_story_returns_none(db_session: AsyncSession, asset_storage):
    story_id = await make_story(db_session)
    other_story_id = await make_story(db_session)
    repo = MusicAssetRepository(db_session, asset_storage)

    created = await repo.upsert(story_id, MusicAsset(
        story_id=str(story_id), cue_number=1, asset=b"exact-audio", actual_duration=6.0,
    ))

    result = await repo.get_by_id(other_story_id, created.id)

    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_not_found_returns_none(db_session: AsyncSession, asset_storage):
    story_id = await make_story(db_session)
    repo = MusicAssetRepository(db_session, asset_storage)

    result = await repo.get_by_id(story_id, uuid.uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_accepts_string_story_id_and_asset_id(db_session: AsyncSession, asset_storage):
    story_id = await make_story(db_session)
    repo = MusicAssetRepository(db_session, asset_storage)

    created = await repo.upsert(story_id, MusicAsset(
        story_id=str(story_id), cue_number=1, asset=b"exact-audio", actual_duration=6.0,
    ))

    result = await repo.get_by_id(str(story_id), str(created.id))

    assert result is not None
    assert result.id == created.id
