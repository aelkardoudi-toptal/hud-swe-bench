"""Shared paging primitives for the export readers.

Every reader in this package offers "newest first" positional paging over a
LazyFrame that is far too large to materialise.  Readers must not hand-roll that
arithmetic.  The offset/length bookkeeping for end-relative paging is fiddly and
we have already shipped it wrong once, so there is exactly one implementation of
it: :func:`page_from_end`.  A reader is expected to build its LazyFrame (scan,
filter, project, cast) and then hand that frame to :func:`page_from_end` -- it
should never take a slice of the frame itself.

``src.metrics`` is the reference call site for the convention.

``src.logs`` and ``src.audit`` predate this module and still inline their own
end-relative slicing.  They have not been migrated yet; new readers should not
copy them.
"""

from __future__ import annotations

import polars as pl

#: The only collect engine the readers are allowed to use.  The exports are
#: bigger than the box, so nothing here may fall back to the in-memory engine
#: (nor to ``engine="auto"``, which silently picks it).
STREAMING = "streaming"


def frame_length(lf: pl.LazyFrame) -> int:
    """Count the rows ``lf`` would produce, without materialising them."""
    return int(lf.select(pl.len()).collect(engine=STREAMING).item())


def empty_like(lf: pl.LazyFrame) -> pl.DataFrame:
    """An empty DataFrame with the same schema as ``lf``."""
    return lf.limit(0).collect(engine=STREAMING)


def page_from_end(lf: pl.LazyFrame, skip: int, count: int) -> pl.DataFrame:
    """Return one page of ``lf``, counted backwards from its last row.

    Page ``(skip, count)`` is the block of rows ending ``skip`` rows before the
    final row of ``lf`` -- that is, rows ``[n - skip - count, n - skip)`` of
    ``lf``, clipped to the frame.  Rows keep the relative order they have in
    ``lf``.

    The pages are half-open, so walking ``(0, c)``, ``(c, c)``, ``(2c, c)``, ...
    visits every row of ``lf`` exactly once and never repeats one.  A request
    for ``count`` rows yields at most ``count`` rows: the oldest page may be
    short, and a ``skip`` at or past the start of the frame yields nothing.

    Raises ValueError for negative ``skip`` or ``count``.
    """
    if skip < 0:
        raise ValueError(f"skip must not be negative, got {skip}")
    if count < 0:
        raise ValueError(f"count must not be negative, got {count}")
    if count == 0:
        return empty_like(lf)
    return lf.slice(-(skip + count), count).collect(engine=STREAMING)
