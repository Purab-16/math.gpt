"""Unit tests for the YouTube service. All HTTP calls are mocked (zero quota used)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services import youtube_service
from app.services.youtube_service import parse_search_results, search_math_videos


def make_item(video_id: str, title: str) -> dict:
    """Build one fake item in the YouTube search API format."""
    return {
        "id": {"videoId": video_id},
        "snippet": {
            "title": title,
            "thumbnails": {"medium": {"url": f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"}},
        },
    }


def make_response(items: list) -> MagicMock:
    """Build a fake httpx response that returns the given items."""
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value={"items": items})
    return response


def test_parse_search_results():
    """Verify parsing builds watch URLs, unescapes titles, and skips broken items."""
    data = {
        "items": [
            make_item("abc123", "Algebra &#39;Basics&#39;"),
            {"id": {}, "snippet": {"title": "No video id"}},
        ]
    }

    videos = parse_search_results(data)

    assert len(videos) == 1
    assert videos[0].title == "Algebra 'Basics'"
    assert videos[0].url == "https://www.youtube.com/watch?v=abc123"
    assert videos[0].thumbnail.startswith("https://")


def test_missing_api_key():
    """Verify no API call is made and [] is returned when the key is missing."""
    mock_get = AsyncMock()
    with patch.object(youtube_service, "YOUTUBE_API_KEY", ""), patch.object(
        httpx.AsyncClient, "get", new=mock_get
    ):
        videos = asyncio.run(search_math_videos("linear equations"))

    assert videos == []
    mock_get.assert_not_called()


def test_youtube_failure_returns_empty():
    """Verify network errors return [] instead of raising."""
    with patch.object(youtube_service, "YOUTUBE_API_KEY", "test-key"), patch.object(
        httpx.AsyncClient, "get", new=AsyncMock(side_effect=httpx.ConnectError("offline"))
    ):
        videos = asyncio.run(search_math_videos("linear equations"))

    assert videos == []
    assert len(youtube_service._cache) == 0


def test_english_search():
    """Verify English mode makes one search and returns the videos."""
    mock_get = AsyncMock(return_value=make_response([make_item("en1", "English video")]))
    with patch.object(youtube_service, "YOUTUBE_API_KEY", "test-key"), patch.object(
        httpx.AsyncClient, "get", new=mock_get
    ):
        videos = asyncio.run(search_math_videos("linear equations", language="english"))

    assert len(videos) == 1
    assert mock_get.call_count == 1
    assert mock_get.call_args.kwargs["params"]["relevanceLanguage"] == "en"


def test_hinglish_search_mixes_hindi_and_english():
    """Verify Hinglish mode runs a Hindi and an English search and removes duplicates."""

    async def fake_get(url, params):
        if params["relevanceLanguage"] == "hi":
            return make_response([make_item("hi1", "Hindi video"), make_item("same", "Shared video")])
        return make_response([make_item("en1", "English video"), make_item("same", "Shared video")])

    with patch.object(youtube_service, "YOUTUBE_API_KEY", "test-key"), patch.object(
        httpx.AsyncClient, "get", new=AsyncMock(side_effect=fake_get)
    ):
        videos = asyncio.run(search_math_videos("linear equations", language="hinglish"))

    urls = [video.url for video in videos]
    assert len(urls) == 3
    assert "https://www.youtube.com/watch?v=hi1" in urls
    assert "https://www.youtube.com/watch?v=en1" in urls


def test_cache_avoids_second_call():
    """Verify the same query is served from cache without a second API call."""
    mock_get = AsyncMock(return_value=make_response([make_item("en1", "English video")]))
    with patch.object(youtube_service, "YOUTUBE_API_KEY", "test-key"), patch.object(
        httpx.AsyncClient, "get", new=mock_get
    ):
        first = asyncio.run(search_math_videos("Linear Equations"))
        second = asyncio.run(search_math_videos("linear equations"))

    assert first == second
    assert mock_get.call_count == 1
