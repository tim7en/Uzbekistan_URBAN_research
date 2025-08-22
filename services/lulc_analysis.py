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
                # freq is an ee.Dictionary mapping band_name -> dict(class->count)
                # We'll compute entropy server-side using ee.List.iterate over the values
                try:
                    freq_dict_ee = ee.Dictionary(freq.get(band_name))
                    vals = ee.List(freq_dict_ee.values())
                    total = ee.Number(vals.iterate(lambda v, acc: ee.Number(acc).add(ee.Number(v)), ee.Number(0)))
                    # entropy = - sum(p * log(p)) in nats; convert to bits later
                    def _acc_entropy(v, acc):
                        vnum = ee.Number(v)
                        p = vnum.divide(total)
                        # guard against zero
                        term = ee.Algorithms.If(p.gt(0), p.multiply(p.log()), ee.Number(0))
                        return ee.Number(acc).add(ee.Number(term))
                    entropy_nats = ee.Number(vals.iterate(_acc_entropy, ee.Number(0))).multiply(-1)
                    entropy_bits = entropy_nats.divide(ee.Number(ee.Number(2).log()))
                    # get client-side histogram to preserve areas etc.
                    freq_dict = freq.get(band_name).getInfo() if freq and freq.getInfo() else {}
                except Exception:
                    # fallback to client-side retrieval
                    freq_dict = freq.get(band_name).getInfo() if freq and freq.getInfo() else {}
                    entropy_nats = None
                    entropy_bits = None

                # Convert counts to area (m2) and compute 95% Wilson CI for proportions
                areas = {}
                total_pixels = sum(freq_dict.values()) if freq_dict else 0
                total_area_m2 = float(total_pixels) * (download_scale ** 2) if total_pixels else 0.0
                import math
                z = 1.96  # 95% CI
                for class_id, px_count in freq_dict.items():
                    area_m2 = float(px_count) * (download_scale ** 2)
                    class_name = ESRI_CLASSES.get(int(class_id), f'Class_{class_id}')
                    pct = (px_count / total_pixels * 100) if total_pixels > 0 else None
                    ci_pct = None
                    ci_area = None
                    if total_pixels and total_pixels > 0:
                        n = total_pixels
                        k = px_count
                        p = float(k) / n
                        denom = 1 + (z*z)/n
                        center = (p + (z*z)/(2*n)) / denom
                        half = (z * math.sqrt((p*(1-p)/n) + (z*z)/(4*(n*n)))) / denom
                        lower = max(0.0, center - half)
                        upper = min(1.0, center + half)
                        ci_pct = [lower * 100.0, upper * 100.0]
                        ci_area = [lower * total_area_m2, upper * total_area_m2]
                    areas[class_name] = {'pixels': int(px_count), 'area_m2': area_m2, 'percentage': pct, 'ci_percentage': ci_pct, 'ci_area_m2': ci_area}
                hist = areas
                # attach entropy values (may be None if we fell back)
                if entropy_nats is not None:
                    hist.setdefault('_entropy', {})
                    hist['_entropy']['nats'] = float(entropy_nats.getInfo())
                    hist['_entropy']['bits'] = float(entropy_bits.getInfo())
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

