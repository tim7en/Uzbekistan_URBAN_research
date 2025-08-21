"""Classification dataset loading and accuracy assessment."""
import ee
from typing import Dict, Optional, Any
from .utils import DATASETS, GEE_CONFIG, ESRI_CLASSES


def load_esri_classification(year: int, geometry: ee.Geometry) -> Optional[ee.Image]:
    try:
        esri_lulc_ts = ee.ImageCollection(DATASETS['esri_lulc'])
        if year < 2017:
            year = 2017
        elif year > 2024:
            year = 2024
        try:
            start_date = ee.Date.fromYMD(year,1,1)
            end_date = ee.Date.fromYMD(year,12,31)
            year_composite = esri_lulc_ts.filterDate(start_date,end_date).filterBounds(geometry).mosaic()
            pixel_count = year_composite.select([0]).reduceRegion(
                reducer=ee.Reducer.count(), geometry=geometry, scale=100, maxPixels=1e6)
            count = pixel_count.getInfo()
            if count and list(count.values())[0] > 0:
                return year_composite.clip(geometry)
        except Exception:
            pass
        try:
            year_collection = esri_lulc_ts.filter(ee.Filter.eq('year', year))
            if year_collection.size().getInfo() > 0:
                return year_collection.first().clip(geometry)
        except Exception:
            pass
        try:
            latest_image = esri_lulc_ts.sort('system:time_start', False).first()
            return latest_image.clip(geometry)
        except Exception:
            return None
    except Exception:
        return None


def load_all_classifications(year: int, geometry: ee.Geometry, start_date: str, end_date: str, optimal_scales: Optional[Dict]=None) -> Dict[str, ee.Image]:
    if optimal_scales is None:
        optimal_scales = {'scale': GEE_CONFIG['scale'], 'maxPixels': GEE_CONFIG['max_pixels']}
    scale = int(optimal_scales.get('scale', GEE_CONFIG['scale']) or GEE_CONFIG['scale'])
    # Enforce at least 200 m coarse resolution to avoid very-high-res outputs for local downloads
    if scale < 200:
        scale = 200
    return _load_classifications_at_scale(year, geometry, start_date, end_date, scale)


def load_all_classifications_highres(year: int, geometry: ee.Geometry, start_date: str, end_date: str, optimal_scales: Optional[Dict]=None) -> Dict[str, ee.Image]:
    """Load classifications at high resolution (30m) for Drive exports or local high-res downloads."""
    if optimal_scales is None:
        optimal_scales = {'scale': 30, 'maxPixels': 1e13}
    scale = int(optimal_scales.get('scale', 30) or 30)
    # Allow high resolution for Drive exports
    return _load_classifications_at_scale(year, geometry, start_date, end_date, scale)


def _load_classifications_at_scale(year: int, geometry: ee.Geometry, start_date: str, end_date: str, scale: int) -> Dict[str, ee.Image]:
    """Internal function to load all classifications at the specified scale."""
    classifications = {}

    # ESRI: try to return the full classification and a built-up mask
    try:
        esri = load_esri_classification(year, geometry)
        if esri is not None:
            # For categorical maps, aggregate with mode then reproject to the target coarse scale
            try:
                # Set default projection for reduceResolution (ESRI data is in Web Mercator)
                esri_proj = esri.setDefaultProjection('EPSG:3857', None, 10)
                esri_mode = esri_proj.reduceResolution(ee.Reducer.mode(), maxPixels=1024)
                esri_agg = esri_mode.reproject(crs='EPSG:4326', scale=scale).rename('esri_full')
            except Exception:
                # Fallback to simple reproject if reduceResolution fails
                esri_agg = esri.reproject(crs='EPSG:4326', scale=scale).rename('esri_full')

            classifications['esri_full'] = esri_agg.clip(geometry)
            try:
                classifications['esri_built'] = esri_agg.eq(7).rename('esri_built').clip(geometry)
            except Exception:
                # fallback to computing built mask from original image
                try:
                    classifications['esri_built'] = esri.eq(7).rename('esri_built').clip(geometry)
                except Exception:
                    pass
    except Exception:
        pass

    # Dynamic World: keep 'built' probability band resampled to scale
    try:
        dw_col = ee.ImageCollection(DATASETS['dynamic_world']).filterDate(start_date, end_date).filterBounds(geometry)
        dw_mid = dw_col.select('built').median()
        try:
            # Set default projection for Dynamic World (10m in Web Mercator)
            dw_proj = dw_mid.setDefaultProjection('EPSG:3857', None, 10)
            dw_mean = dw_proj.reduceResolution(ee.Reducer.mean(), maxPixels=1024)
            dw_resampled = dw_mean.reproject(crs='EPSG:4326', scale=scale).rename('dw_built')
        except Exception:
            # fallback: direct reproject
            dw_resampled = dw_mid.reproject(crs='EPSG:4326', scale=scale).rename('dw_built')
        classifications['dynamic_world'] = dw_resampled.clip(geometry)
    except Exception:
        pass

    # GHSL: built-surface percentage and binary mask
    try:
        ghsl = ee.Image(DATASETS['ghsl']).select('built_surface')
        try:
            ghsl_mean = ghsl.divide(100).reduceResolution(ee.Reducer.mean(), maxPixels=1024)
            ghsl_resampled = ghsl_mean.reproject(crs='EPSG:4326', scale=scale).rename('ghsl_pct').clip(geometry)
        except Exception:
            ghsl_resampled = ghsl.divide(100).reproject(crs='EPSG:4326', scale=scale).rename('ghsl_pct').clip(geometry)
        classifications['ghsl_pct'] = ghsl_resampled
        try:
            classifications['ghsl_built'] = ghsl_resampled.gt(0).rename('ghsl_built')
        except Exception:
            pass
    except Exception:
        pass

    # ESA WorldCover: full map + built mask (50)
    try:
        esa = ee.Image(DATASETS['esa_worldcover']).select('Map')
        try:
            esa_mode = esa.reduceResolution(ee.Reducer.mode(), maxPixels=1024)
            esa_map = esa_mode.reproject(crs='EPSG:4326', scale=scale).rename('esa_map').clip(geometry)
        except Exception:
            esa_map = esa.reproject(crs='EPSG:4326', scale=scale).rename('esa_map').clip(geometry)
        classifications['esa_map'] = esa_map
        try:
            classifications['esa_built'] = esa_map.eq(50).rename('esa_built')
        except Exception:
            pass
    except Exception:
        pass

    # MODIS land cover: full map and urban mask (class 13)
    try:
        modis_lc = ee.ImageCollection(DATASETS['modis_lc']).filterDate(f'{year}-01-01', f'{year+1}-01-01').first().select('LC_Type1')
        if modis_lc is not None:
            try:
                modis_mode = modis_lc.reduceResolution(ee.Reducer.mode(), maxPixels=1024)
                modis_map = modis_mode.reproject(crs='EPSG:4326', scale=scale).rename('modis_map').clip(geometry)
            except Exception:
                modis_map = modis_lc.reproject(crs='EPSG:4326', scale=scale).rename('modis_map').clip(geometry)
            classifications['modis_map'] = modis_map
            try:
                classifications['modis_urban'] = modis_map.eq(13).rename('modis_urban')
            except Exception:
                classifications['modis_urban'] = modis_lc.eq(13).rename('modis_urban').clip(geometry)
    except Exception:
        pass

    return classifications


def assess_classification_accuracy(classifications: Dict[str, ee.Image], geometry: ee.Geometry) -> Any:
    if len(classifications) < 2:
        return {'accuracy_assessment': 'Insufficient data'}
    if 'esri' in classifications:
        reference = classifications['esri']
    else:
        classification_list = list(classifications.values())
        if len(classification_list) == 1:
            reference = classification_list[0]
        else:
            try:
                stack = ee.Image.cat(classification_list)
                reference = stack.reduce(ee.Reducer.mode())
            except Exception:
                reference = classification_list[0]
    metrics = {}
    for name, classification in classifications.items():
        if name != 'esri':
            try:
                agreement = classification.eq(reference)
                metrics[f'{name}_agreement'] = agreement.reduceRegion(
                    reducer=ee.Reducer.mean(), geometry=geometry, scale=GEE_CONFIG['scale'], maxPixels=GEE_CONFIG['max_pixels'], bestEffort=GEE_CONFIG['best_effort'])
            except Exception as e:
                metrics[f'{name}_agreement'] = {'error': str(e)}
    return metrics


def analyze_esri_landcover_changes(city_name: str, start_year: int = 2017, end_year: int = 2024) -> Dict[str, Any]:
    """Analyze ESRI landcover changes over time for a city (extracted from monolith)."""
    from .utils import UZBEKISTAN_CITIES, ESRI_CLASSES
    print(f"   🏗️ Analyzing ESRI landcover changes {start_year}-{end_year}...")
    city_info = UZBEKISTAN_CITIES[city_name]
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    buffer_m = city_info['buffer_m']
    region = center.buffer(buffer_m)
    results = {}
    yearly_stats = {}
    for year in range(start_year, end_year + 1):
        try:
            esri_image = load_esri_classification(year, region)
            if esri_image is None:
                print(f"     ⚠️ No ESRI data for {year}")
                continue
            band_names = esri_image.bandNames().getInfo()
            band_name = band_names[0] if band_names else 'b1'
            landcover_stats = esri_image.select(band_name).reduceRegion(
                reducer=ee.Reducer.frequencyHistogram(), geometry=region, scale=30, maxPixels=1e8, bestEffort=True)
            histogram = landcover_stats.get(band_name).getInfo()
            landcover_areas = {}
            total_pixels = sum(histogram.values()) if histogram else 0
            if histogram and total_pixels > 0:
                for class_id, pixel_count in histogram.items():
                    class_name = ESRI_CLASSES.get(int(class_id), f'Unknown_{class_id}')
                    area_km2 = (pixel_count * 30 * 30) / 1000000
                    landcover_areas[class_name] = {'area_km2': area_km2, 'percentage': (pixel_count / total_pixels) * 100}
            yearly_stats[year] = landcover_areas
        except Exception as e:
            print(f"     ⚠️ Error analyzing {year}: {e}")
            yearly_stats[year] = {'error': str(e)}
    if start_year in yearly_stats and end_year in yearly_stats:
        if 'error' not in yearly_stats[start_year] and 'error' not in yearly_stats[end_year]:
            changes = {}
            all_classes = set(yearly_stats[start_year].keys()) | set(yearly_stats[end_year].keys())
            for class_name in all_classes:
                start_area = yearly_stats[start_year].get(class_name, {}).get('area_km2', 0)
                end_area = yearly_stats[end_year].get(class_name, {}).get('area_km2', 0)
                changes[class_name] = {
                    'start_area_km2': start_area,
                    'end_area_km2': end_area,
                    'change_km2': end_area - start_area,
                    'change_percent': ((end_area - start_area) / start_area * 100) if start_area > 0 else float('inf')
                }
            results['landcover_changes'] = changes
    results['yearly_stats'] = yearly_stats
    results['analysis_period'] = f"{start_year}-{end_year}"
    return results
