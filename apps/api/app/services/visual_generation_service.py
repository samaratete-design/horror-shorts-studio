from shared_types.visual_asset import VisualAsset


class VisualGenerationError(Exception):
    pass


class InvalidVisualGenerationRequestError(Exception):
    pass


class VisualGenerationService:
    def __init__(self, image_provider, video_provider):
        self._image_provider = image_provider
        self._video_provider = video_provider

    async def generate_image(self, story_id, scene_number, shot):
        if not story_id:
            raise InvalidVisualGenerationRequestError("story_id is required")
        if shot is None:
            raise InvalidVisualGenerationRequestError("shot is required")

        try:
            image_bytes = await self._image_provider.generate(
                shot.visual_prompt,
                "9:16",
            )
        except Exception as exc:
            raise VisualGenerationError(str(exc)) from exc

        return VisualAsset(
            story_id=story_id,
            scene_number=scene_number,
            shot_number=shot.shot_number,
            asset_type="image",
            asset=image_bytes,
            actual_duration=None,
        )

    async def generate_video(self, story_id, scene_number, shot):
        if not story_id:
            raise InvalidVisualGenerationRequestError("story_id is required")
        if shot is None:
            raise InvalidVisualGenerationRequestError("shot is required")

        try:
            generated_video = await self._video_provider.generate(
                shot.visual_prompt,
                shot.estimated_duration,
            )
        except Exception as exc:
            raise VisualGenerationError(str(exc)) from exc

        return VisualAsset(
            story_id=story_id,
            scene_number=scene_number,
            shot_number=shot.shot_number,
            asset_type="video",
            asset=generated_video.video,
            actual_duration=generated_video.duration,
        )
