"""YouTube Service module for finding educational math videos."""

from typing import List, Dict
from app.config import YOUTUBE_API_KEY


async def search_math_videos(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """Search YouTube Data API v3 for educational math videos matching the query.

    Args:
        query: Search keywords or topic for math tutorial videos.
        max_results: Maximum number of video recommendations to return (default is 3).

    Returns:
        List[Dict[str, str]]: List of video objects, each containing:
                              - title: Video title
                              - url: Full YouTube watch URL
                              - thumbnail: Video thumbnail image URL

    Raises:
        NotImplementedError: Stub function for project setup.
    """
    # TODO: Verify that YOUTUBE_API_KEY is configured in environment.
    # TODO: Use httpx.AsyncClient to query the YouTube Data API v3 search endpoint:
    #       https://www.googleapis.com/youtube/v3/search
    # TODO: Pass query parameters:
    #       - key: YOUTUBE_API_KEY
    #       - q: query
    #       - part: 'snippet'
    #       - type: 'video'
    #       - maxResults: max_results
    # TODO: Parse the JSON response to extract video IDs, titles, and thumbnails.
    # TODO: Construct watch URLs (https://www.youtube.com/watch?v={video_id}).
    # TODO: Return list of video dictionaries matching the VideoItem schema.
    raise NotImplementedError("YouTube service search logic will be implemented in a future step.")
