import argparse
from pathlib import Path

from pipeline.generate_image import MODEL, generate_scene_image
from pipeline.storyboard import DEFAULT_STORYBOARD, load_storyboard
from pipeline.tracking import StageCache, compute_input_hash


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def generate_all_images(
    storyboard_path: Path = DEFAULT_STORYBOARD,
    overwrite: bool = False,
) -> list[Path]:
    """Generate keyframe images for all scenes in storyboard.json."""
    storyboard = load_storyboard(storyboard_path)
    project_root = storyboard_path.resolve().parent
    cache = StageCache()
    generated: list[Path] = []

    for scene in storyboard["scenes"]:
        scene_id = scene["id"]
        rel_path = Path(scene["visual"]["image_path"])
        output_path = (project_root / rel_path).resolve()
        cache_key = f"image:{scene_id}"
        input_hash = compute_input_hash({
            "prompt": scene["visual"]["prompt"],
            "provider": "cloudflare",
            "model": MODEL,
        })

        if output_path.is_file() and not overwrite:
            if cache.is_fresh(cache_key, input_hash, output_path):
                print(f"[CACHE HIT] {scene_id}: {rel_path}")
                generated.append(output_path)
                continue
            if cache_key not in cache._data:
                cache.update(cache_key, input_hash)
                print(
                    f"[SKIP] {scene_id}: {rel_path} already exists "
                    f"({output_path.stat().st_size:,} bytes)"
                )
                generated.append(output_path)
                continue

        generated.append(generate_scene_image(scene_id))

    return generated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate keyframe images for storyboard scenes."
    )
    parser.add_argument(
        "--storyboard",
        type=Path,
        default=DEFAULT_STORYBOARD,
        help="Path to storyboard JSON.",
    )
    parser.add_argument(
        "--scene",
        help="Optional single scene ID to generate (defaults to all scenes).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate existing keyframe images.",
    )

    args = parser.parse_args()

    if args.scene:
        generate_scene_image(args.scene)
    else:
        generate_all_images(
            storyboard_path=args.storyboard,
            overwrite=args.overwrite,
        )


if __name__ == "__main__":
    main()
