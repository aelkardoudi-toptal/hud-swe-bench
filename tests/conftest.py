import csv
import pathlib

import pytest

FIXTURES = pathlib.Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture(scope="session")
def logs_csv():
    return FIXTURES / "logs_small.csv"


@pytest.fixture(scope="session")
def audit_csv():
    return FIXTURES / "audit_small.csv"


@pytest.fixture(scope="session")
def metrics_csv():
    return FIXTURES / "metrics_small.csv"


def read_rows(path):
    """The fixture rows, in file order, as plain dicts.

    Used to build expectations without going through polars.
    """
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))
