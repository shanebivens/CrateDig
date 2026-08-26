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
- **Sideways.** Not rare at all, just never crossed your path, or it did and you
  wrote it off. Weird, mainstream, sideways, all of it counts.

A deep cut by a famous band is usually neither. If most people know the artist,
it probably belongs somewhere else.

## How to join

**[Fill in the form](https://shanebivens.github.io/CrateDig/submit.html).** Four
fields. It hands you a filled-out submission, you press one button, and a bot
files it into this repository and replies within a minute. No git, no pull
request, nothing to learn.

**One track at a time, on purpose.** Playlists are not accepted. A pick should be
something you chose and have something to say about, not something a machine
pulled out of your listening. It also means your writeup goes out in your words
rather than a placeholder, and a place on the contributor list is earned by
sending something in.

The site keeps one playlist of its own, the maintainer's, as the well it draws
from when submissions do not fill a week. Only a playlist marked `pool: true` is
ever read, and nobody else's is.

You send public links, nothing else. Nothing here ever asks for a password, a
cookie, or access to your listening account, and it never will.

## How a submission becomes a drop

1. Someone submits through the form, which opens a prefilled issue.
2. The `Intake` workflow parses it, writes the pick into `inbox/`, replies on
   the issue, and closes it. Your handle comes from your GitHub username, so
   nobody can claim someone else's.
3. Every week holds **two spots open** for submitted picks. On Monday,
   `scripts/place_inbox.py` moves the two most recent out of `inbox/` and into
   the next week ahead of anything the pull chose. Submissions arrive with the
   submitter's own kind and writeup, so those go out in their words.
4. Anything that does not fit keeps for the following week.
5. Pushing rebuilds `data/drops.json` and the site updates.

## Mondays at 12:01pm Eastern

Weeks are lined up in advance in `scheduled/`, five to seven tracks each. Two
spots go to submitted picks and the rest are pulled from the maintainer's
playlist so a week is never empty. Nothing there reaches the site. At
12:01pm Eastern on its Monday, one week moves into `drops/` and appears. One at
a time, never the whole queue at once.

Playlists are read through the official YouTube Data API with a plain API key:
public playlist data only, no OAuth and no listening history.

Daylight saving is worked out from the real Eastern clock rather than a cron
line, so nothing shifts by an hour twice a year. The workflow fires at both
16:01 and 17:01 UTC and whichever run is early publishes nothing.

Seeding ahead is the point. You can set `kind` and write the real story for a
track days before anyone sees it. Edit its file in `scheduled/` and it goes out
that way.

Listening stays daily. That is what the playlist is for.

**Nothing ever repeats.** Before picking, `scripts/make_drop.py` reads every
file in `drops/` *and* `scheduled/` and rules out anything already used or
already lined up, matching both on YouTube video ID and on a normalized artist
and title, so the same song cannot come back through a different upload or a
remaster. Anything longer than ten minutes is skipped as well, since a concert
recording or a full album upload is not a track.

Automatic picks land as `kind: unsorted` with no writeup, which the validator
flags until a curator calls it forgotten or obscure and writes the story.

Line up more weeks, or check what is due, any time:

    python3 scripts/seed_weeks.py --weeks 8
    python3 scripts/publish_due.py --dry-run

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

## Every pick is a doorway

A drop is not a playlist to sit through. Each track links to its YouTube mix,
`watch?v=<id>&list=RD<id>`, which plays the song and then keeps going into
whatever the recommender thinks it resembles. One song becomes an afternoon of
music you have never heard, which is the entire point.

That is why a drop is five to seven tracks rather than a fixed runtime. You are
being handed starting points, and you are not expected to use all of them.

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

    submissions/      the playlist the site draws from when a week is short
    inbox/            submitted picks waiting to be placed in a drop
    scheduled/        weeks lined up but not yet published
    drops/            one YAML file per published drop
    data/drops.json   built from drops/, read by the site
    scripts/build.py  validates everything and builds data/drops.json
    scripts/intake.py turns a submitted issue into a file in the repository
    scripts/pull_playlist.py reads participants' public YouTube playlists
    scripts/make_drop.py builds a drop without ever repeating a track
    scripts/seed_weeks.py lines up future Mondays in scheduled/
    scripts/place_inbox.py puts submitted picks into the spots held for them
    scripts/publish_due.py releases a week once its moment has passed
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
