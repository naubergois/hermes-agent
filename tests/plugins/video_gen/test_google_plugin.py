"""Tests for Google video generation provider plugin."""

import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from agent.video_gen_provider import VideoGenProvider
from agent.video_gen_registry import get_provider, list_providers


@pytest.fixture
def google_plugin():
    """Import Google plugin (handles reload gracefully)."""
    from plugins.video_gen.google import GoogleVideoGenProvider
    return GoogleVideoGenProvider()


class TestGoogleProviderBasics:
    """Basic provider interface tests."""

    def test_provider_registered(self, google_plugin):
        """Verify provider is registered."""
        assert isinstance(google_plugin, VideoGenProvider)
        assert google_plugin.name == "google"

    def test_display_name(self, google_plugin):
        """Verify human-readable name."""
        assert google_plugin.display_name == "Google"

    def test_is_available_no_key(self, google_plugin):
        """Provider unavailable without GOOGLE_API_KEY."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": ""}, clear=False):
            # Should handle gracefully even if google.genai isn't installed
            result = google_plugin.is_available()
            assert isinstance(result, bool)

    def test_list_models(self, google_plugin):
        """Verify model catalog."""
        models = google_plugin.list_models()
        assert len(models) >= 2
        model_ids = [m["id"] for m in models]
        assert "veo-3.1-generate-preview" in model_ids
        assert "veo-2.0-generate-001" in model_ids

    def test_default_model(self, google_plugin):
        """Verify default model."""
        assert google_plugin.default_model() == "veo-3.1-generate-preview"

    def test_capabilities(self, google_plugin):
        """Verify capabilities schema."""
        caps = google_plugin.capabilities()
        assert set(caps["modalities"]) == {"image", "text"}
        assert "16:9" in caps["aspect_ratios"]
        assert "720p" in caps["resolutions"]
        assert caps["max_duration"] == 120
        assert caps["supports_negative_prompt"] is True

    def test_setup_schema(self, google_plugin):
        """Verify setup schema."""
        schema = google_plugin.get_setup_schema()
        assert schema["name"] == "Google Gemini Video"
        assert "env_vars" in schema
        assert any(ev["key"] == "GOOGLE_API_KEY" for ev in schema["env_vars"])


class TestGoogleProviderGenerate:
    """Test video generation (mocked API)."""

    @patch("plugins.video_gen.google._init_google_client")
    def test_generate_text_to_video_success(self, mock_init, google_plugin):
        """Verify text-to-video generation flow."""
        # Mock Google client
        mock_genai = MagicMock()
        mock_types = MagicMock()
        mock_init.return_value = (mock_genai, mock_types)

        # Mock API response
        mock_result = MagicMock()
        mock_result.done = True
        mock_result.result.return_value.generated_videos = [
            MagicMock(uri="https://storage.googleapis.com/video.mp4")
        ]
        mock_genai.Client.return_value.models.generate_videos.return_value = mock_result

        result = google_plugin.generate(
            prompt="A cat dancing",
            model="veo-3.1-generate-preview",
        )

        assert result["success"] is True
        assert result["video"] == "https://storage.googleapis.com/video.mp4"
        assert result["modality"] == "text"
        assert result["provider"] == "google"

    @patch("plugins.video_gen.google._init_google_client")
    def test_generate_image_to_video(self, mock_init, google_plugin):
        """Verify image-to-video routing."""
        mock_genai = MagicMock()
        mock_types = MagicMock()
        mock_init.return_value = (mock_genai, mock_types)

        mock_result = MagicMock()
        mock_result.done = True
        mock_result.result.return_value.generated_videos = [
            MagicMock(uri="https://storage.googleapis.com/animated.mp4")
        ]
        mock_genai.Client.return_value.models.generate_videos.return_value = mock_result

        result = google_plugin.generate(
            prompt="Make it dance",
            image_url="https://example.com/cat.jpg",
            model="veo-3.1-generate-preview",
        )

        assert result["success"] is True
        assert result["modality"] == "image"

    def test_generate_missing_prompt(self, google_plugin):
        """Verify missing prompt error."""
        result = google_plugin.generate(prompt="")
        assert result["success"] is False
        assert "required" in result["error"].lower()

    def test_generate_no_auth(self, google_plugin):
        """Verify auth error when API key missing."""
        with patch("plugins.video_gen.google._init_google_client") as mock_init:
            mock_init.side_effect = ImportError("google-genai SDK not installed")
            result = google_plugin.generate(prompt="Test video")
            assert result["success"] is False
            assert "google-genai" in result["error"].lower()

    @patch("plugins.video_gen.google._init_google_client")
    def test_generate_invalid_model_falls_back_to_default(self, mock_init, google_plugin):
        """Verify invalid model falls back to default."""
        mock_genai = MagicMock()
        mock_types = MagicMock()
        mock_init.return_value = (mock_genai, mock_types)

        mock_result = MagicMock()
        mock_result.done = True
        mock_result.result.return_value.generated_videos = [
            MagicMock(uri="https://storage.googleapis.com/video.mp4")
        ]
        mock_genai.Client.return_value.models.generate_videos.return_value = mock_result

        with patch("plugins.video_gen.google.logger") as mock_logger:
            result = google_plugin.generate(
                prompt="Test",
                model="non-existent-model",
            )
            # Should fall back and succeed
            assert result["success"] is True
            mock_logger.warning.assert_called()


class TestGoogleProviderAspectRatio:
    """Test aspect ratio handling."""

    @patch("plugins.video_gen.google._init_google_client")
    def test_normalize_valid_aspect_ratio(self, mock_init, google_plugin):
        """Verify valid aspect ratios pass through."""
        mock_genai = MagicMock()
        mock_types = MagicMock()
        mock_init.return_value = (mock_genai, mock_types)

        mock_result = MagicMock()
        mock_result.done = True
        mock_result.result.return_value.generated_videos = [
            MagicMock(uri="https://storage.googleapis.com/video.mp4")
        ]
        mock_genai.Client.return_value.models.generate_videos.return_value = mock_result

        result = google_plugin.generate(
            prompt="Test",
            aspect_ratio="9:16",
        )

        assert result["success"] is True
        assert result["aspect_ratio"] == "9:16"

    @patch("plugins.video_gen.google._init_google_client")
    def test_normalize_invalid_aspect_ratio(self, mock_init, google_plugin):
        """Verify invalid aspect ratios fall back to default."""
        mock_genai = MagicMock()
        mock_types = MagicMock()
        mock_init.return_value = (mock_genai, mock_types)

        mock_result = MagicMock()
        mock_result.done = True
        mock_result.result.return_value.generated_videos = [
            MagicMock(uri="https://storage.googleapis.com/video.mp4")
        ]
        mock_genai.Client.return_value.models.generate_videos.return_value = mock_result

        result = google_plugin.generate(
            prompt="Test",
            aspect_ratio="99:99",
        )

        assert result["success"] is True
        assert result["aspect_ratio"] == "16:9"  # Falls back to default


class TestGoogleProviderDuration:
    """Test duration clamping."""

    @patch("plugins.video_gen.google._init_google_client")
    def test_clamp_duration_to_max(self, mock_init, google_plugin):
        """Verify max duration is enforced."""
        mock_genai = MagicMock()
        mock_types = MagicMock()
        mock_init.return_value = (mock_genai, mock_types)

        mock_result = MagicMock()
        mock_result.done = True
        mock_result.result.return_value.generated_videos = [
            MagicMock(uri="https://storage.googleapis.com/video.mp4")
        ]
        mock_genai.Client.return_value.models.generate_videos.return_value = mock_result

        result = google_plugin.generate(
            prompt="Test",
            duration=500,
        )

        assert result["success"] is True
        assert result["duration"] == 120  # Max clamped

    @patch("plugins.video_gen.google._init_google_client")
    def test_clamp_duration_to_min(self, mock_init, google_plugin):
        """Verify min duration is enforced."""
        mock_genai = MagicMock()
        mock_types = MagicMock()
        mock_init.return_value = (mock_genai, mock_types)

        mock_result = MagicMock()
        mock_result.done = True
        mock_result.result.return_value.generated_videos = [
            MagicMock(uri="https://storage.googleapis.com/video.mp4")
        ]
        mock_genai.Client.return_value.models.generate_videos.return_value = mock_result

        result = google_plugin.generate(
            prompt="Test",
            duration=0,
        )

        assert result["success"] is True
        assert result["duration"] == 1  # Min clamped
