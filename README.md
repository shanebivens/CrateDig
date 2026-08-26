# CrateDig

**30 Minutes of Rare Tracks.**

Every day, roughly thirty minutes of music you have never heard, or have not
heard in a very long time. That is the whole ritual. This repository collects
what people are finding and publishes a new drop from it.

The ask is not for great music. It is not even for music you personally like.
What genre, album, artist, or song do you think almost nobody has heard, or
nobody has played in years? Weird, mainstream, sideways, all of it counts.

One rule, carried over from the original post: do not judge people by what they
submit. Doing that misses the point of the experiment.

## Two kinds of find

Drops separate picks into two categories, because they are different pleasures.

- **Forgotten.** It was popular once and nobody plays it now. A regional hit, a
  band that broke up before the second record, something that fell out of
  rotation in 1979 and never came back.
- **Obscure.** It never surfaced in the first place. Private press, a cassette
  someone made for their friends, a record that sold two hundred copies.

A deep cut by a famous band is usually neither. If most people know the artist,
it probably belongs somewhere else.

## How to join

**[Fill in the form](https://shanebivens.github.io/CrateDig/submit.html).** Four
fields for a track, one for a playlist. It hands you a filled-out submission,
you press one button, and a bot files it into this repository and replies within
a minute. No git, no pull request, nothing to learn.

If you would rather do it by hand, copy `submissions/EXAMPLE.yml` to
`submissions/your-handle.yml` and open a pull request. Both routes end in the
same place.

You send public links, nothing else. Nothing here ever asks for a password, a
cookie, or access to your listening account, and it never will. If a future
version reads listening history, it will do it through something you control and
can revoke.

## How a submission becomes a drop

1. Someone submits through the form, which opens a prefilled issue.
2. The `Intake` workflow parses it, writes a file, replies on the issue, and
   closes it. Track picks land in `inbox/`. Playlists go straight into
   `submissions/`, since joining is self service. Your handle comes from your
   GitHub username, so nobody can claim someone else's.
3. A curator moves inbox picks into the current file in `drops/`.
4. Pushing that rebuilds `data/drops.json` and the site updates.

## The daily pull

A scheduled workflow builds a drop every day from participants' public
YouTube playlists, two tracks by default. It reads them through the official
YouTube Data API with a plain API key: public playlist data only, no OAuth and
no listening history.

**Nothing ever repeats.** Before picking, `scripts/make_drop.py` reads every
file in `drops/` and rules out anything already used, matching both on YouTube
video ID and on a normalized artist and title, so the same song cannot come back
through a different upload or a remaster.

Automatic picks land as `kind: unsorted` with no writeup, which the validator
flags until a curator calls it forgotten or obscure and writes the story.

To turn it on, create an API key at
[console.cloud.google.com](https://console.cloud.google.com) with the YouTube
Data API v3 enabled, then add it as the repository secret `YOUTUBE_API_KEY`.
Without the secret the workflow runs, finds nothing to pull, and changes
nothing.

Picks are otherwise chosen by hand. Automated obscurity scoring comes later,
once there are enough submissions to tune it against. When it arrives, the plan is to
score obscurity from open sources (Last.fm listener and play counts,
MusicBrainz release dates) rather than raw view counts, since a track uploaded
last week has few views without being rare at all.

Each drop targets about thirty minutes of runtime, not a fixed track count.

## Playing a whole drop

If the tracks in a drop carry YouTube links, the build script collects the video
IDs into a single `watch_videos` link that plays the drop straight through. It
creates no playlist and needs no account or API key.

Nothing equivalent exists for Spotify or Apple Music, where a real playlist has
to be made by someone signed in. Make one by hand and add it to the drop file
and a button appears:

    playlists:
      spotify: https://open.spotify.com/playlist/...

Leave it out and nothing breaks.

## Repository layout

    submissions/      one YAML file per participant
    inbox/            submitted picks waiting to be placed in a drop
    drops/            one YAML file per published drop
    data/drops.json   built from drops/, read by the site
    scripts/build.py  validates everything and builds data/drops.json
    scripts/intake.py turns a submitted issue into a file in the repository
    scripts/pull_playlist.py reads participants' public YouTube playlists
    scripts/make_drop.py builds a day's drop without ever repeating a track
    index.html        the site, served from the repository root
    submit.html       the submission form

Build the site data locally:

    python3 -m pip install pyyaml
    python3 scripts/build.py

The same script runs on every pull request and rejects malformed files, so you
find out about a typo before a human has to.

## About the music

CrateDig links to music. It does not host it, stream it, or copy it. Every
recording belongs to whoever made it. Where an artist sells the record
directly, the link points there.

## License

Code and site are AGPL-3.0 (see [`LICENSE`](LICENSE)), with a commercial option
described in [`COMMERCIAL-LICENSE.md`](COMMERCIAL-LICENSE.md). Contributions are
covered by [`CLA.md`](CLA.md). Read that one before your first pull request.
