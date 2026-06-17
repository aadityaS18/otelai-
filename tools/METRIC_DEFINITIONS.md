# Metric Definitions

`reservations_hackathon` is stay-date grain: one row represents one reservation on one `stay_date`. A stay row is not the same as a reservation. `reservation_count` means `count(distinct reservation_id)`. Room nights mean `sum(number_of_spaces)` at stay-date grain, so a 2-room booking for 3 nights is 6 room nights.

Default on-the-books (OTB) uses stay dates and excludes `reservation_status = 'Cancelled'` and `financial_status = 'Provisional'`. The default anchor is the currently loaded dataset, with OTB months grouped by `stay_date`.

Pickup windows use `create_datetime`, not `stay_date`. The `booking_window_days` boundary starts at Europe/London local midnight for `now - days`, then is converted to UTC for comparison because `create_datetime` is stored as UTC.

`effective_macro_group` comes from `market_macro_group_history` joined by `stay_date` over `[valid_from, valid_to)`. This can differ from the static `market_code_lookup.macro_group`, for example when a market code is reclassified over time.