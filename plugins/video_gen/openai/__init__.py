"""OpenAI video generation backend.

User-facing surface: text-to-video and image-to-video via OpenAI's DALL-E Video API.

Models:

  dall-e-video         OpenAI DALL-E Video (latest)
                       - text-to-video, image-to-video (when available)
                       - up to 1080p, 24fps

Credentials: OPENAI_API_KEY from https://platform.openai.com/api-keys
Output: MP4 URLs.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional
import httpx

from agent.video_gen_provider import (
    VideoGenProvider,
    error_response,
    success_response,
)

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "dall-e-video"
DEFAULT_DURATION = 5
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_RESOLUTION = "1080p"
DEFAULT_TIMEOUT_SECONDS = 600

VALID_ASPECT_RATIOS = {"1:1", "16:9", "9:16", "4:3", "3:4"}
VALID_RESOLUTIONS = {"480p", "720p", "1080p"}

OPENAI_API_BASE = "https://api.openai.com/v1"

_MODELS: Dict[str, Dict[str, Any]] = {
    "dall-e-video": {
        "display": "DALL-E Video",
        "speed": "~30-90s",
        "strengths": "OpenAI's latest video generation model, high quality.",
        "price": "see https://openai.com/pricing/video",
        "modalities": ["text"],  # image-to-video may come later
    },
}


def _resolve_openai_credentials() -> str:
    """Return OPENAI_API_KEY or empty string."""
    return os.getenv("OPENAI_API_KEY", "").strip()


def _openai_headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


class OpenAIVideoGenProvider(VideoGenProvider):
    """OpenAI DALL-E video generation backend."""

    @property
    def name(self) -> str:
        return "openai"

    @property
    def display_name(self) -> str:
        return "OpenAI"

    def is_available(self) -> bool:
        api_key = _resolve_openai_credentials()
        return bool(api_key)

    def list_models(self) -> List[Dict[str, Any]]:
        return [{"id": mid, **meta} for mid, meta in _MODELS.items()]

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "OpenAI DALL-E Video",
            "badge": "paid",
            "tag": "Text-to-video via DALL-E Video; uses OPENAI_API_KEY",
            "env_vars": [
                {
                    "key": "OPENAI_API_KEY",
                    "prompt": "OpenAI API key",
                    "url": "https://platform.openai.com/api-keys",
                }
            ],
        }

    def capabilities(self) -> Dict[str, Any]:
        return {
            "modalities": ["text"],  # image-to-video may be added later
            "aspect_ratios": sorted(VALID_ASPECT_RATIOS),
            "resolutions": sorted(VALID_RESOLUTIONS),
            "max_duration": 60,
            "min_duration": 1,
            "supports_audio": False,
            "supports_negative_prompt": False,
            "max_reference_images": 0,
        }

    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        image_url: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
        duration: Optional[int] = None,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        resolution: str = DEFAULT_RESOLUTION,
        negative_prompt: Optional[str] = None,
        audio: Optional[bool] = None,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        try:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self._generate_async(
                    prompt=prompt,
                    model=model,
                    image_url=image_url,
                    duration=duration,
                    aspect_ratio=aspect_ratio,
                    resolution=resolution,
                ))
            finally:
                loop.close()
        except Exception as exc:
            logger.warning("OpenAI video gen unexpected failure: %s", exc, exc_info=True)
            return error_response(
                error=f"OpenAI video generation failed: {exc}",
                error_type="api_error",
                provider="openai",
                model=model or DEFAULT_MODEL,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
            )

    async def _generate_async(
        self,
        *,
        prompt: str,
        model: Optional[str],
        image_url: Optional[str],
        duration: Optional[int],
        aspect_ratio: str,
        resolution: str,
    ) -> Dict[str, Any]:
        api_key = _resolve_openai_credentials()
        if not api_key:
            return error_response(
                error="OPENAI_API_KEY not set. Get one from https://platform.openai.com/api-keys",
                error_type="auth_required",
                provider="openai",
                prompt=prompt,
            )

        prompt = (prompt or "").strip()
        if not prompt:
            return error_response(
                error="prompt is required for OpenAI video generation",
                error_type="missing_prompt",
                provider="openai",
                prompt=prompt,
            )

        resolved_model = (model or DEFAULT_MODEL).strip()
        if resolved_model not in _MODELS:
            resolved_model = DEFAULT_MODEL

        normalized_aspect_ratio = (aspect_ratio or DEFAULT_ASPECT_RATIO).strip()
        if normalized_aspect_ratio not in VALID_ASPECT_RATIOS:
            normalized_aspect_ratio = DEFAULT_ASPECT_RATIO

        normalized_resolution = (resolution or DEFAULT_RESOLUTION).strip()
        if normalized_resolution not in VALID_RESOLUTIONS:
            normalized_resolution = DEFAULT_RESOLUTION

        clamped_duration = duration if duration is not None else DEFAULT_DURATION
        if clamped_duration < 1:
            clamped_duration = 1
        if clamped_duration > 60:
            clamped_duration = 60

        modality_used = "text"  # OpenAI's current API only supports text-to-video

        # Build request
        payload = {
            "model": "gpt-4-vision",  # Use vision model to understand context better
            "prompt": f"{prompt}\n\nGenerate a {clamped_duration}s video in {normalized_aspect_ratio} aspect ratio at {normalized_resolution}.",
            "size": "1920x1080" if normalized_resolution == "1080p" else "1280x720",
            "quality": "hd",
            "n": 1,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{OPENAI_API_BASE}/videos/generations",
                    headers=_openai_headers(api_key),
                    json=payload,
                    timeout=60,
                )
                response.raise_for_status()
                result = response.json()

            created = result.get("created")
            if not created:
                return error_response(
                    error="No creation timestamp returned",
                    error_type="api_error",
                    provider="openai",
                    model=resolved_model,
                    prompt=prompt,
                )

            # Extract video URL
            video_data = result.get("data", [{}])[0]
            video_url = video_data.get("url") or video_data.get("b64_json")

            if not video_url:
                return error_response(
                    error="No video URL or data in response",
                    error_type="empty_response",
                    provider="openai",
                    model=resolved_model,
                    prompt=prompt,
                )

            return success_response(
                video=video_url,
                model=resolved_model,
                prompt=prompt,
                modality=modality_used,
                aspect_ratio=normalized_aspect_ratio,
                duration=clamped_duration,
                provider="openai",
                extra={"created": created},
            )

        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                detail = exc.response.json().get("error", {}).get("message", "")
            except Exception:
                pass
            return error_response(
                error=f"OpenAI API error ({exc.response.status_code}): {detail or exc}",
                error_type="api_error",
                provider="openai",
                model=resolved_model,
                prompt=prompt,
            )
        except Exception as exc:
            logger.warning("OpenAI generation error: %s", exc, exc_info=True)
            return error_response(
                error=f"Generation failed: {exc}",
                error_type="api_error",
                provider="openai",
                model=resolved_model,
                prompt=prompt,
            )


def register(ctx) -> None:
    """Plugin entry point."""
    ctx.register_video_gen_provider(OpenAIVideoGenProvider())
