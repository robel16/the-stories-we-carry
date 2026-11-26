# Costs & Latency

## Measured Execution (`runs.jsonl` & Local Benchmarks)
| Stage | Provider / Model | Calls | Avg Latency | Out-of-Pocket Cost |
| :--- | :--- | :--- | :--- | :--- |
| Narration (`am`) | Gemini `gemini-2.5-flash-preview-tts` (Free Tier) | 6 | ~3.5s / scene | `$0.00` |
| Keyframes | Cloudflare `@cf/black-forest-labs/flux-1-schnell` (Free Tier) | 6 | ~2.5s / image | `$0.00` |
| Music (Local) | Procedural Pentatonic Pad (`pipeline/music.py`) | 1 | ~6s total | `$0.00` |
| Moving Shots (Local Fallback) | FFmpeg Ken Burns (`1080x1920` & `1920x1080`) | 12 | ~10s / clip | `$0.00` |
| Moving Shots (Kaggle GPU) | `Wan-AI/Wan2.2-TI2V-5B` (2× T4, 480p, 30 steps) | 6 | ~4–6 GPU min / clip | `$0.00` (30 hrs/wk quota) |
| Score Candidates (Kaggle GPU) | `ACE-Step/ACE-Step-1.5` (2× T4, 75s, 27 steps) | 3 | ~0.5 GPU min / track | `$0.00` (30 hrs/wk quota) |

## List-Price Equivalent Estimate
- **Cloudflare FLUX.1 Schnell (6 images)**: ~$0.01–$0.02 equivalent.
- **Gemini TTS (6 short clips, ~25s total audio)**: <$0.01 equivalent.
- **Hosted T4 GPU (~30 GPU min for Wan 2.2 + ACE-Step)**: ~$0.15–$0.25 at ~$0.35/hr cloud T4 rates.
- **Total Estimated List-Price Equivalent**: **~$0.20–$0.30** per full run.
