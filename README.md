# exportkit

Read-only readers for the nightly CSV exports that the platform team drops into
`data/`.  Three of them exist today:

| export                | reader                | entry point                    |
| --------------------- | --------------------- | ------------------------------ |
| `logs_export.csv`     | `src/logs.py`         | `get_log_page_from_end`        |
| `audit_export.csv`    | `src/audit.py`        | `get_audit_page`               |
| `metrics_export.csv`  | `src/metrics.py`      | `get_metric_page`              |

## Ground rules

* **The exports do not fit in memory.**  A nightly `logs_export.csv` is a few
  hundred megabytes and growing; the retention-window exports are multiple
  gigabytes.  Every reader therefore scans lazily and collects with the polars
  **streaming** engine (`collect(engine="streaming")`).  Do not collect a whole
  export and post-process it in Python, and do not fall back to the in-memory
  engine "just for this one query" -- it will work fine on the fixtures in
  `fixtures/` and then take the box down in production.
* **Exports are append-ordered.**  Row order in the file is the order the
  platform emitted the records, oldest first.  Every reader preserves it.
* **Paging runs backwards.**  Callers (the log viewer, the audit trail UI, the
  metric explorer) all want the newest records first, so all three readers take
  `skip`/`count` counted from the *end* of the filtered export.
* **Positional paging goes through `src/paging.py`.**  See the module docstring
  there.

## Fixtures and generated data

`fixtures/` holds the small committed CSVs the test suite runs against.  They
are deliberately tiny so the suite stays fast.

Realistic exports are big and are **not** committed.  Generate them yourself:

    python tools/generate_exports.py            # writes data/*.csv
    python tools/generate_exports.py --rows 400000

`data/` is gitignored apart from its `.gitkeep`.

Note that the generator reproduces something the real exports do as well: not
every category is present from the first row.  Services get deployed, audit
actions get added by a permissions release, metrics get introduced -- so a
category can be absent for the first chunk of an export and present from there
to the end.

## Running the tests

    python -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    pytest -q
