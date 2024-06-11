#!/usr/bin/env python3
"""Generate realistic-sized copies of the three nightly exports into ``data/``.

The real exports are not committed (they are hundreds of megabytes), so this
script rebuilds something with the same shape:

* rows are append-ordered, oldest first;
* a category is not necessarily present from the first row.  Services get
  deployed, audit actions arrive with a permissions release, metrics get
  introduced -- so several categories here are absent for the first stretch of
  the export and then present, regularly, all the way to the last row;
* a small fraction of rows are incomplete (no message / undecided outcome /
  missing sample) the way the collectors really do leave them.

Usage:
    python tools/generate_exports.py [--rows 250000] [--out data] [--seed 7]
"""

from __future__ import annotations

import argparse
import pathlib
import random

# level -> fraction of the export that must go by before the level shows up
LOG_LEVELS = {
    "INFO": 0.0,
    "WARN": 0.0,
    "DEBUG": 0.0,
    "ERROR": 0.18,      # error taxonomy landed a fifth of the way in
    "CRITICAL": 0.42,   # pager integration landed later still
}
SERVICES = ("gateway", "billing", "search", "notifier")

AUDIT_ACTIONS = {
    "session.login": 0.0,
    "object.read": 0.0,
    "role.revoke": 0.25,    # arrived with the permissions release
    "key.rotate": 0.55,     # arrived with the KMS migration
}
ACTORS = ("svc-batch", "u-1041", "u-2277", "u-9013", "svc-sync")
TARGETS = ("repo/alpha", "repo/beta", "bucket/raw", "bucket/curated")

METRICS = {
    "cpu.pct": 0.0,
    "mem.pct": 0.0,
    "cache.evictions": 0.22,   # cache tier shipped part way through
    "queue.depth": 0.48,       # queue rewrite shipped later
}
HOSTS = ("host-a", "host-b", "host-c")


def _stamp(i: int) -> str:
    return f"2024-06-{1 + i // 86400:02d}T{i % 86400 // 3600:02d}:{i % 3600 // 60:02d}:{i % 60:02d}Z"


def _available(table: dict[str, float], i: int, rows: int) -> list[str]:
    return [k for k, start in table.items() if i >= int(start * rows)]


def write_logs(path: pathlib.Path, rows: int, rng: random.Random) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write("ts,level,service,message\n")
        for i in range(rows):
            level = rng.choice(_available(LOG_LEVELS, i, rows))
            service = rng.choice(SERVICES)
            # A rotation that gets truncated leaves the message column empty.
            message = "" if i % 4001 == 0 else f"{service} handled request {i}"
            fh.write(f"{_stamp(i)},{level},{service},{message}\n")


def write_audit(path: pathlib.Path, rows: int, rng: random.Random) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write("event_time,actor,action,target,outcome\n")
        for i in range(rows):
            action = rng.choice(_available(AUDIT_ACTIONS, i, rows))
            outcome = "error" if i % 733 == 0 else rng.choice(("allow", "allow", "deny"))
            fh.write(
                f"{_stamp(i)},{rng.choice(ACTORS)},{action},{rng.choice(TARGETS)},{outcome}\n"
            )


def write_metrics(path: pathlib.Path, rows: int, rng: random.Random) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write("collected_at,metric,host,value\n")
        for i in range(rows):
            metric = rng.choice(_available(METRICS, i, rows))
            # An agent that could not sample still emits the row.
            value = "" if i % 1301 == 0 else f"{rng.random() * 100:.3f}"
            fh.write(f"{_stamp(i)},{metric},{rng.choice(HOSTS)},{value}\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows", type=int, default=250_000)
    ap.add_argument("--out", default="data")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for name, writer in (
        ("logs_export.csv", write_logs),
        ("audit_export.csv", write_audit),
        ("metrics_export.csv", write_metrics),
    ):
        target = out / name
        writer(target, args.rows, random.Random(args.seed))
        print(f"wrote {target} ({args.rows} rows)")


if __name__ == "__main__":
    main()
