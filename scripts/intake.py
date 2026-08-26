#!/usr/bin/env python3
"""Turn a submitted GitHub issue into a file in the repository.

The issue body is untrusted input from anyone on the internet, so every value
is length capped, every link is checked for an http(s) scheme, and the handle
comes from the GitHub login rather than anything the submitter typed.

Track picks land in inbox/ and wait for a curator to place them in a drop.
Playlists go straight into submissions/, since joining is self service.

Usage:
    python scripts/intake.py --type track
    python scripts/intake.py --type playlist

Reads ISSUE_NUMBER, ISSUE_AUTHOR and ISSUE_BODY from the environment. Writes a
reply for the workflow to post at .intake-comment.md and exits non-zero if the
submission cannot be used.
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required. Install it with: python3 -m pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "inbox"
SUBMISSIONS = ROOT / "submissions"
COMMENT = ROOT / ".intake-comment.md"

NO_RESPONSE = "_No response_"
KINDS = {"obscure", "forgotten"}
SERVICES = {
    "youtube-music", "youtube", "spotify", "apple-music",
    "bandcamp", "soundcloud", "tidal", "other",
}
LIMITS = {"short": 200, "long": 1200}
HANDLE_RE = re.compile(r"[^a-z0-9-]+")


def parse_issue_form(body):
    """GitHub renders an issue form as '### Label' followed by the value."""
    fields = {}
    label = None
    buffer = []
    for line in (body or "").replace("\r\n", "\n").split("\n"):
        if line.startswith("### "):
            if label is not None:
                fields[label] = "\n".join(buffer).strip()
            label = line[4:].strip()
            buffer = []
        elif label is not None:
            buffer.append(line)
    if label is not None:
        fields[label] = "\n".join(buffer).strip()

    for key, value in list(fields.items()):
        if value == NO_RESPONSE:
            fields[key] = ""
    return fields


def clean(value, limit="short"):
    text = re.sub(r"\s+", " ", (value or "")).strip()
    return text[:LIMITS[limit]]


def safe_link(value):
    """Only http(s) survives. Keeps javascript: and data: out of the site."""
    url = (value or "").strip().split()[0] if (value or "").strip() else ""
    if not url.lower().startswith(("http://", "https://")):
        return ""
    if len(url) > 500 or any(char in url for char in "<>\"'\\ "):
        return ""
    return url


def checked(value):
    return "[x]" in (value or "").lower()


def slugify(value):
    slug = HANDLE_RE.sub("-", (value or "").lower()).strip("-")
    return slug[:40] or "pick"


def write_comment(lines):
    COMMENT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fail(reason, fixes):
    write_comment(
        [f"Could not file this one yet. {reason}", ""]
        + [f"- {fix}" for fix in fixes]
        + ["", "Edit the issue and it gets picked up again automatically."]
    )
    print(f"intake failed: {reason}")
    return 1


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=88),
        encoding="utf-8",
    )


def handle_track(fields, number, author):
    artist = clean(fields.get("Artist"))
    title = clean(fields.get("Track or album"))
    why = clean(fields.get("Why this one"), "long")

    missing = [
        name for name, value in
        (("Artist", artist), ("Track or album", title), ("Why this one", why))
        if not value
    ]
    if missing:
        return fail(
            "Some required fields came through empty.",
            [f"Fill in **{name}**." for name in missing],
        )

    kind = clean(fields.get("Which kind of find is this")).lower()
    if kind not in KINDS:
        kind = "obscure"

    year = clean(fields.get("Year"))
    match = re.search(r"(1[89]\d{2}|20\d{2})", year)
    year_value = int(match.group(1)) if match else None

    link = safe_link(fields.get("A public link"))
    links = {}
    if link:
        service = "other"
        lowered = link.lower()
        if "music.youtube." in lowered:
            service = "youtube-music"
        elif "youtube.com" in lowered or "youtu.be" in lowered:
            service = "youtube"
        elif "spotify." in lowered:
            service = "spotify"
        elif "bandcamp." in lowered:
            service = "bandcamp"
        elif "soundcloud." in lowered:
            service = "soundcloud"
        elif "music.apple." in lowered:
            service = "apple-music"
        elif "archive.org" in lowered:
            service = "archive"
        links[service] = link

    if checked(fields.get("Disclosure")):
        why = why.rstrip() + " (Submitter has a stake in this record.)"

    path = INBOX / f"{number:05d}-{slugify(artist)}.yml"
    dump(path, {
        "artist": artist,
        "title": title,
        "year": year_value,
        "duration": None,
        "kind": kind,
        "submitted_by": HANDLE_RE.sub("-", author.lower()).strip("-")[:39],
        "why": why,
        "links": links,
        "source_issue": number,
    })

    note = "" if link else (
        "\nNo link came through, so the site will point at a search until one is added."
    )
    write_comment([
        f"Filed as `{path.relative_to(ROOT)}`.",
        "",
        f"**{artist}, {title}** is in the inbox as "
        f"{'an' if kind[0] in 'aeiou' else 'a'} *{kind}* pick and will be placed "
        "in an upcoming drop." + note,
        "",
        "Thanks for digging.",
    ])
    print(f"wrote {path.relative_to(ROOT)}")
    return 0


def handle_playlist(fields, number, author):
    url = safe_link(fields.get("Playlist link"))
    if not url:
        return fail(
            "That playlist link did not look like a usable web address.",
            ["Paste the full link, starting with `https://`.",
             "Make sure the playlist is public, not private or unlisted."],
        )

    service = clean(fields.get("Service")).lower()
    if service not in SERVICES:
        service = "other"

    handle = HANDLE_RE.sub("-", author.lower()).strip("-")[:39]
    if len(handle) < 2:
        return fail("Could not build a handle from that GitHub username.",
                    ["Open a pull request adding the file by hand instead."])

    path = SUBMISSIONS / f"{handle}.yml"
    if path.exists():
        existing = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    else:
        existing = {}

    playlists = existing.get("playlists") or []
    if any((entry or {}).get("url") == url for entry in playlists):
        write_comment([
            f"That playlist is already on `{path.relative_to(ROOT)}`, so nothing changed.",
            "",
            "Send a different link if you meant to add another one.",
        ])
        print("playlist already present")
        return 0

    playlists.append({
        "url": url,
        "service": service,
        "note": clean(fields.get("What is this playlist")),
    })

    bio = clean(fields.get("One line about what you dig for")) or existing.get("bio", "")
    dump(path, {
        "handle": handle,
        "joined": existing.get("joined") or os.environ.get("TODAY", ""),
        "bio": bio,
        "playlists": playlists,
    })

    write_comment([
        f"You are on the list. Added to `{path.relative_to(ROOT)}` as `{handle}`.",
        "",
        f"That is {len(playlists)} playlist(s) on your file. Your handle comes from "
        "your GitHub username, so nobody else can claim it.",
        "",
        "Picks pulled from your playlists will credit you when they land in a drop.",
    ])
    print(f"wrote {path.relative_to(ROOT)}")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=["track", "playlist"])
    args = parser.parse_args()

    try:
        number = int(os.environ.get("ISSUE_NUMBER", "0"))
    except ValueError:
        number = 0
    author = (os.environ.get("ISSUE_AUTHOR") or "").strip()
    body = os.environ.get("ISSUE_BODY", "")

    if not number or not author:
        return fail("The workflow did not receive the issue details.",
                    ["This one is on the maintainer, not you."])

    fields = parse_issue_form(body)
    if not fields:
        return fail(
            "This issue was not filed with one of the submission forms.",
            ["Use [Submit a track](https://github.com/shanebivens/CrateDig/issues/new?template=submission.yml)"
             " or [Add my playlist](https://github.com/shanebivens/CrateDig/issues/new?template=playlist.yml)."],
        )

    if args.type == "track":
        return handle_track(fields, number, author)
    return handle_playlist(fields, number, author)


if __name__ == "__main__":
    sys.exit(main())
