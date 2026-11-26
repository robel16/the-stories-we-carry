import argparse
import subprocess
import textwrap
import time
import wave
from pathlib import Path

from pipeline.storyboard import DEFAULT_STORYBOARD, load_storyboard
from pipeline.tracking import StageCache, compute_input_hash, log_run


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RADIO_CUT = PROJECT_ROOT / "outputs" / "audio" / "radio_cut.wav"
DEFAULT_DUCKED_AUDIO = PROJECT_ROOT / "outputs" / "audio" / "final_mix.wav"
DEFAULT_ROUGH_CUT = PROJECT_ROOT / "outputs" / "video" / "rough_cut.mp4"
DEFAULT_SRT_PATH = PROJECT_ROOT / "outputs" / "subtitles" / "subtitles.srt"
VIDEO_CLIPS_DIR = PROJECT_ROOT / "outputs" / "video"
FINAL_DIR = PROJECT_ROOT / "outputs" / "final"

ASPECT_DIMENSIONS = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
}


def _resolve_asset(relative_path_str: str, project_root: Path) -> Path:
    """Resolve an asset path safely inside the project root."""
    rel = Path(relative_path_str)
    if rel.is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {relative_path_str}")
    resolved = (project_root / rel).resolve()
    if not resolved.is_relative_to(project_root.resolve()):
        raise ValueError(f"Asset path escapes project directory: {relative_path_str}")
    if not resolved.is_file():
        raise FileNotFoundError(f"Required asset is missing: {relative_path_str}")
    return resolved


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        return wav_file.getnframes() / float(wav_file.getframerate())


def _video_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1",
            str(path),
        ],
        text=True,
    ).strip()
    return max(0.5, float(out))


def _format_srt_time(seconds: float) -> str:
    ms_total = max(0, int(round(seconds * 1000)))
    hours, rem = divmod(ms_total, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _format_ass_time(seconds: float) -> str:
    cs_total = max(0, int(round(seconds * 100)))
    hours, rem = divmod(cs_total, 360_000)
    minutes, rem = divmod(rem, 6_000)
    secs, cs = divmod(rem, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def generate_ass(
    storyboard_path: Path,
    output_path: Path,
    width: int,
    height: int,
    margin_v: int,
) -> Path:
    """Generate an ASS subtitle file with exact PlayRes so font size & bottom placement are accurate."""
    storyboard = load_storyboard(storyboard_path)
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    font_size = 38 if width < height else 34
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "WrapStyle: 0\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
        f"0,0,0,0,100,100,0,0,1,1.8,0.8,2,60,60,{margin_v},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    events: list[str] = []
    offset = 0.0
    for scene in storyboard["scenes"]:
        for sub in scene["subtitles"]:
            start = offset + float(sub["start_seconds"])
            end = offset + float(sub["end_seconds"])
            wrapped = "\\N".join(textwrap.wrap(sub["text"].strip(), width=42)[:2])
            events.append(
                f"Dialogue: 0,{_format_ass_time(start)},{_format_ass_time(end)},Default,,0,0,0,,{wrapped}"
            )
        offset += float(scene["duration_seconds"])

    output_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return output_path


def generate_srt(
    storyboard_path: Path = DEFAULT_STORYBOARD,
    output_path: Path = DEFAULT_SRT_PATH,
) -> Path:
    """Generate an SRT subtitle file with max 2 lines (~40 chars/line) per cue."""
    storyboard = load_storyboard(storyboard_path)
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    cue_index = 1
    offset = 0.0

    for scene in storyboard["scenes"]:
        for sub in scene["subtitles"]:
            start = offset + float(sub["start_seconds"])
            end = offset + float(sub["end_seconds"])
            wrapped = textwrap.wrap(sub["text"].strip(), width=40)[:2]
            lines.append(str(cue_index))
            lines.append(f"{_format_srt_time(start)} --> {_format_srt_time(end)}")
            lines.extend(wrapped)
            lines.append("")
            cue_index += 1
        offset += float(scene["duration_seconds"])

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Subtitles saved: {output_path} ({cue_index - 1} cues)")
    return output_path


def _build_audio_mix(
    storyboard_path: Path,
    output_path: Path,
    duck: bool,
) -> Path:
    """Mix timed narration with music (optionally sidechain-ducked and -14 LUFS normalized)."""
    storyboard = load_storyboard(storyboard_path)
    project_root = storyboard_path.resolve().parent

    music_cfg = storyboard["music"]
    music_path = _resolve_asset(music_cfg["path"], project_root)
    total_duration = float(storyboard["project"]["target_duration_seconds"])
    music_volume = float(music_cfg["volume"])
    fade_in = float(music_cfg["fade_in_seconds"])
    fade_out = float(music_cfg["fade_out_seconds"])
    fade_out_start = max(0.0, total_duration - fade_out)

    scenes = storyboard["scenes"]
    narration_inputs: list[tuple[str, Path, float, float]] = []
    current_offset = 0.0

    for scene in scenes:
        scene_id = scene["id"]
        scene_dur = float(scene["duration_seconds"])
        narration_path = _resolve_asset(scene["narration"]["audio_path"], project_root)
        narration_inputs.append((scene_id, narration_path, current_offset, scene_dur))
        current_offset += scene_dur

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd: list[str] = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(music_path)]
    for _, narration_path, _, _ in narration_inputs:
        cmd.extend(["-i", str(narration_path)])

    filter_parts: list[str] = [
        (
            f"[0:a]aresample=44100,aformat=channel_layouts=stereo,"
            f"apad=whole_dur={total_duration:.3f},"
            f"atrim=0:{total_duration:.3f},"
            f"volume={music_volume:.3f},"
            f"afade=t=in:st=0:d={fade_in:.3f},"
            f"afade=t=out:st={fade_out_start:.3f}:d={fade_out:.3f}[music]"
        )
    ]

    narration_labels: list[str] = []
    for idx, (_, _, offset_sec, _) in enumerate(narration_inputs, start=1):
        delay_ms = int(round(offset_sec * 1000))
        label = f"[n{idx}]"
        filter_parts.append(
            f"[{idx}:a]aresample=44100,aformat=channel_layouts=stereo,"
            f"adelay={delay_ms}|{delay_ms}{label}"
        )
        narration_labels.append(label)

    n_count = len(narration_labels)
    if duck:
        # Build narration stem, split for sidechain trigger + mix, then duck music and normalize to -14 LUFS.
        filter_parts.append(
            f"{''.join(narration_labels)}amix=inputs={n_count}:duration=longest:"
            f"dropout_transition=0:normalize=0,apad=whole_dur={total_duration:.3f},"
            f"atrim=0:{total_duration:.3f},asplit=2[narr_trig][narr_mix]"
        )
        filter_parts.append(
            "[music][narr_trig]sidechaincompress=threshold=0.02:ratio=6:"
            "attack=300:release=1500[ducked_music]"
        )
        filter_parts.append(
            "[ducked_music][narr_mix]amix=inputs=2:duration=first:"
            "dropout_transition=0:normalize=0,"
            "loudnorm=I=-14:TP=-1.0:LRA=11[out]"
        )
    else:
        mix_labels = ["[music]"] + narration_labels
        filter_parts.append(
            f"{''.join(mix_labels)}amix=inputs={1 + n_count}:duration=first:"
            f"dropout_transition=0:normalize=0,alimiter=limit=0.95[out]"
        )

    cmd.extend([
        "-filter_complex",
        ";".join(filter_parts),
        "-map",
        "[out]",
        "-t",
        f"{total_duration:.3f}",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ])

    t0 = time.monotonic()
    subprocess.run(cmd, check=True)
    log_run(
        stage="audio_mix",
        model="ffmpeg-sidechain-loudnorm" if duck else "ffmpeg-amix",
        parameters={"duck": duck, "target_lufs": -14 if duck else None},
        latency_seconds=time.monotonic() - t0,
        status="success",
        output_path=str(output_path),
    )
    return output_path


def assemble_radio_cut(
    storyboard_path: Path = DEFAULT_STORYBOARD,
    output_path: Path = DEFAULT_RADIO_CUT,
) -> Path:
    """Assemble Phase 1 radio cut: timed narration tracks mixed with ambient music."""
    out = _build_audio_mix(storyboard_path, output_path, duck=False)
    print(f"[OK] Radio cut saved: {out} ({_wav_duration(out):.2f}s, {out.stat().st_size:,} bytes)")
    return out


def _animate_scene_still(
    image_path: Path,
    clip_path: Path,
    duration_seconds: float,
    width: int,
    height: int,
    fps: int,
    zoom_in: bool,
) -> None:
    """Animate a still keyframe into a slow pan-and-zoom MP4 clip."""
    clip_path.parent.mkdir(parents=True, exist_ok=True)
    frames = max(1, int(round(duration_seconds * fps)))
    upscale_w = width * 2
    upscale_h = height * 2
    zoom_expr = f"1+0.10*on/{frames}" if zoom_in else f"1.10-0.10*on/{frames}"

    vf = (
        f"scale={upscale_w}:{upscale_h}:force_original_aspect_ratio=increase,"
        f"crop={upscale_w}:{upscale_h},setsar=1,"
        f"zoompan=z='{zoom_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={width}x{height}:fps={fps},"
        f"format=yuv420p"
    )

    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-loop", "1", "-i", str(image_path),
            "-vf", vf,
            "-t", f"{duration_seconds:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            str(clip_path),
        ],
        check=True,
    )


def _prepare_scene_clip(
    scene: dict,
    idx: int,
    project_root: Path,
    width: int,
    height: int,
    fps: int,
    aspect_tag: str,
) -> Path:
    """
    Use a Kaggle Wan 2.2 clip if present in outputs/video/{id}.mp4,
    otherwise animate the keyframe still with FFmpeg Ken Burns.
    Caches rendered clips by input hash so unchanged scenes are skipped.
    """
    scene_id = scene["id"]
    duration = float(scene["duration_seconds"])
    kaggle_clip = (VIDEO_CLIPS_DIR / f"{scene_id}.mp4").resolve()
    rendered_clip = (VIDEO_CLIPS_DIR / f"{scene_id}_{aspect_tag}.mp4").resolve()
    image_path = _resolve_asset(scene["visual"]["image_path"], project_root)

    cache = StageCache()
    cache_key = f"clip:{aspect_tag}:{scene_id}"
    use_kaggle = kaggle_clip.is_file() and kaggle_clip != rendered_clip
    input_hash = compute_input_hash({
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "image_mtime": image_path.stat().st_mtime_ns,
        "kaggle_mtime": kaggle_clip.stat().st_mtime_ns if use_kaggle else None,
    })

    if cache.is_fresh(cache_key, input_hash, rendered_clip):
        print(f"  [CACHE HIT] {scene_id} ({aspect_tag})")
        return rendered_clip

    t0 = time.monotonic()
    if use_kaggle:
        clip_dur = _video_duration(kaggle_clip)
        pts_scale = max(1.0, duration / clip_dur)
        print(
            f"  Using Kaggle moving shot (single forward {pts_scale:.1f}x slow-mo) "
            f"for {scene_id} ({aspect_tag})..."
        )
        # Stretch clip to fill exact scene duration in one continuous forward pass (no loop, no reverse).
        vf = (
            f"setpts={pts_scale:.4f}*PTS,"
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,"
            f"minterpolate=fps={fps}:mi_mode=blend,"
            f"format=yuv420p"
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(kaggle_clip),
                "-vf", vf,
                "-t", f"{duration:.3f}",
                "-an", "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
                "-preset", "medium", "-crf", "20",
                str(rendered_clip),
            ],
            check=True,
        )
        source_model = "wan2.2-kaggle-slowmo"
    else:
        print(f"  Animating still for {scene_id} ({aspect_tag}, {duration:.2f}s)...")
        _animate_scene_still(
            image_path=image_path,
            clip_path=rendered_clip,
            duration_seconds=duration,
            width=width,
            height=height,
            fps=fps,
            zoom_in=(idx % 2 == 0),
        )
        source_model = "ffmpeg-ken-burns"

    cache.update(cache_key, input_hash)
    log_run(
        stage="video_clip",
        scene_id=scene_id,
        model=source_model,
        parameters={"width": width, "height": height, "fps": fps, "duration": duration},
        latency_seconds=time.monotonic() - t0,
        status="success",
        output_path=str(rendered_clip.relative_to(project_root)),
    )
    return rendered_clip


def _render_ai_end_card(
    output_path: Path,
    title: str,
    width: int,
    height: int,
    fps: int = 30,
    duration_seconds: float = 2.5,
) -> Path:
    """Render a 2.5s visible AI disclosure end card with silent stereo audio."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    safe_title = title.replace(":", "\\:").replace("'", "")
    win_font = Path("C:/Windows/Fonts/arial.ttf")
    font_opt = f"fontfile='{win_font.as_posix().replace(':', chr(92) + ':')}':" if win_font.is_file() else ""
    vf = (
        f"drawtext={font_opt}text='{safe_title}':fontcolor=0xF5EFE6:fontsize={int(height * 0.032)}:"
        f"x=(w-text_w)/2:y=(h-text_h)/2-{int(height * 0.04)},"
        f"drawtext={font_opt}text='Made with AI':fontcolor=0xD4A373:fontsize={int(height * 0.024)}:"
        f"x=(w-text_w)/2:y=(h-text_h)/2+{int(height * 0.03)},"
        f"fade=t=in:st=0:d=0.4,fade=t=out:st={duration_seconds - 0.5:.2f}:d=0.5,format=yuv420p"
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c=0x14100D:s={width}x{height}:r={fps}:d={duration_seconds}",
            "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100",
            "-vf", vf,
            "-t", f"{duration_seconds:.2f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-shortest",
            str(output_path),
        ],
        check=True,
    )
    return output_path


def assemble_rough_cut(
    storyboard_path: Path = DEFAULT_STORYBOARD,
    radio_cut_path: Path = DEFAULT_RADIO_CUT,
    output_path: Path = DEFAULT_ROUGH_CUT,
    fps: int = 30,
) -> Path:
    """Assemble Phase 2 rough visual cut: animated keyframes + Phase 1 radio cut."""
    storyboard = load_storyboard(storyboard_path)
    project_root = storyboard_path.resolve().parent
    aspect = storyboard["project"]["aspect_ratio"]
    aspect_tag = aspect.replace(":", "x")
    width, height = ASPECT_DIMENSIONS[aspect]

    radio_cut_path = radio_cut_path.resolve()
    if not radio_cut_path.is_file():
        assemble_radio_cut(storyboard_path=storyboard_path, output_path=radio_cut_path)

    print(f"\n=== PREPARING CLIPS ({width}x{height} @ {fps}fps) ===")
    clips = [
        _prepare_scene_clip(scene, idx, project_root, width, height, fps, aspect_tag)
        for idx, scene in enumerate(storyboard["scenes"])
    ]

    concat_list = (VIDEO_CLIPS_DIR / f"concat_{aspect_tag}.txt").resolve()
    concat_list.write_text(
        "\n".join(f"file '{c.as_posix()}'" for c in clips) + "\n",
        encoding="utf-8",
    )

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-i", str(radio_cut_path),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
            str(output_path),
        ],
        check=True,
    )
    print(f"[OK] Rough cut saved: {output_path} ({output_path.stat().st_size:,} bytes)")
    return output_path


def assemble_final_film(
    storyboard_path: Path = DEFAULT_STORYBOARD,
    fps: int = 30,
) -> list[Path]:
    """
    Assemble Phase 3 final film in BOTH 9:16 and 16:9 aspect ratios:
    - Sidechain-ducked score under narration, normalized to -14 LUFS
    - Burned-in English subtitles inside safe area
    - Visible 2.5s 'Made with AI' end card
    """
    storyboard = load_storyboard(storyboard_path)
    project_root = storyboard_path.resolve().parent
    title = storyboard["project"]["title"]
    base_name = Path(storyboard["project"]["output_filename"]).stem

    srt_path = generate_srt(storyboard_path, DEFAULT_SRT_PATH)
    ducked_audio = _build_audio_mix(storyboard_path, DEFAULT_DUCKED_AUDIO, duck=True)

    outputs: list[Path] = []
    targets = [
        ("9:16", "9x16", FINAL_DIR / f"{base_name}.mp4", 120),
        ("16:9", "16x9", FINAL_DIR / f"{base_name}_16x9.mp4", 50),
    ]

    for aspect, tag, final_mp4, margin_v in targets:
        width, height = ASPECT_DIMENSIONS[aspect]
        print(f"\n=== ASSEMBLING FINAL FILM ({aspect} / {width}x{height}) ===")
        fade_dur = 0.8
        scenes = storyboard["scenes"]
        clips: list[Path] = []
        for idx, scene in enumerate(scenes):
            # Pad non-final scenes by fade_dur so xfade dissolves keep total duration = 75.0s
            padded_scene = dict(scene)
            if idx < len(scenes) - 1:
                padded_scene["duration_seconds"] = float(scene["duration_seconds"]) + fade_dur
            clips.append(
                _prepare_scene_clip(padded_scene, idx, project_root, width, height, fps, tag)
            )

        ass_path = generate_ass(
            storyboard_path,
            PROJECT_ROOT / "outputs" / "subtitles" / f"subtitles_{tag}.ass",
            width=width,
            height=height,
            margin_v=margin_v,
        )
        ass_escaped = ass_path.as_posix().replace(":", "\\:")

        # Chain smooth xfade dissolves between all 6 clips, add subtle film vignette, and burn ASS subtitles.
        cmd_body: list[str] = ["ffmpeg", "-y", "-loglevel", "error"]
        for c in clips:
            cmd_body.extend(["-i", str(c)])
        cmd_body.extend(["-i", str(ducked_audio)])

        xfade_filters: list[str] = []
        prev_label = "[0:v]"
        cumulative_offset = 0.0
        for idx in range(len(clips) - 1):
            cumulative_offset += float(scenes[idx]["duration_seconds"])
            out_label = f"[v{idx + 1}]"
            xfade_filters.append(
                f"{prev_label}[{idx + 1}:v]xfade=transition=dissolve:"
                f"duration={fade_dur:.2f}:offset={cumulative_offset:.2f}{out_label}"
            )
            prev_label = out_label

        xfade_filters.append(
            f"{prev_label}vignette=angle=PI/6,ass='{ass_escaped}',format=yuv420p[vout]"
        )

        body_mp4 = (VIDEO_CLIPS_DIR / f"body_{tag}.mp4").resolve()
        audio_input_idx = len(clips)
        cmd_body.extend([
            "-filter_complex", ";".join(xfade_filters),
            "-map", "[vout]",
            "-map", f"{audio_input_idx}:a",
            "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-shortest",
            str(body_mp4),
        ])
        subprocess.run(cmd_body, check=True)

        end_card_mp4 = _render_ai_end_card(
            VIDEO_CLIPS_DIR / f"end_card_{tag}.mp4",
            title=title,
            width=width,
            height=height,
            fps=fps,
        )

        final_mp4.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(body_mp4),
                "-i", str(end_card_mp4),
                "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]",
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
                "-preset", "medium", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart",
                str(final_mp4),
            ],
            check=True,
        )
        print(f"[OK] Final {aspect} export: {final_mp4} ({final_mp4.stat().st_size:,} bytes)")
        outputs.append(final_mp4)

    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble radio cut, rough cut, or final dual-aspect film."
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="final",
        choices=["radio-cut", "rough-cut", "final"],
        help="Assembly mode (default: final).",
    )
    parser.add_argument("--storyboard", type=Path, default=DEFAULT_STORYBOARD)
    parser.add_argument("--output", type=Path)

    args = parser.parse_args()
    if args.mode == "radio-cut":
        assemble_radio_cut(args.storyboard, args.output or DEFAULT_RADIO_CUT)
    elif args.mode == "rough-cut":
        assemble_rough_cut(args.storyboard, output_path=args.output or DEFAULT_ROUGH_CUT)
    else:
        assemble_final_film(args.storyboard)


if __name__ == "__main__":
    main()
