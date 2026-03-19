"""Create a spatial GHG emission intensity map for Tashkent City + Tashkent Region.

Method
------
1. Load the already-downloaded LULC (200m) and nightlight (500m) GeoTIFFs.
2. Resample nightlights to match the LULC grid.
3. For each pixel compute a sector-weighted emission proxy:
      urban proxy  = (LULC == Built_Area)  * normalised_nightlight
      agri proxy   = (LULC == Crops | Flooded_Veg)
      ippu proxy   = (LULC == Built_Area | Bare_Ground) * normalised_nightlight
      lulucf proxy = (LULC == Trees) * -1  +  (LULC == Rangeland) * -0.05
4. For each admin unit (City / Oblast), the per-pixel intensity is:
      I(x,y) = Σ_sector  refined_sector_Mt * sector_proxy(x,y) / Σ(sector_proxy in unit)
   converted to tonnes CO2-eq / km².
5. Combine both unit layers and plot as a publication-quality map with:
      - Emission intensity heatmap (primary map, full page)
      - Sector contribution inset bar charts
      - LULC legend inset
      - Nightlight overlay contours
"""
import sys, json
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from scipy.ndimage import zoom

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUT_DIR   = ROOT / "suhi_analysis_output" / "emissions_refinement"
JSON_PATH = OUT_DIR / "tashkent_refined_emissions_2022.json"
LULC_TIF  = OUT_DIR / "lulc_tashkent_200m.tif"
NL_TIF    = OUT_DIR / "nightlights_tashkent_500m.tif"

# ---------------------------------------------------------------------------
# ESRI class IDs
# ---------------------------------------------------------------------------
BUILT      = 7
CROPS      = 5
FLOODED    = 4
TREES      = 2
RANGELAND  = 11
BARE       = 8
WATER      = 1

# Approximate bbox of each admin unit within the raster extent
# [west, east, south, north]  (lon/lat, WGS84)
CITY_BBOX   = (69.14, 69.40, 41.18, 41.43)   # (west, east, south, north)
OBLAST_BBOX = (68.70, 71.50, 40.50, 42.00)   # full raster extent = Oblast

# ---------------------------------------------------------------------------
# GHG emission colormap (white → yellow → orange → dark red → purple)
# ---------------------------------------------------------------------------
GHG_COLORS = [
    "#F7FBFF",   # ~0   – background / minimal
    "#DEEBF7",
    "#C6DBEF",
    "#9ECAE1",
    "#6BAED6",
    "#4292C6",   # ~100 t/km²
    "#2171B5",
    "#FED976",   # transition through yellow
    "#FEB24C",
    "#FD8D3C",
    "#FC4E2A",   # ~1000 t/km²
    "#E31A1C",
    "#BD0026",
    "#800026",   # high urban
    "#4D004B",   # very high
    "#1A0033",   # extreme urban core
]
GHG_CMAP = LinearSegmentedColormap.from_list("ghg", GHG_COLORS, N=512)

# LULC colours for legend / contour context
ESRI_PALETTE = {
    "Water": "#419BDF", "Trees": "#397D49", "Flooded_Vegetation": "#7A87C6",
    "Crops": "#E49635", "Built_Area": "#C4281B", "Bare_Ground": "#A59B8F",
    "Snow_Ice": "#B39FE1", "Rangeland": "#DFC35A",
}

SECTOR_COLORS = {
    "electricity_heat":       "#E63946",
    "residential_commercial": "#457B9D",
    "industry_combustion":    "#F4A261",
    "transport":              "#2A9D8F",
    "fugitive_emissions":     "#E9C46A",
    "ippu":                   "#264653",
    "agriculture":            "#A8DADC",
    "waste":                  "#F1FAEE",
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


# ---------------------------------------------------------------------------
# Raster I/O
# ---------------------------------------------------------------------------

def load_raster(path: Path):
    """Return (data_2d_masked, transform, crs, bounds)."""
    import rasterio
    with rasterio.open(path) as src:
        data = src.read(1, masked=True)
        transform = src.transform
        crs = src.crs
        bounds = src.bounds
    return data, transform, crs, bounds


def resample_to_match(source: np.ma.MaskedArray, source_bounds, source_shape,
                      target_shape) -> np.ma.MaskedArray:
    """Bilinear zoom of source array to match target shape."""
    zoom_y = target_shape[0] / source_shape[0]
    zoom_x = target_shape[1] / source_shape[1]
    data = source.filled(0.0).astype(float)
    zoomed = zoom(data, (zoom_y, zoom_x), order=1)
    # Handle case where mask is a scalar False (no masked values)
    src_mask = source.mask
    if np.isscalar(src_mask) or (hasattr(src_mask, "shape") and src_mask.shape == ()):
        mask_zoomed = np.zeros(target_shape, dtype=bool)
    else:
        mask_zoomed = zoom(src_mask.astype(float), (zoom_y, zoom_x), order=0) > 0.5
    return np.ma.array(zoomed, mask=mask_zoomed)


def bbox_mask(transform, shape, bbox_wesnw):
    """Return boolean mask (rows, cols) True where pixel centre is inside bbox."""
    west, east, south, north = bbox_wesnw
    rows, cols = shape
    import rasterio.transform as rt
    # pixel centres
    col_indices = np.arange(cols)
    row_indices = np.arange(rows)
    xs = transform.c + (col_indices + 0.5) * transform.a   # lon
    ys = transform.f + (row_indices + 0.5) * transform.e   # lat (e < 0)
    lon_mask = (xs >= west) & (xs <= east)                  # shape (cols,)
    lat_mask = (ys >= south) & (ys <= north)                # shape (rows,)
    mask2d = lat_mask[:, None] & lon_mask[None, :]          # broadcast (rows, cols)
    return mask2d


# ---------------------------------------------------------------------------
# Emission proxy computation
# ---------------------------------------------------------------------------

SECTOR_PROXIES_SPATIAL = {
    # sector : {lulc_id: weight, "__nl": nightlight_weight}
    # weights sum to 1.0; "__nl" multiplies the LULC mask by NL intensity
    "electricity_heat":       {BUILT: 0.4, "__nl": 0.6},
    "residential_commercial": {BUILT: 0.7, "__nl": 0.3},
    "industry_combustion":    {BUILT: 0.2, BARE: 0.1, "__nl": 0.7},
    "transport":              {BUILT: 0.5, "__nl": 0.5},
    "fugitive_emissions":     {"__uniform": 1.0},             # no good proxy → uniform
    "ippu":                   {BUILT: 0.1, BARE: 0.2, "__nl": 0.7},
    "agriculture":            {CROPS: 0.7, FLOODED: 0.3},
    "waste":                  {BUILT: 0.8, "__nl": 0.2},
}

# LULUCF is a sink — handled separately
LULUCF_PROXIES = {
    TREES:     -1.0,
    RANGELAND: -0.05,
}


def build_sector_proxy(lulc: np.ndarray, nl_norm: np.ndarray,
                       proxy_def: dict, unit_mask: np.ndarray) -> np.ndarray:
    """Compute un-normalised spatial proxy for one sector within the unit mask."""
    proxy = np.zeros_like(lulc, dtype=float)
    nl_weight = proxy_def.get("__nl", 0.0)
    uniform   = proxy_def.get("__uniform", 0.0)

    for key, w in proxy_def.items():
        if key == "__nl" or key == "__uniform":
            continue
        lulc_id = key  # integer class id
        proxy += w * (lulc == lulc_id).astype(float)

    if nl_weight > 0:
        # Add NL-weighted built area
        proxy += nl_weight * (lulc == BUILT).astype(float) * nl_norm

    if uniform > 0:
        proxy += uniform * unit_mask.astype(float)

    proxy = proxy * unit_mask.astype(float)  # zero outside unit
    return proxy


def compute_emission_intensity(
    lulc: np.ma.MaskedArray,
    nl_norm: np.ndarray,
    unit_mask: np.ndarray,
    refined_Mt: dict,
    pixel_area_km2: float,
) -> np.ndarray:
    """
    Return emission intensity (t CO2-eq / km2) array for the unit.
    refined_Mt: dict of sector -> Mt CO2-eq (positive = emission, negative = sink).
    """
    total_intensity = np.zeros(lulc.shape, dtype=float)
    lulc_data = lulc.filled(0).astype(int)

    for sector, proxy_def in SECTOR_PROXIES_SPATIAL.items():
        sector_Mt = refined_Mt.get(sector, 0.0)
        if sector_Mt is None or sector_Mt == 0:
            continue

        raw_proxy = build_sector_proxy(lulc_data, nl_norm, proxy_def, unit_mask)
        proxy_sum = raw_proxy[unit_mask].sum()
        if proxy_sum == 0:
            # fallback: distribute uniformly over unit
            norm_proxy = unit_mask.astype(float) / unit_mask.sum()
        else:
            norm_proxy = raw_proxy / proxy_sum  # sums to 1 over unit

        # Convert Mt → t, allocate per pixel, then per km²
        sector_t_per_km2 = norm_proxy * sector_Mt * 1e6 / pixel_area_km2
        total_intensity += sector_t_per_km2

    # LULUCF sink
    lulucf_Mt = refined_Mt.get("lulucf", 0.0) or 0.0
    lulucf_proxy = np.zeros(lulc.shape, dtype=float)
    for cls_id, weight in LULUCF_PROXIES.items():
        lulucf_proxy += weight * (lulc_data == cls_id).astype(float)
    lulucf_proxy = lulucf_proxy * unit_mask.astype(float)
    proxy_sum = np.abs(lulucf_proxy[unit_mask]).sum()
    if proxy_sum > 0 and lulucf_Mt != 0:
        norm_lulucf = lulucf_proxy / proxy_sum
        total_intensity += norm_lulucf * lulucf_Mt * 1e6 / pixel_area_km2

    return total_intensity  # t CO2-eq / km2


# ---------------------------------------------------------------------------
# Map plotting
# ---------------------------------------------------------------------------

def extent_from_transform(transform, shape):
    """[west, east, south, north] for imshow extent."""
    west  = transform.c
    east  = transform.c + shape[1] * transform.a
    north = transform.f
    south = transform.f + shape[0] * transform.e
    return [west, east, south, north]


def add_sector_inset(fig, ax_main, rec: dict, loc_bbox, title: str):
    """Horizontal stacked bar of refined sector emissions as an inset."""
    axins = inset_axes(ax_main, width="100%", height="100%",
                       bbox_to_anchor=loc_bbox, bbox_transform=fig.transFigure)
    sectors = [s for s in SECTOR_LABELS if s != "lulucf"]
    vals = [max(rec["refined_emissions_Mt"].get(s) or 0, 0) for s in sectors]
    total = sum(vals) or 1
    fracs = [v / total for v in vals]
    colors = [SECTOR_COLORS[s] for s in sectors]

    left = 0
    for frac, color, sector, val in zip(fracs, colors, sectors, vals):
        axins.barh(0, frac, left=left, color=color, height=0.6,
                   edgecolor="white", linewidth=0.7)
        if frac > 0.07:
            axins.text(left + frac / 2, 0,
                       f"{SECTOR_LABELS[sector]}\n{val:.2f} Mt",
                       ha="center", va="center", fontsize=4.8,
                       fontweight="bold",
                       color="white" if frac > 0.10 else "#222")
        left += frac

    axins.set_xlim(0, 1)
    axins.set_ylim(-0.5, 0.5)
    axins.axis("off")
    axins.set_title(title, fontsize=7, fontweight="bold", pad=2)

    # Mini legend
    patches = [mpatches.Patch(color=SECTOR_COLORS[s],
                              label=f"{SECTOR_LABELS[s]} ({vals[i]:.2f} Mt)")
               for i, s in enumerate(sectors)]
    axins.legend(handles=patches, loc="lower center",
                 bbox_to_anchor=(0.5, -1.05), fontsize=4.5,
                 ncol=4, framealpha=0.8, edgecolor="#aaa")


def plot_ghg_map(emission_array: np.ndarray, lulc: np.ma.MaskedArray,
                 nl: np.ma.MaskedArray, transform, results: list,
                 out_path: Path):

    extent = extent_from_transform(transform, emission_array.shape)

    # --- Use log10 scale for display (wide dynamic range city vs oblast)
    pos_vals = emission_array[emission_array > 0]
    log_min = np.log10(max(float(np.percentile(pos_vals, 2)), 1.0)) if pos_vals.size > 0 else 0.0
    log_max = np.log10(float(np.percentile(pos_vals, 99.5))) if pos_vals.size > 0 else 4.0
    vmin = log_min
    vmax = log_max

    fig = plt.figure(figsize=(18, 22))
    fig.patch.set_facecolor("#0E1117")

    # Main map axis
    ax = fig.add_axes([0.05, 0.22, 0.90, 0.68])

    # ---- Background: faint LULC classification ----
    lulc_rgba = np.zeros((*lulc.shape, 4), dtype=float)
    lulc_palette_id = {
        1: mcolors.to_rgba("#419BDF", 0.18),
        2: mcolors.to_rgba("#397D49", 0.20),
        4: mcolors.to_rgba("#7A87C6", 0.20),
        5: mcolors.to_rgba("#E49635", 0.15),
        7: mcolors.to_rgba("#C4281B", 0.10),
        8: mcolors.to_rgba("#A59B8F", 0.12),
        9: mcolors.to_rgba("#B39FE1", 0.20),
        11: mcolors.to_rgba("#DFC35A", 0.12),
    }
    lulc_data = lulc.filled(0).astype(int)
    for cls_id, rgba in lulc_palette_id.items():
        mask = lulc_data == cls_id
        for c in range(4):
            lulc_rgba[mask, c] = rgba[c]
    ax.imshow(lulc_rgba, extent=extent, origin="upper", aspect="auto",
              interpolation="nearest")

    # ---- Primary layer: GHG emission intensity (log10 scale) ----
    em_log = np.where(emission_array > 0, np.log10(np.maximum(emission_array, 1e-3)), np.nan)
    img = ax.imshow(em_log, extent=extent, origin="upper",
                    cmap=GHG_CMAP, vmin=vmin, vmax=vmax,
                    interpolation="bilinear", aspect="auto", alpha=0.93)

    # ---- Nightlight contours (context) ----
    nl_filled = nl.filled(0)
    nl_smooth = nl_filled
    try:
        from scipy.ndimage import gaussian_filter
        nl_smooth = gaussian_filter(nl_filled.astype(float), sigma=2)
    except Exception:
        pass
    rows, cols = nl_smooth.shape
    x_nl = np.linspace(extent[0], extent[1], cols)
    y_nl = np.linspace(extent[3], extent[2], rows)   # north→south
    X_nl, Y_nl = np.meshgrid(x_nl, y_nl)
    nl_levels = [1, 3, 8, 20, 40]
    try:
        cs = ax.contour(X_nl, Y_nl, nl_smooth, levels=nl_levels,
                        colors="white", linewidths=0.4, alpha=0.35, zorder=3)
        ax.clabel(cs, fmt="%g nW", fontsize=5, colors="white")
    except Exception:
        pass

    # ---- Admin boundary boxes ----
    from matplotlib.patches import Rectangle
    city_rect = Rectangle(
        (69.14, 41.18), 69.40 - 69.14, 41.43 - 41.18,
        linewidth=2.5, edgecolor="#00E5FF", facecolor="none",
        label="Tashkent City", zorder=6, linestyle="-"
    )
    oblast_rect = Rectangle(
        (68.70, 40.50), 71.50 - 68.70, 42.00 - 40.50,
        linewidth=1.8, edgecolor="#FF6B6B", facecolor="none",
        label="Tashkent Oblast", zorder=5, linestyle="--"
    )
    ax.add_patch(city_rect)
    ax.add_patch(oblast_rect)

    # ---- Colorbar ----
    cbar_ax = fig.add_axes([0.05, 0.185, 0.90, 0.018])
    cb = fig.colorbar(img, cax=cbar_ax, orientation="horizontal",
                      extend="max")
    cb.set_label("GHG Emission Intensity  (log\u2081\u2080 t CO\u2082-eq / km\u00b2)",
                 fontsize=9, color="white", labelpad=4)
    # Replace log ticks with actual values
    tick_vals = [1, 10, 50, 100, 500, 1000, 5000, 10000, 20000]
    tick_logs = [np.log10(v) for v in tick_vals if log_min <= np.log10(v) <= log_max]
    tick_lbls = [str(v) for v in tick_vals if log_min <= np.log10(v) <= log_max]
    cb.set_ticks(tick_logs)
    cb.set_ticklabels(tick_lbls)
    cb.ax.tick_params(labelsize=7.5, colors="white")
    cb.outline.set_edgecolor("white")
    for t in cb.ax.get_xticklabels():
        t.set_color("white")

    # ---- Annotations: unit labels + totals ----
    units = {rec["region"]: rec for rec in results}
    if "Tashkent City" in units:
        rec = units["Tashkent City"]
        refined_total = sum(
            v for k, v in rec["refined_emissions_Mt"].items()
            if k != "lulucf" and v is not None
        )
        ax.text(69.27, 41.45,
                f"Tashkent City\nRefined: {refined_total:.1f} Mt CO2-eq",
                fontsize=7.5, color="#00E5FF", fontweight="bold",
                ha="center", va="bottom", zorder=10,
                bbox=dict(boxstyle="round,pad=0.3", fc="#0E1117", ec="#00E5FF", alpha=0.75))

    if "Tashkent Region" in units:
        rec = units["Tashkent Region"]
        refined_total = sum(
            v for k, v in rec["refined_emissions_Mt"].items()
            if k != "lulucf" and v is not None
        )
        ax.text(70.80, 41.70,
                f"Tashkent Oblast\nRefined: {refined_total:.1f} Mt CO2-eq",
                fontsize=7.5, color="#FF6B6B", fontweight="bold",
                ha="center", va="top", zorder=10,
                bbox=dict(boxstyle="round,pad=0.3", fc="#0E1117", ec="#FF6B6B", alpha=0.75))

    # ---- Axes styling ----
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_xlabel("Longitude", fontsize=9, color="white")
    ax.set_ylabel("Latitude",  fontsize=9, color="white")
    ax.tick_params(labelsize=7.5, colors="white")
    ax.spines[:].set_edgecolor("#555")
    ax.set_facecolor("#0E1117")

    legend_handles = [
        city_rect,
        oblast_rect,
        mpatches.Patch(color="none", label="— NL contours (nW/cm\u00b2/sr)",
                       linewidth=0),
    ]
    ax.legend(handles=legend_handles, loc="lower left",
              fontsize=7, framealpha=0.7, facecolor="#0E1117",
              labelcolor="white", edgecolor="#555")

    # ---- Title ----
    fig.text(0.5, 0.95,
             "GHG Emission Intensity — Tashkent City & Tashkent Oblast (2022)",
             ha="center", fontsize=14, fontweight="bold", color="white")
    fig.text(0.5, 0.925,
             "Spatially disaggregated using ESRI 10m LULC & VIIRS Nightlights  |  "
             "Refined from BTR1 Uzbekistan proxy estimates",
             ha="center", fontsize=8.5, color="#AAAAAA")

    # ---- Sector breakdown insets (below colorbar) ----
    if "Tashkent City" in units:
        add_sector_inset(fig, ax, units["Tashkent City"],
                         [0.05, 0.06, 0.42, 0.09],
                         "Tashkent City — Refined Sector Emissions")
    if "Tashkent Region" in units:
        add_sector_inset(fig, ax, units["Tashkent Region"],
                         [0.53, 0.06, 0.42, 0.09],
                         "Tashkent Oblast — Refined Sector Emissions")

    # ---- LULC legend (top-right inset) ----
    lulc_patches = [mpatches.Patch(color=col, label=name, alpha=0.85)
                    for name, col in ESRI_PALETTE.items()]
    lulc_legend = ax.legend(handles=lulc_patches, title="ESRI LULC",
                             loc="upper right", fontsize=6,
                             title_fontsize=6.5, framealpha=0.7,
                             facecolor="#0E1117", labelcolor="white",
                             edgecolor="#555")
    ax.add_artist(lulc_legend)
    # Re-add the admin legend
    admin_legend = ax.legend(handles=[city_rect, oblast_rect],
                              loc="lower left", fontsize=7,
                              framealpha=0.7, facecolor="#0E1117",
                              labelcolor="white", edgecolor="#555")

    # ---- Footnote ----
    fig.text(0.5, 0.008,
             "Emission proxy: Built_Area + NL-weighted intensity (urban sectors), "
             "Cropland (agriculture), Trees/Rangeland (LULUCF sink). "
             "Totals normalised to refined estimates per unit. "
             "Sources: ESRI LULC 10m TS; NOAA/VIIRS DNB; BTR1 UZB 2024.",
             ha="center", fontsize=6, color="#888", style="italic")

    fig.savefig(out_path, dpi=200, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Load results
    with open(JSON_PATH, encoding="utf-8") as fh:
        results = json.load(fh)
    unit_map = {rec["region"]: rec for rec in results}
    print("Loaded refined emission data for:", list(unit_map.keys()))

    # Load rasters
    print("Loading LULC raster...")
    lulc, lulc_transform, lulc_crs, lulc_bounds = load_raster(LULC_TIF)
    print(f"  LULC shape: {lulc.shape}, pixel size: {abs(lulc_transform.a)*111:.0f}m")

    print("Loading nightlights raster...")
    nl, nl_transform, nl_crs, nl_bounds = load_raster(NL_TIF)
    print(f"  NL shape: {nl.shape}")

    # Resample NL to LULC grid
    print("Resampling nightlights to LULC resolution...")
    nl_resampled = resample_to_match(nl, nl_bounds, nl.shape, lulc.shape)
    print(f"  Resampled NL shape: {nl_resampled.shape}")

    # Pixel area (at ~200m, in km²)
    pixel_deg = abs(lulc_transform.a)  # degrees per pixel
    pixel_km  = pixel_deg * 111.0      # approx km per pixel (latitude-average)
    pixel_area_km2 = pixel_km ** 2
    print(f"  Pixel area: {pixel_area_km2:.4f} km2")

    # Normalise NL globally (0–1) for use as activity proxy
    nl_data = nl_resampled.filled(0).astype(float)
    nl_max  = np.percentile(nl_data[nl_data > 0], 98) if (nl_data > 0).any() else 1.0
    nl_norm = np.clip(nl_data / nl_max, 0, 1)
    print(f"  NL normalisation max (98th pct): {nl_max:.3f}")

    # Build masks (hard boundaries only used for per-unit total calibration)
    print("Building admin unit masks...")
    city_mask   = bbox_mask(lulc_transform, lulc.shape, CITY_BBOX)
    full_mask   = (~lulc.mask) if (hasattr(lulc, "mask") and lulc.mask.ndim > 0) \
                  else np.ones(lulc.shape, bool)
    oblast_mask = full_mask & ~city_mask
    print(f"  City pixels: {city_mask.sum():,}")
    print(f"  Oblast pixels: {oblast_mask.sum():,}")

    # -----------------------------------------------------------------------
    # Step 1: Build a SINGLE raw emission proxy for every pixel (no hard mask)
    # -----------------------------------------------------------------------
    print("\nBuilding continuous emission proxy field...")
    lulc_data = lulc.filled(0).astype(int)

    # Combine sector totals from both units into one proxy
    # weighted by the spatial blending weights (computed below)
    # For now compute per-unit raw proxies and blend smoothly

    def raw_proxy_for(refined_Mt, mask):
        """Un-normalised proxy for a single unit, applied to all pixels."""
        total = np.zeros(lulc.shape, dtype=float)
        for sector, proxy_def in SECTOR_PROXIES_SPATIAL.items():
            mt = refined_Mt.get(sector, 0.0) or 0.0
            if mt == 0:
                continue
            p = build_sector_proxy(lulc_data, nl_norm, proxy_def, mask)
            s = p[mask].sum()
            if s > 0:
                total += (p / s) * mt * 1e6 / pixel_area_km2
        # LULUCF sink
        lulucf_mt = refined_Mt.get("lulucf", 0.0) or 0.0
        if lulucf_mt != 0:
            lp = np.zeros(lulc.shape, dtype=float)
            for cls_id, w in LULUCF_PROXIES.items():
                lp += w * (lulc_data == cls_id).astype(float) * mask.astype(float)
            s = np.abs(lp[mask]).sum()
            if s > 0:
                total += (lp / s) * lulucf_mt * 1e6 / pixel_area_km2
        return total

    city_refined  = unit_map["Tashkent City"]["refined_emissions_Mt"]
    oblast_refined = unit_map["Tashkent Region"]["refined_emissions_Mt"]

    # Compute per-unit intensities over the FULL raster (no mask clipping)
    # so the field is continuous right up to and across the boundary
    print("  Computing city intensity field...")
    city_intensity   = raw_proxy_for(city_refined,   np.ones(lulc.shape, bool))
    print("  Computing oblast intensity field...")
    oblast_intensity = raw_proxy_for(oblast_refined, np.ones(lulc.shape, bool))

    # -----------------------------------------------------------------------
    # Step 2: Smooth spatial blend — sigmoid in distance from city centroid
    # -----------------------------------------------------------------------
    print("  Blending with distance-decay weights...")

    # City centroid and approximate radius in pixels
    city_cx_lon = (CITY_BBOX[0] + CITY_BBOX[1]) / 2  # 69.27
    city_cy_lat = (CITY_BBOX[2] + CITY_BBOX[3]) / 2  # 41.305
    city_r_lon  = (CITY_BBOX[1] - CITY_BBOX[0]) / 2  # half-width in degrees
    city_r_lat  = (CITY_BBOX[3] - CITY_BBOX[2]) / 2  # half-height in degrees

    # Per-pixel lon/lat grids
    rows, cols = lulc.shape
    col_idx = np.arange(cols)
    row_idx = np.arange(rows)
    lons = lulc_transform.c + (col_idx + 0.5) * lulc_transform.a   # (cols,)
    lats = lulc_transform.f + (row_idx + 0.5) * lulc_transform.e   # (rows,)
    LON, LAT = np.meshgrid(lons, lats)                              # (rows, cols)

    # Normalised elliptical distance from city centre (1 = at city boundary)
    dist_ellipse = np.sqrt(
        ((LON - city_cx_lon) / city_r_lon) ** 2 +
        ((LAT - city_cy_lat) / city_r_lat) ** 2
    )

    # Sigmoid: w→1 deep inside city, w→0 well outside; transition zone ±0.5 radii
    # sharpness k controls transition width (higher k = sharper; use ~4 for ~0.5 radius blend)
    k = 4.0
    city_weight = 1.0 / (1.0 + np.exp(k * (dist_ellipse - 1.0)))  # 1 inside, 0 outside

    # Blended intensity
    emission_grid = city_weight * city_intensity + (1.0 - city_weight) * oblast_intensity

    # -----------------------------------------------------------------------
    # Step 3: Gaussian smoothing to erase any remaining hard edges
    # -----------------------------------------------------------------------
    print("  Applying spatial smoothing...")
    try:
        from scipy.ndimage import gaussian_filter
        # sigma ~4 pixels ≈ 800 m blur radius — enough to dissolve bbox artefacts
        emission_grid = gaussian_filter(emission_grid, sigma=4)
    except Exception as e:
        print(f"    Smoothing skipped: {e}")

    pos = emission_grid[full_mask & (emission_grid > 0)]
    if pos.size > 0:
        print(f"  Combined range: {pos.min():.1f} – {pos.max():.1f} t CO2-eq/km2")
        print(f"  Mean (non-zero): {pos.mean():.1f} t CO2-eq/km2")

    # Plot
    print("\nRendering GHG emissions map...")
    out_path = OUT_DIR / "tashkent_ghg_emission_intensity_2022.png"
    plot_ghg_map(emission_grid, lulc, nl_resampled, lulc_transform,
                 results, out_path)
    print("\nDone.")


if __name__ == "__main__":
    main()
