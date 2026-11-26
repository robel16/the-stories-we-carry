import argparse
from pathlib import Path

from pipeline.assembly import (
    DEFAULT_RADIO_CUT,
    DEFAULT_ROUGH_CUT,
    assemble_final_film,
    assemble_radio_cut,
    assemble_rough_cut,
)
from pipeline.generate_image import generate_scene_image
from pipeline.images import generate_all_images
from pipeline.music import generate_ambient_music
from pipeline.narration import (
    DEFAULT_MODEL as DEFAULT_TTS_MODEL,
    DEFAULT_VOICE as DEFAULT_TTS_VOICE,
    generate_all_narration,
    generate_scene_narration,
)
from pipeline.storyboard import DEFAULT_STORYBOARD
from pipeline.validate import print_validation_report, validate_file


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.cli",
        description="The Stories We Carry film generation pipeline CLI.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate
    val_parser = subparsers.add_parser("validate", help="Validate storyboard.json.")
    val_parser.add_argument("--storyboard", type=Path, default=DEFAULT_STORYBOARD)
    val_parser.add_argument("--check-assets", action="store_true")

    # narration
    nar_parser = subparsers.add_parser("narration", help="Generate scene narration audio.")
    nar_parser.add_argument("--storyboard", type=Path, default=DEFAULT_STORYBOARD)
    nar_parser.add_argument("--scene", help="Single scene ID (default: all scenes).")
    nar_parser.add_argument("--model", default=DEFAULT_TTS_MODEL)
    nar_parser.add_argument("--voice", default=DEFAULT_TTS_VOICE)
    nar_parser.add_argument("--overwrite", action="store_true")

    # music
    mus_parser = subparsers.add_parser("music", help="Generate ambient background music.")
    mus_parser.add_argument("--storyboard", type=Path, default=DEFAULT_STORYBOARD)
    mus_parser.add_argument("--overwrite", action="store_true")

    # radio-cut
    rad_parser = subparsers.add_parser("radio-cut", help="Assemble Phase 1 radio cut.")
    rad_parser.add_argument("--storyboard", type=Path, default=DEFAULT_STORYBOARD)
    rad_parser.add_argument("--output", type=Path, default=DEFAULT_RADIO_CUT)

    # phase1
    p1_parser = subparsers.add_parser(
        "phase1",
        help="Run full Phase 1: validate, generate narration + music, and assemble radio cut.",
    )
    p1_parser.add_argument("--storyboard", type=Path, default=DEFAULT_STORYBOARD)
    p1_parser.add_argument("--output", type=Path, default=DEFAULT_RADIO_CUT)
    p1_parser.add_argument("--voice", default=DEFAULT_TTS_VOICE)
    p1_parser.add_argument("--overwrite", action="store_true")

    # images
    img_parser = subparsers.add_parser("images", help="Generate scene keyframe images.")
    img_parser.add_argument("--storyboard", type=Path, default=DEFAULT_STORYBOARD)
    img_parser.add_argument("--scene", help="Single scene ID (default: all scenes).")
    img_parser.add_argument("--overwrite", action="store_true")

    # rough-cut
    rc_parser = subparsers.add_parser("rough-cut", help="Assemble Phase 2 rough visual cut.")
    rc_parser.add_argument("--storyboard", type=Path, default=DEFAULT_STORYBOARD)
    rc_parser.add_argument("--radio-cut", type=Path, default=DEFAULT_RADIO_CUT)
    rc_parser.add_argument("--output", type=Path, default=DEFAULT_ROUGH_CUT)

    # phase2
    p2_parser = subparsers.add_parser(
        "phase2",
        help="Run full Phase 2: generate keyframes, validate assets, and assemble rough cut.",
    )
    p2_parser.add_argument("--storyboard", type=Path, default=DEFAULT_STORYBOARD)
    p2_parser.add_argument("--radio-cut", type=Path, default=DEFAULT_RADIO_CUT)
    p2_parser.add_argument("--output", type=Path, default=DEFAULT_ROUGH_CUT)
    p2_parser.add_argument("--overwrite", action="store_true")

    # film (end-to-end)
    film_parser = subparsers.add_parser(
        "film",
        help="Run full end-to-end pipeline: validate, narration, music, keyframes, and dual-aspect final exports.",
    )
    film_parser.add_argument("--storyboard", type=Path, default=DEFAULT_STORYBOARD)
    film_parser.add_argument("--voice", default=DEFAULT_TTS_VOICE)
    film_parser.add_argument("--overwrite", action="store_true")

    args = parser.parse_args()

    if args.command == "validate":
        errors = validate_file(args.storyboard, check_assets=args.check_assets)
        print_validation_report(errors)
        raise SystemExit(1 if errors else 0)

    if args.command == "narration":
        if args.scene:
            generate_scene_narration(
                scene_id=args.scene,
                storyboard_path=args.storyboard,
                model=args.model,
                voice_name=args.voice,
                overwrite=args.overwrite,
            )
        else:
            generate_all_narration(
                storyboard_path=args.storyboard,
                model=args.model,
                voice_name=args.voice,
                overwrite=args.overwrite,
            )
        return

    if args.command == "music":
        generate_ambient_music(
            storyboard_path=args.storyboard,
            overwrite=args.overwrite,
        )
        return

    if args.command == "radio-cut":
        assemble_radio_cut(
            storyboard_path=args.storyboard,
            output_path=args.output,
        )
        return

    if args.command == "images":
        if args.scene:
            generate_scene_image(args.scene)
        else:
            generate_all_images(
                storyboard_path=args.storyboard,
                overwrite=args.overwrite,
            )
        return

    if args.command == "rough-cut":
        assemble_rough_cut(
            storyboard_path=args.storyboard,
            radio_cut_path=args.radio_cut,
            output_path=args.output,
        )
        return

    if args.command == "film":
        errors = validate_file(args.storyboard, check_assets=False)
        print_validation_report(errors)
        if errors:
            raise SystemExit(1)

        generate_all_narration(
            storyboard_path=args.storyboard,
            voice_name=args.voice,
            overwrite=args.overwrite,
        )
        generate_ambient_music(
            storyboard_path=args.storyboard,
            overwrite=args.overwrite,
        )
        generate_all_images(
            storyboard_path=args.storyboard,
            overwrite=args.overwrite,
        )
        errors = validate_file(args.storyboard, check_assets=True)
        print_validation_report(errors)
        if errors:
            raise SystemExit(1)

        assemble_final_film(storyboard_path=args.storyboard)
        return

    if args.command == "phase2":
        generate_all_images(
            storyboard_path=args.storyboard,
            overwrite=args.overwrite,
        )
        errors = validate_file(args.storyboard, check_assets=True)
        print_validation_report(errors)
        if errors:
            raise SystemExit(1)
        assemble_rough_cut(
            storyboard_path=args.storyboard,
            radio_cut_path=args.radio_cut,
            output_path=args.output,
        )
        return

    if args.command == "film":
        errors = validate_file(args.storyboard, check_assets=False)
        print_validation_report(errors)
        if errors:
            raise SystemExit(1)

        generate_all_narration(
            storyboard_path=args.storyboard,
            voice_name=args.voice,
            overwrite=args.overwrite,
        )
        generate_ambient_music(
            storyboard_path=args.storyboard,
            overwrite=args.overwrite,
        )
        generate_all_images(
            storyboard_path=args.storyboard,
            overwrite=args.overwrite,
        )
        errors = validate_file(args.storyboard, check_assets=True)
        print_validation_report(errors)
        if errors:
            raise SystemExit(1)

        assemble_final_film(storyboard_path=args.storyboard)
        return

    if args.command == "phase1":
        errors = validate_file(args.storyboard, check_assets=False)
        print_validation_report(errors)
        if errors:
            raise SystemExit(1)

        generate_all_narration(
            storyboard_path=args.storyboard,
            voice_name=args.voice,
            overwrite=args.overwrite,
        )
        generate_ambient_music(
            storyboard_path=args.storyboard,
            overwrite=args.overwrite,
        )
        assemble_radio_cut(
            storyboard_path=args.storyboard,
            output_path=args.output,
        )
        return

    if args.command == "images":
        if args.scene:
            generate_scene_image(args.scene)
        else:
            generate_all_images(
                storyboard_path=args.storyboard,
                overwrite=args.overwrite,
            )
        return

    if args.command == "rough-cut":
        assemble_rough_cut(
            storyboard_path=args.storyboard,
            radio_cut_path=args.radio_cut,
            output_path=args.output,
        )
        return

    if args.command == "film":
        errors = validate_file(args.storyboard, check_assets=False)
        print_validation_report(errors)
        if errors:
            raise SystemExit(1)

        generate_all_narration(
            storyboard_path=args.storyboard,
            voice_name=args.voice,
            overwrite=args.overwrite,
        )
        generate_ambient_music(
            storyboard_path=args.storyboard,
            overwrite=args.overwrite,
        )
        generate_all_images(
            storyboard_path=args.storyboard,
            overwrite=args.overwrite,
        )
        errors = validate_file(args.storyboard, check_assets=True)
        print_validation_report(errors)
        if errors:
            raise SystemExit(1)

        assemble_final_film(storyboard_path=args.storyboard)
        return

    if args.command == "phase2":
        generate_all_images(
            storyboard_path=args.storyboard,
            overwrite=args.overwrite,
        )
        errors = validate_file(args.storyboard, check_assets=True)
        print_validation_report(errors)
        if errors:
            raise SystemExit(1)
        assemble_rough_cut(
            storyboard_path=args.storyboard,
            radio_cut_path=args.radio_cut,
            output_path=args.output,
        )
        return

    if args.command == "film":
        errors = validate_file(args.storyboard, check_assets=False)
        print_validation_report(errors)
        if errors:
            raise SystemExit(1)

        generate_all_narration(
            storyboard_path=args.storyboard,
            voice_name=args.voice,
            overwrite=args.overwrite,
        )
        generate_ambient_music(
            storyboard_path=args.storyboard,
            overwrite=args.overwrite,
        )
        generate_all_images(
            storyboard_path=args.storyboard,
            overwrite=args.overwrite,
        )
        errors = validate_file(args.storyboard, check_assets=True)
        print_validation_report(errors)
        if errors:
            raise SystemExit(1)

        assemble_final_film(storyboard_path=args.storyboard)


if __name__ == "__main__":
    main()
