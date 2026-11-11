-- The marts every model and report reads.

-- One row per market and day: what is known in advance about that day.
CREATE OR REPLACE TABLE dim_calendar AS
WITH days AS (SELECT DISTINCT day, market FROM stg_orders)
SELECT
    d.day,
    d.market,
    isodow(d.day) - 1 AS weekday,                       -- 0 = Monday
    dayofyear(d.day) AS day_of_year,
    h.day IS NOT NULL AS is_holiday,
    COALESCE(lag_h.is_after_holiday, FALSE) AS is_after_holiday,
    c.campaign,
    c.day_of_campaign
FROM days d
LEFT JOIN stg_holidays h ON h.market = d.market AND h.day = d.day
LEFT JOIN (
    SELECT market, day + INTERVAL 1 DAY AS day, TRUE AS is_after_holiday FROM stg_holidays
) lag_h ON lag_h.market = d.market AND CAST(lag_h.day AS DATE) = d.day
LEFT JOIN stg_campaigns c ON c.day = d.day;

-- Orders per market and day, actual and planned, both apps.
CREATE OR REPLACE TABLE mart_orders AS
SELECT
    day,
    market,
    SUM(orders) FILTER (WHERE app = 'fashion') AS fashion_orders,
    SUM(orders) FILTER (WHERE app = 'lounge') AS lounge_orders,
    SUM(planned_orders) FILTER (WHERE app = 'fashion') AS fashion_plan,
    SUM(planned_orders) FILTER (WHERE app = 'lounge') AS lounge_plan
FROM stg_orders
GROUP BY day, market;

-- The forecast grain: market x channel x reason per day.
CREATE OR REPLACE TABLE mart_contacts AS
SELECT
    market || '|' || channel || '|' || reason AS series,
    day, market, channel, reason, contacts
FROM stg_contacts_daily;

-- The intraday grain: market x channel per half hour, with the day's share in each slot.
CREATE OR REPLACE TABLE mart_intraday AS
SELECT
    day, market, channel, slot, contacts,
    contacts / NULLIF(SUM(contacts) OVER (PARTITION BY day, market, channel), 0) AS share_of_day
FROM stg_contacts_intraday;
