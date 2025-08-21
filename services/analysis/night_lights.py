"""
Night lights analysis for urban research
"""

import ee
import os
import json
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from ..config import UZBEKISTAN_CITIES, GEEConfig
from ..utils.gee_utils import rate_limiter


def get_viirs_collection(year: int) -> ee.ImageCollection:
    """Get VIIRS night lights collection for a specific year"""
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    return (ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG")
            .filterDate(start_date, end_date)
            .select('avg_rad'))


def compute_global_normalization_params(region: ee.Geometry) -> Dict:
    """Compute global normalization parameters for consistent scaling"""
    try:
        # Get early and late year collections
        early_collection = get_viirs_collection(2017)
        late_collection = get_viirs_collection(2024)
        
        # Get median composites
        early_composite = early_collection.median()
        late_composite = late_collection.median()
        
        # Compute statistics across the region
        early_stats = early_composite.reduceRegion(
            reducer=ee.Reducer.minMax(),
            geometry=region,
            scale=500,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        
        late_stats = late_composite.reduceRegion(
            reducer=ee.Reducer.minMax(),
            geometry=region,
            scale=500,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        
        # Find global min/max for consistent normalization
        global_min = min(
            early_stats.get('avg_rad_min', 0),
            late_stats.get('avg_rad_min', 0)
        )
        global_max = max(
            early_stats.get('avg_rad_max', 1),
            late_stats.get('avg_rad_max', 1)
        )
        
        return {
            'global_min': global_min,
            'global_max': global_max,
            'early_stats': early_stats,
            'late_stats': late_stats
        }
        
    except Exception as e:
        print(f"   ⚠️ Global normalization failed: {e}")
        return {'global_min': 0, 'global_max': 1}


def enhance_contrast(image: ee.Image, region: ee.Geometry) -> ee.Image:
    """Enhance contrast using histogram stretching"""
    # Compute local statistics
    stats = image.reduceRegion(
        reducer=ee.Reducer.percentile([2, 98]),
        geometry=region,
        scale=500,
        maxPixels=1e8,
        bestEffort=True
    )
    
    # Get percentile values
    p2 = ee.Number(stats.get('avg_rad_p2', 0))
    p98 = ee.Number(stats.get('avg_rad_p98', 1))
    
    # Stretch to 0-1 range
    stretched = image.subtract(p2).divide(p98.subtract(p2)).clamp(0, 1)
    
    return stretched


def analyze_city_night_lights(city_name: str, year_early: int, year_late: int, 
                            output_dir: Path, gee_config: GEEConfig) -> Dict:
    """
    Analyze night lights for a specific city over time period
    """
    try:
        rate_limiter.wait()
        
        print(f"   🌙 Analyzing {city_name} night lights ({year_early}-{year_late})...")
        
        # Get city info
        city_info = UZBEKISTAN_CITIES[city_name]
        point = ee.Geometry.Point([city_info['lon'], city_info['lat']])
        city_area = point.buffer(city_info['buffer_m'])
        
        # Get night lights data
        early_collection = get_viirs_collection(year_early)
        late_collection = get_viirs_collection(year_late)
        
        if early_collection.size().getInfo() == 0 or late_collection.size().getInfo() == 0:
            return {'error': 'No night lights data available'}
        
        # Create median composites
        early_composite = early_collection.median().clip(city_area)
        late_composite = late_collection.median().clip(city_area)
        
        # Calculate statistics
        early_stats = early_composite.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.stdDev(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.sum(),
                sharedInputs=True
            ),
            geometry=city_area,
            scale=gee_config.scale,
            maxPixels=gee_config.max_pixels,
            bestEffort=gee_config.best_effort
        ).getInfo()
        
        late_stats = late_composite.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.stdDev(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.sum(),
                sharedInputs=True
            ),
            geometry=city_area,
            scale=gee_config.scale,
            maxPixels=gee_config.max_pixels,
            bestEffort=gee_config.best_effort
        ).getInfo()
        
        # Calculate change metrics
        early_mean = early_stats.get('avg_rad_mean', 0)
        late_mean = late_stats.get('avg_rad_mean', 0)
        early_sum = early_stats.get('avg_rad_sum', 0)
        late_sum = late_stats.get('avg_rad_sum', 0)
        
        change_absolute = late_mean - early_mean
        change_percent = ((late_mean - early_mean) / early_mean * 100) if early_mean > 0 else 0
        
        # Export raster files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Early year raster
        early_filename = f"{city_name.lower()}_night_lights_{year_early}_{timestamp}"
        early_task = ee.batch.Export.image.toDrive(
            image=early_composite,
            description=early_filename,
            scale=gee_config.scale,
            region=city_area,
            maxPixels=1e13,
            crs='EPSG:4326'
        )
        early_task.start()
        
        # Late year raster  
        late_filename = f"{city_name.lower()}_night_lights_{year_late}_{timestamp}"
        late_task = ee.batch.Export.image.toDrive(
            image=late_composite,
            description=late_filename,
            scale=gee_config.scale,
            region=city_area,
            maxPixels=1e13,
            crs='EPSG:4326'
        )
        late_task.start()
        
        # Change raster
        change_image = late_composite.subtract(early_composite)
        change_filename = f"{city_name.lower()}_night_lights_change_{year_early}_{year_late}_{timestamp}"
        change_task = ee.batch.Export.image.toDrive(
            image=change_image,
            description=change_filename,
            scale=gee_config.scale,
            region=city_area,
            maxPixels=1e13,
            crs='EPSG:4326'
        )
        change_task.start()
        
        result = {
            'city': city_name,
            'year_early': year_early,
            'year_late': year_late,
            'early_mean_radiance': early_mean,
            'late_mean_radiance': late_mean,
            'early_total_radiance': early_sum,
            'late_total_radiance': late_sum,
            'change_absolute': change_absolute,
            'change_percent': change_percent,
            'early_std': early_stats.get('avg_rad_stdDev', 0),
            'late_std': late_stats.get('avg_rad_stdDev', 0),
            'raster_exports': {
                'early': early_filename,
                'late': late_filename,
                'change': change_filename
            },
            'task_ids': {
                'early': early_task.id,
                'late': late_task.id,
                'change': change_task.id
            }
        }
        
        # Save individual city results
        city_file = output_dir / f"{city_name.lower()}_night_lights_analysis.json"
        with open(city_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"   ✅ {city_name} night lights analysis complete")
        return result
        
    except Exception as e:
        error_result = {
            'city': city_name,
            'error': str(e)
        }
        print(f"   ❌ {city_name} night lights analysis failed: {e}")
        return error_result


def analyze_country_night_lights(year_early: int, year_late: int, 
                               output_dir: Path, gee_config: GEEConfig) -> Dict:
    """
    Analyze night lights for entire country
    """
    try:
        print(f"   🌍 Analyzing country-wide night lights ({year_early}-{year_late})...")
        
        # Get Uzbekistan geometry
        uzbekistan = ee.FeatureCollection("FAO/GAUL/2015/level0").filter(
            ee.Filter.eq("ADM0_NAME", "Uzbekistan")
        ).geometry()
        
        # Get collections
        early_collection = get_viirs_collection(year_early)
        late_collection = get_viirs_collection(year_late)
        
        # Create composites
        early_composite = early_collection.median().clip(uzbekistan)
        late_composite = late_collection.median().clip(uzbekistan)
        
        # Calculate statistics
        early_stats = early_composite.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.sum(),
                sharedInputs=True
            ),
            geometry=uzbekistan,
            scale=gee_config.scale,
            maxPixels=gee_config.max_pixels,
            bestEffort=gee_config.best_effort
        ).getInfo()
        
        late_stats = late_composite.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.sum(),
                sharedInputs=True
            ),
            geometry=uzbekistan,
            scale=gee_config.scale,
            maxPixels=gee_config.max_pixels,
            bestEffort=gee_config.best_effort
        ).getInfo()
        
        # Export country-level rasters
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Country early year
        country_early_filename = f"uzbekistan_night_lights_{year_early}_{timestamp}"
        country_early_task = ee.batch.Export.image.toDrive(
            image=early_composite,
            description=country_early_filename,
            scale=gee_config.scale,
            region=uzbekistan,
            maxPixels=1e13,
            crs='EPSG:4326'
        )
        country_early_task.start()
        
        # Country late year
        country_late_filename = f"uzbekistan_night_lights_{year_late}_{timestamp}"
        country_late_task = ee.batch.Export.image.toDrive(
            image=late_composite,
            description=country_late_filename,
            scale=gee_config.scale,
            region=uzbekistan,
            maxPixels=1e13,
            crs='EPSG:4326'
        )
        country_late_task.start()
        
        result = {
            'scope': 'country',
            'year_early': year_early,
            'year_late': year_late,
            'early_mean_radiance': early_stats.get('avg_rad_mean', 0),
            'late_mean_radiance': late_stats.get('avg_rad_mean', 0),
            'early_total_radiance': early_stats.get('avg_rad_sum', 0),
            'late_total_radiance': late_stats.get('avg_rad_sum', 0),
            'raster_exports': {
                'early': country_early_filename,
                'late': country_late_filename
            },
            'task_ids': {
                'early': country_early_task.id,
                'late': country_late_task.id
            }
        }
        
        return result
        
    except Exception as e:
        return {'error': f'Country analysis failed: {str(e)}'}


def run_comprehensive_night_lights_analysis(cities: List[str], year_early: int, year_late: int,
                                           output_dir: Path, gee_config: GEEConfig) -> Dict:
    """
    Run comprehensive night lights analysis for cities and country
    """
    print(f"\n🌙 NIGHT LIGHTS ANALYSIS ({year_early}-{year_late})")
    print("="*60)
    
    results = {
        'analysis_type': 'night_lights',
        'year_early': year_early,
        'year_late': year_late,
        'timestamp': datetime.now().isoformat(),
        'cities': [],
        'country': None
    }
    
    # Analyze each city
    for city in cities:
        city_result = analyze_city_night_lights(city, year_early, year_late, output_dir, gee_config)
        results['cities'].append(city_result)
    
    # Analyze country
    country_result = analyze_country_night_lights(year_early, year_late, output_dir, gee_config)
    results['country'] = country_result
    
    # Save comprehensive results
    results_file = output_dir / f"comprehensive_night_lights_analysis_{year_early}_{year_late}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✅ Night lights analysis complete - results saved to {results_file}")
    return results