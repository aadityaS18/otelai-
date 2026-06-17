---
name: pickup_pace
description: Use for pickup, booking pace, recent booking changes, and questions like "what changed in the last 7 days?"
---

Use `get_pickup_delta`.

Rules:
- Pickup uses `create_datetime`, not `stay_date`.
- `future_stay_from` filters the stay dates included in the pickup result.
- Booking window boundaries use Europe/London local midnight, converted to UTC for comparison.
- Use posted, non-cancelled OTB unless the question explicitly asks for provisional or cancelled business.

Interpretation:
- Separate "booked recently" from "staying recently".
- Highlight top contributing segments by revenue.
- If pickup is heavily group/block-led, mention concentration risk.
- If pickup is mostly OTA-led, evaluate whether it is helpful base demand or dependency risk.

Recommended action:
- Strong pickup in high-rated segments: protect rate and avoid unnecessary discounts.
- Weak pickup for near-term stays: consider targeted direct offers or controlled OTA visibility.
- Pickup concentrated in one segment/company: monitor cancellation and displacement risk.