"""Tests for render_doc_template URL template rendering."""
import os
from unittest.mock import patch

import pytest


def _render(template: str, site_url: str = "", api_url: str = "") -> str:
    """Call render_doc_template with patched env vars."""
    env = {}
    if site_url:
        env["NEXT_PUBLIC_SITE_URL"] = site_url
    if api_url:
        env["NEXT_PUBLIC_API_URL"] = api_url
    with patch.dict(os.environ, env, clear=False):
        from main import render_doc_template
        return render_doc_template(template)


class TestRenderDocTemplate:
    def test_defaults_when_env_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            from main import render_doc_template
            result = render_doc_template("{{SITE_URL}} {{API_URL}} {{API_BASE}}")
        assert result == "http://localhost:3000 http://localhost:8000/api http://localhost:8000"

    def test_uses_env_vars(self):
        result = _render(
            "Site: {{SITE_URL}}, API: {{API_URL}}, Base: {{API_BASE}}",
            site_url="https://deep-sci-fi.world",
            api_url="https://api.deep-sci-fi.world/api",
        )
        assert result == (
            "Site: https://deep-sci-fi.world, "
            "API: https://api.deep-sci-fi.world/api, "
            "Base: https://api.deep-sci-fi.world"
        )

    def test_strips_trailing_slashes(self):
        result = _render(
            "{{SITE_URL}} {{API_URL}} {{API_BASE}}",
            site_url="https://example.com/",
            api_url="https://api.example.com/api/",
        )
        assert result == "https://example.com https://api.example.com/api https://api.example.com"

    def test_multiple_occurrences(self):
        result = _render(
            "{{API_URL}}/heartbeat and {{API_URL}}/stories",
            api_url="https://api.example.com/api",
        )
        assert result == "https://api.example.com/api/heartbeat and https://api.example.com/api/stories"

    def test_no_tokens_unchanged(self):
        result = _render("Some text with no tokens at all.")
        assert result == "Some text with no tokens at all."

    def test_api_base_when_url_not_ending_in_api(self):
        result = _render(
            "{{API_BASE}}",
            api_url="https://api.example.com/v2",
        )
        # /v2 does not match /api suffix, so API_BASE equals the full URL
        assert result == "https://api.example.com/v2"
