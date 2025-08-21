"""LULC service: functions for generating coarse local LULC data, starting
Drive exports for detailed LULC, and running ESRI-based change analysis.

These functions are intended to be imported and used by a small root runner.
"""
from pathlib import Path
import time
import json
from typing import Dict, Any, Optional

import ee
import requests

from .utils import UZBEKISTAN_CITIES
from . import classification
from . import error_assessment
from .utils import create_output_directories, make_json_safe
from pathlib import Path


def _download_image_geturl(image, region, scale: int, out_path: Path, file_name: str, crs: str = 'EPSG:4326') -> Optional[Path]:
    try:
        region_geo = region.bounds().getInfo()['coordinates']
        params = {
            'scale': int(scale),
            'crs': crs,
            'region': region_geo,
            'format': 'GEO_TIFF'
        }
        url = image.getDownloadURL(params)
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
            return None
    except Exception:
        return None


def generate_coarse_local(base: Path, city: str, year: int, coarse_scale: int = 200) -> Dict[str, Any]:
    out: Dict[str, Any] = {'city': city, 'year': year, 'generated': {}}
    city_info = UZBEKISTAN_CITIES.get(city)
    if not city_info:
        out['error'] = 'city not found'
        return out
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    region = center.buffer(city_info['buffer_m']).bounds()
    try:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        classifications = classification.load_all_classifications(year, region, start_date, end_date, optimal_scales={'scale': coarse_scale, 'maxPixels': 1e8})
    except Exception as e:
        out['error'] = f'load_all_classifications failed: {e}'
        return out

    out_dir = base / 'lulc' / city
    for name, img in classifications.items():
        try:
            fname = f"{name}_{year}_coarse"
            p = _download_image_geturl(img, region, coarse_scale, out_dir, fname)
            out['generated'][name] = str(p) if p else None
            time.sleep(1)
        except Exception as e:
            out['generated'][name] = {'error': str(e)}
        # compute categorical uncertainty (histogram, entropy) and save
        try:
            cat_unc = error_assessment.compute_categorical_uncertainty(img, region, scale=coarse_scale, maxPixels=int(1e8))
            out.setdefault('uncertainty', {})[name] = cat_unc
        except Exception:
            out.setdefault('uncertainty', {})[name] = None
    return out


def generate_highres_local(base: Path, city: str, year: int, highres_scale: int = 30) -> Dict[str, Any]:
    """Generate high-resolution LULC maps locally (30m) - WARNING: Large files!"""
    out: Dict[str, Any] = {'city': city, 'year': year, 'generated': {}}
    city_info = UZBEKISTAN_CITIES.get(city)
    if not city_info:
        out['error'] = 'city not found'
        return out
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    region = center.buffer(city_info['buffer_m']).bounds()
    try:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        classifications = classification.load_all_classifications_highres(year, region, start_date, end_date, optimal_scales={'scale': highres_scale, 'maxPixels': 1e13})
    except Exception as e:
        out['error'] = f'load_all_classifications_highres failed: {e}'
        return out

    out_dir = base / 'lulc_highres' / city
    for name, img in classifications.items():
        try:
            fname = f"{name}_{year}_highres"
            p = _download_image_geturl(img, region, highres_scale, out_dir, fname)
            out['generated'][name] = str(p) if p else None
            time.sleep(2)  # Longer sleep for larger downloads
        except Exception as e:
            out['generated'][name] = {'error': str(e)}
        try:
            cat_unc = error_assessment.compute_categorical_uncertainty(img, region, scale=highres_scale, maxPixels=int(1e9))
            out.setdefault('uncertainty', {})[name] = cat_unc
        except Exception:
            out.setdefault('uncertainty', {})[name] = None
    return out


def generate_detailed_drive(base: Path, city: str, year: int, drive_scale: int = 30, drive_folder: str = 'LULC_Exports') -> Dict[str, Any]:
    out: Dict[str, Any] = {'city': city, 'year': year, 'drive_tasks': {}}
    city_info = UZBEKISTAN_CITIES.get(city)
    if not city_info:
        out['error'] = 'city not found'
        return out
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    region = center.buffer(city_info['buffer_m']).bounds()
    try:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        classifications = classification.load_all_classifications_highres(year, region, start_date, end_date, optimal_scales={'scale': drive_scale, 'maxPixels': 1e13})
    except Exception as e:
        out['error'] = f'load_all_classifications_highres failed: {e}'
        return out

    for name, img in classifications.items():
        try:
            desc = f"LULC_{city}_{year}_{name}"
            task = ee.batch.Export.image.toDrive(image=img, description=desc, folder=drive_folder, fileNamePrefix=desc, region=region.bounds().getInfo()['coordinates'], scale=drive_scale, crs='EPSG:4326', maxPixels=1e13)
            task.start()
            out['drive_tasks'][name] = getattr(task, 'id', None)
            time.sleep(0.5)
        except Exception as e:
            out['drive_tasks'][name] = {'error': str(e)}
    return out


def analyze_changes(base: Path, city: str, start_year: int, end_year: int) -> Dict[str, Any]:
    try:
        res = classification.analyze_esri_landcover_changes(city, start_year=start_year, end_year=end_year)
        out_dir = base / 'lulc_analysis' / city
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / f'{city}_landcover_changes_{start_year}_{end_year}.json', 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=2)
        return {'city': city, 'result_file': str(out_dir / f'{city}_landcover_changes_{start_year}_{end_year}.json')}
    except Exception as e:
        return {'city': city, 'error': str(e)}
