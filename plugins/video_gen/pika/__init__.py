"""Pika Labs video generation provider.

High-quality short-form video generation (1-4 seconds).
Specializes in smooth, cinematic video generation from text or images.

API: https://docs.pika.art/
"""

import asyncio
import base64
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

from agent.video_gen_provider import VideoGenProvider, error_response, success_response


class PikaVideoGenProvider(VideoGenProvider):
    """Pika Labs video generation provider."""

    def __init__(self):
        """Initialize Pika provider."""
        self._name = "pika"
        self.base_url = "https://api.pika.art/v1"
        self._api_key = os.getenv("PIKA_API_KEY", "").strip()

    @property
    def name(self) -> str:
        """Get provider name."""
        return self._name

    @property
    def display_name(self) -> str:
        """Human-readable provider name."""
        return "Pika"

    def is_available(self) -> bool:
        """Check if provider is available."""
        return bool(self._api_key)

    def list_models(self) -> list[dict]:
        """List available models."""
        return [
            {
                "id": "1.0",
                "name": "Pika 1.0",
                "description": "High-quality video generation (1-4 seconds)",
            }
        ]

    def default_model(self) -> str:
        """Get default model."""
        return "1.0"

    def get_setup_schema(self) -> dict:
        """Get setup schema for configuration."""
        return {
            "name": "Pika Labs",
            "description": "High-quality short-form video generation",
            "env_vars": [
                {
                    "key": "PIKA_API_KEY",
                    "description": "Pika Labs API key",
                    "url": "https://console.pika.art/",
                    "required": True,
                }
            ],
            "models": self.list_models(),
        }

    def capabilities(self) -> dict:
        """Get provider capabilities."""
        return {
            "modalities": ["text", "image"],
            "min_duration": 1,
            "max_duration": 4,
            "aspect_ratios": ["16:9", "9:16", "1:1"],
            "resolutions": ["576p", "768p", "960p", "1080p"],
            "features": {
                "negative_prompts": False,
                "seed": False,
                "motion_controls": True,
                "quality_settings": ["standard", "high"],
            },
        }

    def generate(
        self,
        prompt: str = "",
        image_url: str = "",
        model: str = "",
        duration: int = 2,
        resolution: str = "1080p",
        aspect_ratio: str = "16:9",
        **kwargs,
    ) -> dict:
        """Generate video."""
        # Validate input
        if not prompt and not image_url:
            return error_response(
                "Prompt or image_url is required",
                "validation_error",
                self.name,
            )

        if not self._api_key:
            return error_response(
                "PIKA_API_KEY not set. Get one from https://console.pika.art/",
                "auth_error",
                self.name,
            )

        # Clamp duration
        duration = max(1, min(4, duration))

        # Normalize resolution
        res_map = {"576p": "576", "768p": "768", "960p": "960", "1080p": "1080"}
        resolution_str = res_map.get(resolution, "1080")

        # Determine modality
        modality = "image-to-video" if image_url else "text-to-video"

        # Run async generation
        try:
            result = asyncio.run(
                self._generate_async(
                    prompt=prompt,
                    image_url=image_url,
                    duration=duration,
                    resolution=resolution_str,
                    aspect_ratio=aspect_ratio,
                    modality=modality,
                    **kwargs,
                )
            )
            return result
        except Exception as e:
            return error_response(str(e), "generation_error", self.name)

    async def _generate_async(
        self,
        prompt: str,
        image_url: str,
        duration: int,
        resolution: str,
        aspect_ratio: str,
        modality: str,
        **kwargs,
    ) -> dict:
        """Generate video asynchronously."""
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=600.0) as client:
            # Prepare payload
            payload = {
                "width": 1080 if "1080" in resolution else int(resolution),
                "height": 1080 if "1080" in resolution else int(resolution),
                "duration": duration,
            }

            # Add prompt or image
            if image_url:
                # Download and encode image
                try:
                    image_data = await self._fetch_image(image_url)
                    payload["source_image"] = f"data:image/png;base64,{image_data}"
                except Exception as e:
                    return error_response(f"Failed to fetch image: {e}", "image_error", self.name)
            else:
                payload["prompt"] = prompt

            # Create generation request
            try:
                create_response = await client.post(
                    f"{self.base_url}/generations", json=payload, headers=headers
                )
                create_response.raise_for_status()
                gen_data = create_response.json()
            except httpx.HTTPError as e:
                return error_response(f"Generation request failed: {e}", "api_error", self.name)

            # Get generation ID
            gen_id = gen_data.get("id")
            if not gen_id:
                return error_response("No generation ID returned", "api_error", self.name)

            # Poll for completion
            start_time = time.time()
            timeout = 600  # 10 minutes
            poll_interval = 5

            while time.time() - start_time < timeout:
                try:
                    status_response = await client.get(
                        f"{self.base_url}/generations/{gen_id}", headers=headers
                    )
                    status_response.raise_for_status()
                    status_data = status_response.json()
                except httpx.HTTPError as e:
                    return error_response(f"Status check failed: {e}", "api_error", self.name)

                status = status_data.get("status", "")

                if status == "completed":
                    # Get video URL
                    video_url = status_data.get("video_url", "")
                    if not video_url:
                        return error_response("No video URL in response", "api_error", self.name)

                    # Fetch video and encode
                    try:
                        video_response = await client.get(video_url)
                        video_response.raise_for_status()
                        video_data = base64.b64encode(video_response.content).decode()
                    except httpx.HTTPError as e:
                        return error_response(f"Failed to fetch video: {e}", "download_error", self.name)

                    return success_response(
                        video=video_data,
                        model=self.default_model(),
                        prompt=prompt or f"Image: {image_url}",
                        modality=modality,
                        aspect_ratio=aspect_ratio,
                        duration=duration,
                        provider=self.name,
                    )

                elif status == "failed":
                    error_msg = status_data.get("error", "Unknown error")
                    return error_response(f"Generation failed: {error_msg}", "generation_error", self.name)

                # Wait before next poll
                await asyncio.sleep(poll_interval)

            return error_response("Generation timeout (10 minutes)", "timeout_error", self.name)

    async def _fetch_image(self, image_url: str) -> str:
        """Fetch and encode image as base64."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            return base64.b64encode(response.content).decode()


def register(ctx) -> None:
    """Plugin entry point."""
    ctx.register_video_gen_provider(PikaVideoGenProvider())
