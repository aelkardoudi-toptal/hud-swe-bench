import pytest

from src.logs import KNOWN_LEVELS, VIEW_COLUMNS, count_logs, get_log_page_from_end
from tests.conftest import read_rows


def expected(path, level):
    """Timestamps of the fixture rows the reader should consider, in file order."""
    return [
        r["ts"]
        for r in read_rows(path)
        if r["level"] == level and r["message"] != ""
    ]


def test_counts_only_rows_with_a_message(logs_csv):
    rows = read_rows(logs_csv)
    with_message = [r for r in rows if r["level"] == "ERROR" and r["message"] != ""]
    all_error = [r for r in rows if r["level"] == "ERROR"]
    assert len(all_error) >= len(with_message)
    assert count_logs(logs_csv, "ERROR") == len(with_message)


def test_view_columns(logs_csv):
    page = get_log_page_from_end(logs_csv, "INFO", 0, 5)
    assert page.columns == list(VIEW_COLUMNS)


def test_level_is_normalised(logs_csv):
    a = get_log_page_from_end(logs_csv, "info", 0, 5)["ts"].to_list()
    b = get_log_page_from_end(logs_csv, "  INFO ", 0, 5)["ts"].to_list()
    assert a == b == expected(logs_csv, "INFO")[-5:]


def test_unknown_level_rejected(logs_csv):
    with pytest.raises(ValueError):
        get_log_page_from_end(logs_csv, "VERBOSE", 0, 5)


def test_negative_arguments_rejected(logs_csv):
    with pytest.raises(ValueError):
        get_log_page_from_end(logs_csv, "INFO", -1, 5)
    with pytest.raises(ValueError):
        get_log_page_from_end(logs_csv, "INFO", 0, -1)


def test_first_page_is_the_newest_rows(logs_csv):
    want = expected(logs_csv, "WARN")
    assert get_log_page_from_end(logs_csv, "WARN", 0, 6)["ts"].to_list() == want[-6:]


def test_pages_do_not_overlap(logs_csv):
    want = expected(logs_csv, "WARN")
    first = get_log_page_from_end(logs_csv, "WARN", 0, 6)["ts"].to_list()
    second = get_log_page_from_end(logs_csv, "WARN", 6, 6)["ts"].to_list()
    assert second == want[-12:-6]
    assert not set(first) & set(second)


def test_zero_count(logs_csv):
    page = get_log_page_from_end(logs_csv, "INFO", 0, 0)
    assert page.height == 0
    assert page.columns == list(VIEW_COLUMNS)


def test_level_with_no_rows(logs_csv):
    assert count_logs(logs_csv, "TRACE") == 0
    assert get_log_page_from_end(logs_csv, "TRACE", 0, 10).height == 0


def test_all_known_levels_are_readable(logs_csv):
    for level in KNOWN_LEVELS:
        page = get_log_page_from_end(logs_csv, level, 0, 3)
        assert page.height <= 3
