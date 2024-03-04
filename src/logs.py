"""Reader for ``logs_export.csv``, used by the log viewer.

Columns in the export: ``ts,level,service,message``.
"""

from __future__ import annotations

import polars as pl

ENGINE = "streaming"

#: Levels the platform emits.  Anything else is a caller bug, not a data bug.
KNOWN_LEVELS = ("TRACE", "DEBUG", "INFO", "WARN", "ERROR", "CRITICAL")

#: The columns the viewer renders, in render order.
VIEW_COLUMNS = ("ts", "level", "service", "message")

_SCHEMA = {
    "ts": pl.Utf8,
    "level": pl.Utf8,
    "service": pl.Utf8,
    "message": pl.Utf8,
}


def _normalise_level(level: str) -> str:
    if not isinstance(level, str):
        raise ValueError(f"level must be a string, got {type(level).__name__}")
    wanted = level.strip().upper()
    if wanted not in KNOWN_LEVELS:
        raise ValueError(
            f"unknown level {level!r}; expected one of {', '.join(KNOWN_LEVELS)}"
        )
    return wanted


def _scan(source, level: str) -> pl.LazyFrame:
    """Lazy frame of the export rows at ``level``, oldest first."""
    return (
        pl.scan_csv(source, schema_overrides=_SCHEMA)
        .filter(pl.col("level") == level)
        # Truncated writes at the end of a rotation leave rows with no message.
        # The viewer has nothing to show for those, so they never count.
        .filter(pl.col("message").is_not_null())
    )


def count_logs(source, level: str) -> int:
    """How many rows the export holds at ``level``."""
    lf = _scan(source, _normalise_level(level))
    return int(lf.select(pl.len()).collect(engine=ENGINE).item())


def get_log_page_from_end(source, level: str, skip: int = 0, count: int = 50):
    """One page of ``level`` rows, newest page first.

    ``skip`` rows are stepped over from the end of the export and the next
    ``count`` rows (in export order) are returned.  ``(0, c)``, ``(c, c)``,
    ``(2c, c)``, ... walks the whole level backwards without repeats; the oldest
    page may be short and a ``skip`` past the start returns nothing.
    """
    if not isinstance(skip, int) or isinstance(skip, bool):
        raise ValueError(f"skip must be an int, got {skip!r}")
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError(f"count must be an int, got {count!r}")
    if skip < 0:
        raise ValueError(f"skip must not be negative, got {skip}")
    if count < 0:
        raise ValueError(f"count must not be negative, got {count}")

    lf = _scan(source, _normalise_level(level))

    if count == 0:
        page = lf.limit(0).collect(engine=ENGINE)
    else:
        page = lf.slice(-(skip + count), count).collect(engine=ENGINE)

    return page.select(list(VIEW_COLUMNS))
