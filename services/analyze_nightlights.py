"""Analyze existing nightlight images: statistics, histograms, trends, and area estimates.

This module reads images produced by the pipeline (GeoTIFF or PNG thumbnails) and
computes per-image statistics (mean, median, std), histograms, lit-area estimates
and temporal trends across years for each city. Results are saved under the
`suhi_analysis_output/nightlights_analysis/` folder.
"""
from pathlib import Path
import json
from typing import Dict, Any, List, Optional
import numpy as np
import math
import datetime

try:
    import rasterio
    from rasterio import Affine
    HAS_RASTERIO = True
except Exception:
    HAS_RASTERIO = False

from PIL import Image
import matplotlib.pyplot as plt

from .utils import create_output_directories, ANALYSIS_CONFIG


def find_image_for_city_year(base_dir: Path, city: str, year: int) -> Optional[Path]:
    """Look for GeoTIFF (preferred) or PNG thumbnail for a given city/year."""
    city_dir = base_dir / 'nightlights' / city
    if not city_dir.exists():
        return None
    # prefer GeoTIFFs
    candidates = [f"viirs_{year}.tif", f"viirs_{year}_coarse.tif", f"viirs_{year}.png", f"viirs_{year}.png"]
    for name in candidates:
        p = city_dir / name
        if p.exists():
            return p
    # fallback: any file with year in name
    for p in city_dir.glob(f"*{year}*.*"):
        return p
    return None


def _load_image_array(path: Path) -> Dict[str, Any]:
    """Load an image file to numpy array and return metadata.

    Returns dict with: array (2D float), pixel_area_m2 (if known or None), nodata
    """
    meta = {'path': str(path), 'pixel_area_m2': None, 'nodata': None}
    if path.suffix.lower() in ['.tif', '.tiff'] and HAS_RASTERIO:
        with rasterio.open(path) as src:
            arr = src.read(1).astype(float)
            transform = src.transform
            # approximate pixel area in m^2 when CRS is in meters
            try:
                # pixel width = transform.a, pixel height = -transform.e
                pix_w = abs(transform.a)
                pix_h = abs(transform.e)
                meta['pixel_area_m2'] = pix_w * pix_h
            except Exception:
                meta['pixel_area_m2'] = None
            meta['nodata'] = src.nodata
            return {'array': arr, 'meta': meta}
    else:
        # load with PIL, convert to grayscale float
        im = Image.open(path).convert('L')
        arr = np.asarray(im).astype(float)
        # if image is thumbnail, no georef; estimate pixel area from ANALYSIS_CONFIG target resolution
        default_scale = ANALYSIS_CONFIG.get('target_resolution_m', 500)
        meta['pixel_area_m2'] = float(default_scale) ** 2
        return {'array': arr, 'meta': meta}


def compute_image_statistics(arr: np.ndarray, meta: Dict[str, Any], lit_threshold: float = 1.0) -> Dict[str, Any]:
    """Compute basic statistics and lit-area estimates for a numpy array."""
    clean = np.array(arr, dtype=float)
    # mask nodata if provided
    if meta.get('nodata') is not None:
        clean = np.where(clean == meta['nodata'], np.nan, clean)
    flat = clean[~np.isnan(clean)]
    stats: Dict[str, Any] = {}
    if flat.size == 0:
        stats['error'] = 'no valid pixels'
        return stats
    stats['count'] = int(flat.size)
    stats['mean'] = float(np.mean(flat))
    stats['median'] = float(np.median(flat))
    stats['std'] = float(np.std(flat))
    stats['min'] = float(np.min(flat))
    stats['max'] = float(np.max(flat))
    # histogram
    hist, bin_edges = np.histogram(flat, bins=50)
    stats['histogram'] = {'counts': hist.tolist(), 'bins': bin_edges.tolist()}
    # lit area estimate: pixels greater than threshold
    lit_mask = flat > lit_threshold
    lit_pixels = int(np.sum(lit_mask))
    stats['lit_pixels'] = lit_pixels
    pixel_area_m2 = meta.get('pixel_area_m2')
    if pixel_area_m2:
        lit_area_km2 = lit_pixels * pixel_area_m2 / 1e6
        stats['lit_area_km2'] = float(lit_area_km2)
    else:
        stats['lit_area_km2'] = None
    stats['percent_lit'] = float(lit_pixels) / float(flat.size)
    return stats


def analyze_city_year(base_dir: Path, city: str, year: int, lit_threshold: float = 1.0) -> Dict[str, Any]:
    """Analyze available image for a city-year and produce stats and histogram plot."""
    out = {'city': city, 'year': year, 'timestamp': datetime.datetime.utcnow().isoformat()}
    img_path = find_image_for_city_year(base_dir, city, year)
    if not img_path:
        out['error'] = 'image not found'
        return out
    loaded = _load_image_array(img_path)
    arr = loaded['array']
    meta = loaded['meta']
    stats = compute_image_statistics(arr, meta, lit_threshold=lit_threshold)
    out['image_path'] = str(img_path)
    out['stats'] = stats
    # save histogram plot
    try:
        city_out = base_dir / 'nightlights_analysis' / city
        city_out.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(figsize=(6,4))
        hist = stats.get('histogram', {})
        if hist:
            counts = hist.get('counts', [])
            bins = hist.get('bins', [])
            ax.bar((np.array(bins[:-1]) + np.array(bins[1:]))/2, counts, width=np.diff(bins), align='center')
        ax.set_title(f"{city} {year} Radiance Histogram")
        ax.set_xlabel('Pixel value')
        ax.set_ylabel('Count')
        hist_file = city_out / f"{city}_{year}_histogram.png"
        fig.tight_layout()
        fig.savefig(str(hist_file), dpi=150)
        plt.close(fig)
        out['histogram_png'] = str(hist_file)
    except Exception as e:
        out['hist_error'] = str(e)
    return out


def analyze_cities_years(base_dir: Path, cities: List[str], years: List[int], lit_threshold: float = 1.0) -> List[Dict[str, Any]]:
    results = []
    for city in cities:
        for y in years:
            print(f"Analyzing {city} {y}...")
            res = analyze_city_year(base_dir, city, y, lit_threshold=lit_threshold)
            results.append(res)
    return results


def analyze_trends(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute simple linear trends of lit area per city from results list."""
    city_map: Dict[str, List] = {}
    for r in results:
        city = r.get('city')
        year = r.get('year')
        lit_area = None
        if r.get('stats'):
            lit_area = r['stats'].get('lit_area_km2')
        city_map.setdefault(city, []).append((year, lit_area))
    trends = {}
    for city, entries in city_map.items():
        # filter valid entries
        pts = sorted(entries, key=lambda x: x[0])
        years = [p[0] for p in pts if p[1] is not None]
        areas = [p[1] for p in pts if p[1] is not None]
        if len(years) >= 2:
            # linear fit
            try:
                coef = np.polyfit(years, areas, 1)
                slope = float(coef[0])
                intercept = float(coef[1])
                trends[city] = {'slope_km2_per_year': slope, 'intercept': intercept, 'n_years': len(years)}
            except Exception as e:
                trends[city] = {'error': str(e)}
        else:
            trends[city] = {'error': 'insufficient data'}
    return trends


def generate_summary_report(all_results: List[Dict[str, Any]], output_base: Path) -> Path:
    """Save aggregated JSON and markdown summary with trends and basic tables."""
    out_dir = output_base / 'nightlights_analysis'
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / 'nightlights_analysis_results.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2)

    trends = analyze_trends(all_results)
    md = out_dir / 'nightlights_analysis_summary.md'
    # Prepare per-city trend plots
    city_entries: Dict[str, List] = {}
    for r in all_results:
        city = str(r.get('city'))
        year = r.get('year')
        lit_area = None
        if r.get('stats'):
            lit_area = r['stats'].get('lit_area_km2')
        city_entries.setdefault(city, []).append((year, lit_area))

    # Create plots for each city
    for city, entries in city_entries.items():
        pts = sorted(entries, key=lambda x: x[0])
        years = [p[0] for p in pts if p[1] is not None]
        areas = [p[1] for p in pts if p[1] is not None]
        city_dir = out_dir / city
        city_dir.mkdir(parents=True, exist_ok=True)
        trend_png = city_dir / f"{city}_lit_area_trend.png"
        try:
            if len(years) >= 1:
                fig, ax = plt.subplots(figsize=(6,4))
                if years and areas:
                    ax.scatter(years, areas, color='#1f77b4')
                    if len(years) >= 2:
                        coef = np.polyfit(years, areas, 1)
                        p = np.poly1d(coef)
                        xs = np.array(years)
                        ax.plot(xs, p(xs), color='red', linestyle='--')
                ax.set_title(f"{city} - Lit Area Trend")
                ax.set_xlabel('Year')
                ax.set_ylabel('Lit area (km²)')
                fig.tight_layout()
                fig.savefig(str(trend_png), dpi=150)
                plt.close(fig)
            else:
                # create empty placeholder
                fig, ax = plt.subplots(figsize=(6,4))
                ax.text(0.5,0.5,'No data', ha='center', va='center')
                fig.savefig(str(trend_png), dpi=150)
                plt.close(fig)
        except Exception:
            # skip plotting errors
            if trend_png.exists():
                try:
                    trend_png.unlink()
                except Exception:
                    pass

    with open(md, 'w', encoding='utf-8') as f:
        f.write('# Nightlights Analysis Summary\n')
        f.write(f'Generated: {datetime.datetime.utcnow().isoformat()}\n\n')
        f.write('## Trends (lit area km² per year)\n')
        for city, t in trends.items():
            if 'error' in t:
                f.write(f'- {city}: {t["error"]}\n')
            else:
                f.write(f'- {city}: slope = {t["slope_km2_per_year"]:.4f} km²/year (n={t["n_years"]})\n')
        f.write('\n')
        f.write('## Per-city trend plots\n')
        for city in city_entries.keys():
            img_rel = f"{city}/{city}_lit_area_trend.png"
            f.write(f"### {city}\n\n")
            f.write(f"![]({img_rel})\n\n")
        f.write('\n')
        f.write('## Details\n')
        for r in all_results:
            f.write(f"- {r.get('city')} {r.get('year')}: ")
            if 'error' in r:
                f.write(f"ERROR: {r['error']}\n")
                continue
            stats = r.get('stats', {})
            f.write(f"mean={stats.get('mean')}, median={stats.get('median')}, lit_area_km2={stats.get('lit_area_km2')}\n")
    return md
