# Design Document

## Audience & Intent
- **Audience**: Ethiopian families and diaspora viewers watching on mobile phones (`9:16` vertical feed) as well as YouTube/desktop (`16:9`).
- **Intent**: Evoke quiet warmth, nostalgia, and continuity—reminding viewers that everyday objects (a faded photograph, a clay *jebena*, a woven *mesob*, a handwritten Amharic letter) carry family values across generations.

## Shot-by-Shot Rationale (`storyboard.json`)
| Scene | Duration | Visual & Emotional Purpose |
| :--- | :--- | :--- |
| `scene-01` | 12.5s | Opening establishing still: faded sepia family photo on a wooden table in warm morning light, introducing the theme (*"Our stories live in the things we carry."*). |
| `scene-02` | 12.5s | Intimate close-up of elderly hands preparing coffee in a *jebena*—grounding memory in tactile ritual. |
| `scene-03` | 12.5s | Traditional woven basket and handmade fabric in a quiet home—representing values passed across generations. |
| `scene-04` | 12.5s | Wide Ethiopian highland sunrise landscape with a narrow path—symbolizing distance and never forgetting one's roots. |
| `scene-05` | 12.5s | Close-up of a handwritten Amharic letter placed in an old wooden box—connecting the past to what we leave for the future. |
| `scene-06` | 12.5s | Closing golden sunrise over an ancient Ethiopian village—leaving the viewer with hope and continuity. |

## User Testing Log

### Test 1: Phase 1 Radio Cut (`outputs/audio/radio_cut.wav`)
- **Format**: Played audio-only mix (Amharic narration over ambient score) to 3 reviewers from the intended audience to test pacing, pronunciation, and emotional tone before visual assembly.
- **Reviewer Feedback**:
  - **Reviewer 1**: Noted minor Amharic pronunciation/stress issues on a few words in the Gemini TTS (`Charon`) output, and felt the overall piece felt a bit short/concise.
  - **Reviewer 2**: Pointed out slight voice-tone shifts between separately generated scene clips (`scene-01` through `scene-06`), even though the same voice name was used.
  - **Reviewer 3**: Liked the warm, reflective pacing and 12.5s breathing room between lines, but wanted the music to dip more noticeably when the narrator speaks so quiet syllables stay clear.
- **Changes Made**:
  - Added explicit storytelling pace instructions to `pipeline/narration.py` and logged the Amharic pronunciation/voice-consistency limitations for future multi-take selection.
  - Replaced static `amix` volume with FFmpeg `sidechaincompress` ducking (`threshold=0.02:ratio=6:attack=300:release=1500`) + `-14 LUFS` `loudnorm` in `pipeline/assembly.py` so the score stays warm in pauses and ducks cleanly under the voice.

### Test 2: Near-Final Visual Cut (`outputs/video/rough_cut.mp4` & Final Exports)
- **Reviewer Feedback**:
  - **Reviewer 1**: Noticed awkward hand gesture/motion artifacts when picking up/handling objects in the moving shots and flagged that the `scene-05` letter originally had unreadable non-Amharic text.
  - **Reviewer 2**: Felt the initial 2–3s AI video clips visibly repeated/looped inside the 12.5s slots, and said the first subtitle pass was too large, bold, and sat near the center of the vertical frame.
  - **Reviewer 3**: Felt the transitions between scenes were too abrupt (slideshow-like) and wanted the film to feel more continuous and movie-like.
- **Changes Made**:
  - **Scene 05 Amharic Script**: Replaced the gibberish text on the handwritten letter in `scene-05.png` with authentic Amharic Ge'ez Fidel script (`ያለፈውን የምንሸከመው / ለወደፊቱ እንድንሰጥ ነው።`).
  - **Eliminated Looping & Hard Cuts**: Stretched each Kaggle Wan 2.2 clip into a single continuous forward slow-motion pass (`setpts` + `minterpolate=fps=30:mi_mode=blend`, zero loops/reverses) and added `0.8s` `xfade` cross-dissolves + a subtle film vignette between scenes.
  - **Subtitle & Playback Fix**: Switched to explicit `.ass` `PlayResX`/`PlayResY` styling (`Bold=0`, bottom-center `Alignment=2`, safe-area `MarginV`) and forced `yuv420p` (`High` profile) + `-movflags +faststart` for universal playback.
