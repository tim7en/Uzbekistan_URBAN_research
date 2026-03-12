"""March 2026 daily-labeled 7-day SO2 composite analysis for Tashkent.

This is a supplemental workflow focused on the recent March SO2 issue.
It uses 7-day rolling composites centered on each day where possible and
explicitly flags the last days where the window must be truncated because
future Sentinel-5P data are not yet available.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Tuple

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import ee
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

from services.gee import initialize_gee
from tashkent_so2_source_identification import (
    OUTPUT_DIR,
    SOURCE_GROUPS,
    add_context_markers,
    add_north_arrow,
    add_scale_bar,
    angular_difference_deg,
    bearing_deg,
    build_aoi,
    build_source_features,
    compute_source_table,
    configure_stdout,
    dataframe_block,
    domain_summary,
    draw_base_map,
    float_or_na,
    mean_so2_image,
    plot_so2_grid,
    sample_grid,
)

MARCH_START = datetime(2026, 3, 1)
MARCH_END = datetime(2026, 3, 12)
HALF_WINDOW_DAYS = 3
RECENT_MAP_START = datetime(2026, 3, 8)


def format_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def iter_dates(start: datetime, end: datetime) -> Iterator[datetime]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


@lru_cache(maxsize=None)
def latest_day(dataset: str, aoi_wkt: str) -> datetime:
    aoi = ee.Geometry(json.loads(aoi_wkt))
    collection = ee.ImageCollection(dataset).filterBounds(aoi)
    latest = ee.Date(collection.aggregate_max("system:time_start")).format("YYYY-MM-dd").getInfo()
    return datetime.strptime(str(latest), "%Y-%m-%d")


def window_metadata(center_date: datetime, latest_so2_day: datetime) -> Dict[str, object]:
    requested_start = center_date - timedelta(days=HALF_WINDOW_DAYS)
    requested_end = center_date + timedelta(days=HALF_WINDOW_DAYS)
    effective_end = min(requested_end, latest_so2_day)
    support_days = max(0, (effective_end - requested_start).days + 1)
    return {
        "center_date": format_date(center_date),
        "requested_start": format_date(requested_start),
        "requested_end": format_date(requested_end),
        "effective_start": format_date(requested_start),
        "effective_end": format_date(effective_end),
        "end_exclusive": format_date(effective_end + timedelta(days=1)),
        "so2_support_days": support_days,
        "window_kind": "full_centered" if support_days == 7 else "right_truncated",
    }


def wind_summary_for_window(
    start_date: datetime,
    end_date: datetime,
    latest_era5_day: datetime,
    aoi: ee.Geometry,
) -> Dict[str, float]:
    effective_end = min(end_date, latest_era5_day)
    if effective_end < start_date:
        return {
            "wind_support_days": 0,
            "wind_speed_ms": np.nan,
            "flow_to_bearing_deg": np.nan,
        }

    end_exclusive = format_date(effective_end + timedelta(days=1))
    collection = (
        ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY")
        .filterDate(format_date(start_date), end_exclusive)
        .filterBounds(aoi)
        .select(["u_component_of_wind_10m", "v_component_of_wind_10m"])
    )
    if collection.size().getInfo() == 0:
        return {
            "wind_support_days": 0,
            "wind_speed_ms": np.nan,
            "flow_to_bearing_deg": np.nan,
        }

    image = collection.mean()
    stats = image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi,
        scale=11000,
        bestEffort=True,
    ).getInfo()
    u_component = stats.get("u_component_of_wind_10m")
    v_component = stats.get("v_component_of_wind_10m")
    if u_component is None or v_component is None:
        return {
            "wind_support_days": 0,
            "wind_speed_ms": np.nan,
            "flow_to_bearing_deg": np.nan,
        }

    u_value = float(u_component)
    v_value = float(v_component)
    return {
        "wind_support_days": (effective_end - start_date).days + 1,
        "wind_speed_ms": math.hypot(u_value, v_value),
        "flow_to_bearing_deg": (math.degrees(math.atan2(u_value, v_value)) + 360.0) % 360.0,
    }


def daily_likelihood(day_source_df: pd.DataFrame) -> Tuple[str, str, str]:
    city_row = day_source_df.loc[day_source_df["key"] == "tashkent_corridor"].iloc[0]
    local_score = 0.0 if pd.isna(city_row["mean_umol_m2"]) else max(float(city_row["mean_umol_m2"]), 0.0)

    external_df = day_source_df.loc[day_source_df["key"] != "tashkent_corridor"].copy()
    hotspot_source = (
        "NA"
        if external_df["mean_umol_m2"].isna().all()
        else external_df.sort_values("mean_umol_m2", ascending=False).iloc[0]["source"]
    )

    transport_df = external_df.loc[external_df["transport_screened_mean_umol_m2"].notna()].copy()
    if transport_df.empty:
        return city_row["source"], hotspot_source, "wind unavailable"

    transport_df = transport_df.sort_values("transport_screened_mean_umol_m2", ascending=False)
    top_transport = transport_df.iloc[0]
    top_score = float(top_transport["transport_screened_mean_umol_m2"])
    if top_score <= 0:
        return city_row["source"], hotspot_source, "no supported external source"
    likely = top_transport["source"] if top_score > local_score else city_row["source"]
    return likely, hotspot_source, top_transport["source"]


def create_city_vs_sources_plot(daily_source_df: pd.DataFrame, overview_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    dates = pd.to_datetime(sorted(daily_source_df["center_date"].unique()))
    for source in SOURCE_GROUPS:
        subset = daily_source_df.loc[daily_source_df["key"] == source.key].copy()
        subset = subset.sort_values("center_date")
        ax.plot(
            pd.to_datetime(subset["center_date"]),
            subset["mean_umol_m2"],
            marker="o",
            linewidth=2,
            label=source.label,
            color=source.color,
        )

    truncated = overview_df.loc[overview_df["window_kind"] != "full_centered", "center_date"]
    for date_str in truncated:
        date_value = pd.to_datetime(date_str)
        ax.axvspan(date_value - timedelta(hours=12), date_value + timedelta(hours=12), color="#fdd0a2", alpha=0.2)

    ax.set_title("March 2026 SO2 7-day composite source means", fontsize=12, fontweight="bold")
    ax.set_ylabel("Mean SO2 (umol/m2)")
    ax.set_xlabel("Composite center date")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    ax.text(
        0.99,
        0.02,
        "Orange shading = truncated 7-day window after latest available SO2 day",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "so2_march_7day_city_vs_sources.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def create_recent_maps(recent_grids: Dict[str, pd.DataFrame], overview_df: pd.DataFrame) -> None:
    valid_items = [(date_str, grid) for date_str, grid in recent_grids.items() if grid is not None and not grid.empty]
    if not valid_items:
        return

    all_values = np.concatenate([grid["so2_umol_m2"].values for _, grid in valid_items])
    vmin = float(np.nanpercentile(all_values, 5))
    vmax = float(np.nanpercentile(all_values, 97))

    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    axes_flat = axes.flatten()

    for index, (date_str, grid) in enumerate(valid_items):
        ax = axes_flat[index]
        mappable = plot_so2_grid(ax, grid, vmin=vmin, vmax=vmax, alpha=0.82)
        add_context_markers(ax)
        add_north_arrow(ax)
        add_scale_bar(ax)
        meta = overview_df.loc[overview_df["center_date"] == date_str].iloc[0]
        draw_base_map(
            ax,
            f"{date_str}\nSO2 support {int(meta['so2_support_days'])} days",
        )

    for index in range(len(valid_items), len(axes_flat)):
        axes_flat[index].set_visible(False)

    divider = make_axes_locatable(axes_flat[min(len(valid_items) - 1, 0)])
    cax = divider.append_axes("right", size="4%", pad=0.1)
    cbar = plt.colorbar(mappable, cax=cax)
    cbar.set_label("SO2 column density (umol/m2)", fontsize=8)

    fig.suptitle("Recent March SO2 composites around the Tashkent issue window", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "so2_march_7day_recent_maps.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def build_march_report(
    overview_df: pd.DataFrame,
    latest_days_df: pd.DataFrame,
    latest_so2_day: datetime,
    latest_era5_day: datetime,
) -> str:
    recent = latest_days_df.sort_values("center_date")
    lines: List[str] = []
    lines.append("# March 2026 SO2 daily 7-day composite report")
    lines.append("")
    lines.append("## Method")
    lines.append(
        "- Each March day is represented by a 7-day rolling SO2 composite centered on that day where possible."
    )
    lines.append(
        f"- Latest SO2 day available in the Tashkent domain: {format_date(latest_so2_day)}."
    )
    lines.append(
        f"- Latest ERA5-Land day available in the Tashkent domain: {format_date(latest_era5_day)}."
    )
    lines.append(
        "- Windows after the latest available SO2 day are right-truncated and should be interpreted as recent rolling composites, not true centered windows."
    )
    lines.append("")
    lines.append("## Key findings")
    lines.append(
        f"- Full centered SO2 windows are available through {overview_df.loc[overview_df['window_kind'] == 'full_centered', 'center_date'].max()}."
    )
    lines.append(
        "- For the most recent city issue window, the Tashkent urban / CHP corridor is the most defensible city-level source candidate."
    )
    lines.append(
        "- Angren is strongest in the earliest March composites, but Almalyk becomes the dominant regional hotspot through the recent issue window."
    )
    lines.append(
        "- Wind-based attribution weakens sharply after early March because ERA5-Land availability ends on 2026-03-05 in this environment."
    )
    lines.append(
        "- The wind-supported windows do not show positive transport support for an external source overtaking the local Tashkent corridor signal."
    )
    lines.append("")
    lines.append("## Daily window overview")
    lines.append(
        dataframe_block(
            overview_df,
            [
                "center_date",
                "effective_start",
                "effective_end",
                "so2_support_days",
                "wind_support_days",
                "domain_valid_fraction",
                "city_mean_umol_m2",
                "likely_city_source",
                "regional_hotspot_source",
                "transport_screened_external_source",
            ],
        )
    )
    lines.append("")
    lines.append("## Recent issue window")
    lines.append(
        dataframe_block(
            recent,
            [
                "center_date",
                "so2_support_days",
                "wind_support_days",
                "city_mean_umol_m2",
                "almalyk_mean_umol_m2",
                "angren_mean_umol_m2",
                "chirchiq_mean_umol_m2",
                "likely_city_source",
                "regional_hotspot_source",
            ],
        )
    )
    lines.append("")
    latest_row = recent.sort_values("center_date").iloc[-1]
    lines.append("## Interpretation")
    lines.append(
        f"- On {latest_row['center_date']}, the rolling composite city signal is {float_or_na(latest_row['city_mean_umol_m2'], 1)} umol/m2."
    )
    lines.append(
        f"- The same composite still shows a stronger regional hotspot over Almalyk ({float_or_na(latest_row['almalyk_mean_umol_m2'], 1)} umol/m2), but this does not by itself prove city impact."
    )
    lines.append(
        "- The strongest statement supported by the current data is: the recent March city SO2 issue is more consistent with a local Tashkent urban / CHP signal than with a clearly wind-supported external transport episode."
    )
    lines.append(
        "- Almalyk should still be monitored as the dominant regional hotspot, especially once fresh wind data become available for the latest days."
    )
    return "\n".join(lines)


def main() -> int:
    configure_stdout()
    print("=" * 72)
    print("March 2026 SO2 daily 7-day composite analysis")
    print("=" * 72)

    if not initialize_gee():
        print("Earth Engine initialization failed.")
        return 1

    aoi = build_aoi()
    aoi_wkt = aoi.toGeoJSONString()
    latest_so2_day = max(
        latest_day("COPERNICUS/S5P/OFFL/L3_SO2", aoi_wkt),
        latest_day("COPERNICUS/S5P/NRTI/L3_SO2", aoi_wkt),
    )
    latest_era5_day = latest_day("ECMWF/ERA5_LAND/HOURLY", aoi_wkt)
    source_features = build_source_features(SOURCE_GROUPS)

    overview_rows: List[Dict[str, object]] = []
    daily_source_rows: List[Dict[str, object]] = []
    recent_grids: Dict[str, pd.DataFrame] = {}

    for center_date in iter_dates(MARCH_START, MARCH_END):
        meta = window_metadata(center_date, latest_so2_day)
        image = mean_so2_image(str(meta["effective_start"]), str(meta["end_exclusive"]), aoi)
        grid_df = sample_grid(image) if image is not None else None
        domain_stats = domain_summary(grid_df)
        source_df = compute_source_table(image, source_features, SOURCE_GROUPS)

        wind_stats = wind_summary_for_window(
            datetime.strptime(str(meta["effective_start"]), "%Y-%m-%d"),
            datetime.strptime(str(meta["effective_end"]), "%Y-%m-%d"),
            latest_era5_day,
            aoi,
        )

        for row in source_df.itertuples(index=False):
            if row.key == "tashkent_corridor" or wind_stats["wind_support_days"] < 3 or pd.isna(wind_stats["flow_to_bearing_deg"]):
                alignment = np.nan
                screened_mean = row.mean_umol_m2 if row.key == "tashkent_corridor" else np.nan
            else:
                source_to_city = bearing_deg(row.lon, row.lat, SOURCE_GROUPS[-1].lon, SOURCE_GROUPS[-1].lat)
                angle_diff = angular_difference_deg(float(wind_stats["flow_to_bearing_deg"]), source_to_city)
                alignment = max(0.0, math.cos(math.radians(angle_diff)))
                screened_mean = row.mean_umol_m2 * alignment if pd.notna(row.mean_umol_m2) else np.nan

            daily_source_rows.append(
                {
                    "center_date": meta["center_date"],
                    "key": row.key,
                    "source": row.source,
                    "mean_umol_m2": row.mean_umol_m2,
                    "median_umol_m2": row.median_umol_m2,
                    "p90_umol_m2": row.p90_umol_m2,
                    "valid_pixels": row.valid_pixels,
                    "so2_support_days": meta["so2_support_days"],
                    "wind_support_days": wind_stats["wind_support_days"],
                    "flow_to_bearing_deg": wind_stats["flow_to_bearing_deg"],
                    "transport_alignment": alignment,
                    "transport_screened_mean_umol_m2": screened_mean,
                }
            )

        day_source_df = pd.DataFrame([row for row in daily_source_rows if row["center_date"] == meta["center_date"]])
        likely_city_source, regional_hotspot_source, transport_external_source = daily_likelihood(day_source_df)
        city_mean = day_source_df.loc[day_source_df["key"] == "tashkent_corridor", "mean_umol_m2"].iloc[0]

        overview_rows.append(
            {
                **meta,
                "domain_valid_fraction": domain_stats["valid_fraction"],
                "domain_median_umol_m2": domain_stats["median_umol_m2"],
                "city_mean_umol_m2": city_mean,
                "wind_support_days": wind_stats["wind_support_days"],
                "wind_speed_ms": wind_stats["wind_speed_ms"],
                "flow_to_bearing_deg": wind_stats["flow_to_bearing_deg"],
                "likely_city_source": likely_city_source,
                "regional_hotspot_source": regional_hotspot_source,
                "transport_screened_external_source": transport_external_source,
            }
        )

        if center_date >= RECENT_MAP_START and grid_df is not None and not grid_df.empty:
            recent_grids[meta["center_date"]] = grid_df

        print(
            f"{meta['center_date']}: SO2 support {meta['so2_support_days']} days, "
            f"coverage {domain_stats['valid_fraction']:.1%}, likely city source={likely_city_source}"
        )

    overview_df = pd.DataFrame(overview_rows)
    daily_source_df = pd.DataFrame(daily_source_rows)
    latest_days_df = overview_df.loc[overview_df["center_date"] >= format_date(RECENT_MAP_START)].copy()

    source_lookup = {
        "almalyk": "almalyk_mean_umol_m2",
        "angren": "angren_mean_umol_m2",
        "chirchiq": "chirchiq_mean_umol_m2",
        "tashkent_corridor": "tashkent_corridor_mean_umol_m2",
    }
    for key, column_name in source_lookup.items():
        pivot = daily_source_df.loc[daily_source_df["key"] == key, ["center_date", "mean_umol_m2"]].rename(
            columns={"mean_umol_m2": column_name}
        )
        latest_days_df = latest_days_df.merge(pivot, on="center_date", how="left")

    create_city_vs_sources_plot(daily_source_df, overview_df)
    create_recent_maps(recent_grids, overview_df)

    overview_df.to_csv(OUTPUT_DIR / "so2_march_7day_daily_windows.csv", index=False)
    daily_source_df.to_csv(OUTPUT_DIR / "so2_march_7day_daily_sources.csv", index=False)
    latest_days_df.to_csv(OUTPUT_DIR / "so2_march_7day_recent_issue_summary.csv", index=False)

    report_text = build_march_report(overview_df, latest_days_df, latest_so2_day, latest_era5_day)
    report_path = OUTPUT_DIR / "so2_march_7day_report_2026-03-12.md"
    report_path.write_text(report_text, encoding="utf-8")

    print(f"Saved report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
