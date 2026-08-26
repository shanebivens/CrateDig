# Scheduled

Weeks lined up but not yet published, one file per Monday. Nothing here reaches
the site, so a drop appears only when its moment comes.

`scripts/publish_due.py` moves a file into `drops/` once 12:01pm Eastern on its
Monday has passed. The `Monday drop` workflow runs it and tops the queue back up.

Seeding ahead is the point: you can set `kind` and write the real story for a
track days before anyone sees it. Edit the file here and it goes out that way.

    python3 scripts/seed_weeks.py --weeks 8
    python3 scripts/publish_due.py --dry-run
