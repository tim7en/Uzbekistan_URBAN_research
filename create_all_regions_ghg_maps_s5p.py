"""
GHG Emission Intensity Maps — All Uzbekistan Regions (2022)
Enhanced with Sentinel-5P atmospheric chemistry constraints

Spatial disaggregation hierarchy
---------------------------------
Primary : Sentinel-5P annual median composites (actual atmospheric signal)
          - NO2  → combustion, traffic, power plants
          - SO2  → heavy industry, smelters, coal/HFO power plants
          - CO   → incomplete combustion, residential heating, transport
          - CH4  → fugitive gas/coal leaks, livestock, rice cultivation
          - AER  → absorbing aerosol (general pollution load)
Secondary: ESRI 10m LULC (structural land-use constraint)
Tertiary : VIIRS nightlights (economic activity intensity)

Per-sector S5P blend weights
-----------------------------
electricity_heat       : 0.40 SO2 + 0.25 NO2 + 0.15 LULC_built + 0.20 NL
residential_commercial : 0.30 CO  + 0.20 NO2 + 0.25 LULC_built + 0.25 NL
industry_combustion    : 0.35 SO2 + 0.30 NO2 + 0.20 CO + 0.15 LULC_built
transport              : 0.45 NO2 + 0.35 CO  + 0.20 LULC_built
fugitive_emissions     : 0.55 CH4 + 0.25 SO2 + 0.20 uniform
ippu                   : 0.45 SO2 + 0.30 NO2 + 0.15 AER + 0.10 LULC_built
agriculture            : 0.40 CH4 + 0.40 LULC_crops + 0.20 AER
waste                  : 0.40 CH4 + 0.30 CO  + 0.30 LULC_built
"""

import sys, json, time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import numpy as np
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
from matplotlib.colors import LinearSegmentedColormap
from scipy.ndimage import gaussian_filter, zoom
import pandas as pd
import openpyxl

import ee
from services import gee as gee_svc

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUT_DIR    = ROOT / "suhi_analysis_output" / "regional_ghg_maps_s5p"
CACHE_DIR  = ROOT / "suhi_analysis_output" / "regional_ghg_maps" / "_raster_cache"
XLSX_PATH  = ROOT / "uzbekistan_emissions_by_region_2022 (1)+.xlsx"
YEAR       = 2022
LULC_SCALE = 200    # metres — LULC base grid
NL_SCALE   = 500    # metres
S5P_SCALE  = 2000   # metres — S5P native ~5km, download at 2km for spatial detail

# ---------------------------------------------------------------------------
# ESRI classes
# ---------------------------------------------------------------------------
ESRI_CLASSES = {1:"Water",2:"Trees",4:"Flooded_Vegetation",5:"Crops",
                7:"Built_Area",8:"Bare_Ground",9:"Snow_Ice",10:"Clouds",11:"Rangeland"}
BUILT=7; CROPS=5; FLOODED=4; TREES=2; RANGELAND=11; BARE=8

ESRI_PALETTE = {
    "Water":             "#419BDF",
    "Trees":             "#397D49",
    "Flooded Vegetation":"#7A87C6",
    "Crops":             "#E49635",
    "Built Area":        "#C4281B",
    "Bare Ground":       "#A59B8F",
    "Snow / Ice":        "#B39FE1",
    "Rangeland":         "#DFC35A",
}
ESRI_ID_PALETTE = {1:"#419BDF",2:"#397D49",4:"#7A87C6",5:"#E49635",
                   7:"#C4281B",8:"#A59B8F",9:"#B39FE1",11:"#DFC35A"}

SECTOR_LABELS = {
    "electricity_heat":       "Electricity & Heat",
    "residential_commercial": "Residential & Commercial",
    "industry_combustion":    "Industry Combustion",
    "transport":              "Transport",
    "fugitive_emissions":     "Fugitive Emissions",
    "ippu":                   "IPPU",
    "agriculture":            "Agriculture",
    "waste":                  "Waste",
}
SECTOR_COLORS = ["#E63946","#457B9D","#F4A261","#2A9D8F",
                 "#E9C46A","#264653","#A8DADC","#F1FAEE"]

GHG_CMAP = LinearSegmentedColormap.from_list("ghg", [
    "#F7FBFF","#DEEBF7","#C6DBEF","#9ECAE1","#6BAED6",
    "#4292C6","#2171B5","#FED976","#FEB24C","#FD8D3C",
    "#FC4E2A","#E31A1C","#BD0026","#800026","#4D004B","#1A0033",
], N=512)

# S5P cmaps for inset panels
NO2_CMAP  = plt.cm.YlOrRd
SO2_CMAP  = plt.cm.PuRd
CO_CMAP   = plt.cm.Oranges
CH4_CMAP  = plt.cm.BuGn

# ---------------------------------------------------------------------------
# Region → GAUL mapping and fallbacks (same as before)
# ---------------------------------------------------------------------------
REGION_GAUL_MAP = {
    "Tashkent City":      ["Toshkent shahri","Tashkent City","Toshkent City"],
    "Tashkent Region":    ["Toshkent","Tashkent"],
    "Navoi Region":       ["Navoiy","Navoi"],
    "Kashkadarya Region": ["Qashqadaryo","Kashkadarya"],
    "Bukhara Region":     ["Buxoro","Bukhara"],
    "Samarkand Region":   ["Samarqand","Samarkand"],
    "Fergana Region":     ["Farg'ona","Fergana"],
    "Andijan Region":     ["Andijon","Andijan"],
    "Namangan Region":    ["Namangan"],
    "Surkhandarya Region":["Surxondaryo","Surkhandarya"],
    "Khorezm Region":     ["Xorazm","Khorezm"],
    "Jizzakh Region":     ["Jizzax","Jizzakh"],
    "Syrdarya Region":    ["Sirdaryo","Syrdarya"],
    "Rep. Karakalpakstan":["Qoraqalpog'iston","Karakalpakstan"],
}
REGION_FALLBACKS = {
    "Tashkent City":       (69.27, 41.30, 25_000),
    "Tashkent Region":     (70.00, 41.20, 180_000),
    "Navoi Region":        (65.00, 40.50, 200_000),
    "Kashkadarya Region":  (66.00, 38.80, 200_000),
    "Bukhara Region":      (64.50, 39.80, 180_000),
    "Samarkand Region":    (66.90, 39.65, 180_000),
    "Fergana Region":      (71.80, 40.38, 130_000),
    "Andijan Region":      (72.35, 40.78, 100_000),
    "Namangan Region":     (71.67, 41.00, 130_000),
    "Surkhandarya Region": (67.30, 37.80, 200_000),
    "Khorezm Region":      (60.62, 41.55, 120_000),
    "Jizzakh Region":      (67.84, 40.50, 150_000),
    "Syrdarya Region":     (68.78, 40.49, 120_000),
    "Rep. Karakalpakstan": (60.00, 43.00, 400_000),
}

LULUCF_PROXIES = {TREES: -1.0, RANGELAND: -0.05}

# ---------------------------------------------------------------------------
# Excel loader
# ---------------------------------------------------------------------------

def load_emissions_excel(xlsx_path: Path) -> pd.DataFrame:
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb["Emissions by Region"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    header_idx = next(i for i, r in enumerate(rows)
                      if any(v is not None and "Region" in str(v) for v in r))
    data_rows = rows[header_idx + 1:]
    n_cols = max(len(r) for r in data_rows)
    df = pd.DataFrame([list(r)+[None]*(n_cols-len(r)) for r in data_rows],
                      columns=range(n_cols))
    col_names = ["region","electricity_heat","residential_commercial",
                 "industry_combustion","transport","fugitive_emissions",
                 "ippu","agriculture","waste","lulucf","total","national_share","net_total"]
    df = df.rename(columns={i: col_names[i] for i in range(min(len(col_names), n_cols))})
    df["region"] = df["region"].astype(str).str.strip()
    for p in ["nan","None","Note","Source","SUM OF","NATIONAL","Allocation"]:
        df = df[~df["region"].str.startswith(p)]
    for col in col_names[1:]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

# ---------------------------------------------------------------------------
# GEE helpers
# ---------------------------------------------------------------------------

def get_region_geometry(region_name: str) -> ee.Geometry:
    gaul = ee.FeatureCollection("FAO/GAUL/2015/level1")
    uz   = gaul.filter(ee.Filter.eq("ADM0_NAME", "Uzbekistan"))
    exclude_city = (region_name == "Tashkent Region")
    for name in REGION_GAUL_MAP.get(region_name, [region_name]):
        try:
            filt = uz.filter(ee.Filter.stringContains("ADM1_NAME", name.split("'")[0]))
            if exclude_city:
                filt = filt.filter(ee.Filter.Not(
                    ee.Filter.stringContains("ADM1_NAME", "shahri"))).filter(
                    ee.Filter.Not(ee.Filter.stringContains("ADM1_NAME", "City")))
            if filt.size().getInfo() > 0:
                geom = filt.geometry()
                area = geom.area().getInfo() / 1e6
                print(f"    GAUL match '{name}': ~{area:,.0f} km2")
                return geom
        except Exception:
            continue
    lon, lat, buf = REGION_FALLBACKS.get(region_name, (65.0, 40.0, 200_000))
    print(f"    Fallback buffer for '{region_name}'")
    return ee.Geometry.Point([lon, lat]).buffer(buf).bounds()


def download_geotiff(image: ee.Image, region: ee.Geometry,
                     scale: int, out_path: Path, fname: str) -> Path | None:
    try:
        region_geo = region.bounds().getInfo()["coordinates"]
        url = image.getDownloadURL({
            "scale": scale, "crs": "EPSG:4326",
            "region": region_geo, "format": "GEO_TIFF"
        })
        out_path.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, stream=True, timeout=300)
        if r.status_code == 200:
            p = out_path / fname
            with open(p, "wb") as fh:
                for chunk in r.iter_content(8192):
                    if chunk: fh.write(chunk)
            return p
        print(f"    Download failed HTTP {r.status_code}")
    except Exception as e:
        print(f"    Download error: {e}")
    return None


def fetch_s5p_rasters(region_name: str, geom: ee.Geometry,
                      rdir: Path) -> dict:
    """Download S5P annual median composites for a region. Returns dict of paths."""
    slug  = region_name.replace(" ","_").replace(".","").replace("'","")
    rdir.mkdir(parents=True, exist_ok=True)
    region_geo = geom.bounds().getInfo()["coordinates"]
    region_ee  = ee.Geometry.Polygon(region_geo)

    s5p_specs = {
        "no2":  ("COPERNICUS/S5P/OFFL/L3_NO2",
                 "tropospheric_NO2_column_number_density", 0.75),
        "so2":  ("COPERNICUS/S5P/OFFL/L3_SO2",
                 "SO2_column_number_density", 0.5),
        "co":   ("COPERNICUS/S5P/OFFL/L3_CO",
                 "CO_column_number_density", 0.5),
        "ch4":  ("COPERNICUS/S5P/OFFL/L3_CH4",
                 "CH4_column_volume_mixing_ratio_dry_air_bias_corrected", 0.5),
        "aer":  ("COPERNICUS/S5P/OFFL/L3_AER_AI",
                 "absorbing_aerosol_index", 0.5),
    }

    paths = {}
    for key, (collection, band, qa_thresh) in s5p_specs.items():
        fpath = rdir / f"s5p_{key}_{slug}_{YEAR}.tif"
        if fpath.exists():
            print(f"    S5P {key.upper()} cached.")
            paths[key] = fpath
            continue
        print(f"    Downloading S5P {key.upper()}...")
        try:
            col = (ee.ImageCollection(collection)
                   .filterDate(f"{YEAR}-01-01", f"{YEAR}-12-31")
                   .filterBounds(region_ee))
            # QA mask for NO2: cloud_fraction is a band, apply per-pixel mask
            if key == "no2":
                def mask_cloud(img):
                    return img.updateMask(img.select("cloud_fraction").lt(0.5))
                col = col.map(mask_cloud)
            img = col.select(band).median().clip(region_ee)
            p = download_geotiff(img, region_ee, S5P_SCALE, rdir, fpath.name)
            paths[key] = p
        except Exception as e:
            print(f"    S5P {key} failed: {e}")
            paths[key] = None
        time.sleep(0.5)

    return paths


def fetch_base_rasters(region_name: str, geom: ee.Geometry,
                       cache_dir: Path) -> dict:
    """Use cached LULC/NL if available, otherwise download."""
    slug  = region_name.replace(" ","_").replace(".","").replace("'","")
    rdir  = cache_dir / slug
    rdir.mkdir(parents=True, exist_ok=True)
    region_geo = geom.bounds().getInfo()["coordinates"]
    region_ee  = ee.Geometry.Polygon(region_geo)

    lulc_path = rdir / f"lulc_{slug}_{YEAR}.tif"
    if not lulc_path.exists():
        print(f"    Downloading LULC...")
        esri = (ee.ImageCollection(
                    "projects/sat-io/open-datasets/landcover/ESRI_Global-LULC_10m_TS")
                .filterDate(f"{YEAR}-01-01", f"{YEAR}-12-31")
                .filterBounds(region_ee).mosaic().clip(region_ee))
        lulc_path = download_geotiff(esri, region_ee, LULC_SCALE, rdir, lulc_path.name)
    else:
        print(f"    LULC cached.")

    nl_path = rdir / f"nl_{slug}_{YEAR}.tif"
    if not nl_path.exists():
        print(f"    Downloading NL...")
        nl = (ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG")
              .filterDate(f"{YEAR}-01-01", f"{YEAR}-12-31")
              .filterBounds(region_ee).select("avg_rad").median().clip(region_ee))
        nl_path = download_geotiff(nl, region_ee, NL_SCALE, rdir, nl_path.name)
    else:
        print(f"    NL cached.")

    time.sleep(0.5)
    return {"lulc": lulc_path, "nl": nl_path}

# ---------------------------------------------------------------------------
# Raster I/O
# ---------------------------------------------------------------------------

def load_raster(path: Path):
    import rasterio
    with rasterio.open(path) as src:
        data = src.read(1, masked=True)
        transform = src.transform
        bounds = src.bounds
    return data, transform, bounds


def resample_to(arr: np.ma.MaskedArray, target_shape: tuple) -> np.ma.MaskedArray:
    zy = target_shape[0] / arr.shape[0]
    zx = target_shape[1] / arr.shape[1]
    data   = zoom(arr.filled(0).astype(float), (zy, zx), order=1)
    msk    = arr.mask
    mask_z = (np.zeros(target_shape, bool) if (np.isscalar(msk) or msk.shape == ())
              else zoom(msk.astype(float), (zy, zx), order=0) > 0.5)
    return np.ma.array(data, mask=mask_z)


def normalise(arr: np.ndarray, full_mask: np.ndarray,
              clip_pct: float = 99.0) -> np.ndarray:
    """Normalise to [0,1] within valid pixels, clip outliers."""
    vals = arr[full_mask & np.isfinite(arr) & (arr > 0)]
    if vals.size == 0:
        return np.zeros_like(arr)
    vmax = np.percentile(vals, clip_pct)
    vmin = vals.min()
    if vmax == vmin:
        return np.zeros_like(arr)
    out = np.clip((arr - vmin) / (vmax - vmin), 0, 1)
    out[~full_mask] = 0
    return out


def ch4_anomaly(ch4_arr: np.ndarray, full_mask: np.ndarray) -> np.ndarray:
    """Return CH4 anomaly above regional background (positive = elevated)."""
    vals = ch4_arr[full_mask & np.isfinite(ch4_arr) & (ch4_arr > 0)]
    if vals.size == 0:
        return np.zeros_like(ch4_arr)
    bg = np.percentile(vals, 10)   # regional 10th pct as background
    anom = np.maximum(ch4_arr - bg, 0)
    return anom

# ---------------------------------------------------------------------------
# S5P-enhanced emission intensity
# ---------------------------------------------------------------------------

def compute_s5p_reliability(lulc_fracs: dict) -> float:
    """
    Compute a regional S5P signal reliability score in [0.15, 1.0].

    Scientific basis
    ----------------
    TROPOMI column retrievals (NO2, SO2, AER_AI) depend on UV/VIS backscatter
    from the surface.  High-reflectance surfaces inflate retrieval noise and
    cause systematic biases:

    * Bare desert / arid land  (LER_UV ~ 0.15-0.40):
        NO2 uncertainty +2-3x (van Geffen et al. 2022, TROPOMI NO2 ATBD v2.4)
        SO2 noise floor elevated (Theys et al. 2017, ACP)
    * Snow / ice               (LER_UV > 0.60):
        Retrieval failure or large uncertainty (Tilstra et al. 2021, AMT)
    * Semi-arid rangeland      (LER_UV ~ 0.08-0.15, Central Asian steppe):
        Moderate degradation; Kyzylkum / Karakum dust plumes also contaminate
        AER_AI with natural mineral dust (Torres et al. 2007, JGR;
        Herman et al. 1997, JGR)
    * Built / crops / trees    (LER_UV ~ 0.03-0.10):
        Stable intermediate albedo; best S5P retrieval conditions
        (Lorente et al. 2017, AMT; Boersma et al. 2018, AMT)

    Noise-penalty weights per LULC class (linear in surface LER relative
    to optimal urban/crop surface):
        Bare_Ground      1.00   (desert, highest albedo and dust source)
        Snow_Ice         1.00   (retrieval failure / albedo saturation)
        Rangeland        0.65   (semi-arid steppe; also dust source)
        Flooded_Veg      0.20   (dark water surface helps, mixed signal)
        Water            0.10   (dark, excellent backscatter geometry)
        Crops            0.10   (low-LER canopy, reliable)
        Trees            0.05   (lowest LER, best retrievals)
        Built_Area       0.00   (urban albedo well-characterised in TROPOMI)

    reliability = clamp(1 - weighted_noise_score, 0.15, 1.0)
    """
    NOISE_W = {
        "Bare_Ground":         1.00,
        "Snow_Ice":            1.00,
        "Rangeland":           0.65,
        "Flooded_Vegetation":  0.20,
        "Water":               0.10,
        "Crops":               0.10,
        "Trees":               0.05,
        "Built_Area":          0.00,
    }
    noise = sum(NOISE_W.get(cls, 0.50) * frac for cls, frac in lulc_fracs.items())
    return float(np.clip(1.0 - noise, 0.15, 1.0))


def adjust_recipes(base_recipes: dict, reliability: float) -> dict:
    """
    Scale S5P signal weights by reliability; redistribute the lost weight
    to LULC / NL components proportionally so each sector still sums to 1.

    At reliability=1.0  the recipes are unchanged.
    At reliability=0.15 the S5P contribution is reduced to 15 % of its
    nominal weight; the remaining 85 % is added to LULC/NL signals.
    """
    S5P_KEYS   = {"no2", "so2", "co", "ch4", "aer"}
    LULC_KEYS  = {"built", "crops", "flooded", "bare", "nl", "uniform"}

    adjusted = {}
    for sector, recipe in base_recipes.items():
        s5p_total  = sum(v for k, v in recipe.items() if k in S5P_KEYS)
        lulc_total = sum(v for k, v in recipe.items() if k in LULC_KEYS)

        # Weight kept for S5P
        s5p_kept = s5p_total * reliability
        # Redistributed to LULC/NL
        s5p_lost = s5p_total - s5p_kept

        new_recipe = {}
        for k, v in recipe.items():
            if k in S5P_KEYS:
                new_recipe[k] = v * reliability
            elif k in LULC_KEYS and lulc_total > 0:
                # Absorb lost S5P weight proportionally among LULC/NL keys
                new_recipe[k] = v + s5p_lost * (v / lulc_total)
            else:
                new_recipe[k] = v

        # If no LULC/NL keys exist (pure S5P sector), add uniform fallback
        if lulc_total == 0 and s5p_lost > 0:
            new_recipe["uniform"] = new_recipe.get("uniform", 0) + s5p_lost

        adjusted[sector] = new_recipe
    return adjusted


def build_s5p_proxies(lulc, nl_arr, s5p: dict, full_mask: np.ndarray) -> dict:
    """
    Return dict of normalised proxy arrays (0–1) keyed by signal name.
    All arrays are on the LULC grid.
    """
    lulc_d = lulc.filled(0).astype(int)
    shape  = lulc.shape

    # LULC structural layers
    built  = ((lulc_d == BUILT)  & full_mask).astype(float)
    crops  = ((lulc_d == CROPS)  & full_mask).astype(float)
    flooded= ((lulc_d == FLOODED)& full_mask).astype(float)
    bare   = ((lulc_d == BARE)   & full_mask).astype(float)
    trees  = ((lulc_d == TREES)  & full_mask).astype(float)
    rang   = ((lulc_d == RANGELAND)& full_mask).astype(float)

    # NL normalised
    nl_n = normalise(nl_arr, full_mask)

    proxies = {
        "built":   normalise(built,  full_mask),
        "crops":   normalise(crops,  full_mask),
        "flooded": normalise(flooded, full_mask),
        "bare":    normalise(bare,   full_mask),
        "nl":      nl_n,
        "uniform": full_mask.astype(float) / max(full_mask.sum(), 1),
    }

    # S5P layers — resample each to LULC grid
    for key in ("no2", "so2", "co", "ch4", "aer"):
        raw = s5p.get(key)
        if raw is None:
            proxies[key] = np.zeros(shape, float)
            continue
        rs = resample_to(raw, shape)
        data = rs.filled(0).astype(float)
        # CH4: use anomaly above background
        if key == "ch4":
            data = ch4_anomaly(data, full_mask)
        proxies[key] = normalise(data, full_mask)

    return proxies


def compute_sector_intensity(proxies: dict, refined_Mt: dict,
                             full_mask: np.ndarray,
                             pixel_area_km2: float,
                             s5p_reliability: float = 1.0) -> np.ndarray:
    """
    Compute emission intensity (t CO2-eq / km2) per pixel using S5P proxies.
    s5p_reliability [0.15-1.0] scales S5P signal weights; lost weight is
    absorbed by LULC/NL components (see adjust_recipes / compute_s5p_reliability).
    """

    # Sector → base blend recipe  {proxy_key: weight, ...}
    BASE_RECIPES = {
        "electricity_heat":       {"so2":0.40,"no2":0.25,"built":0.15,"nl":0.20},
        "residential_commercial": {"co": 0.30,"no2":0.20,"built":0.25,"nl":0.25},
        "industry_combustion":    {"so2":0.35,"no2":0.30,"co":  0.20,"built":0.15},
        "transport":              {"no2":0.45,"co": 0.35,"built":0.20},
        "fugitive_emissions":     {"ch4":0.55,"so2":0.25,"uniform":0.20},
        "ippu":                   {"so2":0.45,"no2":0.30,"aer":  0.15,"built":0.10},
        "agriculture":            {"ch4":0.40,"crops":0.40,"aer":0.20},
        "waste":                  {"ch4":0.40,"co":  0.30,"built":0.30},
    }
    recipes = adjust_recipes(BASE_RECIPES, s5p_reliability)
    lulc_lulucf_weights = {TREES: -1.0, RANGELAND: -0.05}

    total = np.zeros_like(list(proxies.values())[0], dtype=float)

    for sector, recipe in recipes.items():
        mt = float(refined_Mt.get(sector) or 0.0)
        if mt == 0:
            continue

        # Blend proxies
        raw = np.zeros_like(total)
        weight_sum = sum(recipe.values())
        for pkey, w in recipe.items():
            raw += (w / weight_sum) * proxies.get(pkey, np.zeros_like(total))

        # Normalise so spatial weights sum to 1 over unit
        s = raw[full_mask].sum()
        if s > 0:
            raw = raw / s
        else:
            raw = full_mask.astype(float) / max(full_mask.sum(), 1)

        total += raw * mt * 1e6 / pixel_area_km2

    # LULUCF sink
    lmt = float(refined_Mt.get("lulucf") or 0.0)
    if lmt != 0:
        lulc_d = proxies.get("_lulc_data", None)
        if lulc_d is None:
            pass
        else:
            lp = sum(w * (lulc_d == c).astype(float) * full_mask
                     for c, w in lulc_lulucf_weights.items())
            s  = np.abs(lp[full_mask]).sum()
            if s > 0:
                total += (lp / s) * lmt * 1e6 / pixel_area_km2

    return total


def build_emission_grid(lulc, nl_res, s5p_arrs, refined_Mt, pixel_area_km2):
    full_mask = (~lulc.mask) if (hasattr(lulc,"mask") and lulc.mask.ndim > 0) \
                else np.ones(lulc.shape, bool)
    nl_data = nl_res.filled(0).astype(float)

    # LULC composition for reliability scoring
    lulc_d     = lulc.filled(0).astype(int)
    total_px   = max((lulc_d > 0).sum(), 1)
    lulc_fracs = {ESRI_CLASSES[c]: (lulc_d == c).sum() / total_px
                  for c in ESRI_CLASSES if (lulc_d == c).sum() > 0}

    s5p_reliability = compute_s5p_reliability(lulc_fracs)

    proxies = build_s5p_proxies(lulc, nl_data, s5p_arrs, full_mask)
    proxies["_lulc_data"] = lulc_d

    grid = compute_sector_intensity(proxies, refined_Mt, full_mask,
                                    pixel_area_km2, s5p_reliability)

    # Gaussian smoothing
    grid = gaussian_filter(grid, sigma=3)
    return grid, proxies, full_mask, s5p_reliability

# ---------------------------------------------------------------------------
# Refined emission estimates (same blend as previous script)
# ---------------------------------------------------------------------------

def compute_refined_Mt(original_Mt: dict, lulc, nl_res) -> dict:
    lulc_d = lulc.filled(0).astype(int)
    total_px = (lulc_d > 0).sum() or 1

    def frac(cls_id): return (lulc_d == cls_id).sum() / total_px

    built_f   = frac(BUILT)
    crops_f   = frac(CROPS)
    flooded_f = frac(FLOODED)
    trees_f   = frac(TREES)
    bare_f    = frac(BARE)
    rang_f    = frac(RANGELAND)

    nl_d    = nl_res.filled(0).astype(float)
    nl_pos  = nl_d[nl_d > 0]
    nl_max  = np.percentile(nl_pos, 98) if nl_pos.size > 0 else 1.0
    nl_sc   = float(nl_pos.mean() / nl_max) if nl_pos.size > 0 else 0.0

    def blend(prior, lulc_cmp, lw, nw, pw):
        return prior * (lw * lulc_cmp + nw * nl_sc + pw * 1.0)

    return {
        "electricity_heat":       blend(original_Mt["electricity_heat"],
                                        built_f, 0.20,0.50,0.30),
        "residential_commercial": blend(original_Mt["residential_commercial"],
                                        built_f, 0.55,0.20,0.25),
        "industry_combustion":    blend(original_Mt["industry_combustion"],
                                        0.75*built_f+0.25*bare_f, 0.20,0.50,0.30),
        "transport":              blend(original_Mt["transport"],
                                        built_f, 0.35,0.35,0.30),
        "fugitive_emissions":     original_Mt["fugitive_emissions"]*(0.25*nl_sc+0.75),
        "ippu":                   blend(original_Mt["ippu"],
                                        0.5*built_f+0.5*bare_f, 0.10,0.50,0.40),
        "agriculture":            blend(original_Mt["agriculture"],
                                        0.7*crops_f+0.3*flooded_f, 0.65,0.00,0.35),
        "waste":                  blend(original_Mt["waste"], built_f,0.45,0.00,0.55),
        "lulucf":                 blend(original_Mt["lulucf"],
                                        trees_f+0.1*rang_f, 0.65,0.00,0.35),
    }

# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def lulc_composition(lulc) -> dict:
    data = lulc.filled(0).astype(int)
    total = (data > 0).sum() or 1
    return {ESRI_CLASSES[c]: (data==c).sum()/total
            for c in ESRI_CLASSES if (data==c).sum()>0}


def draw_s5p_inset(ax, arr: np.ma.MaskedArray | None, cmap, title: str,
                   extent: list):
    ax.set_facecolor("#16191F")
    ax.set_title(title, fontsize=7, fontweight="bold", color="white", pad=2)
    if arr is not None and arr.count() > 0:
        data = arr.filled(np.nan)
        vmax = float(np.nanpercentile(data[data > 0], 98)) if np.any(data > 0) else 1
        ax.imshow(data, extent=extent, origin="upper", cmap=cmap,
                  vmin=0, vmax=vmax, interpolation="bilinear", aspect="auto")
    else:
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                transform=ax.transAxes, color="white", fontsize=7)
    ax.tick_params(colors="white", labelsize=5)
    for sp in ax.spines.values(): sp.set_edgecolor("#444")


def draw_map(region_name: str, emission_grid, lulc, nl_data, lulc_transform,
             s5p_arrs: dict, refined_Mt, original_Mt, lulc_comp, out_path: Path,
             s5p_reliability: float = 1.0):

    rows, cols = emission_grid.shape
    west  = lulc_transform.c
    east  = lulc_transform.c + cols * lulc_transform.a
    north = lulc_transform.f
    south = lulc_transform.f + rows * lulc_transform.e
    extent = [west, east, south, north]

    pos_vals = emission_grid[emission_grid > 0]
    if pos_vals.size == 0:
        print(f"  WARNING: no positive values — skipping map for {region_name}")
        return
    log_min = np.log10(max(np.percentile(pos_vals, 2), 1.0))
    log_max = np.log10(np.percentile(pos_vals, 99.5))

    # -----------------------------------------------------------------------
    # Layout:
    #   Row 0 (tall) : main GHG map
    #   Row 1 (thin) : colorbar
    #   Row 2        : S5P insets (NO2 | SO2 | CO | CH4)
    #   Row 3        : sector bars | LULC legend | pie
    # -----------------------------------------------------------------------
    fig = plt.figure(figsize=(18, 20))
    fig.patch.set_facecolor("#0E1117")

    gs = gridspec.GridSpec(
        4, 4, figure=fig,
        height_ratios=[10, 0.4, 3.5, 3.5],
        hspace=0.40, wspace=0.35,
        top=0.93, bottom=0.03, left=0.06, right=0.97,
    )

    ax_map  = fig.add_subplot(gs[0, :])
    ax_cbar = fig.add_subplot(gs[1, :])
    ax_no2  = fig.add_subplot(gs[2, 0])
    ax_so2  = fig.add_subplot(gs[2, 1])
    ax_co   = fig.add_subplot(gs[2, 2])
    ax_ch4  = fig.add_subplot(gs[2, 3])
    ax_bars = fig.add_subplot(gs[3, :2])
    ax_leg  = fig.add_subplot(gs[3, 2])
    ax_pie  = fig.add_subplot(gs[3, 3])

    # ---- LULC faint background ----
    lulc_rgba = np.zeros((*lulc.shape, 4), dtype=float)
    for cid, hex_col in ESRI_ID_PALETTE.items():
        rgba = mcolors.to_rgba(hex_col, 0.18)
        mask = lulc.filled(0).astype(int) == cid
        for c in range(4): lulc_rgba[mask, c] = rgba[c]
    ax_map.imshow(lulc_rgba, extent=extent, origin="upper", aspect="auto",
                  interpolation="nearest")

    # ---- GHG intensity ----
    em_log = np.where(emission_grid > 0,
                      np.log10(np.maximum(emission_grid, 1e-3)), np.nan)
    img = ax_map.imshow(em_log, extent=extent, origin="upper",
                        cmap=GHG_CMAP, vmin=log_min, vmax=log_max,
                        interpolation="bilinear", aspect="auto", alpha=0.93)

    # ---- NL contours ----
    try:
        nl_sm = gaussian_filter(nl_data.astype(float), sigma=2)
        nl_max_d = float(np.percentile(nl_sm[nl_sm>0], 95)) if (nl_sm>0).any() else 10
        lvls = [v for v in [0.5,1,3,8,20,50] if v < nl_max_d]
        if lvls:
            x_nl = np.linspace(west, east, nl_sm.shape[1])
            y_nl = np.linspace(north, south, nl_sm.shape[0])
            X, Y = np.meshgrid(x_nl, y_nl)
            cs = ax_map.contour(X, Y, nl_sm, levels=lvls,
                                colors="white", linewidths=0.35, alpha=0.28)
            ax_map.clabel(cs, fmt="%.0f", fontsize=4.5, colors="white")
    except Exception:
        pass

    # Map styling
    refined_total = sum(v for k,v in refined_Mt.items()
                        if k!="lulucf" and v is not None and v > 0)
    ax_map.set_title(
        f"{region_name}  |  Refined total: {refined_total:.2f} Mt CO\u2082-eq  "
        f"(excl. LULUCF)  |  S5P-constrained spatial disaggregation",
        fontsize=9.5, fontweight="bold", color="white", pad=5)
    ax_map.set_xlabel("Longitude", fontsize=8, color="white")
    ax_map.set_ylabel("Latitude",  fontsize=8, color="white")
    ax_map.tick_params(colors="white", labelsize=7)
    for sp in ax_map.spines.values(): sp.set_edgecolor("#444")
    ax_map.set_facecolor("#0E1117")

    # ---- Colorbar ----
    cb = fig.colorbar(img, cax=ax_cbar, orientation="horizontal", extend="max")
    cb.set_label("GHG Emission Intensity  (t CO\u2082-eq / km\u00b2)",
                 fontsize=9, color="white", labelpad=3)
    tick_vals = [1, 5, 10, 50, 100, 500, 1000, 5000, 10000, 25000]
    t_log = [np.log10(v) for v in tick_vals if log_min <= np.log10(v) <= log_max]
    t_lbl = [f"{v:,}" for v in tick_vals if log_min <= np.log10(v) <= log_max]
    cb.set_ticks(t_log)
    cb.set_ticklabels(t_lbl)
    cb.ax.tick_params(colors="white", labelsize=7.5)
    cb.outline.set_edgecolor("#777")
    ax_cbar.set_facecolor("#0E1117")

    # ---- S5P inset panels ----
    s5p_res = {k: (resample_to(v, lulc.shape) if v is not None else None)
               for k, v in s5p_arrs.items()}

    draw_s5p_inset(ax_no2, s5p_res.get("no2"), NO2_CMAP, "NO2 (mol/m2)", extent)
    draw_s5p_inset(ax_so2, s5p_res.get("so2"), SO2_CMAP, "SO2 (mol/m2)", extent)
    draw_s5p_inset(ax_co,  s5p_res.get("co"),  CO_CMAP,  "CO (mol/m2)",  extent)

    # CH4 anomaly for display
    ch4_raw = s5p_res.get("ch4")
    if ch4_raw is not None:
        full_mask = (~lulc.mask) if (hasattr(lulc,"mask") and lulc.mask.ndim>0) \
                    else np.ones(lulc.shape, bool)
        ch4_anom_data = ch4_anomaly(ch4_raw.filled(0), full_mask)
        ch4_display = np.ma.array(ch4_anom_data, mask=lulc.mask
                                  if lulc.mask.ndim>0 else False)
    else:
        ch4_display = None
    draw_s5p_inset(ax_ch4, ch4_display, CH4_CMAP, "CH4 anomaly (ppb)", extent)

    for ax_s in (ax_no2, ax_so2, ax_co, ax_ch4):
        ax_s.set_xlabel("Lon", fontsize=5.5, color="white")
        ax_s.set_ylabel("Lat", fontsize=5.5, color="white")

    # ---- Sector bars ----
    sectors = list(SECTOR_LABELS.keys())
    x = np.arange(len(sectors))
    w = 0.35
    orig_v = [float(original_Mt.get(s) or 0) for s in sectors]
    ref_v  = [float(refined_Mt.get(s)  or 0) for s in sectors]
    ax_bars.bar(x-w/2, orig_v, w, color="#546E7A", label="Original (proxy)",
                alpha=0.9, edgecolor="white", linewidth=0.4)
    ax_bars.bar(x+w/2, ref_v,  w,
                color=[SECTOR_COLORS[i] for i in range(len(sectors))],
                label="Refined (LULC + NL)", alpha=0.9, edgecolor="white", linewidth=0.4)
    ax_bars.set_xticks(x)
    ax_bars.set_xticklabels([SECTOR_LABELS[s] for s in sectors],
                            rotation=38, ha="right", fontsize=6.5, color="white")
    ax_bars.set_ylabel("Mt CO\u2082-eq", fontsize=8, color="white")
    ax_bars.set_title("Original vs Refined Sector Emissions",
                      fontsize=8, fontweight="bold", color="white")
    ax_bars.tick_params(colors="white", labelsize=7)
    ax_bars.set_facecolor("#16191F")
    ax_bars.spines["top"].set_visible(False)
    ax_bars.spines["right"].set_visible(False)
    for sp in ax_bars.spines.values(): sp.set_edgecolor("#444")
    ax_bars.yaxis.grid(True, alpha=0.2, lw=0.5, color="white")
    ax_bars.set_axisbelow(True)
    ax_bars.legend(fontsize=7, facecolor="#16191F", labelcolor="white",
                   edgecolor="#444", loc="upper right")

    # ---- LULC legend (all 8 classes always present) ----
    ax_leg.set_facecolor("#16191F")
    ax_leg.set_title("ESRI Land Cover Classes", fontsize=8,
                     fontweight="bold", color="white", pad=4)
    ax_leg.axis("off")
    for sp in ax_leg.spines.values(): sp.set_edgecolor("#444")
    for i, (label, color) in enumerate(ESRI_PALETTE.items()):
        row = i % 4
        col = i // 4
        y_pos = 0.90 - row * 0.22
        x_pos = 0.05 + col * 0.52
        ax_leg.add_patch(mpatches.FancyBboxPatch(
            (x_pos, y_pos-0.07), 0.10, 0.14,
            boxstyle="round,pad=0.01", facecolor=color,
            transform=ax_leg.transAxes, clip_on=False, zorder=3))
        ax_leg.text(x_pos+0.13, y_pos, label, transform=ax_leg.transAxes,
                    fontsize=7, color="white", va="center")

    # ---- LULC pie ----
    ax_pie.set_facecolor("#16191F")
    ax_pie.set_title("Land Cover Composition", fontsize=8,
                     fontweight="bold", color="white", pad=4)
    if lulc_comp:
        sorted_comp = sorted(lulc_comp.items(), key=lambda x: -x[1])
        labels  = [c[0] for c in sorted_comp]
        sizes   = [c[1]*100 for c in sorted_comp]
        inv_cls = {v: k for k,v in ESRI_CLASSES.items()}
        pie_cols = [ESRI_ID_PALETTE.get(inv_cls.get(l,0),"#888") for l in labels]
        wedges, _, autotexts = ax_pie.pie(
            sizes, colors=pie_cols,
            autopct=lambda p: f"{p:.0f}%" if p > 4 else "",
            startangle=140,
            wedgeprops={"width":0.55,"edgecolor":"#16191F","linewidth":0.8},
            pctdistance=0.78,
            textprops={"fontsize":6,"color":"white"})
        for t in autotexts: t.set_fontsize(5.5)
        patches = [mpatches.Patch(color=pie_cols[i],
                                  label=f"{labels[i]} {sizes[i]:.0f}%")
                   for i in range(len(labels))]
        ax_pie.legend(handles=patches, loc="lower center",
                      bbox_to_anchor=(0.5,-0.32), fontsize=5.8, ncol=2,
                      facecolor="#16191F", labelcolor="white",
                      edgecolor="#444", framealpha=0.8)
    else:
        ax_pie.text(0.5,0.5,"No data",ha="center",va="center",
                    transform=ax_pie.transAxes,color="white",fontsize=8)

    # ---- S5P reliability badge ----
    rel_pct = int(round(s5p_reliability * 100))
    if rel_pct >= 75:
        rel_color, rel_label = "#2ECC71", "HIGH"
    elif rel_pct >= 40:
        rel_color, rel_label = "#F39C12", "MODERATE"
    else:
        rel_color, rel_label = "#E74C3C", "LOW"
    fig.text(0.97, 0.957,
             f"S5P reliability: {rel_label} ({rel_pct}%)",
             ha="right", fontsize=7.5, fontweight="bold", color=rel_color)

    # ---- Title & footnote ----
    fig.text(0.5, 0.965,
             f"GHG Emissions — {region_name} (2022) — Sentinel-5P Refined",
             ha="center", fontsize=13, fontweight="bold", color="white")
    fig.text(0.5, 0.946,
             f"S5P weight: {rel_pct}% of nominal (LULC-adjusted)  |  "
             "Spatial constraint: S5P NO2/SO2/CO/CH4 + ESRI 10m LULC + VIIRS NL  |  "
             "Totals: BTR1 Uzbekistan 2024",
             ha="center", fontsize=7.5, color="#AAAAAA")
    fig.text(0.5, 0.005,
             "S5P OFFL L3 annual medians, 2km display. "
             "NO2 filtered cloud_fraction<0.5. CH4 anomaly above regional P10. "
             f"S5P reliability score = 1 - weighted LULC noise penalty "
             f"(van Geffen 2022; Theys 2017; Torres 2007). "
             "Sources: Copernicus/S5P OFFL; ESRI LULC 10m; NOAA/VIIRS; BTR1 UZB 2024.",
             ha="center", fontsize=5.8, color="#666", style="italic")

    fig.savefig(out_path, dpi=180, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  Saved: {out_path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def match_region(row_name: str) -> str | None:
    for key in REGION_GAUL_MAP:
        if key.lower() in row_name.lower() or row_name.lower() in key.lower():
            return key
    return None


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Initializing GEE...")
    if not gee_svc.initialize_gee():
        print("ERROR: GEE init failed.")
        sys.exit(1)

    print("Loading emissions data...")
    df = load_emissions_excel(XLSX_PATH)

    skipped = []
    processed = []

    for _, row in df.iterrows():
        region_name = match_region(row["region"])
        if region_name is None:
            skipped.append(row["region"])
            continue

        slug     = region_name.replace(" ","_").replace(".","").replace("'","")
        out_path = OUT_DIR / f"ghg_s5p_{slug}_{YEAR}.png"
        s5p_dir  = OUT_DIR / "_s5p_cache" / slug

        print(f"\n{'='*60}")
        print(f"Processing: {region_name}")
        print(f"{'='*60}")

        # Geometry
        try:
            geom = get_region_geometry(region_name)
        except Exception as e:
            print(f"  Geometry error: {e} — skipping.")
            skipped.append(region_name); continue

        # Base rasters (LULC + NL) — reuse cache from previous run
        try:
            base = fetch_base_rasters(region_name, geom, CACHE_DIR)
        except Exception as e:
            print(f"  Base raster error: {e} — skipping.")
            skipped.append(region_name); continue

        if not base["lulc"] or not base["nl"]:
            skipped.append(region_name); continue

        # S5P rasters
        try:
            s5p_paths = fetch_s5p_rasters(region_name, geom, s5p_dir)
        except Exception as e:
            print(f"  S5P download error: {e}")
            s5p_paths = {k: None for k in ("no2","so2","co","ch4","aer")}

        # Load all rasters
        try:
            lulc, lulc_tr, _ = load_raster(base["lulc"])
            nl,   nl_tr,   _ = load_raster(base["nl"])
        except Exception as e:
            print(f"  Raster load error: {e} — skipping.")
            skipped.append(region_name); continue

        nl_res = resample_to(nl, lulc.shape)

        s5p_arrs = {}
        for key, path in s5p_paths.items():
            if path and Path(str(path)).exists():
                try:
                    arr, _, _ = load_raster(Path(str(path)))
                    s5p_arrs[key] = arr
                except Exception:
                    s5p_arrs[key] = None
            else:
                s5p_arrs[key] = None

        pixel_deg      = abs(lulc_tr.a)
        pixel_area_km2 = (pixel_deg * 111.0) ** 2

        # Emission estimates
        sectors_all = ["electricity_heat","residential_commercial","industry_combustion",
                       "transport","fugitive_emissions","ippu","agriculture","waste","lulucf"]
        original_Mt = {s: float(row[s]) if s in row.index and not pd.isna(row[s]) else 0.0
                       for s in sectors_all}
        refined_Mt  = compute_refined_Mt(original_Mt, lulc, nl_res)

        # Build emission grid
        print(f"  Building S5P-constrained emission grid ({lulc.shape[0]}x{lulc.shape[1]})...")
        try:
            grid, proxies, full_mask, s5p_rel = build_emission_grid(
                lulc, nl_res, s5p_arrs, refined_Mt, pixel_area_km2)
        except Exception as e:
            print(f"  Grid error: {e} — skipping.")
            skipped.append(region_name); continue

        pos = grid[grid > 0]
        if pos.size > 0:
            print(f"  Grid range: {pos.min():.1f} – {pos.max():.1f} t/km2  "
                  f"(mean {pos.mean():.1f})")
        print(f"  S5P reliability: {s5p_rel:.2f}  "
              f"({'HIGH' if s5p_rel>=0.75 else 'MODERATE' if s5p_rel>=0.40 else 'LOW'})")

        lulc_comp = lulc_composition(lulc)
        nl_data   = nl_res.filled(0).astype(float)

        print(f"  Rendering...")
        try:
            draw_map(region_name, grid, lulc, nl_data, lulc_tr,
                     s5p_arrs, refined_Mt, original_Mt, lulc_comp, out_path,
                     s5p_reliability=s5p_rel)
            processed.append(region_name)
        except Exception as e:
            print(f"  Render error: {e}")
            skipped.append(region_name)

        time.sleep(0.5)

    print(f"\n{'='*60}")
    print(f"Done. Processed: {len(processed)}  Skipped: {len(skipped)}")
    if skipped: print(f"Skipped: {skipped}")
    print(f"Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
