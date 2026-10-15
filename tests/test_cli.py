"""Unit and integration tests for CLI interface and UI prompts."""

import io
import unittest
from unittest.mock import MagicMock, patch

from twdownload.cli import create_parser, run
from twdownload.models import MediaItem, TweetMedia, VideoVariant
from twdownload.ui import prompt_resolution_selection


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.variants = [
            VideoVariant(
                url="https://video.twimg.com/vid/1280x720.mp4",
                width=1280,
                height=720,
                bitrate=2176000,
            ),
            VideoVariant(
                url="https://video.twimg.com/vid/640x360.mp4",
                width=640,
                height=360,
                bitrate=832000,
            ),
            VideoVariant(
                url="https://video.twimg.com/vid/480x270.mp4",
                width=480,
                height=270,
                bitrate=288000,
            ),
        ]

    def test_parser_defaults_and_flags(self):
        parser = create_parser()

        args = parser.parse_args(["https://x.com/user/status/123"])
        self.assertEqual(args.url, "https://x.com/user/status/123")
        self.assertEqual(args.output_dir, ".")
        self.assertFalse(args.best)
        self.assertFalse(args.worst)
        self.assertIsNone(args.resolution)
        self.assertFalse(args.info)

        args_custom = parser.parse_args([
            "https://x.com/user/status/123",
            "-o", "/tmp/videos",
            "-b",
            "-r", "720p",
            "-q",
        ])
        self.assertEqual(args_custom.output_dir, "/tmp/videos")
        self.assertTrue(args_custom.best)
        self.assertEqual(args_custom.resolution, "720p")
        self.assertTrue(args_custom.quiet)

    def test_ui_single_variant_bypasses_prompt(self):
        single = [self.variants[0]]
        stream = io.StringIO()
        selected = prompt_resolution_selection(single, stream=stream)
        self.assertEqual(selected, self.variants[0])
        self.assertIn("Only 1 resolution available", stream.getvalue())

    def test_ui_auto_best_flag(self):
        stream = io.StringIO()
        selected = prompt_resolution_selection(self.variants, auto_best=True, stream=stream)
        self.assertEqual(selected.resolution_label, "1280x720")
        self.assertIn("Auto-selected highest resolution", stream.getvalue())

    def test_ui_auto_worst_flag(self):
        stream = io.StringIO()
        selected = prompt_resolution_selection(self.variants, auto_worst=True, stream=stream)
        self.assertEqual(selected.resolution_label, "480x270")
        self.assertIn("Auto-selected lowest resolution", stream.getvalue())

    def test_ui_target_resolution_flag(self):
        stream = io.StringIO()
        selected = prompt_resolution_selection(self.variants, target_resolution="360p", stream=stream)
        self.assertEqual(selected.resolution_label, "640x360")
        self.assertIn("Matched requested resolution", stream.getvalue())

    @patch("builtins.input", return_value="2")
    def test_ui_interactive_numbered_choice(self, mock_input):
        stream = io.StringIO()
        selected = prompt_resolution_selection(self.variants, stream=stream)
        self.assertEqual(selected.resolution_label, "640x360")
        self.assertIn("[1] 1280x720", stream.getvalue())
        self.assertIn("[2] 640x360", stream.getvalue())
        self.assertIn("[3] 480x270", stream.getvalue())

    @patch("builtins.input", return_value="")
    def test_ui_interactive_default_on_enter(self, mock_input):
        stream = io.StringIO()
        selected = prompt_resolution_selection(self.variants, stream=stream)
        # Empty input should default to option 1 (highest quality)
        self.assertEqual(selected.resolution_label, "1280x720")

    @patch("twdownload.cli.fetch_tweet_media")
    def test_cli_info_flag(self, mock_fetch):
        mock_tweet = TweetMedia(
            tweet_id="12345",
            author_name="Alice",
            author_screen_name="alice",
            text="Hello world tweet",
            media_items=[
                MediaItem(
                    media_type="video",
                    id="v1",
                    original_url="https://video.twimg.com/vid.mp4",
                    variants=self.variants,
                )
            ],
        )
        mock_fetch.return_value = mock_tweet

        parser = create_parser()
        args = parser.parse_args(["https://x.com/alice/status/12345", "--info"])

        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            exit_code = run(args)
            self.assertEqual(exit_code, 0)
            output = mock_out.getvalue()
            self.assertIn("Tweet ID : 12345", output)
            self.assertIn("Author   : Alice (@alice)", output)
            self.assertIn("1280x720", output)

    @patch("twdownload.cli.download_file")
    @patch("twdownload.cli.fetch_tweet_media")
    def test_cli_download_flow(self, mock_fetch, mock_download):
        mock_tweet = TweetMedia(
            tweet_id="999",
            author_name="Bob",
            author_screen_name="bob",
            text="Video tweet",
            media_items=[
                MediaItem(
                    media_type="video",
                    id="v99",
                    original_url="https://video.twimg.com/vid.mp4",
                    variants=self.variants,
                )
            ],
        )
        mock_fetch.return_value = mock_tweet
        mock_download.return_value = "/tmp/bob_999_1280x720.mp4"

        parser = create_parser()
        args = parser.parse_args(["https://x.com/bob/status/999", "--best", "-q"])

        exit_code = run(args)
        self.assertEqual(exit_code, 0)
        mock_download.assert_called_once()
        call_url, call_dest = mock_download.call_args[0][:2]
        self.assertEqual(call_url, "https://video.twimg.com/vid/1280x720.mp4")
        self.assertTrue(call_dest.endswith("bob_999_1280x720.mp4"))


if __name__ == "__main__":
    unittest.main()
