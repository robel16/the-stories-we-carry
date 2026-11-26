# Experiments Log

1. **Gemini API Version for TTS (`v1` vs `v1beta`)**
   - *Hypothesis*: `google-genai==3.6.1` supports `gemini-2.5-flash-preview-tts` with `speech_config` on the default client.
   - *Change*: Switched `genai.Client` `http_options` from default (`v1`) to `{"api_version": "v1beta"}`.
   - *Result*: Resolved `400 Unknown name "speechConfig"` and `404 NOT_FOUND`; all 6 Amharic narration clips generated cleanly.

2. **Amharic TTS Pacing & Slot Fit (`Charon` voice)**
   - *Hypothesis*: Prompting Gemini TTS with a calm, reflective storytelling instruction keeps Amharic clips under 12.5s.
   - *Change*: Added pacing instruction to `pipeline/narration.py` and measured WAV durations.
   - *Result*: All 6 clips measured between `2.73s` and `5.61s`, leaving `6.9s–9.8s` of breathing room per scene.

3. **Rate-Limit Handling on Gemini Free Tier**
   - *Hypothesis*: Sequential generation of 6 clips hits the 3 RPM free-tier ceiling on `scene-04` or `scene-06`.
   - *Change*: Added automatic 35s backoff + retry on HTTP `429 RESOURCE_EXHAUSTED` combined with input-hash caching.
   - *Result*: Re-running skipped cached scenes `01–05` and completed `scene-06` in a single request.

4. **FLUX.1 Schnell for Amharic Text in `scene-05`**
   - *Hypothesis*: Explicitly prompting `flux-1-schnell` with `"Amharic Ethiopic Ge'ez Fidel script, no English"` produces readable Amharic handwriting.
   - *Change*: Updated `scene-05` prompt in `storyboard.json` and regenerated.
   - *Result*: Rejected—`flux-1-schnell` still produced gibberish pseudo-Latin glyphs.

5. **Targeted Image Editing for `scene-05` Amharic Script**
   - *Hypothesis*: Using an instruction-following image editor with the exact 4-line Ge'ez text replaces gibberish while preserving lighting and box framing.
   - *Change*: Edited `scene-05.png` with exact Amharic lines (`ያለፈውን የምንሸከመው / ለወደፊቱ እንድንሰጥ ነው። / ታሪኮቻችን በምንይዘው / ነገር ውስጥ ይኖራሉ።`).
   - *Result*: Readable Amharic Fidel script rendered in dark ink on the aged paper.

6. **Privacy & Likeness Safety in `scene-01` Prompting**
   - *Hypothesis*: Describing people in the sepia photograph as indistinct silhouettes avoids generating identifiable faces.
   - *Change*: Used `"indistinct silhouettes with no visible facial features"` in `scene-01` (`scene-01-refined.png`).
   - *Result*: Warm, nostalgic composition with zero identifiable faces.

7. **Ken Burns `zoompan` Resolution (1x vs 2x Supersampling)**
   - *Hypothesis*: Running FFmpeg `zoompan` directly on `1080x1920` causes subpixel shimmer.
   - *Change*: Upscaled/cropped to `2160x3840` (2× target) before `zoompan`, alternating zoom-in and zoom-out across scenes.
   - *Result*: Smooth, jitter-free 30fps motion in `rough_cut.mp4`.

8. **Static Music Volume vs Sidechain Ducking**
   - *Hypothesis*: Fixed `volume=0.18` either masks quiet syllables or feels too quiet during pauses.
   - *Change*: Added FFmpeg `sidechaincompress` (`threshold=0.02:ratio=6:attack=300:release=1500`) driven by the narration stem.
   - *Result*: Music stays present between lines and ducks smoothly under Amharic narration.

9. **Loudness Normalization (`loudnorm` -14 LUFS)**
   - *Hypothesis*: Raw `amix` output varies below streaming targets.
   - *Change*: Added `loudnorm=I=-14:TP=-1.0:LRA=11` to the final audio mix.
   - *Result*: Consistent broadcast/social loudness without clipping.

10. **Input-Hash Caching for Single-Shot Re-renders**
    - *Hypothesis*: Hashing per-scene prompts, narration text, and mtimes in `outputs/.stage_cache.json` enables live single-shot regeneration.
    - *Change*: Implemented `StageCache` in `pipeline/tracking.py` across narration, keyframes, and video clips.
    - *Result*: Re-running `python -m pipeline.cli film` skips unchanged stages (`[CACHE HIT]`) in seconds.
