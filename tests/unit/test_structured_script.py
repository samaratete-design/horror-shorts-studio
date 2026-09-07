from shared_types.structured_script import (
    DialogueLine,
    SceneItem,
    StructuredScript,
)


def test_structured_script_validates_nested_scene_data():
    payload = {
        "title": "الباب الأخير",
        "logline": "رجل يسمع طرقًا على باب شقته رغم أنه يعيش وحده.",
        "tone": "psychological horror",
        "language": "ar",
        "estimated_duration": 45.0,
        "scenes": [
            {
                "scene_number": 1,
                "purpose": "Establish the mystery",
                "location": "شقة قديمة",
                "time_of_day": "night",
                "characters": ["أحمد"],
                "action": "أحمد يجلس وحده ويسمع طرقًا على الباب.",
                "dialogue": [
                    {
                        "character": "أحمد",
                        "line": "مين؟",
                        "emotion": "terrified",
                    }
                ],
                "narration": "كان أحمد متأكدًا أنه يعيش وحده.",
                "emotion": "fear",
                "estimated_duration": 12.5,
            }
        ],
    }

    script = StructuredScript.model_validate(payload)

    assert script.title == "الباب الأخير"
    assert script.language == "ar"
    assert script.estimated_duration == 45.0
    assert len(script.scenes) == 1

    scene = script.scenes[0]
    assert scene.scene_number == 1
    assert scene.characters == ["أحمد"]
    assert len(scene.dialogue) == 1
    assert scene.dialogue[0].character == "أحمد"
    assert scene.dialogue[0].emotion == "terrified"


def test_structured_script_defaults_language_to_ar():
    script = StructuredScript.model_validate(
        {
            "title": "Test",
            "logline": "A horror story.",
            "tone": "horror",
            "estimated_duration": 30.0,
            "scenes": [],
        }
    )

    assert script.language == "ar"


def test_scene_dialogue_defaults_to_empty_list():
    scene = SceneItem.model_validate(
        {
            "scene_number": 1,
            "purpose": "Opening",
            "location": "Apartment",
            "time_of_day": "night",
            "characters": ["Ahmed"],
            "action": "Ahmed enters.",
            "emotion": "fear",
            "estimated_duration": 5.0,
        }
    )

    assert scene.dialogue == []
    assert scene.narration is None
