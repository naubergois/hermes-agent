"""Tests for Luma Dream Machine video generation provider plugin."""

import os
import pytest
from unittest.mock import patch

from agent.video_gen_provider import VideoGenProvider


@pytest.fixture
def luma_plugin():
    """Import Luma plugin."""
    from plugins.video_gen.luma import LumaVideoGenProvider
    return LumaVideoGenProvider()


class TestLumaProviderBasics:
    def test_provider_registered(self, luma_plugin):
        assert isinstance(luma_plugin, VideoGenProvider)
        assert luma_plugin.name == "luma"

    def test_display_name(self, luma_plugin):
        assert luma_plugin.display_name == "Luma"

    def test_list_models(self, luma_plugin):
        models = luma_plugin.list_models()
        assert len(models) >= 1
        assert "dream-machine" in [m["id"] for m in models]

    def test_default_model(self, luma_plugin):
        assert luma_plugin.default_model() == "dream-machine"

    def test_capabilities(self, luma_plugin):
        caps = luma_plugin.capabilities()
        assert set(caps["modalities"]) == {"image", "text"}
        assert "1080p" in caps["resolutions"]
        assert caps["max_duration"] == 5

    def test_generate_missing_prompt(self, luma_plugin):
        result = luma_plugin.generate(prompt="")
        assert result["success"] is False

    def test_generate_no_auth(self, luma_plugin):
        with patch.dict(os.environ, {"LUMA_API_KEY": ""}, clear=False):
            result = luma_plugin.generate(prompt="Test")
            assert result["success"] is False
