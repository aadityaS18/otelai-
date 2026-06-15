# ATTESTATION.md (Phase 0)

Copy this file to your solution repository as `ATTESTATION.md` and fill it in
before starting Phase 1. Keep answers concise — a few sentences per prompt.

---

## Candidate

- Name: AADITYA SHANKAR
- Repository URL:https://github.com/aadityaS18/otelai-
- Date:15 June 2026

---

## Comprehension prompts

### 1. Fact-table grain

In one sentence, what is the grain of `reservations_hackathon`?

> Your answer: reservations_hackthon is one row per reservation_id*stay_date so a multi night reservation has multiple rows

### 2. Revenue columns

Name the two revenue columns and when to use each.

> Your answer: The two revenue columns are daily_room_revenue_before_tax and daily_total_revenue_before_tax.use room revenue for room-only/ADR/OTB room revenue questions, and total revenue when the question asks for broader total value including extras/package effects.

### 3. Row vs reservation

Give one example question where counting rows would be wrong.

> Your answer: Counting rows would be wrong for “How many reservations do we have for July?” because one reservation staying multiple nights creates multiple stay-date rows.

### 4. Schema fields

Is there an `otel_challenge_token` column in the official schema? If so, what is it used for?

> Your answer: No, the official schema does not contain an otel_challenge_token column.

### 5. Default OTB filters

Which `reservation_status` and `financial_status` values are excluded from default OTB?

> Your answer: Default OTB excludes reservation_status = 'Cancelled' and excludes financial_status = 'Provisional'; the default universe is posted, non-cancelled business.

### 6. Stay date vs property date

When can `property_date` differ from `stay_date`, and which field drives monthly OTB?

> Your answer:  property_date can differ from stay_date around hotel night-audit or business-date boundary cases; monthly OTB should be driven by stay_date.

### 7. Point-in-time OTB

How does `as_of_utc` change which cancelled rows are included in `get_as_of_otb`?

> Your answer:  as_of_utc means a cancelled reservation should still be included if it was created before as_of_utc and its cancellation_datetime is after as_of_utc, because at that point in time it was still on the books.

### 8. Block vs transient

How does `is_block` affect a “group vs transient mix” question?
 
> Your answer:  is_block = true identifies block/group-style business, while is_block = false is transient; group vs transient mix should split room nights and revenue using this flag.

### 9. List pagination

How many reservations does the data site show per list page?

> Your answer:   The data site shows 100 reservations per list page.

### 10. Pagination completeness

How will you prove you did not miss the last list page during ETL?

> Your answer:   I will prove completeness by scraping until there is no next page, storing pages_scraped, reservation_ids_count, and a SHA-256 hash of sorted reservation IDs in SCRAPE_MANIFEST.json, then reconciling that count with count(distinct reservation_id) in Postgres and total_reservations on /verify.

### 11. Tool grain

For `get_otb_summary`, what is the difference between `row_count` and `reservation_count`?

> Your answer:   For get_otb_summary, row_count is the number of stay-date rows, while reservation_count is count(distinct reservation_id); they differ when reservations span multiple nights.

### 12. Human-in-the-loop

Why must `get_as_of_otb` be gated behind approval, and what goes wrong if it is not?

> Your answer:  get_as_of_otb should be gated behind approval because point-in-time OTB can be expensive and sensitive to historical cancellation timing; without approval the agent could run broad historical rebuilds accidentally or present a misleading “as-of” view without the user confirming that is what they want.

### 13. Skill vs tool

Name one revenue-manager question that should load a **skill** but call **`get_segment_mix`**, not raw SQL.

> Your answer:  “Are we too dependent on OTA in July?” should load an OTA/channel-dependency revenue-management skill, but call get_segment_mix to get the trusted segment mix numbers instead of raw SQL.

---

## ETL design (one line)

Describe pagination strategy + idempotency approach + **anchor date** you will
scrape against (must match `/verify` on load day).

> Your answer:   I will use Playwright to scrape the client-rendered reservation list page by page at 100 reservations per page until no next page remains, follow each reservation detail page, scrape reference and verify pages for anchor date 2026-06-15, then use an idempotent truncate-and-reload into Postgres and reconcile SCRAPE_MANIFEST.json plus LOAD_PROOF.json against /verify on the same day.
