"""Guessing what kind of find a track is, from the one number we get for free.

Reach says something. A track with four figures of plays never surfaced. A
track with eight never needed to. In between says nothing useful, so this
abstains rather than inventing a category.

`forgotten` is never guessed. It means the record was popular once and is not
now, which needs history the view count does not carry. A person decides that
when they write the track up.
"""

OBSCURE_BELOW = 25_000
SIDEWAYS_ABOVE = 2_000_000

KINDS = ("obscure", "forgotten", "sideways", "unsorted")


def guess(views):
    """obscure, sideways, or unsorted when the number does not settle it."""
    if not isinstance(views, int) or views < 0:
        return "unsorted"
    if views < OBSCURE_BELOW:
        return "obscure"
    if views > SIDEWAYS_ABOVE:
        return "sideways"
    return "unsorted"


def explain(kind, views):
    """One line for the reply, so a submitter can see the reasoning and argue."""
    if kind == "obscure":
        return f"Filed as obscure: {views:,} plays is nobody."
    if kind == "sideways":
        return (f"Filed as sideways, not rare at all with {views:,} plays, "
                "just never crossed your path.")
    return "Left unsorted. Somebody decides which kind it is when it gets written up."
