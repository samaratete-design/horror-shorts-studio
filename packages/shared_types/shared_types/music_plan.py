from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MusicCue:
    cue_number: int
    start_time: float
    end_time: float
    mood: str
    music_prompt: str


@dataclass
class MusicPlan:
    story_id: str
    total_duration: float
    cues: list[MusicCue] = field(default_factory=list)
