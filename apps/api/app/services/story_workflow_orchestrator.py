from app.domain.story_workflow import StoryStatus


class StoryWorkflowOrchestrator:
    def __init__(
        self,
        workflow_service,
        generation_service,
        repository,
        script_generation_service,
        editing_service,
        voice_generation_service,
        visual_planning_service=None,
        visual_generation_service=None,
        music_planning_service=None,
        music_generation_service=None,
        assembly_service=None,
        visual_asset_repository=None,
        music_asset_repository=None,
        final_timeline_repository=None,
    ):
        self._workflow_service = workflow_service
        self._generation_service = generation_service
        self._repository = repository
        self._script_generation_service = script_generation_service
        self._editing_service = editing_service
        self._voice_generation_service = voice_generation_service
        self._visual_planning_service = visual_planning_service
        self._visual_generation_service = visual_generation_service
        self._music_planning_service = music_planning_service
        self._music_generation_service = music_generation_service
        self._assembly_service = assembly_service
        self._visual_asset_repository = visual_asset_repository
        self._music_asset_repository = music_asset_repository
        self._final_timeline_repository = final_timeline_repository

    async def advance_to_generation(self, story_id: str):
        analyzing_story = await self._workflow_service.transition_story(
            story_id,
            StoryStatus.ANALYZING,
        )

        dna = await self._generation_service.generate(
            story_id=story_id,
            original_idea=analyzing_story.original_idea,
        )

        await self._workflow_service.transition_story(
            story_id,
            StoryStatus.GENERATING,
        )

        try:
            await self._repository.save_dna(
                story_id,
                dna,
            )

            script = await self._script_generation_service.generate(dna)

            await self._repository.save_script(
                story_id,
                script,
            )

            edit_plan = await self._editing_service.edit(
                story_id,
                script,
            )

            await self._repository.save_edit_plan(
                story_id,
                edit_plan,
            )

            voice_track = await self._voice_generation_service.generate(
                story_id,
                script,
            )

            await self._repository.save_voice_track(
                story_id,
                voice_track,
            )

            await self._workflow_service.transition_story(
                story_id,
                StoryStatus.EDITING,
            )

        except Exception:
            await self._workflow_service.transition_story(
                story_id,
                StoryStatus.FAILED,
            )
            raise

        return {
            "dna": dna,
            "script": script,
        }


    async def advance_to_assembly(self, story_id):
        try:
            dna = await self._repository.get_dna(story_id)
            if dna is None:
                raise MissingAssemblyPreconditionError("dna missing")

            script = await self._repository.get_script(story_id)
            if script is None:
                raise MissingAssemblyPreconditionError("script missing")

            edit_plan = await self._repository.get_edit_plan(story_id)
            if edit_plan is None:
                raise MissingAssemblyPreconditionError("edit_plan missing")

            voice_track = await self._repository.get_voice_track(story_id)
            if voice_track is None:
                raise MissingAssemblyPreconditionError("voice_track missing")

            visual_assets = []
            for scene in script.scenes:
                shot_plan = await self._visual_planning_service.generate(
                    story_id, scene, dna, edit_plan
                )
                for shot in shot_plan.shots:
                    if shot.asset_type == "video":
                        asset = await self._visual_generation_service.generate_video(
                            story_id, scene.scene_number, shot
                        )
                    else:
                        asset = await self._visual_generation_service.generate_image(
                            story_id, scene.scene_number, shot
                        )
                    visual_assets.append(asset)

            music_plan = await self._music_planning_service.generate(
                story_id, script, dna, edit_plan
            )
            music_assets = []
            for cue in music_plan.cues:
                asset = await self._music_generation_service.generate(story_id, cue)
                music_assets.append(asset)

            final_timeline = await self._assembly_service.assemble(
                story_id, edit_plan, voice_track, visual_assets, music_assets
            )

            visual_asset_ids = []
            for cut in edit_plan.cuts:
                rows = await self._visual_asset_repository.list_by_scene(
                    story_id, cut.scene_number
                )
                visual_asset_ids.extend(str(row.id) for row in rows)

            music_asset_rows = await self._music_asset_repository.list_by_story(story_id)
            music_asset_ids = [str(row.id) for row in music_asset_rows]

            await self._final_timeline_repository.save(
                story_id, final_timeline, visual_asset_ids, music_asset_ids
            )

            await self._workflow_service.transition_story(story_id, StoryStatus.RENDERING)

            return final_timeline

        except Exception:
            await self._workflow_service.transition_story(story_id, StoryStatus.FAILED)
            raise


class MissingAssemblyPreconditionError(Exception):
    pass
