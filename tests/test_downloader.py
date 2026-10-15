"""Unit tests for downloader and helper formatting functions."""

import io
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from twdownload.downloader import (
    download_file,
    format_bytes,
    format_seconds,
    generate_filename,
    sanitize_filename,
)


class TestDownloader(unittest.TestCase):
    def test_format_bytes(self):
        self.assertEqual(format_bytes(500), "500 B")
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(1024 * 1024), "1.0 MB")
        self.assertEqual(format_bytes(int(2.5 * 1024 * 1024)), "2.5 MB")
        self.assertEqual(format_bytes(int(1.5 * 1024 * 1024 * 1024)), "1.50 GB")

    def test_format_seconds(self):
        self.assertEqual(format_seconds(45), "00:45")
        self.assertEqual(format_seconds(125), "02:05")
        self.assertEqual(format_seconds(3665), "01:01:05")
        self.assertEqual(format_seconds(-5), "--:--")

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename('bad:file/name?"test"'), "bad_file_name__test_")
        self.assertEqual(sanitize_filename("clean_filename.mp4"), "clean_filename.mp4")

    def test_generate_filename(self):
        fn_video = generate_filename("jaynitx", "2109957970591412722", "video", "1280x720")
        self.assertEqual(fn_video, "jaynitx_2109957970591412722_1280x720.mp4")

        fn_photo = generate_filename("jaynitx", "2109957970591412722", "photo", index=0, ext="jpg")
        self.assertEqual(fn_photo, "jaynitx_2109957970591412722_photo.jpg")

        fn_photo2 = generate_filename("jaynitx", "2109957970591412722", "photo", index=1, ext="jpg")
        self.assertEqual(fn_photo2, "jaynitx_2109957970591412722_photo2.jpg")

        fn_gif = generate_filename("user", "123", "gif")
        self.assertEqual(fn_gif, "user_123_gif.mp4")

    @patch("urllib.request.urlopen")
    def test_download_file_success(self, mock_urlopen):
        fake_content = b"Mock video file data content here"
        mock_response = MagicMock()
        mock_response.headers.get.return_value = str(len(fake_content))
        mock_response.read.side_effect = [fake_content, b""]
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_file = os.path.join(temp_dir, "test_video.mp4")
            stream = io.StringIO()
            result_path = download_file("https://example.com/video.mp4", dest_file, stream=stream)

            self.assertTrue(os.path.exists(result_path))
            with open(result_path, "rb") as f:
                self.assertEqual(f.read(), fake_content)
            # Ensure partial file was removed
            self.assertFalse(os.path.exists(f"{dest_file}.part"))

    @patch("urllib.request.urlopen")
    def test_download_file_cleans_up_on_failure(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.headers.get.return_value = "1000"
        mock_response.read.side_effect = Exception("Connection reset during download")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_file = os.path.join(temp_dir, "failed_video.mp4")
            stream = io.StringIO()
            with self.assertRaises(Exception):
                download_file("https://example.com/video.mp4", dest_file, stream=stream)

            # Ensure neither dest_file nor .part file remained
            self.assertFalse(os.path.exists(dest_file))
            self.assertFalse(os.path.exists(f"{dest_file}.part"))


if __name__ == "__main__":
    unittest.main()
