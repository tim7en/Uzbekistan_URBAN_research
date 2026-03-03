"""Tashkent AQ — Per-date deep dive for 6 key dates (Jan–Mar 2026).

For each date:
  1. ERA5-Land daily wind direction/speed for the 7 preceding days
  2. Pollutant spatial grids (NO2, CO, PM2.5)
  3. North-half vs South-half concentrations
  4. NW (KZ-side) vs SE quadrant concentrations
  5. Week-over-week trend

Outputs:
  - tashkent_air_quality_rasters/tashkent_aq_date_deep_dive.png  (multi-panel)
  - tashkent_air_quality_rasters/tashkent_aq_date_deep_dive.csv  (tabular)
  - Console narrative for each date
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import ee
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from services.gee import initialize_gee
from services.utils import UZBEKISTAN_CITIES

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# The 6 dates of interest
FOCUS_DATES = [
    "2026-01-15",
    "2026-01-23",
    "2026-01-29",
    "2026-02-07",
    "2026-02-17",
    "2026-03-01",
]
FOCUS_LABELS = ["15 Jan", "23 Jan", "29 Jan", "7 Feb", "17 Feb", "1 Mar"]

# How many days of wind history before each date
WIND_LOOKBACK_DAYS = 7

CENTER_LON = 69.2401
CENTER_LAT = 41.2995
MAP_HALF_DEG = 0.42

WEST  = CENTER_LON - MAP_HALF_DEG
EAST  = CENTER_LON + MAP_HALF_DEG
SOUTH = CENTER_LAT - MAP_HALF_DEG
NORTH = CENTER_LAT + MAP_HALF_DEG

# Pollutant configs
POLLUTANTS = {
    "NO2": {
        "datasets": ["COPERNICUS/S5P/OFFL/L3_NO2", "COPERNICUS/S5P/NRTI/L3_NO2"],
        "band": "tropospheric_NO2_column_number_density",
        "factor": 1e6,
        "units": "µmol/m²",
        "scale": 7000,
        "label": "NO₂",
    },
    "CO": {
        "datasets": ["COPERNICUS/S5P/OFFL/L3_CO", "COPERNICUS/S5P/NRTI/L3_CO"],
        "band": "CO_column_number_density",
        "factor": 1e3,
        "units": "mmol/m²",
        "scale": 7000,
        "label": "CO",
    },
    "PM25": {
        "datasets": ["ECMWF/CAMS/NRT"],
        "band": "particulate_matter_d_less_than_25_um_surface",
        "factor": 1e9,
        "units": "µg/m³",
        "scale": 11000,
        "label": "PM₂.₅",
    },
}

ERA5_DATASET = "ECMWF/ERA5_LAND/HOURLY"
ERA5_U_BAND = "u_component_of_wind_10m"
ERA5_V_BAND = "v_component_of_wind_10m"

OUTPUT_DIR = Path("tashkent_air_quality_rasters")

# Cardinal direction labels for wind
WIND_DIRS_16 = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]

def deg_to_cardinal(deg: float) -> str:
    idx = int((deg + 11.25) / 22.5) % 16
    return WIND_DIRS_16[idx]


# ---------------------------------------------------------------------------
# GEE helpers
# ---------------------------------------------------------------------------

def get_daily_wind(date_str: str, aoi: ee.Geometry) -> Optional[Dict]:
    """Get mean wind for a single day from ERA5-Land."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    start = dt.strftime("%Y-%m-%d")
    end = (dt + timedelta(days=1)).strftime("%Y-%m-%d")

    col = (
        ee.ImageCollection(ERA5_DATASET)
        .filterDate(start, end)
        .filterBounds(aoi)
        .select([ERA5_U_BAND, ERA5_V_BAND])
    )
    n = col.size().getInfo()
    if n == 0:
        return None

    mean_img = col.mean()
    # Reduce to single point at Tashkent center
    point = ee.Geometry.Point([CENTER_LON, CENTER_LAT])
    result = mean_img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=point.buffer(15000),  # 15 km buffer
        scale=11000,
        maxPixels=1e6,
    ).getInfo()

    u = result.get(ERA5_U_BAND)
    v = result.get(ERA5_V_BAND)
    if u is None or v is None:
        return None

    speed = np.sqrt(u**2 + v**2)
    # Meteorological direction: where wind comes FROM
    direction = (270 - np.degrees(np.arctan2(v, u))) % 360
    return {"u": u, "v": v, "speed": round(speed, 2), "direction": round(direction, 1)}


def get_pollutant_grid(
    poll_name: str, target_date: str, aoi: ee.Geometry
) -> Optional[Dict]:
    """Extract pollutant grid + compute N/S and NW/SE stats."""
    cfg = POLLUTANTS[poll_name]
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    start = (dt - timedelta(days=2)).strftime("%Y-%m-%d")
    end = (dt + timedelta(days=3)).strftime("%Y-%m-%d")

    merged = None
    for ds in cfg["datasets"]:
        col = (
            ee.ImageCollection(ds)
            .filterDate(start, end)
            .filterBounds(aoi)
            .select(cfg["band"])
        )
        merged = col if merged is None else merged.merge(col)

    n_imgs = merged.size().getInfo()
    if n_imgs == 0:
        return None

    image = merged.mean()

    # Extract grid via sampleRectangle
    rect = ee.Geometry.Rectangle([WEST, SOUTH, EAST, NORTH])
    proj = ee.Projection("EPSG:4326").atScale(cfg["scale"])
    img_repr = image.select(cfg["band"]).reproject(crs=proj)

    try:
        arr_dict = img_repr.sampleRectangle(
            region=rect, defaultValue=-9999
        ).getInfo()
    except Exception:
        coarser = cfg["scale"] * 2
        proj = ee.Projection("EPSG:4326").atScale(coarser)
        img_repr = image.select(cfg["band"]).reproject(crs=proj)
        arr_dict = img_repr.sampleRectangle(
            region=rect, defaultValue=-9999
        ).getInfo()

    props = arr_dict.get("properties", {})
    raw = props.get(cfg["band"])
    if raw is None:
        return None

    grid = np.array(raw, dtype=float) * cfg["factor"]
    grid[grid <= -9999 * cfg["factor"] * 0.9] = np.nan
    grid = np.flipud(grid)

    nr, nc = grid.shape
    lats = np.linspace(SOUTH, NORTH, nr)
    lons = np.linspace(WEST, EAST, nc)

    valid = grid[~np.isnan(grid)]
    if len(valid) == 0:
        return None

    mid_row = nr // 2
    mid_col = nc // 2

    north_half = grid[mid_row:, :]
    south_half = grid[:mid_row, :]
    nw_quarter = grid[mid_row:, :mid_col]
    se_quarter = grid[:mid_row, mid_col:]
    ne_quarter = grid[mid_row:, mid_col:]
    sw_quarter = grid[:mid_row, :mid_col]

    def safe_mean(a):
        v = a[~np.isnan(a)]
        return float(np.mean(v)) if len(v) > 0 else np.nan

    return {
        "grid": grid,
        "lats": lats,
        "lons": lons,
        "mean": round(safe_mean(grid), 2),
        "max": round(float(np.nanmax(grid)), 2),
        "min": round(float(np.nanmin(grid)), 2),
        "north_mean": round(safe_mean(north_half), 2),
        "south_mean": round(safe_mean(south_half), 2),
        "nw_mean": round(safe_mean(nw_quarter), 2),
        "se_mean": round(safe_mean(se_quarter), 2),
        "ne_mean": round(safe_mean(ne_quarter), 2),
        "sw_mean": round(safe_mean(sw_quarter), 2),
        "ns_ratio": round(safe_mean(north_half) / safe_mean(south_half), 2)
            if safe_mean(south_half) > 0 else np.nan,
        "nw_se_ratio": round(safe_mean(nw_quarter) / safe_mean(se_quarter), 2)
            if safe_mean(se_quarter) > 0 else np.nan,
        "n_valid": int(len(valid)),
    }


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def main():
    initialize_gee()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    aoi = ee.Geometry.Point([CENTER_LON, CENTER_LAT]).buffer(30000)

    # ===================================================================
    # 1. Extract 7-day wind history before each focus date
    # ===================================================================
    print("\n" + "=" * 70)
    print("  EXTRACTING 7-DAY WIND HISTORY BEFORE EACH DATE")
    print("=" * 70)

    wind_history = {}  # date_str → list of daily wind dicts
    for focus_date, label in zip(FOCUS_DATES, FOCUS_LABELS):
        dt = datetime.strptime(focus_date, "%Y-%m-%d")
        print(f"\n📅 {label} ({focus_date}) — wind for preceding 7 days:")
        daily_winds = []
        for day_offset in range(WIND_LOOKBACK_DAYS, 0, -1):
            day = dt - timedelta(days=day_offset)
            day_str = day.strftime("%Y-%m-%d")
            w = get_daily_wind(day_str, aoi)
            if w:
                cardinal = deg_to_cardinal(w["direction"])
                print(f"   {day.strftime('%d %b')}: {w['speed']:.1f} m/s from {cardinal} ({w['direction']:.0f}°)")
                daily_winds.append({
                    "date": day_str,
                    "day_label": day.strftime("%d %b"),
                    **w,
                    "cardinal": cardinal,
                })
            else:
                print(f"   {day.strftime('%d %b')}: no data")
                daily_winds.append({"date": day_str, "day_label": day.strftime("%d %b"),
                                    "speed": np.nan, "direction": np.nan,
                                    "u": np.nan, "v": np.nan, "cardinal": "N/A"})
        wind_history[focus_date] = daily_winds

    # ===================================================================
    # 2. Extract pollution grids for each focus date
    # ===================================================================
    print("\n" + "=" * 70)
    print("  EXTRACTING POLLUTANT SPATIAL GRIDS")
    print("=" * 70)

    poll_data = {}  # focus_date → {poll_name → stats dict}
    for focus_date, label in zip(FOCUS_DATES, FOCUS_LABELS):
        print(f"\n📅 {label} ({focus_date}):")
        poll_data[focus_date] = {}
        for poll_name, cfg in POLLUTANTS.items():
            print(f"   {cfg['label']}...", end=" ", flush=True)
            result = get_pollutant_grid(poll_name, focus_date, aoi)
            if result:
                print(f"✅ mean={result['mean']}, N/S={result['ns_ratio']}, "
                      f"N={result['north_mean']}, S={result['south_mean']}")
                poll_data[focus_date][poll_name] = result
            else:
                print("⚠️ no data")

    # ===================================================================
    # 3. Console narrative for each date
    # ===================================================================
    print("\n" + "=" * 70)
    print("  PER-DATE NARRATIVE")
    print("=" * 70)

    for focus_date, label in zip(FOCUS_DATES, FOCUS_LABELS):
        print(f"\n{'─' * 70}")
        print(f"  📅 {label} ({focus_date})")
        print(f"{'─' * 70}")

        # Wind narrative
        winds = wind_history[focus_date]
        valid_winds = [w for w in winds if not np.isnan(w.get("speed", np.nan))]
        if valid_winds:
            avg_speed = np.mean([w["speed"] for w in valid_winds])
            # Dominant direction via vector mean
            u_avg = np.mean([w["u"] for w in valid_winds])
            v_avg = np.mean([w["v"] for w in valid_winds])
            avg_dir = (270 - np.degrees(np.arctan2(v_avg, u_avg))) % 360
            avg_cardinal = deg_to_cardinal(avg_dir)

            # Count days with north-component wind (from 315-45° = KZ side)
            kz_days = sum(1 for w in valid_winds
                         if w["direction"] <= 90 or w["direction"] >= 270)
            # Count days with NE-E wind (from 0-120° ≈ steppe/KZ)
            ne_e_days = sum(1 for w in valid_winds
                          if 0 <= w["direction"] <= 120)

            print(f"\n  🌬️  WIND (preceding 7 days):")
            print(f"     Average: {avg_speed:.1f} m/s from {avg_cardinal} ({avg_dir:.0f}°)")
            print(f"     Days with wind from north/KZ sector (270°-90°): {kz_days}/{len(valid_winds)}")
            print(f"     Days with wind from NE-E (0°-120° = steppe): {ne_e_days}/{len(valid_winds)}")
            print(f"     Day-by-day:")
            for w in winds:
                if not np.isnan(w.get("speed", np.nan)):
                    print(f"       {w['day_label']}: {w['speed']:.1f} m/s from {w['cardinal']} ({w['direction']:.0f}°)")
                else:
                    print(f"       {w['day_label']}: no data")

            # Assess advection potential
            max_wind = max(w["speed"] for w in valid_winds)
            if ne_e_days >= 4 and avg_speed >= 0.8:
                print(f"     ⚠️  STRONG KZ-side advection potential (NE-E winds {ne_e_days} days, avg {avg_speed:.1f} m/s)")
            elif ne_e_days >= 2 and avg_speed >= 0.5:
                print(f"     ⚡ Moderate KZ-side advection potential")
            else:
                print(f"     ✅ Weak/no KZ-side advection signal")
        else:
            print(f"\n  🌬️  WIND: No data available")

        # Pollution narrative
        pd_entry = poll_data.get(focus_date, {})
        if pd_entry:
            print(f"\n  🏭 POLLUTION LEVELS:")
            for poll_name in ["NO2", "CO", "PM25"]:
                if poll_name in pd_entry:
                    d = pd_entry[poll_name]
                    cfg = POLLUTANTS[poll_name]
                    arrow = "↑" if d["ns_ratio"] > 1.1 else ("↓" if d["ns_ratio"] < 0.9 else "→")
                    print(f"     {cfg['label']:6s}  mean={d['mean']:>8.1f} {cfg['units']}")
                    print(f"            N-half={d['north_mean']:>8.1f}  S-half={d['south_mean']:>8.1f}  "
                          f"N/S ratio={d['ns_ratio']:.2f} {arrow}")
                    print(f"            NW(KZ)={d['nw_mean']:>8.1f}  SE    ={d['se_mean']:>8.1f}  "
                          f"NW/SE   ={d['nw_se_ratio']:.2f}")

        # Interpretation
        no2 = pd_entry.get("NO2", {})
        pm25 = pd_entry.get("PM25", {})
        co = pd_entry.get("CO", {})
        if no2 and valid_winds:
            print(f"\n  📊 INTERPRETATION:")
            # NO2 N/S ratio > 1.3 + NE wind = evidence of KZ transport
            if no2.get("ns_ratio", 1.0) > 1.3 and ne_e_days >= 3:
                print(f"     → Strong evidence of cross-border NO₂ transport from KZ/steppe side")
                print(f"       (N/S ratio {no2['ns_ratio']:.2f} with {ne_e_days} days NE-E wind)")
            elif no2.get("ns_ratio", 1.0) > 1.1:
                print(f"     → Northern NO₂ gradient present (N/S={no2['ns_ratio']:.2f}), "
                      f"partially consistent with KZ-side sources")
            else:
                print(f"     → NO₂ relatively uniform (N/S={no2.get('ns_ratio', 'N/A')}), "
                      f"suggesting local urban emissions dominate")

            if pm25 and pm25.get("ns_ratio", 1.0) < 0.95:
                print(f"     → PM₂.₅ higher in south (N/S={pm25['ns_ratio']:.2f}) — "
                      f"traffic/construction/local sources likely dominant")
            elif pm25 and pm25.get("nw_se_ratio", 1.0) > 1.15:
                print(f"     → PM₂.₅ NW(KZ) elevated (NW/SE={pm25['nw_se_ratio']:.2f}) — "
                      f"possible dust/particulate advection from steppe")

            if co:
                if co.get("ns_ratio", 1.0) > 1.05:
                    print(f"     → CO slight north bias (N/S={co['ns_ratio']:.2f}) — "
                          f"consistent with industrial/heating from north")
                else:
                    print(f"     → CO uniform — suggests well-mixed regional background")

    # ===================================================================
    # 4. Temporal evolution summary
    # ===================================================================
    print(f"\n{'=' * 70}")
    print("  TEMPORAL EVOLUTION ACROSS 6 DATES")
    print(f"{'=' * 70}\n")

    print(f"  {'Date':>8s}  {'NO2_N/S':>8s}  {'NO2_mean':>9s}  {'PM25_N/S':>9s}  "
          f"{'PM25_mean':>10s}  {'CO_N/S':>7s}  {'Prev-wk wind':>14s}  {'KZ advect':>10s}")
    print(f"  {'─' * 90}")

    rows = []
    for focus_date, label in zip(FOCUS_DATES, FOCUS_LABELS):
        no2 = poll_data.get(focus_date, {}).get("NO2", {})
        pm25 = poll_data.get(focus_date, {}).get("PM25", {})
        co = poll_data.get(focus_date, {}).get("CO", {})
        winds = wind_history.get(focus_date, [])
        valid_w = [w for w in winds if not np.isnan(w.get("speed", np.nan))]

        if valid_w:
            u_avg = np.mean([w["u"] for w in valid_w])
            v_avg = np.mean([w["v"] for w in valid_w])
            avg_spd = np.mean([w["speed"] for w in valid_w])
            avg_dir = (270 - np.degrees(np.arctan2(v_avg, u_avg))) % 360
            ne_e = sum(1 for w in valid_w if 0 <= w["direction"] <= 120)
            wind_str = f"{avg_spd:.1f} m/s {deg_to_cardinal(avg_dir):>3s}"
            advect = "HIGH" if ne_e >= 4 and avg_spd >= 0.8 else (
                     "MOD" if ne_e >= 2 and avg_spd >= 0.5 else "LOW")
        else:
            wind_str = "N/A"
            advect = "N/A"
            avg_spd = np.nan
            avg_dir = np.nan
            ne_e = 0

        no2_ns = no2.get("ns_ratio", np.nan)
        no2_m = no2.get("mean", np.nan)
        pm_ns = pm25.get("ns_ratio", np.nan)
        pm_m = pm25.get("mean", np.nan)
        co_ns = co.get("ns_ratio", np.nan)

        print(f"  {label:>8s}  {no2_ns:>8.2f}  {no2_m:>9.1f}  {pm_ns:>9.2f}  "
              f"{pm_m:>10.1f}  {co_ns:>7.2f}  {wind_str:>14s}  {advect:>10s}")

        rows.append({
            "date": focus_date,
            "label": label,
            "no2_mean": no2.get("mean"),
            "no2_north": no2.get("north_mean"),
            "no2_south": no2.get("south_mean"),
            "no2_ns_ratio": no2.get("ns_ratio"),
            "no2_nw_kz": no2.get("nw_mean"),
            "no2_se": no2.get("se_mean"),
            "no2_nw_se_ratio": no2.get("nw_se_ratio"),
            "co_mean": co.get("mean"),
            "co_ns_ratio": co.get("ns_ratio"),
            "pm25_mean": pm25.get("mean"),
            "pm25_north": pm25.get("north_mean"),
            "pm25_south": pm25.get("south_mean"),
            "pm25_ns_ratio": pm25.get("ns_ratio"),
            "pm25_nw_se_ratio": pm25.get("nw_se_ratio"),
            "wind_avg_speed": round(avg_spd, 2) if not np.isnan(avg_spd) else None,
            "wind_avg_dir": round(avg_dir, 1) if not np.isnan(avg_dir) else None,
            "wind_ne_e_days": ne_e,
            "kz_advection": advect,
        })

    # Save CSV
    df = pd.DataFrame(rows)
    csv_path = OUTPUT_DIR / "tashkent_aq_date_deep_dive.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n💾 CSV → {csv_path}")

    # ===================================================================
    # 5. Create combined figure
    # ===================================================================
    create_deep_dive_figure(wind_history, poll_data)


def create_deep_dive_figure(wind_history, poll_data):
    """4-panel figure: wind roses, NO2 N/S, PM2.5 N/S, and timeline."""

    n_dates = len(FOCUS_DATES)

    fig = plt.figure(figsize=(22, 16))
    gs = fig.add_gridspec(3, n_dates, hspace=0.35, wspace=0.3,
                          height_ratios=[1.2, 1, 1])

    # --- Row 1: Wind history panels (one per date) ---
    for i, (focus_date, label) in enumerate(zip(FOCUS_DATES, FOCUS_LABELS)):
        ax = fig.add_subplot(gs[0, i])
        winds = wind_history[focus_date]

        days_labels = []
        speeds = []
        dirs = []
        colors_list = []

        for w in winds:
            days_labels.append(w["day_label"][:5])
            spd = w.get("speed", np.nan)
            d = w.get("direction", np.nan)
            speeds.append(spd if not np.isnan(spd) else 0)
            dirs.append(d if not np.isnan(d) else 0)
            # Color by direction: NE-E (KZ side) = red, other = blue
            if not np.isnan(d) and (0 <= d <= 120):
                colors_list.append("#d32f2f")
            elif not np.isnan(d):
                colors_list.append("#1976d2")
            else:
                colors_list.append("#bdbdbd")

        y_pos = range(len(days_labels))
        ax.barh(y_pos, speeds, color=colors_list, edgecolor="white", linewidth=0.5, height=0.7)

        # Add direction text
        for j, (spd, d, w) in enumerate(zip(speeds, dirs, winds)):
            if spd > 0:
                card = w.get("cardinal", "")
                ax.text(spd + 0.05, j, f" {card} ({d:.0f}°)", va="center",
                        fontsize=7, color="#333")

        ax.set_yticks(y_pos)
        ax.set_yticklabels(days_labels, fontsize=7)
        ax.set_xlabel("Wind speed (m/s)", fontsize=8)
        ax.set_title(f"Week before {label}", fontsize=10, fontweight="bold")
        ax.set_xlim(0, max(max(speeds) * 1.6, 2.0))
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.3)

    # Legend for wind direction
    legend_elements = [
        mpatches.Patch(facecolor="#d32f2f", label="NE-E (KZ/steppe sector, 0°-120°)"),
        mpatches.Patch(facecolor="#1976d2", label="Other directions"),
    ]
    fig.legend(handles=legend_elements, loc="upper center",
               bbox_to_anchor=(0.5, 0.98), ncol=2, fontsize=9,
               title="Wind FROM direction", title_fontsize=10)

    # --- Row 2: NO2 North vs South bar chart ---
    for i, (focus_date, label) in enumerate(zip(FOCUS_DATES, FOCUS_LABELS)):
        ax = fig.add_subplot(gs[1, i])
        d = poll_data.get(focus_date, {}).get("NO2", {})
        if d:
            bars = ax.bar(
                ["NW\n(KZ)", "N-half", "Mean", "S-half", "SE"],
                [d["nw_mean"], d["north_mean"], d["mean"], d["south_mean"], d["se_mean"]],
                color=["#d32f2f", "#ef5350", "#9e9e9e", "#42a5f5", "#1976d2"],
                edgecolor="white", linewidth=0.5,
            )
            ax.set_ylabel("NO₂ (µmol/m²)" if i == 0 else "", fontsize=8)
            ax.set_title(f"NO₂ — {label}\nN/S={d['ns_ratio']:.2f}", fontsize=9, fontweight="bold")
            ax.tick_params(labelsize=7)
            # Add value labels
            for bar in bars:
                h = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, h + 2,
                        f"{h:.0f}", ha="center", va="bottom", fontsize=7)
        else:
            ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center")
            ax.set_title(f"NO₂ — {label}", fontsize=9)

    # --- Row 3: PM2.5 North vs South bar chart ---
    for i, (focus_date, label) in enumerate(zip(FOCUS_DATES, FOCUS_LABELS)):
        ax = fig.add_subplot(gs[2, i])
        d = poll_data.get(focus_date, {}).get("PM25", {})
        if d:
            bars = ax.bar(
                ["NW\n(KZ)", "N-half", "Mean", "S-half", "SE"],
                [d["nw_mean"], d["north_mean"], d["mean"], d["south_mean"], d["se_mean"]],
                color=["#d32f2f", "#ef5350", "#9e9e9e", "#42a5f5", "#1976d2"],
                edgecolor="white", linewidth=0.5,
            )
            ax.set_ylabel("PM₂.₅ (µg/m³)" if i == 0 else "", fontsize=8)
            ax.set_title(f"PM₂.₅ — {label}\nN/S={d['ns_ratio']:.2f}", fontsize=9, fontweight="bold")
            ax.tick_params(labelsize=7)
            for bar in bars:
                h = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, h + 0.2,
                        f"{h:.1f}", ha="center", va="bottom", fontsize=7)
        else:
            ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center")
            ax.set_title(f"PM₂.₅ — {label}", fontsize=9)

    fig.suptitle("Tashkent Air Quality — Per-date Deep Dive (Jan–Mar 2026)\n"
                 "7-day prevailing winds + North/South pollution gradient",
                 fontsize=14, fontweight="bold", y=1.01)

    out = OUTPUT_DIR / "tashkent_aq_date_deep_dive.png"
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\n📊 Figure → {out}")

    # ===================================================================
    # 6. Create temporal evolution figure
    # ===================================================================
    create_evolution_figure(wind_history, poll_data)


def create_evolution_figure(wind_history, poll_data):
    """Timeline showing how pollution & wind evolve across the 6 dates."""

    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True,
                             gridspec_kw={"hspace": 0.15, "height_ratios": [1, 1, 1, 0.8]})

    x = np.arange(len(FOCUS_DATES))

    # Collect data
    no2_north = [poll_data.get(d, {}).get("NO2", {}).get("north_mean", np.nan) for d in FOCUS_DATES]
    no2_south = [poll_data.get(d, {}).get("NO2", {}).get("south_mean", np.nan) for d in FOCUS_DATES]
    no2_ns = [poll_data.get(d, {}).get("NO2", {}).get("ns_ratio", np.nan) for d in FOCUS_DATES]

    pm_north = [poll_data.get(d, {}).get("PM25", {}).get("north_mean", np.nan) for d in FOCUS_DATES]
    pm_south = [poll_data.get(d, {}).get("PM25", {}).get("south_mean", np.nan) for d in FOCUS_DATES]

    co_north = [poll_data.get(d, {}).get("CO", {}).get("north_mean", np.nan) for d in FOCUS_DATES]
    co_south = [poll_data.get(d, {}).get("CO", {}).get("south_mean", np.nan) for d in FOCUS_DATES]

    wind_speeds = []
    wind_dirs = []
    kz_fractions = []
    for d in FOCUS_DATES:
        ws = wind_history.get(d, [])
        valid = [w for w in ws if not np.isnan(w.get("speed", np.nan))]
        if valid:
            wind_speeds.append(np.mean([w["speed"] for w in valid]))
            u_avg = np.mean([w["u"] for w in valid])
            v_avg = np.mean([w["v"] for w in valid])
            wind_dirs.append((270 - np.degrees(np.arctan2(v_avg, u_avg))) % 360)
            kz_fractions.append(sum(1 for w in valid if 0 <= w["direction"] <= 120) / len(valid))
        else:
            wind_speeds.append(np.nan)
            wind_dirs.append(np.nan)
            kz_fractions.append(0)

    # Panel 1: NO2 N vs S
    ax = axes[0]
    ax.bar(x - 0.15, no2_north, 0.3, label="North (KZ side)", color="#d32f2f", alpha=0.85)
    ax.bar(x + 0.15, no2_south, 0.3, label="South (city side)", color="#1976d2", alpha=0.85)
    ax2 = ax.twinx()
    ax2.plot(x, no2_ns, "k--o", markersize=5, label="N/S ratio", zorder=5)
    ax2.axhline(1.0, color="gray", linewidth=0.5, linestyle=":")
    ax2.set_ylabel("N/S ratio", fontsize=9)
    ax.set_ylabel("NO₂ (µmol/m²)", fontsize=9)
    ax.set_title("NO₂ — Northern vs Southern Tashkent", fontsize=11, fontweight="bold")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper right")

    # Panel 2: PM2.5 N vs S
    ax = axes[1]
    ax.bar(x - 0.15, pm_north, 0.3, label="North", color="#d32f2f", alpha=0.85)
    ax.bar(x + 0.15, pm_south, 0.3, label="South", color="#1976d2", alpha=0.85)
    ax.set_ylabel("PM₂.₅ (µg/m³)", fontsize=9)
    ax.set_title("PM₂.₅ — Northern vs Southern Tashkent", fontsize=11, fontweight="bold")
    ax.legend(fontsize=8, loc="upper right")

    # Panel 3: CO N vs S
    ax = axes[2]
    ax.bar(x - 0.15, co_north, 0.3, label="North", color="#d32f2f", alpha=0.85)
    ax.bar(x + 0.15, co_south, 0.3, label="South", color="#1976d2", alpha=0.85)
    ax.set_ylabel("CO (mmol/m²)", fontsize=9)
    ax.set_title("CO — Northern vs Southern Tashkent", fontsize=11, fontweight="bold")
    ax.legend(fontsize=8, loc="upper right")

    # Panel 4: Wind speed + KZ fraction
    ax = axes[3]
    bar_colors = ["#d32f2f" if f > 0.5 else "#1976d2" for f in kz_fractions]
    ax.bar(x, wind_speeds, 0.5, color=bar_colors, alpha=0.8)
    for i_x, (spd, d_val, frac) in enumerate(zip(wind_speeds, wind_dirs, kz_fractions)):
        if not np.isnan(spd):
            card = deg_to_cardinal(d_val)
            ax.text(i_x, spd + 0.05, f"{card}\n{frac*100:.0f}% KZ",
                    ha="center", fontsize=7, fontweight="bold")
    ax.set_ylabel("Wind speed (m/s)", fontsize=9)
    ax.set_title("Prevailing Wind — 7 days before each date", fontsize=11, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(FOCUS_LABELS, fontsize=10)
    ax.set_xlabel("Date (2026)", fontsize=10)

    legend_elements = [
        mpatches.Patch(facecolor="#d32f2f", label=">50% from KZ sector (0°-120°)"),
        mpatches.Patch(facecolor="#1976d2", label="<50% from KZ sector"),
    ]
    ax.legend(handles=legend_elements, fontsize=8, loc="upper right")

    fig.suptitle("Tashkent Air Quality — Temporal Evolution & Wind Source Tracking\n"
                 "6 Key Dates (Jan–Mar 2026)",
                 fontsize=13, fontweight="bold", y=1.02)

    out = OUTPUT_DIR / "tashkent_aq_date_evolution.png"
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"📊 Evolution figure → {out}")


if __name__ == "__main__":
    main()
