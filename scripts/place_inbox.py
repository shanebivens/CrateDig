#!/usr/bin/env python3
"""Move submitted picks out of inbox/ and into the next scheduled drop.

Weeks are seeded with spots deliberately held open, so submitted picks usually
drop straight into a gap. If there is no gap, an untouched automatic pick gets
bumped to make room, and a bumped pick is not lost: it goes back to being
unused, so a later week can pick it up again.

The most recent submissions go first. Anything that does not fit stays in the
inbox for next week.

Submitted picks already carry the submitter's own kind and writeup, so they need
placing, not writing.

    python3 scripts/place_inbox.py
    python3 scripts/place_inbox.py --dry-run
"""

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required. Install it with: python3 -m pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "inbox"
SCHEDULED = ROOT / "scheduled"

PLACEHOLDER = "Pulled from the daily thirty minutes. No writeup yet."
MAX_TRACKS = 6
SLOTS = 2


def is_auto(track):
    """An untouched automatic pick, safe to bump for a real submission."""
    return (track.get("kind") == "unsorted"
            and (track.get("why") or "").strip() == PLACEHOLDER)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--slots", type=int, default=SLOTS,
                        help="how many to place this week. 0 means all of them")
    parser.add_argument("--oldest-first", action="store_true",
                        help="take the longest waiting rather than the newest")
    parser.add_argument("--max-tracks", type=int, default=MAX_TRACKS)
    args = parser.parse_args()

    # Files are named by issue number, so the highest is the newest.
    waiting = sorted(INBOX.glob("*.yml"), reverse=not args.oldest_first)
    if not waiting:
        print("Nothing waiting in inbox/.")
        return 0

    picks = waiting[:args.slots] if args.slots > 0 else waiting

    weeks = sorted(SCHEDULED.glob("*.yml"))
    if not weeks:
        print("No week lined up in scheduled/. Run scripts/seed_weeks.py first.")
        return 1

    # The first week with room, not blindly the first week. A full week of
    # hand-written tracks has nothing to bump, and overfilling breaks the
    # six-a-week shape.
    target = None
    for candidate in weeks:
        data = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
        if len(data.get("tracks") or []) < args.max_tracks:
            target = candidate
            drop = data
            break
    if target is None:
        print("Every scheduled week is full. Submissions keep for the next "
              "seeded week.")
        return 0
    tracks = drop.get("tracks") or []

    placed, skipped = [], []
    for path in picks:
        pick = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not pick.get("artist") or not pick.get("title"):
            skipped.append((path, "missing artist or title"))
            continue

        same = any(
            (t.get("artist", "").lower().strip() == pick["artist"].lower().strip()
             and t.get("title", "").lower().strip() == pick["title"].lower().strip())
            for t in tracks
        )
        if same:
            skipped.append((path, "already in this drop"))
            continue

        entry = {key: pick.get(key) for key in
                 ("artist", "title", "year", "duration", "kind",
                  "submitted_by", "why", "links")}
        entry["links"] = entry.get("links") or {}
        tracks.insert(len(placed), entry)
        placed.append((path, pick))

    # Trim back to size by dropping untouched automatic picks, newest first.
    bumped = 0
    while len(tracks) > args.max_tracks:
        removable = [i for i, t in enumerate(tracks) if is_auto(t)]
        if not removable:
            break
        tracks.pop(removable[-1])
        bumped += 1

    for path, pick in placed:
        print(f"placed  {pick['artist']} - {pick['title']}  (from {path.name})")
    for path, reason in skipped:
        print(f"skipped {path.name}: {reason}")
    if bumped:
        print(f"bumped  {bumped} automatic pick(s) back to the pool to make room")
    if len(tracks) > args.max_tracks:
        print(f"note    this drop now has {len(tracks)} tracks, over the usual "
              f"{args.max_tracks}. Nothing automatic was left to bump.")

    if args.dry_run:
        print("\nDry run, nothing written.")
        return 0

    if placed:
        drop["tracks"] = tracks
        header = ""
        existing = target.read_text(encoding="utf-8")
        if existing.startswith("#"):
            header = existing.split("\n", 1)[0] + "\n"
        target.write_text(
            header + yaml.safe_dump(drop, sort_keys=False, allow_unicode=True, width=88),
            encoding="utf-8")
        for path, _ in placed:
            path.unlink()

    left = len(list(INBOX.glob("*.yml")))
    print(f"\n{len(placed)} placed into {target.relative_to(ROOT)}, {left} still waiting.")
    if left and args.slots > 0:
        print(f"They keep for next week. Pass --slots 0 to place all of them now.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
