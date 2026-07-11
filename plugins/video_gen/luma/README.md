# Luma Dream Machine Video Generation

Ultra-realistic video generation with Luma Dream Machine.

## Setup

1. **Get API Key**
   - Visit [Luma API Console](https://console.luma.ai)
   - Create a project and generate API key

2. **Configure**
   ```bash
   # Add to ~/.hermes/.env or set environment variable:
   export LUMA_API_KEY="your-api-key-here"
   ```

## Models

| Model | Type | Strength |
|-------|------|----------|
| `dream-machine` | Flagship | Ultra-realistic, consistent physics |

## Capabilities

| Feature | Details |
|---------|---------|
| **Modalities** | Text-to-video, Image-to-video (keyframe-based) |
| **Resolutions** | 480p, 720p, 1080p |
| **Aspect Ratios** | 16:9, 9:16, 1:1 |
| **Duration** | 1-5 seconds |
| **Video Codec** | H.264 (MP4) |

## Examples

### Text-to-Video
```
A serene forest clearing with sunlight filtering through trees.
Realistic physics, natural movement, peaceful atmosphere.
```

### Image-to-Video (Keyframe)
```
Base image: A person standing in a field
Motion: "Person walks forward, wind blows hair and clothes"
Duration: 4 seconds
```

## Response

```python
{
    "success": True,
    "video": "base64-encoded-mp4",  # or download URL
    "model": "dream-machine",
    "prompt": "Your input prompt",
    "modality": "text-to-video",
    "aspect_ratio": "16:9",
    "duration": 4,
    "provider": "luma"
}
```

## Image-to-Video with Keyframes

Luma supports optional keyframe-based image extension:

```python
# Request with keyframe motion
result = video_generate(
    prompt="A person walking through a park",
    image_url="https://...",  # Starting image
    # Optional: keyframes configuration
    aspect_ratio="16:9",
    duration=4
)
```

## Comparison with Other Providers

| Provider | Strength | Best For |
|----------|----------|----------|
| **Luma** | Realism, physics accuracy | Product demos, nature videos |
| Google | Diversity, multiple models | All-purpose generation |
| Runway | Speed, professional output | Content creation, iterations |
| FAL | Quick turnaround | Prototyping |

## Strengths & Limitations

✅ **Strengths:**
- Excellent physics simulation
- Highly realistic water, fabric, particle effects
- Consistent character behavior
- Strong on nature and environmental videos

⚠️ **Limitations:**
- Shorter duration (max 5s vs others' 10-120s)
- Limited resolution options
- Smaller model variety (single flagship model)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| API key not found | Ensure `LUMA_API_KEY` is set in `.env` |
| "Too long" error | Maximum duration is 5 seconds |
| Poor quality keyframes | Ensure base image is clear and well-lit |
| Generation timeout | Wait 60-90s for video generation |

## References

- [Luma API Documentation](https://docs.luma.ai)
- [Dream Machine Model Card](https://luma.ai/dream-machine)
- [Getting Started Guide](https://docs.luma.ai/getting-started)
