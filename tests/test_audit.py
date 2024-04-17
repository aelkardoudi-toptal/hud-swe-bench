import pytest

from src.audit import (
    AuditQueryError,
    DECIDED,
    MAX_PAGE_SIZE,
    count_events,
    get_audit_page,
)
from tests.conftest import read_rows


def expected(path, action):
    return [
        r["event_time"]
        for r in read_rows(path)
        if r["action"] == action and r["outcome"] in DECIDED
    ]


def test_undecided_events_are_excluded(audit_csv):
    rows = read_rows(audit_csv)
    undecided = [r for r in rows if r["outcome"] not in DECIDED]
    assert undecided, "fixture should contain at least one undecided event"
    assert count_events(audit_csv, "session.login") == len(
        expected(audit_csv, "session.login")
    )


def test_output_columns(audit_csv):
    page = get_audit_page(audit_csv, "session.login", 0, 4)
    assert page.columns == ["event_time", "actor", "action", "target", "outcome"]
    assert set(page["outcome"].to_list()) <= set(DECIDED)


def test_first_page_is_the_newest_events(audit_csv):
    want = expected(audit_csv, "object.read")
    assert get_audit_page(audit_csv, "object.read", 0, 8)["event_time"].to_list() == want[-8:]


def test_pages_do_not_overlap(audit_csv):
    want = expected(audit_csv, "object.read")
    first = get_audit_page(audit_csv, "object.read", 0, 8)["event_time"].to_list()
    second = get_audit_page(audit_csv, "object.read", 8, 8)["event_time"].to_list()
    assert second == want[-16:-8]
    assert not set(first) & set(second)


def test_zero_count(audit_csv):
    assert get_audit_page(audit_csv, "session.login", 0, 0).height == 0


def test_unknown_action_is_empty(audit_csv):
    assert count_events(audit_csv, "nope.nope") == 0
    assert get_audit_page(audit_csv, "nope.nope", 0, 5).height == 0


def test_bad_arguments_rejected(audit_csv):
    with pytest.raises(AuditQueryError):
        get_audit_page(audit_csv, "", 0, 5)
    with pytest.raises(AuditQueryError):
        get_audit_page(audit_csv, "session.login", -1, 5)
    with pytest.raises(AuditQueryError):
        get_audit_page(audit_csv, "session.login", 0, -5)
    with pytest.raises(AuditQueryError):
        get_audit_page(audit_csv, "session.login", 0, MAX_PAGE_SIZE + 1)


def test_audit_query_error_is_a_value_error():
    assert issubclass(AuditQueryError, ValueError)
