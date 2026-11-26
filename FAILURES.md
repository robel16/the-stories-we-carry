# Failures & Troubleshooting Journal

1. **Gemini TTS `400 Unknown name "speechConfig"` & `404 NOT_FOUND`**
   - *What broke*: `google-genai==3.6.1` defaults to API version `v1`, where `gemini-2.5-flash-preview-tts` and `speechConfig` are not exposed.
   - *Fix*: Passed `http_options={"api_version": "v1beta"}` to `genai.Client(...)` in `pipeline/narration.py`.

2. **Gemini TTS `429 RESOURCE_EXHAUSTED` (3 RPM Free Tier)**
   - *What broke*: Generating all 6 scenes back-to-back exceeded the 3 requests/minute free-tier limit on `scene-06`.
   - *Fix*: Added `StageCache` skip-if-exists + automatic 35s retry backoff on HTTP `429` in `pipeline/narration.py`.

3. **Gemini Image Generation Quota (`limit: 0`)**
   - *What broke*: Calling `gemini-2.5-flash-image` returned `429 RESOURCE_EXHAUSTED` with `limit: 0` on the free-tier API key.
   - *Fix*: Used Cloudflare Workers AI (`@cf/black-forest-labs/flux-1-schnell`) for batch keyframes and targeted image editing for `scene-05` Amharic text.

4. **FLUX.1 Schnell Gibberish Text on `scene-05`**
   - *What broke*: Even with explicit `"Amharic Ethiopic Ge'ez Fidel script"` prompting, `flux-1-schnell` rendered pseudo-Latin/gibberish characters on the letter.
   - *Fix*: Replaced the paper text via an image-editing pass using exact Unicode Ge'ez lines, then re-rendered `scene-05`.

5. **Sandbox Network Blocking (`getaddrinfo failed`)**
   - *What broke*: Running API-dependent scripts inside the restricted terminal sandbox failed DNS resolution for `generativelanguage.googleapis.com` and `api.cloudflare.com`.
   - *Fix*: Kept local processing (music synthesis, validation, FFmpeg assembly, pytest) sandboxed and ran only external API calls outside the sandbox.

6. **PowerShell 5.1 Command Chaining (`&&` Parse Error)**
   - *What broke*: `&&` is invalid in Windows PowerShell 5.1.
   - *Fix*: Used `;` for sequential commands in PowerShell and provided `Makefile` / `python -m pipeline.cli film` as cross-platform entrypoints.
