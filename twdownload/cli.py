"""Command line interface for twdownload."""

import argparse
import os
import sys
from typing import List, Optional

from twdownload import __version__
from twdownload.downloader import download_file, format_bytes, generate_filename
from twdownload.extractor import (
    ExtractionError,
    InvalidTweetURLError,
    NoMediaFoundError,
    TweetError,
    TweetNotFoundError,
    fetch_tweet_media,
)
from twdownload.models import TweetMedia
from twdownload.ui import prompt_resolution_selection


def create_parser() -> argparse.ArgumentParser:
    """Creates the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="twdownload",
        description="Download media from X (Twitter) posts with resolution selection.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Interactive download (prompts for resolution menu if video has multiple options):
  twdownload https://x.com/jaynitx/status/2109957970591412722?s=20

  # Automatically pick highest quality:
  twdownload https://x.com/jaynitx/status/2109957970591412722 --best

  # Save to a custom directory:
  twdownload https://x.com/jaynitx/status/2109957970591412722 -o ~/Videos

  # Inspect media without downloading:
  twdownload https://x.com/jaynitx/status/2109957970591412722 --info
""",
    )

    parser.add_argument(
        "url",
        nargs="?",
        help="URL or ID of the tweet (e.g., https://x.com/user/status/123456...)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=".",
        help="Directory to save downloaded media (default: current directory).",
    )
    parser.add_argument(
        "-f",
        "--filename",
        help="Custom filename for the downloaded file (only for single media).",
    )
    parser.add_argument(
        "-b",
        "--best",
        action="store_true",
        help="Automatically select the highest resolution without prompting.",
    )
    parser.add_argument(
        "-w",
        "--worst",
        action="store_true",
        help="Automatically select the lowest resolution without prompting.",
    )
    parser.add_argument(
        "-r",
        "--resolution",
        help="Target resolution to download (e.g. '720p', '1280x720').",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Display tweet information and available resolutions without downloading.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress informational output and progress bars.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def print_tweet_info(media: TweetMedia, stream=None) -> None:
    """Displays formatted tweet and media metadata."""
    if stream is None:
        stream = sys.stdout
    stream.write(f"\nTweet ID : {media.tweet_id}\n")
    stream.write(f"Author   : {media.author_name} (@{media.author_screen_name})\n")
    preview_text = media.text.strip().replace("\n", " ")
    if len(preview_text) > 80:
        preview_text = preview_text[:77] + "..."
    stream.write(f"Content  : {preview_text}\n")
    stream.write(f"Media    : {len(media.media_items)} item(s)\n")

    for idx, item in enumerate(media.media_items, 1):
        stream.write(f"\n  [Item {idx}] Type: {item.media_type.upper()}\n")
        if item.media_type in ("video", "gif") and item.variants:
            stream.write(f"  Available Resolutions ({len(item.variants)}):\n")
            for v_idx, v in enumerate(item.variants):
                is_highest = (v_idx == 0)
                is_lowest = (v_idx == len(item.variants) - 1)
                stream.write(f"    - {v.format_menu_item(is_highest=is_highest, is_lowest=is_lowest)}\n")
        elif item.media_type == "photo":
            stream.write(f"  Original URL: {item.original_url}\n")
    stream.write("\n")
    stream.flush()


def run(args: argparse.Namespace) -> int:
    """Main CLI execution flow."""
    url = args.url
    if not url:
        if not sys.stdin.isatty():
            sys.stderr.write("Error: No Tweet URL provided.\n")
            return 1
        try:
            url = input("Enter Tweet URL: ").strip()
        except (KeyboardInterrupt, EOFError):
            sys.stdout.write("\n")
            return 130

    if not url:
        sys.stderr.write("Error: No Tweet URL entered.\n")
        return 1

    try:
        tweet_media = fetch_tweet_media(url)
    except (InvalidTweetURLError, TweetNotFoundError, NoMediaFoundError, ExtractionError) as e:
        sys.stderr.write(f"\nError: {e}\n")
        return 1
    except Exception as e:
        sys.stderr.write(f"\nUnexpected error: {e}\n")
        return 1

    if args.info:
        print_tweet_info(tweet_media)
        return 0

    if not args.quiet:
        sys.stdout.write(f"\nAuthor : {tweet_media.author_name} (@{tweet_media.author_screen_name})\n")
        text_preview = tweet_media.text.strip().replace("\n", " ")
        if len(text_preview) > 90:
            text_preview = text_preview[:87] + "..."
        sys.stdout.write(f"Post   : {text_preview}\n")
        sys.stdout.flush()

    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    downloaded_files: List[str] = []

    for item_idx, item in enumerate(tweet_media.media_items):
        if item.media_type in ("video", "gif"):
            if not item.variants:
                if not item.original_url:
                    sys.stderr.write(f"  Warning: No download URL found for item {item_idx + 1}.\n")
                    continue
                chosen_url = item.original_url
                res_label = "original"
            else:
                chosen_variant = prompt_resolution_selection(
                    item.variants,
                    auto_best=args.best,
                    auto_worst=args.worst,
                    target_resolution=args.resolution,
                )
                chosen_url = chosen_variant.url
                res_label = chosen_variant.resolution_label

            if args.filename and len(tweet_media.media_items) == 1:
                filename = args.filename
            else:
                filename = generate_filename(
                    author_screen_name=tweet_media.author_screen_name,
                    tweet_id=tweet_media.tweet_id,
                    media_type=item.media_type,
                    resolution=res_label,
                    index=item_idx,
                    ext="mp4",
                )

            dest_path = os.path.join(output_dir, filename)
            if not args.quiet:
                sys.stdout.write(f"\nDownloading video ({res_label}) to: {filename}\n")
                sys.stdout.flush()

            saved_path = download_file(chosen_url, dest_path, quiet=args.quiet)
            downloaded_files.append(saved_path)

        elif item.media_type == "photo":
            chosen_url = item.original_url
            if args.filename and len(tweet_media.media_items) == 1:
                filename = args.filename
            else:
                filename = generate_filename(
                    author_screen_name=tweet_media.author_screen_name,
                    tweet_id=tweet_media.tweet_id,
                    media_type="photo",
                    index=item_idx,
                    ext="jpg",
                )

            dest_path = os.path.join(output_dir, filename)
            if not args.quiet:
                sys.stdout.write(f"\nDownloading photo {item_idx + 1} to: {filename}\n")
                sys.stdout.flush()

            saved_path = download_file(chosen_url, dest_path, quiet=args.quiet)
            downloaded_files.append(saved_path)

    if not args.quiet and downloaded_files:
        sys.stdout.write("\nDone! Downloaded files:\n")
        for f in downloaded_files:
            file_size = os.path.getsize(f) if os.path.exists(f) else 0
            sys.stdout.write(f"  - {f} ({format_bytes(file_size)})\n")
        sys.stdout.flush()

    return 0


def main() -> None:
    """Entry point for the console script."""
    parser = create_parser()
    args = parser.parse_args()
    try:
        sys.exit(run(args))
    except KeyboardInterrupt:
        sys.stdout.write("\nInterrupted.\n")
        sys.exit(130)


if __name__ == "__main__":
    main()
