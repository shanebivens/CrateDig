#!/usr/bin/env python3
"""Check that every track in a drop actually plays.

The YouTube API will happily return a title, a duration and a view count for a
video nobody can watch. So will oembed. The only honest test is the page's own
playabilityStatus, which is what a player reads before it starts.

    python3 scripts/check_links.py              # report
    python3 scripts/check_links.py --mark       # write playable: false onto the bad ones

A track that fails here is not a broken link, it is a dead video. Replace it.
"""

import argparse
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required. Install it with: python3 -m pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = [ROOT / "drops", ROOT / "scheduled"]

VIDEO_ID = re.compile(
    r"(?:(?:music\.|www\.)?youtube\.com/watch\?(?:[^#\s]*&)?v=|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})"
)
STATUS = re.compile(r'"playabilityStatus":\{"status":"([A-Z_]+)"')
REASON = re.compile(r'"playabilityStatus":\{"status":"[A-Z_]+","reason":"([^"]{0,120})"')


def playability(video_id):
    """OK, UNPLAYABLE, LOGIN_REQUIRED, ERROR, or a note about the request."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    request = urllib.request.Request(url, headers={
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36",
    })
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return f"HTTP {exc.code}", ""
    except Exception as exc:                                  # noqa: BLE001
        return f"unreachable ({exc})", ""

    found = STATUS.search(body)
    reason = REASON.search(body)
    return (found.group(1) if found else "no status"),\
           (reason.group(1) if reason else "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mark", action="store_true",
                        help="write playable: false onto tracks that fail")
    parser.add_argument("--pause", type=float, default=0.4)
    args = parser.parse_args()

    checked = ok = 0
    broken = []

    for folder in FOLDERS:
        for path in sorted(folder.glob("*.yml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            changed = False
            for track in data.get("tracks") or []:
                if not isinstance(track, dict):
                    continue
                video_id = ""
                for url in (track.get("links") or {}).values():
                    match = VIDEO_ID.search(str(url))
                    if match:
                        video_id = match.group(1)
                        break
                if not video_id:
                    continue

                checked += 1
                status, reason = playability(video_id)
                time.sleep(args.pause)

                if status == "OK":
                    ok += 1
                    if track.pop("playable", None) is not None:
                        changed = True
                    continue

                broken.append((path.stem, track.get("artist", "?"),
                               track.get("title", "?"), video_id, status, reason))
                print(f"  {status:<16} {video_id}  {track.get('artist')} - "
                      f"{str(track.get('title'))[:38]}  [{path.stem}]"
                      + (f"\n                   {reason}" if reason else ""))
                if args.mark:
                    track["playable"] = False
                    changed = True

            if changed and args.mark:
                text = path.read_text(encoding="utf-8")
                header = text.split("\n", 1)[0] + "\n" if text.startswith("#") else ""
                path.write_text(header + yaml.safe_dump(
                    data, sort_keys=False, allow_unicode=True, width=88),
                    encoding="utf-8")

    print(f"\n{ok} of {checked} play. {len(broken)} need replacing.")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
