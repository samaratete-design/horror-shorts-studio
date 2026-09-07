from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VoiceSegment:
    scene_number: int
    speaker: str
    start_time: float
    end_time: float
    audio: bytes

    def __post_init__(self) -> None:
        if self.start_time < 0:
            raise ValueError("start_time must be >= 0")

        if self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")


@dataclass
class VoiceTrack:
    story_id: str
    segments: list[VoiceSegment] = field(default_factory=list)
