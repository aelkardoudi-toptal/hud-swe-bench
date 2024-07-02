"""Reader for ``metrics_export.csv``, used by the metric explorer.

Columns in the export: ``collected_at,metric,host,value``.

``value`` is written by several different collectors and is not always a number:
agents that failed to sample a metric still emit the row with an empty value.
Those rows are dropped here so the explorer never has to plot a null.
"""

from __future__ import annotations

import polars as pl

from src import paging

COLUMNS = ["collected_at", "metric", "host", "value"]


def _samples(source, metric_name: str) -> pl.LazyFrame:
    """Lazy frame of the numeric samples for ``metric_name``, oldest first."""
    return (
        pl.scan_csv(source, schema_overrides={"value": pl.Float64})
        .filter(pl.col("metric") == metric_name)
        .filter(pl.col("value").is_not_null())
    )


def count_samples(source, metric_name: str) -> int:
    """How many numeric samples the export holds for ``metric_name``."""
    return paging.frame_length(_samples(source, metric_name))


def get_metric_page(source, metric_name: str, skip: int = 0, count: int = 200):
    """One page of samples for ``metric_name``, counted back from the newest.

    Positional paging is delegated to :func:`src.paging.page_from_end`; see that
    docstring for the exact page semantics (half-open pages, short oldest page,
    empty once ``skip`` runs off the start).
    """
    if metric_name is None or not str(metric_name).strip():
        raise ValueError("metric_name must not be empty")

    samples = _samples(source, metric_name)
    page = paging.page_from_end(samples, skip, count)
    return page.select(COLUMNS)
