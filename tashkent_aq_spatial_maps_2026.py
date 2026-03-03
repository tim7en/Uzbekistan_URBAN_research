"""Tashkent Air Quality — Spatial Maps & Source Tracking (Nov 2025–Mar 2026).

Produces gridded spatial maps of NO2, CO, and PM2.5 over Tashkent and a
~40 km surrounding area from November 2025 through March 2026 to track
the full winter pollution buildup, identify emission sources, and trace
transport pathways using ERA5 wind data.

Coverage: ~bi-weekly snapshots Nov 2025 → Mar 2026 (12 dates)

Outputs (all saved to tashkent_air_quality_rasters/):
  - tashkent_aq_spatial_maps_nov_mar.png           (main multi-panel)
  - tashkent_aq_spatial_NO2_nov_mar.png            (per-pollutant details)
  - tashkent_aq_spatial_CO_nov_mar.png
  - tashkent_aq_spatial_PM25_nov_mar.png
  - tashkent_aq_directional_gradient_nov_mar.png   (N-S / E-W gradient)
  - tashkent_aq_difference_maps_nov_mar.png        (first vs last change)
  - tashkent_aq_source_tracking_nov_mar.png        (NO2 + wind vectors)
  - tashkent_aq_wind_summary_nov_mar.png           (wind rose + timeline)
  - tashkent_aq_pollution_timeline_nov_mar.png     (concentration + wind timeline)
  - tashkent_aq_spatial_data_nov_mar.json          (raw grid data)

Usage:
    python tashkent_aq_spatial_maps_2026.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import ee
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import contextily as ctx
from scipy.interpolate import RegularGridInterpolator

from services.gee import initialize_gee
from services.utils import UZBEKISTAN_CITIES, GEE_CONFIG

# Basemap tile provider — Stamen Toner-Lite for a clean underlay
# Other options: ctx.providers.OpenStreetMap.Mapnik, ctx.providers.CartoDB.Positron
BASEMAP_SOURCE = ctx.providers.CartoDB.Positron
POLLUTANT_OPACITY = 0.65  # pollutant overlay opacity (0=transparent, 1=opaque)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TARGET_DATES = [
    # Nov 2025 — pre-winter baseline
    "2025-11-01",
    "2025-11-15",
    # Dec 2025 — winter onset / heating season starts
    "2025-12-01",
    "2025-12-15",
    # Jan 2026 — deep winter, peak heating
    "2026-01-01",
    "2026-01-15",
    "2026-01-23",
    "2026-01-29",
    # Feb 2026
    "2026-02-07",
    "2026-02-17",
    # Mar 2026 — late winter / transition
    "2026-03-01",
]
DATE_LABELS = [
    "1 Nov", "15 Nov",
    "1 Dec", "15 Dec",
    "1 Jan", "15 Jan", "23 Jan", "29 Jan",
    "7 Feb", "17 Feb",
    "1 Mar",
]

# File suffix for all outputs
FILE_SUFFIX = "nov_mar"

SEARCH_WINDOW_DAYS = 2

# Tashkent center
CENTER_LON = 69.2401
CENTER_LAT = 41.2995

# Map extent: ~40 km radius → ~0.45° in each direction
# This covers Tashkent city + surrounding area including the KZ border
MAP_HALF_DEG = 0.42  # ~46 km at this latitude

# Bounding box for the spatial extraction
WEST  = CENTER_LON - MAP_HALF_DEG
EAST  = CENTER_LON + MAP_HALF_DEG
SOUTH = CENTER_LAT - MAP_HALF_DEG
NORTH = CENTER_LAT + MAP_HALF_DEG

# Grid resolution for sampling (in degrees)
# S5P is ~7 km → ~0.065°; we use ~5 km grid for smooth maps
GRID_STEP = 0.05  # ~5.5 km at 41°N

# Key pollutants for spatial mapping
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
        "cmap": "YlOrRd",
        "label": "NO₂",
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
        "cmap": "YlOrBr",
        "label": "CO",
    },
    "PM25": {
        "datasets": [
            "ECMWF/CAMS/NRT",
        ],
        "band": "particulate_matter_d_less_than_25_um_surface",
        "factor": 1e9,
        "units": "µg/m³",
        "scale": 11000,
        "cmap": "RdYlGn_r",
        "label": "PM₂.₅",
    },
}

# Approximate Kazakhstan border segments near Tashkent
# (simplified polyline from OSM — north of Tashkent)
KZ_BORDER_LONS = [68.65, 68.80, 69.00, 69.15, 69.30, 69.40, 69.55, 69.70, 69.85]
KZ_BORDER_LATS = [41.58, 41.56, 41.52, 41.54, 41.56, 41.58, 41.60, 41.58, 41.55]

# Nearby reference points
LANDMARKS = {
    "Tashkent": (69.2401, 41.2995),
    "Airport": (69.2815, 41.2573),
    "Chirchiq": (69.5826, 41.4689),
    "Olmaliq": (69.5983, 40.8447),
    "KZ border\n(approx.)": (69.20, 41.58),
}

# ERA5 wind configuration for source-tracking
ERA5_DATASET = "ECMWF/ERA5_LAND/HOURLY"  # hourly u/v wind at 10m
ERA5_U_BAND = "u_component_of_wind_10m"
ERA5_V_BAND = "v_component_of_wind_10m"
ERA5_WIND_SCALE = 11000  # ERA5-Land ~11 km resolution

OUTPUT_DIR = Path("tashkent_air_quality_rasters")

# ---------------------------------------------------------------------------
# GEE helpers
# ---------------------------------------------------------------------------

def get_composite_for_date(
    datasets: List[str],
    band: str,
    target_date: str,
    aoi: ee.Geometry,
    window_days: int = SEARCH_WINDOW_DAYS,
) -> Optional[ee.Image]:
    """Return a mean composite image for the date window, or None."""
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    start = (dt - timedelta(days=window_days)).strftime("%Y-%m-%d")
    end = (dt + timedelta(days=window_days + 1)).strftime("%Y-%m-%d")

    merged = None
    for ds in datasets:
        col = (
            ee.ImageCollection(ds)
            .filterDate(start, end)
            .filterBounds(aoi)
            .select(band)
        )
        merged = col if merged is None else merged.merge(col)

    n = merged.size().getInfo()
    if n == 0:
        return None
    return merged.mean()


def extract_grid_values(
    image: ee.Image,
    band: str,
    west: float, south: float, east: float, north: float,
    step: float,
    scale: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract a 2D raster from the image over the bounding box.

    Uses ee.Image.sampleRectangle() to pull pixel values directly.
    Returns (lons_1d, lats_1d, values_2d) where values_2d[row, col]
    corresponds to (lats_1d[row], lons_1d[col]).
    """
    rect = ee.Geometry.Rectangle([west, south, east, north])

    # Reproject to a fixed grid at the desired scale so we control resolution
    proj = ee.Projection("EPSG:4326").atScale(scale)
    img_repr = image.select(band).reproject(crs=proj)

    # sampleRectangle returns a dict with band → 2D array
    try:
        arr_dict = img_repr.sampleRectangle(
            region=rect, defaultValue=-9999
        ).getInfo()
    except Exception as exc:
        # If sampleRectangle hits the pixel limit, fall back to coarser scale
        coarser = scale * 2
        print(f"(retrying at {coarser}m)...", end=" ", flush=True)
        proj = ee.Projection("EPSG:4326").atScale(coarser)
        img_repr = image.select(band).reproject(crs=proj)
        arr_dict = img_repr.sampleRectangle(
            region=rect, defaultValue=-9999
        ).getInfo()

    properties = arr_dict.get("properties", {})
    raw_array = properties.get(band)

    if raw_array is None:
        raise ValueError(f"Band '{band}' not found in sampleRectangle result")

    grid = np.array(raw_array, dtype=float)
    # Replace sentinel -9999 and None with NaN
    grid[grid == -9999] = np.nan
    grid[grid == None] = np.nan  # noqa: E711

    # sampleRectangle returns rows from north to south, flip so row-0 = south
    grid = np.flipud(grid)

    n_rows, n_cols = grid.shape
    lats = np.linspace(south, north, n_rows)
    lons = np.linspace(west, east, n_cols)

    return lons, lats, grid


def get_wind_for_date(
    target_date: str,
    aoi: ee.Geometry,
    window_days: int = SEARCH_WINDOW_DAYS,
) -> Optional[ee.Image]:
    """Get mean ERA5-Land 10m wind composite for the date window."""
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    start = (dt - timedelta(days=window_days)).strftime("%Y-%m-%d")
    end = (dt + timedelta(days=window_days + 1)).strftime("%Y-%m-%d")

    col = (
        ee.ImageCollection(ERA5_DATASET)
        .filterDate(start, end)
        .filterBounds(aoi)
        .select([ERA5_U_BAND, ERA5_V_BAND])
    )
    n = col.size().getInfo()
    if n == 0:
        return None
    return col.mean()


def extract_wind_grid(
    image: ee.Image,
    west: float, south: float, east: float, north: float,
    scale: int = ERA5_WIND_SCALE,
) -> Optional[Dict]:
    """Extract U and V wind component grids via sampleRectangle."""
    rect = ee.Geometry.Rectangle([west, south, east, north])
    proj = ee.Projection("EPSG:4326").atScale(scale)
    img_repr = image.reproject(crs=proj)

    try:
        arr_dict = img_repr.sampleRectangle(
            region=rect, defaultValue=-9999
        ).getInfo()
    except Exception:
        coarser = scale * 2
        proj = ee.Projection("EPSG:4326").atScale(coarser)
        img_repr = image.reproject(crs=proj)
        arr_dict = img_repr.sampleRectangle(
            region=rect, defaultValue=-9999
        ).getInfo()

    props = arr_dict.get("properties", {})
    u_raw = props.get(ERA5_U_BAND)
    v_raw = props.get(ERA5_V_BAND)
    if u_raw is None or v_raw is None:
        return None

    u = np.array(u_raw, dtype=float)
    v = np.array(v_raw, dtype=float)
    for arr in (u, v):
        arr[arr == -9999] = np.nan
    u = np.flipud(u)
    v = np.flipud(v)

    nr, nc = u.shape
    lats = np.linspace(south, north, nr)
    lons = np.linspace(west, east, nc)
    return {"lons": lons, "lats": lats, "u": u, "v": v}


# ---------------------------------------------------------------------------
# Basemap helper
# ---------------------------------------------------------------------------

def add_basemap(ax, zoom=11):
    """Add an OpenStreetMap / CartoDB basemap to a lat/lon axes."""
    try:
        ctx.add_basemap(
            ax,
            crs="EPSG:4326",
            source=BASEMAP_SOURCE,
            zoom=zoom,
            attribution_size=5,
        )
    except Exception as exc:
        # Fail gracefully — basemap is cosmetic
        print(f"  ⚠️ basemap fetch failed: {exc}")


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

def add_map_annotations(ax, show_landmarks=True, show_border=True):
    """Add Tashkent circle, landmarks, and approximate KZ border."""
    # 20 km radius circle around Tashkent (~0.22° at 41°N)
    radius_deg = 20 / 111.32  # rough conversion
    circle = plt.Circle(
        (CENTER_LON, CENTER_LAT), radius_deg,
        fill=False, edgecolor="black", linewidth=1.5, linestyle="--",
        label="20 km radius",
    )
    ax.add_patch(circle)

    # Kazakhstan border
    if show_border:
        ax.plot(
            KZ_BORDER_LONS, KZ_BORDER_LATS,
            color="white", linewidth=2.5, linestyle="-", zorder=5,
        )
        ax.plot(
            KZ_BORDER_LONS, KZ_BORDER_LATS,
            color="black", linewidth=1.5, linestyle="--", zorder=6,
            label="KZ border (approx.)",
        )

    # Landmarks
    if show_landmarks:
        for name, (lon, lat) in LANDMARKS.items():
            if WEST < lon < EAST and SOUTH < lat < NORTH:
                ax.plot(lon, lat, "k^", markersize=5, zorder=7)
                ax.annotate(
                    name, (lon, lat),
                    textcoords="offset points", xytext=(5, 5),
                    fontsize=6, color="black", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", alpha=0.7, lw=0),
                    zorder=8,
                )


def add_north_arrow(ax):
    """Add a simple north arrow."""
    x = EAST - 0.04
    y = SOUTH + 0.06
    ax.annotate(
        "N", xy=(x, y + 0.04), fontsize=8, fontweight="bold", ha="center",
        va="bottom",
    )
    ax.annotate(
        "", xy=(x, y + 0.04), xytext=(x, y),
        arrowprops=dict(arrowstyle="->", lw=1.5),
    )


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def run_spatial_analysis():
    """Extract gridded pollutant data and create spatial maps."""
    print("=" * 70)
    print("  TASHKENT AIR QUALITY — SPATIAL MAPS (Nov 2025–Mar 2026)")
    print("=" * 70)

    # Initialize GEE
    print("\n🔑 Initializing Google Earth Engine...")
    ok = initialize_gee()
    if not ok:
        print("❌ GEE initialization failed.")
        return None
    print("   ✅ GEE ready\n")

    aoi = ee.Geometry.Rectangle([WEST, SOUTH, EAST, NORTH])

    # Storage for all grids
    all_grids: Dict[str, Dict[str, Any]] = {}
    # all_grids[pollutant][date_str] = {"lons": ..., "lats": ..., "grid": ...}

    for poll_name, cfg in POLLUTANTS.items():
        all_grids[poll_name] = {}
        print(f"\n📊 Extracting {poll_name} spatial grids...")

        for date_str, date_label in zip(TARGET_DATES, DATE_LABELS):
            print(f"   {date_label}...", end=" ", flush=True)

            composite = get_composite_for_date(
                cfg["datasets"], cfg["band"], date_str, aoi
            )
            if composite is None:
                print("⚠️ no data")
                all_grids[poll_name][date_str] = None
                continue

            try:
                lons, lats, grid = extract_grid_values(
                    composite, cfg["band"],
                    WEST, SOUTH, EAST, NORTH,
                    GRID_STEP, cfg["scale"],
                )
                # Apply unit conversion
                grid_converted = grid * cfg["factor"]
                all_grids[poll_name][date_str] = {
                    "lons": lons,
                    "lats": lats,
                    "grid": grid_converted,
                    "grid_raw": grid,
                }
                valid = np.count_nonzero(~np.isnan(grid_converted))
                print(f"✅ {valid} valid cells, "
                      f"range [{np.nanmin(grid_converted):.2f} – {np.nanmax(grid_converted):.2f}] {cfg['units']}")
            except Exception as exc:
                print(f"❌ {exc}")
                all_grids[poll_name][date_str] = None

    return all_grids


def create_main_panel_figure(all_grids: Dict):
    """Create the main multi-panel figure: rows=pollutants, cols=dates with basemap."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    poll_names = list(POLLUTANTS.keys())
    n_polls = len(poll_names)
    n_dates = len(TARGET_DATES)

    fig, axes = plt.subplots(
        n_polls, n_dates, figsize=(3.8 * n_dates, 3.5 * n_polls),
        sharex=True, sharey=True,
    )

    for i, poll_name in enumerate(poll_names):
        cfg = POLLUTANTS[poll_name]

        # Compute shared colour limits across all dates for this pollutant
        all_vals = []
        for date_str in TARGET_DATES:
            entry = all_grids[poll_name].get(date_str)
            if entry is not None:
                g = entry["grid"]
                all_vals.extend(g[~np.isnan(g)].tolist())

        if all_vals:
            vmin = np.percentile(all_vals, 2)
            vmax = np.percentile(all_vals, 98)
        else:
            vmin, vmax = 0, 1

        for j, (date_str, date_label) in enumerate(zip(TARGET_DATES, DATE_LABELS)):
            ax = axes[i, j]
            entry = all_grids[poll_name].get(date_str)

            # Set extent first so basemap fetches correct tiles
            ax.set_xlim(WEST, EAST)
            ax.set_ylim(SOUTH, NORTH)

            # Basemap underlay
            add_basemap(ax, zoom=10)

            if entry is None:
                ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                        ha="center", va="center", fontsize=10, color="gray")
            else:
                lons = entry["lons"]
                lats = entry["lats"]
                grid = entry["grid"]

                im = ax.pcolormesh(
                    lons, lats, grid,
                    cmap=cfg["cmap"], vmin=vmin, vmax=vmax,
                    shading="nearest",
                    alpha=POLLUTANT_OPACITY,
                    zorder=2,
                )

            add_map_annotations(ax, show_landmarks=(j == 0), show_border=True)

            if i == 0:
                ax.set_title(date_label, fontsize=11, fontweight="bold")
            if j == 0:
                ax.set_ylabel(f"{cfg['label']}\n({cfg['units']})", fontsize=10, fontweight="bold")
            if i == n_polls - 1:
                ax.set_xlabel("Longitude", fontsize=8)

            ax.set_xlim(WEST, EAST)
            ax.set_ylim(SOUTH, NORTH)
            ax.set_aspect("equal")
            ax.tick_params(labelsize=7)

        # Add colourbar for each row
        if all_vals:
            cbar = fig.colorbar(im, ax=axes[i, :].tolist(), shrink=0.85, pad=0.02)
            cbar.set_label(f"{cfg['label']} ({cfg['units']})", fontsize=9)
            cbar.ax.tick_params(labelsize=7)

    fig.suptitle(
        "Tashkent Air Quality — Spatial Distribution (Nov 2025–Mar 2026)\n"
        "Dashed circle = 20 km radius · Dashed line = approx. KZ border · Basemap © CartoDB",
        fontsize=13, fontweight="bold", y=1.02,
    )
    plt.tight_layout()

    out = OUTPUT_DIR / f"tashkent_aq_spatial_maps_{FILE_SUFFIX}.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"\n📊 Main panel figure → {out}")


def create_per_pollutant_figures(all_grids: Dict):
    """Create one larger figure per pollutant with more detail."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for poll_name, cfg in POLLUTANTS.items():
        n_dates = len(TARGET_DATES)
        ncols = 3
        nrows = (n_dates + ncols - 1) // ncols  # ceil division

        fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 5 * nrows))
        axes_flat = axes.flatten()

        # Shared colour limits
        all_vals = []
        for date_str in TARGET_DATES:
            entry = all_grids[poll_name].get(date_str)
            if entry is not None:
                g = entry["grid"]
                all_vals.extend(g[~np.isnan(g)].tolist())

        if not all_vals:
            plt.close(fig)
            continue

        vmin = np.percentile(all_vals, 2)
        vmax = np.percentile(all_vals, 98)

        im = None
        for idx, (date_str, date_label) in enumerate(zip(TARGET_DATES, DATE_LABELS)):
            ax = axes_flat[idx]
            entry = all_grids[poll_name].get(date_str)

            # Set extent and add basemap first
            ax.set_xlim(WEST, EAST)
            ax.set_ylim(SOUTH, NORTH)
            add_basemap(ax, zoom=11)

            if entry is None:
                ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                        ha="center", va="center", fontsize=12, color="gray")
            else:
                lons = entry["lons"]
                lats = entry["lats"]
                grid = entry["grid"]

                im = ax.pcolormesh(
                    lons, lats, grid,
                    cmap=cfg["cmap"], vmin=vmin, vmax=vmax,
                    shading="nearest",
                    alpha=POLLUTANT_OPACITY,
                    zorder=2,
                )
                # Mean value annotation
                mean_v = np.nanmean(grid)
                ax.text(
                    0.02, 0.02, f"mean={mean_v:.2f}",
                    transform=ax.transAxes, fontsize=8,
                    bbox=dict(fc="white", alpha=0.8, lw=0),
                    va="bottom",
                )

            add_map_annotations(ax, show_landmarks=True, show_border=True)
            add_north_arrow(ax)
            # Label with year for Nov/Dec dates
            yr = "25" if date_str.startswith("2025") else "26"
            ax.set_title(f"{date_label} '{yr}", fontsize=12, fontweight="bold")
            ax.set_xlim(WEST, EAST)
            ax.set_ylim(SOUTH, NORTH)
            ax.set_aspect("equal")
            ax.set_xlabel("Longitude", fontsize=9)
            ax.set_ylabel("Latitude", fontsize=9)
            ax.tick_params(labelsize=8)

        # Hide unused axes
        for idx in range(n_dates, len(axes_flat)):
            axes_flat[idx].set_visible(False)

        if im is not None:
            cbar = fig.colorbar(im, ax=axes_flat[:n_dates].tolist(), shrink=0.7, pad=0.03)
            cbar.set_label(f"{cfg['label']} ({cfg['units']})", fontsize=11)

        fig.suptitle(
            f"{cfg['label']} over Tashkent & Surroundings — Nov 2025–Mar 2026\n"
            f"Sentinel-5P / CAMS NRT · Basemap © CartoDB · Dashed circle = 20 km · Dashed line ≈ KZ border",
            fontsize=14, fontweight="bold", y=1.02,
        )
        plt.tight_layout()

        out = OUTPUT_DIR / f"tashkent_aq_spatial_{poll_name}_{FILE_SUFFIX}.png"
        fig.savefig(out, dpi=200, bbox_inches="tight")
        plt.close(fig)
        print(f"📊 {cfg['label']} detail figure → {out}")


def create_directional_gradient_analysis(all_grids: Dict):
    """Analyze N-S and E-W gradients to assess Kazakhstan-side influence.

    Splits the AOI into quadrants:
      NW (Kazakhstan side)  |  NE
      ----------------------+-----
      SW                    |  SE (Tashkent urban core)

    Also computes a "north-half vs south-half" ratio for each date.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    poll_names = list(POLLUTANTS.keys())
    results = {}

    for poll_name in poll_names:
        cfg = POLLUTANTS[poll_name]
        records = []

        for date_str, date_label in zip(TARGET_DATES, DATE_LABELS):
            entry = all_grids[poll_name].get(date_str)
            if entry is None:
                continue

            lons = entry["lons"]
            lats = entry["lats"]
            grid = entry["grid"]

            mid_lon_idx = len(lons) // 2
            mid_lat_idx = len(lats) // 2

            # Quadrants
            north_half = grid[mid_lat_idx:, :]
            south_half = grid[:mid_lat_idx, :]
            nw = grid[mid_lat_idx:, :mid_lon_idx]
            ne = grid[mid_lat_idx:, mid_lon_idx:]
            sw = grid[:mid_lat_idx, :mid_lon_idx]
            se = grid[:mid_lat_idx, mid_lon_idx:]

            rec = {
                "date": date_str,
                "label": date_label,
                "overall_mean": np.nanmean(grid),
                "north_mean": np.nanmean(north_half),
                "south_mean": np.nanmean(south_half),
                "NW_mean": np.nanmean(nw),
                "NE_mean": np.nanmean(ne),
                "SW_mean": np.nanmean(sw),
                "SE_mean": np.nanmean(se),
                "north_south_ratio": (
                    np.nanmean(north_half) / np.nanmean(south_half)
                    if np.nanmean(south_half) != 0 else None
                ),
            }
            records.append(rec)

        results[poll_name] = records

    # Plot
    fig, axes = plt.subplots(len(poll_names), 2, figsize=(14, 4.5 * len(poll_names)))
    if len(poll_names) == 1:
        axes = axes[np.newaxis, :]

    for i, poll_name in enumerate(poll_names):
        cfg = POLLUTANTS[poll_name]
        recs = results[poll_name]
        if not recs:
            continue

        labels = [r["label"] for r in recs]
        north_vals = [r["north_mean"] for r in recs]
        south_vals = [r["south_mean"] for r in recs]
        nw_vals = [r["NW_mean"] for r in recs]
        ne_vals = [r["NE_mean"] for r in recs]
        sw_vals = [r["SW_mean"] for r in recs]
        se_vals = [r["SE_mean"] for r in recs]
        ratios = [r["north_south_ratio"] for r in recs]

        x = np.arange(len(labels))
        width = 0.35

        # Left panel: North vs South
        ax1 = axes[i, 0]
        ax1.bar(x - width / 2, north_vals, width, label="North half (toward KZ)",
                color="#d62728", alpha=0.8)
        ax1.bar(x + width / 2, south_vals, width, label="South half",
                color="#1f77b4", alpha=0.8)
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, fontsize=9)
        ax1.set_ylabel(f"{cfg['label']} ({cfg['units']})", fontsize=10)
        ax1.set_title(f"{cfg['label']}:  North (KZ side) vs South", fontsize=11, fontweight="bold")
        ax1.legend(fontsize=9)
        ax1.grid(True, alpha=0.3, axis="y")

        # Add ratio annotation
        for j_idx, (xi, r) in enumerate(zip(x, ratios)):
            if r is not None:
                ax1.annotate(
                    f"N/S={r:.2f}", (xi, max(north_vals[j_idx], south_vals[j_idx])),
                    textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=8, color="gray",
                )

        # Right panel: 4 quadrants
        ax2 = axes[i, 1]
        w4 = 0.2
        ax2.bar(x - 1.5 * w4, nw_vals, w4, label="NW (KZ side)", color="#d62728", alpha=0.8)
        ax2.bar(x - 0.5 * w4, ne_vals, w4, label="NE (Chirchiq)", color="#ff7f0e", alpha=0.8)
        ax2.bar(x + 0.5 * w4, sw_vals, w4, label="SW", color="#2ca02c", alpha=0.8)
        ax2.bar(x + 1.5 * w4, se_vals, w4, label="SE", color="#1f77b4", alpha=0.8)
        ax2.set_xticks(x)
        ax2.set_xticklabels(labels, fontsize=9)
        ax2.set_ylabel(f"{cfg['label']} ({cfg['units']})", fontsize=10)
        ax2.set_title(f"{cfg['label']}:  Quadrant Analysis", fontsize=11, fontweight="bold")
        ax2.legend(fontsize=8, ncol=2)
        ax2.grid(True, alpha=0.3, axis="y")

    fig.suptitle(
        "Directional Gradient Analysis — Is pollution advected from Kazakhstan?\n"
        "North half / NW quadrant = Kazakhstan border side",
        fontsize=13, fontweight="bold", y=1.02,
    )
    plt.tight_layout()

    out = OUTPUT_DIR / f"tashkent_aq_directional_gradient_{FILE_SUFFIX}.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"\n📊 Directional gradient analysis → {out}")

    # Print summary
    print("\n" + "=" * 70)
    print("  DIRECTIONAL GRADIENT SUMMARY")
    print("=" * 70)
    for poll_name in poll_names:
        cfg = POLLUTANTS[poll_name]
        recs = results[poll_name]
        if not recs:
            continue
        print(f"\n  {cfg['label']} ({cfg['units']}):")
        print(f"  {'Date':>10s}  {'North':>8s}  {'South':>8s}  {'N/S':>6s}  {'NW(KZ)':>8s}  {'SE':>8s}  {'NW/SE':>6s}")
        print(f"  {'-'*60}")
        for r in recs:
            nw_se = (r["NW_mean"] / r["SE_mean"]) if r["SE_mean"] and r["SE_mean"] != 0 else None
            ratio_str = f"{r['north_south_ratio']:.2f}" if r["north_south_ratio"] else "N/A"
            nwse_str = f"{nw_se:.2f}" if nw_se else "N/A"
            print(
                f"  {r['label']:>10s}  "
                f"{r['north_mean']:8.2f}  {r['south_mean']:8.2f}  {ratio_str:>6s}  "
                f"{r['NW_mean']:8.2f}  {r['SE_mean']:8.2f}  {nwse_str:>6s}"
            )

        # Overall assessment
        avg_ratio = np.nanmean([r["north_south_ratio"] for r in recs if r["north_south_ratio"]])
        if avg_ratio > 1.05:
            verdict = f"↑ North (KZ side) consistently HIGHER by {(avg_ratio-1)*100:.1f}%"
        elif avg_ratio < 0.95:
            verdict = f"↓ North (KZ side) consistently LOWER by {(1-avg_ratio)*100:.1f}%"
        else:
            verdict = "→ No consistent north-south gradient"
        print(f"  Average N/S ratio: {avg_ratio:.3f}  ⇒  {verdict}")

    return results


def save_grid_data(all_grids: Dict):
    """Save grid data to JSON for reproducibility."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    serializable = {}
    for poll_name, dates_dict in all_grids.items():
        serializable[poll_name] = {}
        for date_str, entry in dates_dict.items():
            if entry is None:
                serializable[poll_name][date_str] = None
            else:
                serializable[poll_name][date_str] = {
                    "lons": entry["lons"].tolist(),
                    "lats": entry["lats"].tolist(),
                    "grid": np.where(np.isnan(entry["grid"]), None, entry["grid"]).tolist(),
                }

    out = OUTPUT_DIR / f"tashkent_aq_spatial_data_{FILE_SUFFIX}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)
    print(f"💾 Grid data → {out}")


# ---------------------------------------------------------------------------
# Difference maps (last date – first date)
# ---------------------------------------------------------------------------

def _resample_to_common_grid(entry_a, entry_b):
    """Resample two grid entries to the coarser common grid via nearest-neighbour."""
    # Use the coarser grid as the target
    if len(entry_a["lons"]) <= len(entry_b["lons"]):
        target_lons, target_lats = entry_a["lons"], entry_a["lats"]
    else:
        target_lons, target_lats = entry_b["lons"], entry_b["lats"]

    def _interp(entry, t_lons, t_lats):
        interp = RegularGridInterpolator(
            (entry["lats"], entry["lons"]), entry["grid"],
            method="nearest", bounds_error=False, fill_value=np.nan,
        )
        mg = np.meshgrid(t_lats, t_lons, indexing="ij")
        return interp((mg[0], mg[1]))

    grid_a = _interp(entry_a, target_lons, target_lats)
    grid_b = _interp(entry_b, target_lons, target_lats)
    return target_lons, target_lats, grid_a, grid_b


def create_difference_maps(all_grids: Dict):
    """Show the change between the first and last date for each pollutant."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    poll_names = list(POLLUTANTS.keys())

    fig, axes = plt.subplots(1, len(poll_names), figsize=(6 * len(poll_names), 5))
    if len(poll_names) == 1:
        axes = [axes]

    for i, poll_name in enumerate(poll_names):
        cfg = POLLUTANTS[poll_name]
        ax = axes[i]

        first_entry = all_grids[poll_name].get(TARGET_DATES[0])
        last_entry = all_grids[poll_name].get(TARGET_DATES[-1])

        if first_entry is None or last_entry is None:
            ax.text(0.5, 0.5, "Insufficient data", transform=ax.transAxes,
                    ha="center", va="center")
            continue

        # Handle different grid sizes by resampling to common grid
        if first_entry["grid"].shape != last_entry["grid"].shape:
            lons, lats, grid_first, grid_last = _resample_to_common_grid(first_entry, last_entry)
            diff = grid_last - grid_first
        else:
            diff = last_entry["grid"] - first_entry["grid"]
            lons = first_entry["lons"]
            lats = first_entry["lats"]

        abs_max = np.nanmax(np.abs(diff))
        if abs_max == 0:
            abs_max = 1

        # Basemap underlay
        ax.set_xlim(WEST, EAST)
        ax.set_ylim(SOUTH, NORTH)
        add_basemap(ax, zoom=11)

        im = ax.pcolormesh(
            lons, lats, diff,
            cmap="RdBu_r", vmin=-abs_max, vmax=abs_max,
            shading="nearest",
            alpha=POLLUTANT_OPACITY,
            zorder=2,
        )
        add_map_annotations(ax, show_landmarks=True, show_border=True)
        ax.set_title(
            f"{cfg['label']} change\n{DATE_LABELS[-1]} minus {DATE_LABELS[0]}",
            fontsize=11, fontweight="bold",
        )
        ax.set_xlim(WEST, EAST)
        ax.set_ylim(SOUTH, NORTH)
        ax.set_aspect("equal")
        ax.set_xlabel("Longitude", fontsize=9)
        ax.set_ylabel("Latitude", fontsize=9)

        cbar = fig.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label(f"Δ {cfg['label']} ({cfg['units']})", fontsize=9)

    fig.suptitle(
        f"Air Quality Change:  {DATE_LABELS[-1]} '26 − {DATE_LABELS[0]} '25\n"
        "Red = increase · Blue = decrease",
        fontsize=13, fontweight="bold", y=1.04,
    )
    plt.tight_layout()

    out = OUTPUT_DIR / f"tashkent_aq_difference_maps_{FILE_SUFFIX}.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"📊 Difference maps → {out}")


# ---------------------------------------------------------------------------
# Pollution source tracking with wind vectors
# ---------------------------------------------------------------------------

def extract_wind_data(aoi: ee.Geometry) -> Dict[str, Any]:
    """Extract ERA5-Land 10m wind grids for each target date."""
    wind_data = {}
    print("\n🌬️  Extracting ERA5-Land wind data for source tracking...")
    for date_str, date_label in zip(TARGET_DATES, DATE_LABELS):
        print(f"   {date_label}...", end=" ", flush=True)
        try:
            wind_img = get_wind_for_date(date_str, aoi)
            if wind_img is None:
                print("⚠️ no ERA5 data")
                wind_data[date_str] = None
                continue
            wg = extract_wind_grid(wind_img, WEST, SOUTH, EAST, NORTH)
            if wg is None:
                print("⚠️ extraction failed")
                wind_data[date_str] = None
                continue
            mean_u = np.nanmean(wg["u"])
            mean_v = np.nanmean(wg["v"])
            speed = np.sqrt(mean_u**2 + mean_v**2)
            # Wind direction (meteorological: where wind comes FROM)
            wind_dir = (270 - np.degrees(np.arctan2(mean_v, mean_u))) % 360
            print(f"✅ mean wind: {speed:.1f} m/s from {wind_dir:.0f}°")
            wind_data[date_str] = wg
            wind_data[date_str]["mean_u"] = mean_u
            wind_data[date_str]["mean_v"] = mean_v
            wind_data[date_str]["mean_speed"] = speed
            wind_data[date_str]["mean_dir"] = wind_dir
        except Exception as exc:
            print(f"❌ {exc}")
            wind_data[date_str] = None
    return wind_data


def create_source_tracking_figure(all_grids: Dict, wind_data: Dict):
    """Create a figure showing NO2 concentration + wind vectors to track pollution source.

    For each date: NO2 heatmap + wind quiver arrows showing where pollution
    is being transported FROM."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Use NO2 as the primary tracer for source tracking
    poll_name = "NO2"
    cfg = POLLUTANTS[poll_name]
    n_dates = len(TARGET_DATES)
    ncols = 3
    nrows = (n_dates + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(7 * ncols, 6 * nrows))
    axes_flat = axes.flatten()

    # Shared colour limits for NO2
    all_vals = []
    for date_str in TARGET_DATES:
        entry = all_grids[poll_name].get(date_str)
        if entry is not None:
            g = entry["grid"]
            all_vals.extend(g[~np.isnan(g)].tolist())
    if not all_vals:
        print("⚠️ No NO2 data for source tracking.")
        plt.close(fig)
        return
    vmin = np.percentile(all_vals, 2)
    vmax = np.percentile(all_vals, 98)

    for idx, (date_str, date_label) in enumerate(zip(TARGET_DATES, DATE_LABELS)):
        ax = axes_flat[idx]
        ax.set_xlim(WEST, EAST)
        ax.set_ylim(SOUTH, NORTH)
        add_basemap(ax, zoom=11)

        entry = all_grids[poll_name].get(date_str)
        if entry is not None:
            im = ax.pcolormesh(
                entry["lons"], entry["lats"], entry["grid"],
                cmap="YlOrRd", vmin=vmin, vmax=vmax,
                shading="nearest", alpha=0.55, zorder=2,
            )

        # Overlay wind vectors
        wdata = wind_data.get(date_str)
        wind_info = ""
        if wdata is not None:
            u = wdata["u"]
            v = wdata["v"]
            wlons = wdata["lons"]
            wlats = wdata["lats"]
            # Subsample wind grid for cleaner quivers
            step = max(1, len(wlons) // 8)
            lon_mesh, lat_mesh = np.meshgrid(wlons, wlats)
            ax.quiver(
                lon_mesh[::step, ::step], lat_mesh[::step, ::step],
                u[::step, ::step], v[::step, ::step],
                color="navy", scale=60, width=0.004,
                headwidth=4, headlength=4,
                zorder=5, alpha=0.85,
            )
            speed = wdata["mean_speed"]
            wind_dir = wdata["mean_dir"]
            # Compass label
            compass = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                       "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            comp_label = compass[int((wind_dir + 11.25) / 22.5) % 16]
            wind_info = f"Wind: {speed:.1f} m/s from {comp_label} ({wind_dir:.0f}°)"

            # Large arrow showing DOMINANT wind direction (transport direction)
            # This shows where pollutants go TO
            arrow_scale = 0.12  # degrees for arrow length
            norm_u = wdata["mean_u"] / (speed + 0.01) * arrow_scale
            norm_v = wdata["mean_v"] / (speed + 0.01) * arrow_scale
            ax.annotate(
                "", xy=(CENTER_LON + norm_u * 2, CENTER_LAT + norm_v * 2),
                xytext=(CENTER_LON - norm_u * 2, CENTER_LAT - norm_v * 2),
                arrowprops=dict(
                    arrowstyle="->", lw=3, color="darkblue",
                    mutation_scale=20,
                ),
                zorder=10,
            )

        add_map_annotations(ax, show_landmarks=True, show_border=True)

        yr = "'25" if date_str.startswith("2025") else "'26"
        title = f"{date_label} {yr}"
        if wind_info:
            title += f"\n{wind_info}"
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_xlim(WEST, EAST)
        ax.set_ylim(SOUTH, NORTH)
        ax.set_aspect("equal")
        ax.set_xlabel("Longitude", fontsize=9)
        ax.set_ylabel("Latitude", fontsize=9)
        ax.tick_params(labelsize=8)

    # Hide unused axes
    for idx in range(n_dates, len(axes_flat)):
        axes_flat[idx].set_visible(False)

    # Colourbar
    if all_vals:
        cbar = fig.colorbar(im, ax=axes_flat[:n_dates].tolist(), shrink=0.6, pad=0.03)
        cbar.set_label(f"NO₂ ({cfg['units']})", fontsize=11)

    fig.suptitle(
        "Pollution Source Tracking — NO₂ + Wind Direction over Tashkent (Nov '25–Mar '26)\n"
        "Arrows = wind flow direction (where pollution travels TO) · Blue arrow = dominant transport\n"
        "Basemap © CartoDB · Dashed circle = 20 km · Dashed line ≈ KZ border",
        fontsize=13, fontweight="bold", y=1.03,
    )
    plt.tight_layout()

    out = OUTPUT_DIR / f"tashkent_aq_source_tracking_{FILE_SUFFIX}.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"📊 Source tracking figure → {out}")


def create_wind_rose_summary(wind_data: Dict):
    """Create a summary panel: wind direction + speed for each date,
    plus a transport pathway timeline."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    valid_dates = [(d, l) for d, l in zip(TARGET_DATES, DATE_LABELS)
                   if wind_data.get(d) is not None]
    if not valid_dates:
        print("⚠️ No wind data for rose summary.")
        return

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # Left: wind speed + direction bar chart
    ax1 = axes[0]
    labels = [l for _, l in valid_dates]
    speeds = [wind_data[d]["mean_speed"] for d, _ in valid_dates]
    dirs = [wind_data[d]["mean_dir"] for d, _ in valid_dates]
    colors_bar = ["#1f77b4" if 180 < wd < 360 else "#d62728" for wd in dirs]
    # Red = wind FROM north/east (KZ side), Blue = wind FROM south/west

    x = np.arange(len(labels))
    bars = ax1.bar(x, speeds, color=colors_bar, alpha=0.8, edgecolor="black", lw=0.5)
    for xi, (s, d) in enumerate(zip(speeds, dirs)):
        compass = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                   "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        comp = compass[int((d + 11.25) / 22.5) % 16]
        ax1.annotate(f"{comp}\n{d:.0f}°", (xi, s), textcoords="offset points",
                     xytext=(0, 8), ha="center", fontsize=9, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=10)
    ax1.set_ylabel("Wind speed (m/s)", fontsize=11)
    ax1.set_title("Mean 10m Wind Speed & Direction\n(Red = from N/E / KZ side · Blue = from S/W)",
                  fontsize=12, fontweight="bold")
    ax1.grid(True, alpha=0.3, axis="y")

    # Right: polar plot showing wind FROM direction
    ax2 = fig.add_subplot(122, projection="polar")
    for (date_str, date_label) in valid_dates:
        wd = wind_data[date_str]
        # Meteorological convention: wind comes FROM this direction
        theta = np.radians(90 - wd["mean_dir"])  # convert to math convention
        r = wd["mean_speed"]
        color = "#d62728" if 0 <= wd["mean_dir"] <= 180 else "#1f77b4"
        ax2.plot(theta, r, "o", markersize=10, color=color, zorder=5)
        ax2.annotate(date_label, (theta, r), textcoords="offset points",
                     xytext=(8, 5), fontsize=8, fontweight="bold")
    ax2.set_theta_zero_location("N")
    ax2.set_theta_direction(-1)
    ax2.set_title("Wind FROM Direction\n(polar plot)", fontsize=12, fontweight="bold", pad=20)
    axes[1].set_visible(False)  # hide the normal axes behind polar

    fig.suptitle(
        "Wind Transport Analysis — Tashkent Nov 2025–Mar 2026\n"
        "ERA5-Land 10m wind · Direction = where wind comes FROM",
        fontsize=14, fontweight="bold", y=1.02,
    )
    plt.tight_layout()

    out = OUTPUT_DIR / f"tashkent_aq_wind_summary_{FILE_SUFFIX}.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"📊 Wind summary → {out}")


def create_pollution_wind_timeline(all_grids: Dict, wind_data: Dict):
    """Combined timeline: pollutant concentrations + wind speed/direction.

    Shows how pollution builds up as wind patterns change — key for
    identifying whether KZ-side emissions are transported into Tashkent.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    poll_names = list(POLLUTANTS.keys())
    dates_dt = [datetime.strptime(d, "%Y-%m-%d") for d in TARGET_DATES]

    fig, axes = plt.subplots(len(poll_names) + 1, 1, figsize=(16, 4 * (len(poll_names) + 1)),
                             sharex=True)

    # --- Wind panel (top) ---
    ax_wind = axes[0]
    valid_wind_dates = []
    wind_speeds = []
    wind_dirs = []
    wind_u = []
    wind_v = []
    for d, dt_val in zip(TARGET_DATES, dates_dt):
        wd = wind_data.get(d)
        if wd is not None:
            valid_wind_dates.append(dt_val)
            wind_speeds.append(wd["mean_speed"])
            wind_dirs.append(wd["mean_dir"])
            wind_u.append(wd["mean_u"])
            wind_v.append(wd["mean_v"])

    if valid_wind_dates:
        # Bar chart of wind speed + color by direction
        colors_w = []
        for wd_dir in wind_dirs:
            # Red if wind blows FROM N/NE/E (KZ side → city), Blue otherwise
            if 0 <= wd_dir <= 135 or wd_dir >= 315:
                colors_w.append("#d62728")  # from N/NE/E/NW → KZ advection
            else:
                colors_w.append("#1f77b4")  # from S/SW/W
        ax_wind.bar(valid_wind_dates, wind_speeds, width=2.5, color=colors_w, alpha=0.7,
                    edgecolor="black", lw=0.5, zorder=2)

        # Add direction quiver arrows on each bar
        for dt_val, sp, mu, mv in zip(valid_wind_dates, wind_speeds, wind_u, wind_v):
            # Normalize to unit vector, plot small arrow
            norm = max(sp, 0.01)
            ax_wind.annotate(
                "", xy=(dt_val, sp + 0.15),
                xytext=(dt_val, sp + 0.15),
                fontsize=8,
            )
            compass = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                       "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            wd_dir = (270 - np.degrees(np.arctan2(mv, mu))) % 360
            comp = compass[int((wd_dir + 11.25) / 22.5) % 16]
            ax_wind.annotate(f"from {comp}\n{wd_dir:.0f}°", (dt_val, sp),
                             textcoords="offset points", xytext=(0, 10),
                             ha="center", fontsize=7, fontweight="bold")

        ax_wind.set_ylabel("Wind speed\n(m/s)", fontsize=10, fontweight="bold")
        ax_wind.set_title("10m Wind Speed & Direction (Red = from KZ side · Blue = from S/W)",
                          fontsize=11, fontweight="bold")
        ax_wind.grid(True, alpha=0.3, axis="y")

        # Add legend
        from matplotlib.patches import Patch
        ax_wind.legend(
            handles=[
                Patch(facecolor="#d62728", alpha=0.7, label="Wind FROM N/NE/NW (KZ side)"),
                Patch(facecolor="#1f77b4", alpha=0.7, label="Wind FROM S/SW/W"),
            ],
            fontsize=9, loc="upper right",
        )

    # --- Pollutant panels ---
    for i, poll_name in enumerate(poll_names):
        ax = axes[i + 1]
        cfg = POLLUTANTS[poll_name]

        # Compute north-half and south-half means per date
        overall_vals = []
        north_vals = []
        south_vals = []
        valid_dates_p = []

        for d, dt_val in zip(TARGET_DATES, dates_dt):
            entry = all_grids[poll_name].get(d)
            if entry is not None:
                grid = entry["grid"]
                mid_lat = len(entry["lats"]) // 2
                valid_dates_p.append(dt_val)
                overall_vals.append(np.nanmean(grid))
                north_vals.append(np.nanmean(grid[mid_lat:, :]))
                south_vals.append(np.nanmean(grid[:mid_lat, :]))

        if valid_dates_p:
            ax.fill_between(valid_dates_p, north_vals, south_vals, alpha=0.15,
                            color=cfg.get("color", "gray"), zorder=1,
                            label="N-S spread")
            ax.plot(valid_dates_p, north_vals, "^-", color="#d62728", lw=1.5,
                    markersize=6, label="North (KZ side)", zorder=3)
            ax.plot(valid_dates_p, south_vals, "v-", color="#1f77b4", lw=1.5,
                    markersize=6, label="South (city)", zorder=3)
            ax.plot(valid_dates_p, overall_vals, "o-", color="black", lw=2,
                    markersize=7, label="Overall mean", zorder=4)

            # Shade periods where wind is from KZ side AND north > south
            for j_idx in range(len(valid_dates_p)):
                dt_v = valid_dates_p[j_idx]
                ds = TARGET_DATES[dates_dt.index(dt_v)] if dt_v in dates_dt else None
                wd = wind_data.get(ds) if ds else None
                if wd and north_vals[j_idx] > south_vals[j_idx]:
                    wd_dir = wd["mean_dir"]
                    if 0 <= wd_dir <= 135 or wd_dir >= 315:
                        ax.axvspan(dt_v - timedelta(days=2), dt_v + timedelta(days=2),
                                   alpha=0.08, color="red", zorder=0)

            ax.set_ylabel(f"{cfg['label']}\n({cfg['units']})", fontsize=10, fontweight="bold")
            ax.legend(fontsize=8, ncol=4, loc="upper right")
            ax.grid(True, alpha=0.3)

    import matplotlib.dates as mdates
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    axes[-1].xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha="right")
    axes[-1].set_xlabel("Date (Nov 2025 → Mar 2026)", fontsize=11)

    fig.suptitle(
        "Tashkent Pollution & Wind Timeline — Nov 2025 to Mar 2026\n"
        "Is pollution from CKZ side? Red shading = wind FROM KZ + North > South concentration",
        fontsize=14, fontweight="bold", y=1.01,
    )
    plt.tight_layout()

    out = OUTPUT_DIR / f"tashkent_aq_pollution_timeline_{FILE_SUFFIX}.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"📊 Pollution + wind timeline → {out}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    all_grids = run_spatial_analysis()
    if all_grids is None:
        print("❌ No data extracted.")
        return 1

    # Extract wind data for source tracking
    aoi = ee.Geometry.Rectangle([WEST, SOUTH, EAST, NORTH])
    wind_data = extract_wind_data(aoi)

    print("\n🎨 Creating visualizations (with basemap + wind overlays)...")
    create_main_panel_figure(all_grids)
    create_per_pollutant_figures(all_grids)
    create_difference_maps(all_grids)
    create_directional_gradient_analysis(all_grids)
    create_source_tracking_figure(all_grids, wind_data)
    create_wind_rose_summary(wind_data)
    create_pollution_wind_timeline(all_grids, wind_data)
    save_grid_data(all_grids)

    print("\n✅ Spatial analysis complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
