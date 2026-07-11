# Runway Gen-3 Video Generation

High-performance video generation with Runway's Gen-3 and Gen-3 Turbo models.

## Setup

1. **Get API Key**
   - Visit [Runway API Dashboard](https://app.runwayml.com/settings/api-keys)
   - Generate and copy your API key

2. **Configure**
   ```bash
   # Add to ~/.hermes/.env or set environment variable:
   export RUNWAY_API_KEY="your-api-key-here"
   ```

## Models

| Model | Speed | Quality | Best For |
|-------|-------|---------|----------|
| `gen-3` | Standard | High | General purpose, cinematic videos |
| `gen-3-turbo` | Faster | Excellent | Quick iterations, content creators |

## Capabilities

| Feature | Details |
|---------|---------|
| **Modalities** | Text-to-video, Image-to-video |
| **Resolutions** | 360p, 540p, 720p, 1080p, 1440p |
| **Aspect Ratios** | 16:9, 9:16, 1:1, 21:9, 9:21 |
| **Duration** | 4-10 seconds |
| **Video Codec** | H.264 (MP4) |

## Examples

### Text-to-Video
```
A professional cinematic shot of a futuristic city at night, 
with neon lights reflecting on wet streets. 4K quality, 
smooth camera movement, 8 seconds.
```

### Image-to-Video
```
Starting from an image of a peaceful beach,
create a video where waves gently roll in and 
seagulls fly across the sky.
```

## Response

```python
{
    "success": True,
    "video": "base64-encoded-mp4",  # or URL if webhook configured
    "model": "gen-3",
    "prompt": "Your input prompt",
    "modality": "text-to-video",
    "aspect_ratio": "16:9",
    "duration": 8,
    "provider": "runway"
}
```

## Comparison with Other Providers

| Provider | Speed | Quality | Cost | Best For |
|----------|-------|---------|------|----------|
| **Runway** | ⚡⚡ Fast | ⭐⭐⭐⭐ Excellent | $$ | Professional video production |
| Google | ⚡ Standard | ⭐⭐⭐⭐ Great | $ | Diverse scenarios |
| FAL | ⚡⚡ Fast | ⭐⭐⭐ Good | $ | Quick generation |
| Luma | ⚡ Standard | ⭐⭐⭐⭐ Excellent | $$ | Consistent, high-quality |
| xAI | ⚡ Standard | ⭐⭐⭐ Good | $ | Creative, diverse |

## Configuration

### Model Selection
```python
# Use faster model for quick iterations
result = agent.delegate_task(
    goal="Generate video of dancing robot",
    context="Use gen-3-turbo for speed"
)
```

### Custom Duration & Resolution
The provider automatically clamps your requested values:
- Duration: 4-10 seconds (will adjust request to this range)
- Resolution: Picks closest supported (360p, 540p, 720p, 1080p, 1440p)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| API key not found | Ensure `RUNWAY_API_KEY` is set in `.env` |
| Request timeout | Videos take 30-120s to generate; consider using polling |
| Low quality output | Use gen-3 instead of gen-3-turbo for higher quality |
| Unsupported aspect ratio | Provider supports 16:9, 9:16, 1:1, 21:9, 9:21 only |

## References

- [Runway Documentation](https://docs.runwayml.com/api/overview)
- [API Reference](https://docs.runwayml.com/api/endpoints)
- [Model Cards](https://runwayml.com/model-cards)
