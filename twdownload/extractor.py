"""Media extractor module for twdownload.

Supports extracting media from X / Twitter posts using a dual-engine approach:
1. FixTweet API (api.fxtwitter.com) as primary engine.
2. Twitter Syndication API (cdn.syndication.twimg.com) as fallback engine.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from twdownload.models import MediaItem, TweetMedia, VideoVariant

# Default headers matching a standard modern browser
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


class TweetError(Exception):
    """Base class for twdownload extraction errors."""
    pass


class InvalidTweetURLError(TweetError):
    """Raised when the provided input is not a recognized Tweet URL or ID."""
    pass


class TweetNotFoundError(TweetError):
    """Raised when the specified Tweet is not found, private, or deleted."""
    pass


class NoMediaFoundError(TweetError):
    """Raised when the Tweet exists but contains no downloadable media."""
    pass


class ExtractionError(TweetError):
    """Raised when both primary and fallback extractors fail."""
    pass


def extract_tweet_id(url_or_id: str) -> str:
    """Extracts the numeric status ID from a Tweet URL or plain ID string.

    Supports:
      - https://x.com/username/status/1234567890
      - https://twitter.com/username/status/1234567890?s=20
      - https://x.com/i/status/1234567890
      - https://mobile.twitter.com/username/status/1234567890/video/1
      - 1234567890
    """
    s = url_or_id.strip()
    if not s:
        raise InvalidTweetURLError("Input cannot be empty.")

    if s.isdigit():
        return s

    pattern = r"(?:twitter\.com|x\.com)/(?:[^/]+/status/|i/status/)(\d+)"
    match = re.search(pattern, s, re.IGNORECASE)
    if match:
        return match.group(1)

    raise InvalidTweetURLError(
        f"Could not extract a valid Tweet ID from '{url_or_id}'. "
        "Expected a format like 'https://x.com/user/status/1234567890'."
    )


def _http_get_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> Dict[str, Any]:
    """Helper to fetch and parse JSON over HTTP using urllib."""
    req_headers = dict(DEFAULT_HEADERS)
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise TweetNotFoundError(f"Resource not found (HTTP 404) at {url}")
        raise ExtractionError(f"HTTP error {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise ExtractionError(f"Network error connecting to {url}: {e.reason}")
    except json.JSONDecodeError as e:
        raise ExtractionError(f"Failed to parse response JSON from {url}: {e}")


def _extract_dimensions_from_url(url: str) -> Tuple[int, int]:
    """Extracts width and height from Twitter video URLs like /vid/avc1/1280x720/."""
    m = re.search(r"/vid/(?:avc1/)?(\d+)x(\d+)/", url)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, 0


def _parse_fxtwitter(data: Dict[str, Any], tweet_id: str) -> TweetMedia:
    """Parses response from api.fxtwitter.com."""
    code = data.get("code")
    if code != 200 or not data.get("tweet"):
        raise TweetNotFoundError(f"Tweet {tweet_id} not found on FixTweet API.")

    tweet_data = data["tweet"]
    author = tweet_data.get("author", {})
    author_name = author.get("name", "Unknown")
    author_screen_name = author.get("screen_name", "unknown")
    text = tweet_data.get("text", "")

    media_data = tweet_data.get("media", {})
    if not media_data:
        raise NoMediaFoundError(f"Tweet {tweet_id} has no media attached.")

    items: List[MediaItem] = []

    # 1. Videos & Animated GIFs
    video_list = media_data.get("videos") or []
    # If media.all exists and has videos not in videos list
    if not video_list and "all" in media_data:
        video_list = [m for m in media_data.get("all", []) if m.get("type") in ("video", "gif")]

    for v_idx, v in enumerate(video_list):
        media_id = str(v.get("id", f"{tweet_id}_vid_{v_idx}"))
        orig_url = v.get("url", "")
        duration_sec = v.get("duration", 0)
        duration_millis = int(duration_sec * 1000) if duration_sec else None
        thumb_url = v.get("thumbnail_url")
        m_type = "gif" if v.get("type") == "gif" else "video"

        # Formats list
        raw_formats = v.get("formats", [])
        if not raw_formats and "variants" in v:
            raw_formats = v.get("variants", [])

        variants: List[VideoVariant] = []
        seen_res = set()

        for f in raw_formats:
            f_url = f.get("url", "")
            # Skip m3u8 playlists when direct mp4 streams exist
            container = f.get("container", "").lower()
            content_type = f.get("content_type", "").lower()
            if ".m3u8" in f_url or container == "m3u8" or "application/x-mpegurl" in content_type:
                continue

            width = f.get("width", 0)
            height = f.get("height", 0)
            if width == 0 or height == 0:
                extracted_w, extracted_h = _extract_dimensions_from_url(f_url)
                width = width or extracted_w
                height = height or extracted_h

            bitrate = f.get("bitrate", 0)
            filesize = None
            if bitrate > 0 and duration_sec > 0:
                filesize = int((bitrate / 8) * duration_sec)

            res_key = f"{width}x{height}" if width and height else f_url
            if res_key not in seen_res:
                seen_res.add(res_key)
                variants.append(
                    VideoVariant(
                        url=f_url,
                        width=width,
                        height=height,
                        bitrate=bitrate,
                        content_type="video/mp4",
                        filesize_approx=filesize,
                    )
                )

        # Fallback if no mp4 variants parsed: use direct video URL
        if not variants and orig_url and ".m3u8" not in orig_url:
            w, h = _extract_dimensions_from_url(orig_url)
            variants.append(
                VideoVariant(
                    url=orig_url,
                    width=w or v.get("width", 0),
                    height=h or v.get("height", 0),
                    bitrate=0,
                    content_type="video/mp4",
                )
            )

        # Sort variants descending: resolution (area) first, then bitrate
        variants.sort(key=lambda x: (x.width * x.height, x.bitrate), reverse=True)

        items.append(
            MediaItem(
                media_type=m_type,
                id=media_id,
                original_url=orig_url,
                variants=variants,
                duration_millis=duration_millis,
                thumbnail_url=thumb_url,
            )
        )

    # 2. Photos
    photo_list = media_data.get("photos") or []
    if not photo_list and "all" in media_data:
        photo_list = [m for m in media_data.get("all", []) if m.get("type") == "photo"]

    for p_idx, p in enumerate(photo_list):
        media_id = str(p.get("id", f"{tweet_id}_photo_{p_idx}"))
        raw_url = p.get("url", "")
        # Normalize to highest original quality
        if "?" in raw_url:
            base_url = raw_url.split("?")[0]
            orig_quality_url = f"{base_url}?name=orig"
        else:
            orig_quality_url = f"{raw_url}?name=orig"

        items.append(
            MediaItem(
                media_type="photo",
                id=media_id,
                original_url=orig_quality_url,
                variants=[],
                photo_urls=[orig_quality_url],
                alt_text=p.get("altText"),
            )
        )

    if not items:
        raise NoMediaFoundError(f"Tweet {tweet_id} contains no downloadable video, image, or GIF.")

    return TweetMedia(
        tweet_id=tweet_id,
        author_name=author_name,
        author_screen_name=author_screen_name,
        text=text,
        media_items=items,
    )


def _parse_syndication(data: Dict[str, Any], tweet_id: str) -> TweetMedia:
    """Parses response from cdn.syndication.twimg.com/tweet-result."""
    user = data.get("user", {})
    author_name = user.get("name", "Unknown")
    author_screen_name = user.get("screen_name", "unknown")
    text = data.get("text", "")

    media_details = data.get("mediaDetails", [])
    if not media_details:
        raise NoMediaFoundError(f"Tweet {tweet_id} has no media details attached.")

    items: List[MediaItem] = []

    for m_idx, m in enumerate(media_details):
        m_type = m.get("type", "video")
        media_id = str(m.get("id_str", f"{tweet_id}_media_{m_idx}"))
        thumb_url = m.get("media_url_https", "")

        if m_type in ("video", "animated_gif"):
            video_info = m.get("video_info", {})
            duration_millis = video_info.get("duration_millis")
            duration_sec = (duration_millis / 1000) if duration_millis else 0
            raw_variants = video_info.get("variants", [])

            variants: List[VideoVariant] = []
            seen_res = set()

            for v in raw_variants:
                v_url = v.get("url", "")
                c_type = v.get("content_type", "")
                if c_type != "video/mp4" or ".m3u8" in v_url:
                    continue

                width, height = _extract_dimensions_from_url(v_url)
                if width == 0 and "original_info" in m:
                    width = m["original_info"].get("width", 0)
                    height = m["original_info"].get("height", 0)

                bitrate = v.get("bitrate", 0)
                filesize = int((bitrate / 8) * duration_sec) if bitrate and duration_sec else None

                res_key = f"{width}x{height}" if width and height else v_url
                if res_key not in seen_res:
                    seen_res.add(res_key)
                    variants.append(
                        VideoVariant(
                            url=v_url,
                            width=width,
                            height=height,
                            bitrate=bitrate,
                            content_type="video/mp4",
                            filesize_approx=filesize,
                        )
                    )

            variants.sort(key=lambda x: (x.width * x.height, x.bitrate), reverse=True)

            items.append(
                MediaItem(
                    media_type="gif" if m_type == "animated_gif" else "video",
                    id=media_id,
                    original_url=variants[0].url if variants else "",
                    variants=variants,
                    duration_millis=duration_millis,
                    thumbnail_url=thumb_url,
                )
            )

        elif m_type == "photo":
            photo_url = m.get("media_url_https", "")
            if "?" in photo_url:
                base_url = photo_url.split("?")[0]
                orig_url = f"{base_url}?name=orig"
            else:
                orig_url = f"{photo_url}?name=orig"

            items.append(
                MediaItem(
                    media_type="photo",
                    id=media_id,
                    original_url=orig_url,
                    variants=[],
                    photo_urls=[orig_url],
                )
            )

    if not items:
        raise NoMediaFoundError(f"No downloadable media found in Tweet {tweet_id}.")

    return TweetMedia(
        tweet_id=tweet_id,
        author_name=author_name,
        author_screen_name=author_screen_name,
        text=text,
        media_items=items,
    )


def fetch_tweet_media(tweet_id_or_url: str) -> TweetMedia:
    """Fetches media from a Tweet using dual-engine fallback (FixTweet -> Syndication)."""
    tweet_id = extract_tweet_id(tweet_id_or_url)
    errors: List[str] = []

    # 1. Primary engine: FixTweet API
    fx_url = f"https://api.fxtwitter.com/status/{tweet_id}"
    try:
        data = _http_get_json(fx_url)
        return _parse_fxtwitter(data, tweet_id)
    except TweetNotFoundError:
        # Don't try fallback if it was explicitly a 404
        errors.append(f"FixTweet: Tweet {tweet_id} not found.")
    except NoMediaFoundError:
        raise
    except Exception as e:
        errors.append(f"FixTweet engine error: {e}")

    # 2. Fallback engine: Twitter Syndication API
    syndication_url = f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&token=x"
    try:
        data = _http_get_json(syndication_url)
        return _parse_syndication(data, tweet_id)
    except TweetNotFoundError:
        errors.append(f"Syndication API: Tweet {tweet_id} not found.")
    except NoMediaFoundError:
        raise
    except Exception as e:
        errors.append(f"Syndication engine error: {e}")

    raise ExtractionError(
        f"Unable to fetch media for Tweet ID {tweet_id}. All extractors failed:\n" +
        "\n".join(f"  - {err}" for err in errors)
    )
