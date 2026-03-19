"""
GHG Emission Intensity Maps — All Uzbekistan Regions (2022)

For each administrative region:
  1. Fetch GAUL Level-1 boundary from Earth Engine
  2. Download ESRI 10m LULC and VIIRS nightlight rasters
  3. Read proxy-based emission estimates from the Excel workbook
  4. Spatially disaggregate emissions using LULC class + nightlight intensity
  5. Apply distance-decay blend + Gaussian smoothing for continuous field
  6. Produce a publication-quality map (fixed legend, colorbar, sector insets)

Legend fix vs previous version
-------------------------------
- LULC legend is now a dedicated axes panel (no more overwrite bug)
- Colorbar displays actual t CO2-eq/km2 values (not log ticks)
- Sector inset uses a compact grouped bar, not a fragile inset_axes call
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
from matplotlib.colors import LinearSegmentedColormap
from scipy.ndimage import gaussian_filter, zoom
import pandas as pd
import openpyxl

import ee
from services import gee as gee_svc
from services.utils import make_json_safe

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
OUT_DIR   = ROOT / "suhi_analysis_output" / "regional_ghg_maps"
XLSX_PATH = ROOT / "uzbekistan_emissions_by_region_2022 (1)+.xlsx"
YEAR      = 2022
LULC_SCALE = 200   # metres
NL_SCALE   = 500   # metres

ESRI_CLASSES = {1:"Water",2:"Trees",4:"Flooded_Vegetation",5:"Crops",
                7:"Built_Area",8:"Bare_Ground",9:"Snow_Ice",10:"Clouds",11:"Rangeland"}
BUILT=7; CROPS=5; FLOODED=4; TREES=2; RANGELAND=11; BARE=8; WATER=1

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
ESRI_ID_PALETTE = {
    1:"#419BDF",2:"#397D49",4:"#7A87C6",5:"#E49635",
    7:"#C4281B",8:"#A59B8F",9:"#B39FE1",11:"#DFC35A",
}

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

SECTOR_PROXIES_SPATIAL = {
    "electricity_heat":       {BUILT:0.4,"__nl":0.6},
    "residential_commercial": {BUILT:0.7,"__nl":0.3},
    "industry_combustion":    {BUILT:0.2,BARE:0.1,"__nl":0.7},
    "transport":              {BUILT:0.5,"__nl":0.5},
    "fugitive_emissions":     {"__uniform":1.0},
    "ippu":                   {BUILT:0.1,BARE:0.2,"__nl":0.7},
    "agriculture":            {CROPS:0.7,FLOODED:0.3},
    "waste":                  {BUILT:0.8,"__nl":0.2},
}
LULUCF_PROXIES = {TREES:-1.0, RANGELAND:-0.05}

# Excel region name → GAUL ADM1 candidate strings (tried in order)
REGION_GAUL_MAP = {
    "Tashkent City":      ["Toshkent shahri","Tashkent City","Toshkent City"],
    "Tashkent Region":    ["Toshkent","Tashkent"],
    "Navoi Region":       ["Navoiy","Navoi"],
    "Kashkadarya Region": ["Qashqadaryo","Kashkadarya","Kashqadaryo"],
    "Bukhara Region":     ["Buxoro","Bukhara"],
    "Samarkand Region":   ["Samarqand","Samarkand"],
    "Fergana Region":     ["Farg'ona","Fergana","Farghona"],
    "Andijan Region":     ["Andijon","Andijan"],
    "Namangan Region":    ["Namangan"],
    "Surkhandarya Region":["Surxondaryo","Surkhandarya"],
    "Khorezm Region":     ["Xorazm","Khorezm","Khwarazm"],
    "Jizzakh Region":     ["Jizzax","Jizzakh"],
    "Syrdarya Region":    ["Sirdaryo","Syrdarya"],
    "Rep. Karakalpakstan":["Qoraqalpog'iston","Karakalpakstan","Qoraqalpog"],
}

# Fallback centre + radius for regions where GAUL lookup fails
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
    df = pd.DataFrame([list(r) + [None]*(n_cols-len(r)) for r in data_rows],
                      columns=range(n_cols))

    col_names = ["region","electricity_heat","residential_commercial",
                 "industry_combustion","transport","fugitive_emissions",
                 "ippu","agriculture","waste","lulucf","total",
                 "national_share","net_total"]
    df = df.rename(columns={i: col_names[i] for i in range(min(len(col_names), n_cols))})
    df["region"] = df["region"].astype(str).str.strip()
    excludes = ["nan","None","Note","Source","SUM OF","NATIONAL","Allocation"]
    mask = df["region"].notna()
    for p in excludes:
        mask &= ~df["region"].str.startswith(p)
    df = df[mask].copy()
    for col in col_names[1:]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# GEE helpers
# ---------------------------------------------------------------------------

def get_region_geometry(region_name: str) -> ee.Geometry:
    """Try GAUL lookup; fall back to buffer if not found."""
    gaul = ee.FeatureCollection("FAO/GAUL/2015/level1")
    uz   = gaul.filter(ee.Filter.eq("ADM0_NAME", "Uzbekistan"))

    # For Tashkent Region specifically, exclude the City feature
    exclude_city = region_name == "Tashkent Region"

    candidates = REGION_GAUL_MAP.get(region_name, [region_name])
    for name in candidates:
        try:
            filt = uz.filter(ee.Filter.stringContains("ADM1_NAME", name.split("'")[0]))
            if exclude_city:
                filt = filt.filter(
                    ee.Filter.Not(ee.Filter.stringContains("ADM1_NAME", "shahri"))
                ).filter(
                    ee.Filter.Not(ee.Filter.stringContains("ADM1_NAME", "City"))
                )
            if filt.size().getInfo() > 0:
                geom = filt.geometry()
                area = geom.area().getInfo() / 1e6
                print(f"    GAUL match '{name}': ~{area:,.0f} km2")
                return geom
        except Exception:
            continue

    # Fallback
    lon, lat, buf = REGION_FALLBACKS.get(region_name, (65.0, 40.0, 200_000))
    print(f"    GAUL lookup failed for '{region_name}' — using fallback buffer")
    return ee.Geometry.Point([lon, lat]).buffer(buf).bounds()


def download_geotiff(image: ee.Image, region: ee.Geometry, scale: int,
                     out_path: Path, fname: str) -> Path | None:
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
                    if chunk:
                        fh.write(chunk)
            return p
        print(f"    Download failed ({r.status_code})")
    except Exception as e:
        print(f"    Download error: {e}")
    return None


def fetch_region_rasters(region_name: str, geom: ee.Geometry,
                         cache_dir: Path) -> dict:
    region_geo = geom.bounds().getInfo()["coordinates"]
    region_ee  = ee.Geometry.Polygon(region_geo)
    slug = region_name.replace(" ", "_").replace(".", "").replace("'", "")
    rdir = cache_dir / slug

    # LULC
    lulc_path = rdir / f"lulc_{slug}_{YEAR}.tif"
    if not lulc_path.exists():
        print(f"    Downloading LULC...")
        esri = (ee.ImageCollection("projects/sat-io/open-datasets/landcover/ESRI_Global-LULC_10m_TS")
                .filterDate(f"{YEAR}-01-01", f"{YEAR}-12-31")
                .filterBounds(region_ee).mosaic().clip(region_ee))
        lulc_path = download_geotiff(esri, region_ee, LULC_SCALE, rdir, lulc_path.name)
    else:
        print(f"    LULC cached.")

    # Nightlights
    nl_path = rdir / f"nl_{slug}_{YEAR}.tif"
    if not nl_path.exists():
        print(f"    Downloading nightlights...")
        nl = (ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG")
              .filterDate(f"{YEAR}-01-01", f"{YEAR}-12-31")
              .filterBounds(region_ee).select("avg_rad").median().clip(region_ee))
        nl_path = download_geotiff(nl, region_ee, NL_SCALE, rdir, nl_path.name)
    else:
        print(f"    Nightlights cached.")

    time.sleep(1)
    return {"lulc": lulc_path, "nl": nl_path}


# ---------------------------------------------------------------------------
# Raster processing
# ---------------------------------------------------------------------------

def load_raster(path: Path):
    import rasterio
    with rasterio.open(path) as src:
        data = src.read(1, masked=True)
        transform = src.transform
        bounds = src.bounds
    return data, transform, bounds


def resample_to_match(src_arr: np.ma.MaskedArray, src_shape, tgt_shape):
    zy = tgt_shape[0] / src_shape[0]
    zx = tgt_shape[1] / src_shape[1]
    data = zoom(src_arr.filled(0).astype(float), (zy, zx), order=1)
    msk  = src_arr.mask
    if np.isscalar(msk) or msk.shape == ():
        mask_z = np.zeros(tgt_shape, bool)
    else:
        mask_z = zoom(msk.astype(float), (zy, zx), order=0) > 0.5
    return np.ma.array(data, mask=mask_z)


def build_sector_proxy(lulc_data, nl_norm, proxy_def, full_mask):
    proxy = np.zeros(lulc_data.shape, dtype=float)
    nl_w  = proxy_def.get("__nl", 0.0)
    uni   = proxy_def.get("__uniform", 0.0)
    for k, w in proxy_def.items():
        if k in ("__nl", "__uniform"):
            continue
        proxy += w * (lulc_data == k).astype(float)
    if nl_w > 0:
        proxy += nl_w * (lulc_data == BUILT).astype(float) * nl_norm
    if uni > 0:
        proxy += uni * full_mask.astype(float)
    return proxy * full_mask.astype(float)


def compute_intensity(lulc, nl_norm, full_mask, refined_Mt, pixel_area_km2):
    lulc_data = lulc.filled(0).astype(int)
    total = np.zeros(lulc.shape, dtype=float)
    for sector, pdef in SECTOR_PROXIES_SPATIAL.items():
        mt = refined_Mt.get(sector) or 0.0
        if mt == 0:
            continue
        raw = build_sector_proxy(lulc_data, nl_norm, pdef, full_mask)
        s   = raw[full_mask].sum()
        if s > 0:
            total += (raw / s) * mt * 1e6 / pixel_area_km2
    # LULUCF sink
    lmt = refined_Mt.get("lulucf") or 0.0
    if lmt != 0:
        lp = sum(w * (lulc_data == c).astype(float) * full_mask
                 for c, w in LULUCF_PROXIES.items())
        s  = np.abs(lp[full_mask]).sum()
        if s > 0:
            total += (lp / s) * lmt * 1e6 / pixel_area_km2
    return total


def build_emission_grid(lulc, nl_resampled, refined_Mt, pixel_area_km2):
    full_mask = (~lulc.mask) if (hasattr(lulc,"mask") and lulc.mask.ndim>0) \
                else np.ones(lulc.shape, bool)
    nl_data = nl_resampled.filled(0).astype(float)
    nl_max  = np.percentile(nl_data[nl_data > 0], 98) if (nl_data > 0).any() else 1.0
    nl_norm = np.clip(nl_data / nl_max, 0, 1)

    grid = compute_intensity(lulc, nl_norm, full_mask, refined_Mt, pixel_area_km2)
    # Gaussian smoothing
    grid = gaussian_filter(grid, sigma=4)
    return grid, nl_norm, nl_data


def lulc_composition(lulc) -> dict:
    """Return {class_name: fraction} from masked lulc array."""
    data = lulc.filled(0).astype(int)
    valid = data[data > 0]
    if valid.size == 0:
        return {}
    total = valid.size
    result = {}
    for cid, name in ESRI_CLASSES.items():
        count = (data == cid).sum()
        if count > 0:
            result[name] = count / total
    return result


# ---------------------------------------------------------------------------
# Figure drawing
# ---------------------------------------------------------------------------

def draw_map(region_name: str, emission_grid: np.ndarray,
             lulc, nl_data, lulc_transform,
             refined_Mt: dict, original_Mt: dict,
             lulc_comp: dict, out_path: Path):

    rows, cols = emission_grid.shape
    west  = lulc_transform.c
    east  = lulc_transform.c + cols * lulc_transform.a
    north = lulc_transform.f
    south = lulc_transform.f + rows * lulc_transform.e
    extent = [west, east, south, north]

    # Log scale
    pos_vals = emission_grid[emission_grid > 0]
    if pos_vals.size == 0:
        print(f"  WARNING: no positive emission values for {region_name}")
        return
    log_min = np.log10(max(np.percentile(pos_vals, 2), 1.0))
    log_max = np.log10(np.percentile(pos_vals, 99.5))

    # -----------------------------------------------------------------------
    # Figure layout: 3 rows × 4 cols
    #   Row 0 (tall)  : main map [cols 0-3]
    #   Row 1 (short) : colorbar [cols 0-3]
    #   Row 2 (medium): sector bars [cols 0-1] | LULC legend [col 2] | pie [col 3]
    # -----------------------------------------------------------------------
    fig = plt.figure(figsize=(18, 16))
    fig.patch.set_facecolor("#0E1117")

    gs = gridspec.GridSpec(
        3, 4, figure=fig,
        height_ratios=[10, 0.5, 3.5],
        hspace=0.35, wspace=0.35,
        top=0.93, bottom=0.03, left=0.06, right=0.97,
    )

    ax_map  = fig.add_subplot(gs[0, :])
    ax_cbar = fig.add_subplot(gs[1, :])
    ax_bars = fig.add_subplot(gs[2, :2])
    ax_leg  = fig.add_subplot(gs[2, 2])
    ax_pie  = fig.add_subplot(gs[2, 3])

    # ---- LULC faint background ----
    lulc_rgba = np.zeros((*lulc.shape, 4), dtype=float)
    import matplotlib.colors as mcolors
    for cid, hex_col in ESRI_ID_PALETTE.items():
        rgba = mcolors.to_rgba(hex_col, 0.18)
        mask = lulc.filled(0).astype(int) == cid
        for c in range(4):
            lulc_rgba[mask, c] = rgba[c]
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
        nl_max_disp = float(np.percentile(nl_sm[nl_sm > 0], 95)) if (nl_sm > 0).any() else 10
        levels = [v for v in [0.5, 1, 3, 8, 20, 50]
                  if v < nl_max_disp and v > float(nl_sm.min())]
        if levels:
            x_nl = np.linspace(west, east, nl_sm.shape[1])
            y_nl = np.linspace(north, south, nl_sm.shape[0])
            X, Y = np.meshgrid(x_nl, y_nl)
            cs = ax_map.contour(X, Y, nl_sm, levels=levels,
                                colors="white", linewidths=0.4, alpha=0.30)
            ax_map.clabel(cs, fmt="%.0f", fontsize=5, colors="white")
    except Exception:
        pass

    # ---- Map style ----
    refined_total = sum(v for k, v in refined_Mt.items()
                        if k != "lulucf" and v is not None and v > 0)
    ax_map.set_title(
        f"{region_name}  —  Refined total: {refined_total:.2f} Mt CO\u2082-eq (excl. LULUCF)",
        fontsize=10, fontweight="bold", color="white", pad=6,
    )
    ax_map.set_xlabel("Longitude", fontsize=8, color="white")
    ax_map.set_ylabel("Latitude",  fontsize=8, color="white")
    ax_map.tick_params(colors="white", labelsize=7)
    for sp in ax_map.spines.values():
        sp.set_edgecolor("#444")
    ax_map.set_facecolor("#0E1117")

    # ---- Colorbar (dedicated axis) ----
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

    # ---- Sector bars: original vs refined ----
    sectors = list(SECTOR_LABELS.keys())
    x = np.arange(len(sectors))
    w = 0.35
    orig_vals    = [float(original_Mt.get(s) or 0) for s in sectors]
    refined_vals = [float(refined_Mt.get(s)  or 0) for s in sectors]
    bars_orig = ax_bars.bar(x - w/2, orig_vals, w, color="#546E7A",
                            label="Original (proxy)", alpha=0.9, edgecolor="white", lw=0.4)
    bars_ref  = ax_bars.bar(x + w/2, refined_vals, w,
                            color=[SECTOR_COLORS[i] for i in range(len(sectors))],
                            label="Refined (LULC + NL)", alpha=0.9, edgecolor="white", lw=0.4)
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
    for sp in ax_bars.spines.values():
        sp.set_edgecolor("#444")
    ax_bars.yaxis.grid(True, alpha=0.2, lw=0.5, color="white")
    ax_bars.set_axisbelow(True)
    ax_bars.legend(fontsize=7, facecolor="#16191F", labelcolor="white",
                   edgecolor="#444", loc="upper right")

    # ---- LULC legend panel (all 8 classes, always shown) ----
    ax_leg.set_facecolor("#16191F")
    ax_leg.set_title("ESRI Land Cover Classes", fontsize=8,
                     fontweight="bold", color="white", pad=4)
    ax_leg.axis("off")
    for sp in ax_leg.spines.values():
        sp.set_edgecolor("#444")
    legend_items = list(ESRI_PALETTE.items())  # 8 fixed entries
    n_items = len(legend_items)
    for i, (label, color) in enumerate(legend_items):
        row = i % 4
        col = i // 4
        y_pos = 0.90 - row * 0.22
        x_pos = 0.05 + col * 0.52
        ax_leg.add_patch(mpatches.FancyBboxPatch(
            (x_pos, y_pos - 0.07), 0.10, 0.14,
            boxstyle="round,pad=0.01", facecolor=color,
            transform=ax_leg.transAxes, clip_on=False, zorder=3,
        ))
        ax_leg.text(x_pos + 0.13, y_pos, label, transform=ax_leg.transAxes,
                    fontsize=7, color="white", va="center")

    # ---- LULC pie chart ----
    ax_pie.set_facecolor("#16191F")
    ax_pie.set_title("Land Cover Composition", fontsize=8,
                     fontweight="bold", color="white", pad=4)
    if lulc_comp:
        sorted_comp = sorted(lulc_comp.items(), key=lambda x: -x[1])
        labels  = [c[0] for c in sorted_comp]
        sizes   = [c[1]*100 for c in sorted_comp]
        # Map class name to colour from ESRI_ID_PALETTE (via ESRI_CLASSES inverse)
        inv_cls = {v: k for k, v in ESRI_CLASSES.items()}
        pie_colors = [ESRI_ID_PALETTE.get(inv_cls.get(l, 0), "#888") for l in labels]
        wedges, _, autotexts = ax_pie.pie(
            sizes, colors=pie_colors,
            autopct=lambda p: f"{p:.0f}%" if p > 4 else "",
            startangle=140,
            wedgeprops={"width": 0.55, "edgecolor": "#16191F", "linewidth": 0.8},
            pctdistance=0.78,
            textprops={"fontsize": 6, "color": "white"},
        )
        for t in autotexts:
            t.set_fontsize(5.5)
        # Compact legend below pie
        pie_patches = [mpatches.Patch(color=pie_colors[i],
                                      label=f"{labels[i]} {sizes[i]:.0f}%")
                       for i in range(len(labels))]
        ax_pie.legend(handles=pie_patches, loc="lower center",
                      bbox_to_anchor=(0.5, -0.30), fontsize=5.8, ncol=2,
                      facecolor="#16191F", labelcolor="white",
                      edgecolor="#444", framealpha=0.8)
    else:
        ax_pie.text(0.5, 0.5, "No LULC data", ha="center", va="center",
                    transform=ax_pie.transAxes, color="white", fontsize=8)

    # ---- Overall title ----
    fig.text(0.5, 0.965,
             f"GHG Emissions — {region_name} (2022)",
             ha="center", fontsize=14, fontweight="bold", color="white")
    fig.text(0.5, 0.945,
             "Spatially disaggregated using ESRI 10m LULC + VIIRS Nightlights  |  "
             "Refined from BTR1 Uzbekistan proxy-based estimates",
             ha="center", fontsize=8, color="#AAAAAA")

    # ---- Footnote ----
    fig.text(0.5, 0.005,
             "Sources: ESRI Global LULC 10m TS; NOAA/VIIRS DNB Monthly; "
             "BTR1 Uzbekistan to UNFCCC (2024). "
             "Proxy: Built+NL (urban), Crops (agriculture), Trees (LULUCF).",
             ha="center", fontsize=6, color="#666", style="italic")

    fig.savefig(out_path, dpi=180, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  Saved: {out_path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cache_dir = OUT_DIR / "_raster_cache"

    # GEE
    print("Initializing GEE...")
    if not gee_svc.initialize_gee():
        print("ERROR: GEE init failed.")
        sys.exit(1)

    # Load emissions
    print("Loading emissions data...")
    df = load_emissions_excel(XLSX_PATH)
    print(f"  Regions found: {df['region'].tolist()}")

    # Map row → region name using REGION_GAUL_MAP keys
    def match_region(row_name: str) -> str | None:
        for key in REGION_GAUL_MAP:
            if key.lower() in row_name.lower() or row_name.lower() in key.lower():
                return key
        return None

    skipped = []
    processed = []

    for _, row in df.iterrows():
        region_name = match_region(row["region"])
        if region_name is None:
            print(f"\nSkipping unrecognised row: '{row['region']}'")
            skipped.append(row["region"])
            continue

        slug = region_name.replace(" ", "_").replace(".", "").replace("'", "")
        out_path = OUT_DIR / f"ghg_{slug}_{YEAR}.png"

        print(f"\n{'='*60}")
        print(f"Processing: {region_name}")
        print(f"{'='*60}")

        # --- GEE boundary ---
        try:
            geom = get_region_geometry(region_name)
        except Exception as e:
            print(f"  ERROR getting geometry: {e} — skipping.")
            skipped.append(region_name)
            continue

        # --- Download rasters ---
        try:
            rasters = fetch_region_rasters(region_name, geom, cache_dir)
        except Exception as e:
            print(f"  ERROR downloading rasters: {e} — skipping.")
            skipped.append(region_name)
            continue

        if not rasters["lulc"] or not rasters["nl"]:
            print(f"  ERROR: raster download returned None — skipping.")
            skipped.append(region_name)
            continue

        # --- Load rasters ---
        try:
            lulc, lulc_transform, lulc_bounds = load_raster(rasters["lulc"])
            nl,   nl_transform,   nl_bounds   = load_raster(rasters["nl"])
        except Exception as e:
            print(f"  ERROR loading rasters: {e} — skipping.")
            skipped.append(region_name)
            continue

        nl_res = resample_to_match(nl, nl.shape, lulc.shape)

        pixel_deg    = abs(lulc_transform.a)
        pixel_km     = pixel_deg * 111.0
        pixel_area_km2 = pixel_km ** 2

        # --- Emission totals ---
        sectors_all = ["electricity_heat","residential_commercial","industry_combustion",
                       "transport","fugitive_emissions","ippu","agriculture","waste","lulucf"]
        original_Mt = {s: (float(row[s]) if s in row.index and not pd.isna(row[s]) else 0.0)
                       for s in sectors_all}

        # Simple refinement: use original values scaled by LULC fractions
        # (full refinement pipeline already done for Tashkent;
        #  for other regions apply the same proxy weighting inline)
        lulc_comp_frac = lulc_composition(lulc)
        built_frac   = lulc_comp_frac.get("Built_Area", 0)
        crops_frac   = lulc_comp_frac.get("Crops", 0)
        flooded_frac = lulc_comp_frac.get("Flooded_Vegetation", 0)
        trees_frac   = lulc_comp_frac.get("Trees", 0)
        bare_frac    = lulc_comp_frac.get("Bare_Ground", 0)
        rangeland_frac = lulc_comp_frac.get("Rangeland", 0)

        nl_data_raw = nl_res.filled(0).astype(float)
        nl_max_reg  = np.percentile(nl_data_raw[nl_data_raw > 0], 98) \
                      if (nl_data_raw > 0).any() else 1.0
        nl_score    = float(np.mean(nl_data_raw[nl_data_raw > 0]) / nl_max_reg) \
                      if (nl_data_raw > 0).any() else 0.0

        def blend(prior, lulc_component, lulc_weight, nl_weight, prior_weight):
            adj = lulc_weight * lulc_component + nl_weight * nl_score + prior_weight * 1.0
            return prior * adj

        refined_Mt = {
            "electricity_heat":       blend(original_Mt["electricity_heat"],
                                            built_frac, 0.20, 0.50, 0.30),
            "residential_commercial": blend(original_Mt["residential_commercial"],
                                            built_frac, 0.55, 0.20, 0.25),
            "industry_combustion":    blend(original_Mt["industry_combustion"],
                                            0.75*built_frac+0.25*bare_frac, 0.20, 0.50, 0.30),
            "transport":              blend(original_Mt["transport"],
                                            built_frac, 0.35, 0.35, 0.30),
            "fugitive_emissions":     original_Mt["fugitive_emissions"] * (0.25*nl_score + 0.75),
            "ippu":                   blend(original_Mt["ippu"],
                                            0.5*built_frac+0.5*bare_frac, 0.10, 0.50, 0.40),
            "agriculture":            blend(original_Mt["agriculture"],
                                            0.7*crops_frac+0.3*flooded_frac, 0.65, 0.00, 0.35),
            "waste":                  blend(original_Mt["waste"], built_frac, 0.45, 0.00, 0.55),
            "lulucf":                 blend(original_Mt["lulucf"],
                                            trees_frac+0.1*rangeland_frac, 0.65, 0.00, 0.35),
        }

        # --- Build emission grid ---
        print(f"  Building emission grid ({lulc.shape[0]}x{lulc.shape[1]} px)...")
        try:
            grid, nl_norm, nl_data = build_emission_grid(
                lulc, nl_res, refined_Mt, pixel_area_km2
            )
        except Exception as e:
            print(f"  ERROR building grid: {e} — skipping.")
            skipped.append(region_name)
            continue

        pos = grid[grid > 0]
        if pos.size > 0:
            print(f"  Grid range: {pos.min():.1f} – {pos.max():.1f} t/km2  "
                  f"(mean {pos.mean():.1f})")

        # --- Draw map ---
        print(f"  Rendering map...")
        try:
            draw_map(
                region_name, grid, lulc, nl_data, lulc_transform,
                refined_Mt, original_Mt, lulc_comp_frac, out_path,
            )
            processed.append(region_name)
        except Exception as e:
            print(f"  ERROR rendering: {e}")
            skipped.append(region_name)

        time.sleep(1)

    # Summary
    print(f"\n{'='*60}")
    print(f"Done.  Processed: {len(processed)}  Skipped: {len(skipped)}")
    print(f"Processed: {processed}")
    if skipped:
        print(f"Skipped:   {skipped}")
    print(f"Output dir: {OUT_DIR}")


if __name__ == "__main__":
    main()
