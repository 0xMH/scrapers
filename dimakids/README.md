# DimaKids Downloader

Interactive downloader for dimakids.com that extracts and downloads M3U8 video streams.

## Features

- Interactive CLI with rich formatting
- Episode selection (single, ranges, or all)
- M3U8 stream extraction and download
- Progress bar with download speed
- Auto-retry on failed downloads
- Exports links to JSON for later use

## Installation

```bash
pip install requests beautifulsoup4 rich
```

## Usage

```bash
python3 dimakids-downloader.py
```

Then paste a URL from dimakids.com when prompted.

## Episode Selection

When prompted, you can enter:
- Single episodes: `1, 5, 10`
- Ranges: `1-10`
- Combined: `1, 3-5, 10, 15-20`
- All episodes: `all`

## Output

- Videos saved as `01.mp4`, `02.mp4`, etc. in a folder named after the show
- `links.json` file with all extracted M3U8 URLs

## Example

```
Paste a URL from dimakids.com (or 'q' to quit): https://dimakids.com/show/example

╭─────────── Show Title ───────────╮
│   Total Episodes Found: 26       │
╰──────────────────────────────────╯

Enter episode numbers to download (e.g., 1, 3-5, all): 1-5

Finding and resolving M3U8 links...
Processing episodes...

✓ Link data saved to: Show Title/links.json

Proceed with download? (y/n): y

Downloading 01.mp4: [##########----------] 50.0% | 2.5 MB/s
```
