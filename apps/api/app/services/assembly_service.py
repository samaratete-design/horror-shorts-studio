from shared_types.edit_plan import EditPlan
from shared_types.voice_track import VoiceTrack
from shared_types.visual_asset import VisualAsset
from shared_types.music_asset import MusicAsset
from shared_types.final_timeline import FinalTimeline, FinalSegment


class AssemblyError(Exception):
    """Raised when assembly fails (identity mismatch, invalid reconciliation)."""


class InvalidAssemblyRequestError(Exception):
    """Raised when the assembly request is invalid, before any reconciliation happens."""


class AssemblyService:
    """
    Reconciles the planned timeline (EditPlan) with actual generated
    evidence (VoiceTrack, VisualAssets) into a FinalTimeline — the first
    artifact in the pipeline to own a global (non-scene-relative) timeline.

    Reconciliation rule per scene:
        final_duration = max(actual_voice_duration, actual_visual_duration)
        - actual_voice_duration: max end_time across that scene's VoiceSegments,
          or None if the scene has no voice segments.
        - actual_visual_duration: max actual_duration across that scene's
          VisualAssets where asset_type == "video" and actual_duration is not
          None (images never contribute — they have no intrinsic duration).
        - If both are None, falls back to EditPlan's planned duration for
          that scene.

    Music does not influence scene duration. MusicAssets are passed through
    unchanged. This service performs no media transformation, no rendering,
    no persistence — it only builds the FinalTimeline data structure.
    """

    async def assemble(
        self,
        story_id: str,
        edit_plan: EditPlan,
        voice_track: VoiceTrack,
        visual_assets: list[VisualAsset],
        music_assets: list[MusicAsset],
    ) -> FinalTimeline:
        self._validate(edit_plan, voice_track)
        self._validate_identity(story_id, edit_plan, voice_track, visual_assets, music_assets)

        segments: list[FinalSegment] = []
        cursor = 0.0

        for cut in edit_plan.cuts:
            scene_number = cut.scene_number
            planned_duration = cut.end_time - cut.start_time

            actual_voice = self._actual_voice_duration(voice_track, scene_number)
            actual_visual = self._actual_visual_duration(visual_assets, scene_number)

            candidates = [d for d in (actual_voice, actual_visual) if d is not None]
            duration = max(candidates) if candidates else planned_duration

            start = cursor
            end = cursor + duration
            segments.append(
                FinalSegment(scene_number=scene_number, start_time=start, end_time=end)
            )
            cursor = end

        return FinalTimeline(
            story_id=story_id,
            total_duration=cursor,
            segments=segments,
            music_assets=list(music_assets),
        )

    @staticmethod
    def _actual_voice_duration(voice_track: VoiceTrack, scene_number: int) -> float | None:
        scene_segments = [s for s in voice_track.segments if s.scene_number == scene_number]
        if not scene_segments:
            return None
        return max(s.end_time for s in scene_segments)

    @staticmethod
    def _actual_visual_duration(
        visual_assets: list[VisualAsset], scene_number: int
    ) -> float | None:
        durations = [
            a.actual_duration
            for a in visual_assets
            if a.scene_number == scene_number
            and a.asset_type == "video"
            and a.actual_duration is not None
        ]
        if not durations:
            return None
        return max(durations)

    @staticmethod
    def _validate(edit_plan: EditPlan, voice_track: VoiceTrack) -> None:
        if edit_plan is None:
            raise InvalidAssemblyRequestError("edit_plan is required and cannot be None")

        if voice_track is None:
            raise InvalidAssemblyRequestError("voice_track is required and cannot be None")

    @staticmethod
    def _validate_identity(
        story_id: str,
        edit_plan: EditPlan,
        voice_track: VoiceTrack,
        visual_assets: list[VisualAsset],
        music_assets: list[MusicAsset],
    ) -> None:
        if edit_plan.story_id != story_id:
            raise AssemblyError(
                f"EditPlan.story_id mismatch: requested {story_id!r}, got {edit_plan.story_id!r}"
            )

        if voice_track.story_id != story_id:
            raise AssemblyError(
                f"VoiceTrack.story_id mismatch: requested {story_id!r}, got {voice_track.story_id!r}"
            )

        for asset in visual_assets:
            if asset.story_id != story_id:
                raise AssemblyError(
                    f"VisualAsset.story_id mismatch: requested {story_id!r}, got {asset.story_id!r}"
                )

        for asset in music_assets:
            if asset.story_id != story_id:
                raise AssemblyError(
                    f"MusicAsset.story_id mismatch: requested {story_id!r}, got {asset.story_id!r}"
                )
