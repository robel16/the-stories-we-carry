# Architecture

## Overview
`storyboard.json` is the single source of truth between every stage. All stages read `storyboard.json`, validate against `schema/storyboard.schema.json`, and write deterministic artifacts to `assets/` and `outputs/`.

```text
storyboard.json ──► pipeline/validate.py (JSON Schema + timing + path safety)
       │
       ├──► pipeline/narration.py  ──► assets/narration/scene-01..06.wav (Gemini TTS)
       ├──► pipeline/music.py      ──► assets/music/ambient.wav (or Kaggle ACE-Step 1.5)
       ├──► pipeline/images.py     ──► assets/images/scene-01..06.png (Cloudflare FLUX.1)
       ├──► kaggle/heritage_short_gpu.ipynb ──► outputs/video/scene-01..06.mp4 (Wan 2.2)
       │
       └──► pipeline/assembly.py   ──► outputs/audio/radio_cut.wav
                                   ──► outputs/video/rough_cut.mp4
                                   ──► outputs/final/the_stories_we_carry.mp4 (9:16)
                                   ──► outputs/final/the_stories_we_carry_16x9.mp4 (16:9)
```

## Stage Contracts & Validation
- **Schema (`schema/storyboard.schema.json`)**: Enforces `aspect_ratio` (`9:16` or `16:9`), `target_duration_seconds` (60–90s), `narration_language` (`am`), `subtitle_language` (`en`), 5–10 scenes, and non-empty prompts/paths.
- **Semantic Checks (`pipeline/validate.py`)**: Verifies total scene duration matches `target_duration_seconds` (75s), scene IDs are unique, subtitle timestamps fall within each scene's duration, and asset paths do not escape `PROJECT_ROOT`.

## Caching & Incremental Regeneration
- `pipeline/tracking.py` implements `StageCache` backed by `outputs/.stage_cache.json`.
- Each shot/stage computes a 16-char SHA-256 hash of its inputs (prompt, text, model, voice, dimensions, and source mtimes).
- Changing a single scene's prompt or narration line in `storyboard.json` invalidates only that scene's cache key; all other shots hit `[CACHE HIT]` and are skipped.

## Logging & Failure Handling
- Every model call and FFmpeg render appends a JSON line to `runs.jsonl` (`timestamp`, `stage`, `scene_id`, `model`, `parameters`, `seed`, `latency_seconds`, `estimated_cost_usd`, `status`, `output_path`).
- **Rate Limits**: `pipeline/narration.py` catches HTTP `429 RESOURCE_EXHAUSTED` (Gemini TTS free tier = 3 RPM), sleeps 35s, and retries up to 3 times.
- **Video Fallback**: `pipeline/assembly.py` uses Kaggle Wan 2.2 clips (`outputs/video/scene-XX.mp4`) when present and falls back to FFmpeg Ken Burns (`zoompan`) if GPU clips are unavailable.
- **Audio Mixing**: `sidechaincompress` (`threshold=0.02:ratio=6:attack=300:release=1500`) ducks the score under narration, followed by `loudnorm=I=-14:TP=-1.0:LRA=11`.
