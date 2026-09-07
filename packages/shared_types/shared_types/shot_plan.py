from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Shot:
    shot_number: int
    visual_prompt: str
    estimated_duration: float
    asset_type: str


@dataclass
class ShotPlan:
    story_id: str
    scene_number: int
    shots: list[Shot] = field(default_factory=list)
