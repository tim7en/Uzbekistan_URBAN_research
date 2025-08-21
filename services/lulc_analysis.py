"""Simplified LULC analysis focused on ESRI landcover maps only.

This module reads available ESRI landcover GeoTIFFs under the local
output directories and produces a compact JSON summary that lists the
ESRI map file used per year, area per class (m2), and the built-up
area (ESRI class 7) per year. Visuals and cross-dataset comparisons
were intentionally removed to keep the output minimal.
"""

"""ESRI-focused LULC analysis that performs Earth Engine-side extraction
and downloads georeferenced GeoTIFFs for the ESRI landcover map and a
built-up mask (class 7). Results (histograms and built-up areas) are
saved as JSON per city.
"""

import json
from pathlib import Path
from typing import Dict, Any, List

import ee

from . import classification, lulc
from .utils import UZBEKISTAN_CITIES, ESRI_CLASSES


def run_city_lulc_analyze_esri_only(base: Path, city: str, start_year: int, end_year: int, download_scale: int = 30) -> Dict[str, Any]:
    """For a city, pull ESRI landcover images from Earth Engine per year,
    compute frequency histograms on the server, download georeferenced
    GeoTIFFs for the full map and the built-up mask, and save a compact JSON
    summary under `suhi_analysis_output/lulc_analysis/<city>/`.

    Args:
      base: Path to repository output base (from `create_output_directories`).
      city: city name in `UZBEKISTAN_CITIES`.
      start_year, end_year: inclusive year range.
      download_scale: output GeoTIFF scale in meters (default 30).
    """
    years: List[int] = list(range(start_year, end_year + 1))
    out_dir = base / 'lulc_analysis' / city
    out_dir.mkdir(parents=True, exist_ok=True)
    tiff_dir = base / 'lulc_highres' / city
    tiff_dir.mkdir(parents=True, exist_ok=True)

    city_info = UZBEKISTAN_CITIES[city]
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    region = center.buffer(city_info['buffer_m']).bounds()

    summary: Dict[str, Any] = {'city': city, 'years': years, 'esri_maps': {}, 'areas_m2': {}, 'built_up_area_m2': {}}

    for year in years:
        try:
            esri_image = classification.load_esri_classification(year, region)
            if esri_image is None:
                summary['esri_maps'][str(year)] = None
                summary['areas_m2'][str(year)] = {}
                summary['built_up_area_m2'][str(year)] = 0.0
                continue

            # Determine band name
            band_names = esri_image.bandNames().getInfo()
            band_name = band_names[0] if band_names else 'b1'

            # Compute histogram on Earth Engine side (frequencyHistogram)
            hist = {}
            try:
                freq = esri_image.select(band_name).reduceRegion(
                    reducer=ee.Reducer.frequencyHistogram(), geometry=region, scale=download_scale, maxPixels=1e10, bestEffort=True)
                freq_dict = freq.get(band_name).getInfo() if freq and freq.getInfo() else {}
                # Convert counts to area (m2)
                areas = {}
                total_pixels = sum(freq_dict.values()) if freq_dict else 0
                for class_id, px_count in freq_dict.items():
                    area_m2 = float(px_count) * (download_scale ** 2)
                    class_name = ESRI_CLASSES.get(int(class_id), f'Class_{class_id}')
                    areas[class_name] = {'pixels': int(px_count), 'area_m2': area_m2, 'percentage': (px_count / total_pixels * 100) if total_pixels > 0 else None}
                hist = areas
            except Exception as e:
                hist = {'error': str(e)}

            summary['esri_maps'][str(year)] = None
            summary['areas_m2'][str(year)] = hist
            # Built-up area (class 7)
            built_area = 0.0
            if isinstance(hist, dict) and 'Class_7' in hist:
                built_area = hist['Class_7']['area_m2']
            else:
                # try to fetch class 7 by id lookup
                for k, v in hist.items():
                    if k == 'Built_Area' or k == ESRI_CLASSES.get(7):
                        built_area = v.get('area_m2', 0.0)
            summary['built_up_area_m2'][str(year)] = float(built_area)

            # Download GeoTIFFs: full ESRI map and built-up mask
            try:
                # Ensure we request a simple single-band categorical image for download
                full_img = esri_image.select([band_name]).rename('esri_full')
                fname_full = f"esri_full_{year}_highres"
                p_full = lulc._download_image_geturl(full_img, region, download_scale, tiff_dir, fname_full)
                if p_full:
                    summary['esri_maps'][str(year)] = str(p_full)
            except Exception:
                pass

            try:
                built_img = esri_image.select([band_name]).eq(7).rename('esri_built')
                fname_built = f"esri_built_{year}_highres"
                p_built = lulc._download_image_geturl(built_img, region, download_scale, tiff_dir, fname_built)
                if p_built:
                    # Record built path separately
                    summary.setdefault('esri_built_maps', {})[str(year)] = str(p_built)
            except Exception:
                pass

        except Exception as e:
            summary['esri_maps'][str(year)] = None
            summary['areas_m2'][str(year)] = {'error': str(e)}
            summary['built_up_area_m2'][str(year)] = 0.0

    out_file = out_dir / f"{city}_lulc_analysis_{years[0]}_{years[-1]}.json"
    with open(out_file, 'w', encoding='utf-8') as fh:
        json.dump(summary, fh, indent=2)

    return summary


def run_city_lulc_analysis(base: Path, city: str, start_year: int, end_year: int) -> Dict[str, Any]:
    return run_city_lulc_analyze_esri_only(base, city, start_year, end_year)

