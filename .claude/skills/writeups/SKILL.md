---
name: writeups
description: Write the story for the tracks in the next CrateDig drop and set each one to forgotten, obscure or sideways. Use when the user asks to do the writeups, prepare the next drop, or write up this week's picks.
---

# The weekly pass

Everything that has to happen between one Monday and the next. Run it in order.

## 1. Take in what people sent

    python3 scripts/place_inbox.py

This moves the two most recent submitted picks out of `inbox/` and into the next
week, which holds two spots open for them. Submitted picks arrive with the
submitter's own kind and writeup, so they need placing, not rewriting. Leave
their words alone. Fix a typo, nothing more.

If the inbox has a backlog, say so and offer `--oldest-first` or `--slots 0`.
Do not silently place more than the two spots.

## 2. Refresh the pool, if you can

    YOUTUBE_API_KEY=... python3 scripts/pull_playlist.py

Skip this when the key is not in the environment. The Monday workflow does it
anyway, so a local skip costs nothing. Never ask the user to paste the key.

## 3. Write up the rest

Automatic picks arrive with `kind: unsorted` and a placeholder `why`. Turn them
into something worth reading before the drop goes live.

## Find the work

The next drop is the earliest file in `scheduled/`. Read it. Work on every track
whose `kind` is `unsorted` or whose `why` is still
`Pulled from the daily thirty minutes. No writeup yet.`

If the user names a date, use `scheduled/<date>.yml` or `drops/<date>.yml`
instead. If nothing needs work, say so and stop.

## Research every track before writing

Search for each one. Do not write from memory alone, and do not skip this
because the artist seems familiar. Worth finding:

- who made it, where, and when
- what happened to them, if anything did
- how the record was released: label, private press, self-released, a reissue
- whether it was a hit anywhere, and whether it stopped being one
- anything odd about how it was made or how it survived

`data/pool.json` has the view count next to each track, which is a hint about
reach and nothing more.

## The one rule that matters

**Never invent.** No fabricated label names, sales figures, chart positions,
band breakups, or biographical detail. If the search turns up thin, write the
thin true thing:

> Nothing turns up about this beyond the upload itself, which is its own kind of
> answer.

That is a fine writeup. An invented backstory is not, and on a project about
real records it is the one unrecoverable mistake. When you are unsure whether
something is true, leave it out or attribute it: "the story goes that".

## Set the kind

- `forgotten` — it was popular once and nobody plays it now. Needs evidence it
  actually landed at some point.
- `obscure` — it never surfaced. Private press, tiny label, self-released, a few
  hundred copies, an upload with four figures of views after fifteen years.
- `sideways` — not rare at all, just never crossed the listener's path. A big
  band, a novelty record, a cover, a hit in another country. Most mainstream
  picks belong here rather than being forced into the other two.

Every pick is a doorway into its own YouTube mix, so a writeup can point at
where a track leads as much as at the track itself. "Follow that thread instead
of this one" is a legitimate thing to write.

When it is genuinely between two, pick the one the writeup argues for.

## Write the why

Two or three sentences. What is the story, why did it disappear or never land,
what should someone listen for. Specific beats sweeping. The house voice:

- No em dashes. Commas, colons, full stops.
- No "not just X, but Y", no rule of three, no balanced pairs.
- No "delve", "testament", "seamless", "crucial", "it's worth noting".
- Plain and varied. Write like a person who has heard the record.

Read the existing writeups in `drops/2026-08-26.yml` for the register.

## Fill in what else you found

- `year` if research turned up a reliable one
- a better link in `links` if there is a Bandcamp page or an artist's own
  upload. Bandcamp first when the artist sells it directly
- leave `duration` alone, the API set it

## Finish

1. Run `python3 scripts/build.py` and clear any warning it raises about the file.
2. Show the user each track: kind, the writeup, and where the facts came from.
   Mark which came from a submission and which were pulled.
3. Ask before committing. Do not push a drop the user has not read.

The drop stays in `scheduled/` and goes live on its own Monday at 12:01pm
Eastern. Nothing here publishes anything early.
