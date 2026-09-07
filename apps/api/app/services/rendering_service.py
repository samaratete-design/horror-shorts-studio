from __future__ import annotations

import os
import uuid
from pathlib import Path
from uuid import UUID


class MissingRenderingInputError(Exception):
    """Raised when a required input for rendering (timeline, voice track,
    a referenced visual asset, or a referenced music asset) is missing."""


class RenderingService:
    """
    Assembles the final MP4 for a story from its FinalTimeline, the
    story's VoiceTrack, and the visual/music assets referenced by the
    timeline — via FFmpeg. This service performs no reconciliation or
    timing logic of its own (that's AssemblyService's job); it only
    resolves references to real bytes and drives FFmpeg.

    ffmpeg_runner is injected (not a direct subprocess call) so tests
    never need to actually invoke FFmpeg — only a real wiring/integration
    step does that, deliberately kept separate from this TDD cycle.
    """

    def __init__(
        self,
        final_timeline_repository,
        story_repository,
        visual_asset_repository,
        music_asset_repository,
        asset_storage,
        ffmpeg_runner,
        output_dir: str,
    ) -> None:
        self._final_timeline_repository = final_timeline_repository
        self._story_repository = story_repository
        self._visual_asset_repository = visual_asset_repository
        self._music_asset_repository = music_asset_repository
        self._asset_storage = asset_storage
        self._ffmpeg_runner = ffmpeg_runner
        self._output_dir = output_dir

    async def render(self, story_id: str | UUID) -> str:
        timeline = await self._final_timeline_repository.get(story_id)
        if timeline is None:
            raise MissingRenderingInputError(
                f"No FinalTimeline found for story_id={story_id!r}"
            )

        voice_track = await self._story_repository.get_voice_track(story_id)
        if voice_track is None:
            raise MissingRenderingInputError(
                f"No VoiceTrack found for story_id={story_id!r}"
            )

        visual_files: list[str] = []
        for visual_asset_id in timeline.visual_asset_ids:
            visual_row = await self._visual_asset_repository.get_by_id(
                story_id, visual_asset_id
            )
            if visual_row is None:
                raise MissingRenderingInputError(
                    f"VisualAsset {visual_asset_id!r} referenced by FinalTimeline "
                    f"not found for story_id={story_id!r}"
                )
            visual_bytes = await self._asset_storage.load(visual_row.storage_key)
            visual_files.append(
                self._write_temp_file(visual_bytes, suffix=".visual")
            )

        music_files: list[str] = []
        for music_asset_id in timeline.music_asset_ids:
            music_row = await self._music_asset_repository.get_by_id(
                story_id, music_asset_id
            )
            if music_row is None:
                raise MissingRenderingInputError(
                    f"MusicAsset {music_asset_id!r} referenced by FinalTimeline "
                    f"not found for story_id={story_id!r}"
                )
            music_bytes = await self._asset_storage.load(music_row.storage_key)
            music_files.append(
                self._write_temp_file(music_bytes, suffix=".music")
            )

        voice_files = [
            self._write_temp_file(segment.audio, suffix=".voice")
            for segment in voice_track.segments
        ]

        output_path = self._build_output_path(story_id)
        command = self._build_ffmpeg_command(
            visual_files=visual_files,
            voice_files=voice_files,
            music_files=music_files,
            output_path=output_path,
        )

        await self._ffmpeg_runner.run(command)

        return output_path

    def _write_temp_file(self, data: bytes, suffix: str) -> str:
        Path(self._output_dir).mkdir(parents=True, exist_ok=True)
        path = os.path.join(self._output_dir, f"{uuid.uuid4().hex}{suffix}")
        with open(path, "wb") as f:
            f.write(data)
        return path

    def _build_output_path(self, story_id: str | UUID) -> str:
        Path(self._output_dir).mkdir(parents=True, exist_ok=True)
        return os.path.join(self._output_dir, f"{story_id}.mp4")

    def _build_ffmpeg_command(
        self,
        visual_files: list[str],
        voice_files: list[str],
        music_files: list[str],
        output_path: str,
    ) -> list[str]:
        command = ["ffmpeg", "-y"]
        for f in visual_files:
            command += ["-i", f]
        for f in voice_files:
            command += ["-i", f]
        for f in music_files:
            command += ["-i", f]
        command += [output_path]
        return command
