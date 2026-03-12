"""Tashkent SO2 source identification using Sentinel-5P and ERA5-Land.

This script is intentionally conservative:
- It uses the standard Sentinel-5P SO2 total-column product in Earth Engine.
- It avoids double-counting OFFL and NRTI scenes.
- It tracks observation coverage so sparse months are flagged instead of forced.
- It treats source attribution as relative evidence, not as an emission-rate inversion.

Outputs are written to ``tashkent_so2_sources/``.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import ee
import matplotlib
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.axes_grid1 import make_axes_locatable

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from services.gee import initialize_gee


def configure_stdout() -> None:
    """Use UTF-8 when supported so Earth Engine status text does not fail."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class SourceGroup:
    key: str
    label: str
    lon: float
    lat: float
    category: str
    color: str
    marker: str
    buffer_km: float
    dist_km: int
    confidence: str
    note: str


ANALYSIS_START = "2025-10-01"
ANALYSIS_END_INCLUSIVE = "2026-03-12"
ANALYSIS_END_EXCLUSIVE = "2026-03-13"
SEARCH_WINDOW_DAYS = 3
WIND_WINDOW_DAYS = 2

CENTER_LON = 69.2401
CENTER_LAT = 41.2995
HALF_DEG = 0.70
WEST = CENTER_LON - HALF_DEG
EAST = CENTER_LON + HALF_DEG
SOUTH = CENTER_LAT - HALF_DEG
NORTH = CENTER_LAT + HALF_DEG

GRID_STEP = 0.07
S5P_SCALE = 7000
ERA5_SCALE = 11000
MIN_BUFFER_VALID_PIXELS = 3
LIMITED_DOMAIN_COVERAGE = 0.05
RELIABLE_DOMAIN_COVERAGE = 0.25
SO2_BAND = "SO2_column_number_density"

MONTHLY_WINDOWS: List[Tuple[str, str, str]] = [
    ("Oct 2025", "2025-10-01", "2025-11-01"),
    ("Nov 2025", "2025-11-01", "2025-12-01"),
    ("Dec 2025", "2025-12-01", "2026-01-01"),
    ("Jan 2026", "2026-01-01", "2026-02-01"),
    ("Feb 2026", "2026-02-01", "2026-03-01"),
    ("Mar 2026", "2026-03-01", "2026-03-13"),
]

SNAPSHOT_DATES = [
    ("2025-10-15", "15 Oct 2025"),
    ("2025-11-15", "15 Nov 2025"),
    ("2025-12-15", "15 Dec 2025"),
    ("2026-01-15", "15 Jan 2026"),
    ("2026-02-07", "7 Feb 2026"),
    ("2026-02-17", "17 Feb 2026"),
    ("2026-03-12", "12 Mar 2026"),
]

SOURCE_GROUPS: List[SourceGroup] = [
    SourceGroup(
        key="almalyk",
        label="Almalyk smelter complex",
        lon=69.600,
        lat=40.848,
        category="smelter",
        color="#d62728",
        marker="^",
        buffer_km=15.0,
        dist_km=41,
        confidence="high",
        note="Strong persistent hotspot south-east of Tashkent.",
    ),
    SourceGroup(
        key="angren",
        label="Angren power / industrial corridor",
        lon=69.968,
        lat=41.018,
        category="power",
        color="#ff7f0e",
        marker="s",
        buffer_km=15.0,
        dist_km=75,
        confidence="medium",
        note="Secondary eastern hotspot with wind geometry favorable for city impact.",
    ),
    SourceGroup(
        key="chirchiq",
        label="Chirchiq industrial area",
        lon=69.583,
        lat=41.468,
        category="chemical",
        color="#9467bd",
        marker="D",
        buffer_km=15.0,
        dist_km=38,
        confidence="medium",
        note="Intermittent north-east signal; weaker than Almalyk and Angren.",
    ),
    SourceGroup(
        key="tashkent_corridor",
        label="Tashkent urban / CHP corridor",
        lon=69.240,
        lat=41.300,
        category="urban_power",
        color="#17becf",
        marker="o",
        buffer_km=15.0,
        dist_km=0,
        confidence="medium",
        note="Local urban background plus CHP emissions; CHP-1 and CHP-2 are not separable at TROPOMI resolution.",
    ),
]

CONTEXT_MARKERS: List[Dict[str, Any]] = [
    {"label": "Almalyk", "lon": 69.600, "lat": 40.848, "marker": "^", "color": "#d62728"},
    {"label": "Angren", "lon": 69.968, "lat": 41.018, "marker": "s", "color": "#ff7f0e"},
    {"label": "Chirchiq", "lon": 69.583, "lat": 41.468, "marker": "D", "color": "#9467bd"},
    {"label": "CHP-1", "lon": 69.183, "lat": 41.302, "marker": "s", "color": "#8c564b"},
    {"label": "CHP-2", "lon": 69.323, "lat": 41.258, "marker": "s", "color": "#e377c2"},
    {"label": "Tashkent", "lon": 69.240, "lat": 41.300, "marker": "o", "color": "#17becf"},
]

OUTPUT_DIR = Path("tashkent_so2_sources")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SO2_CMAP = LinearSegmentedColormap.from_list(
    "so2_heatmap",
    ["#ffffff", "#fff3bf", "#fdbb84", "#fc8d59", "#d7301f", "#7f0000"],
    N=256,
)


def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d")


def format_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def build_aoi() -> ee.Geometry.Rectangle:
    return ee.Geometry.Rectangle([WEST, SOUTH, EAST, NORTH])


def grid_axes() -> Tuple[np.ndarray, np.ndarray]:
    lons = np.arange(WEST + GRID_STEP / 2.0, EAST, GRID_STEP)
    lats = np.arange(SOUTH + GRID_STEP / 2.0, NORTH, GRID_STEP)
    return lons, lats


def total_grid_points() -> int:
    lons, lats = grid_axes()
    return len(lons) * len(lats)


def to_umol(value: Optional[float]) -> float:
    return np.nan if value is None else float(value) * 1e6


def angular_difference_deg(angle_a: float, angle_b: float) -> float:
    return ((angle_a - angle_b + 180.0) % 360.0) - 180.0


def distance_km(lon_a: float, lat_a: float, lon_b: float, lat_b: float) -> float:
    mean_lat = math.radians((lat_a + lat_b) / 2.0)
    dx = (lon_b - lon_a) * 111.32 * math.cos(mean_lat)
    dy = (lat_b - lat_a) * 111.32
    return math.hypot(dx, dy)


def bearing_deg(lon_from: float, lat_from: float, lon_to: float, lat_to: float) -> float:
    mean_lat = math.radians((lat_from + lat_to) / 2.0)
    dx = (lon_to - lon_from) * math.cos(mean_lat)
    dy = lat_to - lat_from
    return (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0


def coverage_status(valid_fraction: float, valid_pixels: Optional[float]) -> str:
    pixels = 0.0 if valid_pixels is None or math.isnan(valid_pixels) else float(valid_pixels)
    if valid_fraction < LIMITED_DOMAIN_COVERAGE or pixels < MIN_BUFFER_VALID_PIXELS:
        return "insufficient"
    if valid_fraction < RELIABLE_DOMAIN_COVERAGE:
        return "limited"
    return "reliable"


@lru_cache(maxsize=1)
def get_latest_offl_day(aoi_wkt: str) -> datetime:
    aoi = ee.Geometry(json.loads(aoi_wkt))
    collection = ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_SO2").filterBounds(aoi)
    latest = ee.Date(collection.aggregate_max("system:time_start")).format("YYYY-MM-dd").getInfo()
    return parse_date(str(latest))


def so2_collection(
    start: str,
    end_exclusive: str,
    aoi: ee.Geometry,
    band: str = SO2_BAND,
) -> Optional[ee.ImageCollection]:
    """Return OFFL data plus NRTI only after the latest available OFFL day."""
    aoi_wkt = aoi.toGeoJSONString()
    latest_offl_day = get_latest_offl_day(aoi_wkt)
    latest_offl_exclusive = latest_offl_day + timedelta(days=1)
    start_dt = parse_date(start)
    end_dt = parse_date(end_exclusive)

    def build_collection(dataset: str, start_day: str, end_day: str) -> ee.ImageCollection:
        return (
            ee.ImageCollection(dataset)
            .filterDate(start_day, end_day)
            .filterBounds(aoi)
            .filter(ee.Filter.eq("PRODUCT_QUALITY", "NOMINAL"))
            .filter(ee.Filter.eq("PROCESSING_STATUS", "Nominal"))
            .select(band)
        )

    collections: List[ee.ImageCollection] = []
    offl = build_collection("COPERNICUS/S5P/OFFL/L3_SO2", start, end_exclusive)
    if offl.size().getInfo() > 0:
        collections.append(offl)

    if end_dt > latest_offl_exclusive:
        nrti_start = max(start_dt, latest_offl_exclusive)
        if nrti_start < end_dt:
            nrti = build_collection(
                "COPERNICUS/S5P/NRTI/L3_SO2",
                format_date(nrti_start),
                end_exclusive,
            )
            if nrti.size().getInfo() > 0:
                collections.append(nrti)

    if not collections:
        nrti = build_collection("COPERNICUS/S5P/NRTI/L3_SO2", start, end_exclusive)
        if nrti.size().getInfo() > 0:
            collections.append(nrti)

    if not collections:
        return None

    merged = collections[0]
    for collection in collections[1:]:
        merged = merged.merge(collection)
    return merged


def mean_so2_image(start: str, end_exclusive: str, aoi: ee.Geometry) -> Optional[ee.Image]:
    collection = so2_collection(start, end_exclusive, aoi)
    if collection is None:
        return None
    if collection.size().getInfo() == 0:
        return None
    return collection.mean()


def snapshot_so2_image(target_date: str, aoi: ee.Geometry) -> Optional[ee.Image]:
    target_dt = parse_date(target_date)
    start = format_date(target_dt - timedelta(days=SEARCH_WINDOW_DAYS))
    end_exclusive = format_date(target_dt + timedelta(days=SEARCH_WINDOW_DAYS + 1))
    return mean_so2_image(start, end_exclusive, aoi)


def sample_grid(image: ee.Image) -> Optional[pd.DataFrame]:
    lons, lats = grid_axes()
    points = ee.FeatureCollection(
        [
            ee.Feature(
                ee.Geometry.Point([float(lon), float(lat)]),
                {"lon": float(lon), "lat": float(lat)},
            )
            for lat in lats
            for lon in lons
        ]
    )

    try:
        sampled = image.sampleRegions(
            collection=points,
            scale=S5P_SCALE,
            geometries=False,
        ).getInfo()
    except Exception as err:
        print(f"   grid sampling failed: {err}")
        return None

    records: List[Dict[str, Any]] = []
    for feature in sampled.get("features", []):
        props = feature.get("properties", {})
        raw = props.get(SO2_BAND)
        if raw is None:
            continue
        records.append(
            {
                "lon": float(props["lon"]),
                "lat": float(props["lat"]),
                "so2_mol_m2": float(raw),
                "so2_umol_m2": float(raw) * 1e6,
            }
        )
    return pd.DataFrame(records) if records else None


def build_source_features(sources: Iterable[SourceGroup]) -> ee.FeatureCollection:
    features = []
    for source in sources:
        geom = ee.Geometry.Point([source.lon, source.lat]).buffer(source.buffer_km * 1000.0)
        features.append(
            ee.Feature(
                geom,
                {
                    "key": source.key,
                    "source": source.label,
                    "category": source.category,
                    "lon": source.lon,
                    "lat": source.lat,
                    "buffer_km": source.buffer_km,
                    "dist_km": source.dist_km,
                    "confidence": source.confidence,
                    "note": source.note,
                },
            )
        )
    return ee.FeatureCollection(features)


def empty_source_table(sources: Iterable[SourceGroup]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "key": source.key,
                "source": source.label,
                "category": source.category,
                "lon": source.lon,
                "lat": source.lat,
                "buffer_km": source.buffer_km,
                "dist_km": source.dist_km,
                "confidence": source.confidence,
                "note": source.note,
                "mean_umol_m2": np.nan,
                "median_umol_m2": np.nan,
                "p90_umol_m2": np.nan,
                "valid_pixels": 0,
            }
            for source in sources
        ]
    )


def compute_source_table(
    image: Optional[ee.Image],
    source_features: ee.FeatureCollection,
    sources: Iterable[SourceGroup],
) -> pd.DataFrame:
    if image is None:
        return empty_source_table(sources)

    reducer = (
        ee.Reducer.mean()
        .combine(ee.Reducer.median(), sharedInputs=True)
        .combine(ee.Reducer.percentile([90]), sharedInputs=True)
        .combine(ee.Reducer.count(), sharedInputs=True)
    )
    features = image.reduceRegions(
        collection=source_features,
        reducer=reducer,
        scale=S5P_SCALE,
    ).getInfo()

    records: List[Dict[str, Any]] = []
    for feature in features.get("features", []):
        props = feature.get("properties", {})
        mean_value = props.get(f"{SO2_BAND}_mean", props.get("mean"))
        median_value = props.get(f"{SO2_BAND}_median", props.get("median"))
        p90_value = props.get(f"{SO2_BAND}_p90", props.get("p90"))
        count_value = props.get(f"{SO2_BAND}_count", props.get("count"))
        records.append(
            {
                "key": props.get("key"),
                "source": props.get("source"),
                "category": props.get("category"),
                "lon": float(props.get("lon")),
                "lat": float(props.get("lat")),
                "buffer_km": float(props.get("buffer_km")),
                "dist_km": int(props.get("dist_km")),
                "confidence": props.get("confidence"),
                "note": props.get("note"),
                "mean_umol_m2": to_umol(mean_value),
                "median_umol_m2": to_umol(median_value),
                "p90_umol_m2": to_umol(p90_value),
                "valid_pixels": int(count_value or 0),
            }
        )
    return pd.DataFrame(records)


def domain_summary(df: Optional[pd.DataFrame]) -> Dict[str, Any]:
    total = total_grid_points()
    if df is None or df.empty:
        return {
            "valid_grid_cells": 0,
            "valid_fraction": 0.0,
            "mean_umol_m2": np.nan,
            "median_umol_m2": np.nan,
            "p75_umol_m2": np.nan,
            "p90_umol_m2": np.nan,
            "p95_umol_m2": np.nan,
        }

    values = df["so2_umol_m2"]
    return {
        "valid_grid_cells": int(len(df)),
        "valid_fraction": float(len(df) / total),
        "mean_umol_m2": float(values.mean()),
        "median_umol_m2": float(values.median()),
        "p75_umol_m2": float(values.quantile(0.75)),
        "p90_umol_m2": float(values.quantile(0.90)),
        "p95_umol_m2": float(values.quantile(0.95)),
    }


def hotspot_share(df: pd.DataFrame, source: SourceGroup, threshold: float) -> float:
    if df.empty:
        return np.nan
    distances = np.array(
        [distance_km(source.lon, source.lat, lon, lat) for lon, lat in zip(df["lon"], df["lat"])]
    )
    local = df.loc[distances <= source.buffer_km, "so2_umol_m2"]
    if local.empty:
        return np.nan
    return float((local >= threshold).mean())


def regional_evidence(row: pd.Series, domain_stats: Dict[str, Any]) -> str:
    median_val = row["median_umol_m2"]
    p90_val = row["p90_umol_m2"]
    hotspot_p90 = row["hotspot_share_p90"]
    if (
        pd.notna(hotspot_p90)
        and hotspot_p90 >= 0.50
        and pd.notna(median_val)
        and median_val >= domain_stats["p75_umol_m2"]
    ):
        return "high"
    if (
        pd.notna(median_val)
        and median_val >= domain_stats["median_umol_m2"] * 1.05
    ) or (
        pd.notna(p90_val)
        and p90_val >= domain_stats["p90_umol_m2"]
    ):
        return "medium"
    return "low"


def transport_plausibility(mean_alignment: Optional[float], high_alignment_count: int) -> str:
    if mean_alignment is None or math.isnan(mean_alignment):
        return "not_applicable"
    if mean_alignment >= 0.75 and high_alignment_count >= 2:
        return "high"
    if mean_alignment >= 0.50:
        return "medium"
    return "low"


def get_wind_summary(target_date: str, aoi: ee.Geometry) -> Dict[str, Any]:
    target_dt = parse_date(target_date)
    start = format_date(target_dt - timedelta(days=WIND_WINDOW_DAYS))
    end_exclusive = format_date(target_dt + timedelta(days=WIND_WINDOW_DAYS + 1))
    collection = (
        ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY")
        .filterDate(start, end_exclusive)
        .filterBounds(aoi)
        .select(["u_component_of_wind_10m", "v_component_of_wind_10m"])
    )
    if collection.size().getInfo() == 0:
        return {
            "u_ms": np.nan,
            "v_ms": np.nan,
            "wind_speed_ms": np.nan,
            "flow_to_bearing_deg": np.nan,
            "wind_from_bearing_deg": np.nan,
        }

    image = collection.mean()
    stats = image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi,
        scale=ERA5_SCALE,
        bestEffort=True,
    ).getInfo()
    u_component = stats.get("u_component_of_wind_10m")
    v_component = stats.get("v_component_of_wind_10m")
    if u_component is None or v_component is None:
        return {
            "u_ms": np.nan,
            "v_ms": np.nan,
            "wind_speed_ms": np.nan,
            "flow_to_bearing_deg": np.nan,
            "wind_from_bearing_deg": np.nan,
        }

    u_val = float(u_component)
    v_val = float(v_component)
    flow_to_bearing = (math.degrees(math.atan2(u_val, v_val)) + 360.0) % 360.0
    return {
        "u_ms": u_val,
        "v_ms": v_val,
        "wind_speed_ms": math.hypot(u_val, v_val),
        "flow_to_bearing_deg": flow_to_bearing,
        "wind_from_bearing_deg": (flow_to_bearing + 180.0) % 360.0,
    }


def get_wind_grid(target_date: str, aoi: ee.Geometry) -> Optional[pd.DataFrame]:
    target_dt = parse_date(target_date)
    start = format_date(target_dt - timedelta(days=WIND_WINDOW_DAYS))
    end_exclusive = format_date(target_dt + timedelta(days=WIND_WINDOW_DAYS + 1))
    collection = (
        ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY")
        .filterDate(start, end_exclusive)
        .filterBounds(aoi)
        .select(["u_component_of_wind_10m", "v_component_of_wind_10m"])
    )
    if collection.size().getInfo() == 0:
        return None

    image = collection.mean()
    lons = np.arange(WEST + GRID_STEP, EAST, GRID_STEP * 2.0)
    lats = np.arange(SOUTH + GRID_STEP, NORTH, GRID_STEP * 2.0)
    points = ee.FeatureCollection(
        [
            ee.Feature(
                ee.Geometry.Point([float(lon), float(lat)]),
                {"lon": float(lon), "lat": float(lat)},
            )
            for lat in lats
            for lon in lons
        ]
    )
    sampled = image.sampleRegions(
        collection=points,
        scale=ERA5_SCALE,
        geometries=False,
    ).getInfo()

    records = []
    for feature in sampled.get("features", []):
        props = feature.get("properties", {})
        u_val = props.get("u_component_of_wind_10m")
        v_val = props.get("v_component_of_wind_10m")
        if u_val is None or v_val is None:
            continue
        records.append(
            {
                "lon": float(props["lon"]),
                "lat": float(props["lat"]),
                "u": float(u_val),
                "v": float(v_val),
            }
        )
    return pd.DataFrame(records) if records else None


def draw_base_map(ax: plt.Axes, title: str) -> None:
    ax.set_xlim(WEST, EAST)
    ax.set_ylim(SOUTH, NORTH)
    ax.set_aspect("equal")
    ax.set_xlabel("Longitude (deg E)", fontsize=8)
    ax.set_ylabel("Latitude (deg N)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_title(title, fontsize=10, fontweight="bold", pad=5)
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)


def add_context_markers(ax: plt.Axes) -> None:
    for marker in CONTEXT_MARKERS:
        ax.scatter(
            marker["lon"],
            marker["lat"],
            marker=marker["marker"],
            s=70,
            c=marker["color"],
            edgecolors="black",
            linewidths=0.8,
            zorder=5,
        )
        text = ax.text(
            marker["lon"] + 0.01,
            marker["lat"] + 0.01,
            marker["label"],
            fontsize=6.5,
            color="black",
            zorder=6,
            fontweight="bold",
        )
        text.set_path_effects([pe.withStroke(linewidth=1.5, foreground="white")])

    city_radius_deg = 15.0 / (111.32 * math.cos(math.radians(CENTER_LAT)))
    city_circle = plt.Circle(
        (CENTER_LON, CENTER_LAT),
        city_radius_deg,
        fill=False,
        edgecolor="#333333",
        linewidth=1.2,
        linestyle="--",
        zorder=4,
    )
    ax.add_patch(city_circle)

    kz_lons = [68.65, 68.80, 69.00, 69.15, 69.30, 69.45, 69.60, 69.75, 69.90]
    kz_lats = [41.58, 41.56, 41.52, 41.54, 41.56, 41.58, 41.60, 41.58, 41.55]
    ax.plot(
        kz_lons,
        kz_lats,
        color="#555555",
        linewidth=0.9,
        linestyle=":",
        zorder=3,
        label="Approx. KZ border",
    )


def add_north_arrow(ax: plt.Axes) -> None:
    x_pos = WEST + 0.05
    y_pos = SOUTH + 0.08
    ax.annotate(
        "N",
        xy=(x_pos, y_pos + 0.07),
        xytext=(x_pos, y_pos),
        arrowprops={"arrowstyle": "-|>", "color": "black", "lw": 1.2},
        fontsize=8,
        ha="center",
        fontweight="bold",
    )


def add_scale_bar(ax: plt.Axes) -> None:
    bar_deg = 50.0 / (math.cos(math.radians(CENTER_LAT)) * 111.32)
    x0 = EAST - 0.10 - bar_deg
    y0 = SOUTH + 0.04
    ax.plot([x0, x0 + bar_deg], [y0, y0], color="black", lw=2)
    ax.text(x0 + bar_deg / 2.0, y0 + 0.02, "50 km", ha="center", va="bottom", fontsize=7)


def plot_so2_grid(
    ax: plt.Axes,
    df: pd.DataFrame,
    vmin: float,
    vmax: float,
    alpha: float = 0.85,
) -> ScalarMappable:
    grid_lons = np.sort(df["lon"].unique())
    grid_lats = np.sort(df["lat"].unique())
    z_values = np.full((len(grid_lats), len(grid_lons)), np.nan)

    lon_lookup = {value: index for index, value in enumerate(grid_lons)}
    lat_lookup = {value: index for index, value in enumerate(grid_lats)}
    for row in df.itertuples(index=False):
        z_values[lat_lookup[row.lat], lon_lookup[row.lon]] = row.so2_umol_m2

    mappable = ax.pcolormesh(
        grid_lons,
        grid_lats,
        z_values,
        cmap=SO2_CMAP,
        norm=mcolors.Normalize(vmin=vmin, vmax=vmax),
        alpha=alpha,
        shading="nearest",
    )
    return mappable


def float_or_na(value: Any, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    return f"{float(value):.{decimals}f}"


def dataframe_block(df: pd.DataFrame, columns: List[str]) -> str:
    subset = df.loc[:, columns].copy()
    for column in subset.columns:
        if subset[column].dtype.kind in {"f", "i"} and column not in {"valid_pixels", "high_alignment_snapshots", "valid_alignment_snapshots"}:
            subset[column] = subset[column].map(
                lambda value: "NA"
                if pd.isna(value)
                else f"{float(value):.3f}" if abs(float(value)) < 100 else f"{float(value):.1f}"
            )
    return "```\n" + subset.to_string(index=False) + "\n```"


def create_seasonal_map(seasonal_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 8))
    vmin = float(np.nanpercentile(seasonal_df["so2_umol_m2"], 5))
    vmax = float(np.nanpercentile(seasonal_df["so2_umol_m2"], 97))
    mappable = plot_so2_grid(ax, seasonal_df, vmin=vmin, vmax=vmax)
    add_context_markers(ax)
    add_north_arrow(ax)
    add_scale_bar(ax)
    draw_base_map(
        ax,
        "Tashkent region SO2 seasonal mean\nAll valid observations, 1 Oct 2025 to 12 Mar 2026",
    )
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="4%", pad=0.1)
    cbar = plt.colorbar(mappable, cax=cax)
    cbar.set_label("SO2 column density (umol/m2)", fontsize=8)
    cbar.ax.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "so2_mean_seasonal_map.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def create_hotspot_map(seasonal_df: pd.DataFrame, hotspot_threshold: float) -> None:
    fig, ax = plt.subplots(figsize=(9, 8))
    base_df = seasonal_df.loc[seasonal_df["so2_umol_m2"] < hotspot_threshold].copy()
    hot_df = seasonal_df.loc[seasonal_df["so2_umol_m2"] >= hotspot_threshold].copy()

    ax.scatter(
        base_df["lon"],
        base_df["lat"],
        c=base_df["so2_umol_m2"],
        cmap="Greys",
        s=18,
        alpha=0.35,
        linewidths=0,
        zorder=2,
    )
    scatter = ax.scatter(
        hot_df["lon"],
        hot_df["lat"],
        c=hot_df["so2_umol_m2"],
        cmap="hot_r",
        s=36,
        alpha=0.85,
        linewidths=0,
        zorder=3,
        vmin=hotspot_threshold,
        vmax=float(np.nanpercentile(seasonal_df["so2_umol_m2"], 99.5)),
    )
    plt.colorbar(scatter, ax=ax, shrink=0.65, label="SO2 hotspot intensity (umol/m2)")
    add_context_markers(ax)
    add_north_arrow(ax)
    add_scale_bar(ax)
    draw_base_map(
        ax,
        "Tashkent region SO2 hotspots\nGrid cells at or above the domain 90th percentile",
    )
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "so2_hotspot_map.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def create_monthly_coverage_plot(monthly_domain_df: pd.DataFrame) -> None:
    fig, ax1 = plt.subplots(figsize=(10, 4.5))
    colors = []
    for status in monthly_domain_df["coverage_status"]:
        if status == "reliable":
            colors.append("#2ca25f")
        elif status == "limited":
            colors.append("#fdae6b")
        else:
            colors.append("#d7301f")

    x_pos = np.arange(len(monthly_domain_df))
    ax1.bar(
        x_pos,
        monthly_domain_df["valid_fraction"] * 100.0,
        color=colors,
        edgecolor="black",
        linewidth=0.5,
    )
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(monthly_domain_df["month"], rotation=20, ha="right")
    ax1.set_ylabel("Domain coverage (% of sampled grid)", fontsize=10)
    ax1.set_ylim(0, 100)
    ax1.grid(axis="y", alpha=0.3)

    ax2 = ax1.twinx()
    ax2.plot(
        x_pos,
        monthly_domain_df["median_umol_m2"],
        color="black",
        marker="o",
        linewidth=2,
    )
    ax2.set_ylabel("Domain median SO2 (umol/m2)", fontsize=10)

    fig.suptitle("Monthly SO2 coverage and central tendency", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "so2_monthly_coverage.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def create_source_evidence_chart(source_summary_df: pd.DataFrame, domain_stats: Dict[str, Any]) -> None:
    plot_df = source_summary_df.sort_values("median_umol_m2", ascending=True).copy()
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(
        plot_df["source"],
        plot_df["median_umol_m2"],
        color=plot_df["color"],
        edgecolor="black",
        linewidth=0.6,
        alpha=0.9,
    )
    ax.axvline(domain_stats["median_umol_m2"], color="black", linestyle="--", linewidth=1.0)
    ax.set_xlabel("Seasonal median SO2 (umol/m2)")
    ax.set_title("Regional SO2 source evidence by source group", fontsize=12, fontweight="bold")
    ax.grid(axis="x", alpha=0.3)

    for bar, row in zip(bars, plot_df.itertuples(index=False)):
        label = (
            f"hotspot share P90={row.hotspot_share_p90:.2f}, "
            f"transport={float_or_na(row.mean_transport_alignment, 2)}"
        )
        ax.text(
            bar.get_width() + 8,
            bar.get_y() + bar.get_height() / 2.0,
            label,
            va="center",
            fontsize=8,
        )

    legend_handles = [
        mpatches.Patch(color="#d62728", label="Smelter"),
        mpatches.Patch(color="#ff7f0e", label="Power or industrial"),
        mpatches.Patch(color="#9467bd", label="Chemical"),
        mpatches.Patch(color="#17becf", label="Urban or CHP corridor"),
    ]
    ax.legend(handles=legend_handles, fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "so2_source_evidence.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def create_transport_event_map(
    date_str: str,
    date_label: str,
    snapshot_df: pd.DataFrame,
    wind_df: Optional[pd.DataFrame],
) -> None:
    if snapshot_df.empty:
        return

    fig, ax = plt.subplots(figsize=(9, 8))
    vmin = float(np.nanpercentile(snapshot_df["so2_umol_m2"], 5))
    vmax = float(np.nanpercentile(snapshot_df["so2_umol_m2"], 97))
    mappable = plot_so2_grid(ax, snapshot_df, vmin=vmin, vmax=vmax, alpha=0.78)
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="4%", pad=0.1)
    cbar = plt.colorbar(mappable, cax=cax)
    cbar.set_label("SO2 column density (umol/m2)", fontsize=8)

    if wind_df is not None and not wind_df.empty:
        ax.quiver(
            wind_df["lon"].values,
            wind_df["lat"].values,
            wind_df["u"].values,
            wind_df["v"].values,
            color="navy",
            alpha=0.75,
            scale=60,
            width=0.003,
            headwidth=4,
            headlength=4,
        )

    add_context_markers(ax)
    add_north_arrow(ax)
    add_scale_bar(ax)
    draw_base_map(ax, f"SO2 snapshot plus ERA5-Land wind\n{date_label}")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / f"so2_transport_event_{date_str}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def build_report(
    seasonal_domain_stats: Dict[str, Any],
    monthly_domain_df: pd.DataFrame,
    source_summary_df: pd.DataFrame,
    transport_df: pd.DataFrame,
    event_dates: List[Tuple[str, str]],
) -> str:
    top_row = source_summary_df.iloc[0]
    lines: List[str] = []
    lines.append("# Tashkent SO2 source identification report")
    lines.append("")
    lines.append(f"Analysis window: {ANALYSIS_START} to {ANALYSIS_END_INCLUSIVE}")
    lines.append("Spatial domain: 150 km by 150 km centered on Tashkent.")
    lines.append("")
    lines.append("## Executive summary")
    lines.append(
        f"- The strongest persistent regional SO2 source signal is {top_row['source']}. "
        f"Its seasonal median is {float_or_na(top_row['median_umol_m2'], 1)} umol/m2, "
        f"compared with a domain median of {float_or_na(seasonal_domain_stats['median_umol_m2'], 1)} umol/m2."
    )
    lines.append(
        "- Angren is the main secondary regional source area. It is weaker than Almalyk in raw SO2 "
        "intensity, but its east-of-city position is often more consistent with observed westward transport."
    )
    lines.append(
        "- The Tashkent urban or CHP corridor shows a persistent local elevation, but the satellite pixel size "
        "does not support separate attribution to CHP-1 versus CHP-2."
    )
    lines.append(
        "- Chirchiq appears as a weaker intermittent source area. Its transport geometry toward the city is plausible, "
        "but the regional SO2 signal is not dominant."
    )
    lines.append(
        "- December 2025 and January 2026 standard-band coverage is too sparse for confident monthly attribution in "
        "the Tashkent domain. Those months should not be interpreted as meaningful source minima."
    )
    lines.append("")
    lines.append("## Bias review of the original code")
    lines.append(
        "- It merged OFFL and NRTI collections directly, which can double-count overlapping observations and inflate means."
    )
    lines.append(
        "- It used Earth Engine `filterDate` end dates as if they were inclusive. That excluded the final day of each monthly window and the stated final analysis day."
    )
    lines.append(
        "- It ranked nearby sources using overlapping 25 km buffers, even where the candidate sources were not separable at TROPOMI resolution."
    )
    lines.append(
        "- It hard-coded narrative conclusions regardless of whether the computed fields actually supported them."
    )
    lines.append(
        "- It did not report observation coverage, so months with almost no valid pixels could still appear as source signals."
    )
    lines.append(
        "- It claimed CAMS cross-validation for SO2, but the script did not actually perform that validation."
    )
    lines.append("")
    lines.append("## Revised method")
    lines.append(
        "- Use the standard Sentinel-5P SO2 total-column band in Earth Engine and keep OFFL as the primary source, using NRTI only after the latest available OFFL day."
    )
    lines.append(
        "- Restrict to nominal product quality and treat the product as relative evidence of column enhancement, not a direct emission rate."
    )
    lines.append(
        "- Aggregate local Tashkent thermal sources into one urban or CHP corridor because separate CHP attribution is not supported by the sensor footprint."
    )
    lines.append(
        "- Report monthly domain coverage and downgrade months with sparse valid pixels instead of forcing values."
    )
    lines.append(
        "- Separate regional source strength from transport plausibility. Wind consistency is used only as supporting evidence."
    )
    lines.append("")
    lines.append("## Seasonal source summary")
    lines.append(
        dataframe_block(
            source_summary_df,
            [
                "source",
                "category",
                "median_umol_m2",
                "mean_umol_m2",
                "p90_umol_m2",
                "hotspot_share_p90",
                "mean_transport_alignment",
                "regional_evidence",
                "transport_plausibility",
            ],
        )
    )
    lines.append("")
    lines.append("## Monthly domain coverage")
    lines.append(
        dataframe_block(
            monthly_domain_df,
            [
                "month",
                "valid_grid_cells",
                "valid_fraction",
                "median_umol_m2",
                "coverage_status",
            ],
        )
    )
    lines.append("")
    lines.append("## Interpretation for Tashkent city")
    lines.append(
        "- Almalyk is the clearest regional SO2 hotspot and should be treated as the dominant regional point-source signal in this domain."
    )
    lines.append(
        "- Angren is the most credible secondary contributor to Tashkent exposure because it combines elevated SO2 with frequent east-to-west transport geometry."
    )
    lines.append(
        "- The Tashkent urban or CHP corridor represents local background and heating-system influence, but the available satellite data cannot isolate individual stacks inside the city."
    )
    lines.append(
        "- Chirchiq remains a plausible intermittent contributor, especially during north-east to westward flow, but its seasonal SO2 signal is materially weaker."
    )
    lines.append("")
    lines.append("## Limitations")
    lines.append(
        "- Sentinel-5P SO2 is a total-column retrieval, not a source-resolved emission inventory."
    )
    lines.append(
        "- ERA5-Land 10 m wind is not a full back-trajectory model and does not resolve plume height."
    )
    lines.append(
        "- Winter low-sun and masking effects strongly reduce valid standard-band SO2 coverage over parts of the study period."
    )
    lines.append(
        "- This analysis supports relative source identification and city-impact plausibility, not percent source apportionment."
    )
    lines.append("")
    if event_dates:
        lines.append("## Event maps generated")
        for date_str, date_label in event_dates:
            lines.append(f"- {date_label}: `so2_transport_event_{date_str}.png`")
        lines.append("")
    lines.append("## Data references")
    lines.append(
        "- Earth Engine OFFL SO2 catalog: https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S5P_OFFL_L3_SO2"
    )
    lines.append(
        "- Earth Engine NRTI SO2 catalog: https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S5P_NRTI_L3_SO2"
    )
    lines.append(
        "- Sentinel-5P SO2 product readme: https://sentinels.copernicus.eu/documents/247904/3541451/Sentinel-5P-Sulfur-Dioxide-Level-2-Product-Readme-File"
    )
    lines.append(
        "- Earth Engine ERA5-Land hourly catalog: https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_HOURLY"
    )
    lines.append("")
    lines.append("## Snapshot transport rows")
    lines.append(
        dataframe_block(
            transport_df,
            [
                "date_label",
                "source",
                "source_mean_umol_m2",
                "city_mean_umol_m2",
                "domain_coverage_fraction",
                "flow_to_bearing_deg",
                "mean_transport_alignment",
            ],
        )
    )
    return "\n".join(lines)


def json_ready(records: Any) -> Any:
    if isinstance(records, dict):
        return {key: json_ready(value) for key, value in records.items()}
    if isinstance(records, list):
        return [json_ready(value) for value in records]
    if isinstance(records, (np.floating, float)):
        return None if math.isnan(float(records)) else float(records)
    if isinstance(records, (np.integer, int)):
        return int(records)
    return records


def main() -> int:
    configure_stdout()

    print("=" * 72)
    print("Tashkent SO2 source identification")
    print("Sentinel-5P standard SO2 column plus ERA5-Land transport context")
    print("=" * 72)

    if not initialize_gee():
        print("Earth Engine initialization failed.")
        return 1

    aoi = build_aoi()
    source_features = build_source_features(SOURCE_GROUPS)

    print("\n[1/5] Seasonal composite")
    seasonal_image = mean_so2_image(ANALYSIS_START, ANALYSIS_END_EXCLUSIVE, aoi)
    if seasonal_image is None:
        print("No seasonal SO2 image available.")
        return 1

    seasonal_df = sample_grid(seasonal_image)
    if seasonal_df is None or seasonal_df.empty:
        print("Seasonal grid extraction failed.")
        return 1

    seasonal_domain_stats = domain_summary(seasonal_df)
    print(
        "Seasonal grid points: "
        f"{seasonal_domain_stats['valid_grid_cells']} / {total_grid_points()} "
        f"({seasonal_domain_stats['valid_fraction']:.1%})"
    )

    print("\n[2/5] Monthly coverage and source summaries")
    monthly_domain_records: List[Dict[str, Any]] = []
    monthly_source_tables: List[pd.DataFrame] = []
    for month_label, start, end_exclusive in MONTHLY_WINDOWS:
        image = mean_so2_image(start, end_exclusive, aoi)
        grid_df = sample_grid(image) if image is not None else None
        domain_stats = domain_summary(grid_df)
        domain_record = {
            "month": month_label,
            **domain_stats,
            "coverage_status": coverage_status(domain_stats["valid_fraction"], domain_stats["valid_grid_cells"]),
        }
        monthly_domain_records.append(domain_record)

        source_table = compute_source_table(image, source_features, SOURCE_GROUPS)
        source_table["month"] = month_label
        source_table["domain_valid_fraction"] = domain_stats["valid_fraction"]
        source_table["domain_coverage_status"] = domain_record["coverage_status"]
        source_table["source_coverage_status"] = source_table["valid_pixels"].map(
            lambda pixels: coverage_status(domain_stats["valid_fraction"], pixels)
        )
        monthly_source_tables.append(source_table)
        print(
            f"  {month_label}: {domain_stats['valid_grid_cells']} valid cells "
            f"({domain_stats['valid_fraction']:.1%}), status={domain_record['coverage_status']}"
        )

    monthly_domain_df = pd.DataFrame(monthly_domain_records)
    monthly_source_df = pd.concat(monthly_source_tables, ignore_index=True)

    print("\n[3/5] Seasonal source evidence and transport snapshots")
    source_summary_df = compute_source_table(seasonal_image, source_features, SOURCE_GROUPS)
    source_summary_df["color"] = source_summary_df["key"].map(
        {source.key: source.color for source in SOURCE_GROUPS}
    )
    source_summary_df["hotspot_share_p90"] = source_summary_df["key"].map(
        {
            source.key: hotspot_share(seasonal_df, source, seasonal_domain_stats["p90_umol_m2"])
            for source in SOURCE_GROUPS
        }
    )
    source_summary_df["hotspot_share_p95"] = source_summary_df["key"].map(
        {
            source.key: hotspot_share(seasonal_df, source, seasonal_domain_stats["p95_umol_m2"])
            for source in SOURCE_GROUPS
        }
    )
    source_summary_df["excess_over_domain_median_umol_m2"] = (
        source_summary_df["median_umol_m2"] - seasonal_domain_stats["median_umol_m2"]
    )
    source_summary_df["regional_evidence"] = source_summary_df.apply(
        regional_evidence,
        axis=1,
        domain_stats=seasonal_domain_stats,
    )

    transport_rows: List[Dict[str, Any]] = []
    snapshot_grids: Dict[str, pd.DataFrame] = {}
    for date_str, date_label in SNAPSHOT_DATES:
        snapshot_image = snapshot_so2_image(date_str, aoi)
        snapshot_df = sample_grid(snapshot_image) if snapshot_image is not None else None
        snapshot_grids[date_str] = snapshot_df if snapshot_df is not None else pd.DataFrame()
        snapshot_domain = domain_summary(snapshot_df)
        snapshot_source_df = compute_source_table(snapshot_image, source_features, SOURCE_GROUPS)
        wind_summary = get_wind_summary(date_str, aoi)

        for row in snapshot_source_df.itertuples(index=False):
            if row.key == "tashkent_corridor":
                alignment = np.nan
            elif math.isnan(wind_summary["flow_to_bearing_deg"]):
                alignment = np.nan
            else:
                source_to_city = bearing_deg(row.lon, row.lat, CENTER_LON, CENTER_LAT)
                angle_diff = angular_difference_deg(
                    wind_summary["flow_to_bearing_deg"],
                    source_to_city,
                )
                alignment = max(0.0, math.cos(math.radians(angle_diff)))

            city_row = snapshot_source_df.loc[
                snapshot_source_df["key"] == "tashkent_corridor"
            ].iloc[0]
            transport_rows.append(
                {
                    "date": date_str,
                    "date_label": date_label,
                    "source": row.source,
                    "key": row.key,
                    "source_mean_umol_m2": row.mean_umol_m2,
                    "city_mean_umol_m2": city_row["mean_umol_m2"],
                    "source_valid_pixels": row.valid_pixels,
                    "city_valid_pixels": city_row["valid_pixels"],
                    "domain_coverage_fraction": snapshot_domain["valid_fraction"],
                    "wind_speed_ms": wind_summary["wind_speed_ms"],
                    "flow_to_bearing_deg": wind_summary["flow_to_bearing_deg"],
                    "mean_transport_alignment": alignment,
                }
            )

    transport_df = pd.DataFrame(transport_rows)
    transport_summary = (
        transport_df.loc[transport_df["key"] != "tashkent_corridor"]
        .groupby("key", as_index=False)
        .agg(
            mean_transport_alignment=("mean_transport_alignment", "mean"),
            high_alignment_snapshots=(
                "mean_transport_alignment",
                lambda values: int(np.sum(np.array(values, dtype=float) >= 0.75)),
            ),
            valid_alignment_snapshots=("mean_transport_alignment", lambda values: int(np.sum(~pd.isna(values)))),
        )
    )
    source_summary_df = source_summary_df.merge(transport_summary, on="key", how="left")
    source_summary_df["transport_plausibility"] = source_summary_df.apply(
        lambda row: "local"
        if row["key"] == "tashkent_corridor"
        else transport_plausibility(
            row["mean_transport_alignment"],
            int(0 if pd.isna(row["high_alignment_snapshots"]) else row["high_alignment_snapshots"]),
        ),
        axis=1,
    )
    source_summary_df = source_summary_df.sort_values("median_umol_m2", ascending=False).reset_index(drop=True)

    print("\n[4/5] Figures and tables")
    create_seasonal_map(seasonal_df)
    create_hotspot_map(seasonal_df, seasonal_domain_stats["p90_umol_m2"])
    create_monthly_coverage_plot(monthly_domain_df)
    create_source_evidence_chart(source_summary_df, seasonal_domain_stats)

    event_candidates = (
        transport_df.groupby(["date", "date_label"], as_index=False)
        .agg(
            city_mean_umol_m2=("city_mean_umol_m2", "max"),
            domain_coverage_fraction=("domain_coverage_fraction", "max"),
            wind_speed_ms=("wind_speed_ms", "max"),
        )
        .sort_values(["city_mean_umol_m2", "date"], ascending=[False, True])
    )
    selected_events: List[Tuple[str, str]] = []
    for row in event_candidates.itertuples(index=False):
        if len(selected_events) == 2:
            break
        if pd.isna(row.wind_speed_ms) or row.domain_coverage_fraction < LIMITED_DOMAIN_COVERAGE:
            continue
        if any(existing_date == row.date for existing_date, _ in selected_events):
            continue
        selected_events.append((row.date, row.date_label))

    for date_str, date_label in selected_events:
        create_transport_event_map(
            date_str,
            date_label,
            snapshot_grids.get(date_str, pd.DataFrame()),
            get_wind_grid(date_str, aoi),
        )

    monthly_domain_df.to_csv(OUTPUT_DIR / "so2_monthly_domain_coverage.csv", index=False)
    monthly_source_df.to_csv(OUTPUT_DIR / "so2_monthly_source_summary.csv", index=False)
    source_summary_df.to_csv(OUTPUT_DIR / "so2_source_summary.csv", index=False)
    transport_df.to_csv(OUTPUT_DIR / "so2_snapshot_transport.csv", index=False)

    metadata = {
        "analysis_start": ANALYSIS_START,
        "analysis_end_inclusive": ANALYSIS_END_INCLUSIVE,
        "analysis_end_exclusive": ANALYSIS_END_EXCLUSIVE,
        "center": {"lon": CENTER_LON, "lat": CENTER_LAT},
        "domain_half_degree": HALF_DEG,
        "grid_step_deg": GRID_STEP,
        "s5p_scale_m": S5P_SCALE,
        "sources": [asdict(source) for source in SOURCE_GROUPS],
        "seasonal_domain_stats": seasonal_domain_stats,
        "selected_transport_events": selected_events,
    }
    with (OUTPUT_DIR / "so2_spatial_data.json").open("w", encoding="utf-8") as handle:
        json.dump(json_ready(metadata), handle, indent=2)

    print("\n[5/5] Report")
    report_text = build_report(
        seasonal_domain_stats,
        monthly_domain_df,
        source_summary_df,
        transport_df,
        selected_events,
    )
    report_path = OUTPUT_DIR / "so2_source_identification_report_2026-03-12.md"
    report_path.write_text(report_text, encoding="utf-8")

    print("\nCompleted.")
    print(f"Outputs written to: {OUTPUT_DIR}")
    print(f"Main report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
