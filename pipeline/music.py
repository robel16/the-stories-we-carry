import argparse
import math
import struct
import time
import wave
from pathlib import Path

from pipeline.storyboard import DEFAULT_STORYBOARD, load_storyboard
from pipeline.tracking import log_run


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RATE = 44100


def _resolve_music_path(relative_path_str: str, project_root: Path = PROJECT_ROOT) -> Path:
    """Resolve the music asset path safely inside the project root."""
    relative_path = Path(relative_path_str)
    if relative_path.is_absolute():
        raise ValueError(f"Absolute music paths are not allowed: {relative_path_str}")

    resolved = (project_root / relative_path).resolve()
    if not resolved.is_relative_to(project_root.resolve()):
        raise ValueError(f"Music path escapes project directory: {relative_path_str}")

    return resolved


def _synthesize_ambient_pad(duration_seconds: float, output_path: Path) -> None:
    """
    Synthesize a warm, contemplative stereo ambient pad WAV.

    Uses a slow pentatonic-inspired harmonic drone (D3, A3, E4, F#4, A4)
    with gentle LFO breathing so it sits softly underneath narration.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total_frames = int(duration_seconds * SAMPLE_RATE)

    # Warm frequencies (Hz) with subtle stereo detuning and slow amplitude LFOs.
    voices = [
        (146.83, 0.34, 0.05, 0.0, -0.15),   # D3 root
        (220.00, 0.24, 0.07, 1.1, 0.15),    # A3 fifth
        (293.66, 0.16, 0.09, 2.3, -0.25),   # D4 octave
        (329.63, 0.11, 0.06, 3.7, 0.30),    # E4 ninth
        (369.99, 0.09, 0.08, 4.9, -0.35),   # F#4 major third
        (440.00, 0.06, 0.04, 0.6, 0.20),    # A4 shimmer
    ]

    two_pi = 2.0 * math.pi
    amplitude_scale = 0.28 * 32767.0
    chunk_frames = 4096

    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)

        for start_frame in range(0, total_frames, chunk_frames):
            end_frame = min(start_frame + chunk_frames, total_frames)
            buffer = bytearray()

            for frame_idx in range(start_frame, end_frame):
                t = frame_idx / SAMPLE_RATE
                left = 0.0
                right = 0.0

                for freq, weight, lfo_hz, phase, pan in voices:
                    lfo = 0.65 + 0.35 * math.sin(two_pi * lfo_hz * t + phase)
                    tone = (
                        0.82 * math.sin(two_pi * freq * t + phase)
                        + 0.18 * math.sin(two_pi * (freq * 2.0) * t + phase * 0.5)
                    )
                    sample = weight * lfo * tone
                    left += sample * (0.5 - 0.5 * pan)
                    right += sample * (0.5 + 0.5 * pan)

                # Soft edge de-click (50ms) at start and end.
                edge_env = 1.0
                if t < 0.05:
                    edge_env = t / 0.05
                elif duration_seconds - t < 0.05:
                    edge_env = max(0.0, (duration_seconds - t) / 0.05)

                left_i16 = max(-32767, min(32767, int(left * edge_env * amplitude_scale)))
                right_i16 = max(-32767, min(32767, int(right * edge_env * amplitude_scale)))
                buffer.extend(struct.pack("<hh", left_i16, right_i16))

            wav_file.writeframes(bytes(buffer))


def generate_ambient_music(
    storyboard_path: Path = DEFAULT_STORYBOARD,
    overwrite: bool = False,
) -> Path:
    """Generate the ambient background music WAV specified in storyboard.json."""
    storyboard = load_storyboard(storyboard_path)
    project_root = storyboard_path.resolve().parent

    music_cfg = storyboard["music"]
    duration_seconds = float(storyboard["project"]["target_duration_seconds"])
    output_path = _resolve_music_path(music_cfg["path"], project_root)

    if output_path.is_file() and not overwrite:
        print(
            f"[SKIP] Music already exists: {output_path.relative_to(project_root)}"
        )
        return output_path

    print(
        f"Synthesizing {duration_seconds:.1f}s ambient soundtrack -> "
        f"{output_path.relative_to(project_root)}..."
    )
    t0 = time.monotonic()
    _synthesize_ambient_pad(duration_seconds, output_path)
    log_run(
        stage="music",
        model="procedural-pentatonic-pad",
        parameters={"duration_seconds": duration_seconds, "sample_rate": SAMPLE_RATE},
        latency_seconds=time.monotonic() - t0,
        estimated_cost_usd=0.0,
        status="success",
        output_path=str(output_path.relative_to(project_root)),
    )
    print(
        f"[OK] Music saved: {output_path.relative_to(project_root)} "
        f"({output_path.stat().st_size:,} bytes)"
    )

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate ambient background music for the storyboard."
    )
    parser.add_argument(
        "--storyboard",
        type=Path,
        default=DEFAULT_STORYBOARD,
        help="Path to storyboard JSON.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate ambient music even if it already exists.",
    )

    args = parser.parse_args()
    generate_ambient_music(
        storyboard_path=args.storyboard,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
