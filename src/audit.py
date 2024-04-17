"""Reader for ``audit_export.csv``, used by the audit trail UI and by the
quarterly compliance report.

Columns in the export: ``event_time,actor,action,target,outcome``.

Compliance only cares about decided events: the collector writes ``outcome=error``
for records it could not resolve, and those are excluded everywhere so that the
row numbering in the UI matches the row numbering in the report.
"""

from __future__ import annotations

import polars as pl

_ENGINE = "streaming"

#: Outcomes that count as a decided event.
DECIDED = ["allow", "deny"]

#: The audit trail UI paginates; anything bigger than this is a runaway query.
MAX_PAGE_SIZE = 500

_OUT_COLUMNS = ["event_time", "actor", "action", "target", "outcome"]


class AuditQueryError(ValueError):
    """Raised for a request the audit reader will not serve."""


def _decided(source, action: str) -> pl.LazyFrame:
    return (
        pl.scan_csv(source)
        .filter(pl.col("outcome").is_in(DECIDED))
        .filter(pl.col("action") == action)
        .select(
            [
                pl.col("event_time").cast(pl.Utf8),
                pl.col("actor").cast(pl.Utf8),
                pl.col("action").cast(pl.Utf8),
                pl.col("target").cast(pl.Utf8),
                pl.col("outcome").cast(pl.Utf8),
            ]
        )
    )


def _check(action: str, skip: int, count: int) -> None:
    if not action or not isinstance(action, str):
        raise AuditQueryError(f"action must be a non-empty string, got {action!r}")
    if skip < 0:
        raise AuditQueryError(f"skip must not be negative, got {skip}")
    if count < 0:
        raise AuditQueryError(f"count must not be negative, got {count}")
    if count > MAX_PAGE_SIZE:
        raise AuditQueryError(
            f"count {count} exceeds the maximum page size of {MAX_PAGE_SIZE}"
        )


def count_events(source, action: str) -> int:
    """Number of decided events for ``action`` in the export."""
    if not action or not isinstance(action, str):
        raise AuditQueryError(f"action must be a non-empty string, got {action!r}")
    return int(
        _decided(source, action).select(pl.len()).collect(engine=_ENGINE).item()
    )


def get_audit_page(source, action: str, skip: int = 0, count: int = 100):
    """One page of decided ``action`` events, counted back from the newest.

    Successive calls with ``skip`` advancing by ``count`` step backwards through
    the export, each page holding at most ``count`` rows and no row appearing in
    two pages.  The oldest page can be short; once ``skip`` reaches the start of
    the export the result is empty.
    """
    _check(action, skip, count)

    events = _decided(source, action)

    if count == 0:
        return events.limit(0).collect(engine=_ENGINE)

    window = -(skip + count)
    return events.slice(window, count).collect(engine=_ENGINE).select(_OUT_COLUMNS)
