# StarDima Video URL Extractor

Extracts video streaming URLs from StarDima and optionally downloads episodes using yt-dlp.

## Features

- Supports both `www.stardima.com` and `watch.stardima.com` URLs
- Extracts multiple server sources (Krakenfiles, Lulustream, Uqload, etc.)
- Download episodes with yt-dlp (best quality)
- Parallel fetching and downloading
- Multiple output formats (table, JSON, CSV)
- Server prioritization and filtering

## Installation

```bash
uv sync
```

## Usage

```bash
# Basic usage - table output
uv run python stardima-extract.py "https://www.stardima.com/tvshow/693fcadf20e3a/play/56876"

# JSON output
uv run python stardima-extract.py "https://www.stardima.com/tvshow/693fcadf20e3a/play/56876" json

# CSV output
uv run python stardima-extract.py "https://www.stardima.com/tvshow/693fcadf20e3a/play/56876" csv

# Download all episodes
uv run python stardima-extract.py "https://www.stardima.com/tvshow/693fcadf20e3a/play/56876" -d

# Download to specific directory with preferred servers
uv run python stardima-extract.py "https://www.stardima.com/tvshow/693fcadf20e3a/play/56876" -d -o ~/Videos --prefer-servers krakenfiles,lulustream

# Skip unreliable servers
uv run python stardima-extract.py "https://www.stardima.com/tvshow/693fcadf20e3a/play/56876" -d --skip-servers uqload,darkibox
```

## Options

| Argument | Description |
|----------|-------------|
| `url` | Show or episode URL |
| `format` | Output format: `table` (default), `json`, `csv` |
| `-w, --workers` | Number of parallel workers for URL extraction (default: 10) |
| `-d, --download` | Download episodes using yt-dlp |
| `-o, --output-dir` | Output directory for downloads (default: current directory) |
| `-p, --parallel-downloads` | Number of parallel downloads (default: 3) |
| `--prefer-servers` | Comma-separated list of servers to try first |
| `--skip-servers` | Comma-separated list of servers to skip |

## Output Example

```
=== عالم الطباشير | ChalkZone ===
Show ID: 693fcadf20e3a | Total Episodes: 31

S1E1 (ID: 56876)
  [1] Uqload       https://uqload.bz/embed-hu6g6lsuiyl4.html
  [2] Streamhg     https://davioad.com/e/auelyxcugrrk
  [3] Darkibox     https://darkibox.com/embed-vd9ro65uay6p.html

S1E2 (ID: 56877)
  [1] Uqload       https://uqload.bz/embed-40rs94zhs2ks.html
  ...
```

## Supported URL Formats

- `https://www.stardima.com/tvshow/{show_id}/play/{episode_id}`
- `https://watch.stardima.com/watch/tvshows/{slug}/`
- `https://watch.stardima.com/watch/episodes/{slug}-1x1/`
