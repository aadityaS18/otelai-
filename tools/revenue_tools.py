import os
from datetime import datetime, time, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://hackathon:hackathon@localhost:5432/hotel_hackathon",
)





def _get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return database_url

    try:
        import streamlit as st
        database_url = st.secrets.get("DATABASE_URL", "")
        if database_url:
            return database_url
    except Exception:
        pass

    raise RuntimeError(
        "DATABASE_URL is missing. Add it in Streamlit Cloud secrets."
    )


def _connect():
    return psycopg.connect(_get_database_url())
def _to_float(value):
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return value


def _to_int(value):
    if value is None:
        return 0
    return int(value)


def _month_bounds(stay_month: str):
    start = datetime.strptime(stay_month, "%Y-%m").date()
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def get_otb_summary(stay_month: str, exclude_cancelled: bool = True) -> dict:
    """
    On-the-books summary for a calendar month of stay dates (YYYY-MM).

    Default universe: vw_stay_night_base (Posted, non-cancelled).

    Grain notes:
      - row_count is stay-date row count, not reservation count.
      - reservation_count is count(distinct reservation_id) at the filtered stay-date grain.
      - room_nights is sum(number_of_spaces) at stay-date grain.
      - room_revenue is sum(daily_room_revenue_before_tax) at stay-date grain.
      - total_revenue is sum(daily_total_revenue_before_tax) at stay-date grain.

    Returns:
      - stay_month
      - row_count (stay-date rows)
      - reservation_count (distinct reservation_id)
      - room_nights (sum of number_of_spaces)
      - room_revenue (sum daily_room_revenue_before_tax)
      - total_revenue (sum daily_total_revenue_before_tax)
      - exclude_cancelled (echo input)
    """
    start, end = _month_bounds(stay_month)

    if exclude_cancelled:
        sql = """
            select
                count(*) as row_count,
                count(distinct reservation_id) as reservation_count,
                coalesce(sum(number_of_spaces), 0) as room_nights,
                coalesce(sum(daily_room_revenue_before_tax), 0) as room_revenue,
                coalesce(sum(daily_total_revenue_before_tax), 0) as total_revenue
            from public.vw_stay_night_base
            where stay_date >= %s and stay_date < %s
        """
        params = (start, end)
    else:
        sql = """
            select
                count(*) as row_count,
                count(distinct reservation_id) as reservation_count,
                coalesce(sum(number_of_spaces), 0) as room_nights,
                coalesce(sum(daily_room_revenue_before_tax), 0) as room_revenue,
                coalesce(sum(daily_total_revenue_before_tax), 0) as total_revenue
            from public.reservations_hackathon
            where stay_date >= %s
              and stay_date < %s
              and financial_status = 'Posted'
        """
        params = (start, end)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()

    return {
        "stay_month": stay_month,
        "row_count": _to_int(row[0]),
        "reservation_count": _to_int(row[1]),
        "room_nights": _to_int(row[2]),
        "room_revenue": _to_float(row[3]),
        "total_revenue": _to_float(row[4]),
        "exclude_cancelled": exclude_cancelled,
    }


def get_segment_mix(stay_month: str, macro_group: str | None = None) -> dict:
    """
    Segment mix for a stay month using vw_segment_stay_night.

    Grain notes:
      - room_nights is sum(number_of_spaces) at stay-date grain.
      - total_revenue is sum(daily_total_revenue_before_tax) at stay-date grain.
      - shares use the same filtered population for every segment in the result set.

    Returns a list of segments with:
      - market_code, market_name, macro_group (effective_macro_group)
      - room_nights, total_revenue
      - share_of_room_nights (0-1, denominator = all segments in scope)
      - share_of_revenue (0-1, same denominator)

    If macro_group is set, filter to that effective macro_group only.
    """
    start, end = _month_bounds(stay_month)

    where = "where stay_date >= %s and stay_date < %s"
    params = [start, end]

    if macro_group is not None:
        where += " and effective_macro_group = %s"
        params.append(macro_group)

    sql = f"""
        with segment_rows as (
            select
                market_code,
                market_name,
                effective_macro_group as macro_group,
                coalesce(sum(number_of_spaces), 0) as room_nights,
                coalesce(sum(daily_total_revenue_before_tax), 0) as total_revenue
            from public.vw_segment_stay_night
            {where}
            group by market_code, market_name, effective_macro_group
        ),
        totals as (
            select
                coalesce(sum(room_nights), 0) as total_room_nights,
                coalesce(sum(total_revenue), 0) as total_revenue
            from segment_rows
        )
        select
            s.market_code,
            s.market_name,
            s.macro_group,
            s.room_nights,
            s.total_revenue,
            case when t.total_room_nights = 0 then 0
                 else s.room_nights::numeric / t.total_room_nights end as share_of_room_nights,
            case when t.total_revenue = 0 then 0
                 else s.total_revenue::numeric / t.total_revenue end as share_of_revenue,
            t.total_room_nights,
            t.total_revenue
        from segment_rows s
        cross join totals t
        order by s.total_revenue desc, s.room_nights desc
    """

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    denominator_room_nights = _to_int(rows[0][7]) if rows else 0
    denominator_revenue = _to_float(rows[0][8]) if rows else 0.0

    return {
        "stay_month": stay_month,
        "macro_group_filter": macro_group,
        "denominator": {
            "scope": "all segments after stay_month and macro_group filters",
            "room_nights": denominator_room_nights,
            "total_revenue": denominator_revenue,
        },
        "segments": [
            {
                "market_code": row[0],
                "market_name": row[1],
                "macro_group": row[2],
                "room_nights": _to_int(row[3]),
                "total_revenue": _to_float(row[4]),
                "share_of_room_nights": _to_float(row[5]),
                "share_of_revenue": _to_float(row[6]),
            }
            for row in rows
        ],
    }


def get_pickup_delta(booking_window_days: int, future_stay_from: str) -> dict:
    """
    Booking pace / pickup for future stays.

    Grain notes:
      - new_reservations is count(distinct reservation_id) created in the booking window.
      - new_room_nights is sum(number_of_spaces) for matching stay-date rows.
      - new_total_revenue is sum(daily_total_revenue_before_tax) for matching stay-date rows.
      - by_segment uses the same stay-date grain and revenue definitions.

    booking_window_days: reservations whose create_datetime falls in the window
      [start_of_day_london(now - days), now] converted to UTC.
    future_stay_from: ISO date; only stay_date >= this date.

    Uses create_datetime for the booking window, not stay_date.
    """
    london = ZoneInfo("Europe/London")
    now_utc = datetime.now(timezone.utc)
    now_london = now_utc.astimezone(london)

    start_date_london = now_london.date().fromordinal(
        now_london.date().toordinal() - booking_window_days
    )
    start_london = datetime.combine(start_date_london, time.min, tzinfo=london)
    start_utc = start_london.astimezone(timezone.utc)

    sql_summary = """
        select
            count(distinct reservation_id) as new_reservations,
            coalesce(sum(number_of_spaces), 0) as new_room_nights,
            coalesce(sum(daily_total_revenue_before_tax), 0) as new_total_revenue
        from public.vw_segment_stay_night
        where create_datetime >= %s
          and create_datetime <= %s
          and stay_date >= %s
    """

    sql_segments = """
        select
            market_code,
            market_name,
            effective_macro_group,
            count(distinct reservation_id) as new_reservations,
            coalesce(sum(number_of_spaces), 0) as new_room_nights,
            coalesce(sum(daily_total_revenue_before_tax), 0) as new_total_revenue
        from public.vw_segment_stay_night
        where create_datetime >= %s
          and create_datetime <= %s
          and stay_date >= %s
        group by market_code, market_name, effective_macro_group
        order by new_total_revenue desc
        limit 5
    """

    params = (start_utc, now_utc, future_stay_from)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_summary, params)
            summary = cur.fetchone()

            cur.execute(sql_segments, params)
            segment_rows = cur.fetchall()

    return {
        "booking_window_days": booking_window_days,
        "future_stay_from": future_stay_from,
        "window_start_utc": start_utc.isoformat(),
        "window_end_utc": now_utc.isoformat(),
        "new_reservations": _to_int(summary[0]),
        "new_room_nights": _to_int(summary[1]),
        "new_total_revenue": _to_float(summary[2]),
        "by_segment": [
            {
                "market_code": row[0],
                "market_name": row[1],
                "macro_group": row[2],
                "new_reservations": _to_int(row[3]),
                "new_room_nights": _to_int(row[4]),
                "new_total_revenue": _to_float(row[5]),
            }
            for row in segment_rows
        ],
    }


def get_as_of_otb(stay_month: str, as_of_utc: str) -> dict:
    """
    Point-in-time on-the-books for stay_date month as known at as_of_utc.

    Grain notes:
      - row_count is stay-date row count, not reservation count.
      - reservation_count is count(distinct reservation_id) at the filtered stay-date grain.
      - room_nights is sum(number_of_spaces) at stay-date grain.
      - room_revenue is sum(daily_room_revenue_before_tax) at stay-date grain.
      - total_revenue is sum(daily_total_revenue_before_tax) at stay-date grain.

    Include a stay row when:
      - create_datetime <= as_of_utc
      - and (reservation_status <> 'Cancelled' OR cancellation_datetime > as_of_utc)
      - and financial_status = 'Posted' (provisional excluded)

    Same return shape as get_otb_summary plus as_of_utc echo.
    """
    start, end = _month_bounds(stay_month)

    sql = """
        select
            count(*) as row_count,
            count(distinct reservation_id) as reservation_count,
            coalesce(sum(number_of_spaces), 0) as room_nights,
            coalesce(sum(daily_room_revenue_before_tax), 0) as room_revenue,
            coalesce(sum(daily_total_revenue_before_tax), 0) as total_revenue
        from public.reservations_hackathon
        where stay_date >= %s
          and stay_date < %s
          and create_datetime <= %s
          and (
              reservation_status <> 'Cancelled'
              or cancellation_datetime > %s
          )
          and financial_status = 'Posted'
    """

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (start, end, as_of_utc, as_of_utc))
            row = cur.fetchone()

    return {
        "stay_month": stay_month,
        "as_of_utc": as_of_utc,
        "row_count": _to_int(row[0]),
        "reservation_count": _to_int(row[1]),
        "room_nights": _to_int(row[2]),
        "room_revenue": _to_float(row[3]),
        "total_revenue": _to_float(row[4]),
        "exclude_cancelled": True,
    }


def get_block_vs_transient_mix(stay_month: str) -> dict:
    """
    Block vs transient mix for a stay month (vw_stay_night_base).

    Grain notes:
      - block_room_nights and transient_room_nights are sum(number_of_spaces)
        at stay-date grain.
      - block_total_revenue and transient_total_revenue are sum(daily_total_revenue_before_tax)
        at stay-date grain.
      - top_companies are ranked by total_revenue at stay-date grain.
      - top3_company_revenue_share is top 3 company total revenue divided by month total revenue.

    Returns:
      - block_room_nights, transient_room_nights
      - block_total_revenue, transient_total_revenue
      - block_share_of_room_nights, block_share_of_revenue
      - top_companies: top 3 company_name by total_revenue (null -> 'Transient')
      - top3_company_revenue_share (0-1 of month total revenue)
    """
    start, end = _month_bounds(stay_month)

    sql_mix = """
        select
            coalesce(sum(case when is_block then number_of_spaces else 0 end), 0) as block_room_nights,
            coalesce(sum(case when not is_block then number_of_spaces else 0 end), 0) as transient_room_nights,
            coalesce(sum(case when is_block then daily_total_revenue_before_tax else 0 end), 0) as block_total_revenue,
            coalesce(sum(case when not is_block then daily_total_revenue_before_tax else 0 end), 0) as transient_total_revenue
        from public.vw_stay_night_base
        where stay_date >= %s and stay_date < %s
    """

    sql_companies = """
        select
            coalesce(company_name, 'Transient') as company_name,
            coalesce(sum(daily_total_revenue_before_tax), 0) as total_revenue
        from public.vw_stay_night_base
        where stay_date >= %s and stay_date < %s
        group by coalesce(company_name, 'Transient')
        order by total_revenue desc
        limit 3
    """

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_mix, (start, end))
            mix = cur.fetchone()

            cur.execute(sql_companies, (start, end))
            company_rows = cur.fetchall()

    block_room_nights = _to_int(mix[0])
    transient_room_nights = _to_int(mix[1])
    block_total_revenue = _to_float(mix[2])
    transient_total_revenue = _to_float(mix[3])

    total_room_nights = block_room_nights + transient_room_nights
    total_revenue = block_total_revenue + transient_total_revenue

    top_companies = [
        {
            "company_name": row[0],
            "total_revenue": _to_float(row[1]),
        }
        for row in company_rows
    ]

    top3_revenue = sum(company["total_revenue"] for company in top_companies)

    return {
        "stay_month": stay_month,
        "block_room_nights": block_room_nights,
        "transient_room_nights": transient_room_nights,
        "block_total_revenue": block_total_revenue,
        "transient_total_revenue": transient_total_revenue,
        "block_share_of_room_nights": (
            block_room_nights / total_room_nights if total_room_nights else 0
        ),
        "block_share_of_revenue": (
            block_total_revenue / total_revenue if total_revenue else 0
        ),
        "top_companies": top_companies,
        "top3_company_revenue_share": (
            top3_revenue / total_revenue if total_revenue else 0
        ),
    }