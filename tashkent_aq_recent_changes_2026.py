"""Tashkent Air Quality — Recent Changes Assessment (Jan–Mar 2026).

Extracts Sentinel-5P (NO2, SO2, CO, O3, Aerosol Index) and CAMS NRT (PM2.5)
data for six target dates over the Tashkent AOI and produces:
  1. A summary CSV table with pollutant values per date
  2. A multi-panel line+bar chart (PNG) showing change across dates
  3. A console summary with percentage changes

Target dates (2026):
  15 Jan · 23 Jan · 29 Jan · 7 Feb · 17 Feb · 1 Mar

AOI: Tashkent city center (41.2995°N, 69.2401°E) with ~30 km buffer
      to capture urban + peri-urban area visible in the satellite image.

Usage:
    python tashkent_aq_recent_changes_2026.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import ee
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from services.gee import initialize_gee
from services.utils import UZBEKISTAN_CITIES, GEE_CONFIG

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TARGET_DATES = [
    "2026-01-15",
    "2026-01-23",
    "2026-01-29",
    "2026-02-07",
    "2026-02-17",
    "2026-03-01",
]

# How many days around each target date to search for imagery (±)
SEARCH_WINDOW_DAYS = 2

TASHKENT = UZBEKISTAN_CITIES["Tashkent"]
CENTER_LON = TASHKENT["lon"]  # 69.2401
CENTER_LAT = TASHKENT["lat"]  # 41.2995
BUFFER_M = 30_000  # 30 km radius — covers the satellite image extent

# Pollutant definitions — use BOTH OFFL and NRTI for best coverage near real-time
POLLUTANTS = {
    "NO2": {
        "datasets": [
            "COPERNICUS/S5P/OFFL/L3_NO2",
            "COPERNICUS/S5P/NRTI/L3_NO2",
        ],
        "band": "tropospheric_NO2_column_number_density",
        "factor": 1e6,
        "units": "µmol/m²",
        "scale": 7000,
        "color": "#d62728",
    },
    "SO2": {
        "datasets": [
            "COPERNICUS/S5P/OFFL/L3_SO2",
            "COPERNICUS/S5P/NRTI/L3_SO2",
        ],
        "band": "SO2_column_number_density",
        "factor": 1e6,
        "units": "µmol/m²",
        "scale": 7000,
        "color": "#1f77b4",
    },
    "CO": {
        "datasets": [
            "COPERNICUS/S5P/OFFL/L3_CO",
            "COPERNICUS/S5P/NRTI/L3_CO",
        ],
        "band": "CO_column_number_density",
        "factor": 1e3,
        "units": "mmol/m²",
        "scale": 7000,
        "color": "#ff7f0e",
    },
    "O3": {
        "datasets": [
            "COPERNICUS/S5P/OFFL/L3_O3",
            "COPERNICUS/S5P/NRTI/L3_O3",
        ],
        "band": "O3_column_number_density",
        "factor": 1e3,
        "units": "mmol/m²",
        "scale": 7000,
        "color": "#9467bd",
    },
    "AER_AI": {
        "datasets": [
            "COPERNICUS/S5P/OFFL/L3_AER_AI",
            "COPERNICUS/S5P/NRTI/L3_AER_AI",
        ],
        "band": "absorbing_aerosol_index",
        "factor": 1,
        "units": "index",
        "scale": 7000,
        "color": "#8c564b",
    },
    "PM2.5": {
        "datasets": [
            "ECMWF/CAMS/NRT",
        ],
        "band": "particulate_matter_d_less_than_25_um_surface",
        "factor": 1e9,          # kg/m³ → µg/m³
        "units": "µg/m³",
        "scale": 11000,          # CAMS ~11 km resolution
        "color": "#2ca02c",
    },
}

OUTPUT_DIR = Path("tashkent_air_quality_rasters")

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def make_aoi(lon: float, lat: float, buffer_m: int) -> ee.Geometry:
    """Return a buffered point geometry."""
    return ee.Geometry.Point([lon, lat]).buffer(buffer_m)


def get_collection_for_date(
    datasets: List[str],
    band: str,
    target_date: str,
    aoi: ee.Geometry,
    window_days: int = SEARCH_WINDOW_DAYS,
) -> ee.ImageCollection:
    """Get merged collection from multiple dataset IDs within a date window."""
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    start = (dt - timedelta(days=window_days)).strftime("%Y-%m-%d")
    end = (dt + timedelta(days=window_days + 1)).strftime("%Y-%m-%d")  # +1 for inclusive end

    merged = None
    for ds in datasets:
        col = (
            ee.ImageCollection(ds)
            .filterDate(start, end)
            .filterBounds(aoi)
            .select(band)
        )
        merged = col if merged is None else merged.merge(col)
    return merged


def extract_stats(image: ee.Image, aoi: ee.Geometry, band: str, scale: int) -> Dict[str, Any]:
    """Reduce image to mean/std/min/max/count over the AOI."""
    reducer = (
        ee.Reducer.mean()
        .combine(ee.Reducer.stdDev(), sharedInputs=True)
        .combine(ee.Reducer.minMax(), sharedInputs=True)
        .combine(ee.Reducer.count(), sharedInputs=True)
    )
    stats = image.reduceRegion(
        reducer=reducer,
        geometry=aoi,
        scale=scale,
        maxPixels=GEE_CONFIG["max_pixels"],
        bestEffort=True,
    ).getInfo()

    # Flatten band-prefixed keys
    result = {}
    for key, val in stats.items():
        short = key.replace(f"{band}_", "").replace(band, "mean") if "_" not in key.replace(band, "") else key.split("_")[-1]
        # Robust key extraction
        if "mean" in key:
            result["mean"] = val
        elif "stdDev" in key:
            result["std"] = val
        elif "_min" in key:
            result["min"] = val
        elif "_max" in key:
            result["max"] = val
        elif "count" in key:
            result["count"] = val

    # Fallback: if "mean" key not found, try the band name itself
    if "mean" not in result and band in stats:
        result["mean"] = stats[band]

    return result


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def run_analysis():
    """Run the full analysis for all dates and pollutants."""
    print("=" * 70)
    print("  TASHKENT AIR QUALITY — RECENT CHANGES (Jan–Mar 2026)")
    print("=" * 70)

    # Initialize GEE
    print("\n🔑 Initializing Google Earth Engine...")
    ok = initialize_gee()
    if not ok:
        print("❌ GEE initialization failed.")
        return None
    print("   ✅ GEE ready\n")

    aoi = make_aoi(CENTER_LON, CENTER_LAT, BUFFER_M)

    # Results table: rows = dates, columns = pollutants
    rows = []

    for date_str in TARGET_DATES:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        label = dt.strftime("%d %b %Y")
        print(f"📅 {label}")
        row = {"date": date_str, "label": label}

        for poll_name, cfg in POLLUTANTS.items():
            try:
                col = get_collection_for_date(
                    cfg["datasets"], cfg["band"], date_str, aoi
                )
                n_images = col.size().getInfo()

                if n_images == 0:
                    print(f"   {poll_name:8s}: ⚠️  no imagery in ±{SEARCH_WINDOW_DAYS}-day window")
                    row[f"{poll_name}_raw"] = None
                    row[f"{poll_name}"] = None
                    row[f"{poll_name}_std"] = None
                    row[f"{poll_name}_count"] = None
                    row[f"{poll_name}_n_images"] = 0
                    continue

                composite = col.mean()
                stats = extract_stats(composite, aoi, cfg["band"], cfg["scale"])

                mean_raw = stats.get("mean")
                if mean_raw is not None:
                    value = mean_raw * cfg["factor"]
                    std_val = (stats.get("std") or 0) * cfg["factor"]
                    print(
                        f"   {poll_name:8s}: {value:12.4f} {cfg['units']}"
                        f"  (±{std_val:.4f}, n_img={n_images}, pixels={stats.get('count', '?')})"
                    )
                else:
                    value = None
                    std_val = None
                    print(f"   {poll_name:8s}: ⚠️  reducer returned None (n_img={n_images})")

                row[f"{poll_name}_raw"] = mean_raw
                row[f"{poll_name}"] = value
                row[f"{poll_name}_std"] = std_val
                row[f"{poll_name}_count"] = stats.get("count")
                row[f"{poll_name}_n_images"] = n_images

            except Exception as exc:
                print(f"   {poll_name:8s}: ❌ {exc}")
                row[f"{poll_name}_raw"] = None
                row[f"{poll_name}"] = None
                row[f"{poll_name}_std"] = None
                row[f"{poll_name}_count"] = None
                row[f"{poll_name}_n_images"] = 0

        rows.append(row)
        print()

    df = pd.DataFrame(rows)
    return df


def compute_changes(df: pd.DataFrame) -> pd.DataFrame:
    """Compute absolute and percentage change vs. first valid observation."""
    poll_names = list(POLLUTANTS.keys())
    change_rows = []
    for _, r in df.iterrows():
        cr = {"date": r["date"], "label": r["label"]}
        for p in poll_names:
            cr[p] = r[p]
        change_rows.append(cr)

    cdf = pd.DataFrame(change_rows)

    for p in poll_names:
        first_valid = cdf[p].dropna().iloc[0] if cdf[p].dropna().shape[0] > 0 else None
        if first_valid and first_valid != 0:
            cdf[f"{p}_pct_chg"] = ((cdf[p] - first_valid) / abs(first_valid)) * 100
        else:
            cdf[f"{p}_pct_chg"] = None

    return cdf


def create_visualization(df: pd.DataFrame, change_df: pd.DataFrame):
    """Create a multi-panel chart showing pollutant trends across the target dates."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    poll_names = [p for p in POLLUTANTS if df[p].notna().any()]
    n = len(poll_names)
    if n == 0:
        print("⚠️  No valid data to plot.")
        return

    fig, axes = plt.subplots(n, 1, figsize=(13, 3.5 * n), sharex=True)
    if n == 1:
        axes = [axes]

    dates = pd.to_datetime(df["date"])

    for i, p in enumerate(poll_names):
        ax = axes[i]
        cfg = POLLUTANTS[p]
        vals = df[p].values.astype(float)
        mask = ~np.isnan(vals)

        if mask.sum() == 0:
            ax.text(0.5, 0.5, f"No {p} data", transform=ax.transAxes, ha="center", va="center")
            continue

        # Bar chart background
        ax.bar(dates[mask], vals[mask], width=2.5, alpha=0.30, color=cfg["color"], zorder=2)
        # Line + markers
        ax.plot(dates[mask], vals[mask], "o-", color=cfg["color"], lw=2, markersize=8, zorder=3)

        # Value annotations
        for d, v in zip(dates[mask], vals[mask]):
            ax.annotate(
                f"{v:.3f}" if abs(v) < 100 else f"{v:.1f}",
                (d, v),
                textcoords="offset points",
                xytext=(0, 12),
                ha="center",
                fontsize=8,
                fontweight="bold",
            )

        # Percent-change annotation (vs first date)
        pct_col = f"{p}_pct_chg"
        if pct_col in change_df.columns:
            for idx_j in range(len(change_df)):
                pct = change_df[pct_col].iloc[idx_j]
                val_j = df[p].iloc[idx_j]
                if pd.notna(pct) and pd.notna(val_j) and idx_j > 0:
                    sign = "+" if pct > 0 else ""
                    ax.annotate(
                        f"{sign}{pct:.1f}%",
                        (dates.iloc[idx_j], val_j),
                        textcoords="offset points",
                        xytext=(0, -16),
                        ha="center",
                        fontsize=7,
                        color="gray",
                    )

        ax.set_ylabel(f"{p}\n({cfg['units']})", fontsize=11)
        ax.set_title(f"{p} over Tashkent AOI", fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))

    axes[-1].set_xlabel("Date (2026)", fontsize=11)
    fig.suptitle(
        "Tashkent Air Quality — Recent Changes (Jan–Mar 2026)\n"
        "Sentinel-5P (NO₂, SO₂, CO, O₃, Aerosol AI) · CAMS NRT (PM₂.₅)",
        fontsize=14,
        fontweight="bold",
        y=1.01,
    )
    plt.tight_layout()

    out_png = OUTPUT_DIR / "tashkent_aq_recent_changes_2026.png"
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"📊 Chart saved → {out_png}")
    return out_png


def save_results(df: pd.DataFrame, change_df: pd.DataFrame):
    """Save CSV tables."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = OUTPUT_DIR / "tashkent_aq_recent_changes_2026.csv"
    df.to_csv(csv_path, index=False)
    print(f"💾 Full data  → {csv_path}")

    chg_csv = OUTPUT_DIR / "tashkent_aq_recent_changes_2026_pct.csv"
    change_df.to_csv(chg_csv, index=False)
    print(f"💾 Changes    → {chg_csv}")


def print_summary(change_df: pd.DataFrame):
    """Print a concise console summary."""
    poll_names = list(POLLUTANTS.keys())
    print("\n" + "=" * 70)
    print("  SUMMARY — % Change vs First Observation (15 Jan 2026)")
    print("=" * 70)

    header = f"{'Date':>12s}"
    for p in poll_names:
        header += f"  {p:>10s}"
    print(header)
    print("-" * len(header))

    for _, r in change_df.iterrows():
        line = f"{r['label']:>12s}"
        for p in poll_names:
            pct_col = f"{p}_pct_chg"
            val = r.get(pct_col)
            if pd.isna(val) if isinstance(val, float) else val is None:
                line += f"  {'N/A':>10s}"
            else:
                sign = "+" if val > 0 else ""
                line += f"  {sign}{val:>8.1f}%"
        print(line)

    # Overall direction
    print("\n📌 Key observations:")
    for p in poll_names:
        pct_col = f"{p}_pct_chg"
        if pct_col not in change_df.columns:
            continue
        series = change_df[pct_col].dropna()
        if series.shape[0] < 2:
            continue
        last_pct = series.iloc[-1]
        cfg = POLLUTANTS[p]
        direction = "↑ increased" if last_pct > 5 else "↓ decreased" if last_pct < -5 else "→ stable"
        first_val = change_df[p].dropna().iloc[0]
        last_val = change_df[p].dropna().iloc[-1]
        print(
            f"   {p:8s}: {direction} from {first_val:.4f} to {last_val:.4f} {cfg['units']}"
            f"  ({'+' if last_pct > 0 else ''}{last_pct:.1f}%)"
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    df = run_analysis()
    if df is None or df.empty:
        print("❌ No results obtained.")
        return 1

    change_df = compute_changes(df)
    save_results(df, change_df)
    create_visualization(df, change_df)
    print_summary(change_df)

    print("\n✅ Analysis complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
