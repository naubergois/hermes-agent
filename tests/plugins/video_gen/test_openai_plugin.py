"""Tests for OpenAI DALL-E Video generation provider plugin."""

import os
import pytest
from unittest.mock import patch

from agent.video_gen_provider import VideoGenProvider


@pytest.fixture
def openai_plugin():
    """Import OpenAI plugin."""
    from plugins.video_gen.openai import OpenAIVideoGenProvider
    return OpenAIVideoGenProvider()


class TestOpenAIProviderBasics:
    def test_provider_registered(self, openai_plugin):
        assert isinstance(openai_plugin, VideoGenProvider)
        assert openai_plugin.name == "openai"

    def test_display_name(self, openai_plugin):
        assert openai_plugin.display_name == "OpenAI"

    def test_list_models(self, openai_plugin):
        models = openai_plugin.list_models()
        assert len(models) >= 1
        assert "dall-e-video" in [m["id"] for m in models]

    def test_default_model(self, openai_plugin):
        assert openai_plugin.default_model() == "dall-e-video"

    def test_capabilities(self, openai_plugin):
        caps = openai_plugin.capabilities()
        assert "text" in caps["modalities"]

    def test_generate_missing_prompt(self, openai_plugin):
        result = openai_plugin.generate(prompt="")
        assert result["success"] is False

    def test_generate_no_auth(self, openai_plugin):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            result = openai_plugin.generate(prompt="Test")
            assert result["success"] is False
