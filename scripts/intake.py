#!/usr/bin/env python3
"""Turn a submitted GitHub issue into a file in the repository.

The issue body is untrusted input from anyone on the internet, so every value
is length capped, every link is checked for an http(s) scheme, and the handle
comes from the GitHub login rather than anything the submitter typed.

Picks land in inbox/ and wait to be placed in a drop. One track at a time is
the only way in: a pick should be something a person chose on purpose and has
something to say about.

Usage:
    python scripts/intake.py --type track

Reads ISSUE_NUMBER, ISSUE_AUTHOR and ISSUE_BODY from the environment. Writes a
reply for the workflow to post at .intake-comment.md and exits non-zero if the
submission cannot be used.
"""

import argparse
import os
import re
import sys
import urllib.parse
import urllib.request
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
KINDS = {"obscure", "forgotten", "sideways"}

# Somewhere the track can actually be played or looked up. Keeps out search
# pages, shortener links and whatever someone copied out of a chat window.
MUSIC_HOSTS = (
    "youtube.com", "youtu.be", "open.spotify.com", "spotify.com",
    "bandcamp.com", "soundcloud.com", "music.apple.com", "itunes.apple.com",
    "tidal.com", "deezer.com", "discogs.com", "archive.org", "last.fm",
    "mixcloud.com", "audiomack.com", "hearthis.at", "jamendo.com",
)
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


YOUTUBE_ID = re.compile(
    r"(?:(?:music\.|www\.)?youtube\.com/watch\?(?:[^#\s]*&)?v=|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})"
)
PLAYABILITY = re.compile(r'"playabilityStatus":\{"status":"([A-Z_]+)"')


def plays(url):
    """For a YouTube link, whether a signed out visitor can actually watch it.

    Everything else is taken on trust, since only YouTube exposes this. See
    scripts/check_links.py for why the API and oembed are not good enough.
    """
    match = YOUTUBE_ID.search(url)
    if not match:
        return True
    request = urllib.request.Request(
        "https://www.youtube.com/watch?v=" + match.group(1),
        headers={"Accept-Language": "en-US,en;q=0.9",
                 "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body = response.read().decode("utf-8", "replace")
    except Exception:                                          # noqa: BLE001
        return True          # a network blip is not evidence the video is dead
    found = PLAYABILITY.search(body)
    return found.group(1) == "OK" if found else True


def music_host(url):
    """True when the link points somewhere the track can be played."""
    host = urllib.parse.urlparse(url).netloc.lower().split(":")[0]
    host = host[4:] if host.startswith("www.") else host
    return any(host == known or host.endswith("." + known) for known in MUSIC_HOSTS)


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
    why = clean(fields.get("Why this one"), "long")   # optional

    missing = [
        name for name, value in
        (("Artist", artist), ("Track or album", title))
        if not value
    ]
    if missing:
        return fail(
            "Some required fields came through empty.",
            [f"Fill in **{name}**." for name in missing],
        )

    raw_link = (fields.get("A link to the track") or "").strip()
    if not raw_link:
        return fail(
            "This one needs a link.",
            ["Paste a link to somewhere the track plays: YouTube, Spotify, "
             "Bandcamp, SoundCloud, Apple Music, Tidal, Discogs or Archive.org.",
             "The link is what people press, so it is the one thing that "
             "cannot be left out."],
        )

    kind = clean(fields.get("Which kind of find is this")).lower()
    if kind not in KINDS:
        kind = "obscure"

    year = clean(fields.get("Year"))
    match = re.search(r"(1[89]\d{2}|20\d{2})", year)
    year_value = int(match.group(1)) if match else None

    link = safe_link(raw_link)
    if not link:
        return fail(
            "That link did not look like a web address.",
            ["Paste the whole thing, starting with `https://`."],
        )
    if not music_host(link):
        return fail(
            "That link does not point at a music site.",
            ["Use YouTube, Spotify, Bandcamp, SoundCloud, Apple Music, Tidal, "
             "Discogs or Archive.org.",
             "A search page or a shortened link will not work, since the site "
             "needs the track itself to build the doorway."],
        )

    if not plays(link):
        return fail(
            "That video will not play for anyone who is not signed in.",
            ["It works for you because it is in your library. Signed out, "
             "YouTube returns it as unavailable.",
             "Try a different upload of the same track, or send a Bandcamp or "
             "Spotify link instead."],
        )

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

    if why and checked(fields.get("Disclosure")):
        why = why.rstrip() + " (Submitter has a stake in this record.)"
    elif checked(fields.get("Disclosure")):
        why = "Submitter has a stake in this record."

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

    note = "" if why else (
        "\nNo writeup came with it, so one gets written before it goes out."
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", default="track", choices=["track"])
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
            ["Use [Submit a track](https://github.com/shanebivens/CrateDig/issues/new?template=submission.yml)."],
        )

    return handle_track(fields, number, author)


if __name__ == "__main__":
    sys.exit(main())
