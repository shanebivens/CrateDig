#!/usr/bin/env python3
"""Line up future weeks in scheduled/, one file per Monday.

Each week gets six tracks from the pool, minus whatever is held open for
people to fill. Nothing is ever handed out twice: seeding checks published
drops and already-scheduled weeks together.

Files here do not reach the site. scripts/publish_due.py moves one into drops/
when its Monday arrives, so weeks appear one at a time.

    python3 scripts/seed_weeks.py --weeks 8

Seeding ahead means you can write the real story for a track days before anyone
sees it.
"""

import argparse
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SCHEDULED = ROOT / "scheduled"
EASTERN = ZoneInfo("America/New_York")
PUBLISH_HOUR, PUBLISH_MINUTE = 12, 1


def next_monday(start):
    """The first Monday strictly after start."""
    ahead = 7 - start.weekday() or 7
    return start + timedelta(days=ahead)


def publish_at(day):
    moment = datetime(day.year, day.month, day.day,
                      PUBLISH_HOUR, PUBLISH_MINUTE, tzinfo=EASTERN)
    return moment.isoformat()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weeks", type=int, default=8)
    parser.add_argument("--reserve", type=int, default=2,
                        help="spots per week held open for submitted picks")
    parser.add_argument("--start", default="", help="YYYY-MM-DD, defaults to today")
    parser.add_argument("--today", default="", help="override today, for testing")
    args = parser.parse_args()

    if args.start:
        cursor = date.fromisoformat(args.start)
        if cursor.weekday() != 0:
            cursor = next_monday(cursor)
    else:
        base = date.fromisoformat(args.today) if args.today \
            else datetime.now(EASTERN).date()
        cursor = next_monday(base)

    made = 0
    for _ in range(max(0, args.weeks)):
        day = cursor.isoformat()
        cursor += timedelta(days=7)

        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "make_drop.py"),
             "--date", day,
             "--reserve", str(args.reserve),
             "--out-dir", str(SCHEDULED),
             "--publish-at", publish_at(date.fromisoformat(day))],
            capture_output=True, text=True,
        )
        sys.stdout.write(result.stdout)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            return result.returncode
        if "The pool is exhausted" in result.stdout:
            print("Stopping here. Nothing left to line up.")
            break
        if "ok. Wrote" in result.stdout:
            made += 1

    waiting = len(list(SCHEDULED.glob("*.yml")))
    print(f"\nSeeded {made} week(s). {waiting} week(s) now waiting in scheduled/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
