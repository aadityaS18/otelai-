---
name: ota_dependency
description: Use for OTA dependency, channel exposure, retail mix risk, and questions like "are we too dependent on OTA?"
---

Use `get_segment_mix` to retrieve trusted segment mix numbers. Do not use raw SQL.

Judgment thresholds:
- OTA room-night share under 25%: healthy.
- OTA room-night share from 25% to 40%: monitor.
- OTA room-night share from 40% to 55%: dependency risk.
- OTA room-night share above 55%: urgent dependency risk.

Recommended actions:
- If OTA share is high and lower-rated than direct or corporate business, protect high-demand dates and reduce OTA exposure.
- If OTA is filling weak periods without displacing higher-rated demand, keep it open but cap discount depth.
- If direct share is weak, recommend brand-web offers, email campaigns, and direct booking incentives.
- If OTA is concentrated in a single future month, flag it as a tactical rather than structural risk.

Final answer must include:
- OTA share of room nights and revenue.
- Risk level using the thresholds above.
- Driver explanation.
- Recommended commercial action.