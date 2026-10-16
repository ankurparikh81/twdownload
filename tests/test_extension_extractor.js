/**
 * Node.js test runner for extension/extractor.js
 */

const assert = require("assert");
const Extractor = require("../extension/extractor.js");

async function runTests() {
  console.log("Running extension extractor tests...");

  // 1. extractTweetId
  assert.strictEqual(
    Extractor.extractTweetId("https://x.com/jaynitx/status/2109957970591412722?s=20"),
    "2109957970591412722"
  );
  assert.strictEqual(
    Extractor.extractTweetId("https://twitter.com/user/status/1234567890"),
    "1234567890"
  );
  assert.strictEqual(
    Extractor.extractTweetId("https://x.com/i/status/9876543210"),
    "9876543210"
  );
  assert.strictEqual(
    Extractor.extractTweetId("2109957970591412722"),
    "2109957970591412722"
  );
  assert.throws(() => Extractor.extractTweetId("https://google.com"));
  assert.throws(() => Extractor.extractTweetId(""));

  // 2. extractDimensionsFromUrl
  assert.deepStrictEqual(
    Extractor.extractDimensionsFromUrl("https://video.twimg.com/vid/avc1/1280x720/abc.mp4"),
    { width: 1280, height: 720 }
  );
  assert.deepStrictEqual(
    Extractor.extractDimensionsFromUrl("https://video.twimg.com/vid/640x360/abc.mp4"),
    { width: 640, height: 360 }
  );

  // 3. formatBytes & formatBitrate
  assert.strictEqual(Extractor.formatBytes(1024 * 1024), "1.0 MB");
  assert.strictEqual(Extractor.formatBitrate(2176000), "~2.18 Mbps");
  assert.strictEqual(Extractor.formatBitrate(288000), "~288 kbps");

  // 4. generateFilename
  const fnVideo = Extractor.generateFilename("jaynitx", "2109957970591412722", "video", "1280x720");
  assert.strictEqual(fnVideo, "jaynitx_2109957970591412722_1280x720.mp4");

  const fnPhoto = Extractor.generateFilename("user", "123", "photo", null, "jpg", 0);
  assert.strictEqual(fnPhoto, "user_123_photo.jpg");

  // 5. parseFixTweet mock
  const mockFixTweetData = {
    code: 200,
    tweet: {
      id: "123",
      author: { name: "Tester", screen_name: "tester", avatar_url: "https://avatar.png" },
      text: "Test tweet content",
      media: {
        videos: [
          {
            id: "v1",
            duration: 10,
            thumbnail_url: "https://thumb.jpg",
            type: "video",
            formats: [
              { url: "https://video.twimg.com/vid/avc1/480x270/vid.mp4", width: 480, height: 270, bitrate: 288000 },
              { url: "https://video.twimg.com/vid/avc1/1280x720/vid.mp4", width: 1280, height: 720, bitrate: 2176000 },
              { url: "https://video.twimg.com/pl/master.m3u8", container: "m3u8" }
            ]
          }
        ]
      }
    }
  };

  const parsed = Extractor.parseFixTweet(mockFixTweetData, "123");
  assert.strictEqual(parsed.authorScreenName, "tester");
  assert.strictEqual(parsed.mediaItems.length, 1);
  const videoItem = parsed.mediaItems[0];
  assert.strictEqual(videoItem.type, "video");
  // Should filter out .m3u8 and sort descending (1280x720 first, 480x270 second)
  assert.strictEqual(videoItem.variants.length, 2);
  assert.strictEqual(videoItem.variants[0].resolutionLabel, "1280x720");
  assert.strictEqual(videoItem.variants[0].isHighest, true);
  assert.strictEqual(videoItem.variants[1].resolutionLabel, "480x270");
  assert.strictEqual(videoItem.variants[1].isLowest, true);

  console.log("All extension extractor unit tests passed successfully!");
}

runTests();
