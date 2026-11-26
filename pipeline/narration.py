import argparse
import re
import time
import wave
from pathlib import Path

from google import genai
from google.genai import errors, types

from pipeline.config import get_gemini_api_key
from pipeline.storyboard import DEFAULT_STORYBOARD, load_storyboard
from pipeline.tracking import StageCache, compute_input_hash, log_run


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "gemini-2.5-flash-preview-tts"
DEFAULT_VOICE = "Charon"
DEFAULT_SAMPLE_RATE = 24000


def _resolve_asset_path(relative_path_str: str, project_root: Path = PROJECT_ROOT) -> Path:
    """Resolve a storyboard asset path safely inside the project root."""
    relative_path = Path(relative_path_str)
    if relative_path.is_absolute():
        raise ValueError(f"Absolute asset paths are not allowed: {relative_path_str}")

    resolved = (project_root / relative_path).resolve()
    if not resolved.is_relative_to(project_root.resolve()):
        raise ValueError(f"Asset path escapes project directory: {relative_path_str}")

    return resolved


def _parse_sample_rate(mime_type: str | None) -> int:
    """Extract sample rate from an audio MIME type, defaulting to 24000 Hz."""
    if not mime_type:
        return DEFAULT_SAMPLE_RATE
    match = re.search(r"rate=(\d+)", mime_type)
    return int(match.group(1)) if match else DEFAULT_SAMPLE_RATE


def _write_wav_bytes(output_path: Path, audio_bytes: bytes, mime_type: str | None) -> None:
    """Write raw PCM or WAV audio bytes to a valid 16-bit PCM WAV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if audio_bytes.startswith(b"RIFF"):
        output_path.write_bytes(audio_bytes)
        return

    sample_rate = _parse_sample_rate(mime_type)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_bytes)


def get_wav_duration_seconds(wav_path: Path) -> float:
    """Return the duration in seconds of a WAV file."""
    with wave.open(str(wav_path), "rb") as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        return frames / float(rate)


def _extract_audio_part(response: types.GenerateContentResponse) -> tuple[bytes, str | None]:
    """Extract inline audio bytes and MIME type from a Gemini response."""
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            if inline_data and getattr(inline_data, "data", None):
                return bytes(inline_data.data), getattr(inline_data, "mime_type", None)

    raise RuntimeError("Gemini TTS response did not contain audio data.")


def generate_scene_narration(
    scene_id: str,
    storyboard_path: Path = DEFAULT_STORYBOARD,
    model: str = DEFAULT_MODEL,
    voice_name: str = DEFAULT_VOICE,
    overwrite: bool = False,
) -> Path:
    """Generate narration WAV audio for a single storyboard scene using Gemini TTS."""
    storyboard = load_storyboard(storyboard_path)
    project_root = storyboard_path.resolve().parent

    scene = next(
        (item for item in storyboard["scenes"] if item["id"] == scene_id),
        None,
    )
    if scene is None:
        raise ValueError(f"Scene not found: {scene_id}")

    output_path = _resolve_asset_path(scene["narration"]["audio_path"], project_root)
    cache = StageCache()
    cache_key = f"narration:{scene_id}"
    input_hash = compute_input_hash({
        "text": scene["narration"]["text"],
        "model": model,
        "voice": voice_name,
    })

    if output_path.is_file() and not overwrite:
        if cache.is_fresh(cache_key, input_hash, output_path):
            duration = get_wav_duration_seconds(output_path)
            print(
                f"[CACHE HIT] {scene_id}: {output_path.relative_to(project_root)} "
                f"({duration:.2f}s / {scene['duration_seconds']}s)"
            )
            return output_path
        if cache_key not in cache._data:
            cache.update(cache_key, input_hash)
            duration = get_wav_duration_seconds(output_path)
            print(
                f"[SKIP] {scene_id}: {output_path.relative_to(project_root)} "
                f"already exists ({duration:.2f}s / {scene['duration_seconds']}s)"
            )
            return output_path

    text = scene["narration"]["text"]
    prompt = (
        "Read the following Amharic narration aloud warmly, clearly, and "
        "at a calm, reflective storytelling pace:\n\n"
        f"{text}"
    )

    client = genai.Client(
        api_key=get_gemini_api_key(),
        http_options={"api_version": "v1beta"},
    )
    print(f"Generating narration for {scene_id} (voice={voice_name}, model={model})...")

    t0 = time.monotonic()
    response = None
    for attempt in range(1, 5):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name,
                            )
                        )
                    ),
                ),
            )
            break
        except errors.ClientError as exc:
            if exc.code == 429 and attempt < 4:
                wait_seconds = 35
                print(f"[RATE LIMIT] {scene_id}: waiting {wait_seconds}s before retry ({attempt}/3)...")
                time.sleep(wait_seconds)
            else:
                log_run(
                    stage="narration",
                    scene_id=scene_id,
                    model=model,
                    parameters={"voice": voice_name, "language": "am"},
                    latency_seconds=time.monotonic() - t0,
                    status="error",
                    note=str(exc)[:200],
                )
                raise

    assert response is not None
    latency = time.monotonic() - t0
    audio_bytes, mime_type = _extract_audio_part(response)
    _write_wav_bytes(output_path, audio_bytes, mime_type)
    cache.update(cache_key, input_hash)
    log_run(
        stage="narration",
        scene_id=scene_id,
        model=model,
        parameters={"voice": voice_name, "language": "am", "text_len": len(text)},
        latency_seconds=latency,
        estimated_cost_usd=0.0,
        status="success",
        output_path=str(output_path.relative_to(project_root)),
    )

    duration = get_wav_duration_seconds(output_path)
    scene_duration = float(scene["duration_seconds"])
    status = "OK" if duration <= scene_duration else "WARNING: EXCEEDS SCENE DURATION"
    print(
        f"[{status}] {scene_id}: saved {output_path.relative_to(project_root)} "
        f"({duration:.2f}s / {scene_duration:.2f}s)"
    )

    return output_path


def generate_all_narration(
    storyboard_path: Path = DEFAULT_STORYBOARD,
    model: str = DEFAULT_MODEL,
    voice_name: str = DEFAULT_VOICE,
    overwrite: bool = False,
) -> list[Path]:
    """Generate narration WAV audio for all scenes in the storyboard."""
    storyboard = load_storyboard(storyboard_path)
    generated: list[Path] = []

    for scene in storyboard["scenes"]:
        path = generate_scene_narration(
            scene_id=scene["id"],
            storyboard_path=storyboard_path,
            model=model,
            voice_name=voice_name,
            overwrite=overwrite,
        )
        generated.append(path)

    return generated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Amharic narration audio for storyboard scenes."
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
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini TTS model (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help=f"Prebuilt voice name (default: {DEFAULT_VOICE}).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate existing narration files.",
    )

    args = parser.parse_args()

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


if __name__ == "__main__":
    main()
