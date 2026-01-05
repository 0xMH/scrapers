# Arabic Toons Downloader

Simple bash script to download videos from arabic-toons.com.

## Requirements

- `curl`
- `wget`
- `grep` with `-P` (Perl regex) support

## Usage

```bash
./download_toon.sh "https://www.arabic-toons.com/video/example"
```

## How it works

1. Fetches the page and extracts the `videoSrc` variable
2. Downloads the MP4 file using wget with proper headers
