# Content Pack Generator Design

## Goal

Build a CLI-first content pack generator for one long YouTube video. The tool creates editor-ready assets, scripts, transcripts, timelines, and metadata for multiple content formats without auto-rendering the final video.

The design must stay Web UI-ready: core logic should be separated from CLI parsing, and output JSON should be stable enough for a future dashboard or AI video-maker agent.

## Primary Use Case

Given one long video, generate multiple content assets around a user-provided or AI-discovered theme.

Examples:

- "Top 5 kelucuan si Bagus"
- "Best survival moments"
- "Funny moments pack"
- "Story highlight max 10 minutes"
- "Shorts/TikTok candidates"

## Priorities

1. High transcript accuracy for Indonesian and English, including mixed-language speech.
2. Low cost over speed.
3. Manual-edit and AI-agent-ready output.
4. Flexible content formats, not hardcoded Top 5 only.
5. CLI-first implementation with future Web UI support.

## Recommended Approach

Use the Hybrid Best Value approach:

1. Download full audio for the video.
2. Transcribe the full audio locally with `faster-whisper`.
3. Extract YouTube heatmap peaks with the existing `yt-dlp` metadata pipeline.
4. Build candidate moments from transcript segments and heatmap windows.
5. Use an LLM for theme discovery, semantic ranking, bilingual scripts, and editor notes.
6. Export clips, transcripts, timeline, scripts, and pack metadata.

This keeps transcription cost low while using stronger reasoning only where it adds value.

## Inference Engine

### Transcription

Use local `faster-whisper` for full-video transcription.

Requirements:

- Support Indonesian, English, and mixed-language speech.
- Generate timestamped transcript segments.
- Export `full.srt` and machine-readable transcript JSON.
- Prefer accuracy over speed.

### Reasoning

Use an LLM for tasks that need semantic judgment:

- Discover content themes when the user does not provide one.
- Score transcript moments against a theme.
- Rank candidate clips.
- Generate Indonesian and English scripts.
- Generate title, description, hashtags, and editor notes.

The design should allow provider substitution later. OpenAI API can be used, but core interfaces should not hardcode a single provider deeply into the pipeline.

## Content Formats

Content format must be pluggable. Initial formats:

### `top_n`

Countdown-style compilation such as "Top 5" or "Top 7".

- Default `top_n = 5`.
- Output sequence can be ordered from lowest rank to highest rank, such as `#5` to `#1`.
- Includes intro, per-moment narration, outro, title ideas, descriptions, and hashtags.

### `best_moments`

A set of strong clips without countdown structure.

- Useful for manual editing.
- Can be exported as independent assets.
- Avoids forcing a ranking when ranking is unnecessary.

### `story_highlight`

Chronological highlight plan with a maximum target duration of 10 minutes.

- Useful for narrative recap videos.
- Prioritizes story flow over raw heatmap strength.
- Can include bridging narration between clips.

### `shorts_pack`

Independent short-form clips for TikTok, Shorts, or Reels.

- Each clip should work standalone.
- Hook and caption suggestions are included per clip.
- Default duration target is short and engaging.

### `custom_prompt`

Allows the user to request a custom content structure.

- The LLM interprets the requested format.
- Output still conforms to the same `content_pack.json` schema.

## Theme Handling

The tool supports both user-guided and automatic theme selection.

### User Theme Provided

If the user passes `--theme`, the system ranks candidate moments against that theme.

Example:

```bash
python3 heatmap_pipeline.py content-pack \
  --url "https://www.youtube.com/watch?v=..." \
  --theme "kelucuan si Bagus" \
  --formats top_n,shorts_pack \
  --languages id,en
```

### No Theme Provided

If `--theme` is omitted:

1. The system transcribes the video.
2. The LLM proposes 3-5 theme ideas.
3. The CLI displays the theme ideas.
4. A later implementation can let the user choose one interactively or rerun with `--theme`.

For the first implementation, non-interactive CLI may write proposed themes to the content pack folder and stop before generating final format scripts.

## Candidate Moment Generation

Candidates come from a hybrid of heatmap and transcript data.

Inputs:

- Heatmap peaks from the existing pipeline.
- Full transcript segments from `faster-whisper`.
- User theme or auto-discovered theme.

Candidate windows:

- Start from heatmap peak windows.
- Attach nearby transcript segments for context.
- Allow transcript-only semantic candidates in future iterations.
- Preserve timestamps for clip extraction.

Duration rules:

- Target clip duration: 20-60 seconds.
- Hard maximum per clip: 90 seconds.
- Allow shorter clips when the moment is naturally short.
- Avoid long clips that become boring.

## Scoring

Each candidate should receive component scores:

- `heatmap_score`: popularity/replay signal from YouTube heatmap.
- `theme_score`: relevance to the user theme or selected auto theme.
- `story_score`: setup, payoff, and narrative usefulness.
- `edit_score`: clear start/end, minimal awkward cuts, usable dialogue boundaries.
- `diversity_penalty`: reduces duplicates and moments that are too close together.

The final score combines these components. Exact weights can be configurable later.

Selection rules:

- Avoid selecting many clips from the same nearby section.
- Prefer moments with context and payoff.
- Prefer clips that can be edited cleanly.
- For `story_highlight`, chronology can override raw score.
- For `top_n`, ranking should be explainable in editor notes.

## Output Structure

Output goes under:

```text
content_packs/<video_id>/
```

Expected files:

```text
content_packs/<video_id>/
  content_pack.json
  timeline.json
  editor_notes.md
  script_id.md
  script_en.md
  clips/
    clip01.mp4
    clip02.mp4
  transcripts/
    full.srt
    full.json
    clip01.srt
    clip02.srt
  metadata/
    source.json
    heatmap.json
    candidates.json
    themes.json
```

## Output Artifacts

### `content_pack.json`

Stable machine-readable summary for CLI, Web UI, and AI video-maker agents.

Includes:

- Source video metadata.
- Selected formats.
- Selected theme.
- Languages.
- Clip list.
- Scores.
- Scripts.
- Titles/descriptions/hashtags.
- Paths to generated files.

### `timeline.json`

Editor-ready sequence data.

Includes:

- Clip order.
- Source start/end timestamps.
- Local clip paths.
- Suggested narration timing.
- Notes for transitions.

### `script_id.md` and `script_en.md`

Human-readable scripts for Indonesian and English channels.

Includes:

- Intro.
- Per-clip narration.
- Outro.
- Optional caption copy.

### `editor_notes.md`

Practical guidance for manual editors or video-making agents.

Includes:

- Why each clip was selected.
- Suggested cuts.
- Suggested pacing.
- Any weak spots or transcript uncertainty.

## CLI Design

Initial CLI subcommand:

```bash
python3 heatmap_pipeline.py content-pack \
  --url URL \
  --theme "optional theme" \
  --formats top_n,shorts_pack \
  --languages id,en \
  --top-n 5
```

Defaults:

- `--formats best_moments,shorts_pack`
- `--languages id,en`
- `--top-n 5`
- `--output-dir content_packs`
- clip duration target `20-60s`
- hard max clip duration `90s`

## Architecture Boundaries

Keep implementation modular:

- CLI parser: handles arguments and user-facing command flow.
- Audio extractor: downloads or extracts full audio.
- Transcriber: runs `faster-whisper` and exports transcript files.
- Heatmap extractor: existing heatmap metadata logic.
- Candidate builder: merges heatmap and transcript windows.
- Scoring engine: applies hybrid scores and diversity filtering.
- LLM engine: theme discovery, ranking explanation, scripts, metadata.
- Asset exporter: clips, SRT, JSON, Markdown files.

This separation makes the future Web UI easier: the UI can call the same core services without shelling into CLI internals.

## Non-Goals For MVP

- No final video auto-rendering.
- No Web UI yet.
- No upload automation.
- No thumbnail image generation unless added later.
- No complex multi-video batch mode.

## Success Criteria

The MVP succeeds when it can process one long video and produce:

1. A full transcript in SRT and JSON.
2. Heatmap-informed candidate moments.
3. A selected set of clips for requested formats.
4. Indonesian and English scripts.
5. Editor-ready timeline and notes.
6. A stable `content_pack.json` for future Web UI or AI video-maker agents.
