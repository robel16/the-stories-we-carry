# Ethics, Consent & Licences

## Consent & Likeness
- **No real person's face, likeness, or cloned voice is used in this film.**
- `scene-01` explicitly depicts only indistinct silhouettes with no visible facial features.
- `scene-02` shows anonymous elderly hands pouring coffee with no identifiable face.
- Narration uses a synthetic prebuilt voice (`Charon` via Gemini TTS) rather than voice cloning of any real individual.

## AI Disclosure & Labelling
- **Visible End Card**: Both the `9:16` and `16:9` final MP4s include a 2.5-second closing end card stating `"Made with AI"`.
- **Platform Disclosure**: When publishing to YouTube, TikTok, or Meta, the platform's AI-generated content label is enabled.
- **Provenance**: No watermarks or provenance metadata are stripped.

## Model & Output Licences
| Component | Model / Tool | Licence / Terms |
| :--- | :--- | :--- |
| Moving Shots (Kaggle) | `Wan-AI/Wan2.2-TI2V-5B` | Apache 2.0 |
| Score (Kaggle) | `ACE-Step/ACE-Step-1.5` | MIT (outputs usable commercially) |
| Keyframes | `FLUX.1 schnell` (Cloudflare Workers AI) | Apache 2.0 |
| Narration | Gemini `gemini-2.5-flash-preview-tts` | Google Gemini API Terms |
| Assembly & Subtitles | FFmpeg | LGPL / GPL |
