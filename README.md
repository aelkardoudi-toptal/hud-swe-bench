# exportkit

Read-only readers for the nightly CSV exports that the platform team drops into
`data/`.

The exports do not fit in memory, so every reader scans lazily and collects with
the polars streaming engine.  Row order in a file is the order the platform
emitted the records, oldest first, and every reader preserves it.

Callers all want the newest records first, so the readers take `skip`/`count`
counted from the *end* of the filtered export.

`fixtures/` holds the small committed CSVs the test suite runs against.

## Running the tests

    python -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    pytest -q
