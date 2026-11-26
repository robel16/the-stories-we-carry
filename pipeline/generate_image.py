
import base64
import subprocess
import time
from pathlib import Path

import requests
from google import genai
from google.genai import types

from pipeline.config import get_cloudflare_credentials, get_gemini_api_key
from pipeline.storyboard import load_storyboard
from pipeline.tracking import StageCache, compute_input_hash, log_run


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL = "@cf/black-forest-labs/flux-1-schnell"
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
# SEED = 1001
STEPS = 4


def _generate_gemini_image_bytes(prompt: str) -> bytes:
    """Generate an image using Google Gemini image generation."""
    client = genai.Client(
        api_key=get_gemini_api_key(),
        http_options={"api_version": "v1beta"},
    )
    response = client.models.generate_content(
        model=GEMINI_IMAGE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            if inline_data and getattr(inline_data, "data", None):
                return bytes(inline_data.data)
    raise RuntimeError("Gemini did not return image data.")


def generate_scene_image(scene_id: str, provider: str = "cloudflare") -> Path:
    """Generate one storyboard scene image using Cloudflare Workers AI or Gemini."""

    storyboard = load_storyboard()

    scene = next(
        (item for item in storyboard["scenes"] if item["id"] == scene_id),
        None,
    )

    if scene is None:
        raise ValueError(f"Scene not found: {scene_id}")

    prompt = scene["visual"]["prompt"]
    relative_path = Path(scene["visual"]["image_path"])

    if relative_path.is_absolute():
        raise ValueError("Absolute image paths are not allowed.")

    output_path = (PROJECT_ROOT / relative_path).resolve()

    if not output_path.is_relative_to(PROJECT_ROOT.resolve()):
        raise ValueError("Image output path escapes the project directory.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    model_used = GEMINI_IMAGE_MODEL if provider == "gemini" else MODEL
    t0 = time.monotonic()

    if provider == "gemini":
        print(f"Generating image for {scene_id}...")
        print(f"Model: {GEMINI_IMAGE_MODEL}")
        image_bytes = _generate_gemini_image_bytes(prompt)
    else:
        account_id, api_token = get_cloudflare_credentials()
        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{account_id}/ai/run/{MODEL}"
        )

        print(f"Generating image for {scene_id}...")
        print(f"Model: {MODEL}")
        # print(f"Seed: {SEED}")

        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            json={
                "prompt": prompt,
                # "seed": SEED,
                "steps": STEPS,
            },
            timeout=180,
        )

        if not response.ok:
            raise RuntimeError(
                f"Cloudflare API error ({response.status_code}): "
                f"{response.text[:1000]}"
            )

        try:
            result = response.json()
            image_base64 = result["result"]["image"]
            image_bytes = base64.b64decode(image_base64, validate=True)
        except (ValueError, KeyError, TypeError) as exc:
            raise RuntimeError(
                "Cloudflare returned an unexpected image response."
            ) from exc

    if not image_bytes:
        raise RuntimeError("Provider returned an empty image.")

    # FLUX.1 schnell returns JPEG image data.
    temporary_jpeg = output_path.with_name(
        output_path.stem + ".cloudflare.jpg"
    )

    try:
        temporary_jpeg.write_bytes(image_bytes)

        if output_path.suffix.lower() in {".png", ".webp"}:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loglevel", "error",
                    "-i", str(temporary_jpeg),
                    "-frames:v", "1",
                    str(output_path),
                ],
                check=True,
            )
        else:
            temporary_jpeg.replace(output_path)

    finally:
        if temporary_jpeg.exists():
            temporary_jpeg.unlink()

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("Image generation completed without a valid file.")

    latency = time.monotonic() - t0
    input_hash = compute_input_hash({"prompt": prompt, "provider": provider, "model": model_used})
    StageCache().update(f"image:{scene_id}", input_hash)
    log_run(
        stage="keyframes",
        scene_id=scene_id,
        model=model_used,
        parameters={"steps": STEPS if provider == "cloudflare" else None, "provider": provider},
        latency_seconds=latency,
        estimated_cost_usd=0.0,
        status="success",
        output_path=str(output_path.relative_to(PROJECT_ROOT)),
    )

    print(f"Image saved: {output_path.relative_to(PROJECT_ROOT)}")
    print(f"File size: {output_path.stat().st_size:,} bytes")

    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a storyboard scene image."
    )
    parser.add_argument(
        "scene_id",
        help="Scene ID from storyboard.json",
    )
    parser.add_argument(
        "--provider",
        choices=["cloudflare", "gemini"],
        default="cloudflare",
        help="Image generation provider (default: cloudflare).",
    )

    args = parser.parse_args()
    generate_scene_image(args.scene_id, provider=args.provider)
