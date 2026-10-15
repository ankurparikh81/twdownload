"""Streaming chunked downloader module for twdownload with dynamic progress display."""

import os
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Optional

from twdownload.extractor import DEFAULT_HEADERS


def format_bytes(num_bytes: int) -> str:
    """Formats bytes into human readable string (KB, MB, GB)."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_seconds(seconds: float) -> str:
    """Formats seconds into MM:SS."""
    if seconds < 0 or seconds > 3600 * 24:
        return "--:--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def sanitize_filename(name: str) -> str:
    """Sanitizes filename removing illegal characters."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def generate_filename(
    author_screen_name: str,
    tweet_id: str,
    media_type: str,
    resolution: Optional[str] = None,
    index: int = 0,
    ext: str = "mp4",
) -> str:
    """Generates a structured, clean filename for downloaded media."""
    prefix = author_screen_name if author_screen_name and author_screen_name != "unknown" else "tweet"
    parts = [prefix, tweet_id]

    if media_type == "photo":
        parts.append(f"photo{index + 1 if index > 0 else ''}".rstrip())
    elif media_type == "gif":
        parts.append("gif")
    elif resolution:
        parts.append(resolution)

    base = "_".join(parts)
    return sanitize_filename(f"{base}.{ext}")


def download_file(
    url: str,
    output_path: str,
    quiet: bool = False,
    chunk_size: int = 64 * 1024,
    stream=sys.stdout,
) -> str:
    """Downloads a file via streaming HTTP chunks with real-time terminal progress.

    Args:
        url: Remote file URL to download.
        output_path: Destination local file path.
        quiet: If True, suppresses progress reporting.
        chunk_size: Read buffer chunk size in bytes (default 64 KB).
        stream: Output stream for progress bar.

    Returns:
        Absolute path to the downloaded file.
    """
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Check if target already exists; prompt if interactive
    if os.path.exists(output_path):
        if not quiet and sys.stdin.isatty():
            stream.write(f"File '{os.path.basename(output_path)}' already exists. Overwrite? [y/N]: ")
            stream.flush()
            try:
                ans = input().strip().lower()
            except (EOFError, KeyboardInterrupt):
                stream.write("\n")
                sys.exit(130)

            if ans not in ("y", "yes"):
                # Append duplicate counter
                base, ext = os.path.splitext(output_path)
                counter = 1
                while os.path.exists(f"{base}_{counter}{ext}"):
                    counter += 1
                output_path = f"{base}_{counter}{ext}"
                stream.write(f"Saving to new file: {os.path.basename(output_path)}\n")
                stream.flush()

    part_path = f"{output_path}.part"
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)

    start_time = time.time()
    downloaded = 0
    total_size = 0

    try:
        with urllib.request.urlopen(req, timeout=30) as resp, open(part_path, "wb") as out_file:
            header_len = resp.headers.get("Content-Length")
            if header_len and header_len.isdigit():
                total_size = int(header_len)

            bar_width = 30
            last_render_time = 0.0

            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)

                current_time = time.time()
                # Update progress bar ~10 times per second
                if not quiet and (current_time - last_render_time > 0.1):
                    last_render_time = current_time
                    elapsed = max(current_time - start_time, 0.001)
                    speed = downloaded / elapsed

                    if total_size > 0:
                        pct = min(downloaded / total_size, 1.0)
                        filled = int(bar_width * pct)
                        bar = "=" * filled + (">" if filled < bar_width else "")
                        bar = bar.ljust(bar_width)
                        remaining = max(total_size - downloaded, 0)
                        eta_sec = remaining / speed if speed > 0 else 0

                        status_line = (
                            f"\r[{bar}] {pct * 100:5.1f}% "
                            f"({format_bytes(downloaded)}/{format_bytes(total_size)}) "
                            f"{format_bytes(int(speed))}/s ETA {format_seconds(eta_sec)}"
                        )
                    else:
                        status_line = (
                            f"\rDownloading: {format_bytes(downloaded)} "
                            f"at {format_bytes(int(speed))}/s..."
                        )

                    stream.write(status_line)
                    stream.flush()

        # Final progress bar completion render
        if not quiet:
            elapsed = max(time.time() - start_time, 0.001)
            speed = downloaded / elapsed
            if total_size > 0:
                bar = "=" * bar_width
                status_line = (
                    f"\r[{bar}] 100.0% "
                    f"({format_bytes(downloaded)}/{format_bytes(total_size)}) "
                    f"{format_bytes(int(speed))}/s in {format_seconds(elapsed)}\n"
                )
            else:
                status_line = f"\rDownloaded {format_bytes(downloaded)} in {format_seconds(elapsed)}\n"
            stream.write(status_line)
            stream.flush()

        # Atomic rename on success
        if os.path.exists(output_path):
            os.remove(output_path)
        os.rename(part_path, output_path)
        return os.path.abspath(output_path)

    except (KeyboardInterrupt, Exception):
        # Clean up partial download file
        if os.path.exists(part_path):
            try:
                os.remove(part_path)
            except OSError:
                pass
        raise
