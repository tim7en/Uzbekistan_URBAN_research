"""SUHI unit: generate pixel SUHI maps per city/year using MODIS LST composites (day and night)
and compute comprehensive SUHI analysis. Saves GeoTIFFs and JSON summaries.

This module reuses existing helpers: `services.temperature`, `services.classification`,
`services.lulc._download_image_geturl`, and `services.suhi` computation helpers.

Changed from Landsat thermal to MODIS LST data (MOD11A2) for better temporal coverage
and dedicated day/night LST measurements.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

import ee

from . import lulc, classification, suhi as suhi_core
from . import error_assessment
from .utils import create_output_directories, make_json_safe, GEE_CONFIG
from pathlib import Path
from .temperature import load_modis_lst
from .utils import UZBEKISTAN_CITIES, create_output_directories, GEE_CONFIG, ANALYSIS_CONFIG, get_optimal_scale_for_city
import math
import time


def _safe_serialize(obj):
    """Recursively convert common Earth Engine objects and other non-JSON types
    into JSON-serializable Python types. Falls back to string representation.

    This avoids json.dump failing when the result dict contains ee.Image, ee.Number,
    ee.List, ee.Dictionary or Task objects.
    """
    from collections.abc import Mapping, Sequence
    # Primitives
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    # Mappings
    if isinstance(obj, Mapping):
        return {str(k): _safe_serialize(v) for k, v in obj.items()}
    # Sequences (but not bytes/str)
    if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
        return [_safe_serialize(v) for v in obj]
    # Try Earth Engine getInfo() where available
    try:
        if hasattr(obj, 'getInfo'):
            return obj.getInfo()
    except Exception:
        pass
    # Fallback to string
    try:
        return str(obj)
    except Exception:
        return None


def _make_urban_mask_from_classifications(classifications: Dict[str, ee.Image]) -> ee.Image:
    # Weighted ensemble: ESRI weighted if present
    if 'esri' in classifications and len(classifications) > 1:
        w = ANALYSIS_CONFIG.get('esri_weight', 0.5)
        urban_mask = classifications['esri'].multiply(w)
        other_w = (1 - w) / (len(classifications) - 1)
        for name, img in classifications.items():
            if name != 'esri':
                urban_mask = urban_mask.add(img.multiply(other_w))
    else:
        weight = 1.0 / max(1, len(classifications))
        urban_mask = ee.Image.constant(0)
        for img in classifications.values():
            urban_mask = urban_mask.add(img.multiply(weight))
    return urban_mask.gt(0.5)


def run_city_suhi(base: Path, city: str, year: int, download_scale: int = 30) -> Dict[str, Any]:
    out: Dict[str, Any] = {'city': city, 'year': year, 'generated': {}, 'stats': {}}
    if city not in UZBEKISTAN_CITIES:
        out['error'] = 'city not found'
        return out
    city_info = UZBEKISTAN_CITIES[city]
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    zones = {
        'urban_core': center.buffer(city_info['buffer_m']).buffer(-100),
        'rural_ring': center.buffer(city_info['buffer_m'] + ANALYSIS_CONFIG['rural_buffer_km']*1000).difference(center.buffer(city_info['buffer_m']))
    }

    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    try:
        classifications = classification.load_all_classifications(year, zones['urban_core'].buffer(ANALYSIS_CONFIG['rural_buffer_km']*1000), start_date, end_date)
    except Exception as e:
        classifications = {}

    try:
        # Primary SUHI analysis using MODIS LST data (day and night)
        modis_lst = load_modis_lst(start_date, end_date, zones['urban_core'].buffer(ANALYSIS_CONFIG['rural_buffer_km']*1000))

        # Urban mask
        urban_mask = _make_urban_mask_from_classifications(classifications) if classifications else ee.Image.constant(0)
        rural_mask = urban_mask.Not()

        # Process MODIS LST data for primary SUHI analysis
        if modis_lst is not None:
            try:
                m_bands = modis_lst.bandNames().getInfo()
                # expect day band first, night second
                day_band = m_bands[0] if len(m_bands) > 0 else None
                night_band = m_bands[1] if len(m_bands) > 1 else None
            except Exception:
                day_band = None; night_band = None
            
            # Process day LST for primary SUHI
            if day_band is not None:
                day_lst = modis_lst.select([day_band])
                # Use MODIS scale for region statistics to avoid excessive computation
                stats_scale = max(GEE_CONFIG.get('scale_modis', 1000), 250)
                try:
                    rural_stats_day = day_lst.updateMask(rural_mask).reduceRegion(
                        reducer=ee.Reducer.mean(), 
                        geometry=zones['rural_ring'], 
                        scale=stats_scale, 
                        maxPixels=GEE_CONFIG['max_pixels'], 
                        bestEffort=True
                    )
                except Exception:
                    rural_stats_day = day_lst.updateMask(rural_mask).reduceRegion(
                        reducer=ee.Reducer.mean(), 
                        geometry=zones['rural_ring'], 
                        scale=stats_scale*2, 
                        maxPixels=GEE_CONFIG['max_pixels'], 
                        bestEffort=True
                    )
                rural_mean_day = rural_stats_day.get(day_band)
                rural_mean_day_val = rural_mean_day.getInfo() if rural_mean_day else None
                
                if rural_mean_day_val is not None:
                    suhi_day_img = day_lst.select(day_band).toFloat().subtract(float(rural_mean_day_val)).rename('SUHI_Day_MODIS')
                    
                    # Zonal stats for day LST
                    try:
                        urban_mean_day = day_lst.select([day_band]).updateMask(urban_mask).reduceRegion(
                            reducer=ee.Reducer.mean(), 
                            geometry=zones['urban_core'], 
                            scale=stats_scale, 
                            maxPixels=GEE_CONFIG['max_pixels']
                        ).get(day_band).getInfo()
                        
                        out['stats']['modis_day_urban_mean'] = float(urban_mean_day) if urban_mean_day is not None else None
                        out['stats']['modis_day_rural_mean'] = float(rural_mean_day_val) if rural_mean_day_val is not None else None
                        out['stats']['suhi_day_mean'] = (float(urban_mean_day) - float(rural_mean_day_val)) if urban_mean_day is not None and rural_mean_day_val is not None else None
                        
                        # compute uncertainty for day LST
                        try:
                            day_unc = error_assessment.compute_zonal_uncertainty(
                                day_lst.select([day_band]), 
                                {'urban_core': zones['urban_core'], 'rural_ring': zones['rural_ring']}, 
                                scale=stats_scale, 
                                maxPixels=GEE_CONFIG.get('max_pixels', int(1e8))
                            )
                            out['stats']['uncertainty_day'] = day_unc
                        except Exception:
                            out['stats']['uncertainty_day'] = None
                    except Exception:
                        pass
                else:
                    out['warning'] = 'Could not compute rural mean for MODIS day LST'
            else:
                out['warning'] = 'No MODIS day LST band available'
            
            # Process night LST for SUHI
            if night_band is not None:
                night_lst = modis_lst.select([night_band])
                try:
                    rural_stats_night = night_lst.updateMask(rural_mask).reduceRegion(
                        reducer=ee.Reducer.mean(), 
                        geometry=zones['rural_ring'], 
                        scale=stats_scale, 
                        maxPixels=GEE_CONFIG['max_pixels'], 
                        bestEffort=True
                    )
                except Exception:
                    rural_stats_night = night_lst.updateMask(rural_mask).reduceRegion(
                        reducer=ee.Reducer.mean(), 
                        geometry=zones['rural_ring'], 
                        scale=stats_scale*2, 
                        maxPixels=GEE_CONFIG['max_pixels'], 
                        bestEffort=True
                    )
                rural_mean_night = rural_stats_night.get(night_band)
                rural_mean_night_val = rural_mean_night.getInfo() if rural_mean_night else None
                
                if rural_mean_night_val is not None:
                    suhi_night_img = night_lst.select(night_band).toFloat().subtract(float(rural_mean_night_val)).rename('SUHI_Night_MODIS')
                    
                    # Zonal stats for night LST
                    try:
                        urban_mean_night = night_lst.select([night_band]).updateMask(urban_mask).reduceRegion(
                            reducer=ee.Reducer.mean(), 
                            geometry=zones['urban_core'], 
                            scale=stats_scale, 
                            maxPixels=GEE_CONFIG['max_pixels']
                        ).get(night_band).getInfo()
                        
                        out['stats']['modis_night_urban_mean'] = float(urban_mean_night) if urban_mean_night is not None else None
                        out['stats']['modis_night_rural_mean'] = float(rural_mean_night_val) if rural_mean_night_val is not None else None
                        out['stats']['suhi_night_mean'] = (float(urban_mean_night) - float(rural_mean_night_val)) if urban_mean_night is not None and rural_mean_night_val is not None else None
                        
                        # compute uncertainty for night LST
                        try:
                            night_unc = error_assessment.compute_zonal_uncertainty(
                                night_lst.select([night_band]), 
                                {'urban_core': zones['urban_core'], 'rural_ring': zones['rural_ring']}, 
                                scale=stats_scale, 
                                maxPixels=GEE_CONFIG.get('max_pixels', int(1e8))
                            )
                            out['stats']['uncertainty_night'] = night_unc
                        except Exception:
                            out['stats']['uncertainty_night'] = None
                    except Exception:
                        pass
                else:
                    out['warning'] = 'Could not compute rural mean for MODIS night LST'
            else:
                out['warning'] = 'No MODIS night LST band available'
                
            # Day/night SUHI comparative analysis using MODIS
            try:
                day_img = modis_lst.select([day_band]).rename('LST_Day_MODIS') if day_band else None
                night_img = modis_lst.select([night_band]).rename('LST_Night_MODIS') if night_band else None
                day_night_res = suhi_core.compute_day_night_suhi({'urban_core': zones['urban_core'], 'rural_ring': zones['rural_ring']}, day_img, night_img, classifications)
                out['day_night'] = day_night_res
            except Exception as e:
                out['day_night_error'] = str(e)
        else:
            out['warning'] = 'No MODIS LST data available'

    except Exception as e:
        # If the failure is due to large reprojection output, fall back to a safe
        # zonal/stats-only computation so the result JSON still contains usable information.
        err_str = str(e)
        out['error'] = err_str
        if 'reprojection' in err_str.lower() or 'reproject' in err_str.lower() or 'too large' in err_str.lower():
            try:
                # Choose a coarser stats scale based on city to reduce computation
                fallback_params = get_optimal_scale_for_city(city, analysis_phase='fallback')
                stats_scale = int(fallback_params.get('scale_landsat', 500))
                stats_res = run_city_suhi_stats(city, year, stats_scale=stats_scale)
                out['note'] = 'Fell back to stats-only computation due to reprojection limits'
                out['stats'] = stats_res.get('stats', {}) if isinstance(stats_res, dict) else {}
                # Clear the heavy 'error' if stats were computed
                if out['stats']:
                    out.pop('error', None)
            except Exception as fallback_e:
                out['fallback_error'] = str(fallback_e)

    # Save JSON
    try:
        save_dir = base / 'suhi' / city
        save_dir.mkdir(parents=True, exist_ok=True)
        out_file = save_dir / f"{city}_suhi_{year}.json"
        # sanitize the result so json.dump doesn't fail on EE objects
        safe_out = _safe_serialize(out)
        with open(out_file, 'w', encoding='utf-8') as fh:
            json.dump(safe_out, fh, indent=2)
        out['summary_json'] = str(out_file)
    except Exception:
        # try to preserve reason for failure in the returned dictionary
        import traceback
        tb = traceback.format_exc()
        print(f"⚠️ Failed to write SUHI JSON for {city} {year}: {tb}")
        out['summary_json'] = None

    return out


def run_batch(cities: Optional[List[str]] = None, years: Optional[List[int]] = None, download_scale: int = 30) -> Dict[str, Any]:
    base_dirs = create_output_directories()

    if cities is None:
        cities = list(UZBEKISTAN_CITIES.keys())
    if years is None:
        years = list(range(2017, 2025))

    results = {}
    for city in cities:
        results[city] = {}
        for y in years:
            # Use stats-only run to avoid large reprojection/export issues.
            res = run_city_suhi_stats(city, y, stats_scale=max(download_scale, 250))
            # Save per-city/year JSON summary for easy reporting
            save_dir = base_dirs['base'] / 'suhi' / city
            save_dir.mkdir(parents=True, exist_ok=True)
            out_file = save_dir / f"{city}_suhi_{y}.json"
            try:
                # sanitize before saving
                safe = _safe_serialize(res)
                with open(out_file, 'w', encoding='utf-8') as fh:
                    json.dump(safe, fh, indent=2)
                res['summary_json'] = str(out_file)
            except Exception:
                res['summary_json'] = None
            results[city][str(y)] = res
    return results


def run_city_suhi_stats(city: str, year: int, stats_scale: int = 500) -> Dict[str, Any]:
    """Compute zonal SUHI statistics (urban vs rural means) without any exports.

    This helper is intended for quick tests: it avoids image exports and
    large reprojection operations by only running server-side reductions.
    Now uses MODIS LST data (day and night) instead of Landsat thermal.
    """
    out: Dict[str, Any] = {'city': city, 'year': year, 'stats': {}}
    if city not in UZBEKISTAN_CITIES:
        out['error'] = 'city not found'
        return out
    city_info = UZBEKISTAN_CITIES[city]
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    urban_core = center.buffer(city_info['buffer_m'])
    rural_ring = center.buffer(city_info['buffer_m'] + ANALYSIS_CONFIG['rural_buffer_km']*1000).difference(urban_core)
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    try:
        # Use MODIS LST instead of Landsat thermal
        modis_lst = load_modis_lst(start_date, end_date, urban_core.buffer(ANALYSIS_CONFIG['rural_buffer_km']*1000))
        if modis_lst is None:
            out['error'] = 'No MODIS LST data available'
            return out
        
        # Get day and night bands
        try:
            band_names = modis_lst.bandNames().getInfo()
            day_band = band_names[0] if len(band_names) > 0 else None
            night_band = band_names[1] if len(band_names) > 1 else None
        except Exception:
            out['error'] = 'Could not read MODIS LST band names'
            return out

        # Use MODIS scale for statistics
        modis_scale = max(stats_scale, GEE_CONFIG.get('scale_modis', 1000))
        
        # Process day LST
        if day_band is not None:
            day_lst = modis_lst.select([day_band])
            try:
                urban_stats_day = day_lst.reduceRegion(
                    reducer=ee.Reducer.mean(), 
                    geometry=urban_core, 
                    scale=modis_scale, 
                    maxPixels=GEE_CONFIG['max_pixels'], 
                    bestEffort=True
                )
                rural_stats_day = day_lst.reduceRegion(
                    reducer=ee.Reducer.mean(), 
                    geometry=rural_ring, 
                    scale=modis_scale, 
                    maxPixels=GEE_CONFIG['max_pixels'], 
                    bestEffort=True
                )
                urban_mean_day = urban_stats_day.get(day_band).getInfo() if urban_stats_day else None
                rural_mean_day = rural_stats_day.get(day_band).getInfo() if rural_stats_day else None
                
                out['stats']['day_urban_mean'] = float(urban_mean_day) if urban_mean_day is not None else None
                out['stats']['day_rural_mean'] = float(rural_mean_day) if rural_mean_day is not None else None
                out['stats']['suhi_day'] = (out['stats']['day_urban_mean'] - out['stats']['day_rural_mean']) if out['stats']['day_urban_mean'] is not None and out['stats']['day_rural_mean'] is not None else None
                
            except Exception as e:
                out['day_error'] = str(e)
        
        # Process night LST
        if night_band is not None:
            night_lst = modis_lst.select([night_band])
            try:
                urban_stats_night = night_lst.reduceRegion(
                    reducer=ee.Reducer.mean(), 
                    geometry=urban_core, 
                    scale=modis_scale, 
                    maxPixels=GEE_CONFIG['max_pixels'], 
                    bestEffort=True
                )
                rural_stats_night = night_lst.reduceRegion(
                    reducer=ee.Reducer.mean(), 
                    geometry=rural_ring, 
                    scale=modis_scale, 
                    maxPixels=GEE_CONFIG['max_pixels'], 
                    bestEffort=True
                )
                urban_mean_night = urban_stats_night.get(night_band).getInfo() if urban_stats_night else None
                rural_mean_night = rural_stats_night.get(night_band).getInfo() if rural_stats_night else None
                
                out['stats']['night_urban_mean'] = float(urban_mean_night) if urban_mean_night is not None else None
                out['stats']['night_rural_mean'] = float(rural_mean_night) if rural_mean_night is not None else None
                out['stats']['suhi_night'] = (out['stats']['night_urban_mean'] - out['stats']['night_rural_mean']) if out['stats']['night_urban_mean'] is not None and out['stats']['night_rural_mean'] is not None else None
                
            except Exception as e:
                out['night_error'] = str(e)
        
        # Add day-night difference analysis
        if 'suhi_day' in out['stats'] and 'suhi_night' in out['stats']:
            if out['stats']['suhi_day'] is not None and out['stats']['suhi_night'] is not None:
                out['stats']['suhi_day_night_diff'] = out['stats']['suhi_day'] - out['stats']['suhi_night']
                out['stats']['day_stronger_than_night'] = out['stats']['suhi_day'] > out['stats']['suhi_night']
            
        # Add uncertainty analysis for MODIS LST
        try:
            zones = {'urban_core': urban_core, 'rural_ring': rural_ring}
            if day_band is not None:
                day_uncertainty = error_assessment.compute_zonal_uncertainty(
                    day_lst, zones, scale=modis_scale, maxPixels=GEE_CONFIG['max_pixels']
                )
                out['stats']['uncertainty_day'] = day_uncertainty
            if night_band is not None:
                night_uncertainty = error_assessment.compute_zonal_uncertainty(
                    night_lst, zones, scale=modis_scale, maxPixels=GEE_CONFIG['max_pixels']
                )
                out['stats']['uncertainty_night'] = night_uncertainty
        except Exception as unc_err:
            out['stats']['uncertainty_error'] = str(unc_err)
            
    except Exception as e:
        out['error'] = str(e)
    return out


def export_suhi_tiles(base: Path, city: str, year: int, tile_size_m: int = 5000, scale: int = 1000, overlap_m: int = 250) -> Dict[str, Any]:
    """Export SUHI map in tiles to Google Drive. Returns task ids and summary.
    Now uses MODIS LST data (day and night) instead of Landsat thermal.

    Notes:
    - Requires GEE and Drive export enabled for the authenticated account.
    - This will create multiple ee.batch.Export.image.toDrive tasks; monitor them in the GEE Task Manager or Drive.
    - tile_size_m controls approximate tile side in meters. overlap_m controls tile overlap to avoid edge artifacts.
    - Default scale is now 1000m to match MODIS LST resolution.
    """
    out: Dict[str, Any] = {'city': city, 'year': year, 'generated': {'tile_tasks': []}, 'stats': {}}
    if city not in UZBEKISTAN_CITIES:
        out['error'] = 'city not found'
        return out
    city_info = UZBEKISTAN_CITIES[city]
    lon = city_info['lon']; lat = city_info['lat']
    buffer_m = city_info['buffer_m'] + ANALYSIS_CONFIG['rural_buffer_km'] * 1000

    # compute SUHI image using MODIS LST (reuse logic from run_city_suhi)
    start_date = f"{year}-01-01"; end_date = f"{year}-12-31"
    try:
        classifications = classification.load_all_classifications(year, ee.Geometry.Point([lon, lat]).buffer(city_info['buffer_m'] + ANALYSIS_CONFIG['rural_buffer_km']*1000), start_date, end_date)
    except Exception:
        classifications = {}
    
    modis_lst = load_modis_lst(start_date, end_date, ee.Geometry.Point([lon, lat]).buffer(buffer_m))
    if modis_lst is None:
        out['error'] = 'No MODIS LST data available for export'
        return out
    
    # determine day and night bands
    try:
        band_names = modis_lst.bandNames().getInfo()
        day_band = band_names[0] if len(band_names) > 0 else None
        night_band = band_names[1] if len(band_names) > 1 else None
    except Exception:
        out['error'] = 'Could not determine MODIS LST bands for export'
        return out
    
    if day_band is None:
        out['error'] = 'No day LST band available for export'
        return out
        
    # create urban/rural masks
    if classifications:
        urban_mask = _make_urban_mask_from_classifications(classifications)
    else:
        urban_mask = ee.Image.constant(0)
    rural_mask = urban_mask.Not()
    
    # Compute rural mean for day LST
    day_lst = modis_lst.select([day_band])
    try:
        rural_stats = day_lst.updateMask(rural_mask).reduceRegion(
            reducer=ee.Reducer.mean(), 
            geometry=ee.Geometry.Point([lon, lat]).buffer(buffer_m).difference(ee.Geometry.Point([lon, lat]).buffer(city_info['buffer_m'])), 
            scale=max(scale, GEE_CONFIG.get('scale_modis', 1000)), 
            maxPixels=GEE_CONFIG['max_pixels'], 
            bestEffort=True
        )
        rural_mean = rural_stats.get(day_band).getInfo()
    except Exception:
        rural_mean = None
        
    if rural_mean is None:
        # Try a stats-only fallback to get a coarse rural mean
        try:
            stats_res = run_city_suhi_stats(city, year, stats_scale=max(scale, GEE_CONFIG.get('scale_modis', 1000)))
            rm = None
            if isinstance(stats_res, dict):
                stats = stats_res.get('stats', {})
                # try expected keys for day rural mean
                rm = stats.get('day_rural_mean') or stats.get('rural_mean')
            if rm is not None:
                rural_mean = float(rm)
            else:
                out['error'] = 'Could not compute rural mean for SUHI export'
                return out
        except Exception as e:
            out['error'] = f'Could not compute rural mean for SUHI export: {e}'
            return out
    
    # Create SUHI image using day LST
    suhi_img = day_lst.toFloat().subtract(float(rural_mean)).rename('SUHI_Day_MODIS')

    # compute bounding box in degrees using approximate meters->degrees conversion
    lat_rad = math.radians(lat)
    deg_per_m_lat = 1.0 / 111320.0
    deg_per_m_lon = 1.0 / (111320.0 * math.cos(lat_rad))
    half = buffer_m
    min_lon = lon - half * deg_per_m_lon
    max_lon = lon + half * deg_per_m_lon
    min_lat = lat - half * deg_per_m_lat
    max_lat = lat + half * deg_per_m_lat

    dx = tile_size_m * deg_per_m_lon
    dy = tile_size_m * deg_per_m_lat
    step_x = dx - overlap_m * deg_per_m_lon
    step_y = dy - overlap_m * deg_per_m_lat

    ix = 0
    for x in frange(min_lon, max_lon, step_x):
        iy = 0
        for y in frange(min_lat, max_lat, step_y):
            tile_minx = x
            tile_miny = y
            tile_maxx = min(x + dx, max_lon)
            tile_maxy = min(y + dy, max_lat)
            geom = ee.Geometry.Rectangle([tile_minx, tile_miny, tile_maxx, tile_maxy])
            tile_img = suhi_img.clip(geom).updateMask(urban_mask)
            fname = f"{city}_suhi_modis_{year}_tile_{ix}_{iy}"
            try:
                task = ee.batch.Export.image.toDrive(image=tile_img, description=fname, folder='SUHI_Exports', fileNamePrefix=fname, region=geom.bounds().getInfo()['coordinates'], scale=scale, crs='EPSG:4326', maxPixels=1e13)
                task.start()
                out['generated']['tile_tasks'].append({'tile': (ix, iy), 'task_id': getattr(task, 'id', None), 'fname': fname})
                # small delay to avoid hammering the API
                time.sleep(0.5)
            except Exception as e:
                out['generated']['tile_tasks'].append({'tile': (ix, iy), 'error': str(e), 'fname': fname})
            iy += 1
        ix += 1
    return out


def frange(start, stop, step):
    x = start
    while x < stop:
        yield x
        x += step
    
