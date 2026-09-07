from dataclasses import dataclass


@dataclass(frozen=True)
class VisualAsset:
    story_id: str
    scene_number: int
    shot_number: int
    asset_type: str
    asset: bytes
    actual_duration: float | None = None
