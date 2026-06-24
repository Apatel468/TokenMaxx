"""
Tests for web research pipeline — search, scrape, chat integration (mocked).
"""

from services.content_cleaner import clean_content
from services.context_builder import PromptContext
from services.web_search import SearchResult
from services.web_research_service import (
    apply_web_research_to_context,
    retrieve_web_for_chat,
    should_use_web_research,
    WebResearchResult,
    WebSource,
)
from services.web_scraper import ScrapedPage
from tests.conftest import auth_headers


def test_prompt_analyzer_classifies_web_research():
    from services.prompt_analyzer import analyze_prompt

    result = analyze_prompt("What is OpenAI's latest API pricing?")
    assert result.task_type == "web_research"


def test_should_use_web_research_for_latest_keyword():
    assert should_use_web_research("What is OpenAI's latest pricing?", "general_qa")


def test_should_use_web_research_for_task_type():
    assert should_use_web_research("hello", "web_research")


def test_should_use_web_research_for_direct_url():
    assert should_use_web_research(
        "Summarize https://example.com/docs", "general_qa"
    )


def test_should_not_use_web_research_for_simple_qa():
    assert not should_use_web_research("What is 2+2?", "general_qa")


def test_apply_web_research_updates_system_prompt():
    context = PromptContext(
        prompt="test",
        task_type="web_research",
        confidence=0.8,
        estimated_input_tokens=10,
        is_long_prompt=False,
        keywords_matched=[],
        system_prompt="You are helpful.",
    )
    web = WebResearchResult(
        web_research_used=True,
        search_query="openai pricing",
        search_provider="tavily",
        sources=[WebSource(url="https://example.com", title="Example", snippet="")],
        context_block="Web research content:\n\n### Source: Example\nURL: https://example.com\n\nPricing info.",
    )
    updated = apply_web_research_to_context(context, web)
    assert updated.web_research_used is True
    assert "supplied web content" in updated.system_prompt.lower()
    assert "https://example.com" in updated.system_prompt


def test_retrieve_web_direct_urls_skips_search(monkeypatch):
    monkeypatch.setattr(
        "services.web_research_service.scrape_urls",
        lambda urls, max_pages=5: [
            ScrapedPage(
                url=urls[0],
                title="Example Page",
                content="Important pricing details from the page.",
                word_count=6,
                duration_ms=100,
            )
        ],
    )

    result = retrieve_web_for_chat(
        user_id=1,
        prompt="Summarize https://example.com/pricing",
        task_type="general_qa",
    )
    assert result.web_research_used is True
    assert result.search_provider == "direct"
    assert result.direct_urls is True
    assert len(result.sources) == 1


def test_retrieve_web_search_failure_graceful(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("search down")

    monkeypatch.setattr("services.web_research_service.has_search_provider", lambda: True)
    monkeypatch.setattr("services.web_research_service.search", boom)

    result = retrieve_web_for_chat(
        user_id=2,
        prompt="What is the latest Groq announcement?",
        task_type="web_research",
    )
    assert result.web_research_used is False
    assert "Unable to retrieve web search results" in result.error_message


def test_chat_web_research_metadata(client, auth_token, monkeypatch):
    monkeypatch.setattr(
        "services.chat_service.retrieve_web_for_chat",
        lambda user_id, prompt, task_type, **kwargs: WebResearchResult(
            web_research_used=True,
            search_query="openai pricing",
            search_provider="tavily",
            sources=[
                WebSource(
                    url="https://openai.com/pricing",
                    title="OpenAI Pricing",
                    snippet="API costs",
                    word_count=100,
                )
            ],
            context_block=(
                "Web research content:\n\n"
                "### Source: OpenAI Pricing\n"
                "URL: https://openai.com/pricing\n\n"
                "GPT-4o pricing details."
            ),
            scrape_duration_ms=250.0,
        ),
    )

    response = client.post(
        "/chat",
        json={
            "prompt": "What is OpenAI's latest pricing?",
            "enhance_prompt": False,
        },
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["web_research_used"] is True
    assert body["web_source_count"] == 1
    assert body["web_sources"][0]["url"] == "https://openai.com/pricing"
    assert body["task_type"] == "web_research"
    assert "supplied web content" in body.get("system_prompt", "").lower()


def test_build_fallback_search_query_includes_url_hints():
    from services.web_research_service import _build_fallback_search_query

    query = _build_fallback_search_query(
        "can you describe this and give me the price",
        ["https://www.sephora.com/product/pretty-grunge-eyeshadow-palette-P507079"],
    )
    assert "pretty grunge eyeshadow palette" in query.lower()
    assert "price" in query.lower()


def test_direct_url_scrape_failure_falls_back_to_search(monkeypatch):
    sephora = "https://www.sephora.com/product/pretty-grunge-eyeshadow-palette-P507079"
    alt_url = "https://www.temptalia.com/pretty-grunge-review"

    def fake_scrape(urls, max_pages=5):
        pages = []
        for url in urls:
            if "sephora.com" in url:
                pages.append(
                    ScrapedPage(
                        url=url,
                        title="",
                        content="",
                        word_count=0,
                        duration_ms=50,
                        error="Unable to retrieve content from the source.",
                    )
                )
            else:
                pages.append(
                    ScrapedPage(
                        url=url,
                        title="Pretty Grunge Review",
                        content="This palette retails for $39 and includes 12 shades.",
                        word_count=12,
                        duration_ms=120,
                    )
                )
        return pages

    def fake_search(query, max_results=5):
        return (
            [
                SearchResult(
                    title="Pretty Grunge Review",
                    url=alt_url,
                    snippet="Retail price $39",
                    score=0.9,
                )
            ],
            "tavily",
        )

    monkeypatch.setattr("services.web_research_service.scrape_urls", fake_scrape)
    monkeypatch.setattr("services.web_research_service.has_search_provider", lambda: True)
    monkeypatch.setattr("services.web_research_service.search", fake_search)

    result = retrieve_web_for_chat(
        user_id=99,
        prompt=f"{sephora}\n\ncan you describe the product and give me a price",
        task_type="general_qa",
    )

    assert result.web_research_used is True
    assert result.fallback_used is True
    assert result.fallback_reason == "direct_scrape_blocked"
    assert sephora in result.original_blocked_urls
    assert any("temptalia" in s.url for s in result.sources)


def test_search_fallback_uses_snippets_when_scrape_also_fails(monkeypatch):
    def fake_scrape(urls, max_pages=5):
        return [
            ScrapedPage(
                url=url,
                title="",
                content="",
                word_count=0,
                duration_ms=30,
                error="Unable to retrieve content from the source.",
            )
            for url in urls
        ]

    def fake_search(query, max_results=5):
        return (
            [
                SearchResult(
                    title="Product Info",
                    url="https://example.com/product",
                    snippet="The palette costs $34 at major retailers.",
                    score=0.85,
                )
            ],
            "tavily",
        )

    monkeypatch.setattr("services.web_research_service.scrape_urls", fake_scrape)
    monkeypatch.setattr("services.web_research_service.has_search_provider", lambda: True)
    monkeypatch.setattr("services.web_research_service.search", fake_search)

    result = retrieve_web_for_chat(
        user_id=100,
        prompt="https://www.sephora.com/product/test-product\nwhat is the price?",
        task_type="general_qa",
    )

    assert result.web_research_used is True
    assert result.fallback_used is True
    assert "$34" in result.context_block
    assert "search excerpts" in result.context_block.lower()


def test_direct_url_no_fallback_without_search_api(monkeypatch):
    monkeypatch.setattr(
        "services.web_research_service.scrape_urls",
        lambda urls, max_pages=5: [
            ScrapedPage(
                url=urls[0],
                title="",
                content="",
                word_count=0,
                duration_ms=50,
                error="Unable to retrieve content from the source.",
            )
        ],
    )
    monkeypatch.setattr("services.web_research_service.has_search_provider", lambda: False)

    result = retrieve_web_for_chat(
        user_id=101,
        prompt="https://www.sephora.com/product/test describe and price",
        task_type="general_qa",
    )

    assert result.web_research_used is False
    assert result.fallback_used is False
    assert "Unable to retrieve content" in result.error_message


def test_chat_without_web_research_unchanged(client, auth_token, monkeypatch):
    monkeypatch.setattr(
        "services.web_research_service.should_use_web_research",
        lambda _prompt, _task: False,
    )
    response = client.post(
        "/chat",
        json={"prompt": "What is 2+2?", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["web_research_used"] is False
    assert body["web_source_count"] == 0
