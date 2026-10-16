/**
 * twdownload Chrome Extension Popup Script
 */

document.addEventListener("DOMContentLoaded", async () => {
  // DOM Elements
  const inputSection = document.getElementById("input-section");
  const tweetUrlInput = document.getElementById("tweet-url-input");
  const btnPaste = document.getElementById("btn-paste");
  const btnFetch = document.getElementById("btn-fetch");
  const btnToggleInput = document.getElementById("btn-toggle-input");

  const stateLoading = document.getElementById("state-loading");
  const stateError = document.getElementById("state-error");
  const stateIdle = document.getElementById("state-idle");
  const stateResult = document.getElementById("state-result");

  const loadingMsg = document.getElementById("loading-msg");
  const errorMsg = document.getElementById("error-msg");
  const btnRetry = document.getElementById("btn-retry");

  const authorAvatar = document.getElementById("author-avatar");
  const authorName = document.getElementById("author-name");
  const authorHandle = document.getElementById("author-handle");
  const tweetLink = document.getElementById("tweet-link");
  const tweetText = document.getElementById("tweet-text");

  const mediaTabsBar = document.getElementById("media-tabs-bar");
  const mediaPoster = document.getElementById("media-poster");
  const mediaTypeBadge = document.getElementById("media-type-badge");
  const mediaDurationBadge = document.getElementById("media-duration-badge");

  const resolutionSection = document.getElementById("resolution-section");
  const resolutionCount = document.getElementById("resolution-count");
  const resolutionOptions = document.getElementById("resolution-options");

  const btnDownload = document.getElementById("btn-download");
  const downloadBtnText = document.getElementById("download-btn-text");
  const downloadStatus = document.getElementById("download-status");
  const statusText = document.getElementById("status-text");

  // Application State
  let currentMediaData = null;
  let activeItemIndex = 0;
  let selectedVariantIndex = 0;

  function showPanel(panel) {
    stateLoading.classList.add("hidden");
    stateError.classList.add("hidden");
    stateIdle.classList.add("hidden");
    stateResult.classList.add("hidden");

    if (panel) {
      panel.classList.remove("hidden");
    }
  }

  function formatDuration(sec) {
    if (!sec || sec <= 0) return "";
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  }

  /**
   * Main function to fetch and display media for a Tweet URL or ID
   */
  async function loadTweet(urlOrId) {
    if (!urlOrId || !urlOrId.trim()) return;

    showPanel(stateLoading);
    loadingMsg.textContent = "Detecting media on X...";
    downloadStatus.classList.add("hidden");

    try {
      const data = await Extractor.fetchTweetMedia(urlOrId.trim());
      currentMediaData = data;
      activeItemIndex = 0;
      selectedVariantIndex = 0;
      renderResult(data);
    } catch (err) {
      showPanel(stateError);
      errorMsg.textContent = err.message || "Failed to extract media.";
    }
  }

  /**
   * Renders the parsed Tweet and Media in the popup UI
   */
  function renderResult(data) {
    showPanel(stateResult);

    // Author & Content
    authorAvatar.src = data.avatarUrl || "icons/icon48.png";
    authorName.textContent = data.authorName;
    authorHandle.textContent = `@${data.authorScreenName}`;
    tweetLink.href = `https://x.com/${data.authorScreenName}/status/${data.tweetId}`;
    tweetText.textContent = data.text || "(Media post)";

    // Multi-media tabs if more than 1 item
    renderTabs(data.mediaItems);

    // Render active media item
    renderActiveMediaItem();
  }

  function renderTabs(items) {
    mediaTabsBar.innerHTML = "";
    if (!items || items.length <= 1) {
      mediaTabsBar.classList.add("hidden");
      return;
    }

    mediaTabsBar.classList.remove("hidden");
    items.forEach((item, idx) => {
      const tabBtn = document.createElement("button");
      tabBtn.className = `media-tab-btn ${idx === activeItemIndex ? "active" : ""}`;
      const typeLabel = item.type.toUpperCase();
      tabBtn.textContent = `${typeLabel} ${idx + 1}`;
      tabBtn.addEventListener("click", () => {
        activeItemIndex = idx;
        selectedVariantIndex = 0;
        document.querySelectorAll(".media-tab-btn").forEach((b, bIdx) => {
          b.classList.toggle("active", bIdx === activeItemIndex);
        });
        renderActiveMediaItem();
      });
      mediaTabsBar.appendChild(tabBtn);
    });
  }

  function renderActiveMediaItem() {
    if (!currentMediaData || !currentMediaData.mediaItems.length) return;

    const item = currentMediaData.mediaItems[activeItemIndex];
    downloadStatus.classList.add("hidden");

    // Poster & Badges
    if (item.thumbnailUrl) {
      mediaPoster.src = item.thumbnailUrl;
      mediaPoster.style.display = "block";
    } else {
      mediaPoster.style.display = "none";
    }

    mediaTypeBadge.textContent = item.type.toUpperCase();

    if (item.durationSec && item.durationSec > 0) {
      mediaDurationBadge.textContent = formatDuration(item.durationSec);
      mediaDurationBadge.classList.remove("hidden");
    } else {
      mediaDurationBadge.classList.add("hidden");
    }

    // Video / GIF vs Photo handling
    if (item.type === "video" || item.type === "gif") {
      resolutionSection.classList.remove("hidden");
      renderResolutionMenu(item.variants);
      updateDownloadButton();
    } else {
      // Photo
      resolutionSection.classList.add("hidden");
      downloadBtnText.textContent = "Download Photo (Original)";
    }
  }

  function renderResolutionMenu(variants) {
    resolutionOptions.innerHTML = "";
    if (!variants || variants.length === 0) {
      resolutionSection.classList.add("hidden");
      return;
    }

    resolutionCount.textContent = `${variants.length} option${variants.length > 1 ? "s" : ""}`;

    variants.forEach((v, idx) => {
      const card = document.createElement("div");
      card.className = `res-option-card ${idx === selectedVariantIndex ? "selected" : ""}`;

      const bestTagHtml = v.isHighest ? '<span class="res-tag-best">BEST</span>' : "";
      const subInfo = [v.standardLabel, v.bitrateLabel, v.filesizeLabel].filter(Boolean).join(" • ");

      card.innerHTML = `
        <div class="res-left">
          <div class="res-radio">
            <div class="res-radio-inner"></div>
          </div>
          <div class="res-labels">
            <div class="res-title">
              <span>${v.resolutionLabel}</span>
              ${bestTagHtml}
            </div>
            <div class="res-sub">${subInfo}</div>
          </div>
        </div>
        <div class="res-right">${v.standardLabel}</div>
      `;

      card.addEventListener("click", () => {
        selectedVariantIndex = idx;
        document.querySelectorAll(".res-option-card").forEach((c, cIdx) => {
          c.classList.toggle("selected", cIdx === selectedVariantIndex);
        });
        updateDownloadButton();
      });

      resolutionOptions.appendChild(card);
    });
  }

  function updateDownloadButton() {
    const item = currentMediaData?.mediaItems[activeItemIndex];
    if (!item) return;

    if (item.type === "photo") {
      downloadBtnText.textContent = "Download Photo (Original)";
    } else {
      const variant = item.variants[selectedVariantIndex];
      const resName = variant ? variant.standardLabel : "Video";
      downloadBtnText.textContent = `Download Video (${resName})`;
    }
  }

  /**
   * Triggers file download via chrome.downloads API
   */
  async function triggerDownload() {
    if (!currentMediaData || !currentMediaData.mediaItems.length) return;

    const item = currentMediaData.mediaItems[activeItemIndex];
    let downloadUrl = "";
    let resolution = null;
    let ext = "mp4";

    if (item.type === "photo") {
      downloadUrl = item.url || item.thumbnailUrl;
      ext = "jpg";
    } else {
      const variant = item.variants[selectedVariantIndex] || item.variants[0];
      downloadUrl = variant.url;
      resolution = variant.resolutionLabel;
      ext = "mp4";
    }

    if (!downloadUrl) {
      alert("No download URL available for this item.");
      return;
    }

    const filename = Extractor.generateFilename(
      currentMediaData.authorScreenName,
      currentMediaData.tweetId,
      item.type,
      resolution,
      ext,
      activeItemIndex
    );

    btnDownload.classList.add("downloading");
    downloadBtnText.textContent = "Starting Download...";

    try {
      if (typeof chrome !== "undefined" && chrome.downloads && chrome.downloads.download) {
        chrome.downloads.download(
          {
            url: downloadUrl,
            filename: filename,
            saveAs: false,
          },
          (downloadId) => {
            btnDownload.classList.remove("downloading");
            updateDownloadButton();

            if (chrome.runtime.lastError) {
              downloadStatus.classList.remove("hidden");
              downloadStatus.style.color = "var(--danger-color)";
              statusText.textContent = `Error: ${chrome.runtime.lastError.message}`;
            } else {
              downloadStatus.classList.remove("hidden");
              downloadStatus.style.color = "var(--success-color)";
              statusText.textContent = `✓ Saved to Downloads: ${filename}`;
            }
          }
        );
      } else {
        // Fallback for non-extension environments (direct anchor download)
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = filename;
        a.target = "_blank";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        btnDownload.classList.remove("downloading");
        updateDownloadButton();
        downloadStatus.classList.remove("hidden");
        statusText.textContent = `✓ Download requested: ${filename}`;
      }
    } catch (err) {
      btnDownload.classList.remove("downloading");
      updateDownloadButton();
      downloadStatus.classList.remove("hidden");
      downloadStatus.style.color = "var(--danger-color)";
      statusText.textContent = `Error: ${err.message}`;
    }
  }

  // Event Listeners
  btnDownload.addEventListener("click", triggerDownload);

  btnFetch.addEventListener("click", () => {
    loadTweet(tweetUrlInput.value);
  });

  tweetUrlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      loadTweet(tweetUrlInput.value);
    }
  });

  btnPaste.addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        tweetUrlInput.value = text.trim();
        loadTweet(text.trim());
      }
    } catch (err) {
      tweetUrlInput.focus();
    }
  });

  btnRetry.addEventListener("click", () => {
    showPanel(stateIdle);
    inputSection.classList.remove("hidden");
    tweetUrlInput.focus();
  });

  btnToggleInput.addEventListener("click", () => {
    inputSection.classList.toggle("hidden");
    if (!inputSection.classList.contains("hidden")) {
      tweetUrlInput.focus();
    }
  });

  // Automatic Detection of Active Tab Tweet on Startup
  try {
    if (typeof chrome !== "undefined" && chrome.tabs && chrome.tabs.query) {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.url) {
        // If current URL is a tweet status link
        const statusMatch = tab.url.match(/(?:twitter\.com|x\.com)\/(?:[^/]+\/status\/|i\/status\/)(\d+)/i);
        if (statusMatch) {
          tweetUrlInput.value = tab.url;
          loadTweet(tab.url);
          return;
        }

        // If on x.com or twitter.com timeline/profile/search, attempt to detect tweet in viewport
        if (tab.url.includes("x.com") || tab.url.includes("twitter.com")) {
          showPanel(stateLoading);
          loadingMsg.textContent = "Scanning active tab for tweets...";

          try {
            const results = await chrome.scripting.executeScript({
              target: { tabId: tab.id },
              func: () => {
                // Check open modal or permalink overlay first
                const modalLink = document.querySelector('div[aria-labelledby="modal-header"] a[href*="/status/"]');
                if (modalLink) return modalLink.href;

                // Look for videos or tweets currently visible
                const videos = Array.from(document.querySelectorAll("video"));
                for (const vid of videos) {
                  const article = vid.closest('article[data-testid="tweet"]');
                  if (article) {
                    const link = article.querySelector('a[href*="/status/"]');
                    if (link) return link.href;
                  }
                }

                // Check first visible tweet article
                const firstTweet = document.querySelector('article[data-testid="tweet"] a[href*="/status/"]');
                if (firstTweet) return firstTweet.href;

                return null;
              },
            });

            if (results && results[0] && results[0].result) {
              const detectedUrl = results[0].result;
              tweetUrlInput.value = detectedUrl;
              loadTweet(detectedUrl);
              return;
            }
          } catch (scriptErr) {
            // Scripting error (e.g. restricted page)
          }
        }
      }
    }
  } catch (tabErr) {
    // Ignore and show idle
  }

  // Fallback to Idle
  showPanel(stateIdle);
});
