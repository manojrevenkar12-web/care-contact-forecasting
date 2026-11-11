-- Raw files into typed staging tables. {raw} is the folder of parquet files.
CREATE OR REPLACE TABLE stg_contacts_daily AS
SELECT CAST(day AS DATE) AS day, market, channel, reason, CAST(contacts AS INTEGER) AS contacts
FROM read_parquet('{raw}/contacts_daily.parquet');

CREATE OR REPLACE TABLE stg_contacts_intraday AS
SELECT CAST(day AS DATE) AS day, market, channel, CAST("interval" AS INTEGER) AS slot, CAST(contacts AS INTEGER) AS contacts
FROM read_parquet('{raw}/contacts_intraday.parquet');

CREATE OR REPLACE TABLE stg_orders AS
SELECT CAST(o.day AS DATE) AS day, o.market, o.app, CAST(o.orders AS INTEGER) AS orders, CAST(p.planned_orders AS INTEGER) AS planned_orders
FROM read_parquet('{raw}/orders.parquet') o
JOIN read_parquet('{raw}/order_plan.parquet') p USING (day, market, app);

CREATE OR REPLACE TABLE stg_holidays AS
SELECT market, CAST(day AS DATE) AS day FROM read_parquet('{raw}/holidays.parquet');

CREATE OR REPLACE TABLE stg_campaigns AS
SELECT campaign, CAST(day AS DATE) AS day, CAST(day_of_campaign AS INTEGER) AS day_of_campaign
FROM read_parquet('{raw}/campaigns.parquet');
