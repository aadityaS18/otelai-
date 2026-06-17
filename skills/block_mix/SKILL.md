---
name: block_mix
description: Use for group vs transient mix, block business, company concentration, and questions like "how much group business do we have?"
---

Use `get_block_vs_transient_mix`.

Rules:
- Block/group business is identified by `is_block = true`.
- Transient business is `is_block = false`.
- Use room nights and total revenue at stay-date grain.
- Top company concentration should be reviewed using top company revenue share.

Judgment thresholds:
- Block revenue share under 25%: mostly transient-led.
- 25% to 45%: balanced mix.
- 45% to 65%: group-heavy; review displacement risk.
- Above 65%: high concentration risk.

Recommended actions:
- If block share is high on high-demand dates, check whether it displaces higher-rated transient demand.
- If block share provides base demand in weak periods, keep it but protect remaining inventory.
- If top 3 company revenue share is high, flag concentration and cancellation risk.