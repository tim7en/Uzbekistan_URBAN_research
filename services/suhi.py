"""SUHI computation functions (pixel and zonal)."""
import ee
import numpy as np
from typing import Dict, Any
from .utils import GEE_CONFIG, ANALYSIS_CONFIG
from .utils import rate_limiter
from typing import Any, Dict
import ee


def compute_pixel_suhi(urban_mask, rural_mask, lst_image, zones):
    band = lst_image.bandNames().get(0)
    stats = lst_image.updateMask(rural_mask).reduceRegion(
        reducer=ee.Reducer.mean(), geometry=zones['rural_ring'], scale=GEE_CONFIG.get('scale_modis', ANALYSIS_CONFIG['target_resolution_m']), maxPixels=GEE_CONFIG['max_pixels'], bestEffort=GEE_CONFIG['best_effort'])
    rural_mean = ee.Number(stats.get(ee.String(band)))
    rural_reference = ee.Image.constant(rural_mean).rename('rural_mean').toFloat()
    return (lst_image.select([ee.String(band)]).toFloat().subtract(rural_reference).updateMask(urban_mask).rename('SUHI_pixel'))


def compute_zonal_suhi(zones: Dict, lst_image: ee.Image, classifications: Dict) -> Dict[str, Any]:
    if 'esri' in classifications and len(classifications) > 1:
        w = ANALYSIS_CONFIG['esri_weight']
        urban_mask = classifications['esri'].multiply(w)
        other_w = (1-w)/(len(classifications)-1)
        for name,img in classifications.items():
            if name != 'esri':
                urban_mask = urban_mask.add(img.multiply(other_w))
    else:
        weight = 1.0 / max(1, len(classifications))
        urban_mask = ee.Image.constant(0)
        for img in classifications.values():
            urban_mask = urban_mask.add(img.multiply(weight))
    urban_mask = urban_mask.gt(0.5)
    rural_mask = urban_mask.Not()
    if lst_image is None:
        return {'error':'No LST data available'}
    band = 'LST_Day_MODIS'
    scale = GEE_CONFIG['scale_modis']
    try:
        urban_mean = lst_image.select(band).updateMask(urban_mask).reduceRegion(reducer=ee.Reducer.mean(), geometry=zones['urban_core'], scale=scale, maxPixels=GEE_CONFIG['max_pixels'], bestEffort=True, tileScale=4)
        urban_stdDev = lst_image.select(band).updateMask(urban_mask).reduceRegion(reducer=ee.Reducer.stdDev(), geometry=zones['urban_core'], scale=scale, maxPixels=GEE_CONFIG['max_pixels'], bestEffort=True, tileScale=4)
        urban_count = lst_image.select(band).updateMask(urban_mask).reduceRegion(reducer=ee.Reducer.count(), geometry=zones['urban_core'], scale=scale, maxPixels=GEE_CONFIG['max_pixels'], bestEffort=True, tileScale=4)
        rural_mean = lst_image.select(band).updateMask(rural_mask).reduceRegion(reducer=ee.Reducer.mean(), geometry=zones['rural_ring'], scale=scale, maxPixels=GEE_CONFIG['max_pixels'], bestEffort=True, tileScale=4)
        rural_stdDev = lst_image.select(band).updateMask(rural_mask).reduceRegion(reducer=ee.Reducer.stdDev(), geometry=zones['rural_ring'], scale=scale, maxPixels=GEE_CONFIG['max_pixels'], bestEffort=True, tileScale=4)
        rural_count = lst_image.select(band).updateMask(rural_mask).reduceRegion(reducer=ee.Reducer.count(), geometry=zones['rural_ring'], scale=scale, maxPixels=GEE_CONFIG['max_pixels'], bestEffort=True, tileScale=4)
        urban_stats = {f'{band}_mean': urban_mean.get(band).getInfo(), f'{band}_stdDev': urban_stdDev.get(band).getInfo(), f'{band}_count': urban_count.get(band).getInfo()}
        rural_stats = {f'{band}_mean': rural_mean.get(band).getInfo(), f'{band}_stdDev': rural_stdDev.get(band).getInfo(), f'{band}_count': rural_count.get(band).getInfo()}
        return {'urban_stats': urban_stats, 'rural_stats': rural_stats}
    except Exception as e:
        try:
            fallback_scale = scale * 2
            urban_mean = lst_image.select(band).updateMask(urban_mask).reduceRegion(reducer=ee.Reducer.mean(), geometry=zones['urban_core'], scale=fallback_scale, maxPixels=1e7, bestEffort=True, tileScale=8)
            rural_mean = lst_image.select(band).updateMask(rural_mask).reduceRegion(reducer=ee.Reducer.mean(), geometry=zones['rural_ring'], scale=fallback_scale, maxPixels=1e7, bestEffort=True, tileScale=8)
            urban_stats = {f'{band}_mean': urban_mean.get(band).getInfo(), f'{band}_stdDev': 0, f'{band}_count': 0}
            rural_stats = {f'{band}_mean': rural_mean.get(band).getInfo(), f'{band}_stdDev': 0, f'{band}_count': 0}
            return {'urban_stats': urban_stats, 'rural_stats': rural_stats}
        except Exception as fallback_error:
            return {'error': f'Computation failed: {str(e)}'}


def calculate_error_metrics(urban_stats: Dict, rural_stats: Dict) -> Dict:
    import numpy as np
    urban_mean = urban_stats.get('LST_Day_MODIS_mean', None)
    urban_std = urban_stats.get('LST_Day_MODIS_stdDev', 0)
    urban_count = urban_stats.get('LST_Day_MODIS_count', 0)
    rural_mean = rural_stats.get('LST_Day_MODIS_mean', None)
    rural_std = rural_stats.get('LST_Day_MODIS_stdDev', 0)
    rural_count = rural_stats.get('LST_Day_MODIS_count', 0)
    if urban_mean is None or rural_mean is None:
        return {'error': 'Insufficient data'}
    suhi = float(urban_mean) - float(rural_mean)
    if urban_count > 0 and rural_count > 0:
        urban_se = float(urban_std) / np.sqrt(float(urban_count))
        rural_se = float(rural_std) / np.sqrt(float(rural_count))
        suhi_se = np.sqrt(urban_se**2 + rural_se**2)
        ci_95 = 1.96 * suhi_se
        relative_error = (suhi_se / abs(suhi) * 100) if suhi != 0 else float('inf')
    else:
        suhi_se = float('inf'); ci_95 = float('inf'); relative_error = float('inf')
    return {
        'suhi': suhi,
        'suhi_se': suhi_se,
        'ci_95_lower': suhi - ci_95,
        'ci_95_upper': suhi + ci_95,
        'relative_error_pct': relative_error,
        'urban_pixels': int(urban_count) if urban_count else 0,
        'rural_pixels': int(rural_count) if rural_count else 0,
        'urban_std': float(urban_std),
        'rural_std': float(rural_std)
    }


def compute_day_night_suhi(zones: Dict[str, ee.Geometry], lst_day: ee.Image, lst_night: ee.Image, classifications: Dict[str, ee.Image]) -> Dict[str, Any]:
    print(f"   📊 Computing day vs night SUHI analysis...")
    rate_limiter.wait()
    if 'esri' in classifications and len(classifications) > 1:
        w = ANALYSIS_CONFIG['esri_weight']
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
    urban_mask = urban_mask.gt(0.5)
    rural_mask = urban_mask.Not()
    scale = GEE_CONFIG['scale_modis']
    results = {}
    for time_period, lst_image in [('day', lst_day), ('night', lst_night)]:
        if lst_image is None:
            results[time_period] = {'error': f'No {time_period} LST data available'}
            continue
        try:
            band_names = lst_image.bandNames().getInfo()
            band_name = band_names[0] if band_names else f'LST_{time_period.title()}_MODIS'
            lst_celsius = lst_image.select(band_name).multiply(0.02).subtract(273.15)
            urban_stats = lst_celsius.updateMask(urban_mask).reduceRegion(reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), None, True).combine(ee.Reducer.count(), None, True), geometry=zones['urban_core'], scale=scale, maxPixels=GEE_CONFIG['max_pixels'], bestEffort=True, tileScale=4)
            rural_stats = lst_celsius.updateMask(rural_mask).reduceRegion(reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), None, True).combine(ee.Reducer.count(), None, True), geometry=zones['rural_ring'], scale=scale, maxPixels=GEE_CONFIG['max_pixels'], bestEffort=True, tileScale=4)
            urban_mean = urban_stats.get(f'{band_name}_mean').getInfo()
            urban_std = urban_stats.get(f'{band_name}_stdDev').getInfo()
            urban_count = urban_stats.get(f'{band_name}_count').getInfo()
            rural_mean = rural_stats.get(f'{band_name}_mean').getInfo()
            rural_std = rural_stats.get(f'{band_name}_stdDev').getInfo()
            rural_count = rural_stats.get(f'{band_name}_count').getInfo()
            suhi = urban_mean - rural_mean if urban_mean and rural_mean else None
            results[time_period] = {'urban_mean': urban_mean, 'urban_std': urban_std, 'urban_count': urban_count, 'rural_mean': rural_mean, 'rural_std': rural_std, 'rural_count': rural_count, 'suhi': suhi, 'band': band_name}
        except Exception as e:
            print(f"     ⚠️ Error computing {time_period} SUHI: {e}")
            results[time_period] = {'error': str(e)}
    if 'day' in results and 'night' in results and 'error' not in results['day'] and 'error' not in results['night']:
        day_suhi = results['day']['suhi']; night_suhi = results['night']['suhi']
        if day_suhi is not None and night_suhi is not None:
            results['day_night_difference'] = {'suhi_difference': day_suhi - night_suhi, 'day_stronger': day_suhi > night_suhi, 'magnitude_ratio': day_suhi / night_suhi if night_suhi != 0 else float('inf')}
    return results
