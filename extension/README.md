# twdownload Chrome Extension

A Chrome Extension (Manifest V3) that allows you to download videos, GIFs, and photos from X (Twitter) directly from your browser toolbar, complete with resolution selection.

---

## How to Install in Google Chrome

1. Open Google Chrome.
2. In the address bar, navigate to:
   ```
   chrome://extensions/
   ```
3. Enable **Developer mode** using the toggle in the upper-right corner.
4. Click the **Load unpacked** button in the top-left corner.
5. In the file picker dialog, select the `extension` folder inside this repository:
   ```
   /Users/ankur/src/twdownload/extension
   ```
6. Click the Extensions puzzle piece icon (🧩) in Chrome's top toolbar, find **twdownload**, and click the **Pin** icon (📌) to keep it visible in your toolbar.

---

## How to Use

1. **Browse X / Twitter:** Navigate to any tweet containing video, photo, or GIF media (e.g., `https://x.com/jaynitx/status/2109957970591412722?s=20`).
2. **Click the twdownload icon** in your Chrome toolbar.
3. The popup will automatically detect the tweet and display:
   - Author profile and tweet snippet.
   - Media preview with length/type badges.
   - Available resolutions (e.g. `1280x720`, `640x360`, `480x270`) with bitrates and quality tags.
4. Select your preferred resolution (defaults to **Highest Quality**).
5. Click **Download Video** (or **Download Photo**). The file will be saved directly into your browser's Downloads folder!

### Downloading Any Tweet from Anywhere
You can also open the extension while on any page, click the link icon in the top header, paste any Tweet link, and click **Go** to fetch and download its media!
