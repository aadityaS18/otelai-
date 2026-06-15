import json
from pathlib import Path

RAW_REFERENCE = Path("etl/raw/reference_raw.json")
OUTPUT_REFERENCE = Path("etl/raw/reference_tables.json")


def clean(value):
    value = value.strip()
    return None if value == "—" else value


def bool_value(value):
    return value.lower() == "true"


def section_lines(text, table_name):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    start = lines.index(table_name)
    return lines[start:]


def parse_room_types(text):
    lines = section_lines(text, "room_type_lookup")
    rows = []
    for line in lines[2:]:
        if line.startswith("Synthetic dataset"):
            break
        parts = line.split()
        rows.append({
            "space_type": parts[0],
            "room_class": parts[1],
            "display_name": " ".join(parts[2:-1]),
            "number_of_rooms": int(parts[-1]),
        })
    return rows

def parse_markets(text):
    lines = section_lines(text, "market_code_lookup")
    rows = []

    for line in lines[2:]:
        if line.startswith("Synthetic dataset"):
            break

        parts = [part.strip() for part in line.split("\t") if part.strip()]

        if len(parts) != 4:
            raise ValueError(f"Could not parse market line: {line}")

        rows.append({
            "market_code": parts[0],
            "market_name": parts[1],
            "macro_group": parts[2],
            "description": parts[3],
        })

    return rows


def parse_channels(text):
    lines = section_lines(text, "channel_code_lookup")
    rows = []
    known_groups = {"Digital", "Direct", "Offline"}

    for line in lines[2:]:
        if line.startswith("Synthetic dataset"):
            break

        parts = line.split()
        channel_code = parts[0]
        channel_group = parts[-1]

        if channel_group not in known_groups:
            raise ValueError(f"Unknown channel group in line: {line}")

        channel_name = " ".join(parts[1:-1])

        rows.append({
            "channel_code": channel_code,
            "channel_name": channel_name,
            "channel_group": channel_group,
        })

    return rows


def parse_rate_plans(text):
    lines = section_lines(text, "rate_plan_lookup")
    rows = []

    for line in lines[2:]:
        if line.startswith("Synthetic dataset"):
            break

        parts = line.split()

        rows.append({
            "rate_plan_code": parts[0],
            "plan_family": parts[1],
            "is_commissionable": bool_value(parts[2]),
        })

    return rows


def parse_macro_history(text):
    lines = section_lines(text, "market_macro_group_history")
    rows = []

    for line in lines[2:]:
        if line.startswith("Synthetic dataset"):
            break

        parts = line.split()
        rows.append({
            "market_code": parts[0],
            "valid_from": parts[1],
            "valid_to": clean(parts[2]),
            "macro_group": " ".join(parts[3:]),
        })

    return rows


def main():
    raw = json.loads(RAW_REFERENCE.read_text())

    tables = {
        "room_type_lookup": parse_room_types(raw["Room types"]),
        "market_code_lookup": parse_markets(raw["Markets"]),
        "channel_code_lookup": parse_channels(raw["Channels"]),
        "rate_plan_lookup": parse_rate_plans(raw["Rate plans"]),
        "market_macro_group_history": parse_macro_history(raw["Macro history"]),
    }

    OUTPUT_REFERENCE.write_text(json.dumps(tables, indent=2))

    for table, rows in tables.items():
        print(f"{table}: {len(rows)} rows")

    print(f"Wrote {OUTPUT_REFERENCE}")


if __name__ == "__main__":
    main()