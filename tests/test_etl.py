import json
import os
from pathlib import Path

import psycopg


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://hackathon:hackathon@localhost:5432/hotel_hackathon",
)


def test_scrape_manifest_reservation_count_matches_ids_file():
    manifest = json.loads(Path("etl/SCRAPE_MANIFEST.json").read_text())
    ids = json.loads(Path("etl/raw/reservation_ids.json").read_text())

    assert manifest["reservation_ids_count"] == len(ids)
    assert manifest["reservation_ids_count"] == len(set(ids))


def test_parsed_rows_use_stay_date_grain():
    rows = json.loads(Path("etl/raw/reservation_stay_rows.json").read_text())
    reservations = {row["reservation_id"] for row in rows}

    assert len(rows) > len(reservations)
    assert len(reservations) == 254


def test_database_counts_match_parsed_files():
    rows = json.loads(Path("etl/raw/reservation_stay_rows.json").read_text())

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select count(*), count(distinct reservation_id)
                from reservations_hackathon
                """
            )
            stay_rows, reservations = cur.fetchone()

    assert stay_rows == len(rows)
    assert reservations == len({row["reservation_id"] for row in rows})


def test_room_nights_are_sum_of_number_of_spaces_not_row_count():
    rows = json.loads(Path("etl/raw/reservation_stay_rows.json").read_text())
    room_nights = sum(row["number_of_spaces"] for row in rows)

    assert room_nights >= len(rows)
    assert any(row["number_of_spaces"] > 1 for row in rows)