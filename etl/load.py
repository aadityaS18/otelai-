import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://hackathon:hackathon@localhost:5432/hotel_hackathon",
)

REFERENCE_PATH = Path("etl/raw/reference_tables.json")
STAY_ROWS_PATH = Path("etl/raw/reservation_stay_rows.json")
SCRAPE_MANIFEST_PATH = Path("etl/SCRAPE_MANIFEST.json")


def load_json(path):
    return json.loads(path.read_text())


def insert_many(cur, table, columns, rows):
    if not rows:
        return

    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(columns)

    sql = f"""
        INSERT INTO {table} ({column_sql})
        VALUES ({placeholders})
    """

    values = [tuple(row[col] for col in columns) for row in rows]
    cur.executemany(sql, values)

def enrich_rate_plan_lookup(reference, stay_rows):
    existing = {row["rate_plan_code"] for row in reference["rate_plan_lookup"]}
    missing = sorted({row["rate_plan_code"] for row in stay_rows} - existing)

    def infer_family(code):
        if "GROUP" in code:
            return "Group"
        if "CORP" in code:
            return "Corporate"
        return "Retail"

    for code in missing:
        reference["rate_plan_lookup"].append({
            "rate_plan_code": code,
            "plan_family": infer_family(code),
            "is_commissionable": code.startswith(("BOOK", "EXP", "OCH", "GOO")),
        })

    if missing:
        print("Added missing rate plan lookup codes:", missing)



def main():
    reference = load_json(REFERENCE_PATH)
    stay_rows = load_json(STAY_ROWS_PATH)
    manifest = load_json(SCRAPE_MANIFEST_PATH)
    enrich_rate_plan_lookup(reference, stay_rows)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Idempotent reload: remove fact rows first, then lookup tables.
            cur.execute("TRUNCATE TABLE public.reservations_hackathon RESTART IDENTITY CASCADE")
            cur.execute("TRUNCATE TABLE public.market_macro_group_history CASCADE")
            cur.execute("TRUNCATE TABLE public.room_type_lookup CASCADE")
            cur.execute("TRUNCATE TABLE public.rate_plan_lookup CASCADE")
            cur.execute("TRUNCATE TABLE public.market_code_lookup CASCADE")
            cur.execute("TRUNCATE TABLE public.channel_code_lookup CASCADE")

            insert_many(
                cur,
                "public.room_type_lookup",
                ["space_type", "room_class", "display_name", "number_of_rooms"],
                reference["room_type_lookup"],
            )

            insert_many(
                cur,
                "public.rate_plan_lookup",
                ["rate_plan_code", "plan_family", "is_commissionable"],
                reference["rate_plan_lookup"],
            )

            insert_many(
                cur,
                "public.market_code_lookup",
                ["market_code", "market_name", "macro_group", "description"],
                reference["market_code_lookup"],
            )

            insert_many(
                cur,
                "public.channel_code_lookup",
                ["channel_code", "channel_name", "channel_group"],
                reference["channel_code_lookup"],
            )

            insert_many(
                cur,
                "public.market_macro_group_history",
                ["market_code", "valid_from", "valid_to", "macro_group"],
                reference["market_macro_group_history"],
            )

            insert_many(
                cur,
                "public.reservations_hackathon",
                [
                    "reservation_id",
                    "arrival_date",
                    "departure_date",
                    "stay_date",
                    "property_date",
                    "reservation_status",
                    "financial_status",
                    "create_datetime",
                    "cancellation_datetime",
                    "guest_country",
                    "is_block",
                    "is_walk_in",
                    "number_of_spaces",
                    "space_type",
                    "market_code",
                    "channel_code",
                    "source_name",
                    "rate_plan_code",
                    "daily_room_revenue_before_tax",
                    "daily_total_revenue_before_tax",
                    "nights",
                    "adr_room",
                    "lead_time",
                    "company_name",
                    "travel_agent_name",
                ],
                stay_rows,
            )

            cur.execute(
                """
                INSERT INTO public.load_manifest
                    (dataset_revision, scraped_at, source_url, row_hash)
                VALUES
                    (%s, %s, %s, %s)
                """,
                (
                    manifest["anchor_date"],
                    datetime.now(timezone.utc),
                    manifest["source_url"],
                    manifest["reservation_ids_sha256"],
                ),
            )

        conn.commit()

    print("Loaded reference tables and reservations into Postgres.")
    print(f"Loaded stay rows: {len(stay_rows)}")


if __name__ == "__main__":
    main()