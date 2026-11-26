from pathlib import Path

from pipeline.assembly import generate_srt
from pipeline.tracking import StageCache, compute_input_hash, log_run


def test_input_hash_is_deterministic():
    h1 = compute_input_hash({"prompt": "a", "seed": 1})
    h2 = compute_input_hash({"seed": 1, "prompt": "a"})
    h3 = compute_input_hash({"prompt": "b", "seed": 1})

    assert h1 == h2
    assert h1 != h3


def test_stage_cache_roundtrip(tmp_path: Path):
    cache_file = tmp_path / "cache.json"
    output_file = tmp_path / "scene-01.wav"
    output_file.write_bytes(b"data")

    cache = StageCache(cache_file)
    assert not cache.is_fresh("narration:scene-01", "abc123", output_file)

    cache.update("narration:scene-01", "abc123")
    reloaded = StageCache(cache_file)
    assert reloaded.is_fresh("narration:scene-01", "abc123", output_file)
    assert not reloaded.is_fresh("narration:scene-01", "changed", output_file)


def test_log_run_appends_jsonl(tmp_path: Path):
    log_path = tmp_path / "runs.jsonl"
    log_run(
        stage="narration",
        scene_id="scene-01",
        model="gemini-2.5-flash-preview-tts",
        latency_seconds=1.234,
        status="success",
        log_path=log_path,
    )
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert '"scene_id": "scene-01"' in lines[0]


def test_generate_srt_creates_valid_cues(tmp_path: Path):
    srt_path = tmp_path / "subtitles.srt"
    generate_srt(output_path=srt_path)
    content = srt_path.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:10,000" in content
    assert "Our stories live in the things we carry." in content
