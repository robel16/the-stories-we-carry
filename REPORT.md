# The Stories We Carry — Project Report

## 1. What I Set Out to Make and for Whom
**The Stories We Carry** is a 75-second heritage short film (77.5s including the closing AI disclosure card) narrated in Amharic (`am`) with English subtitles (`en`), exported in both vertical (`9:16`, `1080x1920`) and horizontal (`16:9`, `1920x1080`).

- **Audience**: Ethiopian families and diaspora viewers watching on mobile phones (`9:16`) and desktop/YouTube (`16:9`).
- **Intent**: Evoke quiet warmth, nostalgia, and continuity—showing how everyday objects (a faded sepia family photo, a clay *jebena*, a woven *mesob*, a mountain path, and a handwritten Amharic letter) carry family values from one generation to the next.
- **Pipeline Goal**: Build a reproducible, contract-driven studio in code (`storyboard.json` + `schema/storyboard.schema.json`) where a single command (`python -m pipeline.cli film` or `make film`) validates, generates/caches assets, mixes audio, burns subtitles, and exports both aspect ratios while logging every model call to `runs.jsonl`.

---

## 2. What I Learned from My Audience (User Tests & Changes)
I tested the film at two checkpoints with three reviewers from the intended audience (documented in `DESIGN.md`):

### Test 1 — Phase 1 Radio Cut (`outputs/audio/radio_cut.wav`)
- **What they said**:
  - Minor Amharic pronunciation and stress issues on a few words in the Gemini TTS (`Charon`) output, and the overall piece felt concise/short.
  - Slight voice-tone shifts between separately generated scene clips (`scene-01` through `scene-06`).
  - The ambient score needed to dip more clearly underneath spoken lines so quiet syllables stayed intelligible.
- **What changed**:
  - Added explicit reflective pacing instructions in `pipeline/narration.py` and logged Amharic TTS prosody/voice-consistency limits in `DESIGN.md` / `FAILURES.md`.
  - Replaced static `amix` volume with FFmpeg `sidechaincompress` ducking (`threshold=0.02:ratio=6:attack=300:release=1500`) and `-14 LUFS` `loudnorm` normalization in `pipeline/assembly.py`.

### Test 2 — Near-Final Visual Cut (`outputs/video/rough_cut.mp4` & Final Exports)
- **What they said**:
  - Noticed awkward hand-gesture motion artifacts when objects were handled, and flagged that the `scene-05` handwritten letter originally showed unreadable non-Amharic text.
  - The initial 2–3s Wan 2.2 clips visibly repeated/looped inside the 12.5s slots, transitions felt abrupt, and the first subtitle pass rendered oversized, bold text in the middle of the screen.
  - One exported MP4 failed to open in Windows Media Player ("Unsupported") due to `yuv444p` (`High 4:4:4 Predictive`) pixel format output from the subtitle filter.
- **What changed**:
  - **Scene 05 Amharic Script**: Replaced the gibberish writing on `scene-05.png` with authentic Amharic Ge'ez Fidel script (`ያለፈውን የምንሸከመው / ለወደፊቱ እንድንሰጥ ነው።`).
  - **Continuous Motion (No Loops)**: Measured each Kaggle Wan 2.2 clip's exact duration (`3.38s` for `scene-01`, `2.04s` for `scene-02..06`) and stretched it into a single forward slow-motion pass (`setpts` + `minterpolate=fps=30:mi_mode=blend`), combined with `0.8s` `xfade` cross-dissolves and a subtle vignette.
  - **Subtitles & Playback**: Switched to explicit `.ass` `PlayResX`/`PlayResY` styling (`Bold=0`, bottom-center `Alignment=2`, safe-area `MarginV`) and forced `yuv420p` (`High` profile) + `-movflags +faststart`.

---

## 3. Hardest Problems and How I Solved Them
1. **Kaggle 2× T4 Kernel Restarts (RAM/VRAM OOM) & Dependency Breakage**:
   - `ACE-Step-1.5` failed to install on Kaggle's Python 3.13.16 runtime because `nano-vllm` had no Python 3.13 wheel. Rather than burning hours debugging Python environments, I dropped `ace-step` from the Kaggle run and kept the local procedural score with FFmpeg ducking.
   - `Wan-AI/Wan2.2-TI2V-5B` initially returned `404` (`-Diffusers` suffix required: `Wan-AI/Wan2.2-TI2V-5B-Diffusers`) and crashed Kaggle's 30 GB CPU RAM during 81-frame VAE decoding. Enabling `pipe.vae.enable_tiling()`, switching to `torch.float16` + `enable_sequential_cpu_offload()`, reducing to `NUM_FRAMES=49` / `20` steps, and saving each `.mp4` immediately after generation allowed all 6 scenes to complete across resumes without losing progress.
2. **Rendering Authentic Amharic Script in `scene-05`**:
   - Prompting `FLUX.1 schnell` with `"Amharic Ethiopic Ge'ez Fidel script"` still produced pseudo-Latin gibberish. Solving it required a targeted image-editing pass using exact Unicode Ge'ez lines while keeping the lighting and wooden box intact.
3. **Eliminating Video Looping Without Re-generating Longer GPU Clips**:
   - Looping 2–3s Wan 2.2 clips inside 12.5s slots looked visibly repetitive. Dynamically computing `pts_scale = target_duration / clip_duration` per scene and blending frames forward in a single pass eliminated all visible loop seams.

---

## 4. Suggested Practices Tested Honestly
- **What beat my instinct — A strict JSON contract (`storyboard.json`) + SHA-256 input-hash caching (`StageCache`) + Radio Cut first**:
  - My instinct was to jump straight into generating visuals and video clips. Building `storyboard.json` + `pipeline/validate.py` + `StageCache` (`outputs/.stage_cache.json`) first felt like extra boilerplate, but it paid off immediately: when `scene-05` needed fixing or `assembly.py` needed subtitle/codec tweaks, unchanged narration and image stages hit `[CACHE HIT]` in under a second without wasting API quotas or rate-limited Gemini TTS calls.
- **What did not work as expected — Relying on text-to-image prompting for non-Latin script & unpinned open-weight music stacks**:
  - Even detailed negative/positive prompts in `FLUX.1 schnell` could not reliably render Amharic Fidel script on paper (`scene-05`), and `ACE-Step-1.5` broke on Kaggle's default Python 3.13 image. Both confirmed the guide's warning: handle text in code (subtitles/titles) or targeted edits, and always keep a deterministic local fallback ready.

---

## 5. Curiosity Beyond the Floor (Ceiling Work)
- **Hybrid Multi-Provider Orchestration**: Combined Gemini `v1beta` TTS (Amharic), Cloudflare Workers AI (`FLUX.1 schnell`), targeted image editing (`scene-05`), and Kaggle 2× T4 open-weight **Wan 2.2 TI2V-5B** video generation under a single unified CLI (`pipeline/cli.py`).
- **Temporal Motion Engineering**: Built automatic fallback logic in `pipeline/assembly.py` that detects Kaggle Wan 2.2 clips when present, stretches each clip cleanly to its exact scene duration with `minterpolate` frame blending (zero loop jumps), and falls back to 2× supersampled Ken Burns pan-and-zoom if GPU clips are absent.
- **Full Dual-Format Mastering**: Automated `sidechaincompress` ducking, `-14 LUFS` `loudnorm`, safe-area `.ass` subtitle rendering, and `yuv420p` `+faststart` export for both `9:16` and `16:9`.

---

## 6. What I Would Build Next
1. **Multi-Take Amharic TTS Auditioning**: Generate 2–3 takes per line and add an automated silence-trim + prosody/speaker-consistency check with native-speaker sign-off.
2. **Pinned Python 3.11 Container for ACE-Step 1.5**: Run `ACE-Step 1.5` in a pinned 3.11 environment so *krar* and *washint* instrumental candidates can be auditioned alongside the procedural score.
3. **Character & Object Reference Sheet + 8–12 Tighter Cuts**: Split 12.5s scenes into 5–6s shots conditioned on a shared style/character reference sheet so Wan 2.2 clips play at native 1×–2× speed with zero slow-motion stretching.
