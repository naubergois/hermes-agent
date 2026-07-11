"""Runway Gen-3 video generation backend.

User-facing surface: pick a **model** (Gen-3 or Gen-3 Turbo) and the provider
auto-routes to the appropriate endpoint for text-to-video or image-to-video.

Models:

  gen-3                Runway Gen-3 (latest, highest quality)
                       - text-to-video, image-to-video
                       - up to 1440p, 25fps, 10s default
                       
  gen-3-turbo          Runway Gen-3 Turbo (faster, cheaper)
                       - text-to-video, image-to-video
                       - up to 1440p, 25fps, 6s default

Credentials: RUNWAY_API_KEY from https://app.runwayml.com/settings/api-keys
Output: MP4 URLs from Runway's CDN or local cache.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import httpx
import json

from agent.video_gen_provider import (
    VideoGenProvider,
    error_response,
    success_response,
)

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "gen-3"
DEFAULT_DURATION = 10
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_RESOLUTION = "1080p"
DEFAULT_FPS = 25
DEFAULT_TIMEOUT_SECONDS = 600  # 10 minutes
DEFAULT_POLL_INTERVAL_SECONDS = 5

VALID_ASPECT_RATIOS = {"1:1", "16:9", "9:16", "21:9", "4:3", "3:4"}
VALID_RESOLUTIONS = {"360p", "540p", "720p", "1080p", "1440p"}

RUNWAY_API_BASE = "https://api.runwayml.com/v1"

_MODELS: Dict[str, Dict[str, Any]] = {
    "gen-3": {
        "display": "Gen-3",
        "speed": "~60-120s",
        "strengths": "Latest model. Highest quality, best prompt adherence.",
        "price": "see https://runwayml.com/pricing",
        "modalities": ["text", "image"],
    },
    "gen-3-turbo": {
        "display": "Gen-3 Turbo",
        "speed": "~30-60s",
        "strengths": "Faster generation, good quality, cheaper than Gen-3.",
        "price": "see https://runwayml.com/pricing",
        "modalities": ["text", "image"],
    },
}


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _resolve_runway_credentials() -> str:
    """Return RUNWAY_API_KEY or empty string."""
    return os.getenv("RUNWAY_API_KEY", "").strip()


def _runway_headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class RunwayVideoGenProvider(VideoGenProvider):
    """Runway Gen-3 video generation backend."""

    @property
    def name(self) -> str:
        return "runway"

    @property
    def display_name(self) -> str:
        return "Runway"

    def is_available(self) -> bool:
        api_key = _resolve_runway_credentials()
        return bool(api_key)

    def list_models(self) -> List[Dict[str, Any]]:
        return [{"id": mid, **meta} for mid, meta in _MODELS.items()]

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Runway Gen-3",
            "badge": "paid",
            "tag": "Gen-3 for highest quality, Gen-3 Turbo for faster generation; uses RUNWAY_API_KEY",
            "env_vars": [
                {
                    "key": "RUNWAY_API_KEY",
                    "prompt": "Runway API key",
                    "url": "https://app.runwayml.com/settings/api-keys",
                }
            ],
        }

    def capabilities(self) -> Dict[str, Any]:
        return {
            "modalities": ["text", "image"],
            "aspect_ratios": sorted(VALID_ASPECT_RATIOS),
            "resolutions": sorted(VALID_RESOLUTIONS),
            "max_duration": 10,
            "min_duration": 4,
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
            logger.warning("Runway video gen unexpected failure: %s", exc, exc_info=True)
            return error_response(
                error=f"Runway video generation failed: {exc}",
                error_type="api_error",
                provider="runway",
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
        api_key = _resolve_runway_credentials()
        if not api_key:
            return error_response(
                error="RUNWAY_API_KEY not set. Get one from https://app.runwayml.com/settings/api-keys",
                error_type="auth_required",
                provider="runway",
                prompt=prompt,
            )

        prompt = (prompt or "").strip()
        if not prompt:
            return error_response(
                error="prompt is required for Runway video generation",
                error_type="missing_prompt",
                provider="runway",
                prompt=prompt,
            )

        # Resolve model
        resolved_model = (model or DEFAULT_MODEL).strip()
        if resolved_model not in _MODELS:
            resolved_model = DEFAULT_MODEL

        # Normalize parameters
        normalized_aspect_ratio = (aspect_ratio or DEFAULT_ASPECT_RATIO).strip()
        if normalized_aspect_ratio not in VALID_ASPECT_RATIOS:
            normalized_aspect_ratio = DEFAULT_ASPECT_RATIO

        normalized_resolution = (resolution or DEFAULT_RESOLUTION).strip()
        if normalized_resolution not in VALID_RESOLUTIONS:
            normalized_resolution = DEFAULT_RESOLUTION

        clamped_duration = duration if duration is not None else DEFAULT_DURATION
        if clamped_duration < 4:
            clamped_duration = 4
        if clamped_duration > 10:
            clamped_duration = 10

        # Determine modality
        modality_used = "image" if image_url else "text"

        # Build request payload
        payload: Dict[str, Any] = {
            "model": resolved_model,
            "prompt": prompt,
            "duration": clamped_duration,
            "ratio": normalized_aspect_ratio,
        }
        if image_url:
            payload["image"] = image_url

        try:
            async with httpx.AsyncClient() as client:
                # Submit request
                response = await client.post(
                    f"{RUNWAY_API_BASE}/image_to_video" if image_url else f"{RUNWAY_API_BASE}/text_to_video",
                    headers=_runway_headers(api_key),
                    json=payload,
                    timeout=60,
                )
                response.raise_for_status()
                result = response.json()

            # Extract task ID
            task_id = result.get("id") or result.get("task_id")
            if not task_id:
                return error_response(
                    error="No task ID returned from Runway API",
                    error_type="api_error",
                    provider="runway",
                    model=resolved_model,
                    prompt=prompt,
                )

            # Poll for completion
            start_time = time.time()
            while time.time() - start_time < DEFAULT_TIMEOUT_SECONDS:
                await asyncio.sleep(DEFAULT_POLL_INTERVAL_SECONDS)

                async with httpx.AsyncClient() as client:
                    status_response = await client.get(
                        f"{RUNWAY_API_BASE}/tasks/{task_id}",
                        headers=_runway_headers(api_key),
                        timeout=30,
                    )
                    status_response.raise_for_status()
                    status_data = status_response.json()

                status = (status_data.get("status") or "").lower()
                if status == "succeeded":
                    video_url = status_data.get("output", [{}])[0].get("url") if status_data.get("output") else None
                    if video_url:
                        return success_response(
                            video=video_url,
                            model=resolved_model,
                            prompt=prompt,
                            modality=modality_used,
                            aspect_ratio=normalized_aspect_ratio,
                            duration=clamped_duration,
                            provider="runway",
                            extra={"task_id": task_id},
                        )
                    return error_response(
                        error="Generation succeeded but no video URL returned",
                        error_type="empty_response",
                        provider="runway",
                        model=resolved_model,
                        prompt=prompt,
                    )

                if status in {"failed", "error", "cancelled"}:
                    error_msg = status_data.get("error", {}).get("message") or f"Task {status}"
                    return error_response(
                        error=f"Runway generation {status}: {error_msg}",
                        error_type=f"runway_{status}",
                        provider="runway",
                        model=resolved_model,
                        prompt=prompt,
                    )

            return error_response(
                error=f"Timed out waiting for video generation after {DEFAULT_TIMEOUT_SECONDS}s",
                error_type="timeout",
                provider="runway",
                model=resolved_model,
                prompt=prompt,
            )

        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                detail = exc.response.text[:500]
            except Exception:
                pass
            return error_response(
                error=f"Runway API error ({exc.response.status_code}): {detail or exc}",
                error_type="api_error",
                provider="runway",
                model=resolved_model,
                prompt=prompt,
            )
        except Exception as exc:
            logger.warning("Runway generation error: %s", exc, exc_info=True)
            return error_response(
                error=f"Generation failed: {exc}",
                error_type="api_error",
                provider="runway",
                model=resolved_model,
                prompt=prompt,
            )


def register(ctx) -> None:
    """Plugin entry point."""
    ctx.register_video_gen_provider(RunwayVideoGenProvider())
