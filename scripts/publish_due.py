#!/usr/bin/env python3
"""Move any scheduled week whose moment has come into drops/.

A week is due once 12:01pm Eastern on its Monday has passed. Eastern is worked
out properly, so this stays right across daylight saving without anyone editing
a cron line twice a year.

    python3 scripts/publish_due.py

Safe to run as often as you like. It publishes what is due and nothing else.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required. Install it with: python3 -m pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
SCHEDULED = ROOT / "scheduled"
DROPS = ROOT / "drops"
EASTERN = ZoneInfo("America/New_York")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", default="", help="override the clock, for testing")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    now = datetime.fromisoformat(args.now) if args.now else datetime.now(EASTERN)
    if now.tzinfo is None:
        now = now.replace(tzinfo=EASTERN)

    waiting = sorted(SCHEDULED.glob("*.yml"))
    if not waiting:
        print("Nothing lined up in scheduled/.")
        return 0

    published = 0
    for path in waiting:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        stamp = data.get("publish_at")
        if not stamp:
            print(f"{path.name} has no publish_at, leaving it alone.")
            continue
        try:
            due = datetime.fromisoformat(str(stamp))
        except ValueError:
            print(f"{path.name} has an unreadable publish_at, leaving it alone.")
            continue
        if due.tzinfo is None:
            due = due.replace(tzinfo=EASTERN)

        if due > now:
            print(f"{path.name} is not due yet ({due:%a %d %b, %I:%M%p %Z}).")
            continue

        target = DROPS / path.name
        if target.exists():
            print(f"{target.name} is already published, dropping the copy.")
            path.unlink()
            continue

        if args.dry_run:
            print(f"would publish {path.name}")
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        path.unlink()
        published += 1
        print(f"published {target.relative_to(ROOT)}")

    left = len(list(SCHEDULED.glob("*.yml")))
    print(f"\n{published} published, {left} week(s) still waiting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
