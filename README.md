# twdownload

A lightweight, robust command-line tool to download media (videos, photos, and animated GIFs) from posts on X (formerly Twitter).

When a video contains multiple resolutions, `twdownload` displays a numbered selection menu and lets you choose your desired quality, or automatically pick the best/worst stream with convenient CLI flags.

---

## Features

- **Multi-Resolution Video Selection:** Displays a clean numbered terminal menu showing resolution (`1280x720`, `640x360`, `480x270`), standard tag (`720p`, `360p`), approximate bitrate, and file size.
- **Dual-Engine Media Extractor:** Uses FixTweet API with automatic fallback to Twitter Syndication API. Requires **no API keys, tokens, or browser cookies**.
- **Real-Time Progress Bar:** Displays streaming download progress with percentage, downloaded/total size, transfer speed, and ETA.
- **Photos & GIFs Support:** Automatically downloads full-resolution (`orig`) photos and looping GIFs.
- **Zero External Dependencies Required:** Works out of the box using standard Python 3.8+ libraries (`urllib`, `argparse`, `json`). Also supports `requests`.
- **Scriptable & Pipe-Friendly:** Non-interactive shortcuts (`--best`, `--worst`, `-r 720p`) and graceful handling of piped inputs.

---

## Installation & Setup

### Option 1: Direct Usage (Zero Installation)

You can run `twdownload` immediately using your system Python 3:

```bash
./bin/twdownload "https://x.com/jaynitx/status/2109957970591412722?s=20"
```

Or invoke the module directly:

```bash
python3 -m twdownload.cli "https://x.com/jaynitx/status/2109957970591412722?s=20"
```

### Option 2: Install via Pip (Editable or Virtual Environment)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

After installation, the `twdownload` command will be directly available in your terminal:

```bash
twdownload "https://x.com/jaynitx/status/2109957970591412722?s=20"
```

---

## Usage Examples

### 1. Interactive Download with Resolution Menu

```bash
twdownload https://x.com/jaynitx/status/2109957970591412722?s=20
```

Output:
```text
Author : Jaynit (@jaynitx)
Post   : Marc Andreessen reveals why housing, health care, and education keep getting more expen...

Multiple resolutions available:
  [1] 1280x720   (720p, ~2.18 Mbps, ~44.9 MB) [Highest Quality]
  [2] 640x360    (360p, ~832 kbps, ~17.2 MB)
  [3] 480x270    (270p, ~288 kbps, ~5.9 MB) [Lowest Quality]
Select resolution [1-3] (default: 1): 1

Downloading video (1280x720) to: jaynitx_2109957970591412722_1280x720.mp4
[==============================] 100.0% (11.8 MB/11.8 MB) 28.5 MB/s in 00:00

Done! Downloaded files:
  - /Users/ankur/src/twdownload/jaynitx_2109957970591412722_1280x720.mp4 (11.8 MB)
```

*(Pressing Enter without typing a number automatically defaults to option `[1]` / Highest Quality).*

### 2. Auto-Select Highest Quality (`--best`)

```bash
twdownload https://x.com/jaynitx/status/2109957970591412722 --best
```

### 3. Auto-Select Lowest Quality (`--worst`)

```bash
twdownload https://x.com/jaynitx/status/2109957970591412722 --worst
```

### 4. Target a Specific Resolution (`-r` / `--resolution`)

```bash
twdownload https://x.com/jaynitx/status/2109957970591412722 -r 720p
# or
twdownload https://x.com/jaynitx/status/2109957970591412722 -r 1280x720
```

### 5. Inspect Post Media without Downloading (`--info`)

```bash
twdownload https://x.com/jaynitx/status/2109957970591412722 --info
```

Output:
```text
Tweet ID : 2109957970591412722
Author   : Jaynit (@jaynitx)
Content  : Marc Andreessen reveals why housing, health care, and education keep getting ...
Media    : 1 item(s)

  [Item 1] Type: VIDEO
  Available Resolutions (3):
    - 1280x720   (720p, ~2.18 Mbps, ~44.9 MB) [Highest Quality]
    - 640x360    (360p, ~832 kbps, ~17.2 MB)
    - 480x270    (270p, ~288 kbps, ~5.9 MB) [Lowest Quality]
```

### 6. Save to a Specific Directory (`-o` / `--output-dir`)

```bash
twdownload https://x.com/jaynitx/status/2109957970591412722 -o ~/Downloads
```

---

## CLI Options Reference

| Option | Flag | Description |
|---|---|---|
| `url` | (positional) | Tweet URL or status ID. If omitted, prompts interactively. |
| `--best` | `-b` | Automatically select the highest resolution (skips menu). |
| `--worst` | `-w` | Automatically select the lowest resolution (skips menu). |
| `--resolution` | `-r` | Target resolution by height (e.g. `720p`, `360p`) or dimensions (`1280x720`). |
| `--output-dir` | `-o` | Target directory for saved media (default: current directory `.`). |
| `--filename` | `-f` | Custom filename override (single media posts). |
| `--info` | | Display tweet metadata and available resolutions without downloading. |
| `--quiet` | `-q` | Suppress non-error output and progress bar. |
| `--version` | `-v` | Display `twdownload` version. |
| `--help` | `-h` | Show help and usage examples. |

---

## Running Automated Tests

Run the test suite with standard Python `unittest`:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```
