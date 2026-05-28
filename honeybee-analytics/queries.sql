-- ============================================================
-- Honeybee Colony Analytics — SQL Queries
-- USDA NASS Data | 13 Northeast States | 2002–2022
-- ============================================================


-- ------------------------------------------------------------
-- QUERY 1: Total colony count by state (all years combined)
-- ------------------------------------------------------------
SELECT
    s.state_name,
    SUM(c.colony_count)    AS total_colonies,
    ROUND(AVG(c.colony_count), 0) AS avg_colonies_per_period
FROM colonies c
JOIN states s ON c.state_id = s.state_id
GROUP BY s.state_name
ORDER BY total_colonies DESC;


-- ------------------------------------------------------------
-- QUERY 2: Year-over-year colony count change per state
-- ------------------------------------------------------------
WITH yearly AS (
    SELECT
        s.state_name,
        c.year,
        AVG(c.colony_count) AS avg_colonies
    FROM colonies c
    JOIN states s ON c.state_id = s.state_id
    GROUP BY s.state_name, c.year
)
SELECT
    state_name,
    year,
    ROUND(avg_colonies, 0) AS avg_colonies,
    ROUND(
        (avg_colonies - LAG(avg_colonies) OVER (PARTITION BY state_name ORDER BY year))
        / NULLIF(LAG(avg_colonies) OVER (PARTITION BY state_name ORDER BY year), 0) * 100,
        2
    ) AS yoy_change_pct
FROM yearly
ORDER BY state_name, year;


-- ------------------------------------------------------------
-- QUERY 3: States with steepest colony decline (2002 vs 2022)
-- ------------------------------------------------------------
WITH base AS (
    SELECT state_id, AVG(colony_count) AS avg_2002
    FROM colonies WHERE year = 2002
    GROUP BY state_id
),
recent AS (
    SELECT state_id, AVG(colony_count) AS avg_2022
    FROM colonies WHERE year = 2022
    GROUP BY state_id
)
SELECT
    s.state_name,
    ROUND(b.avg_2002, 0)  AS colonies_2002,
    ROUND(r.avg_2022, 0)  AS colonies_2022,
    ROUND((r.avg_2022 - b.avg_2002) / NULLIF(b.avg_2002, 0) * 100, 1) AS pct_change
FROM base b
JOIN recent r ON b.state_id = r.state_id
JOIN states s ON b.state_id = s.state_id
ORDER BY pct_change ASC;


-- ------------------------------------------------------------
-- QUERY 4: Average loss rate by quarter (seasonal patterns)
-- ------------------------------------------------------------
SELECT
    quarter,
    CASE quarter
        WHEN 1 THEN 'Q1 (Jan–Mar)'
        WHEN 2 THEN 'Q2 (Apr–Jun)'
        WHEN 3 THEN 'Q3 (Jul–Sep)'
        WHEN 4 THEN 'Q4 (Oct–Dec)'
    END AS season,
    ROUND(AVG(loss_rate_pct), 2) AS avg_loss_rate_pct,
    SUM(colonies_lost)            AS total_colonies_lost
FROM colonies
WHERE quarter IS NOT NULL
GROUP BY quarter
ORDER BY quarter;


-- ------------------------------------------------------------
-- QUERY 5: Total colonies lost per state over all years
-- ------------------------------------------------------------
SELECT
    s.state_name,
    SUM(c.colonies_lost)  AS total_lost,
    SUM(c.colony_count)   AS total_count,
    ROUND(SUM(c.colonies_lost) * 100.0 / NULLIF(SUM(c.colony_count), 0), 2) AS overall_loss_rate_pct
FROM colonies c
JOIN states s ON c.state_id = s.state_id
GROUP BY s.state_name
ORDER BY overall_loss_rate_pct DESC;


-- ------------------------------------------------------------
-- QUERY 6: Renovation trend over time (all states combined)
-- ------------------------------------------------------------
SELECT
    year,
    SUM(colonies_renovated) AS total_renovated,
    SUM(colony_count)       AS total_colonies,
    ROUND(SUM(colonies_renovated) * 100.0 / NULLIF(SUM(colony_count), 0), 2) AS renovation_rate_pct
FROM colonies
GROUP BY year
ORDER BY year;


-- ------------------------------------------------------------
-- QUERY 7: Best and worst years for colony health per state
-- ------------------------------------------------------------
WITH annual AS (
    SELECT
        s.state_name,
        c.year,
        ROUND(AVG(c.loss_rate_pct), 2) AS avg_loss_rate
    FROM colonies c
    JOIN states s ON c.state_id = s.state_id
    WHERE c.loss_rate_pct IS NOT NULL
    GROUP BY s.state_name, c.year
)
SELECT
    state_name,
    MIN(avg_loss_rate) AS best_year_loss_rate,
    MAX(avg_loss_rate) AS worst_year_loss_rate,
    MAX(avg_loss_rate) - MIN(avg_loss_rate) AS loss_rate_range
FROM annual
GROUP BY state_name
ORDER BY worst_year_loss_rate DESC;


-- ------------------------------------------------------------
-- QUERY 8: Regional totals by year (all 13 states combined)
-- ------------------------------------------------------------
SELECT
    year,
    SUM(colony_count)      AS total_colonies,
    SUM(colonies_lost)     AS total_lost,
    SUM(colonies_added)    AS total_added,
    SUM(colonies_renovated) AS total_renovated,
    ROUND(SUM(colonies_lost) * 100.0 / NULLIF(SUM(colony_count), 0), 2) AS regional_loss_rate_pct
FROM colonies
GROUP BY year
ORDER BY year;


-- ------------------------------------------------------------
-- QUERY 9: States where colonies_added > colonies_lost
--          (net positive years)
-- ------------------------------------------------------------
SELECT
    s.state_name,
    c.year,
    SUM(c.colonies_added) AS added,
    SUM(c.colonies_lost)  AS lost,
    SUM(c.colonies_added) - SUM(c.colonies_lost) AS net_change
FROM colonies c
JOIN states s ON c.state_id = s.state_id
GROUP BY s.state_name, c.year
HAVING net_change > 0
ORDER BY net_change DESC;


-- ------------------------------------------------------------
-- QUERY 10: 5-year rolling average colony count per state
-- ------------------------------------------------------------
WITH yearly AS (
    SELECT
        state_id,
        year,
        AVG(colony_count) AS avg_colonies
    FROM colonies
    GROUP BY state_id, year
)
SELECT
    s.state_name,
    y.year,
    ROUND(AVG(y2.avg_colonies), 0) AS rolling_5yr_avg
FROM yearly y
JOIN yearly y2
    ON y.state_id = y2.state_id
    AND y2.year BETWEEN y.year - 4 AND y.year
JOIN states s ON y.state_id = s.state_id
GROUP BY y.state_id, y.year
ORDER BY s.state_name, y.year;


-- ------------------------------------------------------------
-- QUERY 11: Quarter with highest loss rate each year
-- ------------------------------------------------------------
WITH quarterly AS (
    SELECT
        year,
        quarter,
        ROUND(AVG(loss_rate_pct), 2) AS avg_loss_rate,
        RANK() OVER (PARTITION BY year ORDER BY AVG(loss_rate_pct) DESC) AS rnk
    FROM colonies
    WHERE quarter IS NOT NULL AND loss_rate_pct IS NOT NULL
    GROUP BY year, quarter
)
SELECT year, quarter, avg_loss_rate
FROM quarterly
WHERE rnk = 1
ORDER BY year;


-- ------------------------------------------------------------
-- QUERY 12: States ranked by colony recovery rate post-2015
-- ------------------------------------------------------------
SELECT
    s.state_name,
    ROUND(AVG(c.colonies_renovated * 100.0 / NULLIF(c.colony_count, 0)), 2) AS avg_renovation_rate_pct
FROM colonies c
JOIN states s ON c.state_id = s.state_id
WHERE c.year >= 2015
GROUP BY s.state_name
ORDER BY avg_renovation_rate_pct DESC;


-- ------------------------------------------------------------
-- QUERY 13: Correlation proxy — large vs small colony states
--           comparing their loss rates
-- ------------------------------------------------------------
WITH state_size AS (
    SELECT
        state_id,
        AVG(colony_count) AS avg_size,
        CASE WHEN AVG(colony_count) > 10000 THEN 'Large' ELSE 'Small' END AS size_group
    FROM colonies
    GROUP BY state_id
)
SELECT
    ss.size_group,
    ROUND(AVG(c.loss_rate_pct), 2) AS avg_loss_rate_pct,
    COUNT(DISTINCT c.state_id)     AS state_count
FROM colonies c
JOIN state_size ss ON c.state_id = ss.state_id
WHERE c.loss_rate_pct IS NOT NULL
GROUP BY ss.size_group;


-- ------------------------------------------------------------
-- QUERY 14: Peak colony season by state
--           (quarter with highest average colony count)
-- ------------------------------------------------------------
WITH quarterly AS (
    SELECT
        state_id,
        quarter,
        AVG(colony_count) AS avg_colonies,
        RANK() OVER (PARTITION BY state_id ORDER BY AVG(colony_count) DESC) AS rnk
    FROM colonies
    WHERE quarter IS NOT NULL
    GROUP BY state_id, quarter
)
SELECT
    s.state_name,
    q.quarter AS peak_quarter,
    ROUND(q.avg_colonies, 0) AS avg_colonies_at_peak
FROM quarterly q
JOIN states s ON q.state_id = s.state_id
WHERE q.rnk = 1
ORDER BY s.state_name;


-- ------------------------------------------------------------
-- QUERY 15: Summary dashboard — one row per state, all KPIs
-- ------------------------------------------------------------
SELECT
    s.state_name,
    ROUND(AVG(c.colony_count), 0)                                              AS avg_colony_count,
    SUM(c.colonies_lost)                                                        AS total_lost,
    SUM(c.colonies_renovated)                                                   AS total_renovated,
    ROUND(AVG(c.loss_rate_pct), 2)                                             AS avg_loss_rate_pct,
    ROUND(SUM(c.colonies_renovated) * 100.0 / NULLIF(SUM(c.colony_count), 0), 2) AS renovation_rate_pct,
    COUNT(DISTINCT c.year)                                                      AS years_on_record
FROM colonies c
JOIN states s ON c.state_id = s.state_id
GROUP BY s.state_name
ORDER BY avg_colony_count DESC;
