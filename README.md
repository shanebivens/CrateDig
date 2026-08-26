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

1. Fork this repository.
2. Copy `submissions/EXAMPLE.yml` to `submissions/your-handle.yml` and fill it in.
3. Open a pull request. Add `I have read CLA.md and I agree to it.` to the
   description.

Your file holds public playlist links, not credentials. Nothing here ever asks
for a password, a cookie, or access to your account, and it never will. If a
future version reads listening history, it will do it through something you
control and can revoke.

Not comfortable with git? Open an issue using the submission template instead
and it gets picked up the same way.

## How a drop gets made

Picks are chosen by hand right now. Automated scoring comes later, once there
are enough submissions to tune it against. When it arrives, the plan is to
score obscurity from open sources (Last.fm listener and play counts,
MusicBrainz release dates) rather than raw view counts, since a track uploaded
last week has few views without being rare at all.

Each drop targets about thirty minutes of runtime, not a fixed track count.

## Repository layout

    submissions/     one YAML file per participant
    drops/           one YAML file per published drop
    data/drops.json  built from drops/, read by the site
    scripts/build.py validates everything and builds data/drops.json
    index.html       the site, served from the repository root

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
