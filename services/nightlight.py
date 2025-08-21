"""Nighttime lights analysis helpers using Google Earth Engine.

Loads VIIRS monthly composites and DMSP when available, computes simple
statistics (mean radiance), generates thumbnail maps, and exports
aggregated statistics for reporting.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
import ee
import numpy as np

from .utils import UZBEKISTAN_CITIES, DATASETS, ANALYSIS_CONFIG, create_analysis_zones, rate_limiter, create_output_directories, make_json_safe, GEE_CONFIG
from . import error_assessment
from pathlib import Path


def load_viirs_monthly(year: int, geometry: ee.Geometry) -> ee.Image:
    """Load VIIRS monthly composite for a year and return median image clipped to geometry.

    Uses DATASETS['viirs_monthly'] which should point to a monthly VIIRS DNB collection.
    """
    start = f"{year}-01-01"
    end = f"{year}-12-31"
    col = ee.ImageCollection(DATASETS['viirs_monthly']).filterDate(start, end).filterBounds(geometry)
    # Some VIIRS collections use 'avg_rad' or 'radiance' band names; fallback to first band
    img = col.median().clip(geometry)
    return img


def compute_nightlight_stats(image: ee.Image, zones: Dict[str, ee.Geometry], scale: int = 500) -> Dict[str, Any]:
    """Compute mean and histogram of radiance inside urban and rural zones."""
    rate_limiter.wait()
    stats = {}
    try:
        for name, geom in zones.items():
            # Using separate reduceRegion calls for each reducer is more robust
            # because some collections or EE behaviours return scalar values for
            # single reducers and nested dicts for combined reducers. Request
            # mean, stdDev and count separately and parse results.
            stats[name] = {'mean': None, 'stdDev': None, 'count': None}
            try:
                mean_out = image.reduceRegion(reducer=ee.Reducer.mean(), geometry=geom, scale=scale, maxPixels=1e8, bestEffort=True)
                std_out = image.reduceRegion(reducer=ee.Reducer.stdDev(), geometry=geom, scale=scale, maxPixels=1e8, bestEffort=True)
                count_out = image.reduceRegion(reducer=ee.Reducer.count(), geometry=geom, scale=scale, maxPixels=1e8, bestEffort=True)

                mean_info = mean_out.getInfo() if mean_out else {}
                std_info = std_out.getInfo() if std_out else {}
                count_info = count_out.getInfo() if count_out else {}

                # Helper to extract a scalar value from reduceRegion info
                def _extract_scalar(info_dict):
                    if not info_dict:
                        return None
                    # if single key exists, return its value
                    try:
                        k = list(info_dict.keys())[0]
                        v = info_dict[k]
                        if isinstance(v, dict):
                            # nested dict (rare), look for nested mean/std/count keys
                            for sub in ('mean', 'stdDev', 'stddev', 'count'):
                                if sub in v and v[sub] is not None:
                                    return v[sub]
                            # else return None
                            return None
                        else:
                            return v
                    except Exception:
                        return None

                m = _extract_scalar(mean_info)
                s = _extract_scalar(std_info)
                c = _extract_scalar(count_info)

                if m is not None:
                    try:
                        stats[name]['mean'] = float(m)
                    except Exception:
                        stats[name]['mean'] = None
                if s is not None:
                    try:
                        stats[name]['stdDev'] = float(s)
                    except Exception:
                        stats[name]['stdDev'] = None
                if c is not None:
                    try:
                        stats[name]['count'] = int(c)
                    except Exception:
                        try:
                            stats[name]['count'] = int(float(c))
                        except Exception:
                            stats[name]['count'] = None
            except Exception:
                # keep per-zone defaults (None) if sub-requests fail
                pass
    except Exception as e:
        stats['error'] = str(e)
    return stats


def create_nightlight_thumbnail(image: ee.Image, center_lon: float, center_lat: float, buffer_m: int, out_path: Path, file_name: str) -> Optional[Path]:
    """Generate a PNG thumbnail for the image using getThumbURL and save locally.

    This avoids long-running exports; thumbnails are limited resolution suitable for maps.
    """
    try:
        # Visualize: choose first band and apply linear stretch
        bands = image.bandNames().getInfo()
        band = bands[0] if bands else None
        vis_params = {
            'min': 0,
            'max': 50,
            'palette': ['black','#0d0887','#6a00a8','#b12a90','#e16462','#fca636','#f0f921']
        }
        if band:
            vis = image.select([band]).visualize(**vis_params)
        else:
            vis = image.visualize(**vis_params)

        region = ee.Geometry.Point([center_lon, center_lat]).buffer(buffer_m).bounds().getInfo()['coordinates']
        url = vis.getThumbURL({'region': region, 'dimensions': 1024, 'format': 'png'})
        import requests
        out_path.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            p = out_path / f"{file_name}.png"
            with open(p, 'wb') as fh:
                fh.write(r.content)
            return p
        else:
            return None
    except Exception as e:
        print(f"Error creating thumbnail: {e}")
        return None


def download_viirs_geotiff(image: ee.Image, region: ee.Geometry, scale: int, out_path: Path, file_name: str, crs: str = 'EPSG:4326') -> Optional[Path]:
    """Download a GeoTIFF for the given image at specified scale and save locally.

    This uses image.getDownloadURL which can be rate-limited for very large regions. Use a coarse
    scale for local copies (e.g., 500-2000 m) to keep sizes manageable.
    """
    try:
        region_geo = region.bounds().getInfo()['coordinates']
        params = {
            'scale': int(scale),
            'crs': crs,
            'region': region_geo,
            'format': 'GEO_TIFF'
        }
        url = image.getDownloadURL(params)
        import requests
        out_path.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, stream=True, timeout=120)
        if r.status_code == 200:
            p = out_path / f"{file_name}.tif"
            with open(p, 'wb') as fh:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)
            return p
        else:
            print(f"Download failed: status {r.status_code}")
            return None
    except Exception as e:
        print(f"Error downloading GeoTIFF: {e}")
        return None


def run_city_year_viirs(city_name: str, city_info: Dict[str, Any], year: int, output_base: Path) -> Dict[str, Any]:
    """Run VIIRS-based nightlight analysis for a single city and year."""
    result = {'city': city_name, 'year': year}
    try:
        zones = create_analysis_zones(city_info)
        geom = zones['full_extent']
        viirs = load_viirs_monthly(year, geom)
        stats = compute_nightlight_stats(viirs, {'urban_core': zones['urban_core'], 'rural_ring': zones['rural_ring']}, scale=ANALYSIS_CONFIG.get('target_resolution_m',500))
        # compute uncertainty metrics on server-side using EE reducers
        try:
            ua = error_assessment.compute_zonal_uncertainty(viirs, {'urban_core': zones['urban_core'], 'rural_ring': zones['rural_ring']}, scale=ANALYSIS_CONFIG.get('target_resolution_m',500), maxPixels=GEE_CONFIG.get('max_pixels', int(1e8)) if 'GEE_CONFIG' in globals() else int(1e8))
            stats['uncertainty'] = ua
        except Exception:
            stats['uncertainty'] = None
        out_dir = output_base / 'nightlights' / city_name
        out_dir.mkdir(parents=True, exist_ok=True)
        thumb = create_nightlight_thumbnail(viirs, city_info['lon'], city_info['lat'], city_info['buffer_m'], out_dir, f"viirs_{year}")
        result['viirs'] = {'stats': stats, 'thumbnail': str(thumb) if thumb else None}
    except Exception as e:
        result['viirs'] = {'error': str(e)}
    return result


def run_batch_viirs(cities: List[str], years: List[int], output_base: Path) -> List[Dict[str, Any]]:
    """Run VIIRS for a batch of cities and years, and write one JSON per city.

    The output JSON per city will contain yearly entries with stats, uncertainty and
    thumbnail path where available. Returns a list of per-city summaries.
    """
    out_dirs = create_output_directories()
    summaries = []
    for city in cities:
        city_info = UZBEKISTAN_CITIES.get(city)
        if not city_info:
            print(f"City not found: {city}")
            continue
        city_results = {'city': city, 'years': {}}
        print(f"Starting VIIRS batch for city: {city}")
        for y in years:
            print(f"  Running VIIRS for {city} {y}...")
            res = run_city_year_viirs(city, city_info, y, out_dirs['base'])
            # keep only relevant viirs block for compactness
            city_results['years'][str(y)] = res.get('viirs', res)

        # save single JSON per city
        try:
            jdir = out_dirs['base'] / 'nightlights' / city
            jdir.mkdir(parents=True, exist_ok=True)
            jfile = jdir / f"{city}_nightlights.json"
            safe = make_json_safe(city_results)
            import json
            with open(jfile, 'w', encoding='utf-8') as fh:
                json.dump(safe, fh, indent=2)
            city_results['summary_json'] = str(jfile)
        except Exception:
            city_results['summary_json'] = None

        summaries.append(city_results)

    return summaries


def export_viirs_geotiff_drive(image: ee.Image, region: ee.Geometry, scale: int, description: str, folder: str, file_prefix: Optional[str] = None, crs: str = 'EPSG:4326') -> Any:
    """Export an EE image to Google Drive as GeoTIFF and start the task.

    Returns the started ee.batch.Task object (task.id available where possible).
    """
    try:
        print(f"   ▶️ Creating Drive export task: {description}")
        # Use region as GeoJSON coordinates
        region_geo = region.bounds().getInfo()['coordinates']
        fname = file_prefix or description
        task = ee.batch.Export.image.toDrive(
            image=image,
            description=description,
            folder=folder,
            fileNamePrefix=fname,
            region=region_geo,
            scale=scale,
            crs=crs,
            maxPixels=1e13
        )
        task.start()
        try:
            tid = getattr(task, 'id', None)
            print(f"     ✅ Task started: {tid}")
        except Exception:
            tid = None
        return task
    except Exception as e:
        print(f"Error creating Drive export task: {e}")
        return {'error': str(e)}
