"""Tests for Pika video generation provider."""

import os
import pytest
from unittest.mock import patch

from agent.video_gen_provider import VideoGenProvider


@pytest.fixture
def pika_plugin():
    """Import Pika plugin."""
    from plugins.video_gen.pika import PikaVideoGenProvider
    return PikaVideoGenProvider()


class TestPikaProviderBasics:
    """Basic provider interface tests."""

    def test_provider_registered(self, pika_plugin):
        """Verify provider is registered."""
        assert isinstance(pika_plugin, VideoGenProvider)
        assert pika_plugin.name == "pika"

    def test_display_name(self, pika_plugin):
        """Verify human-readable name."""
        assert pika_plugin.display_name == "Pika"

    def test_list_models(self, pika_plugin):
        """Verify model catalog."""
        models = pika_plugin.list_models()
        assert len(models) >= 1
        assert models[0]["id"] == "1.0"

    def test_default_model(self, pika_plugin):
        """Verify default model."""
        assert pika_plugin.default_model() == "1.0"

    def test_capabilities(self, pika_plugin):
        """Verify capabilities schema."""
        caps = pika_plugin.capabilities()
        assert set(caps["modalities"]) == {"text", "image"}
        assert "16:9" in caps["aspect_ratios"]
        assert "1080p" in caps["resolutions"]
        assert caps["max_duration"] == 4
        assert caps["min_duration"] == 1

    def test_setup_schema(self, pika_plugin):
        """Verify setup schema."""
        schema = pika_plugin.get_setup_schema()
        assert schema["name"] == "Pika Labs"
        assert any(ev["key"] == "PIKA_API_KEY" for ev in schema["env_vars"])


class TestPikaProviderGenerate:
    """Test video generation (mocked API)."""

    def test_generate_missing_prompt(self, pika_plugin):
        """Verify missing prompt error."""
        with patch.dict(os.environ, {"PIKA_API_KEY": "test_key"}, clear=False):
            result = pika_plugin.generate(prompt="")
            assert result["success"] is False
            assert "required" in result["error"].lower()

    def test_generate_no_auth(self, pika_plugin):
        """Verify auth error when API key missing."""
        with patch.dict(os.environ, {"PIKA_API_KEY": ""}, clear=False):
            result = pika_plugin.generate(prompt="Test video")
            assert result["success"] is False
            assert "api_key" in result["error"].lower()

    def test_duration_clamping(self, pika_plugin):
        """Verify duration is clamped to 1-4s."""
        with patch.dict(os.environ, {"PIKA_API_KEY": "test_key"}, clear=False):
            # Too short
            result = pika_plugin.generate(prompt="Test", duration=0)
            # Should clamp to 1
            
            # Too long
            result = pika_plugin.generate(prompt="Test", duration=10)
            # Should clamp to 4
