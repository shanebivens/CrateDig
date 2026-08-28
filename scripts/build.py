#!/usr/bin/env python3
"""Validate submissions and drops, then build data/drops.json for the site.

Run it before opening a pull request:

    python3 -m pip install pyyaml
    python3 scripts/build.py

Exits non-zero if anything is wrong, so CI can gate on it.
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required. Install it with: python3 -m pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
SUBMISSIONS = ROOT / "submissions"
DROPS = ROOT / "drops"
OUT = ROOT / "data" / "drops.json"

TARGET_SECONDS = 30 * 60
KINDS = {"forgotten", "obscure", "sideways", "unsorted"}
PLACEHOLDER_WHY = "Pulled from the daily thirty minutes. No writeup yet."
SERVICES = {
    "youtube-music", "youtube", "spotify", "apple-music",
    "bandcamp", "soundcloud", "tidal", "other",
}
HANDLE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DURATION_RE = re.compile(r"^(?:(\d+):)?([0-5]?\d):([0-5]\d)$")
YOUTUBE_ID_RE = re.compile(
    r"(?:(?:music\.|www\.)?youtube\.com/watch\?(?:[^#]*&)?v=|youtu\.be/|youtube\.com/embed/)"
    r"([A-Za-z0-9_-]{11})"
)
# The point of a pick is where it leads. RDAMVM<id> is YouTube Music's song
# radio: a fifty track queue built out from the seed. These are mostly
# auto-generated audio uploads, so music.youtube.com is where they belong.
# youtube.com shows them as a still image, or as nothing at all.
RADIO_URL = "https://music.youtube.com/watch?v={id}&list=RDAMVM{id}"
TRACK_URL = "https://music.youtube.com/watch?v={id}"
# No key needed and never wrong, for anything resolve_spotify could not match.
SPOTIFY_SEARCH = "https://open.spotify.com/search/"

errors = []
warnings = []


def err(where, message):
    errors.append(f"{where}: {message}")


def warn(where, message):
    warnings.append(f"{where}: {message}")


def load_yaml(path):
    try:
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        err(path.name, f"could not be parsed as YAML ({exc})")
        return None


def parse_duration(value):
    """'4:12' or '1:02:33' to seconds. None stays None."""
    if value is None:
        return None
    match = DURATION_RE.match(str(value).strip())
    if not match:
        return False
    hours, minutes, seconds = match.groups()
    return int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds)


def check_url(where, url):
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        err(where, f"not a usable link: {url!r}")
        return False
    return True


def youtube_id(url):
    match = YOUTUBE_ID_RE.search(url or "")
    return match.group(1) if match else ""


def load_submissions():
    people = {}
    for path in sorted(SUBMISSIONS.glob("*.yml")):
        if path.name == "EXAMPLE.yml":
            continue
        data = load_yaml(path)
        if data is None:
            continue
        where = f"submissions/{path.name}"

        handle = data.get("handle")
        if not isinstance(handle, str) or not HANDLE_RE.match(handle):
            err(where, "handle must be lowercase letters, numbers and dashes")
            continue
        if handle != path.stem:
            err(where, f"handle '{handle}' does not match the filename")
            continue
        if handle in people:
            err(where, f"handle '{handle}' is already taken")
            continue

        joined = data.get("joined")
        if not DATE_RE.match(str(joined or "")):
            err(where, "joined must be a date like 2026-08-26")

        playlists = data.get("playlists") or []
        if not isinstance(playlists, list) or not playlists:
            err(where, "at least one playlist is required")
            playlists = []

        clean = []
        for index, entry in enumerate(playlists, start=1):
            spot = f"{where} playlist {index}"
            if not isinstance(entry, dict):
                err(spot, "should be a mapping with url and service")
                continue
            if not check_url(spot, entry.get("url")):
                continue
            service = entry.get("service", "other")
            if service not in SERVICES:
                warn(spot, f"unknown service '{service}'")
            clean.append({
                "url": entry["url"],
                "service": service,
                "note": entry.get("note", ""),
            })

        people[handle] = {
            "handle": handle,
            "joined": str(joined),
            "bio": data.get("bio", ""),
            "pool": bool(data.get("pool")),
            "playlists": clean,
        }
    return people


def load_drops(people):
    drops = []
    seen_tracks = {}
    for path in sorted(DROPS.glob("*.yml")):
        data = load_yaml(path)
        if data is None:
            continue
        where = f"drops/{path.name}"

        date = str(data.get("date", ""))
        if not DATE_RE.match(date):
            err(where, "date must look like 2026-08-26")
        if date != path.stem:
            warn(where, "filename does not match the date inside")

        try:
            target = int(data.get("target_minutes") or 0) * 60
        except (TypeError, ValueError):
            err(where, "target_minutes must be a whole number of minutes")
            target = 0

        tracks = data.get("tracks") or []
        if not isinstance(tracks, list) or not tracks:
            err(where, "a drop needs at least one track")
            continue

        per_person = {}
        clean_tracks = []
        total = 0
        unknown_durations = 0

        for index, track in enumerate(tracks, start=1):
            spot = f"{where} track {index}"
            if not isinstance(track, dict):
                err(spot, "should be a mapping")
                continue

            artist = track.get("artist")
            title = track.get("title")
            if not artist or not title:
                err(spot, "artist and title are both required")
                continue

            kind = track.get("kind")
            if kind not in KINDS:
                err(spot, f"kind must be one of {sorted(KINDS)}")
            elif kind == "unsorted":
                warn(spot, "still needs to be called forgotten or obscure")

            by = track.get("submitted_by", "curator")
            if by != "curator" and not HANDLE_RE.match(str(by)):
                err(spot, f"submitted_by '{by}' is not a usable handle")
            per_person[by] = per_person.get(by, 0) + 1

            why = (track.get("why") or "").strip()
            if not why:
                warn(spot, "no writeup yet, it is the part people read")
            elif why == PLACEHOLDER_WHY:
                warn(spot, "still needs a real writeup")
            elif len(why) > 600:
                warn(spot, "why is very long, two sentences usually lands better")

            seconds = parse_duration(track.get("duration"))
            if seconds is False:
                err(spot, f"duration {track.get('duration')!r} is not M:SS")
                seconds = None
            if seconds is None:
                unknown_durations += 1
            else:
                total += seconds

            key = f"{str(artist).lower().strip()} - {str(title).lower().strip()}"
            if key in seen_tracks:
                err(spot, f"already appeared in {seen_tracks[key]}")
            else:
                seen_tracks[key] = where

            links = track.get("links") or {}
            if not isinstance(links, dict):
                err(spot, "links should be a mapping of service to url")
                links = {}
            for service, url in list(links.items()):
                if not check_url(f"{spot} {service}", url):
                    links.pop(service)
            radio = ""
            for url in list(links.values()):
                found = youtube_id(url)
                if found and not radio:
                    radio = RADIO_URL.format(id=found)
                    # Point the plain link at YouTube Music too, since that is
                    # where an audio-only upload actually plays. youtube.com
                    # shows these as a still image or as nothing at all.
                    links.pop("youtube", None)
                    links["youtube-music"] = TRACK_URL.format(id=found)

            clean_tracks.append({
                "artist": artist,
                "title": title,
                "year": track.get("year"),
                "duration": track.get("duration"),
                "seconds": seconds,
                "kind": kind,
                "submitted_by": by,
                "pooled": bool(people.get(by, {}).get("pool")),
                "why": why,
                "links": links,
                "radio": radio,
                "spotify_search": SPOTIFY_SEARCH + quote(f"{artist} {title}"),
            })

        # The pool owner fills whatever submissions do not, so the variety cap
        # is about submitters crowding a drop, not about them.
        for who, count in per_person.items():
            if who in ("curator",) or people.get(who, {}).get("pool"):
                continue
            if count > 3:
                warn(where, f"{who} has {count} picks, three per drop keeps it varied")

        # A drop is not a playlist to sit through, so there is no play-it-all
        # link. Each track opens its own radio. Anything else has to be a real
        # playlist someone made by hand, so it comes from the drop file.
        made_playlists = {}
        for service, url in (data.get("playlists") or {}).items():
            if check_url(f"{where} playlist {service}", url):
                made_playlists[service] = url

        drops.append({
            "date": date,
            "number": data.get("number"),
            "title": data.get("title") or f"Drop {data.get('number', '')}".strip(),
            "blurb": (data.get("blurb") or "").strip(),
            "tracks": clean_tracks,
            "seconds": total,
            "unknown_durations": unknown_durations,
            "target_seconds": target,
            "playlists": made_playlists,
        })

        # Durations are not the point. The listener takes one track and the
        # radio decides how long it lasts, so nothing warns about timing.

    return drops


def main():
    people = load_submissions()
    drops = load_drops(people)
    drops.sort(key=lambda drop: drop["date"], reverse=True)

    for line in warnings:
        print(f"warning  {line}")
    for line in errors:
        print(f"ERROR    {line}")

    if errors:
        print(f"\n{len(errors)} problem(s) found. Nothing was written.")
        return 1

    # Everyone whose pick has actually gone out, most picks first.
    counts = {}
    for drop in drops:
        for track in drop["tracks"]:
            who = track.get("submitted_by")
            if who and who != "curator" and not track.get("pooled"):
                counts[who] = counts.get(who, 0) + 1
    contributors = [
        {"handle": handle, "picks": count}
        for handle, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    payload = {
        "drops": drops,
        "contributors": contributors,
        "target_seconds": TARGET_SECONDS,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    waiting = len([path for path in (ROOT / "inbox").glob("*.yml")])
    if waiting:
        print(f"\n{waiting} pick(s) waiting in inbox/ to be placed in a drop.")

    lined_up = len([path for path in (ROOT / "scheduled").glob("*.yml")])
    if lined_up:
        print(f"{lined_up} week(s) lined up in scheduled/, not yet published.")
    else:
        print("\nNothing lined up in scheduled/. Run scripts/seed_weeks.py.")

    total_tracks = sum(len(drop["tracks"]) for drop in drops)
    print(
        f"\nok. {len(drops)} drop(s), {total_tracks} track(s), "
        f"{len(contributors)} contributor(s). Wrote {OUT.relative_to(ROOT)}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
