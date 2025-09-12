-- Populate dim_date if empty. Safe to re-run (ON CONFLICT DO NOTHING).
INSERT INTO dw.dim_date (
    date_key,
    full_date,
    year,
    quarter,
    month,
    month_name,
    day,
    day_of_week,
    day_name,
    week_of_year,
    is_weekend
)
SELECT
    EXTRACT(YEAR FROM d)::int * 10000
    + EXTRACT(MONTH FROM d)::int * 100
    + EXTRACT(DAY FROM d)::int AS date_key,
    d AS full_date,
    EXTRACT(YEAR FROM d)::int AS year,
    EXTRACT(QUARTER FROM d)::smallint AS quarter,
    EXTRACT(MONTH FROM d)::smallint AS month,
    TO_CHAR(d, 'Mon') AS month_name,
    EXTRACT(DAY FROM d)::smallint AS day,
    EXTRACT(ISODOW FROM d)::smallint AS day_of_week,
    TO_CHAR(d, 'Dy') AS day_name,
    EXTRACT(WEEK FROM d)::smallint AS week_of_year,
    (EXTRACT(ISODOW FROM d) IN (6, 7)) AS is_weekend
FROM GENERATE_SERIES('2018-01-01'::date, '2030-12-31', '1 day') AS d
ON CONFLICT DO NOTHING;
