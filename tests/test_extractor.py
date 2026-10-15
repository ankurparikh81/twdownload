"""Unit tests for extractor module."""

import unittest
from unittest.mock import patch

from twdownload.extractor import (
    ExtractionError,
    InvalidTweetURLError,
    NoMediaFoundError,
    TweetNotFoundError,
    _extract_dimensions_from_url,
    _parse_fxtwitter,
    _parse_syndication,
    extract_tweet_id,
    fetch_tweet_media,
)


class TestExtractor(unittest.TestCase):
    def test_extract_tweet_id_valid_urls(self):
        cases = [
            ("https://x.com/jaynitx/status/2109957970591412722?s=20", "2109957970591412722"),
            ("https://twitter.com/user/status/1234567890", "1234567890"),
            ("https://mobile.twitter.com/foo/status/9876543210/video/1", "9876543210"),
            ("https://x.com/i/status/1122334455", "1122334455"),
            ("http://x.com/someone/status/5555555555?param=1&other=2", "5555555555"),
            ("2109957970591412722", "2109957970591412722"),
            ("  123456789  ", "123456789"),
        ]
        for url, expected in cases:
            with self.subTest(url=url):
                self.assertEqual(extract_tweet_id(url), expected)

    def test_extract_tweet_id_invalid_urls(self):
        invalid_cases = [
            "",
            "   ",
            "https://google.com",
            "https://x.com/username",
            "https://x.com/user/status/notanid",
            "hello world",
        ]
        for url in invalid_cases:
            with self.subTest(url=url):
                with self.assertRaises(InvalidTweetURLError):
                    extract_tweet_id(url)

    def test_extract_dimensions_from_url(self):
        url = "https://video.twimg.com/amplify_video/123/vid/avc1/1280x720/sample.mp4?tag=16"
        self.assertEqual(_extract_dimensions_from_url(url), (1280, 720))

        url_no_avc = "https://video.twimg.com/ext_tw_video/123/pu/vid/640x360/sample.mp4"
        self.assertEqual(_extract_dimensions_from_url(url_no_avc), (640, 360))

        invalid_url = "https://example.com/video.mp4"
        self.assertEqual(_extract_dimensions_from_url(invalid_url), (0, 0))

    def test_parse_fxtwitter_video(self):
        sample_data = {
            "code": 200,
            "tweet": {
                "id": "12345",
                "author": {"name": "Test User", "screen_name": "testuser"},
                "text": "Check this video!",
                "media": {
                    "videos": [
                        {
                            "id": "vid1",
                            "url": "https://video.twimg.com/vid/avc1/1280x720/hi.mp4",
                            "duration": 60,
                            "formats": [
                                {
                                    "url": "https://video.twimg.com/vid/avc1/480x270/low.mp4",
                                    "bitrate": 288000,
                                    "width": 480,
                                    "height": 270,
                                    "container": "mp4",
                                },
                                {
                                    "url": "https://video.twimg.com/vid/avc1/1280x720/hi.mp4",
                                    "bitrate": 2176000,
                                    "width": 1280,
                                    "height": 720,
                                    "container": "mp4",
                                },
                                {
                                    "url": "https://video.twimg.com/pl/playlist.m3u8",
                                    "container": "m3u8",
                                },
                            ],
                        }
                    ]
                },
            },
        }

        media = _parse_fxtwitter(sample_data, "12345")
        self.assertEqual(media.tweet_id, "12345")
        self.assertEqual(media.author_name, "Test User")
        self.assertEqual(media.author_screen_name, "testuser")
        self.assertEqual(len(media.media_items), 1)

        item = media.media_items[0]
        self.assertEqual(item.media_type, "video")
        # Should filter out .m3u8 and sort descending by resolution
        self.assertEqual(len(item.variants), 2)
        self.assertEqual(item.variants[0].resolution_label, "1280x720")
        self.assertEqual(item.variants[1].resolution_label, "480x270")

    def test_parse_fxtwitter_photo(self):
        sample_data = {
            "code": 200,
            "tweet": {
                "id": "67890",
                "author": {"name": "Photo Poster", "screen_name": "photoposter"},
                "text": "Nice landscape",
                "media": {
                    "photos": [
                        {
                            "id": "photo1",
                            "url": "https://pbs.twimg.com/media/XYZ123?format=jpg&name=medium",
                            "altText": "Sunset over mountain",
                        }
                    ]
                },
            },
        }

        media = _parse_fxtwitter(sample_data, "67890")
        self.assertEqual(len(media.media_items), 1)
        item = media.media_items[0]
        self.assertEqual(item.media_type, "photo")
        self.assertTrue(item.original_url.endswith("?name=orig"))
        self.assertEqual(item.alt_text, "Sunset over mountain")

    def test_parse_fxtwitter_no_media(self):
        sample_data = {
            "code": 200,
            "tweet": {
                "id": "111",
                "author": {"name": "Text Only", "screen_name": "textonly"},
                "text": "Just text",
                "media": {},
            },
        }
        with self.assertRaises(NoMediaFoundError):
            _parse_fxtwitter(sample_data, "111")

    def test_parse_syndication_video(self):
        sample_data = {
            "id_str": "99999",
            "user": {"name": "Synd User", "screen_name": "synduser"},
            "text": "Syndicated tweet",
            "mediaDetails": [
                {
                    "type": "video",
                    "id_str": "media_99",
                    "media_url_https": "https://pbs.twimg.com/thumb.jpg",
                    "video_info": {
                        "duration_millis": 10000,
                        "variants": [
                            {
                                "bitrate": 500000,
                                "content_type": "video/mp4",
                                "url": "https://video.twimg.com/vid/avc1/640x360/vid.mp4",
                            },
                            {
                                "bitrate": 1500000,
                                "content_type": "video/mp4",
                                "url": "https://video.twimg.com/vid/avc1/1280x720/vid.mp4",
                            },
                            {
                                "content_type": "application/x-mpegURL",
                                "url": "https://video.twimg.com/pl/master.m3u8",
                            },
                        ],
                    },
                }
            ],
        }

        media = _parse_syndication(sample_data, "99999")
        self.assertEqual(len(media.media_items), 1)
        item = media.media_items[0]
        self.assertEqual(item.media_type, "video")
        self.assertEqual(len(item.variants), 2)
        self.assertEqual(item.variants[0].resolution_label, "1280x720")
        self.assertEqual(item.variants[1].resolution_label, "640x360")

    @patch("twdownload.extractor._http_get_json")
    def test_dual_engine_fallback_when_primary_fails(self, mock_get_json):
        # First call (FixTweet) fails with ExtractionError, second call (Syndication) succeeds
        mock_get_json.side_effect = [
            ExtractionError("FixTweet timeout"),
            {
                "id_str": "123",
                "user": {"name": "Fallback User", "screen_name": "fallback"},
                "text": "Fallback text",
                "mediaDetails": [
                    {
                        "type": "photo",
                        "id_str": "p1",
                        "media_url_https": "https://pbs.twimg.com/media/test.jpg",
                    }
                ],
            },
        ]

        media = fetch_tweet_media("123")
        self.assertEqual(media.author_screen_name, "fallback")
        self.assertEqual(len(media.media_items), 1)
        self.assertEqual(media.media_items[0].media_type, "photo")


if __name__ == "__main__":
    unittest.main()
