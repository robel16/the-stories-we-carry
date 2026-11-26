# The Stories We Carry

A 75-second heritage short film narrated in Amharic (`am`) with English (`en`) subtitles, original score, and a reproducible, contract-driven Python + FFmpeg + Kaggle GPU pipeline.

## Quickstart (One-Command Run)

```bash
# 1. Configure .env from .env.example (GEMINI_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN)
# 2. Run the entire pipeline end-to-end:
python -m pipeline.cli film
# or with GNU Make:
make film
```

This validates `storyboard.json`, generates/caches Amharic narration, ambient music, and keyframes, applies sidechain audio ducking + `-14 LUFS` loudness normalization, burns in English subtitles, appends a 2.5s `"Made with AI"` end card, and exports **both** aspect ratios:
- Vertical (`9:16`, `1080x1920`): `outputs/final/the_stories_we_carry.mp4`
- Horizontal (`16:9`, `1920x1080`): `outputs/final/the_stories_we_carry_16x9.mp4`

## Kaggle GPU Upgrade (Wan 2.2 TI2V-5B + ACE-Step 1.5)

To replace the local Ken Burns motion and procedural score with open-weight GPU video and music:
1. Upload the repo to a **Kaggle 2× T4** notebook and run `kaggle/heritage_short_gpu.ipynb`.
2. Download `kaggle_outputs.zip` (`outputs/video/scene-01.mp4`…`scene-06.mp4`, `assets/music/candidate_*.wav`, `runs.jsonl`) and extract it into the repo root.
3. Re-run `python -m pipeline.cli film` — `pipeline/assembly.py` automatically detects `outputs/video/scene-XX.mp4` and adapts it to both `9:16` and `16:9`.

## Pipeline Commands

| Command | Purpose |
| :--- | :--- |
| `python -m pipeline.cli validate --check-assets` | Validate `storyboard.json` schema, timing, and asset paths |
| `python -m pipeline.cli phase1` | Validate, generate narration + music, assemble `outputs/audio/radio_cut.wav` |
| `python -m pipeline.cli phase2` | Generate keyframes, validate assets, assemble `outputs/video/rough_cut.mp4` |
| `python -m pipeline.cli film` | Full end-to-end build (`9:16` and `16:9` final MP4s) |
| `python -m pytest` | Run unit tests |

## Cost Summary
All local/hosted steps used free tiers (`$0.00` out-of-pocket): Gemini TTS free tier, Cloudflare Workers AI free daily allowance, local FFmpeg, and Kaggle 2× T4 weekly quota. See `COSTS.md` for measured latency and list-price equivalents.
