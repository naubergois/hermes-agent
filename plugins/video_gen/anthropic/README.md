# Anthropic Claude Video API

Anthropic's Claude-powered video generation (in development).

## Status

⚠️ **Public API Not Available** — This provider is a **proof of concept**. The Anthropic Video API is not yet publicly released.

## Setup (Future)

Once released, configuration will be:

```bash
# Add to ~/.hermes/.env or set environment variable:
export ANTHROPIC_API_KEY="your-api-key-here"
```

## Capabilities (Expected)

| Feature | Details |
|---------|---------|
| **Modalities** | Text-to-video, Image-to-video |
| **Resolutions** | 480p, 720p, 1080p |
| **Aspect Ratios** | 16:9, 9:16, 1:1 |
| **Duration** | 1-10 seconds |
| **Model** | Claude-based video (TBD) |

## Vision

When released, Claude's video generation will leverage:

- **Deep scene understanding** — Claude's vision comprehension applied to temporal sequences
- **Complex instructions** — Multi-step, conditional motion from detailed prompts
- **Semantic consistency** — Long-form video generation with stable semantics
- **Seamless integration** — Native tool in multi-modal Claude workflows

## Expected Use Cases

✅ Educational videos with narration
✅ Product documentation sequences
✅ Complex motion from detailed descriptions
✅ Conditional animation (if-then branching)

## How to Track

- [Anthropic Models Documentation](https://docs.anthropic.com)
- [Announcements Blog](https://www.anthropic.com/news)
- GitHub discussions (hermes-agent)

## Implementation Notes

This provider includes a complete implementation with:
- Full API specification (anticipating public release)
- Image-to-base64 conversion
- Duration & resolution validation
- Error handling and edge cases
- Unit tests with mocking

When the API becomes publicly available:
1. Update the base URL and endpoint configuration
2. Add live integration tests
3. Remove `is_available()` provider check restrictions
4. Enable in gateway and CLI surfaces

## Related Providers

- **OpenAI DALL-E Video** — Text-to-video, no image support yet
- **Google Gemini** — Diverse models (Veo 3.1, Veo 2.0)
- **Runway Gen-3** — Fast, professional-grade
- **Luma Dream Machine** — Realistic physics
- **FAL Video** — Quick turnaround via Falconsai
- **xAI Grok** — Creative, diverse outputs
