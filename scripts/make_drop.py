#!/usr/bin/env python3
"""Build a drop from the pool, never reusing a track.

Nothing that has appeared in any file in drops/ can be picked again. That is
checked two ways, by YouTube video id and by artist and title, so the same song
cannot slip back in through a different upload.

Picks fill a runtime rather than a track count, since the whole idea is thirty
minutes of music.

    python3 scripts/make_drop.py --date 2026-08-30 --minutes 30
    python3 scripts/make_drop.py --date 2026-08-30 --count 2

Writes drops/<date>.yml and does nothing if that file already exists.
"""

import argparse
import json
import random
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required. Install it with: python3 -m pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
DROPS = ROOT / "drops"
POOL = ROOT / "data" / "pool.json"

PLACEHOLDER = "Pulled from the daily thirty minutes. No writeup yet."
YOUTUBE_ID_RE = re.compile(
    r"(?:youtube\.com/watch\?(?:[^#]*&)?v=|youtu\.be/|youtube\.com/embed/)"
    r"([A-Za-z0-9_-]{11})"
)


def track_key(artist, title):
    """Loose match, so a remaster or a reupload still counts as the same song."""
    text = f"{artist} {title}".lower()
    text = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", text)
    text = re.sub(r"\b(feat|ft|featuring|live|remaster(ed)?|version|edit|mix)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def already_used():
    ids, keys = set(), set()
    for path in sorted(DROPS.glob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for track in data.get("tracks") or []:
            if not isinstance(track, dict):
                continue
            keys.add(track_key(track.get("artist", ""), track.get("title", "")))
            for url in (track.get("links") or {}).values():
                match = YOUTUBE_ID_RE.search(str(url))
                if match:
                    ids.add(match.group(1))
    return ids, keys


def next_number():
    highest = 0
    for path in sorted(DROPS.glob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        try:
            highest = max(highest, int(data.get("number") or 0))
        except (TypeError, ValueError):
            continue
    return highest + 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--minutes", type=int, default=30,
                        help="fill roughly this many minutes of runtime")
    parser.add_argument("--count", type=int, default=0,
                        help="pick exactly this many tracks instead of filling a runtime")
    parser.add_argument("--max-tracks", type=int, default=12,
                        help="stop here however short the drop is")
    args = parser.parse_args()

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
        sys.exit("--date must look like 2026-08-27")

    path = DROPS / f"{args.date}.yml"
    if path.exists():
        print(f"{path.relative_to(ROOT)} already exists. Nothing to do.")
        return 0

    if not POOL.exists():
        print("No data/pool.json yet. Run scripts/pull_playlist.py first.")
        return 0

    pool = json.loads(POOL.read_text(encoding="utf-8")).get("tracks", [])
    used_ids, used_keys = already_used()

    fresh = [
        track for track in pool
        if track.get("video_id") not in used_ids
        and track_key(track.get("artist", ""), track.get("title", "")) not in used_keys
    ]

    print(f"{len(pool)} in the pool, {len(pool) - len(fresh)} already used, {len(fresh)} left.")
    if not fresh:
        print("The pool is exhausted. Add more playlists or more tracks.")
        return 0

    # Seeded on the date, so a rerun for the same day picks the same tracks.
    random.Random(args.date).shuffle(fresh)

    target = 0 if args.count else max(0, args.minutes) * 60
    limit = args.count or args.max_tracks

    picked = []
    seen_here = set()
    running = 0
    for track in fresh:
        key = track_key(track.get("artist", ""), track.get("title", ""))
        if key in seen_here:
            continue
        # A missing duration is rare, since the API supplies them. Four minutes
        # is a fair guess so one gap cannot stretch a drop to twice its length.
        seconds = track.get("seconds")
        length = seconds if isinstance(seconds, int) and seconds > 0 else 240

        # Near the end, skip anything that would overshoot badly. One ten minute
        # outlier should not decide how long the whole drop runs.
        if target and running >= target * 0.7 and running + length > target + 300:
            continue

        seen_here.add(key)
        picked.append(track)
        running += length
        if len(picked) >= limit:
            break
        if target and running >= target:
            break

    tracks = []
    for track in picked:
        seconds = track.get("seconds")
        duration = None
        if isinstance(seconds, int) and seconds > 0:
            duration = f"{seconds // 60}:{seconds % 60:02d}"
        tracks.append({
            "artist": track.get("artist", "Unknown"),
            "title": track.get("title", ""),
            "year": None,
            "duration": duration,
            "kind": "unsorted",
            "submitted_by": track.get("submitted_by", "curator"),
            "why": PLACEHOLDER,
            "links": {"youtube": track["url"]},
        })

    number = next_number()
    path.write_text(
        "# Pulled automatically. Set kind and write a real why before this ages.\n"
        + yaml.safe_dump(
            {
                "date": args.date,
                "number": number,
                "title": f"Drop {number:03d}",
                "target_minutes": args.minutes if target else None,
                "blurb": "",
                "tracks": tracks,
            },
            sort_keys=False,
            allow_unicode=True,
            width=88,
        ),
        encoding="utf-8",
    )

    total = sum(t["seconds"] or 0 for t in picked if isinstance(t.get("seconds"), int))
    print(f"\nok. Wrote {path.relative_to(ROOT)} with {len(tracks)} track(s), "
          f"about {total // 60}m{total % 60:02d}s.")
    for track in tracks:
        print(f"  {track['artist']} - {track['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
