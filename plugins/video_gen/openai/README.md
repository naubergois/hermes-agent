# OpenAI DALL-E Video

OpenAI's latest generative model for video creation.

## Setup

1. **Get API Key**
   - Visit [OpenAI Platform](https://platform.openai.com/account/api-keys)
   - Create or use existing API key

2. **Configure**
   ```bash
   # Add to ~/.hermes/.env or set environment variable:
   export OPENAI_API_KEY="sk-..."
   ```

3. **Verify Credits**
   - DALL-E Video API usage requires credits
   - Check usage limits: `hermes tools config openai`

## Models

| Model | Focus | Strength |
|-------|-------|----------|
| `dall-e-video` | Text-to-video | Fast, diverse, high quality |

## Capabilities

| Feature | Details |
|---------|---------|
| **Modalities** | Text-to-video only |
| **Resolutions** | 480p, 720p, 1080p |
| **Aspect Ratios** | 16:9, 9:16, 1:1 |
| **Duration** | 1-60 seconds |
| **Video Format** | MP4 (H.264) |

## Examples

### Text-to-Video
```
A bustling Tokyo street at night with neon signs reflecting 
in rain puddles. People walking with umbrellas. 
Ambient city sounds implied. 4K quality.
```

## Response

```python
{
    "success": True,
    "video": "https://...",  # Presigned download URL
    "model": "dall-e-video",
    "prompt": "Your input prompt",
    "modality": "text-to-video",
    "aspect_ratio": "16:9",
    "duration": 15,
    "provider": "openai"
}
```

## Prompting Tips

### Effective Prompts
✅ "A coffee pouring into a ceramic mug, steam rising"
✅ "Sunset over mountains with clouds moving"
✅ "Person walking through busy marketplace"

### Avoid
❌ People's faces in detail (policy restricted)
❌ Copyrighted content or brand names
❌ Violence or harmful content
❌ Abstract, hard-to-visualize concepts

## Comparison with Other Providers

| Provider | Duration | Modalities | Best For |
|----------|----------|------------|----------|
| **OpenAI** | ⭐⭐⭐ 1-60s | Text only | Diverse, fast generation |
| Google | ⭐⭐⭐⭐⭐ 1-120s | Text + Image | Complex scenarios |
| Runway | ⭐⭐⭐ 4-10s | Text + Image | Professional content |
| Luma | ⭐⭐ 1-5s | Text + Image | Realism, physics |
| FAL | ⭐⭐⭐ 0-15s | Text + Image | Quick iterations |

## Rate Limits

| Tier | Requests/min | Requests/day |
|------|-------------|--------------|
| Free | 3 | 50 |
| Paid | 30 | 10,000 |

## Pricing

Pricing varies; check [OpenAI Pricing](https://openai.com/pricing/video) for current rates.
Generally $0.07-0.20 USD per 1,000 frames depending on resolution.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| API key not found | Ensure `OPENAI_API_KEY` is set in `.env` |
| Rate limit hit | Wait before retrying; consider queueing |
| "Invalid prompt" | Avoid faces, copyrighted content, violence |
| No image-to-video | Currently text-to-video only (image version coming) |
| Long generation wait | Video generation can take 60-120s |

## Known Limitations

⚠️ **Current Limitations:**
- Text-to-video only (image-to-video in development)
- Policy restrictions on specific content (faces, copyrighted material)
- Longer duration = slower generation time
- No webhook support; polling required for long videos

## Future Improvements

🔮 **Coming Soon:**
- Image-to-video support
- Longer duration videos (120+ seconds)
- WebSocket streaming for longer videos
- Webhook notifications for async generation

## References

- [OpenAI DALL-E Video Docs](https://platform.openai.com/docs/guides/videos)
- [API Reference](https://platform.openai.com/docs/api-reference/video)
- [Pricing](https://openai.com/pricing/video)
- [Content Policy](https://openai.com/policies/usage-policies)
