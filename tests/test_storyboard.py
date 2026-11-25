
import copy

from pipeline.storyboard import load_storyboard
from pipeline.validate import validate_storyboard


def get_storyboard():
    return load_storyboard()


def test_current_storyboard_is_valid():
    data = get_storyboard()

    errors = validate_storyboard(data)

    assert errors == []


def test_total_duration_must_match_target():
    data = get_storyboard()
    data["scenes"][0]["duration_seconds"] = 15

    errors = validate_storyboard(data)

    assert any("Total scene duration" in error for error in errors)


def test_scene_ids_must_be_unique():
    data = get_storyboard()
    data["scenes"][1]["id"] = data["scenes"][0]["id"]

    errors = validate_storyboard(data)

    assert any("Scene IDs must be unique" in error for error in errors)


def test_subtitle_cannot_exceed_scene_duration():
    data = get_storyboard()
    data["scenes"][0]["subtitles"][0]["end_seconds"] = 20

    errors = validate_storyboard(data)

    assert any("beyond scene duration" in error for error in errors)


def test_invalid_schema_data_is_rejected():
    data = get_storyboard()
    data["unexpected_field"] = "not allowed"

    errors = validate_storyboard(data)

    assert len(errors) > 0


def test_subtitle_must_end_after_start():
    data = get_storyboard()
    data["scenes"][0]["subtitles"][0]["start_seconds"] = 8
    data["scenes"][0]["subtitles"][0]["end_seconds"] = 5

    errors = validate_storyboard(data)

    assert any("must end after it starts" in error for error in errors)
