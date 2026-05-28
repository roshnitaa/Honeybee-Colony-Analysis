-- ============================================================
-- Honeybee Colony Database Schema
-- USDA NASS Bee Colony Data — 13 Northeast States, 2002–2022
-- ============================================================
-- Entity-Relationship Summary:
--   states (1) ──< colonies (many)
--   colonies tracks colony counts, losses, and renovations
--   per state, year, and quarter
-- ============================================================


-- States reference table
CREATE TABLE IF NOT EXISTS states (
    state_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    state_name  TEXT    NOT NULL UNIQUE,
    region      TEXT    NOT NULL DEFAULT 'Northeast',
    abbrev      TEXT    NOT NULL UNIQUE
);

-- Core colony metrics table
-- One row per state + year + period combination
CREATE TABLE IF NOT EXISTS colonies (
    colony_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    state_id            INTEGER NOT NULL REFERENCES states(state_id),
    year                INTEGER NOT NULL,
    period              TEXT    NOT NULL,   -- e.g. 'JAN THRU MAR', 'APR THRU JUN'
    quarter             INTEGER,            -- 1, 2, 3, or 4
    colony_count        INTEGER,            -- total colonies at start of period
    colonies_lost       INTEGER,            -- colonies lost during period
    colonies_added      INTEGER,            -- new colonies added
    colonies_renovated  INTEGER,            -- colonies renovated/restored
    loss_rate_pct       REAL,               -- percent lost (colonies_lost / colony_count)
    UNIQUE(state_id, year, period)
);

-- Pre-computed yearly aggregates (populated by Python pipeline)
CREATE TABLE IF NOT EXISTS yearly_summary (
    summary_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    state_id            INTEGER NOT NULL REFERENCES states(state_id),
    year                INTEGER NOT NULL,
    avg_colony_count    REAL,
    total_lost          INTEGER,
    total_added         INTEGER,
    total_renovated     INTEGER,
    annual_loss_rate    REAL,
    yoy_change_pct      REAL,               -- year-over-year % change in colony count
    UNIQUE(state_id, year)
);


-- ============================================================
-- Seed states table
-- ============================================================

INSERT OR IGNORE INTO states (state_name, abbrev) VALUES
    ('Connecticut',     'CT'),
    ('Delaware',        'DE'),
    ('Maine',           'ME'),
    ('Maryland',        'MD'),
    ('Massachusetts',   'MA'),
    ('New Hampshire',   'NH'),
    ('New Jersey',      'NJ'),
    ('New York',        'NY'),
    ('Pennsylvania',    'PA'),
    ('Rhode Island',    'RI'),
    ('Vermont',         'VT'),
    ('Virginia',        'VA'),
    ('West Virginia',   'WV');
