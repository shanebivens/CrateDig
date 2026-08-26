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
import json
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
PLAY_REASON = re.compile(
    r'"playabilityStatus":\{"status":"[A-Z_]+","reason":"([^"]{0,140})"')


def plays(url):
    """For a YouTube link, whether a signed out visitor can actually watch it.

    Fails open. YouTube treats datacenter addresses as bots and answers a CI
    runner with a sign-in challenge, so only an unambiguous refusal counts as
    dead. Turning away somebody's real submission is worse than letting a
    questionable one through, which check_links.py catches later anyway.

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
    if not found or found.group(1) == "OK":
        return True

    reason_match = PLAY_REASON.search(body)
    reason = (reason_match.group(1) if reason_match else "").lower()
    if "not a bot" in reason:
        return True                # the checker is being challenged, not the video
    return found.group(1) not in ("UNPLAYABLE", "ERROR", "LOGIN_REQUIRED")


NOISE = re.compile(
    r"\s*[\(\[][^)\]]*(official|video|audio|lyric|visuali[sz]er|hd|hq|4k|"
    r"remaster|full album|m/v|explicit|audio only)[^)\]]*[\)\]]",
    re.IGNORECASE,
)
TOPIC = re.compile(r"\s-\sTopic$")


def tidy(text):
    return re.sub(r"\s{2,}", " ", NOISE.sub("", text or "")).strip()


def oembed(link):
    """Ask the service what the track is. Returns (artist, title), either blank.

    The same read the form does in the browser, repeated here so a submission
    that arrives with only a link still comes out filled in. Bandcamp and the
    rest publish nothing, which is why either half can come back empty.
    """
    host = urllib.parse.urlparse(link).netloc.lower().split(":")[0]
    host = host[4:] if host.startswith("www.") else host

    if host in ("youtube.com", "music.youtube.com", "youtu.be"):
        endpoint = "https://www.youtube.com/oembed?format=json&url="
    elif host in ("open.spotify.com", "spotify.com"):
        endpoint = "https://open.spotify.com/oembed?url="
    elif host == "soundcloud.com":
        endpoint = "https://soundcloud.com/oembed?format=json&url="
    else:
        return "", ""

    try:
        request = urllib.request.Request(
            endpoint + urllib.parse.quote(link, safe=""),
            headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:                                          # noqa: BLE001
        return "", ""

    raw = str(data.get("title") or "")
    author = str(data.get("author_name") or "")

    if host == "soundcloud.com":
        head, sep, tail = raw.rpartition(" by ")
        return (tail.strip(), tidy(head)) if sep else ("", tidy(raw))
    if "spotify" in host:
        return "", tidy(raw)                    # Spotify names no artist
    if TOPIC.search(author):
        return TOPIC.sub("", author).strip(), tidy(raw)

    clean = tidy(raw)
    left, sep, right = clean.partition(" - ")
    if sep and left.strip() and right.strip():
        return left.strip(), right.strip()
    return author.strip(), clean


def canonical(url):
    """A shared YouTube link carries a share token and often somebody else's
    radio queue. Keep the video and drop the rest."""
    match = YOUTUBE_ID.search(url)
    return f"https://music.youtube.com/watch?v={match.group(1)}" if match else url


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

    # A link on its own is a complete submission. Fill in whatever was left out.
    looked_up = []
    if link and not (artist and title):
        found_artist, found_title = oembed(link)
        if found_artist and not artist:
            artist = clean(found_artist)
            looked_up.append("artist")
        if found_title and not title:
            title = clean(found_title)
            looked_up.append("title")

    if not artist or not title:
        return fail(
            "Could not work out what the track is from that link alone.",
            ["Add the **Artist** and **Track or album** by hand and it goes "
             "straight through.",
             "Bandcamp and some other sites publish nothing for this to read."],
        )

    link = canonical(link)

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

    note = ""
    if looked_up:
        note += ("\nThe " + " and ".join(looked_up) +
                 " came from the link. Say so on this issue if it got them wrong.")
    if not why:
        note += "\nNo writeup came with it, so one gets written before it goes out."
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
