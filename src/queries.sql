-- Analytical SQL for the OOH Campaign Performance Analyzer.
-- Each query answers a question an agency actually asks.

-- ============================================================================
-- 1. Spend and delivery by client, ranked.
--    Straightforward aggregate: who are the biggest accounts and what did they get?
-- ============================================================================
WITH placement_totals AS (
    SELECT p.placement_id, p.campaign_id,
           -- negotiated_rate is a four-week (28-day) figure. COUNT(*) is the
           -- number of delivery rows, i.e. the days that have actually run, so
           -- this bills the rate to date and matches metrics.spend_to_date().
           -- Using the contracted flight length instead would over-bill any
           -- campaign still in the air.
           p.negotiated_rate * COUNT(*) / 28.0 AS spend,
           SUM(d.verified_impressions)  AS delivered
    FROM placements p
    JOIN delivery d ON d.placement_id = p.placement_id
    GROUP BY p.placement_id
)
SELECT c.client_name,
       COUNT(DISTINCT pt.campaign_id) AS campaigns,
       COUNT(*)                       AS placements,
       ROUND(SUM(pt.spend))           AS spend,
       SUM(pt.delivered)              AS delivered_impressions
FROM placement_totals pt
JOIN campaigns c ON c.campaign_id = pt.campaign_id
GROUP BY c.client_name
ORDER BY spend DESC;


-- ============================================================================
-- 2. The three worst-delivering sites WITHIN each campaign.
--    Needs a window function. A plain GROUP BY can aggregate per campaign, but
--    it cannot rank rows inside each group and then keep only the top few --
--    that requires ROW_NUMBER() OVER (PARTITION BY ...).
-- ============================================================================
WITH placement_delivery AS (
    SELECT p.placement_id, p.campaign_id, p.site_id, p.contracted_impressions,
           -- contracted_impressions covers the whole flight. COUNT(*) is the
           -- days that have actually run, so prorating by it is what lets a
           -- campaign still in the air be judged fairly -- otherwise a healthy
           -- placement three weeks into a twelve-week flight reads as -75%.
           -- Same basis as metrics.delivery_vs_contract().
           p.contracted_impressions * COUNT(*)
               / (julianday(p.end_date) - julianday(p.start_date)) AS contracted_to_date,
           SUM(d.verified_impressions) AS delivered
    FROM placements p
    JOIN delivery d ON d.placement_id = p.placement_id
    GROUP BY p.placement_id
),
scored AS (
    SELECT pd.*,
           ROUND((pd.delivered - pd.contracted_to_date) * 100.0
                 / pd.contracted_to_date, 1) AS variance_pct,
           ROW_NUMBER() OVER (
               PARTITION BY pd.campaign_id
               ORDER BY (pd.delivered - pd.contracted_to_date) * 1.0
                        / pd.contracted_to_date
           ) AS rank_in_campaign
    FROM placement_delivery pd
)
SELECT c.client_name, s.campaign_id, s.site_id, si.city, si.format,
       ROUND(s.contracted_to_date) AS contracted_to_date,
       s.contracted_impressions AS contracted_full_flight,
       s.delivered, s.variance_pct
FROM scored s
JOIN campaigns c ON c.campaign_id = s.campaign_id
JOIN sites si    ON si.site_id    = s.site_id
WHERE s.rank_in_campaign <= 3
ORDER BY s.campaign_id, s.rank_in_campaign;


-- ============================================================================
-- 3. Running cumulative spend by campaign over time.
--    SUM(...) OVER (PARTITION BY ... ORDER BY ...) gives a running total while
--    keeping every underlying row visible.
-- ============================================================================
WITH daily AS (
    SELECT p.campaign_id, d.date,
           -- negotiated_rate / 28 is the daily rate. Summed over the days that
           -- ran, this is the same basis used in query 1 and metrics.py.
           SUM(p.negotiated_rate / 28.0) AS day_spend
    FROM delivery d
    JOIN placements p ON p.placement_id = d.placement_id
    GROUP BY p.campaign_id, d.date
)
SELECT campaign_id, date, ROUND(day_spend) AS day_spend,
       ROUND(SUM(day_spend) OVER (PARTITION BY campaign_id ORDER BY date)) AS cumulative_spend
FROM daily
ORDER BY campaign_id, date;


-- ============================================================================
-- 4. CPM by site format -- which inventory type is actually efficient?
-- ============================================================================
WITH pt AS (
    SELECT p.placement_id, p.site_id,
           -- prorate the four-week (28-day) rate to the days that ran (query 1)
           p.negotiated_rate * COUNT(*) / 28.0 AS spend,
           SUM(d.verified_impressions) AS delivered
    FROM placements p
    JOIN delivery d ON d.placement_id = p.placement_id
    GROUP BY p.placement_id
)
SELECT s.format,
       COUNT(*)                  AS placements,
       ROUND(SUM(pt.spend))      AS spend,
       SUM(pt.delivered)         AS delivered,
       ROUND(SUM(pt.spend) * 1000.0 / SUM(pt.delivered), 2) AS cpm
FROM pt
JOIN sites s ON s.site_id = pt.site_id
GROUP BY s.format
ORDER BY cpm ASC;


-- ============================================================================
-- 5. Sites used by more than one campaign, with their average delivery rate.
--    Answers "which inventory actually performs when we rebook it?"
-- ============================================================================
WITH pt AS (
    SELECT p.site_id, p.campaign_id,
           -- prorated to the days that ran, as in query 2
           p.contracted_impressions * COUNT(*)
               / (julianday(p.end_date) - julianday(p.start_date)) AS contracted_to_date,
           SUM(d.verified_impressions) AS delivered
    FROM placements p
    JOIN delivery d ON d.placement_id = p.placement_id
    GROUP BY p.placement_id
)
SELECT s.site_id, s.city, s.format,
       COUNT(DISTINCT pt.campaign_id) AS campaigns_booked,
       ROUND(AVG(pt.delivered * 100.0 / pt.contracted_to_date), 1) AS avg_delivery_pct
FROM pt
JOIN sites s ON s.site_id = pt.site_id
GROUP BY s.site_id
HAVING campaigns_booked > 1
ORDER BY avg_delivery_pct ASC
LIMIT 20;


-- ============================================================================
-- 6. Month-over-month change in delivered impressions per client.
--    LAG() reaches back to the previous row in the partition, which is how you
--    compare a period against the one before it without a self-join.
-- ============================================================================
WITH monthly AS (
    SELECT c.client_name,
           substr(d.date, 1, 7) AS month,
           SUM(d.verified_impressions) AS delivered
    FROM delivery d
    JOIN placements p ON p.placement_id = d.placement_id
    JOIN campaigns  c ON c.campaign_id  = p.campaign_id
    GROUP BY c.client_name, month
)
SELECT client_name, month, delivered,
       LAG(delivered) OVER (PARTITION BY client_name ORDER BY month) AS prev_month,
       ROUND((delivered - LAG(delivered) OVER (PARTITION BY client_name ORDER BY month))
             * 100.0 / LAG(delivered) OVER (PARTITION BY client_name ORDER BY month), 1)
             AS mom_change_pct
FROM monthly
ORDER BY client_name, month;
