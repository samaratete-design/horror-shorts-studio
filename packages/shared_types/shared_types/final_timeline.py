from __future__ import annotations

from dataclasses import dataclass, field

from shared_types.music_asset import MusicAsset


@dataclass(frozen=True)
class FinalSegment:
    scene_number: int
    start_time: float
    end_time: float


@dataclass
class FinalTimeline:
    story_id: str
    total_duration: float
    segments: list[FinalSegment] = field(default_factory=list)
    music_assets: list[MusicAsset] = field(default_factory=list)
