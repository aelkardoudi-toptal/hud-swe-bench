import polars as pl
import pytest

from src import paging


def frame(n):
    """A lazy frame of ``n`` rows in a known order."""
    return pl.LazyFrame({"i": list(range(n)), "tag": [f"t{i}" for i in range(n)]})


def test_frame_length():
    assert paging.frame_length(frame(37)) == 37
    assert paging.frame_length(frame(0)) == 0


def test_empty_like_keeps_schema():
    empty = paging.empty_like(frame(9))
    assert empty.height == 0
    assert empty.columns == ["i", "tag"]


def test_first_page_is_the_newest_rows():
    assert paging.page_from_end(frame(20), 0, 5)["i"].to_list() == [15, 16, 17, 18, 19]


def test_second_page_does_not_overlap_the_first():
    first = paging.page_from_end(frame(20), 0, 5)["i"].to_list()
    second = paging.page_from_end(frame(20), 5, 5)["i"].to_list()
    assert second == [10, 11, 12, 13, 14]
    assert not set(first) & set(second)


def test_walking_backwards_covers_every_row_once():
    seen = []
    skip = 0
    while True:
        page = paging.page_from_end(frame(23), skip, 4)["i"].to_list()
        if not page:
            break
        seen = page + seen
        skip += 4
    assert seen == list(range(23))


def test_oldest_page_is_short():
    assert paging.page_from_end(frame(10), 8, 5)["i"].to_list() == [0, 1]


def test_skip_past_the_start_is_empty():
    assert paging.page_from_end(frame(10), 10, 5).height == 0
    assert paging.page_from_end(frame(10), 40, 5).height == 0


def test_zero_count_is_empty_but_keeps_schema():
    page = paging.page_from_end(frame(10), 0, 0)
    assert page.height == 0
    assert page.columns == ["i", "tag"]


def test_negative_arguments_rejected():
    with pytest.raises(ValueError):
        paging.page_from_end(frame(10), -1, 5)
    with pytest.raises(ValueError):
        paging.page_from_end(frame(10), 0, -5)
