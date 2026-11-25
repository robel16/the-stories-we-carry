
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from pipeline.storyboard import (
    DEFAULT_SCHEMA,
    DEFAULT_STORYBOARD,
    load_schema,
    load_storyboard,
)


def validate_storyboard(
    data: dict[str, Any],
    schema_path: Path = DEFAULT_SCHEMA,
    project_root: Path | None = None,
    check_assets: bool = False,
) -> list[str]:
    """
    Validate storyboard structure and semantic constraints.

    Subtitle timestamps are relative to the beginning of each scene.
    Asset existence checks are optional because assets are generated later.
    """
    errors: list[str] = []

    try:
        schema = load_schema(schema_path)
    except ValueError as exc:
        return [str(exc)]

    validator = Draft202012Validator(schema)

    for error in sorted(
        validator.iter_errors(data),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    ):
        location = ".".join(str(part) for part in error.absolute_path)
        location = location or "storyboard"

        errors.append(f"{location}: {error.message}")

    # Do not perform semantic checks on structurally invalid data.
    if errors:
        return errors

    scenes = data["scenes"]
    project = data["project"]

    # Check total duration.
    total_duration = sum(
        scene["duration_seconds"] for scene in scenes
    )
    target_duration = project["target_duration_seconds"]

    if abs(total_duration - target_duration) > 0.01:
        errors.append(
            f"Total scene duration is {total_duration}s, "
            f"but target duration is {target_duration}s."
        )

    # Check scene IDs are unique.
    scene_ids = [scene["id"] for scene in scenes]

    if len(scene_ids) != len(set(scene_ids)):
        errors.append("Scene IDs must be unique.")

    # Check subtitle timing within each scene.
    for scene in scenes:
        scene_id = scene["id"]
        scene_duration = scene["duration_seconds"]

        for index, subtitle in enumerate(scene["subtitles"], start=1):
            start = subtitle["start_seconds"]
            end = subtitle["end_seconds"]

            if start >= end:
                errors.append(
                    f"{scene_id}: subtitle {index} must end "
                    "after it starts."
                )

            if end > scene_duration:
                errors.append(
                    f"{scene_id}: subtitle {index} ends at {end}s, "
                    f"beyond scene duration of {scene_duration}s."
                )

    # Optional checks for files that must exist before rendering.
    if check_assets:
        root = project_root or DEFAULT_STORYBOARD.parent

        asset_paths = [
            ("music", data["music"]["path"])
        ]

        for scene in scenes:
            scene_id = scene["id"]

            asset_paths.extend([
                (
                    f"{scene_id} image",
                    scene["visual"]["image_path"],
                ),
                (
                    f"{scene_id} narration",
                    scene["narration"]["audio_path"],
                ),
            ])

        for description, relative_path in asset_paths:
            asset_path = Path(relative_path)

            if asset_path.is_absolute():
                errors.append(
                    f"{description}: absolute asset paths are not allowed: "
                    f"{relative_path}"
                )
                continue

            resolved_path = (root / asset_path).resolve()

            if not resolved_path.is_relative_to(root.resolve()):
                errors.append(
                    f"{description}: asset path escapes project directory: "
                    f"{relative_path}"
                )
            elif not resolved_path.is_file():
                errors.append(
                    f"{description}: asset file does not exist: "
                    f"{relative_path}"
                )

    return errors


def validate_file(
    storyboard_path: Path = DEFAULT_STORYBOARD,
    check_assets: bool = False,
) -> list[str]:
    """Load and validate a storyboard file."""
    try:
        data = load_storyboard(storyboard_path)
    except ValueError as exc:
        return [str(exc)]

    return validate_storyboard(
        data,
        project_root=storyboard_path.resolve().parent,
        check_assets=check_assets,
    )


def print_validation_report(errors: list[str]) -> None:
    """Print a human-readable validation report."""
    print("\n=== STORYBOARD VALIDATION REPORT ===")

    if errors:
        print(f"FAILED: {len(errors)} issue(s) found.\n")

        for index, error in enumerate(errors, start=1):
            print(f"{index}. {error}")

        print("\nStoryboard is not ready for rendering.")
    else:
        print("PASSED: No validation errors found.")
        print("Storyboard is ready for the next pipeline stage.")

    print("===================================\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate The Stories We Carry storyboard."
    )
    parser.add_argument(
        "--storyboard",
        type=Path,
        default=DEFAULT_STORYBOARD,
        help="Path to storyboard JSON.",
    )
    parser.add_argument(
        "--check-assets",
        action="store_true",
        help="Also verify that referenced asset files exist.",
    )

    args = parser.parse_args()

    errors = validate_file(
        args.storyboard,
        check_assets=args.check_assets,
    )

    print_validation_report(errors)

    raise SystemExit(1 if errors else 0)
