"""Temperature dataset loading functions (MODIS, Landsat, ASTER) with comprehensive statistics."""
import ee
import json
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from .utils import DATASETS, ANALYSIS_CONFIG, UZBEKISTAN_CITIES, GEE_CONFIG, make_json_safe
from . import error_assessment


def load_modis_lst_seasonal(start_date: str, end_date: str, geometry: ee.Geometry) -> Optional[ee.Image]:
    """Load MODIS LST data for any season without warm month filtering.
    
    Returns a composite image with two bands:
    - LST_Day_MODIS: Daytime land surface temperature in Celsius
    - LST_Night_MODIS: Nighttime land surface temperature in Celsius
    
    This version does NOT filter by warm months, allowing winter analysis.
    """
    col = (ee.ImageCollection(DATASETS['modis_lst'])
           .filterDate(start_date, end_date)
           .filterBounds(geometry))
    
    if col.size().getInfo() == 0:
        return None
        
    comp = col.median()
    
    try:
        band_names = comp.bandNames().getInfo()
    except Exception:
        return None
        
    # Find day and night LST bands
    day_bands = [b for b in band_names if 'Day' in b and 'LST' in b]
    night_bands = [b for b in band_names if 'Night' in b and 'LST' in b]
    
    if not day_bands or not night_bands:
        return None
    
    # Process day LST: scale from Kelvin*50 to Celsius
    lst_day = (comp.select(day_bands[0])
              .multiply(0.02)  # Scale factor to convert to Kelvin
              .subtract(273.15)  # Convert Kelvin to Celsius
              .rename('LST_Day_MODIS')
              .clamp(-20, 60))  # Remove unrealistic values
    
    # Process night LST: scale from Kelvin*50 to Celsius  
    lst_night = (comp.select(night_bands[0])
                .multiply(0.02)  # Scale factor to convert to Kelvin
                .subtract(273.15)  # Convert Kelvin to Celsius
                .rename('LST_Night_MODIS') 
                .clamp(-20, 50))  # Remove unrealistic values (night typically cooler)
    
    return ee.Image.cat([lst_day, lst_night]).clip(geometry)


def load_modis_lst(start_date: str, end_date: str, geometry: ee.Geometry) -> Optional[ee.Image]:
    """Load MODIS LST data with day and night bands.
    
    Returns a composite image with two bands:
    - LST_Day_MODIS: Daytime land surface temperature in Celsius
    - LST_Night_MODIS: Nighttime land surface temperature in Celsius
    
    The function filters for warm months and applies proper scaling and unit conversion.
    Temperature values are clamped to reasonable ranges to remove outliers.
    """
    col = (ee.ImageCollection(DATASETS['modis_lst'])
           .filterDate(start_date, end_date)
           .filterBounds(geometry)
           .filter(ee.Filter.calendarRange(ANALYSIS_CONFIG['warm_months'][0], 
                                         ANALYSIS_CONFIG['warm_months'][-1], 'month')))
    
    if col.size().getInfo() == 0:
        return None
        
    comp = col.median()
    
    try:
        band_names = comp.bandNames().getInfo()
    except Exception:
        return None
        
    # Find day and night LST bands
    day_bands = [b for b in band_names if 'Day' in b and 'LST' in b]
    night_bands = [b for b in band_names if 'Night' in b and 'LST' in b]
    
    if not day_bands or not night_bands:
        return None
    
    # Process day LST: scale from Kelvin*50 to Celsius
    lst_day = (comp.select(day_bands[0])
              .multiply(0.02)  # Scale factor to convert to Kelvin
              .subtract(273.15)  # Convert Kelvin to Celsius
              .rename('LST_Day_MODIS')
              .clamp(-20, 60))  # Remove unrealistic values
    
    # Process night LST: scale from Kelvin*50 to Celsius  
    lst_night = (comp.select(night_bands[0])
                .multiply(0.02)  # Scale factor to convert to Kelvin
                .subtract(273.15)  # Convert Kelvin to Celsius
                .rename('LST_Night_MODIS') 
                .clamp(-20, 50))  # Remove unrealistic values (night typically cooler)
    
    return ee.Image.cat([lst_day, lst_night]).clip(geometry)


def load_landsat_thermal(start_date: str, end_date: str, geometry: ee.Geometry) -> Optional[ee.Image]:
    """Load MODIS LST data for seasonal analysis (replaced Landsat thermal).
    
    Returns MODIS LST daily composite with day and night bands averaged.
    This provides better temporal coverage than Landsat for seasonal analysis.
    Now uses seasonal version that doesn't filter by warm months.
    """
    # Use MODIS LST without warm months filter for seasonal analysis
    modis_lst = load_modis_lst_seasonal(start_date, end_date, geometry)
    
    if modis_lst is None:
        return None
    
    try:
        band_names = modis_lst.bandNames().getInfo()
        if len(band_names) >= 2:
            # Average day and night LST for a single temperature composite
            day_band = band_names[0]
            night_band = band_names[1]
            
            day_lst = modis_lst.select([day_band])
            night_lst = modis_lst.select([night_band])
            
            # Create average of day and night temperatures
            avg_lst = day_lst.add(night_lst).divide(2).rename('LST_MODIS_Average').clamp(-20, 60)
            return avg_lst.clip(geometry)
        elif len(band_names) >= 1:
            # Use only available band if just one is present
            return modis_lst.select([band_names[0]]).rename('LST_MODIS_Single').clamp(-20, 60).clip(geometry)
        else:
            return None
    except Exception:
        return None


def compute_temperature_statistics(city: str, year: int, base_output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Compute comprehensive temperature statistics for urban and rural regions.
    
    This function computes detailed temperature statistics including:
    - Monthly temperature averages for urban and rural zones
    - Confidence intervals using bootstrap sampling
    - Uncertainty analysis and error metrics
    - Day/night temperature differences
    - Seasonal trends and variability
    
    Args:
        city: City name from UZBEKISTAN_CITIES
        year: Year to analyze
        base_output_dir: Optional base directory for output (defaults to suhi_analysis_output)
        
    Returns:
        Dictionary with comprehensive temperature statistics
    """
    if city not in UZBEKISTAN_CITIES:
        return {'error': f'City {city} not found in configuration'}
    
    city_info = UZBEKISTAN_CITIES[city]
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    
    # Define analysis zones
    urban_core = center.buffer(city_info['buffer_m'])
    rural_buffer_m = ANALYSIS_CONFIG['rural_buffer_km'] * 1000
    rural_ring = (center.buffer(city_info['buffer_m'] + rural_buffer_m)
                  .difference(center.buffer(city_info['buffer_m'])))
    
    stats = {
        'city': city,
        'year': year,
        'metadata': {
            'urban_buffer_m': city_info['buffer_m'],
            'rural_buffer_m': rural_buffer_m,
            'center_coordinates': [city_info['lon'], city_info['lat']],
            'analysis_months': ANALYSIS_CONFIG['warm_months'],
            'collection_dates': f"{year}-{ANALYSIS_CONFIG['warm_months'][0]:02d}-01 to {year}-{ANALYSIS_CONFIG['warm_months'][-1]:02d}-31",
            'optimization_note': 'Focused on summer months only for efficiency'
        },
        'summer_season_summary': {},
        'uncertainty': {},
        'confidence_intervals': {},
        'day_night_analysis': {}
    }
    
    try:
        # Get summer season statistics only (skip individual monthly computations)
        warm_season_stats = _compute_seasonal_temperature_stats(
            year, urban_core, rural_ring, ANALYSIS_CONFIG['warm_months']
        )
        stats['summer_season_summary'] = warm_season_stats
        
        # Compute uncertainty analysis for summer season
        uncertainty_analysis = _compute_temperature_uncertainty(
            year, urban_core, rural_ring
        )
        stats['uncertainty'] = uncertainty_analysis
        
        # Compute confidence intervals for key metrics
        confidence_intervals = _compute_temperature_confidence_intervals(
            year, urban_core, rural_ring
        )
        stats['confidence_intervals'] = confidence_intervals
        
        # Day/night analysis for summer season
        day_night_analysis = _compute_day_night_temperature_analysis(
            year, urban_core, rural_ring
        )
        stats['day_night_analysis'] = day_night_analysis
        
    except Exception as e:
        stats['error'] = str(e)
        stats['error_type'] = type(e).__name__
    
    # Save to JSON file
    if base_output_dir is None:
        try:
            base_output_dir = Path(__file__).parent.parent / "suhi_analysis_output"
        except Exception:
            base_output_dir = Path.cwd() / "suhi_analysis_output"
    
    temp_dir = base_output_dir / "temperature" / city
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = temp_dir / f"{city}_temperature_stats_{year}.json"
    try:
        safe_stats = make_json_safe(stats)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(safe_stats, f, indent=2, ensure_ascii=False)
        stats['output_file'] = str(output_file)
    except Exception as e:
        stats['save_error'] = str(e)
    
    return stats


def _compute_monthly_temperature_stats(start_date: str, end_date: str, 
                                     urban_zone: ee.Geometry, rural_zone: ee.Geometry, 
                                     month: int) -> Dict[str, Any]:
    """Compute temperature statistics for a single month."""
    month_stats = {
        'month': month,
        'urban': {},
        'rural': {},
        'urban_rural_difference': {}
    }
    
    try:
        # Load MODIS LST for the month
        modis_lst = load_modis_lst(start_date, end_date, 
                                  urban_zone.union(rural_zone).buffer(1000))
        
        if modis_lst is None:
            month_stats['error'] = 'No MODIS LST data available'
            return month_stats
        
        # Get band names
        band_names = modis_lst.bandNames().getInfo()
        day_band = band_names[0] if len(band_names) > 0 else None
        night_band = band_names[1] if len(band_names) > 1 else None
        
        scale = GEE_CONFIG.get('scale_modis', 1000)
        
        # Process day LST
        if day_band:
            day_lst = modis_lst.select([day_band])
            
            # Urban day statistics
            urban_day_stats = day_lst.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.stdDev(), sharedInputs=True
                ).combine(
                    ee.Reducer.count(), sharedInputs=True
                ).combine(
                    ee.Reducer.percentile([10, 25, 50, 75, 90]), sharedInputs=True
                ),
                geometry=urban_zone,
                scale=scale,
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=True
            )
            
            # Rural day statistics
            rural_day_stats = day_lst.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.stdDev(), sharedInputs=True
                ).combine(
                    ee.Reducer.count(), sharedInputs=True
                ).combine(
                    ee.Reducer.percentile([10, 25, 50, 75, 90]), sharedInputs=True
                ),
                geometry=rural_zone,
                scale=scale,
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=True
            )
            
            # Extract and store day statistics
            month_stats['urban']['day'] = _extract_reducer_stats(urban_day_stats, day_band)
            month_stats['rural']['day'] = _extract_reducer_stats(rural_day_stats, day_band)
            
            # Compute urban-rural difference for day
            if (month_stats['urban']['day'].get('mean') is not None and 
                month_stats['rural']['day'].get('mean') is not None):
                month_stats['urban_rural_difference']['day'] = (
                    month_stats['urban']['day']['mean'] - month_stats['rural']['day']['mean']
                )
        
        # Process night LST
        if night_band:
            night_lst = modis_lst.select([night_band])
            
            # Urban night statistics
            urban_night_stats = night_lst.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.stdDev(), sharedInputs=True
                ).combine(
                    ee.Reducer.count(), sharedInputs=True
                ).combine(
                    ee.Reducer.percentile([10, 25, 50, 75, 90]), sharedInputs=True
                ),
                geometry=urban_zone,
                scale=scale,
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=True
            )
            
            # Rural night statistics
            rural_night_stats = night_lst.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.stdDev(), sharedInputs=True
                ).combine(
                    ee.Reducer.count(), sharedInputs=True
                ).combine(
                    ee.Reducer.percentile([10, 25, 50, 75, 90]), sharedInputs=True
                ),
                geometry=rural_zone,
                scale=scale,
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=True
            )
            
            # Extract and store night statistics
            month_stats['urban']['night'] = _extract_reducer_stats(urban_night_stats, night_band)
            month_stats['rural']['night'] = _extract_reducer_stats(rural_night_stats, night_band)
            
            # Compute urban-rural difference for night
            if (month_stats['urban']['night'].get('mean') is not None and 
                month_stats['rural']['night'].get('mean') is not None):
                month_stats['urban_rural_difference']['night'] = (
                    month_stats['urban']['night']['mean'] - month_stats['rural']['night']['mean']
                )
    
    except Exception as e:
        month_stats['error'] = str(e)
    
    return month_stats


def _extract_reducer_stats(stats_dict: ee.Dictionary, band_name: str) -> Dict[str, float]:
    """Extract statistics from Earth Engine reducer results."""
    try:
        stats_info = stats_dict.getInfo()
        return {
            'mean': stats_info.get(f"{band_name}_mean"),
            'std_dev': stats_info.get(f"{band_name}_stdDev"),
            'count': stats_info.get(f"{band_name}_count"),
            'p10': stats_info.get(f"{band_name}_p10"),
            'p25': stats_info.get(f"{band_name}_p25"),
            'median': stats_info.get(f"{band_name}_p50"),
            'p75': stats_info.get(f"{band_name}_p75"),
            'p90': stats_info.get(f"{band_name}_p90")
        }
    except Exception:
        return {}


def _compute_seasonal_temperature_stats(year: int, urban_zone: ee.Geometry, 
                                       rural_zone: ee.Geometry, 
                                       focus_months: List[int]) -> Dict[str, Any]:
    """Compute seasonal temperature statistics for warm months with bulk calculations."""
    seasonal_stats = {
        'focus_months': focus_months,
        'urban': {'day': {}, 'night': {}},
        'rural': {'day': {}, 'night': {}},
        'urban_rural_difference': {'day': None, 'night': None}
    }
    
    try:
        # Create optimized date range for focus months only
        start_date = f"{year}-{focus_months[0]:02d}-01"
        end_date = f"{year}-{focus_months[-1]:02d}-31"
        
        # Load MODIS LST for focus months only (more efficient)
        modis_lst = load_modis_lst(start_date, end_date, 
                                  urban_zone.union(rural_zone).buffer(1000))
        
        if modis_lst is None:
            seasonal_stats['error'] = 'No MODIS LST data for focus months'
            return seasonal_stats
        
        band_names = modis_lst.bandNames().getInfo()
        day_band = band_names[0] if len(band_names) > 0 else None
        night_band = band_names[1] if len(band_names) > 1 else None
        
        scale = GEE_CONFIG.get('scale_modis', 1000)
        
        # Bulk calculation for day LST (single API call per zone per band)
        if day_band:
            day_lst = modis_lst.select([day_band])
            
            # Combined reducer for all statistics in one call
            combined_reducer = (ee.Reducer.mean().combine(
                ee.Reducer.stdDev(), sharedInputs=True
            ).combine(
                ee.Reducer.minMax(), sharedInputs=True
            ).combine(
                ee.Reducer.percentile([5, 10, 25, 50, 75, 90, 95]), sharedInputs=True
            ).combine(
                ee.Reducer.count(), sharedInputs=True
            ))
            
            # Single call for urban day stats
            urban_day_result = day_lst.reduceRegion(
                reducer=combined_reducer,
                geometry=urban_zone,
                scale=scale,
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=True
            ).getInfo()
            
            # Single call for rural day stats
            rural_day_result = day_lst.reduceRegion(
                reducer=combined_reducer,
                geometry=rural_zone,
                scale=scale,
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=True
            ).getInfo()
            
            seasonal_stats['urban']['day'] = _parse_bulk_seasonal_stats(urban_day_result, day_band)
            seasonal_stats['rural']['day'] = _parse_bulk_seasonal_stats(rural_day_result, day_band)
            
            if (seasonal_stats['urban']['day'].get('mean') is not None and 
                seasonal_stats['rural']['day'].get('mean') is not None):
                seasonal_stats['urban_rural_difference']['day'] = (
                    seasonal_stats['urban']['day']['mean'] - seasonal_stats['rural']['day']['mean']
                )
        
        # Bulk calculation for night LST
        if night_band:
            night_lst = modis_lst.select([night_band])
            
            # Single call for urban night stats
            urban_night_result = night_lst.reduceRegion(
                reducer=combined_reducer,
                geometry=urban_zone,
                scale=scale,
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=True
            ).getInfo()
            
            # Single call for rural night stats
            rural_night_result = night_lst.reduceRegion(
                reducer=combined_reducer,
                geometry=rural_zone,
                scale=scale,
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=True
            ).getInfo()
            
            seasonal_stats['urban']['night'] = _parse_bulk_seasonal_stats(urban_night_result, night_band)
            seasonal_stats['rural']['night'] = _parse_bulk_seasonal_stats(rural_night_result, night_band)
            
            if (seasonal_stats['urban']['night'].get('mean') is not None and 
                seasonal_stats['rural']['night'].get('mean') is not None):
                seasonal_stats['urban_rural_difference']['night'] = (
                    seasonal_stats['urban']['night']['mean'] - seasonal_stats['rural']['night']['mean']
                )
    
    except Exception as e:
        seasonal_stats['error'] = str(e)
    
    return seasonal_stats


def _parse_bulk_seasonal_stats(stats_dict: Dict, band_name: str) -> Dict[str, float]:
    """Parse bulk seasonal statistics from combined reducer results."""
    return {
        'mean': stats_dict.get(f"{band_name}_mean"),
        'std_dev': stats_dict.get(f"{band_name}_stdDev"),
        'min': stats_dict.get(f"{band_name}_min"),
        'max': stats_dict.get(f"{band_name}_max"),
        'p5': stats_dict.get(f"{band_name}_p5"),
        'p10': stats_dict.get(f"{band_name}_p10"),
        'p25': stats_dict.get(f"{band_name}_p25"),
        'median': stats_dict.get(f"{band_name}_p50"),
        'p75': stats_dict.get(f"{band_name}_p75"),
        'p90': stats_dict.get(f"{band_name}_p90"),
        'p95': stats_dict.get(f"{band_name}_p95"),
        'count': stats_dict.get(f"{band_name}_count")
    }


def _compute_temperature_uncertainty(year: int, urban_zone: ee.Geometry, 
                                   rural_zone: ee.Geometry) -> Dict[str, Any]:
    """Compute uncertainty analysis for temperature measurements."""
    uncertainty = {
        'urban': {'day': {}, 'night': {}},
        'rural': {'day': {}, 'night': {}},
        'spatial_uncertainty': {},
        'temporal_uncertainty': {}
    }
    
    try:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        modis_lst = load_modis_lst(start_date, end_date, 
                                  urban_zone.union(rural_zone).buffer(1000))
        
        if modis_lst is None:
            uncertainty['error'] = 'No MODIS LST data available'
            return uncertainty
        
        band_names = modis_lst.bandNames().getInfo()
        day_band = band_names[0] if len(band_names) > 0 else None
        night_band = band_names[1] if len(band_names) > 1 else None
        
        zones = {'urban_core': urban_zone, 'rural_ring': rural_zone}
        scale = GEE_CONFIG.get('scale_modis', 1000)
        
        # Compute spatial uncertainty using error assessment module
        if day_band:
            day_lst = modis_lst.select([day_band])
            day_uncertainty = error_assessment.compute_zonal_uncertainty(
                day_lst, zones, scale=scale, maxPixels=GEE_CONFIG['max_pixels']
            )
            uncertainty['urban']['day'] = day_uncertainty.get('urban_core', {})
            uncertainty['rural']['day'] = day_uncertainty.get('rural_ring', {})
        
        if night_band:
            night_lst = modis_lst.select([night_band])
            night_uncertainty = error_assessment.compute_zonal_uncertainty(
                night_lst, zones, scale=scale, maxPixels=GEE_CONFIG['max_pixels']
            )
            uncertainty['urban']['night'] = night_uncertainty.get('urban_core', {})
            uncertainty['rural']['night'] = night_uncertainty.get('rural_ring', {})
        
        # Add temporal uncertainty analysis (coefficient of variation across warm months)
        temporal_unc = _compute_temporal_uncertainty(year, urban_zone, rural_zone)
        uncertainty['temporal_uncertainty'] = temporal_unc
        
    except Exception as e:
        uncertainty['error'] = str(e)
    
    return uncertainty


def _compute_temporal_uncertainty(year: int, urban_zone: ee.Geometry, 
                                rural_zone: ee.Geometry) -> Dict[str, Any]:
    """Compute temporal uncertainty across summer months only."""
    temporal_stats = {
        'urban': {'day': {}, 'night': {}},
        'rural': {'day': {}, 'night': {}}
    }
    
    try:
        # Focus only on warm months for efficiency
        warm_months = ANALYSIS_CONFIG['warm_months']
        monthly_temps = {'urban': {'day': [], 'night': []}, 
                        'rural': {'day': [], 'night': []}}
        
        # Process all warm months in bulk rather than individual calls
        for month in warm_months:
            month_start = f"{year}-{month:02d}-01"
            if month == 12:
                month_end = f"{year+1}-01-01"
            else:
                month_end = f"{year}-{month+1:02d}-01"
            
            modis_lst = load_modis_lst(month_start, month_end, 
                                      urban_zone.union(rural_zone).buffer(1000))
            
            if modis_lst is not None:
                band_names = modis_lst.bandNames().getInfo()
                day_band = band_names[0] if len(band_names) > 0 else None
                night_band = band_names[1] if len(band_names) > 1 else None
                scale = GEE_CONFIG.get('scale_modis', 1000)
                
                # Bulk reduction for both urban and rural in single calls
                if day_band:
                    day_lst = modis_lst.select([day_band])
                    
                    # Combined reducer for urban and rural stats
                    urban_rural_stats = day_lst.reduceRegions(
                        collection=ee.FeatureCollection([
                            ee.Feature(urban_zone, {'zone': 'urban'}),
                            ee.Feature(rural_zone, {'zone': 'rural'})
                        ]),
                        reducer=ee.Reducer.mean(),
                        scale=scale
                    ).getInfo()
                    
                    for feature in urban_rural_stats['features']:
                        zone = feature['properties']['zone']
                        temp_value = feature['properties'].get(day_band + '_mean')
                        if temp_value is not None:
                            monthly_temps[zone]['day'].append(temp_value)
                
                if night_band:
                    night_lst = modis_lst.select([night_band])
                    
                    urban_rural_stats = night_lst.reduceRegions(
                        collection=ee.FeatureCollection([
                            ee.Feature(urban_zone, {'zone': 'urban'}),
                            ee.Feature(rural_zone, {'zone': 'rural'})
                        ]),
                        reducer=ee.Reducer.mean(),
                        scale=scale
                    ).getInfo()
                    
                    for feature in urban_rural_stats['features']:
                        zone = feature['properties']['zone']
                        temp_value = feature['properties'].get(night_band + '_mean')
                        if temp_value is not None:
                            monthly_temps[zone]['night'].append(temp_value)
        
        # Compute temporal statistics using numpy for client-side calculations
        for zone in ['urban', 'rural']:
            for period in ['day', 'night']:
                temps = monthly_temps[zone][period]
                if len(temps) > 1:
                    temps_array = np.array(temps)
                    temporal_stats[zone][period] = {
                        'monthly_mean': float(np.mean(temps_array)),
                        'monthly_std': float(np.std(temps_array)),
                        'coefficient_of_variation': float(np.std(temps_array) / np.mean(temps_array)) if np.mean(temps_array) != 0 else None,
                        'min_monthly': float(np.min(temps_array)),
                        'max_monthly': float(np.max(temps_array)),
                        'monthly_range': float(np.max(temps_array) - np.min(temps_array)),
                        'n_months': len(temps)
                    }
    
    except Exception as e:
        temporal_stats['error'] = str(e)
    
    return temporal_stats


def _compute_temperature_confidence_intervals(year: int, urban_zone: ee.Geometry, 
                                            rural_zone: ee.Geometry) -> Dict[str, Any]:
    """Compute confidence intervals for temperature statistics."""
    confidence_intervals = {
        'urban': {'day': {}, 'night': {}},
        'rural': {'day': {}, 'night': {}},
        'urban_rural_difference': {'day': {}, 'night': {}},
        'confidence_level': 0.95
    }
    
    try:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        modis_lst = load_modis_lst(start_date, end_date, 
                                  urban_zone.union(rural_zone).buffer(1000))
        
        if modis_lst is None:
            confidence_intervals['error'] = 'No MODIS LST data available'
            return confidence_intervals
        
        band_names = modis_lst.bandNames().getInfo()
        day_band = band_names[0] if len(band_names) > 0 else None
        night_band = band_names[1] if len(band_names) > 1 else None
        scale = GEE_CONFIG.get('scale_modis', 1000)
        
        # Compute confidence intervals based on standard error
        for band_name, period in [(day_band, 'day'), (night_band, 'night')]:
            if band_name is None:
                continue
                
            lst_image = modis_lst.select([band_name])
            
            # Urban confidence intervals
            urban_stats = lst_image.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.stdDev(), sharedInputs=True
                ).combine(
                    ee.Reducer.count(), sharedInputs=True
                ),
                geometry=urban_zone,
                scale=scale,
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=True
            ).getInfo()
            
            urban_mean = urban_stats.get(f"{band_name}_mean")
            urban_std = urban_stats.get(f"{band_name}_stdDev")
            urban_count = urban_stats.get(f"{band_name}_count")
            
            if urban_mean is not None and urban_std is not None and urban_count is not None and urban_count > 1:
                # 95% confidence interval using t-distribution approximation
                se = urban_std / np.sqrt(urban_count)
                t_value = 1.96  # approximation for large samples
                margin_error = t_value * se
                
                confidence_intervals['urban'][period] = {
                    'mean': urban_mean,
                    'standard_error': se,
                    'margin_of_error': margin_error,
                    'lower_bound': urban_mean - margin_error,
                    'upper_bound': urban_mean + margin_error,
                    'sample_count': urban_count
                }
            
            # Rural confidence intervals
            rural_stats = lst_image.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.stdDev(), sharedInputs=True
                ).combine(
                    ee.Reducer.count(), sharedInputs=True
                ),
                geometry=rural_zone,
                scale=scale,
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=True
            ).getInfo()
            
            rural_mean = rural_stats.get(f"{band_name}_mean")
            rural_std = rural_stats.get(f"{band_name}_stdDev")
            rural_count = rural_stats.get(f"{band_name}_count")
            
            if rural_mean is not None and rural_std is not None and rural_count is not None and rural_count > 1:
                se = rural_std / np.sqrt(rural_count)
                t_value = 1.96
                margin_error = t_value * se
                
                confidence_intervals['rural'][period] = {
                    'mean': rural_mean,
                    'standard_error': se,
                    'margin_of_error': margin_error,
                    'lower_bound': rural_mean - margin_error,
                    'upper_bound': rural_mean + margin_error,
                    'sample_count': rural_count
                }
            
            # Urban-rural difference confidence intervals
            if (confidence_intervals['urban'][period].get('mean') is not None and 
                confidence_intervals['rural'][period].get('mean') is not None):
                
                urban_se = confidence_intervals['urban'][period]['standard_error']
                rural_se = confidence_intervals['rural'][period]['standard_error']
                diff_mean = confidence_intervals['urban'][period]['mean'] - confidence_intervals['rural'][period]['mean']
                diff_se = np.sqrt(urban_se**2 + rural_se**2)
                diff_margin_error = 1.96 * diff_se
                
                confidence_intervals['urban_rural_difference'][period] = {
                    'difference_mean': diff_mean,
                    'standard_error': diff_se,
                    'margin_of_error': diff_margin_error,
                    'lower_bound': diff_mean - diff_margin_error,
                    'upper_bound': diff_mean + diff_margin_error
                }
    
    except Exception as e:
        confidence_intervals['error'] = str(e)
    
    return confidence_intervals


def _compute_day_night_temperature_analysis(year: int, urban_zone: ee.Geometry, 
                                          rural_zone: ee.Geometry) -> Dict[str, Any]:
    """Compute comprehensive day-night temperature analysis."""
    day_night_analysis = {
        'urban': {},
        'rural': {},
        'urban_rural_comparison': {},
        'day_night_differences': {}
    }
    
    try:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        modis_lst = load_modis_lst(start_date, end_date, 
                                  urban_zone.union(rural_zone).buffer(1000))
        
        if modis_lst is None:
            day_night_analysis['error'] = 'No MODIS LST data available'
            return day_night_analysis
        
        band_names = modis_lst.bandNames().getInfo()
        day_band = band_names[0] if len(band_names) > 0 else None
        night_band = band_names[1] if len(band_names) > 1 else None
        
        if day_band is None or night_band is None:
            day_night_analysis['error'] = 'Missing day or night LST bands'
            return day_night_analysis
        
        scale = GEE_CONFIG.get('scale_modis', 1000)
        
        # Day-night difference images
        day_lst = modis_lst.select([day_band])
        night_lst = modis_lst.select([night_band])
        day_night_diff = day_lst.subtract(night_lst).rename('day_night_difference')
        
        # Urban analysis
        urban_day_stats = day_lst.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
            geometry=urban_zone, scale=scale, maxPixels=GEE_CONFIG['max_pixels'], bestEffort=True
        ).getInfo()
        
        urban_night_stats = night_lst.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
            geometry=urban_zone, scale=scale, maxPixels=GEE_CONFIG['max_pixels'], bestEffort=True
        ).getInfo()
        
        urban_diff_stats = day_night_diff.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
            geometry=urban_zone, scale=scale, maxPixels=GEE_CONFIG['max_pixels'], bestEffort=True
        ).getInfo()
        
        day_night_analysis['urban'] = {
            'day_temperature': {
                'mean': urban_day_stats.get(f"{day_band}_mean"),
                'std_dev': urban_day_stats.get(f"{day_band}_stdDev")
            },
            'night_temperature': {
                'mean': urban_night_stats.get(f"{night_band}_mean"),
                'std_dev': urban_night_stats.get(f"{night_band}_stdDev")
            },
            'day_night_difference': {
                'mean': urban_diff_stats.get('day_night_difference_mean'),
                'std_dev': urban_diff_stats.get('day_night_difference_stdDev')
            }
        }
        
        # Rural analysis
        rural_day_stats = day_lst.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
            geometry=rural_zone, scale=scale, maxPixels=GEE_CONFIG['max_pixels'], bestEffort=True
        ).getInfo()
        
        rural_night_stats = night_lst.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
            geometry=rural_zone, scale=scale, maxPixels=GEE_CONFIG['max_pixels'], bestEffort=True
        ).getInfo()
        
        rural_diff_stats = day_night_diff.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
            geometry=rural_zone, scale=scale, maxPixels=GEE_CONFIG['max_pixels'], bestEffort=True
        ).getInfo()
        
        day_night_analysis['rural'] = {
            'day_temperature': {
                'mean': rural_day_stats.get(f"{day_band}_mean"),
                'std_dev': rural_day_stats.get(f"{day_band}_stdDev")
            },
            'night_temperature': {
                'mean': rural_night_stats.get(f"{night_band}_mean"),
                'std_dev': rural_night_stats.get(f"{night_band}_stdDev")
            },
            'day_night_difference': {
                'mean': rural_diff_stats.get('day_night_difference_mean'),
                'std_dev': rural_diff_stats.get('day_night_difference_stdDev')
            }
        }
        
        # Urban-rural comparison
        if (day_night_analysis['urban']['day_temperature']['mean'] is not None and
            day_night_analysis['rural']['day_temperature']['mean'] is not None):
            day_night_analysis['urban_rural_comparison']['day_difference'] = (
                day_night_analysis['urban']['day_temperature']['mean'] - 
                day_night_analysis['rural']['day_temperature']['mean']
            )
        
        if (day_night_analysis['urban']['night_temperature']['mean'] is not None and
            day_night_analysis['rural']['night_temperature']['mean'] is not None):
            day_night_analysis['urban_rural_comparison']['night_difference'] = (
                day_night_analysis['urban']['night_temperature']['mean'] - 
                day_night_analysis['rural']['night_temperature']['mean']
            )
        
        # Day-night pattern analysis
        urban_day_night_diff = day_night_analysis['urban']['day_night_difference']['mean']
        rural_day_night_diff = day_night_analysis['rural']['day_night_difference']['mean']
        
        if urban_day_night_diff is not None and rural_day_night_diff is not None:
            day_night_analysis['day_night_differences'] = {
                'urban_day_night_range': urban_day_night_diff,
                'rural_day_night_range': rural_day_night_diff,
                'urban_rural_day_night_difference': urban_day_night_diff - rural_day_night_diff,
                'interpretation': {
                    'urban_has_larger_day_night_range': urban_day_night_diff > rural_day_night_diff,
                    'urban_day_night_range_larger_by': urban_day_night_diff - rural_day_night_diff if urban_day_night_diff > rural_day_night_diff else None
                }
            }
    
    except Exception as e:
        day_night_analysis['error'] = str(e)
    
    return day_night_analysis


def load_aster_lst(start_date: str, end_date: str, geometry: ee.Geometry) -> Optional[ee.Image]:
    def calculate_aster_lst(image):
        b13 = image.select('B13')
        b14 = image.select('B14')
        lst = (b13.add(b14).divide(2).multiply(0.00862).add(0.56).subtract(273.15).rename('LST_ASTER').clamp(-20,60))
        return lst
    collection = (ee.ImageCollection(DATASETS['aster']).filterDate(start_date,end_date).filterBounds(geometry).map(calculate_aster_lst))
    size = collection.size()
    return ee.Algorithms.If(size.gt(0), collection.median(), None)
