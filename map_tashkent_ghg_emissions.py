"""Create a multi-panel GHG emissions map for Tashkent City + Tashkent Region.

Panels
------
A  Spatial map: ESRI LULC raster (downloaded from GEE) with admin boundaries
   overlaid, coloured by dominant emission driver.
B  Nightlight intensity raster for the same extent.
C  Stacked bar: original vs refined emissions by sector (both units).
D  LULC composition donut charts per unit.
E  Sector breakdown: refined emissions treemap per unit.
"""
import sys, json, time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
from matplotlib.colors import ListedColormap, BoundaryNorm
from mpl_toolkits.axes_grid1 import make_axes_locatable
import requests

# GEE
import ee
from services import gee as gee_svc
from services.utils import make_json_safe

# -----------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------
OUT_DIR     = ROOT / "suhi_analysis_output" / "emissions_refinement"
RESULTS_JSON = OUT_DIR / "tashkent_refined_emissions_2022.json"
RESULTS_JSON = OUT_DIR / "tashkent_refined_emissions_2022.json"
YEAR = 2022

# ESRI class → colour (same palette as ESRI Living Atlas)
ESRI_PALETTE = {
    "Water":             "#419BDF",
    "Trees":             "#397D49",
    "Flooded_Vegetation":"#7A87C6",
    "Crops":             "#E49635",
    "Built_Area":        "#C4281B",
    "Bare_Ground":       "#A59B8F",
    "Snow_Ice":          "#B39FE1",
    "Clouds":            "#FFFFFF",
    "Rangeland":         "#DFC35A",
    "Unknown":           "#888888",
}

# ESRI class ID → class name (for raster decoding)
ESRI_ID_TO_NAME = {
    1: "Water", 2: "Trees", 4: "Flooded_Vegetation",
    5: "Crops", 7: "Built_Area", 8: "Bare_Ground",
    9: "Snow_Ice", 10: "Clouds", 11: "Rangeland",
}

SECTOR_LABELS = {
    "electricity_heat":        "Electricity & Heat",
    "residential_commercial":  "Residential & Commercial",
    "industry_combustion":     "Industry Combustion",
    "transport":               "Transport",
    "fugitive_emissions":      "Fugitive Emissions",
    "ippu":                    "IPPU",
    "agriculture":             "Agriculture",
    "waste":                   "Waste",
}
SECTOR_COLORS = [
    "#E63946", "#457B9D", "#F4A261", "#2A9D8F",
    "#E9C46A", "#264653", "#A8DADC", "#F1FAEE",
]

# Tashkent City fallback bbox (approximate city extent)
CITY_BBOX   = [69.14, 41.19, 69.38, 41.42]  # [west, south, east, north]
# Tashkent Oblast boundary (tighter — city excluded from this bbox)
OBLAST_BBOX = [68.9,  40.65, 71.25, 41.80]  # Tashkent Oblast approx
# Map view extent (slightly wider than oblast)
REGION_BBOX = [68.7,  40.50, 71.5,  42.00]


# -----------------------------------------------------------------------
# GEE raster downloads
# -----------------------------------------------------------------------

def _download_thumb(image: ee.Image, region_geojson, vis_params: dict,
                    out_path: Path, fname: str, dim: int = 1024) -> Path | None:
    try:
        url = image.visualize(**vis_params).getThumbURL(
            {"region": region_geojson, "dimensions": dim, "format": "png"}
        )
        out_path.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, timeout=90)
        if r.status_code == 200:
            p = out_path / fname
            p.write_bytes(r.content)
            return p
    except Exception as e:
        print(f"  Thumb download failed ({fname}): {e}")
    return None


def _download_geotiff(image: ee.Image, region_geojson, scale: int,
                      out_path: Path, fname: str) -> Path | None:
    try:
        url = image.getDownloadURL({
            "scale": scale, "crs": "EPSG:4326",
            "region": region_geojson, "format": "GEO_TIFF"
        })
        out_path.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, stream=True, timeout=180)
        if r.status_code == 200:
            p = out_path / fname
            with open(p, "wb") as fh:
                for chunk in r.iter_content(8192):
                    if chunk:
                        fh.write(chunk)
            return p
    except Exception as e:
        print(f"  GeoTIFF download failed ({fname}): {e}")
    return None


def fetch_rasters(out_dir: Path) -> dict:
    """Download LULC and nightlight GeoTIFFs for the map extent."""
    paths = {}

    # Use the full map view extent for downloads
    region = ee.Geometry.Rectangle(REGION_BBOX)
    region_geo = region.bounds().getInfo()["coordinates"]

    # --- ESRI LULC 2022 (aggregate to 200m for download size) ---
    print("  Downloading ESRI LULC raster...")
    esri_col = ee.ImageCollection(
        "projects/sat-io/open-datasets/landcover/ESRI_Global-LULC_10m_TS"
    )
    esri = (esri_col
            .filterDate(f"{YEAR}-01-01", f"{YEAR}-12-31")
            .filterBounds(region)
            .mosaic()
            .clip(region))

    lulc_path = _download_geotiff(esri, region_geo, 200, out_dir, "lulc_tashkent_200m.tif")
    paths["lulc"] = lulc_path

    # PNG thumb for quick display (ESRI class palette: 1–11)
    esri_vis = {
        "min": 1, "max": 11,
        "palette": [
            "#419BDF",  # 1 Water
            "#397D49",  # 2 Trees
            "#888888",  # 3 (unused)
            "#7A87C6",  # 4 Flooded_Veg
            "#E49635",  # 5 Crops
            "#888888",  # 6 (unused)
            "#C4281B",  # 7 Built
            "#A59B8F",  # 8 Bare
            "#B39FE1",  # 9 Snow/Ice
            "#FFFFFF",  # 10 Clouds
            "#DFC35A",  # 11 Rangeland
        ]
    }
    thumb_lulc = _download_thumb(esri, region_geo, esri_vis, out_dir, "lulc_thumb.png", dim=1200)
    paths["lulc_thumb"] = thumb_lulc
    time.sleep(1)

    # --- VIIRS nightlights 2022 ---
    print("  Downloading VIIRS nightlights raster...")
    nl = (ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG")
          .filterDate(f"{YEAR}-01-01", f"{YEAR}-12-31")
          .filterBounds(region)
          .select("avg_rad")
          .median()
          .clip(region))

    nl_path = _download_geotiff(nl, region_geo, 500, out_dir, "nightlights_tashkent_500m.tif")
    paths["nightlights"] = nl_path

    nl_vis = {"min": 0, "max": 40,
              "palette": ["000000", "0d0887", "6a00a8", "b12a90",
                          "e16462", "fca636", "f0f921"]}
    thumb_nl = _download_thumb(nl, region_geo, nl_vis, out_dir, "nl_thumb.png", dim=1200)
    paths["nl_thumb"] = thumb_nl
    time.sleep(1)

    return paths


# -----------------------------------------------------------------------
# Raster reading helpers (rasterio optional)
# -----------------------------------------------------------------------

def read_raster_as_array(tif_path: Path):
    """Return (data_array, extent=[west,east,south,north]) or (None, None)."""
    try:
        import rasterio
        with rasterio.open(tif_path) as src:
            data = src.read(1, masked=True)
            bounds = src.bounds
            extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
        return data, extent
    except Exception as e:
        print(f"  rasterio read failed: {e}")
        return None, None


# -----------------------------------------------------------------------
# Plot helpers
# -----------------------------------------------------------------------

def make_lulc_cmap():
    """Build a ListedColormap for ESRI classes 0-11."""
    colors_list = ["#000000"] * 12  # index 0 = nodata
    for cid, name in ESRI_ID_TO_NAME.items():
        colors_list[cid] = ESRI_PALETTE.get(name, "#888888")
    cmap = ListedColormap(colors_list)
    norm = BoundaryNorm(boundaries=np.arange(-0.5, 12.5, 1), ncolors=12)
    return cmap, norm


def draw_lulc_map(ax, lulc_path, thumb_path, title="ESRI Land Cover 2022"):
    """Draw LULC raster on ax; fallback to PNG thumb if rasterio unavailable."""
    drawn = False
    if lulc_path and lulc_path.exists():
        arr, extent = read_raster_as_array(lulc_path)
        if arr is not None:
            cmap, norm = make_lulc_cmap()
            ax.imshow(arr, extent=extent, origin="upper", cmap=cmap, norm=norm,
                      interpolation="nearest", aspect="auto")
            # Legend patches
            patches = [mpatches.Patch(color=col, label=name)
                       for name, col in ESRI_PALETTE.items()
                       if name not in ("Clouds", "Unknown")]
            ax.legend(handles=patches, loc="lower left", fontsize=5.5,
                      framealpha=0.85, ncol=2)
            drawn = True

    if not drawn and thumb_path and thumb_path.exists():
        img = plt.imread(str(thumb_path))
        ax.imshow(img, extent=REGION_BBOX, origin="upper", aspect="auto")
        # simple legend
        patches = [mpatches.Patch(color=col, label=name)
                   for name, col in ESRI_PALETTE.items()
                   if name not in ("Clouds", "Unknown")]
        ax.legend(handles=patches, loc="lower left", fontsize=5.5,
                  framealpha=0.85, ncol=2)

    ax.set_title(title, fontsize=9, fontweight="bold")
    ax.set_xlabel("Longitude", fontsize=7)
    ax.set_ylabel("Latitude", fontsize=7)
    ax.tick_params(labelsize=6)


def draw_nightlight_map(ax, nl_path, thumb_path, title="VIIRS Nightlights 2022"):
    """Draw nightlight raster on ax."""
    drawn = False
    if nl_path and nl_path.exists():
        arr, extent = read_raster_as_array(nl_path)
        if arr is not None:
            nl_cmap = plt.cm.get_cmap("inferno")
            vmax = float(np.nanpercentile(arr.compressed(), 98)) if arr.count() > 0 else 50
            im = ax.imshow(arr, extent=extent, origin="upper",
                           cmap=nl_cmap, vmin=0, vmax=vmax,
                           interpolation="bilinear", aspect="auto")
            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="4%", pad=0.05)
            plt.colorbar(im, cax=cax, label="nW/cm2/sr")
            cax.tick_params(labelsize=6)
            drawn = True

    if not drawn and thumb_path and thumb_path.exists():
        img = plt.imread(str(thumb_path))
        ax.imshow(img, extent=REGION_BBOX, origin="upper", aspect="auto")

    ax.set_title(title, fontsize=9, fontweight="bold")
    ax.set_xlabel("Longitude", fontsize=7)
    ax.set_ylabel("Latitude", fontsize=7)
    ax.tick_params(labelsize=6)


def add_bbox_patch(ax, bbox, label, color, lw=1.5):
    """Draw a rectangle on a map axis."""
    from matplotlib.patches import Rectangle
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    rect = Rectangle((bbox[0], bbox[1]), w, h,
                      linewidth=lw, edgecolor=color, facecolor="none",
                      label=label, zorder=5)
    ax.add_patch(rect)


def draw_sector_bars(ax, results: list):
    """Grouped bar: original vs refined for each sector, per unit."""
    sectors = list(SECTOR_LABELS.keys())
    n = len(sectors)
    x = np.arange(n)
    width = 0.18
    unit_colors = {"Tashkent City": ("#2196F3", "#90CAF9"),
                   "Tashkent Region": ("#E53935", "#EF9A9A")}
    offsets = {"Tashkent City": -width, "Tashkent Region": width}

    for rec in results:
        unit = rec["region"]
        col_orig, col_ref = unit_colors.get(unit, ("#888", "#ccc"))
        orig = rec["original_emissions_Mt"]
        refi = rec["refined_emissions_Mt"]
        off = offsets.get(unit, 0)

        orig_vals = [orig.get(s) or 0 for s in sectors]
        refi_vals = [refi.get(s) or 0 for s in sectors]

        ax.bar(x + off - width/2, orig_vals, width, color=col_orig,
               label=f"{unit} (original)", alpha=0.85, edgecolor="white", linewidth=0.4)
        ax.bar(x + off + width/2, refi_vals, width, color=col_ref,
               label=f"{unit} (refined)", alpha=0.85, edgecolor="white", linewidth=0.4)

    ax.set_xticks(x)
    ax.set_xticklabels([SECTOR_LABELS[s] for s in sectors],
                       rotation=35, ha="right", fontsize=7)
    ax.set_ylabel("Emissions (Mt CO2-eq)", fontsize=7.5)
    ax.set_title("Original vs Refined Sector Emissions — Tashkent City (blue) & Tashkent Region (red)",
                 fontsize=9, fontweight="bold")
    ax.legend(fontsize=6.5, ncol=2, loc="upper right")
    ax.tick_params(axis="y", labelsize=7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)
    # delta annotation line at zero
    ax.axhline(0, color="#333", linewidth=0.6, linestyle="--", alpha=0.4)


def draw_lulc_donuts(ax_city, ax_region, results: list):
    """Draw LULC composition donuts for each unit."""
    unit_axes = {"Tashkent City": ax_city, "Tashkent Region": ax_region}
    for rec in results:
        unit = rec["region"]
        ax = unit_axes.get(unit)
        if ax is None:
            continue
        classes = rec["lulc_summary"]["classes"]
        if not classes:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            continue
        fracs = [(name, d["fraction"]) for name, d in classes.items()]
        fracs.sort(key=lambda x: -x[1])
        labels = [f[0] for f in fracs]
        sizes  = [f[1] * 100 for f in fracs]
        colors = [ESRI_PALETTE.get(l, "#888") for l in labels]
        wedges, texts, autotexts = ax.pie(
            sizes, labels=None, colors=colors,
            autopct=lambda p: f"{p:.1f}%" if p > 4 else "",
            startangle=140,
            wedgeprops={"width": 0.5, "edgecolor": "white", "linewidth": 0.6},
            pctdistance=0.75,
            textprops={"fontsize": 5.5},
        )
        for t in autotexts:
            t.set_fontsize(5)
        ax.set_title(f"{unit}\nLULC Composition", fontsize=8, fontweight="bold")
        # Legend
        patch_list = [mpatches.Patch(color=colors[i], label=f"{labels[i]} {sizes[i]:.1f}%")
                      for i in range(len(labels))]
        ax.legend(handles=patch_list, loc="lower center",
                  bbox_to_anchor=(0.5, -0.28), fontsize=5.5, ncol=2,
                  framealpha=0.7)


def draw_adjustment_heatmap(ax, results: list):
    """Heatmap of adjustment factors (refined/original ratio) per sector × unit."""
    sectors = list(SECTOR_LABELS.keys())
    units   = [rec["region"] for rec in results]
    matrix  = np.zeros((len(units), len(sectors)))
    for i, rec in enumerate(results):
        for j, sector in enumerate(sectors):
            adj = rec.get("adjustments", {}).get(sector, {})
            factor = adj.get("adjustment_factor")
            matrix[i, j] = factor if factor is not None else 1.0

    # Diverging colour map centred at 1.0
    vmin, vmax = 0.0, 2.0
    cmap = plt.cm.RdYlGn
    im = ax.imshow(matrix, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(sectors)))
    ax.set_xticklabels([SECTOR_LABELS[s] for s in sectors],
                       rotation=55, ha="right", fontsize=5.5)
    ax.set_yticks(range(len(units)))
    ax.set_yticklabels(units, fontsize=6)
    ax.set_title("Adjustment\nFactors\n(refined/original)", fontsize=7.5, fontweight="bold")
    # Cell values
    for i in range(len(units)):
        for j in range(len(sectors)):
            val = matrix[i, j]
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=5.5, color="black" if 0.4 < val < 1.6 else "white")
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="8%", pad=0.05)
    cb = plt.colorbar(im, cax=cax)
    cb.set_label("factor", fontsize=6)
    cb.ax.tick_params(labelsize=5.5)


def draw_emission_treemap(ax, rec: dict, title: str):
    """Draw a manual treemap-style bar for refined sector emissions."""
    sectors = [s for s in SECTOR_LABELS if s != "lulucf"]
    refi = rec["refined_emissions_Mt"]
    vals = [max(refi.get(s) or 0, 0) for s in sectors]
    total = sum(vals)
    if total == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        return

    fracs = [v / total for v in vals]
    colors = SECTOR_COLORS[:len(sectors)]

    # Horizontal stacked bar
    left = 0
    for i, (sector, frac, color) in enumerate(zip(sectors, fracs, colors)):
        ax.barh(0, frac, left=left, color=color, height=0.5,
                edgecolor="white", linewidth=0.8)
        if frac > 0.05:
            ax.text(left + frac / 2, 0, f"{SECTOR_LABELS[sector]}\n{vals[i]:.2f} Mt",
                    ha="center", va="center", fontsize=5.5, fontweight="bold",
                    color="white" if frac > 0.08 else "black")
        left += frac

    ax.set_xlim(0, 1)
    ax.set_ylim(-0.5, 0.5)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_title(f"{title}\nTotal refined: {sum(vals):.2f} Mt CO2-eq (excl. LULUCF)",
                 fontsize=8, fontweight="bold")
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Legend below
    patches = [mpatches.Patch(color=colors[i], label=f"{SECTOR_LABELS[sectors[i]]}")
               for i in range(len(sectors))]
    ax.legend(handles=patches, loc="lower center",
              bbox_to_anchor=(0.5, -0.55), fontsize=5.5, ncol=4, framealpha=0.7)


# -----------------------------------------------------------------------
# Main figure assembly
# -----------------------------------------------------------------------

def build_figure(results: list, raster_paths: dict, out_dir: Path):
    fig = plt.figure(figsize=(20, 24))
    fig.patch.set_facecolor("#F5F5F5")

    gs = gridspec.GridSpec(
        4, 4,
        figure=fig,
        hspace=0.45, wspace=0.35,
        top=0.93, bottom=0.04, left=0.05, right=0.97,
    )

    # ---- Row 0: GHG map (left 2 cols) + LULC map + Nightlight map ----
    ax_ghg  = fig.add_subplot(gs[0, :2])
    ax_lulc = fig.add_subplot(gs[0, 2:3])
    ax_nl   = fig.add_subplot(gs[0, 3:])

    # Load and display pre-generated GHG intensity map as image
    ghg_map_path = OUT_DIR / "tashkent_ghg_emission_intensity_2022.png"
    if ghg_map_path.exists():
        ghg_img = plt.imread(str(ghg_map_path))
        ax_ghg.imshow(ghg_img, aspect="auto")
        ax_ghg.axis("off")
        ax_ghg.set_title("GHG Emission Intensity (t CO\u2082-eq/km\u00b2, log scale)",
                          fontsize=8, fontweight="bold")
    else:
        ax_ghg.text(0.5, 0.5, "GHG map not found\nRun create_ghg_spatial_map.py",
                    ha="center", va="center", transform=ax_ghg.transAxes, fontsize=8)
        ax_ghg.axis("off")

    draw_lulc_map(ax_lulc, raster_paths.get("lulc"), raster_paths.get("lulc_thumb"),
                  title="ESRI LULC 2022")
    draw_nightlight_map(ax_nl, raster_paths.get("nightlights"), raster_paths.get("nl_thumb"),
                        title="VIIRS Nightlights 2022")

    # Overlay admin bboxes on LULC and NL panels
    for ax in (ax_lulc, ax_nl):
        add_bbox_patch(ax, OBLAST_BBOX, "Tashkent Oblast", "#FF6B6B", lw=2.0)
        add_bbox_patch(ax, CITY_BBOX,   "Tashkent City",   "#00E5FF", lw=2.5)
        ax.legend(loc="upper right", fontsize=5.5, framealpha=0.85)

    # Panel labels
    for ax, lbl in [(ax_ghg, "A"), (ax_lulc, "B"), (ax_nl, "C")]:
        ax.text(0.01, 0.97, lbl, transform=ax.transAxes,
                fontsize=12, fontweight="bold", va="top", color="#222")

    # ---- Row 1: Sector bar chart (left 3 cols) + adjustment factor heatmap (right 1 col) ----
    ax_bars = fig.add_subplot(gs[1, :3])
    ax_adj  = fig.add_subplot(gs[1, 3])
    draw_sector_bars(ax_bars, results)
    draw_adjustment_heatmap(ax_adj, results)
    ax_bars.text(0.002, 0.97, "D", transform=ax_bars.transAxes,
                 fontsize=12, fontweight="bold", va="top", color="#222")
    ax_adj.text(0.04, 0.97, "E", transform=ax_adj.transAxes,
                fontsize=12, fontweight="bold", va="top", color="#222")

    # ---- Row 2: Donut charts ----
    ax_donut_city   = fig.add_subplot(gs[2, :2])
    ax_donut_region = fig.add_subplot(gs[2, 2:])
    draw_lulc_donuts(ax_donut_city, ax_donut_region, results)
    ax_donut_city.text(0.02, 0.97, "F", transform=ax_donut_city.transAxes,
                       fontsize=12, fontweight="bold", va="top", color="#222")

    # ---- Row 3: Treemaps (one per unit) ----
    ax_tree_city   = fig.add_subplot(gs[3, :2])
    ax_tree_region = fig.add_subplot(gs[3, 2:])
    unit_map = {rec["region"]: rec for rec in results}
    if "Tashkent City" in unit_map:
        draw_emission_treemap(ax_tree_city, unit_map["Tashkent City"], "Tashkent City")
    if "Tashkent Region" in unit_map:
        draw_emission_treemap(ax_tree_region, unit_map["Tashkent Region"], "Tashkent Region")
    ax_tree_city.text(0.01, 0.95, "G", transform=ax_tree_city.transAxes,
                      fontsize=12, fontweight="bold", va="top", color="#222")

    # ---- Title block ----
    fig.suptitle(
        "GHG Emissions — Tashkent City & Tashkent Region (2022)\n"
        "Refined using ESRI 10m Land Cover & VIIRS Nightlights",
        fontsize=14, fontweight="bold", y=0.97, color="#1a1a2e",
    )

    # ---- Footnote ----
    footnote = (
        "Sources: BTR1 of Uzbekistan to UNFCCC (2024); ESRI Global LULC 10m Time Series; "
        "NOAA/VIIRS DNB Monthly Composites.\n"
        "Refinement: weighted blend of LULC fractions, VIIRS nightlight scores, and "
        "GDP/population-based priors. Scale: 100m (LULC), 500m (nightlights)."
    )
    fig.text(0.5, 0.005, footnote, ha="center", fontsize=6.5, color="#555",
             style="italic", wrap=True)

    out_path = out_dir / f"tashkent_ghg_emissions_map_{YEAR}.png"
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Map saved: {out_path}")
    return out_path


# -----------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------

def main():
    print("Initializing GEE...")
    if not gee_svc.initialize_gee():
        print("GEE init failed — raster layers will be skipped.")
        gee_ok = False
    else:
        gee_ok = True

    # Load refinement results
    if not RESULTS_JSON.exists():
        print(f"ERROR: {RESULTS_JSON} not found. Run refine_tashkent_emissions_gee.py first.")
        sys.exit(1)
    with open(RESULTS_JSON, encoding="utf-8") as fh:
        results = json.load(fh)
    print(f"Loaded results for {len(results)} unit(s).")

    raster_paths = {"lulc": None, "lulc_thumb": None,
                    "nightlights": None, "nl_thumb": None}

    if gee_ok:
        print("\nDownloading rasters from GEE...")
        raster_paths = fetch_rasters(OUT_DIR)
        for k, v in raster_paths.items():
            status = "OK" if v and Path(str(v)).exists() else "MISSING"
            print(f"  {k}: {status}")

    print("\nBuilding figure...")
    out = build_figure(results, raster_paths, OUT_DIR)
    print(f"\nDone. Output: {out}")


if __name__ == "__main__":
    main()
