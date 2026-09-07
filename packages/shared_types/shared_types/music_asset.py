from dataclasses import dataclass


@dataclass(frozen=True)
class MusicAsset:
    story_id: str
    cue_number: int
    asset: bytes
    actual_duration: float
