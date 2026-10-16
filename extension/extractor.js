/**
 * twdownload media extractor for Chrome extension.
 * Dual-engine extraction: FixTweet API + Twitter Syndication API fallback.
 */

const Extractor = {
  /**
   * Extracts the numeric Tweet status ID from a URL or raw ID string.
   */
  extractTweetId(input) {
    if (!input || typeof input !== "string") {
      throw new Error("No URL or ID provided.");
    }

    const trimmed = input.trim();
    if (/^\d+$/.test(trimmed)) {
      return trimmed;
    }

    const match = trimmed.match(/(?:twitter\.com|x\.com)\/(?:[^/]+\/status\/|i\/status\/)(\d+)/i);
    if (match && match[1]) {
      return match[1];
    }

    throw new Error(
      "Could not detect a valid Tweet URL. Please provide a link like 'https://x.com/user/status/1234567890'."
    );
  },

  /**
   * Parses width and height from video URLs like /vid/avc1/1280x720/.
   */
  extractDimensionsFromUrl(url) {
    if (!url) return { width: 0, height: 0 };
    const match = url.match(/\/vid\/(?:avc1\/)?(\d+)x(\d+)\//i);
    if (match) {
      return { width: parseInt(match[1], 10), height: parseInt(match[2], 10) };
    }
    return { width: 0, height: 0 };
  },

  /**
   * Formats bytes into human-readable string.
   */
  formatBytes(bytes) {
    if (!bytes || bytes <= 0) return "";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  },

  /**
   * Formats bitrate in bps to kbps or Mbps.
   */
  formatBitrate(bitrate) {
    if (!bitrate || bitrate <= 0) return "direct stream";
    if (bitrate >= 1000000) {
      return `~${(bitrate / 1000000).toFixed(2)} Mbps`;
    }
    return `~${Math.round(bitrate / 1000)} kbps`;
  },

  /**
   * Parses FixTweet API JSON response.
   */
  parseFixTweet(data, tweetId) {
    if (data.code !== 200 || !data.tweet) {
      throw new Error(`Tweet ${tweetId} not found.`);
    }

    const tweet = data.tweet;
    const author = tweet.author || {};
    const authorName = author.name || "Unknown";
    const authorScreenName = author.screen_name || "unknown";
    const avatarUrl = author.avatar_url || "";
    const text = tweet.text || "";

    const mediaData = tweet.media || {};
    const mediaItems = [];

    // 1. Videos & Animated GIFs
    let videoList = mediaData.videos || [];
    if (videoList.length === 0 && mediaData.all) {
      videoList = mediaData.all.filter((m) => m.type === "video" || m.type === "gif");
    }

    videoList.forEach((v, vIdx) => {
      const mediaId = v.id || `${tweetId}_vid_${vIdx}`;
      const durationSec = v.duration || 0;
      const thumbnailUrl = v.thumbnail_url || "";
      const isGif = v.type === "gif";

      const rawFormats = v.formats || v.variants || [];
      const variants = [];
      const seenRes = new Set();

      rawFormats.forEach((f) => {
        const fUrl = f.url || "";
        const container = (f.container || "").toLowerCase();
        const contentType = (f.content_type || "").toLowerCase();

        // Skip m3u8 playlists
        if (fUrl.includes(".m3u8") || container === "m3u8" || contentType.includes("mpegurl")) {
          return;
        }

        let width = f.width || 0;
        let height = f.height || 0;
        if (!width || !height) {
          const dims = this.extractDimensionsFromUrl(fUrl);
          width = width || dims.width;
          height = height || dims.height;
        }

        const bitrate = f.bitrate || 0;
        const resKey = width && height ? `${width}x${height}` : fUrl;

        if (!seenRes.has(resKey)) {
          seenRes.add(resKey);
          const filesize = bitrate > 0 && durationSec > 0 ? Math.round((bitrate / 8) * durationSec) : null;
          variants.push({
            url: fUrl,
            width,
            height,
            resolutionLabel: width && height ? `${width}x${height}` : "Original",
            standardLabel: height ? `${height}p` : "Video",
            bitrate,
            bitrateLabel: this.formatBitrate(bitrate),
            filesizeApprox: filesize,
            filesizeLabel: filesize ? `~${this.formatBytes(filesize)}` : "",
          });
        }
      });

      // Fallback if no mp4 variants parsed
      if (variants.length === 0 && v.url && !v.url.includes(".m3u8")) {
        const dims = this.extractDimensionsFromUrl(v.url);
        variants.push({
          url: v.url,
          width: dims.width,
          height: dims.height,
          resolutionLabel: dims.width && dims.height ? `${dims.width}x${dims.height}` : "Original",
          standardLabel: dims.height ? `${dims.height}p` : "Video",
          bitrate: 0,
          bitrateLabel: "direct stream",
          filesizeApprox: null,
          filesizeLabel: "",
        });
      }

      // Sort descending by resolution (area), then bitrate
      variants.sort((a, b) => b.width * b.height - a.width * a.height || b.bitrate - a.bitrate);

      if (variants.length > 0) {
        variants[0].isHighest = true;
        variants[variants.length - 1].isLowest = variants.length > 1;
      }

      mediaItems.push({
        type: isGif ? "gif" : "video",
        id: mediaId,
        thumbnailUrl,
        durationSec,
        variants,
      });
    });

    // 2. Photos
    let photoList = mediaData.photos || [];
    if (photoList.length === 0 && mediaData.all) {
      photoList = mediaData.all.filter((m) => m.type === "photo");
    }

    photoList.forEach((p, pIdx) => {
      const mediaId = p.id || `${tweetId}_photo_${pIdx}`;
      const rawUrl = p.url || "";
      let origUrl = rawUrl;
      if (rawUrl.includes("?")) {
        origUrl = `${rawUrl.split("?")[0]}?name=orig`;
      } else if (rawUrl) {
        origUrl = `${rawUrl}?name=orig`;
      }

      mediaItems.push({
        type: "photo",
        id: mediaId,
        url: origUrl,
        thumbnailUrl: origUrl,
        altText: p.altText || "",
        width: p.width || 0,
        height: p.height || 0,
      });
    });

    if (mediaItems.length === 0) {
      throw new Error(`Tweet ${tweetId} contains no downloadable video, image, or GIF.`);
    }

    return {
      tweetId,
      authorName,
      authorScreenName,
      avatarUrl,
      text,
      mediaItems,
    };
  },

  /**
   * Parses Twitter Syndication API JSON response.
   */
  parseSyndication(data, tweetId) {
    const user = data.user || {};
    const authorName = user.name || "Unknown";
    const authorScreenName = user.screen_name || "unknown";
    const avatarUrl = user.profile_image_url_https || "";
    const text = data.text || "";

    const mediaDetails = data.mediaDetails || [];
    if (!mediaDetails || mediaDetails.length === 0) {
      throw new Error(`Tweet ${tweetId} has no media attached.`);
    }

    const mediaItems = [];

    mediaDetails.forEach((m, mIdx) => {
      const mType = m.type || "video";
      const mediaId = m.id_str || `${tweetId}_media_${mIdx}`;
      const thumbUrl = m.media_url_https || "";

      if (mType === "video" || mType === "animated_gif") {
        const videoInfo = m.video_info || {};
        const durationSec = videoInfo.duration_millis ? videoInfo.duration_millis / 1000 : 0;
        const rawVariants = videoInfo.variants || [];

        const variants = [];
        const seenRes = new Set();

        rawVariants.forEach((v) => {
          const vUrl = v.url || "";
          const cType = (v.content_type || "").toLowerCase();
          if (cType !== "video/mp4" || vUrl.includes(".m3u8")) {
            return;
          }

          let dims = this.extractDimensionsFromUrl(vUrl);
          let width = dims.width;
          let height = dims.height;

          if (!width && m.original_info) {
            width = m.original_info.width || 0;
            height = m.original_info.height || 0;
          }

          const bitrate = v.bitrate || 0;
          const resKey = width && height ? `${width}x${height}` : vUrl;

          if (!seenRes.has(resKey)) {
            seenRes.add(resKey);
            const filesize = bitrate > 0 && durationSec > 0 ? Math.round((bitrate / 8) * durationSec) : null;
            variants.push({
              url: vUrl,
              width,
              height,
              resolutionLabel: width && height ? `${width}x${height}` : "Original",
              standardLabel: height ? `${height}p` : "Video",
              bitrate,
              bitrateLabel: this.formatBitrate(bitrate),
              filesizeApprox: filesize,
              filesizeLabel: filesize ? `~${this.formatBytes(filesize)}` : "",
            });
          }
        });

        variants.sort((a, b) => b.width * b.height - a.width * a.height || b.bitrate - a.bitrate);

        if (variants.length > 0) {
          variants[0].isHighest = true;
          variants[variants.length - 1].isLowest = variants.length > 1;
        }

        mediaItems.push({
          type: mType === "animated_gif" ? "gif" : "video",
          id: mediaId,
          thumbnailUrl: thumbUrl,
          durationSec,
          variants,
        });
      } else if (mType === "photo") {
        let photoUrl = m.media_url_https || "";
        if (photoUrl.includes("?")) {
          photoUrl = `${photoUrl.split("?")[0]}?name=orig`;
        } else if (photoUrl) {
          photoUrl = `${photoUrl}?name=orig`;
        }

        mediaItems.push({
          type: "photo",
          id: mediaId,
          url: photoUrl,
          thumbnailUrl: photoUrl,
          width: m.original_info?.width || 0,
          height: m.original_info?.height || 0,
        });
      }
    });

    if (mediaItems.length === 0) {
      throw new Error(`Tweet ${tweetId} contains no downloadable media.`);
    }

    return {
      tweetId,
      authorName,
      authorScreenName,
      avatarUrl,
      text,
      mediaItems,
    };
  },

  /**
   * Fetches tweet media metadata using dual-engine approach.
   */
  async fetchTweetMedia(tweetIdOrUrl) {
    const tweetId = this.extractTweetId(tweetIdOrUrl);
    const errors = [];

    // 1. Primary engine: FixTweet API
    try {
      const fxUrl = `https://api.fxtwitter.com/status/${tweetId}`;
      const resp = await fetch(fxUrl, {
        headers: { Accept: "application/json" },
      });
      if (resp.ok) {
        const data = await resp.json();
        return this.parseFixTweet(data, tweetId);
      }
      errors.push(`FixTweet HTTP ${resp.status}`);
    } catch (err) {
      errors.push(`FixTweet: ${err.message}`);
    }

    // 2. Fallback engine: Twitter Syndication API
    try {
      const syndUrl = `https://cdn.syndication.twimg.com/tweet-result?id=${tweetId}&token=x`;
      const resp = await fetch(syndUrl, {
        headers: { Accept: "application/json" },
      });
      if (resp.ok) {
        const data = await resp.json();
        return this.parseSyndication(data, tweetId);
      }
      errors.push(`Syndication HTTP ${resp.status}`);
    } catch (err) {
      errors.push(`Syndication: ${err.message}`);
    }

    throw new Error(
      `Could not extract media for Tweet #${tweetId}.\n${errors.join("; ")}`
    );
  },

  /**
   * Generates clean file name for media download.
   */
  generateFilename(authorScreenName, tweetId, mediaType, resolution = null, ext = "mp4", index = 0) {
    const prefix = authorScreenName && authorScreenName !== "unknown" ? authorScreenName : "tweet";
    const parts = [prefix, tweetId];

    if (mediaType === "photo") {
      parts.push(index > 0 ? `photo_${index + 1}` : "photo");
    } else if (mediaType === "gif") {
      parts.push("gif");
    } else if (resolution) {
      parts.push(resolution);
    }

    const base = parts.join("_").replace(/[\\/*?:"<>|]/g, "_");
    return `${base}.${ext}`;
  },
};

// Export for ES modules / browser global
if (typeof module !== "undefined" && module.exports) {
  module.exports = Extractor;
}
