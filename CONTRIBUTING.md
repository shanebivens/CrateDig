# Contributing

Most contributions here are music, not code. Both are welcome.

## The short way

[Use the form](https://shanebivens.github.io/CrateDig/submit.html). It hands you
a prefilled issue, you press one button, and the `Intake` workflow files it,
replies, and closes the issue within a minute. Everything below is for people
who would rather edit the files themselves.

Before your first pull request, read [`CLA.md`](CLA.md) and add this line to the
pull request description:

    I have read CLA.md and I agree to it.

## Submitting yourself as a participant

Copy `submissions/EXAMPLE.yml` to `submissions/your-handle.yml`, where
`your-handle` matches the `handle` field inside the file. Fill in one or more
public playlist links.

    handle: your-handle
    joined: 2026-08-26
    playlists:
      - url: https://music.youtube.com/playlist?list=XXXXXXXX
        service: youtube-music
        note: what this playlist is

Make the playlist public. A private or unlisted link is useless to everyone
else and the validator cannot check it.

Do not put your email, your real name, or anything else you would not post in
public into these files. The repository is public and git history is forever.

## Submitting a pick for a drop

Open a pull request that adds a track to the current file in `drops/`, or open
an issue with the submission template and someone will place it.

    - artist: Connie Converse
      title: Talkin' Like You (Two Tall Mountains)
      year: 1954
      duration: null
      kind: obscure
      submitted_by: your-handle
      why: >
        One or two sentences. What is the story, why did it disappear,
        what should someone listen for.
      links:
        youtube: https://www.youtube.com/watch?v=XXXXXXXXXXX

Fields:

- `kind` is `forgotten` or `obscure`. See the README for the difference.
- `year` is the recording or release year, whichever tells the better story.
- `duration` is `M:SS`. Leave it `null` if you do not know it yet, the
  validator will tell you which tracks are missing one.
- `why` is the part people actually read. Two sentences beats two paragraphs.
- `links` needs at least one. Prefer a link where the artist gets paid, such as
  Bandcamp, when one exists.

If you have a stake in the track, say so in `why`. Submitting your own band is
allowed and it is more interesting than pretending otherwise.

## What does not get merged

- Links to recordings hosted without permission.
- Anything that requires an account, a cookie, or a credential to read.
- A wall of submissions from one person in a single drop. Three per drop keeps
  it varied.
- Picks with no `why`. The writeup is the reason anyone plays it.

## Code contributions

Run the validator before you open a pull request:

    python3 -m pip install pyyaml
    python3 scripts/build.py

Keep it dependency light. The site is plain HTML, CSS, and JavaScript on
purpose, with no build step and no framework, so that it keeps working
untouched for years.
