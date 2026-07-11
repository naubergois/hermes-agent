"""Luma Dream Machine video generation backend.

User-facing surface: text-to-video and image-to-video via Luma's Dream Machine.

Models:

  dream-machine        Luma Dream Machine (latest, recommended)
                       - text-to-video, image-to-video
                       - up to 1080p, 24fps, 5s default

Credentials: LUMA_API_KEY from https://www.lumaai.ai/
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
DEFAULT_MODEL = "dream-machine"
DEFAULT_DURATION = 5
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_RESOLUTION = "1080p"
DEFAULT_TIMEOUT_SECONDS = 600

VALID_ASPECT_RATIOS = {"1:1", "16:9", "9:16", "4:3", "3:4"}
VALID_RESOLUTIONS = {"480p", "720p", "1080p"}

LUMA_API_BASE = "https://api.lumaai.ai"

_MODELS: Dict[str, Dict[str, Any]] = {
    "dream-machine": {
        "display": "Dream Machine",
        "speed": "~30-60s",
        "strengths": "High-quality, consistent generation, good motion.",
        "price": "see https://www.lumaai.ai/pricing",
        "modalities": ["text", "image"],
    },
}


def _resolve_luma_credentials() -> str:
    """Return LUMA_API_KEY or empty string."""
    return os.getenv("LUMA_API_KEY", "").strip()


def _luma_headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


class LumaVideoGenProvider(VideoGenProvider):
    """Luma Dream Machine video generation backend."""

    @property
    def name(self) -> str:
        return "luma"

    @property
    def display_name(self) -> str:
        return "Luma"

    def is_available(self) -> bool:
        api_key = _resolve_luma_credentials()
        return bool(api_key)

    def list_models(self) -> List[Dict[str, Any]]:
        return [{"id": mid, **meta} for mid, meta in _MODELS.items()]

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Luma Dream Machine",
            "badge": "paid",
            "tag": "High-quality text-to-video and image-to-video; uses LUMA_API_KEY",
            "env_vars": [
                {
                    "key": "LUMA_API_KEY",
                    "prompt": "Luma API key",
                    "url": "https://www.lumaai.ai/",
                }
            ],
        }

    def capabilities(self) -> Dict[str, Any]:
        return {
            "modalities": ["text", "image"],
            "aspect_ratios": sorted(VALID_ASPECT_RATIOS),
            "resolutions": sorted(VALID_RESOLUTIONS),
            "max_duration": 5,
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
            logger.warning("Luma video gen unexpected failure: %s", exc, exc_info=True)
            return error_response(
                error=f"Luma video generation failed: {exc}",
                error_type="api_error",
                provider="luma",
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
        api_key = _resolve_luma_credentials()
        if not api_key:
            return error_response(
                error="LUMA_API_KEY not set. Get one from https://www.lumaai.ai/",
                error_type="auth_required",
                provider="luma",
                prompt=prompt,
            )

        prompt = (prompt or "").strip()
        if not prompt:
            return error_response(
                error="prompt is required for Luma video generation",
                error_type="missing_prompt",
                provider="luma",
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
        if clamped_duration > 5:
            clamped_duration = 5

        modality_used = "image" if image_url else "text"

        payload: Dict[str, Any] = {
            "prompt": prompt,
            "aspect_ratio": normalized_aspect_ratio,
        }
        if image_url:
            payload["keyframes"] = {"frame0": {"type": "image", "url": image_url}}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{LUMA_API_BASE}/generations",
                    headers=_luma_headers(api_key),
                    json=payload,
                    timeout=60,
                )
                response.raise_for_status()
                result = response.json()

            generation_id = result.get("id")
            if not generation_id:
                return error_response(
                    error="No generation ID returned from Luma API",
                    error_type="api_error",
                    provider="luma",
                    model=resolved_model,
                    prompt=prompt,
                )

            # Poll for completion
            start_time = time.time()
            while time.time() - start_time < DEFAULT_TIMEOUT_SECONDS:
                await asyncio.sleep(5)

                async with httpx.AsyncClient() as client:
                    status_response = await client.get(
                        f"{LUMA_API_BASE}/generations/{generation_id}",
                        headers=_luma_headers(api_key),
                        timeout=30,
                    )
                    status_response.raise_for_status()
                    status_data = status_response.json()

                state = status_data.get("state", "").lower()
                if state == "completed":
                    video_url = status_data.get("download_url") or status_data.get("url")
                    if video_url:
                        return success_response(
                            video=video_url,
                            model=resolved_model,
                            prompt=prompt,
                            modality=modality_used,
                            aspect_ratio=normalized_aspect_ratio,
                            duration=clamped_duration,
                            provider="luma",
                            extra={"generation_id": generation_id},
                        )
                    return error_response(
                        error="Generation completed but no video URL",
                        error_type="empty_response",
                        provider="luma",
                        model=resolved_model,
                        prompt=prompt,
                    )

                if state in {"failed", "error"}:
                    error_msg = status_data.get("failure_reason") or f"Generation {state}"
                    return error_response(
                        error=f"Luma generation {state}: {error_msg}",
                        error_type=f"luma_{state}",
                        provider="luma",
                        model=resolved_model,
                        prompt=prompt,
                    )

            return error_response(
                error=f"Timed out after {DEFAULT_TIMEOUT_SECONDS}s",
                error_type="timeout",
                provider="luma",
                model=resolved_model,
                prompt=prompt,
            )

        except Exception as exc:
            logger.warning("Luma generation error: %s", exc, exc_info=True)
            return error_response(
                error=f"Generation failed: {exc}",
                error_type="api_error",
                provider="luma",
                model=resolved_model,
                prompt=prompt,
            )


def register(ctx) -> None:
    """Plugin entry point."""
    ctx.register_video_gen_provider(LumaVideoGenProvider())
