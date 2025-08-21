"""Auxiliary data extraction service.

Produces seasonal Landsat-based NDVI and EVI composites and Landsat thermal
LST composites for specified cities and years. Downloads GeoTIFFs per
indicator and writes a JSON summary per city/year with statistics and
paths to generated rasters.

This module reuses existing helpers in the repo (utils, lulc, temperature)
so it follows established output locations and conventions.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import ee

from . import lulc
from . import error_assessment
from .utils import UZBEKISTAN_CITIES, create_output_directories, ANALYSIS_CONFIG
from .temperature import load_landsat_thermal


def _format_date_range_for_months(year: int, months: List[int]) -> Tuple[str, str]:
    # Compute valid start and end dates for the supplied months.
    # End date uses the actual last day of the month to avoid invalid dates (e.g. Feb 31).
    from calendar import monthrange
    months_sorted = sorted(months)
    start_month = months_sorted[0]
    end_month = months_sorted[-1]
    start = f"{year:04d}-{start_month:02d}-01"
    last_day = monthrange(year, end_month)[1]
    end = f"{year:04d}-{end_month:02d}-{last_day:02d}"
    return start, end


def _compute_seasonal_ndvi_evi(start_date: str, end_date: str, geometry: ee.Geometry, cloud_threshold: int = 20) -> ee.Image:
    """Builds a median composite over Landsat 8/9 SR, returning NDVI and EVI bands.

    Bands expected in the collection: SR_B2 (blue), SR_B4 (red), SR_B5 (nir).
    """
    from .utils import DATASETS

    def proc(img):
        qa = img.select('QA_PIXEL')
        mask = (qa.bitwiseAnd(1<<3).eq(0).And(qa.bitwiseAnd(1<<4).eq(0)))
        optical = img.select(['SR_B2','SR_B4','SR_B5']).multiply(0.0000275).add(-0.2).clamp(0,1)
        blue = optical.select('SR_B2')
        red = optical.select('SR_B4')
        nir = optical.select('SR_B5')
        ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
        # EVI formula tuned for Landsat SR
        evi = nir.subtract(red).multiply(2.5).divide(nir.add(red.multiply(6)).subtract(blue.multiply(7.5)).add(1)).rename('EVI')
        return ee.Image.cat([ndvi, evi]).updateMask(mask)

    l8 = ee.ImageCollection(DATASETS['landsat8'])
    l9 = ee.ImageCollection(DATASETS['landsat9'])
    col = (l8.merge(l9)
           .filterDate(start_date, end_date)
           .filterBounds(geometry)
           .filter(ee.Filter.lt('CLOUD_COVER', cloud_threshold))
           .map(proc))
    return col.median().clip(geometry)


def ndvi_to_biomass_model(ndvi_mean: Optional[float], preset: str = 'central_asia', params: dict = None) -> Optional[float]:
        """Convert NDVI mean to biomass (t/ha) using a simple, configurable model.

        The model supports two basic styles:
            - fvc_scale: convert NDVI to fractional vegetation cover (FVC) via
                (NDVI - ndvi_min)/(ndvi_max - ndvi_min), clamp to [0,1], then
                biomass = FVC * biomass_max_t_per_ha
            - linear: biomass = a * NDVI + b

        Presets provide reasonable starting coefficients for broad land-cover
        types in arid/Central Asia settings. These are approximate and must be
        calibrated with field data for research-grade results.

        Presets (defaults):
            - 'arid' / 'central_asia': conservative FVC scaling with biomass_max ~ 8-12 t/ha
            - 'semiarid': higher biomass_max ~ 12-18 t/ha

        Args:
            ndvi_mean: mean NDVI value (0..1) or None
            preset: one of 'arid','semiarid','central_asia','mesic' or 'custom'
            params: optional dict to override preset values. Recognized keys depend on model type.

        Returns:
            biomass in t/ha or None if input invalid.
        """
        if ndvi_mean is None:
                return None

        presets = {
                'arid': {'model': 'fvc_scale', 'ndvi_min': 0.02, 'ndvi_max': 0.45, 'biomass_max_t_per_ha': 8.0},
                'central_asia': {'model': 'fvc_scale', 'ndvi_min': 0.03, 'ndvi_max': 0.55, 'biomass_max_t_per_ha': 10.0},
                'semiarid': {'model': 'fvc_scale', 'ndvi_min': 0.04, 'ndvi_max': 0.6, 'biomass_max_t_per_ha': 14.0},
                'mesic': {'model': 'fvc_scale', 'ndvi_min': 0.05, 'ndvi_max': 0.75, 'biomass_max_t_per_ha': 20.0},
                # linear model example (units: t/ha per NDVI): biomass = a*NDVI + b
                'linear_example': {'model': 'linear', 'a': 25.0, 'b': -2.0}
        }

        cfg = presets.get(preset, presets['central_asia']).copy()
        if params:
                cfg.update(params)

        try:
                if cfg['model'] == 'fvc_scale':
                        ndvi_min = float(cfg.get('ndvi_min', 0.03))
                        ndvi_max = float(cfg.get('ndvi_max', 0.6))
                        biomass_max = float(cfg.get('biomass_max_t_per_ha', 10.0))
                        fvc = (ndvi_mean - ndvi_min) / (ndvi_max - ndvi_min) if (ndvi_max - ndvi_min) != 0 else 0.0
                        fvc = max(0.0, min(1.0, fvc))
                        return float(fvc * biomass_max)
                elif cfg['model'] == 'linear':
                        a = float(cfg.get('a', 1.0))
                        b = float(cfg.get('b', 0.0))
                        return float(max(0.0, a * ndvi_mean + b))
                else:
                        return None
        except Exception:
                return None


def run_city_auxiliary(base: Path, city: str, year: int, download_scale: int = 30, cloud_threshold: int = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {'city': city, 'year': year, 'generated': {}, 'stats': {}}
    if city not in UZBEKISTAN_CITIES:
        out['error'] = 'city not found'
        return out
    city_info = UZBEKISTAN_CITIES[city]
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    region = center.buffer(city_info['buffer_m']).bounds()

    if cloud_threshold is None:
        cloud_threshold = ANALYSIS_CONFIG.get('cloud_threshold', 20)

    # Seasons: summer from ANALYSIS_CONFIG['warm_months'], winter as Jan-Feb
    summer_months = ANALYSIS_CONFIG.get('warm_months', [6,7,8])
    winter_months = [1,2]

    summer_start, summer_end = _format_date_range_for_months(year, summer_months)
    winter_start, winter_end = _format_date_range_for_months(year, winter_months)

    try:
        # Vegetation indices
        summer_veg = _compute_seasonal_ndvi_evi(summer_start, summer_end, region, cloud_threshold)
        winter_veg = _compute_seasonal_ndvi_evi(winter_start, winter_end, region, cloud_threshold)

        # Landsat thermal
        summer_lst = load_landsat_thermal(summer_start, summer_end, region)
        winter_lst = load_landsat_thermal(winter_start, winter_end, region)

        # Compute change images
        ndvi_change = summer_veg.select('NDVI').subtract(winter_veg.select('NDVI')).rename('NDVI_change')
        evi_change = summer_veg.select('EVI').subtract(winter_veg.select('EVI')).rename('EVI_change')
        lst_change = None
        if summer_lst and winter_lst:
            try:
                lst_change = summer_lst.select(0).subtract(winter_lst.select(0)).rename('LST_change')
            except Exception:
                lst_change = None

        # Prepare output directories
        dirs = create_output_directories()
        veg_dir = dirs['vegetation'] / city
        temp_dir = dirs['temperature'] / city
        veg_dir.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Download rasters
        # Use lulc._download_image_geturl for consistent behaviour
        def _dl(img, out_dir: Path, fname: str) -> Optional[str]:
            try:
                p = lulc._download_image_geturl(img, region, download_scale, out_dir, fname)
                return str(p) if p else None
            except Exception:
                return None

        out['generated']['summer_veg_tif'] = _dl(summer_veg, veg_dir, f"{city}_ndvi_evi_summer_{year}")
        out['generated']['winter_veg_tif'] = _dl(winter_veg, veg_dir, f"{city}_ndvi_evi_winter_{year}")
        out['generated']['ndvi_change_tif'] = _dl(ndvi_change, veg_dir, f"{city}_ndvi_change_{year}")
        out['generated']['evi_change_tif'] = _dl(evi_change, veg_dir, f"{city}_evi_change_{year}")

        if summer_lst is not None:
            out['generated']['summer_lst_tif'] = _dl(summer_lst, temp_dir, f"{city}_lst_summer_{year}")
        else:
            out['generated']['summer_lst_tif'] = None
        if winter_lst is not None:
            out['generated']['winter_lst_tif'] = _dl(winter_lst, temp_dir, f"{city}_lst_winter_{year}")
        else:
            out['generated']['winter_lst_tif'] = None
        if lst_change is not None:
            out['generated']['lst_change_tif'] = _dl(lst_change, temp_dir, f"{city}_lst_change_{year}")
        else:
            out['generated']['lst_change_tif'] = None

        # Summary stats: compute area mean within region using reduceRegion
        try:
            stats = {}
            def _region_mean(img, band_name):
                try:
                    val = img.select(band_name).reduceRegion(reducer=ee.Reducer.mean(), geometry=region, scale=download_scale, maxPixels=1e10).get(band_name).getInfo()
                    return float(val) if val is not None else None
                except Exception:
                    return None

            stats['summer_ndvi_mean'] = _region_mean(summer_veg, 'NDVI')
            stats['winter_ndvi_mean'] = _region_mean(winter_veg, 'NDVI')
            stats['ndvi_change_mean'] = _region_mean(ndvi_change, 'NDVI_change')
            stats['summer_evi_mean'] = _region_mean(summer_veg, 'EVI')
            stats['winter_evi_mean'] = _region_mean(winter_veg, 'EVI')
            stats['evi_change_mean'] = _region_mean(evi_change, 'EVI_change')
            # LST bands: attempt to find numeric band name for landsat thermal
            if summer_lst is not None:
                lst_band = summer_lst.bandNames().getInfo()[0]
                stats['summer_lst_mean'] = _region_mean(summer_lst, lst_band)
            else:
                stats['summer_lst_mean'] = None
            if winter_lst is not None:
                lst_band_w = winter_lst.bandNames().getInfo()[0]
                stats['winter_lst_mean'] = _region_mean(winter_lst, lst_band_w)
            else:
                stats['winter_lst_mean'] = None
            if lst_change is not None:
                stats['lst_change_mean'] = _region_mean(lst_change, 'LST_change')
            else:
                stats['lst_change_mean'] = None

            # Convert NDVI means to coarse biomass proxy (t/ha)
            try:
                stats['summer_biomass_t_per_ha'] = ndvi_to_biomass_model(stats.get('summer_ndvi_mean'), preset='central_asia')
                stats['winter_biomass_t_per_ha'] = ndvi_to_biomass_model(stats.get('winter_ndvi_mean'), preset='central_asia')
                # biomass change (t/ha)
                if stats.get('summer_biomass_t_per_ha') is not None and stats.get('winter_biomass_t_per_ha') is not None:
                    stats['biomass_change_t_per_ha'] = stats['summer_biomass_t_per_ha'] - stats['winter_biomass_t_per_ha']
                else:
                    stats['biomass_change_t_per_ha'] = None
            except Exception:
                stats['biomass_conversion_error'] = True

            out['stats'] = stats
            # Compute uncertainty/error assessments using server-side EE reducers
            try:
                unc = {}
                zones = {'city': region}
                # Vegetation indices: NDVI and EVI (summer, winter, change)
                try:
                    unc['summer_ndvi'] = error_assessment.compute_zonal_uncertainty(summer_veg.select('NDVI'), zones, scale=download_scale)
                except Exception as _e:
                    unc.setdefault('errors', {})['summer_ndvi'] = str(_e)
                try:
                    unc['winter_ndvi'] = error_assessment.compute_zonal_uncertainty(winter_veg.select('NDVI'), zones, scale=download_scale)
                except Exception as _e:
                    unc.setdefault('errors', {})['winter_ndvi'] = str(_e)
                try:
                    unc['ndvi_change'] = error_assessment.compute_zonal_uncertainty(ndvi_change, zones, scale=download_scale)
                except Exception as _e:
                    unc.setdefault('errors', {})['ndvi_change'] = str(_e)

                try:
                    unc['summer_evi'] = error_assessment.compute_zonal_uncertainty(summer_veg.select('EVI'), zones, scale=download_scale)
                except Exception as _e:
                    unc.setdefault('errors', {})['summer_evi'] = str(_e)
                try:
                    unc['winter_evi'] = error_assessment.compute_zonal_uncertainty(winter_veg.select('EVI'), zones, scale=download_scale)
                except Exception as _e:
                    unc.setdefault('errors', {})['winter_evi'] = str(_e)
                try:
                    unc['evi_change'] = error_assessment.compute_zonal_uncertainty(evi_change, zones, scale=download_scale)
                except Exception as _e:
                    unc.setdefault('errors', {})['evi_change'] = str(_e)

                # LST products (if available)
                try:
                    if summer_lst is not None:
                        unc['summer_lst'] = error_assessment.compute_zonal_uncertainty(summer_lst, zones, scale=download_scale)
                except Exception as _e:
                    unc.setdefault('errors', {})['summer_lst'] = str(_e)
                try:
                    if winter_lst is not None:
                        unc['winter_lst'] = error_assessment.compute_zonal_uncertainty(winter_lst, zones, scale=download_scale)
                except Exception as _e:
                    unc.setdefault('errors', {})['winter_lst'] = str(_e)
                try:
                    if lst_change is not None:
                        unc['lst_change'] = error_assessment.compute_zonal_uncertainty(lst_change, zones, scale=download_scale)
                except Exception as _e:
                    unc.setdefault('errors', {})['lst_change'] = str(_e)

                out['uncertainty'] = unc
            except Exception as ee_unc_err:
                out['uncertainty_error'] = str(ee_unc_err)
        except Exception as e:
            out['stats_error'] = str(e)

    except Exception as ex:
        out['error'] = str(ex)

    # Write JSON summary
    try:
        from .utils import make_json_safe
        base_dir = Path(__file__).parent.parent / 'suhi_analysis_output'
        save_dir = base_dir / 'vegetation' / city
        save_dir.mkdir(parents=True, exist_ok=True)
        out_file = save_dir / f"{city}_auxiliary_{year}.json"
        safe_out = make_json_safe(out)
        with open(out_file, 'w', encoding='utf-8') as fh:
            json.dump(safe_out, fh, indent=2)
        out['summary_json'] = str(out_file)
    except Exception:
        out['summary_json'] = None

    return out


def run_batch(cities: Optional[List[str]] = None, years: Optional[List[int]] = None, download_scale: int = 30) -> Dict[str, Any]:
    base_dirs = create_output_directories()
    if cities is None:
        cities = list(UZBEKISTAN_CITIES.keys())
    if years is None:
        years = ANALYSIS_CONFIG.get('years', [])

    results = {}
    for city in cities:
        results[city] = {}
        for y in years:
            results[city][str(y)] = run_city_auxiliary(base_dirs['base'], city, y, download_scale=download_scale)
    return results
