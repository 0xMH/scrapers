# StarDima Video URL Extractor

Extracts video streaming URLs from StarDima for all episodes of a show.

## Features

- Supports both `www.stardima.com` and `watch.stardima.com` URLs
- Extracts multiple server sources (Uqload, Streamhg, Darkibox, etc.)
- Parallel fetching for faster extraction
- Multiple output formats (table, JSON, CSV)

## Installation

```bash
pip install requests
```

## Usage

```bash
# Basic usage - table output
python3 stardima-extract.py "https://www.stardima.com/tvshow/693fcadf20e3a/play/56876"

# JSON output
python3 stardima-extract.py "https://www.stardima.com/tvshow/693fcadf20e3a/play/56876" json

# CSV output
python3 stardima-extract.py "https://www.stardima.com/tvshow/693fcadf20e3a/play/56876" csv

# Old site format
python3 stardima-extract.py "https://watch.stardima.com/watch/tvshows/witch/" json
```

## Options

| Argument | Description |
|----------|-------------|
| `url` | Show or episode URL |
| `format` | Output format: `table` (default), `json`, `csv` |
| `-w, --workers` | Number of parallel workers (default: 10) |

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
