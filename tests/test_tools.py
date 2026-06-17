import inspect
import math
import os

import psycopg

from tools.revenue_tools import (
    get_as_of_otb,
    get_block_vs_transient_mix,
    get_otb_summary,
    get_pickup_delta,
    get_segment_mix,
)


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://hackathon:hackathon@localhost:5432/hotel_hackathon",
)


def db_value(sql, params=None):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()[0]


def test_get_otb_summary_uses_stay_date_rows_not_reservations():
    result = get_otb_summary("2026-07")

    assert result["row_count"] >= result["reservation_count"]
    assert result["row_count"] == 64
    assert result["reservation_count"] == 35


def test_get_otb_summary_excludes_cancelled_by_default():
    expected = db_value(
        """
        select count(*)
        from reservations_hackathon
        where stay_date >= '2026-07-01'
          and stay_date < '2026-08-01'
          and financial_status = 'Posted'
          and reservation_status <> 'Cancelled'
        """
    )

    assert get_otb_summary("2026-07")["row_count"] == expected


def test_get_otb_summary_excludes_provisional_by_default():
    default_rows = get_otb_summary("2026-07")["row_count"]

    posted_non_cancelled = db_value(
        """
        select count(*)
        from reservations_hackathon
        where stay_date >= '2026-07-01'
          and stay_date < '2026-08-01'
          and financial_status = 'Posted'
          and reservation_status <> 'Cancelled'
        """
    )

    assert default_rows == posted_non_cancelled


def test_get_otb_summary_room_nights_sum_number_of_spaces():
    expected = db_value(
        """
        select sum(number_of_spaces)
        from vw_stay_night_base
        where stay_date >= '2026-07-01'
          and stay_date < '2026-08-01'
        """
    )

    assert get_otb_summary("2026-07")["room_nights"] == expected


def test_get_segment_mix_shares_sum_to_one():
    result = get_segment_mix("2026-07")

    room_share = sum(segment["share_of_room_nights"] for segment in result["segments"])
    revenue_share = sum(segment["share_of_revenue"] for segment in result["segments"])

    assert math.isclose(room_share, 1.0, rel_tol=0.0001)
    assert math.isclose(revenue_share, 1.0, rel_tol=0.0001)


def test_get_segment_mix_macro_group_filter_changes_denominator():
    result = get_segment_mix("2026-07", macro_group="Corporate")

    assert result["macro_group_filter"] == "Corporate"
    assert all(segment["macro_group"] == "Corporate" for segment in result["segments"])

    total_segment_room_nights = sum(segment["room_nights"] for segment in result["segments"])
    assert result["denominator"]["room_nights"] == total_segment_room_nights


def test_get_pickup_delta_uses_create_datetime_window_and_future_stay_filter():
    result = get_pickup_delta(7, "2026-06-15")

    expected = db_value(
        """
        select count(distinct reservation_id)
        from vw_segment_stay_night
        where create_datetime >= %s
          and create_datetime <= %s
          and stay_date >= %s
        """,
        (
            result["window_start_utc"],
            result["window_end_utc"],
            "2026-06-15",
        ),
    )

    assert result["new_reservations"] == expected


def test_get_as_of_otb_excludes_rows_created_after_as_of():
    result = get_as_of_otb("2026-07", "2026-06-01T00:00:00Z")

    expected = db_value(
        """
        select count(*)
        from reservations_hackathon
        where stay_date >= '2026-07-01'
          and stay_date < '2026-08-01'
          and create_datetime <= '2026-06-01T00:00:00Z'
          and (reservation_status <> 'Cancelled' or cancellation_datetime > '2026-06-01T00:00:00Z')
          and financial_status = 'Posted'
        """
    )

    assert result["row_count"] == expected


def test_get_block_vs_transient_mix_shares_are_valid():
    result = get_block_vs_transient_mix("2026-07")

    assert 0 <= result["block_share_of_room_nights"] <= 1
    assert 0 <= result["block_share_of_revenue"] <= 1
    assert 0 <= result["top3_company_revenue_share"] <= 1
    assert len(result["top_companies"]) <= 3


def test_no_tool_accepts_raw_sql_string():
    tools = [
        get_otb_summary,
        get_segment_mix,
        get_pickup_delta,
        get_as_of_otb,
        get_block_vs_transient_mix,
    ]

    for tool in tools:
        signature = inspect.signature(tool)
        assert "query" not in signature.parameters
        assert "sql" not in signature.parameters