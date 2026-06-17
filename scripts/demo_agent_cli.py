from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.revenue_tools import (
    get_otb_summary,
    get_segment_mix,
    get_pickup_delta,
    get_block_vs_transient_mix,
)


DEFAULT_STAY_MONTH = "2026-07"
DEFAULT_FUTURE_STAY_FROM = "2026-06-15"


def answer_question(question: str) -> str:
    q = question.lower()

    if "pickup" in q or "pace" in q or "last 7" in q:
        result = get_pickup_delta(
            booking_window_days=7,
            future_stay_from=DEFAULT_FUTURE_STAY_FROM,
        )
        return (
            f"Pickup in the last 7 days is {result['new_room_nights']} room nights "
            f"from {result['new_reservations']} new reservations, worth "
            f"{result['new_total_revenue']} in total revenue.\n\n"
            "Main driver: recent demand is concentrated in the top booking segments shown by the pickup tool.\n"
            "Opportunity: review which segments are contributing most before adjusting pricing or restrictions.\n"
            f"Assumption: future stays from {DEFAULT_FUTURE_STAY_FROM}, based on create_datetime pickup."
        )

    if "segment" in q or "ota" in q or "mix" in q:
        result = get_segment_mix(stay_month=DEFAULT_STAY_MONTH)
        top = result["segments"][0]
        return (
            f"For July 2026, the largest segment is {top['market_code']} "
            f"({top['market_name']}) with {top['room_nights']} room nights "
            f"and {top['total_revenue']} total revenue.\n\n"
            f"Driver: this segment represents {top['share_of_room_nights']:.1%} of room nights "
            f"and {top['share_of_revenue']:.1%} of revenue.\n"
            "Risk/opportunity: check whether the mix is balanced or overly dependent on one channel or segment.\n"
            "Assumption: posted, non-cancelled reservations only."
        )

    if "block" in q or "transient" in q or "company" in q:
        result = get_block_vs_transient_mix(stay_month=DEFAULT_STAY_MONTH)
        return (
            f"For July 2026, block business has {result['block_room_nights']} room nights "
            f"versus {result['transient_room_nights']} transient room nights.\n\n"
            f"Block revenue is {result['block_total_revenue']}, while transient revenue is "
            f"{result['transient_total_revenue']}.\n"
            f"Risk/opportunity: block contributes {result['block_share_of_room_nights']:.1%} of room nights, "
            "so review company concentration and displacement risk.\n"
            "Assumption: posted, non-cancelled reservations only."
        )

    result = get_otb_summary(stay_month=DEFAULT_STAY_MONTH)
    return (
        f"July 2026 OTB is {result['room_nights']} room nights from "
        f"{result['reservation_count']} reservations, with {result['room_revenue']} room revenue "
        f"and {result['total_revenue']} total revenue.\n\n"
        "Driver: this is the current booked position for the stay month.\n"
        "Next action: compare this against pickup pace and segment mix before making rate decisions.\n"
        "Assumption: posted, non-cancelled reservations only."
    )


def main():
    print("Revenue Manager Agent demo")
    print("Ask a question, or type 'exit'.\n")

    while True:
        question = input("You: ").strip()

        if question.lower() in {"exit", "quit"}:
            print("Agent: Done.")
            break

        print("\nAgent:")
        print(answer_question(question))
        print()


if __name__ == "__main__":
    main()