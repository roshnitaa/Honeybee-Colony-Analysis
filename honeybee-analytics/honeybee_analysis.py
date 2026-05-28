"""
Honeybee Colony Data Analytics
================================
Analyzes USDA NASS annual bee colony inventory data across
8 Northeast states from 2002 to 2022 to identify population
trends, decline patterns, and geographic distribution.

Data source: USDA National Agricultural Statistics Service (NASS)
https://quickstats.nass.usda.gov
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import sqlite3
import os
import warnings

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid", palette="muted")
os.makedirs("visuals", exist_ok=True)

DB_PATH = "honeybee.db"

NORTHEAST_STATES = [
    "MAINE", "MARYLAND", "NEW JERSEY", "NEW YORK",
    "PENNSYLVANIA", "VERMONT", "VIRGINIA", "WEST VIRGINIA"
]

STATE_LABELS = {s: s.title() for s in NORTHEAST_STATES}


# =============================================================================
# 1. LOAD & CLEAN DATA
# =============================================================================

def load_data(csv_path: str = "colonies.csv") -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # Filter to Northeast states
    df = df[df["State"].isin(NORTHEAST_STATES)].copy()

    # Clean numeric value (remove commas, convert)
    df["colony_count"] = pd.to_numeric(
        df["Value"].str.replace(",", "").str.strip(), errors="coerce"
    )

    # Drop suppressed/missing values
    df = df.dropna(subset=["colony_count"])

    # Friendly state names
    df["state_name"] = df["State"].map(STATE_LABELS)

    # Keep only needed columns
    df = df[["Year", "state_name", "colony_count"]].rename(columns={"Year": "year"})

    print(f"Loaded {len(df):,} records across {df['state_name'].nunique()} states "
          f"({df['year'].min()}–{df['year'].max()})")
    return df


# =============================================================================
# 2. BUILD SQLITE DATABASE & RUN QUERIES
# =============================================================================

def build_database(df: pd.DataFrame) -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("colonies", conn, if_exists="replace", index=False)
    print(f"Database built: {len(df):,} rows loaded into {DB_PATH}")
    return conn


def run_queries(conn: sqlite3.Connection) -> dict:
    results = {}

    # Q1: Average colony count by state
    results["by_state"] = pd.read_sql("""
        SELECT state_name,
               ROUND(AVG(colony_count), 0) AS avg_colonies,
               SUM(colony_count)           AS total_colonies,
               MIN(colony_count)           AS min_colonies,
               MAX(colony_count)           AS max_colonies
        FROM colonies
        GROUP BY state_name
        ORDER BY avg_colonies DESC
    """, conn)

    # Q2: Regional total by year
    results["by_year"] = pd.read_sql("""
        SELECT year,
               SUM(colony_count)   AS total_colonies,
               ROUND(AVG(colony_count), 0) AS avg_per_state
        FROM colonies
        GROUP BY year
        ORDER BY year
    """, conn)

    # Q3: Year-over-year change per state
    results["yoy"] = pd.read_sql("""
        WITH base AS (
            SELECT state_name, year, colony_count,
                   LAG(colony_count) OVER (
                       PARTITION BY state_name ORDER BY year
                   ) AS prev_year
            FROM colonies
        )
        SELECT state_name, year, colony_count, prev_year,
               ROUND((colony_count - prev_year) * 100.0
                     / NULLIF(prev_year, 0), 1) AS yoy_change_pct
        FROM base
        WHERE prev_year IS NOT NULL
        ORDER BY state_name, year
    """, conn)

    # Q4: Steepest decline — 2002 vs 2022
    results["decline"] = pd.read_sql("""
        WITH y2002 AS (
            SELECT state_name, colony_count AS colonies_2002
            FROM colonies WHERE year = 2002
        ),
        y2022 AS (
            SELECT state_name, colony_count AS colonies_2022
            FROM colonies WHERE year = 2022
        )
        SELECT a.state_name,
               a.colonies_2002,
               b.colonies_2022,
               ROUND((b.colonies_2022 - a.colonies_2002) * 100.0
                     / NULLIF(a.colonies_2002, 0), 1) AS pct_change
        FROM y2002 a JOIN y2022 b ON a.state_name = b.state_name
        ORDER BY pct_change ASC
    """, conn)

    # Q5: Best and worst years per state
    results["best_worst"] = pd.read_sql("""
        SELECT state_name,
               MIN(colony_count) AS lowest_count,
               MAX(colony_count) AS highest_count,
               MAX(colony_count) - MIN(colony_count) AS range_colonies
        FROM colonies
        GROUP BY state_name
        ORDER BY range_colonies DESC
    """, conn)

    # Q6: States ranked by average colony count each decade
    results["by_decade"] = pd.read_sql("""
        SELECT state_name,
               ROUND(AVG(CASE WHEN year BETWEEN 2002 AND 2011
                              THEN colony_count END), 0) AS avg_2002_2011,
               ROUND(AVG(CASE WHEN year BETWEEN 2012 AND 2022
                              THEN colony_count END), 0) AS avg_2012_2022
        FROM colonies
        GROUP BY state_name
        ORDER BY avg_2002_2011 DESC
    """, conn)

    # Q7: Years where each state hit its peak
    results["peak_years"] = pd.read_sql("""
        SELECT c.state_name, c.year AS peak_year, c.colony_count AS peak_count
        FROM colonies c
        INNER JOIN (
            SELECT state_name, MAX(colony_count) AS max_count
            FROM colonies GROUP BY state_name
        ) m ON c.state_name = m.state_name
           AND c.colony_count = m.max_count
        ORDER BY peak_count DESC
    """, conn)

    # Q8: Regional 5-year rolling average
    results["rolling"] = pd.read_sql("""
        SELECT year,
               SUM(colony_count) AS total,
               ROUND(AVG(SUM(colony_count)) OVER (
                   ORDER BY year ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
               ), 0) AS rolling_5yr_avg
        FROM colonies
        GROUP BY year
        ORDER BY year
    """, conn)

    # Q9: States consistently above regional average
    results["above_avg"] = pd.read_sql("""
        WITH reg_avg AS (
            SELECT year, AVG(colony_count) AS regional_avg
            FROM colonies GROUP BY year
        )
        SELECT c.state_name,
               COUNT(*) AS years_above_avg
        FROM colonies c
        JOIN reg_avg r ON c.year = r.year
        WHERE c.colony_count > r.regional_avg
        GROUP BY c.state_name
        ORDER BY years_above_avg DESC
    """, conn)

    # Q10: Largest single-year drops per state
    results["biggest_drops"] = pd.read_sql("""
        WITH yoy AS (
            SELECT state_name, year, colony_count,
                   LAG(colony_count) OVER (
                       PARTITION BY state_name ORDER BY year
                   ) AS prev_year
            FROM colonies
        )
        SELECT state_name, year,
               colony_count, prev_year,
               colony_count - prev_year AS absolute_change,
               ROUND((colony_count - prev_year) * 100.0
                     / NULLIF(prev_year, 0), 1) AS pct_change
        FROM yoy
        WHERE prev_year IS NOT NULL
        ORDER BY pct_change ASC
        LIMIT 10
    """, conn)

    return results


# =============================================================================
# 3. VISUALIZATIONS
# =============================================================================

def plot_results(df: pd.DataFrame, results: dict) -> None:

    # --- Chart 1: Regional colony trend with rolling average ---
    df_yr = results["by_year"]
    df_r  = results["rolling"]
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(df_yr["year"], df_yr["total_colonies"] / 1000,
           color=sns.color_palette("muted")[0], alpha=0.6, label="Total colonies")
    ax.plot(df_r["year"], df_r["rolling_5yr_avg"] / 1000,
            color="darkblue", linewidth=2, marker="o", markersize=4,
            label="5-year rolling avg")
    ax.set_title("Total Bee Colony Count — 8 Northeast States (2002–2022)",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Year")
    ax.set_ylabel("Colonies (thousands)")
    ax.legend()
    ax.xaxis.set_major_locator(mticker.MultipleLocator(2))
    plt.tight_layout()
    plt.savefig("visuals/colony_trend.png", dpi=150)
    plt.close()
    print("Saved: visuals/colony_trend.png")

    # --- Chart 2: Colony count by state over time (line chart) ---
    fig, ax = plt.subplots(figsize=(13, 6))
    for state, group in df.groupby("state_name"):
        group = group.sort_values("year")
        ax.plot(group["year"], group["colony_count"] / 1000,
                marker="o", markersize=3, linewidth=1.5, label=state)
    ax.set_title("Bee Colony Count by State (2002–2022)",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Year")
    ax.set_ylabel("Colonies (thousands)")
    ax.legend(fontsize=8, loc="upper right")
    ax.xaxis.set_major_locator(mticker.MultipleLocator(2))
    plt.tight_layout()
    plt.savefig("visuals/colonies_by_state.png", dpi=150)
    plt.close()
    print("Saved: visuals/colonies_by_state.png")

    # --- Chart 3: % change 2002 vs 2022 by state ---
    df_d = results["decline"].dropna(subset=["pct_change"])
    colors = ["#d9534f" if v < 0 else "#5cb85c" for v in df_d["pct_change"]]
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(df_d["state_name"], df_d["pct_change"],
                   color=colors, alpha=0.85)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_title("Colony Count Change by State: 2002 vs 2022",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("% Change")
    for bar, val in zip(bars, df_d["pct_change"]):
        offset = 1 if val >= 0 else -1
        ax.text(val + offset, bar.get_y() + bar.get_height() / 2,
                f"{val:+.1f}%", va="center", fontsize=9)
    plt.tight_layout()
    plt.savefig("visuals/state_decline.png", dpi=150)
    plt.close()
    print("Saved: visuals/state_decline.png")

    # --- Chart 4: Average colonies by state (bar) ---
    df_s = results["by_state"].sort_values("avg_colonies", ascending=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(df_s["state_name"], df_s["avg_colonies"] / 1000,
            color=sns.color_palette("muted")[1], alpha=0.85)
    ax.set_title("Average Colony Count by State (2002–2022)",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Average Colonies (thousands)")
    plt.tight_layout()
    plt.savefig("visuals/avg_by_state.png", dpi=150)
    plt.close()
    print("Saved: visuals/avg_by_state.png")

    # --- Chart 5: Decade comparison per state ---
    df_dec = results["by_decade"]
    x = np.arange(len(df_dec))
    width = 0.35
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(x - width/2, df_dec["avg_2002_2011"] / 1000, width,
           label="2002–2011", color=sns.color_palette("muted")[0], alpha=0.85)
    ax.bar(x + width/2, df_dec["avg_2012_2022"] / 1000, width,
           label="2012–2022", color=sns.color_palette("muted")[1], alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(df_dec["state_name"], rotation=25, ha="right")
    ax.set_title("Average Colony Count: First vs Second Decade",
                 fontsize=14, fontweight="bold")
    ax.set_ylabel("Avg Colonies (thousands)")
    ax.legend()
    plt.tight_layout()
    plt.savefig("visuals/decade_comparison.png", dpi=150)
    plt.close()
    print("Saved: visuals/decade_comparison.png")


# =============================================================================
# 4. PRINT SUMMARY
# =============================================================================

def print_summary(results: dict) -> None:
    print("\n" + "=" * 60)
    print("ANALYSIS SUMMARY")
    print("=" * 60)

    df_yr = results["by_year"]
    start = df_yr[df_yr["year"] == 2002]["total_colonies"].values[0]
    end   = df_yr[df_yr["year"] == 2022]["total_colonies"].values[0]
    pct   = (end - start) / start * 100
    print(f"\nRegional colony change (2002–2022): {pct:+.1f}%")

    df_d = results["decline"].dropna(subset=["pct_change"])
    if not df_d.empty:
        worst = df_d.iloc[0]
        best  = df_d.iloc[-1]
        print(f"Steepest decline:  {worst['state_name']} ({worst['pct_change']:+.1f}%)")
        print(f"Strongest growth:  {best['state_name']}  ({best['pct_change']:+.1f}%)")

    print("\nPeak colony years by state:")
    for _, row in results["peak_years"].iterrows():
        print(f"  {row['state_name']:<15} {int(row['peak_year'])}  "
              f"({int(row['peak_count']):,} colonies)")

    print("\nTop 5 single-year drops:")
    for _, row in results["biggest_drops"].head(5).iterrows():
        print(f"  {row['state_name']:<15} {int(row['year'])}  "
              f"{row['pct_change']:+.1f}%")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=== Honeybee Colony Analytics Pipeline ===\n")

    df   = load_data("colonies.csv")
    conn = build_database(df)

    print("\nRunning analytical queries...")
    results = run_queries(conn)

    print("\nGenerating visualizations...")
    plot_results(df, results)

    print_summary(results)
    conn.close()
    print("\nDone. Charts saved to /visuals.")
