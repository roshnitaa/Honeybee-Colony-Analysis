# Honeybee Colony Data Analytics

A SQL-first data analytics project examining 20 years of USDA bee colony data across 13 Northeast states to identify population decline patterns, seasonal trends, and geographic distribution.

## Project Overview

Bee colony collapse is a well-documented ecological and agricultural crisis. This project uses USDA NASS survey data to quantify colony loss trends across the Northeast from 2002 to 2022, providing a data-driven picture of where and when colony health deteriorated most severely.

## Key Questions Answered

- Which Northeast states have experienced the steepest colony decline over 20 years?
- Are colony losses seasonal, or consistent year-round?
- What is the relationship between colony loss rate and overall population size?
- How have recovery (renovation) efforts trended over time?

## States Analyzed

Connecticut, Delaware, Maine, Maryland, Massachusetts, New Hampshire, New Jersey, New York, Pennsylvania, Rhode Island, Vermont, Virginia, West Virginia

## Tools Used

- **SQL** (SQLite) — schema design, data loading, analytical queries
- **Python** (pandas, matplotlib, seaborn, sqlite3) — data pipeline and visualization
- **Tableau** — interactive dashboard (see `/visuals`)

## Project Structure

```
honeybee-analytics/
├── README.md
├── schema.sql          # Table definitions and ERD notes
├── queries.sql         # 15+ analytical SQL queries
├── honeybee_analysis.py  # Full Python + SQL pipeline
├── requirements.txt
└── visuals/            # Generated charts
```

## Dataset

Uses USDA National Agricultural Statistics Service (NASS) bee colony survey data, publicly available at:
https://usda.library.cornell.edu/concern/publications/rn301137d

Download the colony loss CSV and place it in the project root as `colonies.csv` before running.

Expected columns: `State`, `Year`, `Period`, `Value` (colonies), and loss/renovation metrics.

## How to Run

```bash
pip install -r requirements.txt
python honeybee_analysis.py
```

This will:
1. Build the SQLite database from raw CSV data
2. Execute all analytical queries
3. Print results and save charts to `/visuals`

## Key Findings

- Total Northeast colony counts declined by approximately **30–40%** from 2002 to 2022
- **Winter losses** (Q4–Q1) are consistently the most severe across all states
- **Pennsylvania and New York** hold the largest colony populations but also show the steepest absolute declines
- Colony renovation rates have increased since 2015, suggesting awareness and intervention growth
- States with smaller colony populations show higher **percentage** loss rates, indicating fragility in low-density regions
