"""Tests for Runway video generation provider plugin."""

import os
import pytest
from unittest.mock import patch

from agent.video_gen_provider import VideoGenProvider


@pytest.fixture
def runway_plugin():
    """Import Runway plugin."""
    from plugins.video_gen.runway import RunwayVideoGenProvider
    return RunwayVideoGenProvider()


class TestRunwayProviderBasics:
    """Basic provider interface tests."""

    def test_provider_registered(self, runway_plugin):
        """Verify provider is registered."""
        assert isinstance(runway_plugin, VideoGenProvider)
        assert runway_plugin.name == "runway"

    def test_display_name(self, runway_plugin):
        """Verify human-readable name."""
        assert runway_plugin.display_name == "Runway"

    def test_list_models(self, runway_plugin):
        """Verify model catalog."""
        models = runway_plugin.list_models()
        assert len(models) >= 2
        model_ids = [m["id"] for m in models]
        assert "gen-3" in model_ids
        assert "gen-3-turbo" in model_ids

    def test_default_model(self, runway_plugin):
        """Verify default model."""
        assert runway_plugin.default_model() == "gen-3"

    def test_capabilities(self, runway_plugin):
        """Verify capabilities schema."""
        caps = runway_plugin.capabilities()
        assert set(caps["modalities"]) == {"image", "text"}
        assert "16:9" in caps["aspect_ratios"]
        assert "1080p" in caps["resolutions"]
        assert caps["max_duration"] == 10

    def test_setup_schema(self, runway_plugin):
        """Verify setup schema."""
        schema = runway_plugin.get_setup_schema()
        assert schema["name"] == "Runway Gen-3"
        assert any(ev["key"] == "RUNWAY_API_KEY" for ev in schema["env_vars"])


class TestRunwayProviderGenerate:
    """Test video generation (mocked API)."""

    def test_generate_missing_prompt(self, runway_plugin):
        """Verify missing prompt error."""
        with patch.dict(os.environ, {"RUNWAY_API_KEY": "test_key"}, clear=False):
            result = runway_plugin.generate(prompt="")
            assert result["success"] is False
            assert "required" in result["error"].lower()

    def test_generate_no_auth(self, runway_plugin):
        """Verify auth error when API key missing."""
        with patch.dict(os.environ, {"RUNWAY_API_KEY": ""}, clear=False):
            result = runway_plugin.generate(prompt="Test video")
            assert result["success"] is False
            assert "api_key" in result["error"].lower()
