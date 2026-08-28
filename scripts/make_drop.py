#!/usr/bin/env python3
"""Build a drop from the pool, never reusing a track.

Nothing that has appeared in any file in drops/ can be picked again. That is
checked two ways, by YouTube video id and by artist and title, so the same song
cannot slip back in through a different upload.

By default a drop is six tracks, one for each day through Saturday, with Sunday
left for bringing one back. Each is a starting point rather than a serving. Pass
--minutes to fill a runtime instead.

    python3 scripts/make_drop.py --date 2026-08-31
    python3 scripts/make_drop.py --date 2026-08-31 --minutes 30

Writes drops/<date>.yml and does nothing if that file already exists.
"""

import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kinds                                                    # noqa: E402

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required. Install it with: python3 -m pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
DROPS = ROOT / "drops"
SCHEDULED = ROOT / "scheduled"
POOL = ROOT / "data" / "pool.json"

PLACEHOLDER = "Pulled from the daily thirty minutes. No writeup yet."
YOUTUBE_ID_RE = re.compile(
    r"(?:(?:music\.|www\.)?youtube\.com/watch\?(?:[^#]*&)?v=|youtu\.be/|youtube\.com/embed/)"
    r"([A-Za-z0-9_-]{11})"
)


def track_key(artist, title):
    """Loose match, so a remaster or a reupload still counts as the same song."""
    text = f"{artist} {title}".lower()
    text = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", text)
    text = re.sub(r"\b(feat|ft|featuring|live|remaster(ed)?|version|edit|mix)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def drop_files():
    """Published drops and the ones waiting their turn. A track lined up for a
    future week is spent, otherwise seeding would hand it out twice."""
    return sorted(DROPS.glob("*.yml")) + sorted(SCHEDULED.glob("*.yml"))


def already_used():
    ids, keys = set(), set()
    for path in drop_files():
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
    for path in drop_files():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        try:
            highest = max(highest, int(data.get("number") or 0))
        except (TypeError, ValueError):
            continue
    return highest + 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--minutes", type=int, default=0,
                        help="fill roughly this many minutes instead of counting tracks")
    parser.add_argument("--count", type=int, default=0,
                        help="pick exactly this many tracks")
    parser.add_argument("--min-count", type=int, default=6)
    parser.add_argument("--max-count", type=int, default=6)
    parser.add_argument("--max-seconds", type=int, default=600,
                        help="skip anything longer. Concerts and mixes are not tracks")
    parser.add_argument("--reserve", type=int, default=0,
                        help="hold this many spots open for submitted picks")
    parser.add_argument("--max-tracks", type=int, default=12,
                        help="stop here however short the drop is")
    parser.add_argument("--out-dir", default=str(DROPS),
                        help="where to write it. scheduled/ holds future weeks")
    parser.add_argument("--publish-at", default="",
                        help="when this drop should become visible")
    args = parser.parse_args()

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
        sys.exit("--date must look like 2026-08-27")

    out_dir = Path(args.out_dir)
    path = out_dir / f"{args.date}.yml"
    for existing in (DROPS / f"{args.date}.yml", SCHEDULED / f"{args.date}.yml"):
        if existing.exists():
            print(f"{existing.relative_to(ROOT)} already exists. Nothing to do.")
            return 0

    if not POOL.exists():
        print("No data/pool.json yet. Run scripts/pull_playlist.py first.")
        return 0

    pool = json.loads(POOL.read_text(encoding="utf-8")).get("tracks", [])
    used_ids, used_keys = already_used()

    def usable(track):
        # The API returns a title, a duration and a view count for videos nobody
        # can watch. playable comes from the page's own playabilityStatus.
        if track.get("playable") is False:
            return False
        if track.get("video_id") in used_ids:
            return False
        if track_key(track.get("artist", ""), track.get("title", "")) in used_keys:
            return False
        seconds = track.get("seconds")
        # A half hour video is a concert, a mix or a full album, not a track.
        if isinstance(seconds, int) and seconds > args.max_seconds:
            return False
        return True

    oversize = len([t for t in pool if isinstance(t.get("seconds"), int)
                    and t["seconds"] > args.max_seconds])
    dead = len([t for t in pool if t.get("playable") is False])
    fresh = [track for track in pool if usable(track)]
    if oversize:
        print(f"{oversize} too long to be a track, skipped.")
    if dead:
        print(f"{dead} will not play for a signed out visitor, skipped.")

    print(f"{len(pool)} in the pool, {len(pool) - len(fresh)} already used, {len(fresh)} left.")
    if not fresh:
        print("The pool is exhausted. Add more playlists or more tracks.")
        return 0

    # Seeded on the date, so a rerun for the same day picks the same tracks.
    rng = random.Random(args.date)
    rng.shuffle(fresh)

    target = max(0, args.minutes) * 60 if args.minutes else 0
    if args.count:
        limit = args.count
    elif target:
        limit = args.max_tracks
    else:
        limit = rng.randint(min(args.min_count, args.max_count),
                            max(args.min_count, args.max_count))
    if args.reserve:
        limit = max(1, limit - args.reserve)

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
            "kind": kinds.guess(track.get("views")),
            "submitted_by": track.get("submitted_by", "curator"),
            "why": PLACEHOLDER,
            "links": {"youtube": track["url"]},
        })

    number = next_number()
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Pulled automatically. Set kind and write a real why before this lands.\n"
        + yaml.safe_dump(
            {
                "date": args.date,
                "number": number,
                "title": f"Drop {number:03d}",
                "publish_at": args.publish_at or None,
                "reserved": args.reserve or None,
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
    held = f", {args.reserve} spot(s) held open" if args.reserve else ""
    print(f"\nok. Wrote {path.relative_to(ROOT)} with {len(tracks)} track(s), "
          f"about {total // 60}m{total % 60:02d}s{held}.")
    for track in tracks:
        print(f"  {track['artist']} - {track['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
