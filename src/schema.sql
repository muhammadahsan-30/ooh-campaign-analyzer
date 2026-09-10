-- OOH Campaign Performance Analyzer — data model
-- Four tables. A placement joins a campaign to a site over a date window;
-- delivery records what that placement actually achieved each day.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS delivery;
DROP TABLE IF EXISTS placements;
DROP TABLE IF EXISTS campaigns;
DROP TABLE IF EXISTS sites;

CREATE TABLE sites (
    site_id            INTEGER PRIMARY KEY,
    city               TEXT    NOT NULL,
    area               TEXT    NOT NULL,
    format             TEXT    NOT NULL CHECK (format IN
                         ('bulletin','transit_shelter','digital_screen','mall_panel')),
    is_digital         INTEGER NOT NULL CHECK (is_digital IN (0,1)),
    width_ft           REAL    NOT NULL,
    height_ft          REAL    NOT NULL,
    daily_traffic      INTEGER NOT NULL,   -- estimated people/vehicles passing per day
    rate_card_monthly  INTEGER NOT NULL    -- published rate card per 4-week period ("monthly"), CAD
);

CREATE TABLE campaigns (
    campaign_id  INTEGER PRIMARY KEY,
    client_name  TEXT NOT NULL,
    industry     TEXT NOT NULL CHECK (industry IN
                   ('FMCG','telecom','QSR','automotive','banking','retail')),
    objective    TEXT NOT NULL CHECK (objective IN ('awareness','product_launch','retail_drive')),
    start_date   TEXT NOT NULL,
    end_date     TEXT NOT NULL,
    budget       INTEGER NOT NULL          -- CAD
);

CREATE TABLE placements (
    placement_id           INTEGER PRIMARY KEY,
    campaign_id            INTEGER NOT NULL REFERENCES campaigns(campaign_id),
    site_id                INTEGER NOT NULL REFERENCES sites(site_id),
    start_date             TEXT    NOT NULL,
    end_date               TEXT    NOT NULL,
    negotiated_rate        INTEGER NOT NULL,  -- per 4-week period, CAD; at or below rate card
    contracted_impressions INTEGER NOT NULL
);

CREATE TABLE delivery (
    delivery_id           INTEGER PRIMARY KEY,
    placement_id          INTEGER NOT NULL REFERENCES placements(placement_id),
    date                  TEXT    NOT NULL,
    estimated_impressions INTEGER NOT NULL,
    verified_impressions  INTEGER NOT NULL,
    downtime_hours        REAL    NOT NULL DEFAULT 0  -- digital sites only
);

CREATE INDEX idx_delivery_placement ON delivery(placement_id);
CREATE INDEX idx_placements_campaign ON placements(campaign_id);
CREATE INDEX idx_placements_site ON placements(site_id);
