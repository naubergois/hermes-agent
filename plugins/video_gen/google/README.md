# Google Gemini Video Generation Provider

## Overview

The Google provider brings Google DeepMind's Veo models to Hermes Agent's unified video generation surface.

**Models:**
- **Veo 3.1** (latest, recommended) — Cinematic quality, strong prompt adherence, ~30-90s generation
- **Veo 2.0** (faster, cheaper) — Balanced quality and speed, ~20-60s generation

**Capabilities:**
- Text-to-video: `prompt` only
- Image-to-video: `prompt` + `image_url` (animate still images)
- Resolutions: 480p, 720p, 1440p
- Aspect ratios: 1:1, 16:9, 9:16, 4:3, 3:4
- Duration: 1–120 seconds (provider clamps)
- Negative prompts
- FPS: 25fps

## Authentication

Two credential paths:

1. **API Key** (recommended for scripts)
   ```bash
   export GOOGLE_API_KEY=<your-api-key>
   ```
   Get an API key from [Google AI Studio](https://ai.google.dev/).

2. **Application Default Credentials (ADC)** (recommended for deployment)
   ```bash
   gcloud auth application-default login
   ```

## Installation

Install the `google-genai` SDK:

```bash
pip install google-genai
```

The provider is bundled and auto-discovered; no additional setup needed.

## Usage Examples

### Text-to-Video

```python
from run_agent import AIAgent

agent = AIAgent(model="gpt-4o")
result = agent.chat("""
    Generate a video of a futuristic city at night using the video_generate tool.
    Prompt: "Neon-lit futuristic city, flying cars, dense traffic, night sky"
    Model: veo-3.1-generate-preview
""")
```

### Image-to-Video

Animate a static image:

```python
result = agent.chat("""
    Animate this image into a video.
    Image URL: https://example.com/painting.jpg
    Prompt: "The painting comes to life with flowing movements"
    Model: veo-3.1-generate-preview
""")
```

### Negative Prompts

Guide the model away from unwanted content:

```python
result = agent.chat("""
    Generate a video of a sunset over a beach.
    Prompt: "Beautiful sunset over a sandy beach, calm waves"
    Negative Prompt: "blurry, low quality, distorted"
    Model: veo-3.1-generate-preview
""")
```

## Output

Videos are returned as HTTPS URLs (for remote videos) or absolute file paths (for cached GCS videos).

The tool response includes:
- `video` — URL or path to the generated video
- `modality` — "text" or "image" (which mode was used)
- `aspect_ratio` — normalized ratio (e.g. "16:9")
- `duration` — video duration in seconds
- `model` — the model used
- `provider` — "google"

## Comparison: Google vs FAL vs xAI

| Feature | Google | FAL | xAI |
|---------|--------|-----|-----|
| Text-to-video | ✅ Veo 3.1 + 2.0 | ✅ 6 models | ✅ Grok Imagine |
| Image-to-video | ✅ | ✅ | ✅ |
| Max resolution | 1440p | 1080p | 720p |
| Max duration | 120s | 15s | 15s |
| Negative prompts | ✅ | ✅ (some models) | ❌ |
| Audio generation | ❌ | ✅ (some models) | ❌ |
| Reference images | ❌ | ❌ | ✅ (up to 7) |
| Speed | ~30-90s | ~30-120s | ~60-240s |
| Price tier | Reasonable | Cheap–Premium | Premium |

## Configuration

Set your preferred Google model in `config.yaml`:

```yaml
video_gen:
  provider: google
  model: veo-3.1-generate-preview  # or veo-2.0-generate-001
```

Or dynamically via `hermes tools` → Video Generation.

## Troubleshooting

### "google-genai SDK is required"
Install the SDK:
```bash
pip install google-genai
```

### "No credentials found"
Ensure `GOOGLE_API_KEY` is set or ADC is configured:
```bash
echo $GOOGLE_API_KEY  # Check API key
gcloud auth application-default login  # Set up ADC
```

### Generation timeout (>10 minutes)
Google's video generation can be slow, especially for Veo 3.1. The default timeout is 10 minutes. If you hit it, try:
- Reducing `duration` (request fewer seconds)
- Using Veo 2.0 for faster generation
- Splitting into multiple smaller videos

### GCS download errors
If the provider can't download from Google Cloud Storage, ensure your credentials have `storage.buckets.get` permission on the temporary cache bucket. The fallback is to return the GCS URI directly.

## Resources

- [Google AI Studio](https://ai.google.dev/)
- [Veo 3 Announcement](https://deepmind.google/technologies/veo/)
- [API Reference](https://ai.google.dev/api/rest)
- [Pricing](https://ai.google.dev/pricing)
