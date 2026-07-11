"""Google Gemini video generation backend.

User-facing surface: pick a **model** (Veo 3.1 or Veo 2.0) and the provider
auto-routes to the appropriate endpoint:

- **Text-to-video** (text prompt only) → Veo generates from scratch
- **Image-to-video** (image_url provided) → Veo animates the image
- **Video editing** (video_url + prompt) → Veo extends or transforms video

Models:

  veo-3.1          Google DeepMind Veo 3.1 (latest, recommended)
                   - text-to-video, image-to-video, video editing
                   - up to 1440p, 25fps, 6s default
                   
  veo-2.0          Google DeepMind Veo 2.0 (faster, cheaper)
                   - text-to-video, image-to-video
                   - up to 1440p, 25fps

Credentials: GOOGLE_API_KEY or Application Default Credentials (ADC).
Output: HTTPS URLs from Google Cloud Storage (gs:// URIs auto-downloaded).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agent.video_gen_provider import (
    VideoGenProvider,
    error_response,
    success_response,
)

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "veo-3.1-generate-preview"
DEFAULT_DURATION = 6
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_RESOLUTION = "720p"
DEFAULT_FPS = 25
DEFAULT_TIMEOUT_SECONDS = 600  # 10 minutes for long-running operations
DEFAULT_POLL_INTERVAL_SECONDS = 5

VALID_ASPECT_RATIOS = {"1:1", "16:9", "9:16", "4:3", "3:4"}
VALID_RESOLUTIONS = {"480p", "720p", "1440p"}

_MODELS: Dict[str, Dict[str, Any]] = {
    "veo-3.1-generate-preview": {
        "display": "Veo 3.1",
        "speed": "~30-90s",
        "strengths": "Latest Google DeepMind model. Cinematic quality, high prompt adherence.",
        "price": "see https://ai.google.dev/pricing",
        "modalities": ["text", "image", "video"],
    },
    "veo-2.0-generate-001": {
        "display": "Veo 2.0",
        "speed": "~20-60s",
        "strengths": "Balanced speed and quality. Cheaper than Veo 3.1.",
        "price": "see https://ai.google.dev/pricing",
        "modalities": ["text", "image"],
    },
}


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _resolve_google_credentials() -> Tuple[str, bool]:
    """Return (api_key, has_credentials).
    
    Returns (api_key, True) if GOOGLE_API_KEY is set, otherwise (empty, False).
    Callers must check the second return value to know if auth is available.
    Google SDK handles Application Default Credentials automatically.
    """
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    has_creds = bool(api_key)
    return api_key, has_creds


def _init_google_client():
    """Lazily import and configure google.genai client."""
    try:
        import google.genai as genai
        from google.genai import types
        
        api_key, has_creds = _resolve_google_credentials()
        if api_key:
            genai.configure(api_key=api_key)
        
        return genai, types
    except ImportError as exc:
        raise ImportError(
            "google-genai SDK is required for Google video generation. "
            "Install with: pip install google-genai"
        ) from exc


def _save_gcs_video(gcs_uri: str) -> str:
    """Download GCS video to local cache and return path.
    
    Args:
        gcs_uri: gs://bucket/path/to/video.mp4
        
    Returns:
        Absolute path to cached video file.
    """
    try:
        from google.cloud import storage
        from hermes_constants import get_hermes_home
        
        # Parse GCS URI
        if not gcs_uri.startswith("gs://"):
            return gcs_uri  # Not a GCS URI, return as-is
            
        parts = gcs_uri[5:].split("/", 1)
        if len(parts) != 2:
            logger.warning("Invalid GCS URI format: %s", gcs_uri)
            return gcs_uri
            
        bucket_name, blob_path = parts
        
        # Download to cache
        cache_dir = get_hermes_home() / "cache" / "videos"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        local_path = cache_dir / Path(blob_path).name
        if local_path.exists():
            return str(local_path)  # Already cached
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        blob.download_to_filename(str(local_path))
        
        logger.debug("Downloaded GCS video to %s", local_path)
        return str(local_path)
        
    except Exception as exc:
        logger.warning("Failed to download GCS video %s: %s", gcs_uri, exc)
        return gcs_uri  # Fallback to GCS URI


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class GoogleVideoGenProvider(VideoGenProvider):
    """Google Gemini video generation backend (Veo 3.1, Veo 2.0)."""

    @property
    def name(self) -> str:
        return "google"

    @property
    def display_name(self) -> str:
        return "Google"

    def is_available(self) -> bool:
        try:
            _init_google_client()
            return True
        except Exception:
            return False

    def list_models(self) -> List[Dict[str, Any]]:
        return [{"id": mid, **meta} for mid, meta in _MODELS.items()]

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Google Gemini Video",
            "badge": "free/paid",
            "tag": "Veo 3.1 for latest quality, Veo 2.0 for speed; uses GOOGLE_API_KEY or Application Default Credentials",
            "env_vars": [
                {
                    "key": "GOOGLE_API_KEY",
                    "prompt": "Google Generative AI API key (optional if using ADC)",
                    "url": "https://ai.google.dev/",
                }
            ],
        }

    def capabilities(self) -> Dict[str, Any]:
        return {
            "modalities": ["text", "image"],  # video editing not exposed in unified surface
            "aspect_ratios": sorted(VALID_ASPECT_RATIOS),
            "resolutions": sorted(VALID_RESOLUTIONS),
            "max_duration": 120,
            "min_duration": 1,
            "supports_audio": False,  # Audio generation is a separate API
            "supports_negative_prompt": True,
            "max_reference_images": 0,  # Google Veo doesn't support reference images yet
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
                    negative_prompt=negative_prompt,
                ))
            finally:
                loop.close()
        except Exception as exc:
            logger.warning("Google video gen unexpected failure: %s", exc, exc_info=True)
            return error_response(
                error=f"Google video generation failed: {exc}",
                error_type="api_error",
                provider="google",
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
        negative_prompt: Optional[str],
    ) -> Dict[str, Any]:
        try:
            genai, types = _init_google_client()
        except ImportError as exc:
            return error_response(
                error=str(exc),
                error_type="missing_dependency",
                provider="google",
                prompt=prompt,
            )

        prompt = (prompt or "").strip()
        if not prompt:
            return error_response(
                error="prompt is required for Google video generation",
                error_type="missing_prompt",
                provider="google",
                prompt=prompt,
            )

        # Resolve model
        resolved_model = (model or DEFAULT_MODEL).strip()
        if resolved_model not in _MODELS:
            resolved_model = DEFAULT_MODEL
            logger.warning("Unknown model %s, using default %s", model, resolved_model)

        # Normalize parameters
        normalized_aspect_ratio = (aspect_ratio or DEFAULT_ASPECT_RATIO).strip()
        if normalized_aspect_ratio not in VALID_ASPECT_RATIOS:
            normalized_aspect_ratio = DEFAULT_ASPECT_RATIO

        normalized_resolution = (resolution or DEFAULT_RESOLUTION).strip()
        if normalized_resolution not in VALID_RESOLUTIONS:
            normalized_resolution = DEFAULT_RESOLUTION

        clamped_duration = duration if duration is not None else DEFAULT_DURATION
        if clamped_duration < 1:
            clamped_duration = 1
        if clamped_duration > 120:
            clamped_duration = 120

        # Determine modality
        modality_used = "image" if image_url else "text"

        # Build source
        try:
            if image_url:
                source = types.GenerateVideosSource(
                    prompt=prompt,
                    image=types.Image.from_file(image_url) if not image_url.startswith(("http://", "https://", "gs://", "data:")) else types.Image(uri=image_url, mime_type="image/jpeg"),
                )
            else:
                source = types.GenerateVideosSource(prompt=prompt)
        except Exception as exc:
            logger.warning("Failed to parse image_url: %s", exc)
            return error_response(
                error=f"Invalid image URL: {exc}",
                error_type="invalid_image",
                provider="google",
                prompt=prompt,
            )

        # Build config
        try:
            config = types.GenerateVideosConfig(
                output_gcs_uri="gs://hermes-agent-video-cache/",
                duration_seconds=clamped_duration,
                fps=DEFAULT_FPS,
                aspect_ratio=normalized_aspect_ratio,
                resolution=normalized_resolution,
                number_of_videos=1,
                enhance_prompt=True,
            )
            if negative_prompt:
                config.negative_prompt = negative_prompt
        except Exception as exc:
            logger.warning("Failed to build config: %s", exc)
            return error_response(
                error=f"Config error: {exc}",
                error_type="config_error",
                provider="google",
                prompt=prompt,
            )

        # Generate
        try:
            client = genai.Client()
            result = client.models.generate_videos(
                model=resolved_model,
                config=config,
                source=source,
            )
            
            # Poll for completion
            start_time = time.time()
            while time.time() - start_time < DEFAULT_TIMEOUT_SECONDS:
                if hasattr(result, "done") and result.done:
                    break
                # Refresh operation
                await asyncio.sleep(DEFAULT_POLL_INTERVAL_SECONDS)
                result = client.operations.get(result.name)

            # Extract video
            if not result.done:
                return error_response(
                    error=f"Generation timed out after {DEFAULT_TIMEOUT_SECONDS}s",
                    error_type="timeout",
                    provider="google",
                    model=resolved_model,
                    prompt=prompt,
                )

            if result.result() and hasattr(result.result(), "generated_videos"):
                videos = result.result().generated_videos
                if videos and len(videos) > 0:
                    video_uri = videos[0].uri
                    # Download GCS video if needed
                    video_path = _save_gcs_video(video_uri) if video_uri.startswith("gs://") else video_uri
                    
                    return success_response(
                        video=video_path,
                        model=resolved_model,
                        prompt=prompt,
                        modality=modality_used,
                        aspect_ratio=normalized_aspect_ratio,
                        duration=clamped_duration,
                        provider="google",
                        extra={"operation_id": result.name},
                    )

            return error_response(
                error="Video generation completed without output",
                error_type="empty_response",
                provider="google",
                model=resolved_model,
                prompt=prompt,
            )

        except Exception as exc:
            logger.warning("Generation API error: %s", exc, exc_info=True)
            return error_response(
                error=f"Generation failed: {exc}",
                error_type="api_error",
                provider="google",
                model=resolved_model,
                prompt=prompt,
            )


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------


def register(ctx) -> None:
    """Plugin entry point — wire GoogleVideoGenProvider into the registry."""
    ctx.register_video_gen_provider(GoogleVideoGenProvider())
