"""Studio in-product documentation route tests."""

from __future__ import annotations


def test_docs_home_returns_cards(studio_client):
    response = studio_client.get("/docs")

    assert response.status_code == 200
    assert 'class="docs-cards"' in response.text
    assert 'href="/docs/guides/agents"' in response.text
    assert "Getting started" in response.text


def test_docs_page_renders_article_and_sidebar(studio_client):
    response = studio_client.get("/docs/guides/agents")

    assert response.status_code == 200
    assert "<h1" in response.text
    assert 'class="docs-sidebar"' in response.text
    assert 'class="docs-article"' in response.text
    assert 'aria-current="page"' in response.text


def test_unknown_docs_page_returns_404(studio_client):
    response = studio_client.get("/docs/does/not/exist")

    assert response.status_code == 404
