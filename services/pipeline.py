"""High-level pipeline that composes service modules into a runnable analysis."""
from . import gee, classification, temperature, vegetation, suhi, visualization, reporting, utils
from typing import Dict, Any


def run_comprehensive_analysis(city_name: str, year: int) -> Dict[str, Any]:
    print(f"\n🔍 Running pipeline for {city_name} {year}")
    city_info = utils.UZBEKISTAN_CITIES[city_name]
    optimal_scales = utils.get_optimal_scale_for_city(city_name, 'detailed_validation')
    zones = utils.create_analysis_zones(city_info)
    start_date = f'{year}-01-01'; end_date = f'{year}-12-31'
    classifications = classification.load_all_classifications(year, zones['full_extent'], start_date, end_date, optimal_scales)
    try:
        accuracy_metrics = classification.assess_classification_accuracy(classifications, zones['urban_core'])
    except Exception:
        accuracy_metrics = {'error': 'Accuracy assessment failed'}
    try:
        modis_lst = temperature.load_modis_lst(start_date, end_date, zones['full_extent'])
    except Exception:
        modis_lst = None
    try:
        vegetation_img = vegetation.calculate_vegetation_indices(start_date, end_date, zones['full_extent'], target_scale=int(optimal_scales.get('scale_landsat', 30)))
    except Exception:
        vegetation_img = None
    try:
        # adjust GEE_CONFIG temporarily
        original = utils.GEE_CONFIG.copy()
        utils.GEE_CONFIG.update({'scale': optimal_scales['scale'], 'max_pixels': optimal_scales['maxPixels']})
        suhi_stats = suhi.compute_zonal_suhi(zones, modis_lst, classifications)
        utils.GEE_CONFIG.update(original)
    except Exception as e:
        suhi_stats = {'error': str(e)}
    if 'urban_stats' in suhi_stats and 'rural_stats' in suhi_stats and isinstance(suhi_stats['urban_stats'], dict):
        try:
            error_metrics = suhi.calculate_error_metrics(suhi_stats['urban_stats'], suhi_stats['rural_stats'])
        except Exception:
            error_metrics = {'error': 'Error metrics failed'}
    else:
        error_metrics = {'error': 'SUHI computation failed'}
    # Day/night
    day_night_analysis = {}
    if modis_lst is not None:
        try:
            # try to split day/night bands
            band_names = modis_lst.bandNames().getInfo()
            day_bands = [b for b in band_names if 'Day' in b and 'LST' in b]
            night_bands = [b for b in band_names if 'Night' in b and 'LST' in b]
            if day_bands and night_bands:
                lst_day = modis_lst.select(day_bands[0]).rename('LST_Day_MODIS')
                lst_night = modis_lst.select(night_bands[0]).rename('LST_Night_MODIS')
                day_night_analysis = suhi.compute_day_night_suhi(zones, lst_day, lst_night, classifications)
        except Exception:
            day_night_analysis = {'error': 'Day/night analysis failed'}
    landcover_changes = {}
    try:
        landcover_changes = classification.analyze_esri_landcover_changes(city_name, 2017, min(2024, year))
    except Exception:
        landcover_changes = {'error': 'Landcover analysis failed'}
    veg_stats = {'note': 'Vegetation skipped' if vegetation_img is None else 'computed'}
    results = {
        'city': city_name,
        'year': year,
        'processing_scale': optimal_scales['scale'],
        'classifications_available': list(classifications.keys()),
        'accuracy_assessment': accuracy_metrics if isinstance(accuracy_metrics, dict) else {},
        'suhi_analysis': error_metrics,
        'day_night_analysis': day_night_analysis,
        'landcover_changes': landcover_changes,
        'vegetation_indices': veg_stats,
        'urban_stats': suhi_stats.get('urban_stats', {}),
        'rural_stats': suhi_stats.get('rural_stats', {}),
    }
    return results
