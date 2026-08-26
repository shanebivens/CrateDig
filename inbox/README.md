# Inbox

Picks submitted through the issue form land here, one file per submission, and
wait for a curator to place them in a drop. Nothing in this folder appears on
the site.

`scripts/place_inbox.py` moves the two most recent into the next week in
`scheduled/`, which holds spots open for exactly this. It runs every Monday, and
`/writeups` runs it too. Anything that does not fit keeps for the following week.

    python3 scripts/place_inbox.py --dry-run
    python3 scripts/place_inbox.py --slots 0        # place all of them now
    python3 scripts/place_inbox.py --oldest-first   # clear the backlog instead

`scripts/build.py` reports how many are waiting.
