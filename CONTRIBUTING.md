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

## Playlists are not accepted

One track at a time. A pick should be something you chose and can say something
about. A playlist means a script picks for you, publishes it under your name,
and nobody has written a word about why it is worth hearing.

The site does draw on one playlist, the maintainer's, to fill weeks that
submissions do not. It is marked `pool: true` in its file, and that flag is the
only thing that makes a playlist readable. Nothing else in `submissions/` is
touched.

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

- `kind` is `forgotten`, `obscure` or `sideways`. See the README for the
  difference. `unsorted` means an automatic pick nobody has judged yet.
- `year` is the recording or release year, whichever tells the better story.
- `duration` is `M:SS`. Leave it `null` if you do not know it yet, the
  validator will tell you which tracks are missing one.
- `why` is the part people actually read. Two sentences beats two paragraphs.
- `links` needs at least one. A YouTube link also becomes the doorway, since
  the site turns it into a mix that keeps playing past the track. Prefer a link
  where the artist gets paid, such as Bandcamp, when one exists.

If you have a stake in the track, say so in `why`. Submitting your own band is
allowed and it is more interesting than pretending otherwise.

## What does not get merged

- Links to recordings hosted without permission.
- Anything that requires an account, a cookie, or a credential to read.
- A wall of submissions from one person at once. Two spots a week go to
  submitted picks, newest first, and the rest keep for the following week.
- Picks with no `why`. The writeup is the reason anyone plays it.

## Code contributions

Run the validator before you open a pull request:

    python3 -m pip install pyyaml
    python3 scripts/build.py

Keep it dependency light. The site is plain HTML, CSS, and JavaScript on
purpose, with no build step and no framework, so that it keeps working
untouched for years.
