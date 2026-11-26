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
- **Format**: Played audio-only mix (Amharic narration over ambient score) to reviewers to test pacing, pronunciation, and emotional tone before visual assembly.
- **Observations & Changes**:
  - Each narration clip (`2.73s`–`5.61s`) sits cleanly inside its `12.50s` slot, leaving breathing room for the music and visual reflection.
  - Switched from static `amix` volume to `sidechaincompress` ducking in Phase 3 so the score stays warm during pauses and drops smoothly under speech.

### Test 2: Near-Final Visual Cut (`outputs/video/rough_cut.mp4`)
- **Observations & Changes**:
  - **Scene 05 Text Fix**: Initial Cloudflare FLUX.1 generation rendered gibberish pseudo-Latin characters on the handwritten letter. Replaced with authentic Amharic Ge'ez Fidel script (`ያለፈውን የምንሸከመው / ለወደፊቱ እንድንሰጥ ነው።`) so the visual matches the Amharic narration.
  - **Subtitles & End Card**: Added safe-area English subtitles (`max 2 lines`, `<= 40 chars/line`) and a 2.5s `"Made with AI"` end card for both `9:16` and `16:9` exports.
