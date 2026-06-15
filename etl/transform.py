import json
from pathlib import Path

RAW_DETAILS = Path("etl/raw/reservation_details_raw.json")
OUTPUT_ROWS = Path("etl/raw/reservation_stay_rows.json")


RESERVATION_FIELDS = {
    "arrival_date",
    "departure_date",
    "nights",
    "reservation_status",
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
    "adr_room",
    "lead_time",
    "company_name",
    "travel_agent_name",
}


def clean_value(value):
    value = value.strip()
    if value == "—":
        return None
    return value


def parse_bool(value):
    return str(value).lower() == "true"


def parse_detail(detail):
    lines = [line.strip() for line in detail["text"].splitlines() if line.strip()]

    reservation_id = detail["reservation_id"]
    fields = {"reservation_id": reservation_id}

    try:
        start = lines.index("RESERVATION FIELDS") + 1
        stay_rows_index = next(
            i for i, line in enumerate(lines) if line.startswith("STAY ROWS")
        )
    except StopIteration:
        raise ValueError(f"Could not find STAY ROWS for {reservation_id}")

    field_lines = lines[start:stay_rows_index]

    i = 0
    while i < len(field_lines) - 1:
        key = field_lines[i]
        value = field_lines[i + 1]

        if key in RESERVATION_FIELDS:
            fields[key] = clean_value(value)
            i += 2
        else:
            i += 1

    if "commercial_rate_code" in fields:
        fields.pop("commercial_rate_code", None)

    header_index = stay_rows_index + 1
    stay_data_lines = lines[header_index + 1 :]

    rows = []

    for line in stay_data_lines:
        if line.startswith("Synthetic dataset"):
            break

        parts = line.split()
        if len(parts) != 5:
            continue

        stay_date, property_date, financial_status, room_rev, total_rev = parts

        row = {
            **fields,
            "stay_date": stay_date,
            "property_date": property_date,
            "financial_status": financial_status,
            "daily_room_revenue_before_tax": room_rev,
            "daily_total_revenue_before_tax": total_rev,
        }

        row["is_block"] = parse_bool(row["is_block"])
        row["is_walk_in"] = parse_bool(row["is_walk_in"])
        row["nights"] = int(row["nights"])
        row["number_of_spaces"] = int(row["number_of_spaces"])
        row["lead_time"] = int(row["lead_time"])
        row["adr_room"] = float(row["adr_room"])
        row["daily_room_revenue_before_tax"] = float(row["daily_room_revenue_before_tax"])
        row["daily_total_revenue_before_tax"] = float(row["daily_total_revenue_before_tax"])

        rows.append(row)

    return rows


def main():
    details = json.loads(RAW_DETAILS.read_text())

    all_rows = []
    for detail in details:
        all_rows.extend(parse_detail(detail))

    OUTPUT_ROWS.write_text(json.dumps(all_rows, indent=2))

    print(f"Parsed {len(details)} reservations")
    print(f"Created {len(all_rows)} stay-date rows")
    print(f"Wrote {OUTPUT_ROWS}")


if __name__ == "__main__":
    main()