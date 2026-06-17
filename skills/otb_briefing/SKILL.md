---
name: otb_briefing
description: Use for on-the-books summaries, monthly revenue questions, GM morning briefings, and questions like "what revenue is on the books?"
---

Use `get_otb_summary` for monthly OTB numbers.

Default assumptions:
- Use posted, non-cancelled reservations unless the user explicitly asks for cancelled, tentative, provisional, or all business.
- Use `stay_date` for monthly OTB.
- Treat `row_count` as stay-date rows, not bookings.
- Treat `reservation_count` as distinct reservations.
- Treat room nights as `sum(number_of_spaces)`.

Answer pattern:
- State the month.
- Give room nights, reservation count, room revenue, total revenue, and ADR if useful.
- Mention the default OTB filters.
- Add one commercial interpretation, not just a metric dump.

Guardrail:
- Never answer OTB from raw SQL.
- Do not count rows as reservations.