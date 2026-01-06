#!/usr/bin/env python3
"""
StarDima Video URL Extractor
Usage: python3 stardima-extract.py <show_url> [output_format] [options]
Examples:
  python3 stardima-extract.py "https://watch.stardima.com/watch/tvshows/witch/" json
  python3 stardima-extract.py "https://www.stardima.com/tvshow/693fcadf20e3a/play/56876"
  python3 stardima-extract.py "https://www.stardima.com/tvshow/693fcadf20e3a/play/56876" --download
  python3 stardima-extract.py "https://www.stardima.com/tvshow/693fcadf20e3a/play/56876" -d -o ~/Videos
"""

import sys
import re
import json
import html
import base64
import urllib.parse
import argparse
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import yt_dlp

# Old watch.stardima.com endpoints
BASE_URL = "https://watch.stardima.com/watch"
AJAX_URL = f"{BASE_URL}/wp-admin/admin-ajax.php"
API_URL = f"{BASE_URL}/wp-json/wp/v2"

# New www.stardima.com endpoints
NEW_API_URL = "https://www.stardima.com/api"

# Server names - standard stardima order
SERVER_NAMES_STANDARD = ["vudeo", "uqload", "mailru", "goodstream", "vk"]
# Server names for hyperwatching-wrapped content
SERVER_NAMES_HYPERWATCHING = ["uqload", "streamhg", "darkibox", "goodstream", "other"]


def extract_slug(url):
    """Extract show slug from URL (handles multiple URL formats)"""
    # New www.stardima.com format: /tvshow/{show_id}/play/{episode_id}
    match = re.search(r'www\.stardima\.com/tvshow/([^/]+)(?:/play/(\d+))?', url)
    if match:
        return match.group(1), "new_stardima", match.group(2)

    # Old watch.stardima.com - tvshows URL
    match = re.search(r'/tvshows/([^/#?]+)', url)
    if match:
        return match.group(1), "tvshow", None

    # Old watch.stardima.com - episodes URL
    match = re.search(r'/episodes/([^/#?]+)', url)
    if match:
        episode_slug = match.group(1)
        # Remove SxE suffix (e.g., "-1x1", "-2x15")
        show_slug = re.sub(r'-\d+x\d+$', '', episode_slug)
        return show_slug, "episode", None

    return None, None, None


def get_new_stardima_show(show_id, ep_id=None):
    """Get show info from new www.stardima.com by scraping page"""
    try:
        # First try the show page
        url = f"https://www.stardima.com/tvshow/{show_id}"
        resp = requests.get(url, timeout=10)
        title = show_id
        season_matches = []

        if resp.status_code == 200:
            # Extract title from page
            title_match = re.search(r'<title>([^<]+)</title>', resp.text)
            title = title_match.group(1).split(' - ')[0].strip() if title_match else show_id

            # Try to find season IDs
            season_matches = re.findall(r'data-season-id=["\'](\d+)["\']', resp.text)
            season_matches += re.findall(r'/series/season/(\d+)', resp.text)

        # If no seasons found and we have an ep_id, try the play page
        if not season_matches and ep_id:
            play_url = f"https://www.stardima.com/tvshow/{show_id}/play/{ep_id}"
            play_resp = requests.get(play_url, timeout=10)
            if play_resp.status_code == 200:
                season_matches = re.findall(r'data-season-id=["\'](\d+)["\']', play_resp.text)
                season_matches += re.findall(r'/series/season/(\d+)', play_resp.text)
                # Extract title if not found before
                if title == show_id:
                    title_match = re.search(r'<title>([^<]+)</title>', play_resp.text)
                    if title_match:
                        title = title_match.group(1).split(' - ')[0].strip()

        return {
            "id": show_id,
            "title": title,
            "slug": show_id,
            "season_ids": list(set(season_matches))
        }
    except:
        pass
    return None


def get_new_stardima_seasons(show_id, page_html=None):
    """Extract season IDs from show page"""
    seasons = []
    try:
        if not page_html:
            url = f"https://www.stardima.com/tvshow/{show_id}"
            resp = requests.get(url, timeout=10)
            page_html = resp.text

        # Look for season data in various patterns
        season_matches = re.findall(r'data-season-id=["\'](\d+)["\']', page_html)
        season_matches += re.findall(r'/series/season/(\d+)', page_html)
        season_matches += re.findall(r'seasonId["\']?\s*:\s*["\']?(\d+)', page_html)

        seasons = list(set(season_matches))
    except:
        pass
    return seasons


def get_new_stardima_episodes(show_id, season_ids=None):
    """Get all episodes from new www.stardima.com using /series/season/{id} API"""
    episodes = []

    # First get season IDs if not provided
    if not season_ids:
        url = f"https://www.stardima.com/tvshow/{show_id}"
        resp = requests.get(url, timeout=10)
        season_ids = get_new_stardima_seasons(show_id, resp.text)

    for season_id in season_ids:
        try:
            resp = requests.get(
                f"https://www.stardima.com/series/season/{season_id}",
                headers={"X-Requested-With": "XMLHttpRequest"},
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                ep_list = data.get("episodes", [])
                for ep in ep_list:
                    episodes.append({
                        "id": ep.get("id"),
                        "season": ep.get("season_number", ep.get("season", 1)),
                        "number": ep.get("episode_number", ep.get("number", 1)),
                        "title": ep.get("title", ""),
                        "watch_url": ep.get("watch_url", "")
                    })
        except:
            pass

    return episodes


def fetch_new_episode(show_id, ep_id):
    """Fetch a single episode's video URL from new stardima using /series/episode/{id}"""
    try:
        resp = requests.get(
            f"https://www.stardima.com/series/episode/{ep_id}",
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            ep_data = data.get("episode", data)
            watch_url = ep_data.get("watch_url", "")
            season = ep_data.get("season_number", ep_data.get("season", 1))
            number = ep_data.get("episode_number", ep_data.get("number", 1))

            # Resolve hyperwatching if applicable
            if "hyperwatching.com/iframe/" in watch_url:
                resolved = resolve_hyperwatching(watch_url)
                return {
                    "episode": f"S{season}E{number}",
                    "post_id": ep_id,
                    "slug": f"{show_id}-{season}x{number}",
                    "servers": resolved,
                    "is_hyperwatching": True,
                    "raw_url": watch_url
                }
            elif watch_url:
                return {
                    "episode": f"S{season}E{number}",
                    "post_id": ep_id,
                    "slug": f"{show_id}-{season}x{number}",
                    "servers": {"direct": watch_url},
                    "is_hyperwatching": False,
                    "raw_url": watch_url
                }
    except Exception as e:
        pass
    return None


def get_show_info(slug, url_type="tvshow"):
    """Get show info from WordPress API"""
    # Try to get from tvshows endpoint
    resp = requests.get(f"{API_URL}/tvshows", params={"slug": slug})
    data = resp.json()
    if data:
        return {
            "id": data[0]["id"],
            "title": html.unescape(data[0]["title"]["rendered"]),
            "slug": slug
        }

    # If not found and came from episode URL, create synthetic show info
    if url_type == "episode":
        # Try to get title from first episode
        resp = requests.get(f"{API_URL}/episodes", params={"slug": f"{slug}-1x1"})
        data = resp.json()
        if data:
            # Extract show title from episode title (remove ": 1x1" suffix)
            ep_title = html.unescape(data[0]["title"]["rendered"])
            show_title = re.sub(r':\s*\d+[x×]\d+.*$', '', ep_title)
            return {
                "id": None,
                "title": show_title,
                "slug": slug
            }

    return None


def search_episodes(slug):
    """Search for all episodes of a show"""
    episodes = {}

    # Strategy 1: Search by slug variations
    search_terms = [slug, slug.replace("-", " ")]
    # Add common variations
    if "witch" in slug.lower():
        search_terms.extend(["w-i-t-c-h", "w.i.t.c.h", "الفتيات الخارقات"])

    for term in search_terms:
        try:
            resp = requests.get(f"{API_URL}/episodes", params={
                "search": term,
                "per_page": 100
            })
            data = resp.json()

            for ep in data:
                ep_slug = urllib.parse.unquote(ep.get("slug", ""))
                ep_slug_lower = ep_slug.lower()
                # Check if episode belongs to this show (flexible matching)
                if (slug in ep_slug_lower or
                    ep_slug_lower.startswith(slug) or
                    (slug == "witch" and "w-i-t-c-h" in ep_slug_lower)):
                    episodes[ep["id"]] = ep_slug
        except:
            pass

    # Strategy 2: Try SxE patterns (more thorough)
    for season in range(1, 6):
        consecutive_misses = 0
        for ep_num in range(1, 100):
            test_slug = f"{slug}-{season}x{ep_num}"
            try:
                resp = requests.get(f"{API_URL}/episodes", params={"slug": test_slug})
                data = resp.json()
                if data:
                    episodes[data[0]["id"]] = data[0]["slug"]
                    consecutive_misses = 0
                else:
                    consecutive_misses += 1
                    # Stop after 3 consecutive misses (likely end of season)
                    if consecutive_misses >= 3:
                        break
            except:
                consecutive_misses += 1
                if consecutive_misses >= 3:
                    break

    return episodes


def parse_episode_key(ep_id, slug):
    """Parse season and episode number from slug"""
    # Check for SxE format
    match = re.search(r'(\d+)x(\d+)', slug)
    if match:
        return f"S{match.group(1)}E{match.group(2)}"

    # Check for Arabic episode format
    if "الحلق" in slug or "%d8%a7%d9%84%d8%ad%d9%84%d9%82" in slug.lower():
        num_match = re.search(r'(\d+)$', slug)
        if num_match:
            return f"S1E{num_match.group(1)}"
        return "S1E1"

    return f"E{ep_id}"


def resolve_hyperwatching(iframe_url):
    """Resolve hyperwatching.com iframe to actual video URLs"""
    try:
        # Extract video ID from URL
        video_id = iframe_url.split("/iframe/")[-1].split("/")[0].split("?")[0]

        # Fetch iframe page to get CSRF token and servers
        resp = requests.get(iframe_url, timeout=10)
        html_content = resp.text

        # Extract CSRF token
        csrf_match = re.search(r'csrf:\s*["\']([^"\']+)["\']', html_content)
        csrf_token = csrf_match.group(1) if csrf_match else ""

        # Extract servers
        servers_match = re.search(r'servers:\s*\[(.*?)\]', html_content, re.DOTALL)
        if not servers_match:
            return {"hyperwatching": iframe_url}

        servers_text = servers_match.group(1)
        server_ids = re.findall(r'id:\s*["\'](\d+)["\']', servers_text)
        server_names = re.findall(r'name:\s*["\']([^"\']+)["\']', servers_text)

        results = {}
        api_url = f"https://hyperwatching.com/api/videos/{video_id}/link"

        for sid, sname in zip(server_ids, server_names):
            try:
                link_resp = requests.post(api_url,
                    headers={
                        "Referer": iframe_url,
                        "X-Requested-With": "XMLHttpRequest",
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "X-CSRF-TOKEN": csrf_token
                    },
                    json={"server_link_id": sid},
                    timeout=10
                )
                link_data = link_resp.json()
                if link_data.get("success") and link_data.get("watch_url"):
                    results[sname.lower()] = link_data["watch_url"]
            except:
                pass

        return results if results else {"hyperwatching": iframe_url}
    except:
        return {"hyperwatching": iframe_url}


def get_video_urls(ep_id):
    """Get video URLs for a single episode. Returns (servers_list, is_hyperwatching)"""
    servers = []
    hyperwatching_url = None

    for server_num in range(1, 6):
        try:
            resp = requests.post(AJAX_URL, data={
                "action": "doo_player_ajax",
                "post": ep_id,
                "nume": server_num,
                "type": "tv"
            }, timeout=10)

            data = resp.json()
            embed_b64 = data.get("embed_url", "")

            if embed_b64:
                decoded = base64.b64decode(embed_b64).decode('utf-8')
                # Extract actual URL from strema wrapper
                if "url=" in decoded:
                    actual_url = decoded.split("url=")[-1]
                else:
                    actual_url = decoded

                # Check if it's a hyperwatching.com URL
                if "hyperwatching.com/iframe/" in actual_url:
                    hyperwatching_url = actual_url
                    servers.append(None)  # Will resolve later
                else:
                    servers.append(actual_url)
            else:
                servers.append(None)
        except:
            servers.append(None)

    # If we got a hyperwatching URL, resolve it to get actual servers
    if hyperwatching_url and all(s is None for s in servers):
        resolved = resolve_hyperwatching(hyperwatching_url)
        # Map resolved servers to hyperwatching names
        servers = [
            resolved.get("uqload"),
            resolved.get("earnvids") or resolved.get("streamhg"),
            resolved.get("darkibox"),
            resolved.get("goodstream"),
            resolved.get("hyperwatching")  # Fallback
        ]
        return servers, True  # is_hyperwatching = True

    return servers, False  # is_hyperwatching = False


def fetch_episode(ep_id, slug):
    """Fetch a single episode's data"""
    ep_key = parse_episode_key(ep_id, slug)
    servers, is_hyperwatching = get_video_urls(ep_id)
    server_names = SERVER_NAMES_HYPERWATCHING if is_hyperwatching else SERVER_NAMES_STANDARD
    return {
        "episode": ep_key,
        "post_id": ep_id,
        "slug": slug,
        "servers": dict(zip(server_names, servers)),
        "is_hyperwatching": is_hyperwatching
    }


def unwrap_video_url(url):
    """Unwrap video URL from wrapper services like strema.top"""
    # Handle strema.top/embed2/?id=<encoded_url>
    if "strema.top/embed" in url and "id=" in url:
        match = re.search(r'[?&]id=([^&]+)', url)
        if match:
            return urllib.parse.unquote(match.group(1))
    return url


def download_episode(episode_data, show_title, output_dir, preferred_servers=None, skip_servers=None):
    """Download a single episode using yt-dlp, trying servers until one succeeds"""
    ep_name = episode_data["episode"]
    servers = episode_data.get("servers", {})

    # Filter out None/empty URLs
    valid_urls = [(name, url) for name, url in servers.items() if url]

    # Apply server filters
    if skip_servers:
        skip_set = set(s.lower() for s in skip_servers)
        valid_urls = [(name, url) for name, url in valid_urls if name.lower() not in skip_set]

    # Sort by preferred servers
    if preferred_servers:
        pref_order = {s.lower(): i for i, s in enumerate(preferred_servers)}
        valid_urls.sort(key=lambda x: pref_order.get(x[0].lower(), 999))

    if not valid_urls:
        print(f"  \033[31m✗ {ep_name}: No valid URLs found\033[0m", file=sys.stderr)
        return False

    # Sanitize show title for filename
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', show_title)
    output_path = os.path.join(output_dir, safe_title)
    os.makedirs(output_path, exist_ok=True)
    output_template = os.path.join(output_path, f"{ep_name}.%(ext)s")

    for server_name, url in valid_urls:
        # Unwrap wrapper URLs
        actual_url = unwrap_video_url(url)

        # Extract domain for referer
        domain_match = re.match(r'(https?://[^/]+)', actual_url)
        referer = domain_match.group(1) + "/" if domain_match else ""

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [lambda d: None],  # Suppress progress
            'http_headers': {
                'Referer': referer,
                'Origin': referer.rstrip('/'),
            },
        }

        print(f"  \033[34m→ {ep_name}: Trying {server_name}...\033[0m", file=sys.stderr)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([actual_url])
            print(f"  \033[32m✓ {ep_name}: Downloaded successfully\033[0m", file=sys.stderr)
            return True
        except Exception as e:
            print(f"  \033[33m⚠ {ep_name}: Failed on {server_name} ({e})\033[0m", file=sys.stderr)

    print(f"  \033[31m✗ {ep_name}: All servers failed\033[0m", file=sys.stderr)
    return False


def process_new_stardima(show_id, ep_id, args):
    """Process new www.stardima.com URLs"""
    print(f"\033[34mExtracting from new stardima: \033[33m{show_id}\033[0m", file=sys.stderr)

    # Get show info from page
    print("\033[34m[1/4] Fetching show info...\033[0m", file=sys.stderr)

    show = get_new_stardima_show(show_id, ep_id)
    if not show:
        show = {"id": show_id, "title": show_id, "slug": show_id, "season_ids": []}

    print(f"  Show ID: \033[32m{show['id']}\033[0m", file=sys.stderr)
    print(f"  Title: \033[32m{show['title']}\033[0m", file=sys.stderr)
    if show.get("season_ids"):
        print(f"  Seasons: \033[32m{len(show['season_ids'])}\033[0m", file=sys.stderr)

    # Get episode list via season API
    print("\033[34m[2/4] Finding episodes...\033[0m", file=sys.stderr)

    episodes = get_new_stardima_episodes(show_id, show.get("season_ids"))

    # If no episodes found via season API, try single episode from URL
    if not episodes and ep_id:
        print("  No seasons found, trying single episode...", file=sys.stderr)
        episodes = [{"id": int(ep_id), "season": 1, "number": 1, "watch_url": ""}]

    print(f"  Found \033[32m{len(episodes)}\033[0m episodes", file=sys.stderr)

    if not episodes:
        print("Error: No episodes found", file=sys.stderr)
        sys.exit(1)

    # Fetch video URLs
    print("\033[34m[3/4] Extracting video URLs...\033[0m", file=sys.stderr)
    results = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(fetch_new_episode, show_id, ep["id"]): ep["id"]
            for ep in episodes
        }

        for i, future in enumerate(as_completed(futures)):
            ep_data = future.result()
            if ep_data:
                results.append(ep_data)
                print(f"\r  Processed: {ep_data['episode']} ({i+1}/{len(episodes)})    ",
                      end="", file=sys.stderr)
            else:
                print(f"\r  Failed: episode {i+1}/{len(episodes)}    ",
                      end="", file=sys.stderr)

    print("\n", file=sys.stderr)
    return show, results


def main():
    parser = argparse.ArgumentParser(description="StarDima Video URL Extractor")
    parser.add_argument("url", help="Show URL")
    parser.add_argument("format", nargs="?", default="table", choices=["table", "json", "csv"],
                       help="Output format (default: table)")
    parser.add_argument("--workers", "-w", type=int, default=10,
                       help="Number of parallel workers (default: 10)")
    parser.add_argument("--download", "-d", action="store_true",
                       help="Download episodes using yt-dlp (best quality)")
    parser.add_argument("--output-dir", "-o", type=str, default=".",
                       help="Output directory for downloads (default: current directory)")
    parser.add_argument("--parallel-downloads", "-p", type=int, default=3,
                       help="Number of parallel downloads (default: 3)")
    parser.add_argument("--prefer-servers", type=str,
                       help="Comma-separated list of servers to try first (e.g., krakenfiles,uqload)")
    parser.add_argument("--skip-servers", type=str,
                       help="Comma-separated list of servers to skip (e.g., lulustream,darkibox)")

    args = parser.parse_args()

    # Extract slug
    slug, url_type, ep_id = extract_slug(args.url)
    if not slug:
        print("Error: Could not extract show slug from URL", file=sys.stderr)
        print("Expected format:", file=sys.stderr)
        print("  https://www.stardima.com/tvshow/<id>/play/<ep_id>", file=sys.stderr)
        print("  https://watch.stardima.com/watch/tvshows/<slug>/", file=sys.stderr)
        print("  https://watch.stardima.com/watch/episodes/<slug>-1x1/", file=sys.stderr)
        sys.exit(1)

    # Handle new stardima.com format
    if url_type == "new_stardima":
        show, results = process_new_stardima(slug, ep_id, args)
    else:
        # Original watch.stardima.com logic
        print(f"\033[34mExtracting videos for: \033[33m{slug}\033[0m", file=sys.stderr)

        # Get show info
        print("\033[34m[1/4] Fetching show info...\033[0m", file=sys.stderr)
        show = get_show_info(slug, url_type)
        if not show:
            print("Error: Show not found", file=sys.stderr)
            sys.exit(1)

        print(f"  Show ID: \033[32m{show['id']}\033[0m", file=sys.stderr)
        print(f"  Title: \033[32m{show['title']}\033[0m", file=sys.stderr)

        # Search episodes
        print("\033[34m[2/4] Finding episodes...\033[0m", file=sys.stderr)
        episodes = search_episodes(slug)
        print(f"  Found \033[32m{len(episodes)}\033[0m episodes", file=sys.stderr)

        if not episodes:
            print("Error: No episodes found", file=sys.stderr)
            sys.exit(1)

        # Fetch video URLs in parallel
        print("\033[34m[3/4] Extracting video URLs...\033[0m", file=sys.stderr)
        results = []

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(fetch_episode, ep_id, slug): ep_id
                for ep_id, slug in episodes.items()
            }

            for i, future in enumerate(as_completed(futures)):
                ep_data = future.result()
                results.append(ep_data)
                print(f"\r  Processed: {ep_data['episode']} ({i+1}/{len(episodes)})    ",
                      end="", file=sys.stderr)

        print("\n", file=sys.stderr)

    # Sort results
    def sort_key(x):
        match = re.match(r'S(\d+)E(\d+)', x['episode'])
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return (999, x['post_id'])

    results.sort(key=sort_key)

    # Download if requested
    if args.download:
        preferred = args.prefer_servers.split(",") if args.prefer_servers else None
        skip = args.skip_servers.split(",") if args.skip_servers else None

        print(f"\033[34m[4/4] Downloading {len(results)} episodes ({args.parallel_downloads} parallel)...\033[0m", file=sys.stderr)
        if preferred:
            print(f"  Preferred servers: {', '.join(preferred)}", file=sys.stderr)
        if skip:
            print(f"  Skipping servers: {', '.join(skip)}", file=sys.stderr)
        print("", file=sys.stderr)

        success_count = 0

        with ThreadPoolExecutor(max_workers=args.parallel_downloads) as executor:
            futures = {
                executor.submit(download_episode, ep, show["title"], args.output_dir, preferred, skip): ep
                for ep in results
            }
            for future in as_completed(futures):
                if future.result():
                    success_count += 1

        print(f"\n\033[32mDownloaded {success_count}/{len(results)} episodes.\033[0m", file=sys.stderr)
        return

    # Output
    print("\033[34m[4/4] Generating output...\033[0m\n", file=sys.stderr)

    if args.format == "json":
        output = {
            "show": show,
            "episodes": results
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))

    elif args.format == "csv":
        # Determine header based on content type
        if results and results[0].get("is_hyperwatching"):
            print("Episode,PostID,Uqload,Streamhg,Darkibox,Goodstream,Other")
            for ep in results:
                servers = ep["servers"]
                print(f"{ep['episode']},{ep['post_id']},"
                      f"{servers.get('uqload', '')},"
                      f"{servers.get('streamhg', '')},"
                      f"{servers.get('darkibox', '')},"
                      f"{servers.get('goodstream', '')},"
                      f"{servers.get('other', '')}")
        else:
            print("Episode,PostID,Vudeo,Uqload,MailRu,Goodstream,VK")
            for ep in results:
                servers = ep["servers"]
                print(f"{ep['episode']},{ep['post_id']},"
                      f"{servers.get('vudeo', '')},"
                      f"{servers.get('uqload', '')},"
                      f"{servers.get('mailru', '')},"
                      f"{servers.get('goodstream', '')},"
                      f"{servers.get('vk', '')}")

    else:  # table
        print(f"\033[32m=== {show['title']} ===\033[0m")
        print(f"\033[32mShow ID: {show['id']} | Total Episodes: {len(results)}\033[0m\n")

        for ep in results:
            print(f"\033[33m{ep['episode']}\033[0m (ID: {ep['post_id']})")
            server_names = SERVER_NAMES_HYPERWATCHING if ep.get("is_hyperwatching") else SERVER_NAMES_STANDARD
            for i, name in enumerate(server_names):
                url = ep["servers"].get(name)
                if url:
                    print(f"  [{i+1}] {name.capitalize():12} {url}")
            print()

        print(f"\033[32mDone! Extracted {len(results)} episodes.\033[0m")


if __name__ == "__main__":
    main()
