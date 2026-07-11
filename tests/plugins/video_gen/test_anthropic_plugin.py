"""Tests for Anthropic video generation provider plugin."""

import os
import pytest
from unittest.mock import patch

from agent.video_gen_provider import VideoGenProvider


@pytest.fixture
def anthropic_plugin():
    """Import Anthropic plugin."""
    from plugins.video_gen.anthropic import AnthropicVideoGenProvider
    return AnthropicVideoGenProvider()


class TestAnthropicProviderBasics:
    def test_provider_registered(self, anthropic_plugin):
        assert isinstance(anthropic_plugin, VideoGenProvider)
        assert anthropic_plugin.name == "anthropic"

    def test_display_name(self, anthropic_plugin):
        assert anthropic_plugin.display_name == "Anthropic"

    def test_list_models(self, anthropic_plugin):
        models = anthropic_plugin.list_models()
        assert len(models) >= 1
        assert "claude-video" in [m["id"] for m in models]

    def test_default_model(self, anthropic_plugin):
        assert anthropic_plugin.default_model() == "claude-video"

    def test_capabilities(self, anthropic_plugin):
        caps = anthropic_plugin.capabilities()
        assert set(caps["modalities"]) == {"image", "text"}

    def test_generate_missing_prompt(self, anthropic_plugin):
        result = anthropic_plugin.generate(prompt="")
        assert result["success"] is False

    def test_generate_no_auth(self, anthropic_plugin):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
            result = anthropic_plugin.generate(prompt="Test")
            assert result["success"] is False
