#!/usr/bin/env python3
"""Read participants' public YouTube playlists into data/pool.json.

Uses the official YouTube Data API v3 with a plain API key. Public playlist
data only: no OAuth, no listening history, no access to anyone's account.

Quota cost is tiny. playlistItems.list is 1 unit per page of 50, videos.list is
1 unit per batch of 50, against a free 10,000 units a day.

    YOUTUBE_API_KEY=... python3 scripts/pull_playlist.py
"""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required. Install it with: python3 -m pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
SUBMISSIONS = ROOT / "submissions"
POOL = ROOT / "data" / "pool.json"
API = "https://www.googleapis.com/youtube/v3/"

# Auto-generated YouTube Music uploads name the channel "Artist - Topic".
TOPIC_RE = re.compile(r"\s*-\s*Topic$")
NOISE_RE = re.compile(
    r"\s*[\(\[]\s*(official\s*(music\s*)?video|official\s*audio|lyric[s]?\s*video|"
    r"audio|visualizer|hd|hq|4k|remaster(ed)?(\s*\d{4})?)\s*[\)\]]",
    re.IGNORECASE,
)


def api_get(endpoint, params, key):
    params = dict(params, key=key)
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise SystemExit(f"YouTube API returned {exc.code} for {endpoint}: {detail}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach the YouTube API: {exc.reason}")


def playlist_id(url):
    query = urllib.parse.urlparse(url).query
    values = urllib.parse.parse_qs(query).get("list")
    return values[0] if values else ""


def clean_title(title):
    text = NOISE_RE.sub("", title or "").strip()
    return re.sub(r"\s{2,}", " ", text)


def split_artist(title, channel):
    """YouTube titles are inconsistent. Topic channels are the reliable case."""
    channel = (channel or "").strip()
    if TOPIC_RE.search(channel):
        return TOPIC_RE.sub("", channel).strip(), clean_title(title)

    text = clean_title(title)
    for separator in (" - ", " – ", " — "):
        if separator in text:
            left, right = text.split(separator, 1)
            if left.strip() and right.strip():
                return left.strip(), right.strip()
    return channel or "Unknown", text


def iso_duration_seconds(value):
    match = re.match(r"^P(?:\d+D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", value or "")
    if not match:
        return None
    hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def fetch_playlist(list_id, key):
    items = []
    page = None
    while True:
        params = {"part": "snippet", "playlistId": list_id, "maxResults": 50}
        if page:
            params["pageToken"] = page
        data = api_get("playlistItems", params, key)
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            resource = snippet.get("resourceId", {})
            if resource.get("kind") != "youtube#video":
                continue
            video_id = resource.get("videoId")
            title = snippet.get("title", "")
            if not video_id or title in ("Private video", "Deleted video"):
                continue
            items.append({
                "video_id": video_id,
                "raw_title": title,
                "channel": snippet.get("videoOwnerChannelTitle", ""),
                "position": snippet.get("position", len(items)),
            })
        page = data.get("nextPageToken")
        if not page:
            break
    return items


def fetch_details(video_ids, key):
    details = {}
    for start in range(0, len(video_ids), 50):
        batch = video_ids[start:start + 50]
        data = api_get(
            "videos",
            {"part": "contentDetails,statistics", "id": ",".join(batch)},
            key,
        )
        for item in data.get("items", []):
            stats = item.get("statistics", {})
            details[item["id"]] = {
                "seconds": iso_duration_seconds(
                    item.get("contentDetails", {}).get("duration")
                ),
                "views": int(stats["viewCount"]) if "viewCount" in stats else None,
            }
    return details


def main():
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        print(
            "YOUTUBE_API_KEY is not set, so there is nothing to pull.\n"
            "Create a key at console.cloud.google.com with the YouTube Data API v3\n"
            "enabled, then add it as the repository secret YOUTUBE_API_KEY."
        )
        return 0

    sources = []
    for path in sorted(SUBMISSIONS.glob("*.yml")):
        if path.name == "EXAMPLE.yml":
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        handle = data.get("handle") or path.stem
        # Only playlists deliberately marked for mining. A playlist that turns up
        # any other way is listed, never pulled from, because nobody signed up to
        # have a random track of theirs published under their name.
        if not data.get("pool"):
            continue
        for entry in data.get("playlists") or []:
            url = (entry or {}).get("url", "")
            list_id = playlist_id(url)
            if list_id and (entry or {}).get("service") in ("youtube-music", "youtube"):
                sources.append((handle, list_id))

    if not sources:
        print("No playlist in submissions/ is marked pool: true, so nothing to pull.")
        return 0

    tracks = {}
    for handle, list_id in sources:
        items = fetch_playlist(list_id, key)
        print(f"{handle}: {len(items)} track(s) from {list_id}")
        details = fetch_details([item["video_id"] for item in items], key)
        for item in items:
            video_id = item["video_id"]
            if video_id in tracks:
                continue
            artist, title = split_artist(item["raw_title"], item["channel"])
            extra = details.get(video_id, {})
            tracks[video_id] = {
                "video_id": video_id,
                "artist": artist,
                "title": title,
                "seconds": extra.get("seconds"),
                "views": extra.get("views"),
                "submitted_by": handle,
                "position": item["position"],
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }

    ordered = sorted(tracks.values(), key=lambda track: (track["submitted_by"], track["position"]))
    POOL.parent.mkdir(parents=True, exist_ok=True)
    POOL.write_text(
        json.dumps({"tracks": ordered}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nok. {len(ordered)} track(s) in the pool. Wrote {POOL.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
