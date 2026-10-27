"""YouTube Service module for finding educational math videos."""

import asyncio
import html
import logging
from typing import List

import httpx

from app.cache import TTLCache
from app.config import YOUTUBE_API_KEY
from app.schemas import VideoItem

# Initialize module logger
logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
REQUEST_TIMEOUT_SECONDS = 5.0

# Number of videos to show
ENGLISH_RESULTS = 3
HINGLISH_RESULTS_PER_LANGUAGE = 2

# Simple in-memory cache to save YouTube quota (each search costs 100 units)
CACHE_TTL_SECONDS = 6 * 60 * 60
MAX_CACHE_SIZE = 200
_cache = TTLCache(ttl_seconds=CACHE_TTL_SECONDS, max_size=MAX_CACHE_SIZE)


def parse_search_results(data: dict) -> List[VideoItem]:
    """Convert a YouTube search API response into a list of VideoItem objects.

    Items with a missing video ID, title, or thumbnail are skipped.
    """
    videos: List[VideoItem] = []

    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        snippet = item.get("snippet", {})
        title = snippet.get("title")
        thumbnails = snippet.get("thumbnails", {})
        thumbnail = (thumbnails.get("medium") or thumbnails.get("default") or {}).get("url")

        if not video_id or not title or not thumbnail:
            continue

        videos.append(
            VideoItem(
                # YouTube returns HTML-escaped titles (e.g. &#39;), so unescape them
                title=html.unescape(title),
                url=f"https://www.youtube.com/watch?v={video_id}",
                thumbnail=thumbnail,
            )
        )

    return videos


async def _search(
    client: httpx.AsyncClient,
    query: str,
    max_results: int,
    relevance_language: str,
) -> List[VideoItem]:
    """Run one YouTube search. Returns an empty list on any failure."""
    params = {
        "key": YOUTUBE_API_KEY,
        "q": query,
        "part": "snippet",
        "type": "video",
        "maxResults": max_results,
        "safeSearch": "strict",
        "relevanceLanguage": relevance_language,
    }

    try:
        response = await client.get(SEARCH_URL, params=params)
        response.raise_for_status()
        return parse_search_results(response.json())
    except httpx.HTTPStatusError as err:
        # 403 usually means the daily quota is used up
        logger.warning("YouTube API returned status %d.", err.response.status_code)
    except (httpx.HTTPError, ValueError) as err:
        logger.warning("YouTube search failed: %s", type(err).__name__)

    return []


async def search_math_videos(query: str, language: str = "english") -> List[VideoItem]:
    """Search YouTube for educational math videos matching the query.

    English mode returns English videos. Hinglish mode returns a mix of
    Hindi and English videos. This function never raises: on any failure it
    returns an empty list so the math solution is still shown.

    Args:
        query: Search keywords from the AI solution (search_query field).
        language: 'english' or 'hinglish'.

    Returns:
        List[VideoItem]: Recommended videos (may be empty).
    """
    if not YOUTUBE_API_KEY:
        logger.warning("YouTube API key is not configured. Skipping video search.")
        return []

    clean_query = query.strip()
    if not clean_query:
        return []

    cache_key = (clean_query.lower(), language)
    cached_videos = _cache.get(cache_key)
    if cached_videos is not None:
        logger.info("Returning %d videos from cache.", len(cached_videos))
        return cached_videos

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        if language == "hinglish":
            # Run Hindi and English searches at the same time
            hindi_videos, english_videos = await asyncio.gather(
                _search(client, f"{clean_query} in hindi", HINGLISH_RESULTS_PER_LANGUAGE, "hi"),
                _search(client, clean_query, HINGLISH_RESULTS_PER_LANGUAGE, "en"),
            )
            videos = hindi_videos + english_videos
        else:
            videos = await _search(client, clean_query, ENGLISH_RESULTS, "en")

    # Remove duplicates (same video can appear in both searches)
    unique_videos: List[VideoItem] = []
    seen_urls = set()
    for video in videos:
        if video.url not in seen_urls:
            seen_urls.add(video.url)
            unique_videos.append(video)

    # Only cache successful results, so a temporary failure is retried next time
    if unique_videos:
        _cache.set(cache_key, unique_videos)

    logger.info("Found %d video recommendations.", len(unique_videos))
    return unique_videos
