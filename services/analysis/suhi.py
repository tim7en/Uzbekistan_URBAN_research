"""
Surface Urban Heat Island (SUHI) analysis
"""

import ee
import json
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from ..config import UZBEKISTAN_CITIES, DATASETS, GEEConfig
from ..utils.gee_utils import rate_limiter
from ..data_processing.temperature import load_modis_lst, calculate_suhi, export_raster


def create_urban_rural_masks(city_name: str, geometry: ee.Geometry, 
                           gee_config: GEEConfig) -> Dict[str, ee.Image]:
    """
    Create urban and rural masks for SUHI analysis
    """
    try:
        # Load ESRI land cover
        esri_collection = ee.ImageCollection(DATASETS["esri_lulc"])
        
        # Get most recent ESRI image
        esri_image = esri_collection.sort('system:time_start', False).first()
        
        # Urban mask (Built class = 7)
        urban_mask = esri_image.eq(7).selfMask()
        
        # Rural mask (exclude built, water, clouds)
        rural_classes = [2, 3, 5, 6, 8, 11]  # Trees, Grass, Crops, Scrub, Bare, Rangeland
        rural_mask = esri_image.remap(
            from_list=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            to_list=[0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1]
        ).selfMask()
        
        # Create rural buffer around city
        city_info = UZBEKISTAN_CITIES[city_name]
        rural_buffer_distance = 25000  # 25km buffer for rural reference
        
        city_point = ee.Geometry.Point([city_info['lon'], city_info['lat']])
        rural_ring = city_point.buffer(rural_buffer_distance).difference(
            city_point.buffer(city_info['buffer_m'])
        )
        
        # Clip masks to appropriate areas
        urban_mask_clipped = urban_mask.clip(geometry)
        rural_mask_clipped = rural_mask.clip(rural_ring)
        
        return {
            'urban_mask': urban_mask_clipped,
            'rural_mask': rural_mask_clipped,
            'urban_geometry': geometry,
            'rural_geometry': rural_ring
        }
        
    except Exception as e:
        print(f"   ❌ Mask creation failed: {e}")
        return None


def analyze_city_suhi(city_name: str, year: int, output_dir: Path, 
                     gee_config: GEEConfig) -> Dict:
    """
    Analyze SUHI for a specific city and year
    """
    try:
        rate_limiter.wait()
        
        print(f"   🔥 Analyzing {city_name} SUHI for {year}...")
        
        # Set date range for warm months
        start_date = f"{year}-06-01"
        end_date = f"{year}-08-31"
        
        # Get city geometry
        city_info = UZBEKISTAN_CITIES[city_name]
        city_point = ee.Geometry.Point([city_info['lon'], city_info['lat']])
        city_geometry = city_point.buffer(city_info['buffer_m'])
        
        # Create urban/rural masks
        masks = create_urban_rural_masks(city_name, city_geometry, gee_config)
        if not masks:
            return {'error': 'Failed to create urban/rural masks'}
        
        # Load temperature data
        lst_image = load_modis_lst(start_date, end_date, city_geometry, gee_config)
        if not lst_image:
            return {'error': 'Failed to load temperature data'}
        
        # Calculate SUHI
        suhi_result = calculate_suhi(
            lst_image, 
            masks['urban_mask'], 
            masks['rural_mask'], 
            gee_config
        )
        
        if 'error' in suhi_result:
            return suhi_result
        
        # Create SUHI map
        suhi_map = lst_image.select('LST_Day').subtract(
            lst_image.select('LST_Day').reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=masks['rural_geometry'],
                scale=gee_config.scale_modis,
                maxPixels=gee_config.max_pixels,
                bestEffort=gee_config.best_effort
            ).get('LST_Day')
        )
        
        # Export SUHI raster
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suhi_filename = f"{city_name.lower()}_suhi_map_{year}_{timestamp}"
        
        export_success = export_raster(
            suhi_map.clip(city_geometry),
            city_geometry,
            suhi_filename,
            gee_config.scale_modis,
            output_dir
        )
        
        # Export urban temperature raster
        urban_temp_filename = f"{city_name.lower()}_urban_temperature_{year}_{timestamp}"
        export_raster(
            lst_image.select('LST_Day').clip(city_geometry),
            city_geometry,
            urban_temp_filename,
            gee_config.scale_modis,
            output_dir
        )
        
        # Compile results
        result = {
            'city': city_name,
            'year': year,
            'analysis_period': f"{start_date} to {end_date}",
            'suhi_intensity_celsius': suhi_result['suhi_intensity'],
            'urban_temperature_celsius': suhi_result['urban_temperature'],
            'rural_temperature_celsius': suhi_result['rural_temperature'],
            'urban_std_celsius': suhi_result['urban_std'],
            'rural_std_celsius': suhi_result['rural_std'],
            'urban_pixel_count': suhi_result['urban_pixel_count'],
            'rural_pixel_count': suhi_result['rural_pixel_count'],
            'processing_scale_m': gee_config.scale_modis,
            'raster_exports': {
                'suhi_map': suhi_filename,
                'urban_temperature': urban_temp_filename
            },
            'export_success': export_success
        }
        
        # Save individual city results
        city_file = output_dir / f"{city_name.lower()}_suhi_analysis_{year}.json"
        with open(city_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"   ✅ {city_name} SUHI analysis complete (SUHI: {suhi_result['suhi_intensity']:.2f}°C)")
        return result
        
    except Exception as e:
        error_result = {
            'city': city_name,
            'year': year,
            'error': str(e)
        }
        print(f"   ❌ {city_name} SUHI analysis failed: {e}")
        return error_result


def analyze_annual_suhi_trends(city_name: str, years: List[int], 
                             output_dir: Path, gee_config: GEEConfig) -> Dict:
    """
    Analyze SUHI trends over multiple years for a city
    """
    print(f"   📈 Analyzing {city_name} SUHI trends ({years[0]}-{years[-1]})...")
    
    trends_data = {
        'city': city_name,
        'analysis_years': years,
        'annual_results': [],
        'trend_statistics': {}
    }
    
    suhi_values = []
    valid_years = []
    
    # Analyze each year
    for year in years:
        annual_result = analyze_city_suhi(city_name, year, output_dir, gee_config)
        trends_data['annual_results'].append(annual_result)
        
        # Collect valid SUHI values for trend analysis
        if 'error' not in annual_result and 'suhi_intensity_celsius' in annual_result:
            suhi_values.append(annual_result['suhi_intensity_celsius'])
            valid_years.append(year)
    
    # Calculate trend statistics
    if len(suhi_values) >= 3:
        try:
            # Import scipy for trend analysis if available
            from scipy import stats
            
            # Calculate linear trend
            slope, intercept, r_value, p_value, std_err = stats.linregress(valid_years, suhi_values)
            
            trends_data['trend_statistics'] = {
                'trend_slope_celsius_per_year': slope,
                'trend_intercept': intercept,
                'correlation_coefficient': r_value,
                'p_value': p_value,
                'standard_error': std_err,
                'mean_suhi': sum(suhi_values) / len(suhi_values),
                'min_suhi': min(suhi_values),
                'max_suhi': max(suhi_values),
                'suhi_range': max(suhi_values) - min(suhi_values),
                'valid_years_count': len(valid_years)
            }
            
        except ImportError:
            # Basic statistics without scipy
            trends_data['trend_statistics'] = {
                'mean_suhi': sum(suhi_values) / len(suhi_values),
                'min_suhi': min(suhi_values),
                'max_suhi': max(suhi_values),
                'suhi_range': max(suhi_values) - min(suhi_values),
                'valid_years_count': len(valid_years),
                'note': 'Advanced trend analysis requires scipy'
            }
    
    # Save trends analysis
    trends_file = output_dir / f"{city_name.lower()}_suhi_trends_{years[0]}_{years[-1]}.json"
    with open(trends_file, 'w') as f:
        json.dump(trends_data, f, indent=2)
    
    return trends_data


def run_comprehensive_suhi_analysis(cities: List[str], years: List[int],
                                  output_dir: Path, gee_config: GEEConfig) -> Dict:
    """
    Run comprehensive SUHI analysis for multiple cities and years
    """
    print(f"\n🔥 SUHI ANALYSIS ({years[0]}-{years[-1]})")
    print("="*60)
    
    results = {
        'analysis_type': 'suhi',
        'years': years,
        'timestamp': datetime.now().isoformat(),
        'processing_scale_m': gee_config.scale_modis,
        'cities_analysis': [],
        'summary_statistics': {}
    }
    
    all_suhi_values = []
    
    # Analyze each city
    for city in cities:
        city_trends = analyze_annual_suhi_trends(city, years, output_dir, gee_config)
        results['cities_analysis'].append(city_trends)
        
        # Collect SUHI values for summary statistics
        for annual_result in city_trends['annual_results']:
            if 'error' not in annual_result and 'suhi_intensity_celsius' in annual_result:
                all_suhi_values.append(annual_result['suhi_intensity_celsius'])
    
    # Calculate summary statistics
    if all_suhi_values:
        results['summary_statistics'] = {
            'total_analyses': len(all_suhi_values),
            'mean_suhi_all_cities': sum(all_suhi_values) / len(all_suhi_values),
            'min_suhi_observed': min(all_suhi_values),
            'max_suhi_observed': max(all_suhi_values),
            'suhi_range': max(all_suhi_values) - min(all_suhi_values)
        }
    
    # Save comprehensive results
    results_file = output_dir / f"comprehensive_suhi_analysis_{years[0]}_{years[-1]}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✅ SUHI analysis complete - results saved to {results_file}")
    return results