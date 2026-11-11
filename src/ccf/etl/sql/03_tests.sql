-- Data tests: each query returns the rows that break a rule; the ETL fails if any does.
-- name: contacts_not_negative
SELECT * FROM mart_contacts WHERE contacts < 0;
-- name: one_row_per_series_and_day
SELECT series, day, COUNT(*) AS n FROM mart_contacts GROUP BY series, day HAVING COUNT(*) > 1;
-- name: every_series_every_day
SELECT series FROM mart_contacts GROUP BY series HAVING COUNT(*) <> (SELECT COUNT(DISTINCT day) FROM mart_contacts);
-- name: plan_for_every_order_day
SELECT * FROM mart_orders WHERE fashion_plan IS NULL OR lounge_plan IS NULL;
-- name: intraday_adds_up_to_daily
SELECT i.day, i.market, i.channel
FROM (SELECT day, market, channel, SUM(contacts) AS n FROM mart_intraday GROUP BY ALL) i
JOIN (SELECT day, market, channel, SUM(contacts) AS n FROM mart_contacts WHERE channel IN ('phone', 'chat') GROUP BY ALL) d
USING (day, market, channel)
WHERE i.n <> d.n;
