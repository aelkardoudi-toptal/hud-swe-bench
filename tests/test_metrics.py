import pytest

from src.metrics import COLUMNS, count_samples, get_metric_page
from tests.conftest import read_rows


def expected(path, metric):
    return [
        r["collected_at"]
        for r in read_rows(path)
        if r["metric"] == metric and r["value"] != ""
    ]


def test_missing_samples_are_dropped(metrics_csv):
    rows = read_rows(metrics_csv)
    blanks = [r for r in rows if r["value"] == ""]
    assert blanks, "fixture should contain at least one unsampled row"
    assert count_samples(metrics_csv, "cpu.pct") == len(expected(metrics_csv, "cpu.pct"))


def test_output_columns_and_value_type(metrics_csv):
    page = get_metric_page(metrics_csv, "mem.pct", 0, 4)
    assert page.columns == COLUMNS
    assert page["value"].dtype.is_float()
    assert page["value"].null_count() == 0


def test_first_page_is_the_newest_samples(metrics_csv):
    want = expected(metrics_csv, "mem.pct")
    assert get_metric_page(metrics_csv, "mem.pct", 0, 7)["collected_at"].to_list() == want[-7:]


def test_pages_do_not_overlap(metrics_csv):
    want = expected(metrics_csv, "mem.pct")
    first = get_metric_page(metrics_csv, "mem.pct", 0, 7)["collected_at"].to_list()
    second = get_metric_page(metrics_csv, "mem.pct", 7, 7)["collected_at"].to_list()
    assert second == want[-14:-7]
    assert not set(first) & set(second)


def test_zero_count(metrics_csv):
    page = get_metric_page(metrics_csv, "cpu.pct", 0, 0)
    assert page.height == 0
    assert page.columns == COLUMNS


def test_unknown_metric_is_empty(metrics_csv):
    assert count_samples(metrics_csv, "nope") == 0
    assert get_metric_page(metrics_csv, "nope", 0, 5).height == 0


def test_empty_metric_name_rejected(metrics_csv):
    with pytest.raises(ValueError):
        get_metric_page(metrics_csv, "  ", 0, 5)


def test_negative_arguments_rejected(metrics_csv):
    with pytest.raises(ValueError):
        get_metric_page(metrics_csv, "cpu.pct", -1, 5)
    with pytest.raises(ValueError):
        get_metric_page(metrics_csv, "cpu.pct", 0, -5)
