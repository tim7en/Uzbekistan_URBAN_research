"""
Urban expansion analysis using land cover data
"""

import ee
import json
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from ..config import UZBEKISTAN_CITIES, DATASETS, ESRI_CLASSES, GEEConfig
from ..utils.gee_utils import rate_limiter


def get_esri_landcover_for_year(year: int) -> Optional[ee.Image]:
    """
    Get ESRI land cover image for a specific year
    """
    try:
        collection = ee.ImageCollection(DATASETS["esri_lulc"])
        
        # Filter by year
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        yearly_collection = collection.filterDate(start_date, end_date)
        
        if yearly_collection.size().getInfo() > 0:
            return yearly_collection.first()
        else:
            # If no exact year match, get the closest available
            return collection.sort('system:time_start', False).first()
            
    except Exception as e:
        print(f"   ❌ Failed to load ESRI land cover for {year}: {e}")
        return None


def calculate_landcover_statistics(image: ee.Image, geometry: ee.Geometry, 
                                 gee_config: GEEConfig) -> Dict:
    """
    Calculate land cover class statistics for a given area
    """
    try:
        # Calculate area for each class
        class_areas = {}
        pixel_counts = {}
        
        for class_id, class_name in ESRI_CLASSES.items():
            # Create mask for this class
            class_mask = image.eq(class_id)
            
            # Calculate pixel count
            pixel_count = class_mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=gee_config.scale,
                maxPixels=gee_config.max_pixels,
                bestEffort=gee_config.best_effort
            ).getInfo()
            
            count = pixel_count.get('classification', 0)
            pixel_counts[class_name] = count
            
            # Convert pixels to area (square meters, then to square kilometers)
            area_m2 = count * gee_config.scale * gee_config.scale
            area_km2 = area_m2 / 1000000
            class_areas[class_name] = area_km2
        
        return {
            'class_areas_km2': class_areas,
            'pixel_counts': pixel_counts,
            'total_area_km2': sum(class_areas.values())
        }
        
    except Exception as e:
        return {'error': f'Statistics calculation failed: {str(e)}'}


def analyze_city_urban_expansion(city_name: str, year_start: int, year_end: int,
                               output_dir: Path, gee_config: GEEConfig) -> Dict:
    """
    Analyze urban expansion for a specific city between two years
    """
    try:
        rate_limiter.wait()
        
        print(f"   🏗️ Analyzing {city_name} urban expansion ({year_start}-{year_end})...")
        
        # Get city geometry
        city_info = UZBEKISTAN_CITIES[city_name]
        city_point = ee.Geometry.Point([city_info['lon'], city_info['lat']])
        city_geometry = city_point.buffer(city_info['buffer_m'])
        
        # Get land cover images for both years
        lc_start = get_esri_landcover_for_year(year_start)
        lc_end = get_esri_landcover_for_year(year_end)
        
        if not lc_start or not lc_end:
            return {'error': 'Failed to load land cover data'}
        
        # Clip to city area
        lc_start_clipped = lc_start.clip(city_geometry)
        lc_end_clipped = lc_end.clip(city_geometry)
        
        # Calculate statistics for both years
        stats_start = calculate_landcover_statistics(lc_start_clipped, city_geometry, gee_config)
        stats_end = calculate_landcover_statistics(lc_end_clipped, city_geometry, gee_config)
        
        if 'error' in stats_start or 'error' in stats_end:
            return {'error': 'Statistics calculation failed'}
        
        # Calculate changes
        built_area_start = stats_start['class_areas_km2'].get('Built', 0)
        built_area_end = stats_end['class_areas_km2'].get('Built', 0)
        
        built_change_km2 = built_area_end - built_area_start
        built_change_percent = ((built_area_end - built_area_start) / built_area_start * 100) if built_area_start > 0 else 0
        
        # Create urban change map
        urban_start = lc_start_clipped.eq(7)  # Built class
        urban_end = lc_end_clipped.eq(7)
        
        # Urban expansion areas (new urban)
        urban_expansion = urban_end.subtract(urban_start).eq(1)
        
        # Urban loss areas (former urban)
        urban_loss = urban_start.subtract(urban_end).eq(1)
        
        # Create change map: 0=no change, 1=expansion, 2=loss, 3=stable urban
        change_map = (urban_expansion.multiply(1)
                     .add(urban_loss.multiply(2))
                     .add(urban_start.And(urban_end).multiply(3)))
        
        # Export raster files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export start year land cover
        start_filename = f"{city_name.lower()}_landcover_{year_start}_{timestamp}"
        start_task = ee.batch.Export.image.toDrive(
            image=lc_start_clipped,
            description=start_filename,
            scale=gee_config.scale,
            region=city_geometry,
            maxPixels=1e13,
            crs='EPSG:4326'
        )
        start_task.start()
        
        # Export end year land cover
        end_filename = f"{city_name.lower()}_landcover_{year_end}_{timestamp}"
        end_task = ee.batch.Export.image.toDrive(
            image=lc_end_clipped,
            description=end_filename,
            scale=gee_config.scale,
            region=city_geometry,
            maxPixels=1e13,
            crs='EPSG:4326'
        )
        end_task.start()
        
        # Export urban change map
        change_filename = f"{city_name.lower()}_urban_change_{year_start}_{year_end}_{timestamp}"
        change_task = ee.batch.Export.image.toDrive(
            image=change_map,
            description=change_filename,
            scale=gee_config.scale,
            region=city_geometry,
            maxPixels=1e13,
            crs='EPSG:4326'
        )
        change_task.start()
        
        # Calculate expansion metrics
        expansion_stats = urban_expansion.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=city_geometry,
            scale=gee_config.scale,
            maxPixels=gee_config.max_pixels,
            bestEffort=gee_config.best_effort
        ).getInfo()
        
        loss_stats = urban_loss.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=city_geometry,
            scale=gee_config.scale,
            maxPixels=gee_config.max_pixels,
            bestEffort=gee_config.best_effort
        ).getInfo()
        
        expansion_pixels = expansion_stats.get('classification', 0)
        loss_pixels = loss_stats.get('classification', 0)
        
        expansion_area_km2 = expansion_pixels * gee_config.scale * gee_config.scale / 1000000
        loss_area_km2 = loss_pixels * gee_config.scale * gee_config.scale / 1000000
        
        # Compile results
        result = {
            'city': city_name,
            'year_start': year_start,
            'year_end': year_end,
            'analysis_period_years': year_end - year_start,
            'built_area_start_km2': built_area_start,
            'built_area_end_km2': built_area_end,
            'built_area_change_km2': built_change_km2,
            'built_area_change_percent': built_change_percent,
            'urban_expansion_km2': expansion_area_km2,
            'urban_loss_km2': loss_area_km2,
            'net_urban_change_km2': expansion_area_km2 - loss_area_km2,
            'processing_scale_m': gee_config.scale,
            'landcover_statistics': {
                'start_year': stats_start,
                'end_year': stats_end
            },
            'raster_exports': {
                'landcover_start': start_filename,
                'landcover_end': end_filename,
                'urban_change_map': change_filename
            },
            'task_ids': {
                'start': start_task.id,
                'end': end_task.id,
                'change': change_task.id
            }
        }
        
        # Save individual city results
        city_file = output_dir / f"{city_name.lower()}_urban_expansion_{year_start}_{year_end}.json"
        with open(city_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"   ✅ {city_name} urban expansion complete (Change: {built_change_km2:.2f} km²)")
        return result
        
    except Exception as e:
        error_result = {
            'city': city_name,
            'year_start': year_start,
            'year_end': year_end,
            'error': str(e)
        }
        print(f"   ❌ {city_name} urban expansion analysis failed: {e}")
        return error_result


def run_comprehensive_urban_expansion_analysis(cities: List[str], year_start: int, year_end: int,
                                             output_dir: Path, gee_config: GEEConfig) -> Dict:
    """
    Run comprehensive urban expansion analysis for multiple cities
    """
    print(f"\n🏗️ URBAN EXPANSION ANALYSIS ({year_start}-{year_end})")
    print("="*60)
    
    results = {
        'analysis_type': 'urban_expansion',
        'year_start': year_start,
        'year_end': year_end,
        'analysis_period_years': year_end - year_start,
        'timestamp': datetime.now().isoformat(),
        'processing_scale_m': gee_config.scale,
        'cities_analysis': [],
        'summary_statistics': {}
    }
    
    total_expansion = 0
    valid_cities = 0
    
    # Analyze each city
    for city in cities:
        city_result = analyze_city_urban_expansion(city, year_start, year_end, output_dir, gee_config)
        results['cities_analysis'].append(city_result)
        
        # Accumulate summary statistics
        if 'error' not in city_result:
            total_expansion += city_result['built_area_change_km2']
            valid_cities += 1
    
    # Calculate summary statistics
    if valid_cities > 0:
        results['summary_statistics'] = {
            'total_cities_analyzed': valid_cities,
            'total_urban_expansion_km2': total_expansion,
            'average_expansion_per_city_km2': total_expansion / valid_cities,
            'expansion_rate_km2_per_year': total_expansion / (year_end - year_start)
        }
    
    # Save comprehensive results
    results_file = output_dir / f"comprehensive_urban_expansion_{year_start}_{year_end}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✅ Urban expansion analysis complete - results saved to {results_file}")
    return results