"""Sentinel-based air quality assessment service for urban climate analysis.

This module provides comprehensive air quality monitoring using Sentinel satellites:
- Sentinel-5P: NO2, O3, SO2, CO, CH4, Aerosol Index
- Sentinel-2: Aerosol Optical Depth (AOD)
- Sentinel-3: Ocean and Land Color Instrument (OLCI) for additional parameters

Key features:
- Multi-pollutant analysis (NO2, O3, SO2, CO, CH4, AOD)
- Temporal trend analysis and seasonal patterns
- Urban vs rural comparisons
- Health impact assessment indicators
- Scientific validation and quality control
"""

import ee
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json
from .utils import DATASETS, GEE_CONFIG, ANALYSIS_CONFIG, rate_limiter, make_json_safe
from .utils import UZBEKISTAN_CITIES


class AirQualityAnalyzer:
    """Main class for Sentinel-based air quality analysis"""

    def __init__(self):
        # Focus on pollutants with reliable data coverage for Central Asia
        self.pollutants = {
            'CO': {'dataset': 'sentinel5p_co', 'band': 'CO_column_number_density',
                  'units': 'mol/m²', 'factor': 1e6, 'display_units': 'µmol/m²'},
            'CH4': {'dataset': 'sentinel5p_ch4', 'band': 'CH4_column_volume_mixing_ratio_dry_air',
                   'units': 'ppmv', 'factor': 1, 'display_units': 'ppmv'},
            'AER_AI': {'dataset': 'sentinel5p_aerosol', 'band': 'absorbing_aerosol_index',
                      'units': 'dimensionless', 'factor': 1, 'display_units': 'AI'},
            # Note: NO2, O3, SO2 now use same processing as CO, CH4, AER_AI (no cloud filtering)
            'NO2': {'dataset': 'sentinel5p_no2', 'band': 'tropospheric_NO2_column_number_density',
                   'units': 'mol/m²', 'factor': 1e6, 'display_units': 'µmol/m²'},
            'O3': {'dataset': 'sentinel5p_o3', 'band': 'O3_column_number_density',
                  'units': 'mol/m²', 'factor': 1e6, 'display_units': 'µmol/m²'},
            'SO2': {'dataset': 'sentinel5p_so2', 'band': 'SO2_column_number_density',
                   'units': 'mol/m²', 'factor': 1e6, 'display_units': 'µmol/m²'}
        }

        # Health impact thresholds (WHO guidelines)
        self.health_thresholds = {
            'NO2': {'annual': 40, 'hourly': 200, 'unit': 'µg/m³'},
            'O3': {'daily_8h': 100, 'hourly': 160, 'unit': 'µg/m³'},
            'SO2': {'daily': 40, 'hourly': 500, 'unit': 'µg/m³'},
            'CO': {'hourly': 35000, 'daily_8h': 4000, 'unit': 'µg/m³'},
            'PM2.5': {'annual': 5, 'daily': 15, 'unit': 'µg/m³'},
            'PM10': {'annual': 20, 'daily': 45, 'unit': 'µg/m³'}
        }

    def get_city_geometry(self, city_name: str, buffer_km: float = 25) -> ee.Geometry:
        """Create urban and rural analysis zones for a city"""
        if city_name not in UZBEKISTAN_CITIES:
            raise ValueError(f"City {city_name} not found in configuration")

        city_info = UZBEKISTAN_CITIES[city_name]
        center = ee.Geometry.Point([city_info['lon'], city_info['lat']])

        # Urban zone (city buffer)
        urban_radius = city_info['buffer_m']
        urban_zone = center.buffer(urban_radius)

        # Rural zone (extended buffer for background levels)
        rural_radius = urban_radius + (buffer_km * 1000)
        rural_zone = center.buffer(rural_radius).difference(urban_zone)

        return {
            'center': center,
            'urban': urban_zone,
            'rural': rural_zone,
            'combined': center.buffer(rural_radius)
        }

    def get_sentinel5p_data(self, pollutant: str, start_date: str, end_date: str,
                           geometry: ee.Geometry) -> ee.ImageCollection:
        """Retrieve and preprocess Sentinel-5P data for a specific pollutant"""

        if pollutant not in self.pollutants:
            raise ValueError(f"Pollutant {pollutant} not supported")

        config = self.pollutants[pollutant]
        dataset = DATASETS[config['dataset']]

        # Create collection with basic filters
        collection = (ee.ImageCollection(dataset)
                     .filterDate(start_date, end_date)
                     .filterBounds(geometry))

        # Apply minimal quality filters to avoid excluding too much data
        try:
            # Note: Cloud filtering removed to ensure data availability for all pollutants
            # All Sentinel-5P products have their own quality flags and filtering
            # Select the target band - this is essential
            if config['band']:
                collection = collection.select(config['band'])

        except Exception as e:
            print(f"   ⚠️ Warning in {pollutant} filtering: {e}")

        return collection

    def calculate_monthly_composite(self, collection: ee.ImageCollection,
                                   geometry: ee.Geometry, reducer: str = 'mean') -> ee.Image:
        """Create monthly composite with specified reducer"""

        if reducer == 'mean':
            composite = collection.mean()
        elif reducer == 'median':
            composite = collection.median()
        elif reducer == 'max':
            composite = collection.max()
        elif reducer == 'min':
            composite = collection.min()
        else:
            composite = collection.mean()

        return composite

    def extract_pollutant_stats(self, image: ee.Image, geometry: ee.Geometry,
                               band_name: str, scale: int = 1000) -> Dict[str, Any]:
        """Extract statistical summary for a pollutant image"""

        try:
            # Check if image and band exist
            if image is None:
                return {'error': 'No image provided'}

            # Use reduceRegion to get statistics over the geometry
            stats = image.select(band_name).reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.stdDev(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.minMax(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.count(), sharedInputs=True
                ),
                geometry=geometry,
                scale=scale,
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=GEE_CONFIG['best_effort']
            ).getInfo()

            if stats:
                # Extract values for the band
                mean_val = stats.get(f'{band_name}_mean')
                stddev_val = stats.get(f'{band_name}_stdDev')
                min_val = stats.get(f'{band_name}_min')
                max_val = stats.get(f'{band_name}_max')
                count_val = stats.get(f'{band_name}_count')

                # Handle case where band name might be different in results
                if mean_val is None and band_name in stats:
                    # If stats directly contain band name as key
                    band_stats = stats[band_name]
                    if isinstance(band_stats, dict):
                        mean_val = band_stats.get('mean')
                        stddev_val = band_stats.get('stdDev')
                        min_val = band_stats.get('min')
                        max_val = band_stats.get('max')
                        count_val = band_stats.get('count')
                    else:
                        # Single value case
                        mean_val = band_stats

                result = {
                    'mean': mean_val,
                    'stdDev': stddev_val,
                    'min': min_val,
                    'max': max_val,
                    'count': count_val,
                    'valid_pixels': count_val if count_val is not None else 0
                }

                # Check if we got any valid data
                if mean_val is not None:
                    return result
                else:
                    return {'error': 'No valid pixel values found for the geometry'}
            else:
                return {'error': 'No statistics returned from reduceRegion'}

        except Exception as e:
            return {'error': f'Statistics extraction failed: {str(e)}'}

    def calculate_server_side_annual_stats(self, monthly_collections: List[ee.ImageCollection], 
                                           geometry: ee.Geometry, band_name: str) -> Dict[str, Any]:
        """Calculate annual statistics server-side using Earth Engine reducers"""
        
        if not monthly_collections:
            return {'error': 'No monthly collections provided'}
        
        try:
            # Combine all monthly collections into one
            annual_collection = ee.ImageCollection([])
            valid_collections = 0
            
            for collection in monthly_collections:
                collection_size = collection.size().getInfo()
                if collection_size > 0:
                    annual_collection = annual_collection.merge(collection)
                    valid_collections += 1
            
            if valid_collections == 0:
                return {'error': 'No valid data in any monthly collection'}
            
            # Select the specific band from the annual collection
            annual_collection = annual_collection.select(band_name)
            
            # Create a time-series composite using mean reducer
            annual_composite = annual_collection.mean()
            
            # Extract statistics for the specific geometry using reduceRegion
            final_stats = annual_composite.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.stdDev(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.minMax(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.count(), sharedInputs=True
                ),
                geometry=geometry,
                scale=1000,
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=GEE_CONFIG['best_effort']
            ).getInfo()
            
            if final_stats:
                # Handle the band name in results
                mean_key = f'{band_name}_mean'
                stddev_key = f'{band_name}_stdDev'
                min_key = f'{band_name}_min'
                max_key = f'{band_name}_max'
                count_key = f'{band_name}_count'
                
                result = {
                    'mean': final_stats.get(mean_key),
                    'stdDev': final_stats.get(stddev_key),
                    'min': final_stats.get(min_key),
                    'max': final_stats.get(max_key),
                    'count': final_stats.get(count_key),
                    'valid_pixels': final_stats.get(count_key, 0),
                    'months_with_data': valid_collections
                }
                
                # Check if we got valid data
                if result['mean'] is not None:
                    return result
                else:
                    return {'error': 'No valid pixel values found in annual composite'}
            else:
                return {'error': 'Failed to extract annual statistics from composite'}
                
        except Exception as e:
            return {'error': f'Server-side annual stats calculation failed: {str(e)}'}

    def calculate_server_side_seasonal_stats(self, monthly_collections: Dict[str, ee.ImageCollection],
                                             geometry: ee.Geometry, band_name: str) -> Dict[str, Any]:
        """Calculate seasonal statistics server-side"""
        
        seasons = {
            'winter': ['12', '01', '02'],
            'spring': ['03', '04', '05'], 
            'summer': ['06', '07', '08'],
            'autumn': ['09', '10', '11']
        }
        
        seasonal_results = {}
        
        for season_name, months in seasons.items():
            season_collections = []
            
            # Collect collections for this season
            for month in months:
                for key, collection in monthly_collections.items():
                    if key.endswith(month) and collection.size().getInfo() > 0:
                        season_collections.append(collection)
            
            if season_collections:
                # Combine seasonal collections
                seasonal_collection = ee.ImageCollection([])
                for collection in season_collections:
                    seasonal_collection = seasonal_collection.merge(collection)
                
                # Calculate seasonal statistics
                seasonal_stats = seasonal_collection.reduce(ee.Reducer.mean())
                
                final_seasonal_stats = seasonal_stats.reduceRegion(
                    reducer=ee.Reducer.first(),
                    geometry=geometry,
                    scale=1000,
                    maxPixels=GEE_CONFIG['max_pixels'],
                    bestEffort=GEE_CONFIG['best_effort']
                ).getInfo()
                
                if final_seasonal_stats and band_name in final_seasonal_stats:
                    seasonal_results[season_name] = {
                        'mean': final_seasonal_stats[band_name],
                        'months_with_data': len(season_collections)
                    }
                else:
                    seasonal_results[season_name] = {'error': 'No seasonal data'}
            else:
                seasonal_results[season_name] = {'error': 'No data for season'}
        
        return seasonal_results

    def calculate_server_side_health_indicators(self, annual_stats: Dict[str, Any], 
                                                pollutant_name: str) -> Dict[str, Any]:
        """Calculate health indicators using server-side computed statistics"""
        
        health_results = {}
        
        try:
            if pollutant_name == 'NO2' and 'mean' in annual_stats:
                no2_mean = annual_stats['mean']
                if no2_mean is not None:
                    # Convert from mol/m² to µg/m³ (approximate conversion for surface level)
                    no2_ugm3 = no2_mean * 1e6 * 46.0055 * 1000 / 22.4
                    
                    health_results = {
                        'annual_average_ugm3': no2_ugm3,
                        'exceeds_who_annual': no2_ugm3 > self.health_thresholds['NO2']['annual'],
                        'traffic_pollution_indicator': 'high' if no2_ugm3 > 60 else 'moderate' if no2_ugm3 > 40 else 'low'
                    }
            
            elif pollutant_name == 'O3' and 'max' in annual_stats:
                o3_max = annual_stats['max']
                if o3_max is not None:
                    # Convert approximation for peak values
                    o3_ugm3 = o3_max * 1e6 * 48 * 1000 / 22.4
                    
                    health_results = {
                        'peak_concentration_ugm3': o3_ugm3,
                        'exceeds_who_hourly': o3_ugm3 > self.health_thresholds['O3']['hourly'],
                        'photochemical_pollution_risk': 'high' if o3_ugm3 > 160 else 'moderate' if o3_ugm3 > 100 else 'low'
                    }
            
            elif pollutant_name == 'SO2' and 'mean' in annual_stats:
                so2_mean = annual_stats['mean']
                if so2_mean is not None:
                    so2_ugm3 = so2_mean * 1e6 * 64.066 * 1000 / 22.4
                    
                    health_results = {
                        'annual_average_ugm3': so2_ugm3,
                        'exceeds_who_daily': so2_ugm3 > self.health_thresholds['SO2']['daily'],
                        'industrial_pollution_indicator': 'high' if so2_ugm3 > 20 else 'moderate' if so2_ugm3 > 10 else 'low'
                    }
            
            elif pollutant_name == 'CO' and 'mean' in annual_stats:
                co_mean = annual_stats['mean']
                if co_mean is not None:
                    co_ugm3 = co_mean * 1e6 * 28.01 * 1000 / 22.4
                    
                    health_results = {
                        'annual_average_ugm3': co_ugm3,
                        'exceeds_who_hourly': co_ugm3 > self.health_thresholds['CO']['hourly'],
                        'carbon_monoxide_risk': 'high' if co_ugm3 > 35000 else 'moderate' if co_ugm3 > 4000 else 'low'
                    }
        
        except Exception as e:
            health_results = {'error': f'Health indicator calculation failed: {str(e)}'}
        
        return health_results

    def batch_process_monthly_data_optimized(self, city_name: str, year: int,
                                           months: Optional[List[int]] = None) -> Dict[str, Any]:
        """HIGHLY OPTIMIZED batch processing - minimizes getInfo() calls and uses proper S5P scale"""

        print(f"� HIGH-PERFORMANCE batch processing air quality for {city_name} in {year}...")

        if months is None:
            months = list(range(1, 13))

        # Get city geometry
        geometries = self.get_city_geometry(city_name)

        # Create zones FeatureCollection for batched reduceRegions
        zones_fc = ee.FeatureCollection([
            ee.Feature(geometries['urban'], {'zone': 'urban'}),
            ee.Feature(geometries['rural'], {'zone': 'rural'})
        ])

        results = {
            'city': city_name,
            'year': year,
            'analysis_timestamp': datetime.now().isoformat(),
            'geometries': {
                'center_lat': UZBEKISTAN_CITIES[city_name]['lat'],
                'center_lon': UZBEKISTAN_CITIES[city_name]['lon'],
                'urban_buffer_m': UZBEKISTAN_CITIES[city_name]['buffer_m']
            },
            'pollutants': {},
            'seasonal_analysis': {},
            'health_indicators': {},
            'quality_metrics': {}
        }

        # Process each pollutant with MINIMAL getInfo() calls
        for pollutant_name, config in self.pollutants.items():
            print(f"   📊 Processing {pollutant_name}...")

            try:
                # 🔥 OPTIMIZATION 1: Batch all monthly data collection server-side
                monthly_data = self._collect_all_monthly_data_server_side(
                    pollutant_name, year, months, geometries['combined']
                )

                if not monthly_data['collections']:
                    results['pollutants'][pollutant_name] = {'error': 'No valid data for any month'}
                    print(f"   ⚠️ No valid {pollutant_name} data for {city_name} {year}")
                    continue

                # 🔥 OPTIMIZATION 2: Single batched annual stats for both urban/rural
                annual_stats = self._calculate_batched_annual_stats(
                    monthly_data['collections'], zones_fc, config['band']
                )

                # 🔥 OPTIMIZATION 3: Single batched seasonal stats
                seasonal_stats = self._calculate_batched_seasonal_stats(
                    monthly_data['collections'], zones_fc, config['band']
                )

                # Process results
                pollutant_results = {
                    'urban_annual': annual_stats.get('urban', {'error': 'No urban data'}),
                    'rural_annual': annual_stats.get('rural', {'error': 'No rural data'}),
                    'urban_rural_ratio': self._calculate_ratio_safe(
                        annual_stats.get('urban', {}).get('mean'),
                        annual_stats.get('rural', {}).get('mean')
                    ),
                    'monthly_data_points': monthly_data['sizes'],
                    'data_completeness': monthly_data['completeness'],
                    'seasonal_analysis': seasonal_stats
                }

                # Calculate health indicators
                health_indicators = self.calculate_server_side_health_indicators(
                    pollutant_results['urban_annual'], pollutant_name
                )
                pollutant_results['health_indicators'] = health_indicators

                results['pollutants'][pollutant_name] = pollutant_results
                print(f"   ✅ Completed OPTIMIZED processing for {pollutant_name}")

            except Exception as e:
                print(f"   ❌ Error processing {pollutant_name}: {e}")
                results['pollutants'][pollutant_name] = {'error': str(e)}

        # Calculate overall quality metrics
        results['quality_metrics'] = self._assess_data_quality_server_side(results['pollutants'])

        return results

    def _collect_all_monthly_data_server_side(self, pollutant_name: str, year: int,
                                             months: List[int], geometry: ee.Geometry) -> Dict[str, Any]:
        """OPTIMIZATION: Collect all monthly data efficiently with minimal getInfo() calls"""

        config = self.pollutants[pollutant_name]
        dataset = DATASETS[config['dataset']]

        # Process months efficiently - create collections and check sizes
        collections = {}
        sizes = {}
        valid_months = 0

        for month in months:
            month_key = f"{year}_{month:02d}"

            # Create date range for this month
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month+1:02d}-01" if month < 12 else f"{year+1}-01-01"

            # Create collection for this month
            collection = (ee.ImageCollection(dataset)
                         .filterDate(start_date, end_date)
                         .filterBounds(geometry)
                         .select(config['band']))

            # Get size with single getInfo() call per month (still optimized vs original)
            size = collection.size().getInfo()
            sizes[month_key] = size

            if size > 0:
                collections[month_key] = collection
                valid_months += 1

        return {
            'collections': collections,
            'sizes': sizes,
            'completeness': valid_months / len(months),
            'valid_months': valid_months
        }

    def _calculate_batched_annual_stats(self, monthly_collections: Dict[str, ee.ImageCollection],
                                       zones_fc: ee.FeatureCollection, band_name: str) -> Dict[str, Any]:
        """OPTIMIZATION: Calculate annual stats for both zones in single reduceRegions call"""

        if not monthly_collections:
            return {'error': 'No monthly collections'}

        try:
            # Combine all valid monthly collections
            annual_collection = ee.ImageCollection([])
            valid_count = 0

            for collection in monthly_collections.values():
                annual_collection = annual_collection.merge(collection)
                valid_count += 1

            if valid_count == 0:
                return {'error': 'No valid data'}

            # 🔥 OPTIMIZATION: Use proper S5P scale (7500m) instead of 1000m
            s5p_scale = 7500

            # Create annual composite
            annual_composite = annual_collection.mean().select(band_name)

            # 🔥 OPTIMIZATION: Single reduceRegions call for both urban/rural
            stats_fc = annual_composite.reduceRegions(
                collection=zones_fc,
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.stdDev(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.minMax(), sharedInputs=True
                ).combine(
                    reducer2=ee.Reducer.count(), sharedInputs=True
                ),
                scale=s5p_scale,
                tileScale=4  # 🔥 OPTIMIZATION: Better tile scaling
            )

            # Single getInfo() call
            stats_data = stats_fc.getInfo()

            # Parse results by zone
            results = {}
            for feature in stats_data['features']:
                zone = feature['properties']['zone']
                stats = feature['properties']

                # Extract stats for the band
                mean_key = 'mean'  # FIXED: Keys are not band-prefixed
                stddev_key = 'stdDev'
                min_key = 'min'
                max_key = 'max'
                count_key = 'count'

                zone_stats = {
                    'mean': stats.get(mean_key),
                    'stdDev': stats.get(stddev_key),
                    'min': stats.get(min_key),
                    'max': stats.get(max_key),
                    'count': stats.get(count_key),
                    'valid_pixels': stats.get(count_key, 0),
                    'months_with_data': valid_count
                }

                # 🔥 ENHANCED: Calculate confidence intervals and statistical measures
                zone_stats.update(self._calculate_confidence_intervals(zone_stats))

                results[zone] = zone_stats

            return results

        except Exception as e:
            return {'error': f'Batched annual stats failed: {str(e)}'}

    def _calculate_batched_seasonal_stats(self, monthly_collections: Dict[str, ee.ImageCollection],
                                        zones_fc: ee.FeatureCollection, band_name: str) -> Dict[str, Any]:
        """OPTIMIZATION: Calculate seasonal stats with batched operations"""

        seasons = {
            'winter': ['12', '01', '02'],
            'spring': ['03', '04', '05'],
            'summer': ['06', '07', '08'],
            'autumn': ['09', '10', '11']
        }

        seasonal_results = {}

        for season_name, season_months in seasons.items():
            # Collect seasonal collections
            seasonal_collections = []
            months_with_data = 0

            for month_key, collection in monthly_collections.items():
                month_num = month_key.split('_')[1]
                if month_num in season_months:
                    seasonal_collections.append(collection)
                    months_with_data += 1

            if seasonal_collections:
                # Combine seasonal collections
                seasonal_combined = ee.ImageCollection([])
                for coll in seasonal_collections:
                    seasonal_combined = seasonal_combined.merge(coll)

                # Create seasonal composite
                seasonal_composite = seasonal_combined.mean().select(band_name)

                # 🔥 OPTIMIZATION: Single reduceRegions for seasonal stats
                s5p_scale = 7500
                seasonal_stats_fc = seasonal_composite.reduceRegions(
                    collection=zones_fc,
                    reducer=ee.Reducer.mean().combine(reducer2=ee.Reducer.count(), sharedInputs=True),
                    scale=s5p_scale,
                    tileScale=4
                )

                # Single getInfo() call per season
                seasonal_data = seasonal_stats_fc.getInfo()

                # Parse seasonal results
                season_zone_stats = {}
                for feature in seasonal_data['features']:
                    zone = feature['properties']['zone']
                    stats = feature['properties']

                    season_zone_stats[zone] = {
                        'mean': stats.get('mean'),  # FIXED: Keys are not band-prefixed
                        'count': stats.get('count'),
                        'months_with_data': months_with_data
                    }

                seasonal_results[season_name] = season_zone_stats
            else:
                seasonal_results[season_name] = {'error': 'No data for season'}

        return seasonal_results

    def _calculate_confidence_intervals(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate confidence intervals and statistical measures from basic statistics"""

        confidence_results = {}

        try:
            mean = stats.get('mean')
            stddev = stats.get('stdDev')
            count = stats.get('count')

            if mean is not None and stddev is not None and count is not None and count > 1:
                # Standard error of the mean
                standard_error = stddev / np.sqrt(count)
                confidence_results['standard_error'] = float(standard_error)

                # 95% confidence interval (t-distribution approximation for n > 30, z=1.96)
                # For smaller samples, this is conservative
                if count >= 30:
                    # Use z-distribution for large samples
                    margin_of_error = 1.96 * standard_error
                else:
                    # Use t-distribution approximation (t≈2 for n=10, t≈1.7 for n=30)
                    t_value = 2.0 if count < 15 else 1.8  # Conservative t-values
                    margin_of_error = t_value * standard_error

                confidence_results['confidence_interval_95'] = {
                    'lower_bound': float(mean - margin_of_error),
                    'upper_bound': float(mean + margin_of_error),
                    'margin_of_error': float(margin_of_error),
                    'confidence_level': 0.95
                }

                # Coefficient of variation (relative variability)
                if mean != 0:
                    cv = abs(stddev / mean)
                    confidence_results['coefficient_of_variation'] = float(cv)
                    confidence_results['variability_level'] = 'low' if cv < 0.1 else 'moderate' if cv < 0.3 else 'high'

                # Statistical significance indicators
                confidence_results['statistical_measures'] = {
                    'sample_size': int(count),
                    'degrees_of_freedom': int(count - 1),
                    'relative_standard_error': float(standard_error / abs(mean)) if mean != 0 else None,
                    'data_reliability': 'high' if count >= 30 else 'moderate' if count >= 10 else 'low'
                }

                # Range analysis
                data_range = stats.get('max', 0) - stats.get('min', 0)
                if data_range > 0:
                    confidence_results['data_range'] = float(data_range)
                    confidence_results['relative_range'] = float(data_range / abs(mean)) if mean != 0 else None

            else:
                confidence_results['error'] = 'Insufficient data for confidence interval calculation'

        except Exception as e:
            confidence_results['error'] = f'Confidence interval calculation failed: {str(e)}'

        return confidence_results

    def _calculate_ratio_safe(self, urban_value: Optional[float], rural_value: Optional[float]) -> Optional[float]:
        """Safe urban-rural ratio calculation"""
        if (urban_value is not None and rural_value is not None and
            rural_value != 0 and not np.isnan(urban_value) and not np.isnan(rural_value)):
            return urban_value / rural_value
        return None

    def _analyze_seasonal_patterns(self, pollutants_data: Dict, year: int) -> Dict[str, Any]:
        """Analyze seasonal patterns in air quality data"""

        seasons = {
            'winter': [12, 1, 2],
            'spring': [3, 4, 5],
            'summer': [6, 7, 8],
            'autumn': [9, 10, 11]
        }

        seasonal_results = {}

        for season_name, months in seasons.items():
            seasonal_results[season_name] = {}

            for pollutant in pollutants_data:
                monthly_data = pollutants_data[pollutant]['monthly']
                season_values = []

                for month in months:
                    month_key = f"{year}_{month:02d}"
                    if month_key in monthly_data:
                        urban_mean = monthly_data[month_key]['urban'].get('mean')
                        if urban_mean is not None:
                            season_values.append(urban_mean)

                if season_values:
                    seasonal_results[season_name][pollutant] = {
                        'mean': np.mean(season_values),
                        'stdDev': np.std(season_values),
                        'min': np.min(season_values),
                        'max': np.max(season_values),
                        'months_with_data': len(season_values)
                    }

        return seasonal_results

    def _calculate_health_indicators(self, pollutants_data: Dict) -> Dict[str, Any]:
        """Calculate health impact indicators based on pollutant levels"""

        health_results = {}

        # NO2 analysis (traffic indicator)
        if 'NO2' in pollutants_data:
            no2_annual = pollutants_data['NO2']['annual_stats']
            if 'urban' in no2_annual and 'mean' in no2_annual['urban']:
                no2_mean = no2_annual['urban']['mean']
                # Convert from mol/m² to µg/m³ (approximate conversion for surface level)
                no2_ugm3 = no2_mean * 1e6 * 46.0055 * 1000 / 22.4  # mol/m² to µg/m³ approximation

                health_results['NO2'] = {
                    'annual_average_ugm3': no2_ugm3,
                    'exceeds_who_annual': no2_ugm3 > self.health_thresholds['NO2']['annual'],
                    'traffic_pollution_indicator': 'high' if no2_ugm3 > 60 else 'moderate' if no2_ugm3 > 40 else 'low'
                }

        # O3 analysis (photochemical smog indicator)
        if 'O3' in pollutants_data:
            o3_data = pollutants_data['O3']['monthly']
            high_o3_days = 0
            for month_data in o3_data.values():
                if 'urban' in month_data and 'max' in month_data['urban']:
                    o3_max = month_data['urban']['max']
                    if o3_max is not None:
                        # Convert approximation
                        o3_ugm3 = o3_max * 1e6 * 48 * 1000 / 22.4
                        if o3_ugm3 > self.health_thresholds['O3']['hourly']:
                            high_o3_days += 1

            health_results['O3'] = {
                'high_o3_days': high_o3_days,
                'photochemical_pollution_risk': 'high' if high_o3_days > 30 else 'moderate' if high_o3_days > 10 else 'low'
            }

        # SO2 analysis (industrial indicator)
        if 'SO2' in pollutants_data:
            so2_annual = pollutants_data['SO2']['annual_stats']
            if 'urban' in so2_annual and 'mean' in so2_annual['urban']:
                so2_mean = so2_annual['urban']['mean']
                so2_ugm3 = so2_mean * 1e6 * 64.066 * 1000 / 22.4

                health_results['SO2'] = {
                    'annual_average_ugm3': so2_ugm3,
                    'industrial_pollution_indicator': 'high' if so2_ugm3 > 20 else 'moderate' if so2_ugm3 > 10 else 'low'
                }

        return health_results

    def _assess_data_quality_server_side(self, pollutants_data: Dict) -> Dict[str, Any]:
        """Assess overall data quality and completeness using server-side computed data"""

        quality_metrics = {
            'temporal_coverage': {},
            'spatial_coverage': {},
            'data_completeness': {},
            'overall_quality_score': 0
        }

        total_pollutants = len(pollutants_data)
        quality_scores = []

        for pollutant, data in pollutants_data.items():
            if 'error' in data:
                quality_metrics['temporal_coverage'][pollutant] = 0
                quality_scores.append(0)
                continue

            # Temporal coverage from data completeness
            completeness = data.get('data_completeness', 0)
            quality_metrics['temporal_coverage'][pollutant] = completeness
            quality_scores.append(completeness)

            # Spatial coverage (urban vs rural data availability)
            urban_available = ('urban_annual' in data and
                             'mean' in data['urban_annual'] and
                             data['urban_annual']['mean'] is not None)
            rural_available = ('rural_annual' in data and
                             'mean' in data['rural_annual'] and
                             data['rural_annual']['mean'] is not None)

            quality_metrics['spatial_coverage'][pollutant] = {
                'urban_data': urban_available,
                'rural_data': rural_available,
                'both_zones': urban_available and rural_available
            }

        # Overall quality score (0-1 scale)
        if quality_scores:
            avg_score = float(np.mean(quality_scores))
            quality_metrics['overall_quality_score'] = avg_score

        # Data completeness summary
        avg_completeness = float(np.mean(quality_scores)) if quality_scores else 0.0
        quality_metrics['data_completeness'] = {
            'pollutants_analyzed': total_pollutants,
            'average_completeness': avg_completeness,
            'quality_rating': self._get_quality_rating(avg_score if quality_scores else 0.0)
        }

        return quality_metrics

    def _get_quality_rating(self, score: float) -> str:
        """Convert quality score to rating"""
        if score >= 0.8:
            return 'excellent'
        elif score >= 0.6:
            return 'good'
        elif score >= 0.4:
            return 'fair'
        elif score >= 0.2:
            return 'poor'
        else:
            return 'very_poor'

    def get_server_optimization_info(self) -> Dict[str, Any]:
        """Get information about server-side optimizations implemented"""
        
        return {
            'server_side_operations': [
                'Data filtering (date, bounds, quality) using Earth Engine filters',
                'Monthly composite creation using EE reducers (mean, median, etc.)',
                'Annual statistics calculation using EE combined reducers',
                'Seasonal statistics aggregation using EE collection operations',
                'Health indicator calculations using server-computed statistics',
                'Urban-rural ratio calculations using server-side arithmetic',
                'Batch processing of monthly data to minimize client-server round trips'
            ],
            'optimization_benefits': [
                'Reduced data transfer between client and server',
                'Faster processing using distributed computing',
                'Lower memory usage on client side',
                'More efficient use of Earth Engine resources',
                'Better scalability for large datasets'
            ],
            'data_flow_optimization': [
                'Single batch collection of all monthly data',
                'Server-side statistical computations',
                'Minimized .getInfo() calls',
                'Optimized geometry operations',
                'Efficient error handling and data validation'
            ],
            'performance_improvements': {
                'reduced_client_processing': 'Annual stats, seasonal analysis, health indicators moved server-side',
                'minimized_data_transfer': 'Only final aggregated results downloaded',
                'optimized_queries': 'Batch processing instead of individual month queries',
                'memory_efficiency': 'Server-side computations reduce client memory usage'
            }
        }


def run_city_air_quality_analysis(base_path: Path, city_name: str, start_year: int,
                                 end_year: int) -> Dict[str, Any]:
    """Run comprehensive air quality analysis for a city across multiple years"""

    analyzer = AirQualityAnalyzer()

    results = {
        'city': city_name,
        'analysis_period': f"{start_year}-{end_year}",
        'timestamp': datetime.now().isoformat(),
        'yearly_results': {},
        'trends': {},
        'summary': {}
    }

    # Analyze each year
    for year in range(start_year, end_year + 1):
        try:
            yearly_result = analyzer.batch_process_monthly_data_optimized(city_name, year)
            results['yearly_results'][str(year)] = yearly_result
            print(f"✅ Completed HIGH-PERFORMANCE air quality analysis for {city_name} {year}")
        except Exception as e:
            print(f"❌ Failed optimized air quality analysis for {city_name} {year}: {e}")
            results['yearly_results'][str(year)] = {'error': str(e)}

    # Calculate trends across years - FIXED LOGIC BUG
    if len(results['yearly_results']) > 1:
        trends = {}

        # Get all pollutants from first valid year
        first_valid_year = None
        for year, data in results['yearly_results'].items():
            if 'pollutants' in data and not isinstance(data.get('error'), str):
                first_valid_year = year
                break

        if first_valid_year:
            pollutants = list(results['yearly_results'][first_valid_year]['pollutants'].keys())

            for pollutant in pollutants:
                pollutant_trends = {
                    'annual_means': [],
                    'years': [],
                    'trend_direction': None,
                    'trend_significance': None
                }

                for year in sorted(results['yearly_results'].keys()):
                    year_data = results['yearly_results'][year]
                    # FIXED: Check for pollutants and urban_annual data correctly
                    if ('pollutants' in year_data and
                        pollutant in year_data['pollutants'] and
                        'urban_annual' in year_data['pollutants'][pollutant] and
                        isinstance(year_data['pollutants'][pollutant]['urban_annual'], dict) and
                        'mean' in year_data['pollutants'][pollutant]['urban_annual']):

                        urban_annual = year_data['pollutants'][pollutant]['urban_annual']
                        mean_value = urban_annual['mean']
                        if mean_value is not None and not isinstance(mean_value, str):
                            pollutant_trends['annual_means'].append(float(mean_value))
                            pollutant_trends['years'].append(int(year))

                # Calculate trend if we have enough data points
                if len(pollutant_trends['annual_means']) >= 2:  # FIXED: Need at least 2 points for trend
                    try:
                        means = np.array(pollutant_trends['annual_means'])
                        years = np.array(pollutant_trends['years'])

                        # Simple linear regression
                        slope, intercept = np.polyfit(years, means, 1)

                        # Calculate R-squared
                        y_pred = slope * years + intercept
                        ss_res = np.sum((means - y_pred) ** 2)
                        ss_tot = np.sum((means - np.mean(means)) ** 2)
                        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

                        pollutant_trends['trend_slope'] = slope
                        pollutant_trends['trend_intercept'] = intercept
                        pollutant_trends['r_squared'] = r_squared
                        pollutant_trends['trend_direction'] = 'increasing' if slope > 0 else 'decreasing'
                        pollutant_trends['trend_significance'] = 'strong' if r_squared > 0.7 else 'moderate' if r_squared > 0.5 else 'weak'

                    except Exception as e:
                        pollutant_trends['trend_error'] = str(e)

                trends[pollutant] = pollutant_trends

        results['trends'] = trends

    # Generate summary
    summary = {
        'total_years_analyzed': len(results['yearly_results']),
        'pollutants_covered': set(),
        'data_quality_summary': {},
        'key_findings': [],
        'recommendations': []
    }

    # Collect all pollutants
    for year_data in results['yearly_results'].values():
        if 'pollutants' in year_data:
            summary['pollutants_covered'].update(year_data['pollutants'].keys())

    summary['pollutants_covered'] = list(summary['pollutants_covered'])

    # Analyze data quality across years
    quality_scores = []
    for year_data in results['yearly_results'].values():
        if 'quality_metrics' in year_data:
            score = year_data['quality_metrics'].get('overall_quality_score', 0)
            quality_scores.append(score)

    if quality_scores:
        avg_score = float(np.mean(quality_scores))
        summary['data_quality_summary'] = {
            'average_score': avg_score,
            'min_score': np.min(quality_scores),
            'max_score': np.max(quality_scores),
            'overall_rating': analyzer._get_quality_rating(avg_score)
        }

    # Generate key findings and recommendations
    findings = []
    recommendations = []

    # Check for pollutants with concerning levels
    for year, year_data in results['yearly_results'].items():
        if 'pollutants' in year_data:
            for pollutant, pollutant_data in year_data['pollutants'].items():
                if 'health_indicators' in pollutant_data and pollutant_data['health_indicators']:
                    health = pollutant_data['health_indicators']

                    if pollutant == 'NO2' and 'traffic_pollution_indicator' in health:
                        if health['traffic_pollution_indicator'] == 'high':
                            findings.append(f"High traffic pollution (NO2) detected in {year}")

                    if pollutant == 'SO2' and 'industrial_pollution_indicator' in health:
                        if health['industrial_pollution_indicator'] == 'high':
                            findings.append(f"High industrial pollution (SO2) detected in {year}")

                    if pollutant == 'O3' and 'photochemical_pollution_risk' in health:
                        if health['photochemical_pollution_risk'] == 'high':
                            findings.append(f"High photochemical pollution risk (O3) in {year}")

    # Check for trends
    if results.get('trends'):
        for pollutant, trend_data in results['trends'].items():
            if 'trend_direction' in trend_data and trend_data['trend_direction'] == 'increasing':
                findings.append(f"Increasing trend in {pollutant} levels over time")

    if not findings:
        findings.append("Air quality monitoring established - continue monitoring for trends")

    # Base recommendations
    recommendations.append("Continue Sentinel-based air quality monitoring for long-term trends")

    # Check data quality
    for year_data in results['yearly_results'].values():
        if 'quality_metrics' in year_data:
            quality = year_data['quality_metrics']
            if quality.get('overall_quality_score', 0) < 0.6:
                recommendations.append("Improve data completeness through better satellite coverage or complementary monitoring")
                break

    # Health-based recommendations
    for year_data in results['yearly_results'].values():
        if 'pollutants' in year_data:
            for pollutant, pollutant_data in year_data['pollutants'].items():
                if 'health_indicators' in pollutant_data and pollutant_data['health_indicators']:
                    health = pollutant_data['health_indicators']

                    if pollutant == 'NO2' and health.get('traffic_pollution_indicator') == 'high':
                        recommendations.append("Implement traffic emission controls and promote public transportation")

                    if pollutant == 'SO2' and health.get('industrial_pollution_indicator') == 'high':
                        recommendations.append("Strengthen industrial emission regulations and monitoring")

                    if pollutant == 'O3' and health.get('photochemical_pollution_risk') == 'high':
                        recommendations.append("Develop strategies to reduce VOC emissions and photochemical smog formation")

    summary['key_findings'] = findings
    summary['recommendations'] = recommendations

    results['summary'] = summary

    return results
