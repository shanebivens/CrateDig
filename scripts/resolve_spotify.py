#!/usr/bin/env python3
"""Find a Spotify link for tracks that do not have one.

Optional. Without SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET this does nothing
and says so, and the site falls back to a prefilled Spotify search, which is
never wrong and never needs a key.

Uses the client credentials flow, so it reads public catalogue data and never
touches anyone's account.

Matching is deliberately strict. A wrong link is worse than no link, so a track
is only accepted when the normalized title matches exactly and the artist lines
up. Anything doubtful is left alone.

    SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=... python3 scripts/resolve_spotify.py
"""

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required. Install it with: python3 -m pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = [ROOT / "drops", ROOT / "scheduled"]
TOKEN_URL = "https://accounts.spotify.com/api/token"
SEARCH_URL = "https://api.spotify.com/v1/search"

NOISE_RE = re.compile(
    r"\s*[\(\[][^)\]]*(official|video|audio|lyric|visualizer|remaster|"
    r"live from|live at|hd|hq|4k|feat|ft\.)[^)\]]*[\)\]]",
    re.IGNORECASE,
)


def normalize(value):
    text = NOISE_RE.sub(" ", value or "")
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return " ".join(text.split())


def get_token(client_id, client_secret):
    credentials = base64.b64encode(
        f"{client_id}:{client_secret}".encode()).decode()
    request = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
        headers={"Authorization": f"Basic {credentials}",
                 "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())["access_token"]
    except urllib.error.HTTPError as exc:
        sys.exit(f"Spotify refused the credentials ({exc.code}). "
                 "Check SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.")
    except urllib.error.URLError as exc:
        sys.exit(f"Could not reach Spotify: {exc.reason}")


def search(artist, title, token):
    query = f'track:"{normalize(title)}" artist:"{normalize(artist)}"'
    url = SEARCH_URL + "?" + urllib.parse.urlencode(
        {"q": query, "type": "track", "limit": 5})
    request = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            sys.exit("Spotify rate limited this run. Try again later.")
        return None
    except urllib.error.URLError:
        return None

    want_title, want_artist = normalize(title), normalize(artist)
    for item in data.get("tracks", {}).get("items", []):
        if normalize(item.get("name", "")) != want_title:
            continue
        for performer in item.get("artists", []):
            got = normalize(performer.get("name", ""))
            if got == want_artist or got in want_artist or want_artist in got:
                return item.get("external_urls", {}).get("spotify")
    return None


def main():
    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "").strip()
    if not (client_id and client_secret):
        print(
            "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are not set, so no links\n"
            "were looked up. The site falls back to a Spotify search, which needs\n"
            "no key. To turn this on, make an app at developer.spotify.com and add\n"
            "both values as repository secrets."
        )
        return 0

    token = get_token(client_id, client_secret)
    found = missed = 0

    for folder in FOLDERS:
        for path in sorted(folder.glob("*.yml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            tracks = data.get("tracks") or []
            changed = False

            for track in tracks:
                if not isinstance(track, dict):
                    continue
                links = track.get("links") or {}
                if links.get("spotify"):
                    continue
                url = search(track.get("artist", ""), track.get("title", ""), token)
                if url:
                    links["spotify"] = url
                    track["links"] = links
                    changed = True
                    found += 1
                    print(f"  found  {track['artist']} - {track['title']}")
                else:
                    missed += 1

            if changed:
                text = path.read_text(encoding="utf-8")
                header = text.split("\n", 1)[0] + "\n" if text.startswith("#") else ""
                path.write_text(
                    header + yaml.safe_dump(data, sort_keys=False,
                                            allow_unicode=True, width=88),
                    encoding="utf-8")

    print(f"\n{found} link(s) added, {missed} left to the search fallback.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
