"""Data models for twdownload representing tweets, media items, and resolution variants."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class VideoVariant:
    """Represents a specific resolution / bitrate variant of a video or GIF."""
    url: str
    width: int = 0
    height: int = 0
    bitrate: int = 0
    content_type: str = "video/mp4"
    filesize_approx: Optional[int] = None

    @property
    def resolution_label(self) -> str:
        """Resolution formatted as WIDTHxHEIGHT (e.g., '1280x720')."""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "Original"

    @property
    def standard_label(self) -> str:
        """Standard vertical resolution tag (e.g., '720p', '1080p')."""
        if self.height:
            return f"{self.height}p"
        return self.resolution_label

    def format_menu_item(self, is_highest: bool = False, is_lowest: bool = False) -> str:
        """Formats the variant into a readable menu description line."""
        tags = []
        if is_highest:
            tags.append("Highest Quality")
        elif is_lowest:
            tags.append("Lowest Quality")

        tag_str = f" [{', '.join(tags)}]" if tags else ""

        if self.bitrate > 0:
            if self.bitrate >= 1_000_000:
                bitrate_str = f"~{self.bitrate / 1_000_000:.2f} Mbps"
            else:
                bitrate_str = f"~{self.bitrate // 1000} kbps"
        else:
            bitrate_str = "direct stream"

        size_str = ""
        if self.filesize_approx and self.filesize_approx > 0:
            mb = self.filesize_approx / (1024 * 1024)
            size_str = f", ~{mb:.1f} MB"

        return f"{self.resolution_label:<10} ({self.standard_label}, {bitrate_str}{size_str}){tag_str}"


@dataclass
class MediaItem:
    """Represents a single media item attached to a tweet (video, photo, or gif)."""
    media_type: str  # "video", "photo", "gif"
    id: str
    original_url: str
    variants: List[VideoVariant] = field(default_factory=list)
    photo_urls: List[str] = field(default_factory=list)
    duration_millis: Optional[int] = None
    thumbnail_url: Optional[str] = None
    alt_text: Optional[str] = None


@dataclass
class TweetMedia:
    """Represents tweet metadata and all attached media items."""
    tweet_id: str
    author_name: str
    author_screen_name: str
    text: str
    media_items: List[MediaItem] = field(default_factory=list)

    @property
    def has_media(self) -> bool:
        return len(self.media_items) > 0
