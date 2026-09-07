from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SceneCut:
    scene_number: int
    start_time: float
    end_time: float


@dataclass
class EditPlan:
    story_id: str
    total_duration: float
    cuts: list[SceneCut] = field(default_factory=list)
