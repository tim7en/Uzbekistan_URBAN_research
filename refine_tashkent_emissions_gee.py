"""Refine Uzbekistan regional emissions estimates for Tashkent using
ESRI 10m LULC and VIIRS nightlight data via Google Earth Engine.

Methodology
-----------
1. Load GAUL Level-1 boundaries for Uzbekistan to get Tashkent City and
   Tashkent Region (oblast) polygons.
2. Extract ESRI 10m LULC class areas (2022) for each admin unit.
3. Extract VIIRS monthly nightlight mean radiance (2022) for each unit.
4. Read the proxy-based regional emissions from the Excel workbook.
5. Apply a refinement algorithm:
   - Built-up area fraction -> weight residential, commercial, transport sectors
   - Cropland fraction       -> weight agriculture sector
   - Tree fraction           -> validate / adjust LULUCF sink
   - Nightlight mean         -> weight industry combustion, IPPU, transport
6. Compute refined emission estimates and a spatial confidence metric.
7. Export results to CSV and JSON with uncertainty notes.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import json
import math
import time
import argparse
import pandas as pd
import numpy as np
import ee

from services import gee as gee_svc
from services.utils import make_json_safe

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_DIR = ROOT / "suhi_analysis_output" / "emissions_refinement"

# ESRI LULC class codes (same as services/utils.py ESRI_CLASSES)
ESRI_CLASSES = {
    1: "Water",
    2: "Trees",
    4: "Flooded_Vegetation",
    5: "Crops",
    7: "Built_Area",
    8: "Bare_Ground",
    9: "Snow_Ice",
    10: "Clouds",
    11: "Rangeland",
}

# Emission-sector → LULC proxy weights  (must sum to 1 across the primary proxies)
# Values represent what fraction of the sector's within-region allocation
# should be driven by each LULC/nightlight signal vs. the prior (GDP/pop proxy).
# blend_lulc + blend_nl + blend_prior = 1
SECTOR_PROXIES = {
    # sector_key : {lulc_class: weight, ..., "_nightlight": weight, "_prior": weight}
    "electricity_heat": {
        "Built_Area": 0.20,
        "_nightlight": 0.50,
        "_prior":      0.30,
    },
    "residential_commercial": {
        "Built_Area": 0.55,
        "_nightlight": 0.20,
        "_prior":      0.25,
    },
    "industry_combustion": {
        "Built_Area": 0.15,
        "Bare_Ground": 0.05,
        "_nightlight": 0.50,
        "_prior":      0.30,
    },
    "transport": {
        "Built_Area": 0.35,
        "_nightlight": 0.35,
        "_prior":      0.30,
    },
    "fugitive_emissions": {
        # Fugitive (gas/coal) driven mostly by known infrastructure -> prior dominant
        "_nightlight": 0.25,
        "_prior":      0.75,
    },
    "ippu": {
        "Bare_Ground": 0.10,
        "_nightlight": 0.50,
        "_prior":      0.40,
    },
    "agriculture": {
        "Crops":              0.45,
        "Flooded_Vegetation": 0.20,
        "_prior":             0.35,
    },
    "waste": {
        "Built_Area": 0.45,
        "_prior":     0.55,
    },
    "lulucf": {
        # Sink: trees dominate
        "Trees":    0.65,
        "Rangeland": 0.10,
        "_prior":    0.25,
    },
}

# Tashkent units to include (GAUL NAME_1 strings as they appear in the dataset)
TASHKENT_UNITS = {
    "Tashkent City": "Toshkent",        # City (Shahar)
    "Tashkent Region": "Toshkent",      # Oblast - same NAME_1; distinguished by TYPE
}

# Emission columns in the Excel "Emissions by Region" sheet (0-indexed col numbers)
EMISSION_COLS = {
    "region":                   0,
    "electricity_heat":         1,
    "residential_commercial":   2,
    "industry_combustion":      3,
    "transport":                4,
    "fugitive_emissions":       5,
    "ippu":                     6,
    "agriculture":              7,
    "waste":                    8,
    "lulucf":                   9,
    "total":                    10,
    "national_share":           11,
    "net_total":                12,
}


# ---------------------------------------------------------------------------
# GEE helpers
# ---------------------------------------------------------------------------

def get_admin_boundaries() -> dict[str, ee.Geometry]:
    """Return EE geometries for Tashkent City and Tashkent Region from GAUL."""
    gaul = ee.FeatureCollection("FAO/GAUL/2015/level1")
    uzbekistan = gaul.filter(ee.Filter.eq("ADM0_NAME", "Uzbekistan"))

    # Tashkent City appears as a separate level-1 feature; its name differs
    # slightly across datasets.  We try multiple spellings.
    city_candidates = [
        ee.Filter.stringContains("ADM1_NAME", "Toshkent City"),
        ee.Filter.stringContains("ADM1_NAME", "Tashkent City"),
        ee.Filter.stringContains("ADM1_NAME", "Toshkent Shahri"),
    ]
    region_candidates = [
        ee.Filter.And(
            ee.Filter.stringContains("ADM1_NAME", "Toshkent"),
            ee.Filter.Not(ee.Filter.stringContains("ADM1_NAME", "City")),
            ee.Filter.Not(ee.Filter.stringContains("ADM1_NAME", "Shahri")),
        ),
        ee.Filter.And(
            ee.Filter.stringContains("ADM1_NAME", "Tashkent"),
            ee.Filter.Not(ee.Filter.stringContains("ADM1_NAME", "City")),
        ),
    ]

    def _try_filters(fc, candidates):
        for f in candidates:
            subset = fc.filter(f)
            try:
                if subset.size().getInfo() > 0:
                    return subset.geometry()
            except Exception:
                continue
        return None

    geoms = {}
    geoms["Tashkent City"] = _try_filters(uzbekistan, city_candidates)
    geoms["Tashkent Region"] = _try_filters(uzbekistan, region_candidates)

    # Fallback: bounding-box buffers if GAUL lookup fails
    fallbacks = {
        "Tashkent City": ee.Geometry.Point([69.2401, 41.2995]).buffer(20_000).bounds(),
        "Tashkent Region": ee.Geometry.Point([69.5, 41.2]).buffer(150_000).bounds(),
    }
    for name in ("Tashkent City", "Tashkent Region"):
        if geoms[name] is None:
            print(f"  WARNING: GAUL lookup failed for '{name}'; using fallback buffer.")
            geoms[name] = fallbacks[name]

    return geoms


def extract_lulc_stats(geom: ee.Geometry, year: int = 2022, scale: int = 100) -> dict:
    """Return ESRI LULC class areas (km²) and fractional composition for a geometry."""
    esri_col = ee.ImageCollection("projects/sat-io/open-datasets/landcover/ESRI_Global-LULC_10m_TS")
    y = max(2017, min(2024, year))
    img = (esri_col
           .filterDate(f"{y}-01-01", f"{y}-12-31")
           .filterBounds(geom)
           .mosaic()
           .clip(geom))

    # Frequency histogram at the native 10m resolution via reduceRegion
    band = img.bandNames().getInfo()[0]
    hist_dict = (img
                 .select(band)
                 .reduceRegion(
                     reducer=ee.Reducer.frequencyHistogram(),
                     geometry=geom,
                     scale=scale,
                     maxPixels=1e9,
                     bestEffort=True,
                 )
                 .get(band)
                 .getInfo())

    if not hist_dict:
        return {"error": "empty histogram", "classes": {}, "total_area_km2": 0}

    # Convert pixel counts → km² (scale² metres² per pixel → / 1e6 for km²)
    px_area_km2 = (scale * scale) / 1e6
    classes = {}
    total_px = sum(hist_dict.values())
    total_km2 = total_px * px_area_km2
    for class_id_str, count in hist_dict.items():
        cid = int(float(class_id_str))
        name = ESRI_CLASSES.get(cid, f"Unknown_{cid}")
        area_km2 = count * px_area_km2
        classes[name] = {
            "class_id": cid,
            "area_km2": round(area_km2, 4),
            "fraction": round(area_km2 / total_km2, 6) if total_km2 > 0 else 0,
        }

    return {"classes": classes, "total_area_km2": round(total_km2, 4)}


def extract_nightlight_stats(geom: ee.Geometry, year: int = 2022, scale: int = 500) -> dict:
    """Return VIIRS DNB mean, median, and P90 radiance for the geometry (2022)."""
    col = (ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG")
           .filterDate(f"{year}-01-01", f"{year}-12-31")
           .filterBounds(geom)
           .select("avg_rad"))

    annual_median = col.median().clip(geom)

    reducers = (ee.Reducer.mean()
                .combine(ee.Reducer.median(), sharedInputs=True)
                .combine(ee.Reducer.percentile([90]), sharedInputs=True)
                .combine(ee.Reducer.stdDev(), sharedInputs=True))

    result = annual_median.reduceRegion(
        reducer=reducers,
        geometry=geom,
        scale=scale,
        maxPixels=1e8,
        bestEffort=True,
    ).getInfo()

    return {k: (round(v, 6) if v is not None else None) for k, v in result.items()}


# ---------------------------------------------------------------------------
# Data reading
# ---------------------------------------------------------------------------

def load_emissions_excel(xlsx_path: Path) -> pd.DataFrame:
    """Read the 'Emissions by Region' sheet and return a tidy DataFrame.

    Uses openpyxl with data_only=True so that formula cells return their last
    cached values (e.g. total, national_share, net_total columns).
    """
    import openpyxl

    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb["Emissions by Region"]

    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    # Find the header row — it contains the literal string "Region"
    header_row_idx = None
    for i, row in enumerate(rows):
        if any(v is not None and "Region" in str(v) for v in row):
            header_row_idx = i
            break
    if header_row_idx is None:
        raise ValueError("Could not locate header row in 'Emissions by Region' sheet")

    # Build DataFrame from rows after the header
    data_rows = rows[header_row_idx + 1:]
    n_cols = max(len(r) for r in data_rows) if data_rows else 13
    records = []
    for row in data_rows:
        padded = list(row) + [None] * (n_cols - len(row))
        records.append(padded)

    df = pd.DataFrame(records, columns=range(n_cols))

    # Rename positional columns using EMISSION_COLS mapping
    rename = {v: k for k, v in EMISSION_COLS.items()}
    df = df.rename(columns=rename)

    # Keep only columns we care about
    keep = list(EMISSION_COLS.keys())
    available = [c for c in keep if c in df.columns]
    df = df[available].copy()

    # Clean region column
    df["region"] = df["region"].astype(str).str.strip()

    # Remove non-data rows: nulls, formula artefacts, aggregates, metadata
    exclude_patterns = ["nan", "None", "Note", "Source", "SUM OF", "NATIONAL",
                        "Allocation Method"]
    mask = df["region"].notna()
    for pat in exclude_patterns:
        mask &= ~df["region"].str.startswith(pat)
    df = df[mask].copy()

    # Coerce numeric columns; formula strings (=SUM...) will become NaN
    num_cols = [c for c in available if c != "region"]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def find_tashkent_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Filter rows for Tashkent City and Tashkent Region."""
    mask = df["region"].str.contains("Tashkent", case=False, na=False)
    result = df[mask].copy()
    if result.empty:
        # Try Uzbek spelling
        mask2 = df["region"].str.contains("Toshkent", case=False, na=False)
        result = df[mask2].copy()
    return result


# ---------------------------------------------------------------------------
# Refinement engine
# ---------------------------------------------------------------------------

def _lulc_fraction(lulc_stats: dict, class_name: str) -> float:
    """Return the fractional area of a LULC class (0–1); 0 if missing."""
    return lulc_stats.get("classes", {}).get(class_name, {}).get("fraction", 0.0)


def _nightlight_score(nl_stats: dict, nl_max: float) -> float:
    """Normalise nightlight mean radiance to [0, 1] using the regional maximum."""
    mean_key = [k for k in nl_stats if "mean" in k.lower()]
    if not mean_key or nl_max == 0:
        return 0.0
    raw = nl_stats.get(mean_key[0], 0.0) or 0.0
    return min(raw / nl_max, 1.0)


def refine_row(
    row: pd.Series,
    lulc: dict,
    nl: dict,
    nl_score: float,
    sector_proxies: dict = SECTOR_PROXIES,
) -> dict:
    """Return a dict of refined emission values for a single region row.

    For each sector we blend:
      refined = Σ_lulc (lulc_weight * lulc_fraction * prior)
              + nl_weight * nl_score * prior
              + prior_weight * prior

    where prior is the original proxy-based estimate from the Excel.
    The formula is a weighted convex combination of adjustment signals.
    """
    refined = {}
    adjustments = {}

    for sector, proxies in sector_proxies.items():
        prior = row.get(sector, np.nan)
        if pd.isna(prior):
            refined[sector] = np.nan
            adjustments[sector] = {"prior": np.nan, "adjustment_factor": None, "signal_breakdown": {}}
            continue

        lulc_total_weight = sum(v for k, v in proxies.items() if not k.startswith("_"))
        nl_weight   = proxies.get("_nightlight", 0.0)
        prior_weight = proxies.get("_prior", 0.0)

        # Weighted signal from LULC classes
        lulc_signal = 0.0
        signal_breakdown = {}
        for class_name, weight in proxies.items():
            if class_name.startswith("_"):
                continue
            frac = _lulc_fraction(lulc, class_name)
            contribution = weight * frac
            lulc_signal += contribution
            signal_breakdown[class_name] = {
                "weight": weight,
                "fraction": round(frac, 5),
                "contribution": round(contribution, 6),
            }

        # Combined adjustment factor (deviation from naive 1.0)
        # lulc_signal is already a weighted sum of fractions (0–lulc_total_weight)
        # normalise to [0, lulc_total_weight] then blend with nl and prior at 1.0
        # so that adjustment_factor = 1.0 → no change
        if lulc_total_weight > 0:
            lulc_component = (lulc_signal / lulc_total_weight) if lulc_total_weight else 0
        else:
            lulc_component = 0.0

        # Adjustment factor blends LULC intensity, NL intensity, and the prior (=1)
        adj_factor = (
            lulc_total_weight * lulc_component
            + nl_weight * nl_score
            + prior_weight * 1.0
        )
        # adj_factor ≈ 1.0 when signals are neutral; > 1 when the area is more
        # active than average; < 1 when less active.

        refined_value = prior * adj_factor
        refined[sector] = round(refined_value, 6)
        adjustments[sector] = {
            "prior_Mt": round(prior, 6),
            "refined_Mt": round(refined_value, 6),
            "adjustment_factor": round(adj_factor, 4),
            "lulc_component": round(lulc_component, 4),
            "nl_score": round(nl_score, 4),
            "signal_breakdown": signal_breakdown,
        }

    return {"refined": refined, "adjustments": adjustments}


def compute_confidence(lulc_stats: dict, nl_stats: dict) -> dict:
    """Compute a simple confidence metric (0–100) for the spatial refinement."""
    # 1. LULC coverage: did we get a valid histogram?
    lulc_ok = bool(lulc_stats.get("classes")) and lulc_stats.get("total_area_km2", 0) > 0
    # 2. Nightlight: did we get a valid mean?
    nl_keys = [k for k in nl_stats if "mean" in k.lower()]
    nl_ok = bool(nl_keys) and nl_stats.get(nl_keys[0]) is not None

    score = 0
    notes = []
    if lulc_ok:
        score += 60
        n_classes = len(lulc_stats["classes"])
        if n_classes >= 5:
            score += 10
            notes.append(f"ESRI LULC: {n_classes} classes detected")
        else:
            notes.append(f"ESRI LULC: only {n_classes} classes (partial coverage?)")
    else:
        notes.append("ESRI LULC data missing or empty")

    if nl_ok:
        score += 25
        notes.append("VIIRS nightlights: valid annual median")
    else:
        notes.append("VIIRS nightlights: data missing")

    # Bonus for high-resolution LULC area match
    if lulc_ok and lulc_stats["total_area_km2"] > 500:
        score += 5
        notes.append("LULC area > 500 km² — good regional coverage")

    return {"score": min(score, 100), "notes": notes}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Refine Tashkent regional emissions using ESRI LULC + VIIRS")
    p.add_argument("--year", type=int, default=2022, help="Analysis year (default 2022)")
    p.add_argument("--lulc-scale", type=int, default=100,
                   help="ESRI LULC reduction scale in metres (default 100; use 50 for more detail but slower)")
    p.add_argument("--nl-scale", type=int, default=500,
                   help="Nightlight reduction scale in metres (default 500)")
    p.add_argument("--xlsx", type=str,
                   default=str(ROOT / "uzbekistan_emissions_by_region_2022 (1)+.xlsx"),
                   help="Path to the emissions Excel file")
    p.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR))
    return p.parse_args()


def main():
    args = parse_args()
    year = args.year
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # -- GEE init -----------------------------------------------------------
    print("Initializing Google Earth Engine...")
    if not gee_svc.initialize_gee():
        print("ERROR: GEE initialization failed. Aborting.")
        sys.exit(1)
    print("GEE ready.\n")

    # -- Load emissions data ------------------------------------------------
    xlsx_path = Path(args.xlsx)
    print(f"Loading emissions data from: {xlsx_path.name}")
    df_all = load_emissions_excel(xlsx_path)
    df_tash = find_tashkent_rows(df_all)
    if df_tash.empty:
        print("ERROR: No Tashkent rows found in the emissions sheet.")
        print("Available regions:", df_all["region"].tolist())
        sys.exit(1)
    print(f"Found {len(df_tash)} Tashkent row(s):")
    for _, r in df_tash.iterrows():
        print(f"  {r['region']}")

    # -- Get admin boundaries -----------------------------------------------
    print("\nFetching GAUL admin boundaries...")
    geoms = get_admin_boundaries()
    for name, geom in geoms.items():
        if geom is None:
            print(f"  WARNING: geometry for '{name}' is None — will skip.")
        else:
            try:
                area = geom.area().getInfo() / 1e6
                print(f"  {name}: ~{area:,.0f} km2")
            except Exception as e:
                print(f"  {name}: geometry obtained (area query failed: {e})")

    # -- Extract ESRI LULC stats -------------------------------------------
    print(f"\nExtracting ESRI LULC statistics for {year} (scale={args.lulc_scale}m)...")
    lulc_results = {}
    for unit_name, geom in geoms.items():
        if geom is None:
            lulc_results[unit_name] = {"error": "no geometry"}
            continue
        print(f"  Processing LULC for {unit_name}...")
        try:
            lulc_results[unit_name] = extract_lulc_stats(geom, year=year, scale=args.lulc_scale)
            classes_found = list(lulc_results[unit_name].get("classes", {}).keys())
            print(f"    Classes: {classes_found}")
            print(f"    Total area: {lulc_results[unit_name].get('total_area_km2', 0):,.1f} km2")
        except Exception as e:
            print(f"    ERROR: {e}")
            lulc_results[unit_name] = {"error": str(e)}
        time.sleep(2)

    # -- Extract VIIRS nightlight stats ------------------------------------
    print(f"\nExtracting VIIRS nightlight statistics for {year} (scale={args.nl_scale}m)...")
    nl_results = {}
    for unit_name, geom in geoms.items():
        if geom is None:
            nl_results[unit_name] = {"error": "no geometry"}
            continue
        print(f"  Processing nightlights for {unit_name}...")
        try:
            nl_results[unit_name] = extract_nightlight_stats(geom, year=year, scale=args.nl_scale)
            print(f"    Stats: {nl_results[unit_name]}")
        except Exception as e:
            print(f"    ERROR: {e}")
            nl_results[unit_name] = {"error": str(e)}
        time.sleep(2)

    # -- Compute nightlight normalisation -----------------------------------
    nl_means = []
    for unit_name, stats in nl_results.items():
        mean_key = [k for k in stats if "mean" in k.lower()]
        if mean_key and stats.get(mean_key[0]) is not None:
            nl_means.append(stats[mean_key[0]])
    nl_max = max(nl_means) if nl_means else 1.0
    print(f"\nNightlight normalisation max: {nl_max:.4f} nW/cm2/sr")

    # -- Apply refinement --------------------------------------------------
    print("\nApplying spatial refinement to Tashkent emission estimates...")
    all_results = []

    for _, row in df_tash.iterrows():
        region_name = row["region"]
        print(f"\n  Region: {region_name}")

        # Match to the appropriate geometry
        # "Tashkent City" rows → City geometry; "Tashkent Region" → Region geometry
        if "City" in region_name or "Shahar" in region_name or "Shahri" in region_name:
            unit_key = "Tashkent City"
        else:
            unit_key = "Tashkent Region"

        lulc = lulc_results.get(unit_key, {})
        nl   = nl_results.get(unit_key, {})

        # Compute nightlight score for this unit
        mean_key = [k for k in nl if "mean" in k.lower()]
        raw_mean = nl.get(mean_key[0], 0.0) if mean_key else 0.0
        nl_score = (raw_mean or 0.0) / nl_max if nl_max > 0 else 0.0

        # Refine emissions
        ref = refine_row(row, lulc, nl, nl_score)
        confidence = compute_confidence(lulc, nl)

        result = {
            "region": region_name,
            "unit_key": unit_key,
            "year": year,
            "confidence": confidence,
            "lulc_summary": {
                "total_area_km2": lulc.get("total_area_km2"),
                "classes": {
                    k: v for k, v in lulc.get("classes", {}).items()
                },
            },
            "nightlight_summary": nl,
            "nl_score_normalised": round(nl_score, 4),
            "original_emissions_Mt": {
                k: (float(row[k]) if k in row and not pd.isna(row[k]) else None)
                for k in EMISSION_COLS if k not in ("region", "national_share")
            },
            "refined_emissions_Mt": ref["refined"],
            "adjustments": ref["adjustments"],
        }
        all_results.append(result)

        # Print summary table for this region
        print(f"    Confidence score: {confidence['score']}/100")
        print(f"    NL score (normalised): {nl_score:.4f}")
        if not lulc.get("error"):
            for cls_name, cls_data in sorted(lulc.get("classes", {}).items(),
                                              key=lambda x: -x[1]["fraction"]):
                print(f"    LULC {cls_name:25s}: {cls_data['fraction']*100:5.2f}%  ({cls_data['area_km2']:,.1f} km2)")
        print(f"\n    Sector refinements:")
        for sector, adj in ref["adjustments"].items():
            if adj.get("prior_Mt") is None:
                continue
            prior = adj["prior_Mt"]
            refined_v = adj.get("refined_Mt", prior)
            delta = refined_v - prior
            sign = "+" if delta >= 0 else ""
            print(f"      {sector:30s}: {prior:8.4f} -> {refined_v:8.4f} Mt  ({sign}{delta:+.4f})")

    # -- Save outputs -------------------------------------------------------
    print("\nSaving results...")

    # JSON (full detail)
    json_path = out_dir / f"tashkent_refined_emissions_{year}.json"
    safe = make_json_safe(all_results)
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(safe, fh, indent=2, ensure_ascii=False)
    print(f"  JSON: {json_path}")

    # CSV summary
    rows_csv = []
    for rec in all_results:
        base = {
            "region": rec["region"],
            "year": rec["year"],
            "confidence_score": rec["confidence"]["score"],
            "nl_score": rec.get("nl_score_normalised"),
            "total_area_km2": rec["lulc_summary"].get("total_area_km2"),
        }
        # Add LULC fractions
        for cls, data in rec["lulc_summary"]["classes"].items():
            base[f"lulc_{cls}_pct"] = round(data.get("fraction", 0) * 100, 3)
        # Original vs refined totals
        orig = rec["original_emissions_Mt"]
        ref_em = rec["refined_emissions_Mt"]
        base["original_total_Mt"] = orig.get("total")
        # Sum refined (excluding lulucf to avoid double-counting)
        ref_sum = sum(
            v for k, v in ref_em.items()
            if k not in ("lulucf", "total", "net_total") and v is not None
        )
        base["refined_total_Mt_excl_lulucf"] = round(ref_sum, 4)
        base["original_net_total_Mt"] = orig.get("net_total")
        refined_net = ref_sum + (ref_em.get("lulucf") or 0)
        base["refined_net_total_Mt"] = round(refined_net, 4)
        # Per-sector
        for sector in SECTOR_PROXIES:
            if sector in orig:
                base[f"original_{sector}_Mt"] = orig.get(sector)
            if sector in ref_em:
                base[f"refined_{sector}_Mt"] = ref_em.get(sector)
        rows_csv.append(base)

    df_out = pd.DataFrame(rows_csv)
    csv_path = out_dir / f"tashkent_refined_emissions_{year}.csv"
    df_out.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"  CSV:  {csv_path}")

    # Sector comparison table
    comp_rows = []
    for rec in all_results:
        orig = rec["original_emissions_Mt"]
        ref_em = rec["refined_emissions_Mt"]
        for sector in SECTOR_PROXIES:
            o = orig.get(sector)
            r = ref_em.get(sector)
            adj_info = rec["adjustments"].get(sector, {})
            comp_rows.append({
                "region": rec["region"],
                "sector": sector,
                "original_Mt": o,
                "refined_Mt": r,
                "delta_Mt": round(r - o, 6) if r is not None and o is not None else None,
                "adjustment_factor": adj_info.get("adjustment_factor"),
                "lulc_component": adj_info.get("lulc_component"),
                "nl_score": adj_info.get("nl_score"),
            })
    df_comp = pd.DataFrame(comp_rows)
    comp_path = out_dir / f"tashkent_sector_comparison_{year}.csv"
    df_comp.to_csv(comp_path, index=False, encoding="utf-8-sig")
    print(f"  Sector comparison CSV: {comp_path}")

    # Confidence notes
    print("\n=== Confidence & Caveats ===")
    for rec in all_results:
        print(f"\n{rec['region']} (confidence {rec['confidence']['score']}/100):")
        for note in rec["confidence"]["notes"]:
            print(f"  - {note}")
    print("\nMethodological notes:")
    print("  - Refinement is a weighted blend; original proxy-based priors are preserved at '_prior' weights.")
    print("  - ESRI LULC fractions proxy land-use activity, not emission intensity directly.")
    print("  - VIIRS nightlights proxy economic/transport activity at ~500m resolution.")
    print("  - Fugitive emissions remain prior-dominant (gas infrastructure location known).")
    print("  - LULUCF refined by tree-cover fraction; cross-check with national inventory.")
    print(f"\nAll outputs saved to: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
