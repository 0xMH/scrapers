#!/bin/bash
# Arabic Toons Video Downloader

URL="$1"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

if [ -z "$URL" ]; then
  echo "Usage: ./download_toon.sh <url>"
  exit 1
fi

VIDEO_URL=$(curl -s "$URL" \
  -H "User-Agent: $UA" \
  -H "Referer: https://www.arabic-toons.com/" | grep -oP 'videoSrc\s*=\s*"\K[^"]+')

if [ -z "$VIDEO_URL" ]; then
  echo "Error: Could not find video URL"
  exit 1
fi

FILENAME=$(echo "$VIDEO_URL" | grep -oP '[^/]+\.mp4' | head -1)
echo "Downloading: $FILENAME"
wget --user-agent="$UA" --header="Referer: https://www.arabic-toons.com/" -O "$FILENAME" "$VIDEO_URL"
