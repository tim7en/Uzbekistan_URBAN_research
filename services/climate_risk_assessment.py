"""
IPCC AR6 Climate Risk Assessment Service
Implements the IPCC AR6 framework for urban climate risk assessment
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .climate_data_loader import ClimateDataLoader, CityPopulationData


@dataclass
class ClimateRiskMetrics:
    """Climate risk assessment metrics for a city"""
    city: str
    population: Optional[int] = None
    gdp_per_capita_usd: Optional[float] = None
    
    # IPCC AR6 Core Components
    hazard_score: float = 0.0
    exposure_score: float = 0.0
    vulnerability_score: float = 0.0
    adaptive_capacity_score: float = 0.0
    
    # Individual hazard components
    heat_hazard: float = 0.0
    dry_hazard: float = 0.0
    dust_hazard: float = 0.0
    pluvial_hazard: float = 0.0
    
    # Individual exposure components
    population_exposure: float = 0.0
    gdp_exposure: float = 0.0
    viirs_exposure: float = 0.0
    
    # Individual vulnerability components
    income_vulnerability: float = 0.0
    veg_access_vulnerability: float = 0.0
    fragmentation_vulnerability: float = 0.0
    bio_trend_vulnerability: float = 0.0
    
    # Social Sector Vulnerability Components
    water_access_vulnerability: float = 0.0
    healthcare_access_vulnerability: float = 0.0
    education_access_vulnerability: float = 0.0
    sanitation_vulnerability: float = 0.0
    building_age_vulnerability: float = 0.0
    
    # Water Scarcity Components
    water_supply_risk: float = 0.0
    water_demand_risk: float = 0.0
    overall_water_scarcity_score: float = 0.0
    water_scarcity_level: str = "Unknown"
    aridity_index: float = 0.0
    climatic_water_deficit: float = 0.0
    drought_frequency: float = 0.0
    surface_water_change: float = 0.0
    cropland_fraction: float = 0.0
    
    # Individual adaptive capacity components
    gdp_adaptive_capacity: float = 0.0
    greenspace_adaptive_capacity: float = 0.0
    services_adaptive_capacity: float = 0.0
    
    # Social Sector Adaptive Capacity Components
    social_infrastructure_capacity: float = 0.0
    water_system_capacity: float = 0.0
    
    # Composite scores
    overall_risk_score: float = 0.0
    hev_score: float = 0.0  # H×E×V (original risk without adaptive capacity)
    hev_adj_score: float = 0.0  # H×E×V×(1-AC) (risk adjusted for adaptive capacity)
    adaptability_score: float = 0.0
    
    # Supporting metrics
    current_suhi_intensity: float = 0.0
    temperature_trend: float = 0.0
    suhi_trend: float = 0.0
    built_area_percentage: float = 0.0
    green_space_accessibility: float = 0.0
    economic_capacity: float = 0.0
    
    # Air Quality Components
    air_quality_hazard: float = 0.0
    air_pollution_vulnerability: float = 0.0
    air_quality_adaptive_capacity: float = 0.0
    
    # Air Quality Supporting Metrics
    co_level: float = 0.0
    no2_level: float = 0.0
    o3_level: float = 0.0
    so2_level: float = 0.0
    ch4_level: float = 0.0
    aerosol_index: float = 0.0
    air_quality_trend: float = 0.0
    health_risk_score: float = 0.0


class IPCCRiskAssessmentService:
    """Service for computing IPCC AR6-based climate risk assessments"""
    
    def __init__(self, data_loader: ClimateDataLoader):
        self.data_loader = data_loader
        self.data = data_loader.load_all_data()
        
        # Load water scarcity data
        self.water_scarcity_data = self._load_water_scarcity_data()
        
        # IPCC AR6 risk thresholds and weights
        self.risk_thresholds = {
            'heat_stress': {'low': 1.0, 'medium': 2.0, 'high': 3.0, 'very_high': 4.0},
            'temperature_trend': {'low': 0.02, 'medium': 0.05, 'high': 0.08, 'very_high': 0.12},  # °C/year
            'urban_expansion': {'low': 0.02, 'medium': 0.05, 'high': 0.08, 'very_high': 0.12}  # fraction/year
        }
        
        # IPCC AR6 hazard weights (from specification)
        self.hazard_weights = {
            'heat': 0.50,
            'dry': 0.20,
            'pluv': 0.10,
            'dust': 0.05,
            'air_quality': 0.15
        }
        
        # IPCC AR6 exposure weights (from specification)
        self.exposure_weights = {
            'population': 0.60,
            'gdp': 0.25,
            'viirs': 0.15
        }
        
        # IPCC AR6 vulnerability weights (from specification)
        self.vulnerability_weights = {
            'income_inv': 0.15,
            'veg_access': 0.10,
            'fragment': 0.06,
            'delta_bio_veg': 0.05,
            'water_scarcity': 0.18,    # Water scarcity vulnerability (critical for arid regions)
            'water_access': 0.12,      # Social sector: water infrastructure vulnerability
            'healthcare_access': 0.05, # Social sector: healthcare access vulnerability
            'education_access': 0.04,  # Social sector: education access vulnerability
            'sanitation': 0.03,        # Social sector: sanitation vulnerability
            'building_age': 0.04,      # Social sector: building age and renovation vulnerability
            'air_pollution': 0.18      # Air pollution vulnerability (health impacts)
        }
        
        # IPCC AR6 adaptive capacity weights (from specification)
        self.adaptive_capacity_weights = {
            'gdp_pc': 0.35,
            'greenspace': 0.20,
            'services': 0.12,
            'social_infrastructure': 0.13,  # Social sector: schools, hospitals per capita
            'water_system': 0.05,          # Social sector: water system resilience
            'air_quality_management': 0.15  # Air quality management and monitoring capacity
        }
    
    def _load_water_scarcity_data(self) -> Dict[str, Dict]:
        """Load water scarcity assessment data from existing JSON files"""
        try:
            from pathlib import Path
            import json
            
            water_scarcity_dir = self.data_loader.base_path / 'water_scarcity'
            water_dict = {}
            
            if water_scarcity_dir.exists():
                for city_dir in water_scarcity_dir.iterdir():
                    if city_dir.is_dir():
                        city_name = city_dir.name
                        water_file = city_dir / 'water_scarcity_assessment.json'
                        
                        if water_file.exists():
                            try:
                                with open(water_file, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                
                                # Extract relevant fields for risk assessment
                                water_dict[city_name] = {
                                    'water_scarcity_index': data.get('overall_water_scarcity_score', 0.0),
                                    'drought_frequency': data.get('drought_frequency', 0.0),
                                    'water_stress_level': data.get('aqueduct_bws_score'),
                                    'irrigation_demand': data.get('cropland_fraction', 0.0),
                                    'surface_water_availability': data.get('surface_water_change', 0.0),
                                    'aridity_index': data.get('aridity_index', 0.2),
                                    'climatic_water_deficit': data.get('climatic_water_deficit', 0.0),
                                    'water_supply_risk': data.get('water_supply_risk', 0.0),
                                    'water_demand_risk': data.get('water_demand_risk', 0.0),
                                    'water_scarcity_level': data.get('water_scarcity_level', 'Unknown')
                                }
                                
                            except Exception as e:
                                print(f"Warning: Could not load water scarcity data for {city_name}: {e}")
                                continue
                    
            if water_dict:
                print(f"Loaded water scarcity data for {len(water_dict)} cities from existing files")
            else:
                print("Warning: No water scarcity data files found - water scarcity vulnerability will be set to default values")
            
            return water_dict
            
        except Exception as e:
            print(f"Warning: Could not load water scarcity data: {e}")
            return {}
    
    def assess_all_cities(self) -> Dict[str, ClimateRiskMetrics]:
        """Run full climate risk assessment for all cities"""
        print("Running IPCC AR6-based climate risk assessment...")
        
        # Assess all cities from population data (which includes all UZBEKISTAN_CITIES)
        all_cities = list(self.data['population_data'].keys())
        
        results = {}
        for city in all_cities:
            print(f"Assessing {city}...")
            results[city] = self.assess_city_climate_risk(city)
        
        print(f"[OK] Completed assessment for {len(results)} cities")
        
        # Quick distribution sanity check (skip when no cities)
        if not results:
            print("No city data available; skipping distribution sanity checks.")
            return results

        ac = [m.adaptive_capacity_score for m in results.values()]
        rk = [m.overall_risk_score for m in results.values()]
        pr = [(r ** 0.8) * ((1 - a) ** 0.6) for r, a in zip(rk, ac)]
        print(f"AC median={np.median(ac):.3f}  IQR=({np.quantile(ac,0.25):.3f},{np.quantile(ac,0.75):.3f})")
        print(f"Risk median={np.median(rk):.3f}  IQR=({np.quantile(rk,0.25):.3f},{np.quantile(rk,0.75):.3f})")
        print(f"Priority median={np.median(pr):.3f}  IQR=({np.quantile(pr,0.25):.3f},{np.quantile(pr,0.75):.3f})")

        return results
    
    def assess_city_climate_risk(self, city: str) -> ClimateRiskMetrics:
        """Assess climate risk for a single city using IPCC AR6 framework"""
        metrics = ClimateRiskMetrics(city=city)
        
        # Get city population data
        population_data = self.data['population_data'].get(city)
        if population_data:
            metrics.population = population_data.population_2024
            metrics.gdp_per_capita_usd = population_data.gdp_per_capita_usd
        
        # Calculate IPCC AR6 components with individual sub-components
        metrics = self._calculate_hazard_components(city, metrics)
        metrics = self._calculate_exposure_components(city, metrics)
        metrics = self._calculate_vulnerability_components(city, metrics)
        metrics = self._calculate_adaptive_capacity_components(city, metrics)
        
        # Load and integrate social sector data
        social_data = self._load_social_sector_data(city)
        if social_data:
            metrics = self._integrate_social_sector_data(city, metrics, social_data)
        
        # Calculate composite scores using IPCC AR6 weights (only if social sector data not integrated)
        if not social_data:
            metrics.hazard_score = (
                self.hazard_weights['heat'] * metrics.heat_hazard +
                self.hazard_weights['dry'] * metrics.dry_hazard +
                self.hazard_weights['pluv'] * metrics.pluvial_hazard +
                self.hazard_weights['dust'] * metrics.dust_hazard +
                self.hazard_weights['air_quality'] * metrics.air_quality_hazard
            )
            
            metrics.exposure_score = (
                self.exposure_weights['population'] * metrics.population_exposure +
                self.exposure_weights['gdp'] * metrics.gdp_exposure +
                self.exposure_weights['viirs'] * metrics.viirs_exposure
            )
            
            metrics.vulnerability_score = (
                self.vulnerability_weights['income_inv'] * metrics.income_vulnerability +
                self.vulnerability_weights['veg_access'] * metrics.veg_access_vulnerability +
                self.vulnerability_weights['fragment'] * metrics.fragmentation_vulnerability +
                self.vulnerability_weights['delta_bio_veg'] * metrics.bio_trend_vulnerability +
                self.vulnerability_weights['water_scarcity'] * metrics.water_scarcity_vulnerability +
                self.vulnerability_weights['air_pollution'] * metrics.air_pollution_vulnerability
            )
            
            metrics.adaptive_capacity_score = (
                self.adaptive_capacity_weights['gdp_pc'] * metrics.gdp_adaptive_capacity +
                self.adaptive_capacity_weights['greenspace'] * metrics.greenspace_adaptive_capacity +
                self.adaptive_capacity_weights['services'] * metrics.services_adaptive_capacity +
                self.adaptive_capacity_weights['air_quality_management'] * metrics.air_quality_adaptive_capacity
            )
        else:
            # Recalculate composite scores with social sector components
            metrics.vulnerability_score = (
                self.vulnerability_weights['income_inv'] * metrics.income_vulnerability +
                self.vulnerability_weights['veg_access'] * metrics.veg_access_vulnerability +
                self.vulnerability_weights['fragment'] * metrics.fragmentation_vulnerability +
                self.vulnerability_weights['delta_bio_veg'] * metrics.bio_trend_vulnerability +
                self.vulnerability_weights['water_access'] * metrics.water_access_vulnerability +
                self.vulnerability_weights['healthcare_access'] * metrics.healthcare_access_vulnerability +
                self.vulnerability_weights['education_access'] * metrics.education_access_vulnerability +
                self.vulnerability_weights['sanitation'] * metrics.sanitation_vulnerability +
                self.vulnerability_weights['building_age'] * metrics.building_age_vulnerability +
                self.vulnerability_weights['air_pollution'] * metrics.air_pollution_vulnerability
            )
            
            metrics.adaptive_capacity_score = (
                self.adaptive_capacity_weights['gdp_pc'] * metrics.gdp_adaptive_capacity +
                self.adaptive_capacity_weights['greenspace'] * metrics.greenspace_adaptive_capacity +
                self.adaptive_capacity_weights['services'] * metrics.services_adaptive_capacity +
                self.adaptive_capacity_weights['social_infrastructure'] * metrics.social_infrastructure_capacity +
                self.adaptive_capacity_weights['water_system'] * metrics.water_system_capacity +
                self.adaptive_capacity_weights['air_quality_management'] * metrics.air_quality_adaptive_capacity
            )
        
        # Apply region-specific corrections for known data gaps
        #metrics = self._apply_regional_corrections(city, metrics)
        
        # Calculate composite scores
        metrics.overall_risk_score = self._calculate_overall_risk(metrics)
        metrics.adaptability_score = self._calculate_adaptability_score(metrics)
        
        # Populate additional metrics
        self._populate_supporting_metrics(city, metrics)
        
        return metrics
    
    def calculate_hazard_score(self, city: str) -> float:
        """Calculate climate hazard score using comprehensive temperature statistics"""
        # Use only temperature data - no fallbacks to SUHI or climatological estimates
        city_data = self.data['temperature_data'].get(city, {})
        if not city_data:
            # No temperature data available - do not apply climatological fallback
            # Return 0.0 so the assessment reflects only available observations
            # (caller _calculate_heat_hazard will treat 0.0 as missing)
            return 0.0  # Return 0.0 if no temperature data available
        
        years = sorted(city_data.keys())
        # Require at least 2 years of data for meaningful trend analysis
        if len(years) < 2:
            return 0.0  # Insufficient data for assessment

        # Current hazard intensity (latest year summer temperatures)
        latest_year = years[-1]
        latest_stats = city_data[latest_year]

        # Use summer season summary for more accurate assessment
        summer_stats = latest_stats.get('summer_season_summary', {})
        if not summer_stats:
            return 0.0  # No summer data available

        # Extract temperature statistics from actual data structure
        urban_data = summer_stats.get('urban', {})
        if not urban_data:
            return 0.0  # No urban temperature data

        urban_day = urban_data.get('day', {})
        if not urban_day:
            return 0.0  # No daytime temperature data

        # Extract actual temperature values - use realistic defaults for Uzbekistan climate
        mean_summer_temp = urban_day.get('mean')
        max_summer_temp = urban_day.get('max')
        p90_summer_temp = urban_day.get('p90')

        # If key statistics are missing, cannot perform assessment
        if mean_summer_temp is None or max_summer_temp is None or p90_summer_temp is None:
            return 0.0

        # Heat stress indicators - derive from available statistics with adjusted thresholds for MODIS data
        # MODIS LST is generally smoother and may underestimate extremes compared to Landsat —
        # lower the thresholds and relax some checks so valid but sparser MODIS-derived extremes are counted.
        extreme_heat_days = 0
        very_hot_days = 0

        # Extreme heat: max > 42°C (severe heat waves) or p90 > 40°C (persistent extreme heat)
        # Adjusted thresholds for Central Asia
        if max_summer_temp > 38:      # Lowered from 42°C
            extreme_heat_days = 15
        elif p90_summer_temp > 35:    # Lowered from 40°C  
            extreme_heat_days = 8
        elif p90_summer_temp > 32:    # Added intermediate threshold
            extreme_heat_days = 3

            
        # Very hot days: p90 > 36°C (hot summers) or mean > 34°C (generally hot)
        if p90_summer_temp > 36:
            very_hot_days = 45      # Very hot summer
        elif p90_summer_temp > 34:
            very_hot_days = 25      # Hot summer
        elif mean_summer_temp > 34:
            very_hot_days = 15      # Moderately hot summer

        # Temperature trend analysis (warming rate)
        temp_trends = []
        for temp_type in ['day', 'night']:
            values = []
            years_list = []
            for year in years:
                year_data = city_data[year]
                summer_data = year_data.get('summer_season_summary', {})
                urban_temp_data = summer_data.get('urban', {})
                temp_data = urban_temp_data.get(temp_type, {})
                temp_val = temp_data.get('mean')

                if temp_val is not None:
                    values.append(temp_val)
                    years_list.append(int(year))

            if len(values) >= 3:  # Need at least 3 points for reliable trend
                try:
                    trend = np.polyfit(years_list, values, 1)[0]  # °C per year
                    temp_trends.append(trend)
                except:
                    pass

        avg_temp_trend = np.mean(temp_trends) if temp_trends else 0.0

        # IPCC AR6 hazard scoring with adjusted thresholds for MODIS data
        # Current intensity (40% weight)
        intensity_score = 0.0
        if extreme_heat_days > 10:
            intensity_score = 1.0
        elif extreme_heat_days > 5:
            intensity_score = 0.7
        elif very_hot_days > 20:
            intensity_score = 0.5
        elif mean_summer_temp > 28:    # lowered threshold to reflect MODIS bias
            intensity_score = 0.3

        # Temperature trend (40% weight) - adjusted for more realistic warming rates for MODIS
        trend_score = 0.0
        if avg_temp_trend > 0.06:  # Very high warming
            trend_score = 1.0
        elif avg_temp_trend > 0.03:  # High warming
            trend_score = 0.7
        elif avg_temp_trend > 0.015:  # Medium warming
            trend_score = 0.4
        elif avg_temp_trend > 0.0:  # Low warming
            trend_score = 0.2

        # Maximum temperature threshold (20% weight) - adjusted for MODIS characteristics
        # Make max temperature more sensitive by lowering baseline
        max_temp_score = min(1.0, max(0.0, (max_summer_temp - 33) / 9))

        hazard_score = (0.4 * intensity_score + 0.4 * trend_score + 0.2 * max_temp_score)
        return min(1.0, hazard_score)
    
    def _calculate_hazard_from_suhi(self, city: str, city_data: Dict) -> float:
        """Calculate hazard score from SUHI data when temperature data unavailable"""
        years = sorted([int(y) for y in city_data.keys()])
        if len(years) < 2:
            return 0.0
        
        # Get SUHI intensity trend
        suhi_values = []
        temp_values = []
        for year in years:
            year_str = str(year)
            if year_str in city_data:
                stats = city_data[year_str].get('stats', {})
                suhi_val = stats.get('suhi_night', 0)
                temp_val = stats.get('night_urban_mean', 0)
                if suhi_val > 0:
                    suhi_values.append(suhi_val)
                if temp_val > 0:
                    temp_values.append(temp_val)
        
        if not suhi_values:
            return 0.0
        
        current_suhi = suhi_values[-1] if suhi_values else 0
        
        # SUHI-based hazard assessment
        if current_suhi > 4.0:
            intensity_score = 1.0
        elif current_suhi > 2.5:
            intensity_score = 0.7
        elif current_suhi > 1.5:
            intensity_score = 0.5
        else:
            intensity_score = max(0.0, current_suhi / 3.0)
        
        # Calculate trend if enough data
        trend_score = 0.0
        if len(suhi_values) >= 3:
            try:
                trend = np.polyfit(years[-len(suhi_values):], suhi_values, 1)[0]
                if trend > 0.1:
                    trend_score = 1.0
                elif trend > 0.05:
                    trend_score = 0.6
                elif trend > 0.02:
                    trend_score = 0.3
            except:
                pass
        
        return min(1.0, 0.7 * intensity_score + 0.3 * trend_score)
    
    def calculate_exposure_score(self, city: str) -> float:
        """Calculate exposure score based on population and urban density"""
        population_data = self.data['population_data'].get(city)
        if not population_data:
            return 0.0
        
        # Ensure cache exists
        if 'cache' not in self.data:
            print(f"Warning: Data cache not available for {city} - exposure score set to 0.0")
            return 0.0
        
        # Population exposure (normalized by city population distribution)
        pop_score = self.data_loader.pct_norm(
            self.data['cache'].get('population', []), 
            population_data.population_2024
        )
        
        # Urban density exposure
        density_score = self.data_loader.pct_norm(
            self.data['cache'].get('density', []), 
            population_data.density_per_km2
        )
        
        # Built environment exposure from LULC data
        built_score = 0.0
        for lulc_city in self.data['lulc_data']:
            if lulc_city.get('city') == city:
                areas = lulc_city.get('areas_m2', {})
                if areas:
                    years = sorted([int(y) for y in areas.keys()])
                    if years:
                        latest_year = str(years[-1])
                        built_pct = areas[latest_year].get('Built_Area', {}).get('percentage', 0)
                        built_score = self.data_loader.pct_norm(
                            self.data['cache'].get('built_pct', []), built_pct
                        )
                break
        
        # Economic activity exposure (nightlights as proxy)
        nightlight_score = 0.0
        for nl_city in self.data['nightlights_data']:
            if nl_city.get('city') == city:
                years_data = nl_city.get('years', {})
                if years_data:
                    years = sorted([int(y) for y in years_data.keys()])
                    if years:
                        latest_year = str(years[-1])
                        urban_nl = years_data[latest_year].get('stats', {}).get('urban_core', {}).get('mean', 0)
                        nightlight_score = self.data_loader.pct_norm(
                            self.data['cache'].get('nightlights', []), urban_nl
                        )
                break
        
        # Weighted exposure score
        exposure_score = (0.4 * pop_score + 0.25 * density_score + 
                         0.2 * built_score + 0.15 * nightlight_score)
        
        return min(1.0, exposure_score)
    
    def calculate_vulnerability_score(self, city: str) -> float:
        """Calculate vulnerability score based on socioeconomic and environmental factors"""
        population_data = self.data['population_data'].get(city)
        if not population_data:
            return 0.0
        
        # Ensure cache exists
        if 'cache' not in self.data:
            print(f"Warning: Data cache not available for {city} - vulnerability score set to 0.0")
            return 0.0
        
        # Economic vulnerability (inverted GDP per capita)
        gdp_vulnerability = self.data_loader.pct_norm(
            self.data['cache'].get('gdp', []), 
            population_data.gdp_per_capita_usd, 
            invert=True  # Lower GDP = higher vulnerability
        )
        
        # Urban heat vulnerability (built area percentage)
        built_vulnerability = 0.0
        for lulc_city in self.data['lulc_data']:
            if lulc_city.get('city') == city:
                areas = lulc_city.get('areas_m2', {})
                if areas:
                    years = sorted([int(y) for y in areas.keys()])
                    if years:
                        latest_year = str(years[-1])
                        built_pct = areas[latest_year].get('Built_Area', {}).get('percentage', 0)
                        built_vulnerability = self.data_loader.pct_norm(
                            self.data['cache'].get('built_pct', []), built_pct
                        )
                break
        
        # Green space access vulnerability (based on distance to vegetation)
        green_vulnerability = 0.0
        spatial_city_data = self.data['spatial_data'].get('per_year', {}).get(city, {})
        if spatial_city_data:
            years = sorted([int(y) for y in spatial_city_data.keys()])
            if years:
                latest_year = str(years[-1])
                veg_distance_m = spatial_city_data[latest_year].get('vegetation_accessibility', {}).get('city', {}).get('mean', 1000)
                
                # Convert distance (meters) to accessibility score (closer = better accessibility)
                max_walking_distance = 1000  # 1km as reasonable walking distance
                accessibility_score = max(0.0, 1.0 - (veg_distance_m / max_walking_distance))
                
                # Higher distance = higher vulnerability
                green_vulnerability = 1.0 - accessibility_score
        
        # Water scarcity vulnerability
        water_vulnerability = 0.0
        if city in self.water_scarcity_data:
            water_data = self.water_scarcity_data[city]
            # Use water scarcity index as vulnerability (higher scarcity = higher vulnerability)
            water_vulnerability = water_data.get('water_scarcity_index', 0.0)
        
        # Air pollution vulnerability (based on PM2.5 levels)
        air_vulnerability = 0.0
        if city in self.data['air_quality_data']:
            air_data = self.data['air_quality_data'][city]
            if 'pm25' in air_data:
                pm25_level = air_data['pm25']
                # Higher PM2.5 levels = higher vulnerability
                air_vulnerability = min(1.0, pm25_level / 35.0)  # 35 µg/m³ as threshold for high risk
            else:
                # Use air quality hazard as proxy for air pollution vulnerability
                air_hazard = self._calculate_air_quality_hazard(city)
                air_vulnerability = min(1.0, air_hazard * 0.8)  # Scale down hazard to vulnerability
                
        # Weighted vulnerability score
        vulnerability_score = (0.4 * gdp_vulnerability + 0.25 * built_vulnerability + 
                              0.15 * green_vulnerability + 0.2 * water_vulnerability +
                              0.18 * air_vulnerability)  # Include air pollution vulnerability
        
        return min(1.0, vulnerability_score)
    
    def calculate_adaptive_capacity_score(self, city: str) -> float:
        """Calculate adaptive capacity score based on economic and environmental resources"""
        population_data = self.data['population_data'].get(city)
        if not population_data:
            return 0.0
        
        # Ensure cache exists
        if 'cache' not in self.data:
            print(f"Warning: Data cache not available for {city} - adaptive capacity score set to 0.0")
            return 0.0
        
        # Economic adaptive capacity
        economic_capacity = self.data_loader.pct_norm(
            self.data['cache']['gdp'], 
            population_data.gdp_per_capita_usd
        )
        
        # Green infrastructure capacity
        green_capacity = 0.0
        spatial_city_data = self.data['spatial_data'].get('per_year', {}).get(city, {})
        if spatial_city_data:
            years = sorted([int(y) for y in spatial_city_data.keys()])
            if years:
                latest_year = str(years[-1])
                veg_distance_m = spatial_city_data[latest_year].get('vegetation_accessibility', {}).get('city', {}).get('mean', 1000)
                veg_patches = spatial_city_data[latest_year].get('veg_patches', {}).get('patch_count', 0)
                
                # Convert distance (meters) to accessibility score (closer = better accessibility)
                max_walking_distance = 1000  # 1km as reasonable walking distance
                accessibility_score = max(0.0, 1.0 - (veg_distance_m / max_walking_distance))
                
                # Combine accessibility with patch diversity
                green_capacity = accessibility_score * 0.7 + self.data_loader.pct_norm(
                    self.data['cache']['veg_patches'], veg_patches
                ) * 0.3
        
        # Urban size capacity (larger cities often have more resources)
        size_capacity = self.data_loader.pct_norm(
            self.data['cache']['population'], 
            population_data.population_2024
        )
        
        # Weighted adaptive capacity
        adaptive_capacity = (0.5 * economic_capacity + 0.3 * green_capacity + 
                           0.2 * size_capacity)
        
        return min(1.0, adaptive_capacity)
    
    def _calculate_water_access_vulnerability(self, sanitation_indicators: Dict[str, Any]) -> float:
        """Calculate water access vulnerability from sanitation indicators"""
        try:
            # Extract water source distribution
            water_sources = sanitation_indicators.get('water_sources', {})
            
            # Get electricity access percentage
            electricity_access_pct = sanitation_indicators.get('electricity_access', 0.0)
            
            # Calculate vulnerability based on water source quality
            # Higher vulnerability for carried/none sources, lower for centralized
            centralized = water_sources.get('centralized', 0)
            local = water_sources.get('local', 0)
            carried = water_sources.get('carried', 0)
            none = water_sources.get('none', 0)
            
            total = centralized + local + carried + none
            if total == 0:
                return 0.5  # Default moderate vulnerability
            
            # Vulnerability weights: centralized (0.1), local (0.3), carried (0.7), none (1.0)
            water_vulnerability = (
                centralized * 0.1 +
                local * 0.3 +
                carried * 0.7 +
                none * 1.0
            ) / total
            
            # Adjust for electricity access (critical for water systems)
            # Low electricity access increases water system vulnerability
            electricity_penalty = (100.0 - electricity_access_pct) / 100.0 * 0.2
            
            # Combine water source and electricity vulnerabilities
            combined_vulnerability = water_vulnerability + electricity_penalty
            
            return min(1.0, max(0.0, combined_vulnerability))
        except:
            return 0.5  # Default moderate vulnerability
    
    def _calculate_healthcare_access_vulnerability(self, per_capita: Dict[str, Any]) -> float:
        """Calculate healthcare access vulnerability from per capita metrics"""
        try:
            hospitals_per_1000 = per_capita.get('hospitals_per_1000', 0)
            
            # Lower healthcare access = higher vulnerability
            # Scale: 0 hospitals/1000 = 1.0 vulnerability, 0.5 hospitals/1000 = 0.0 vulnerability
            vulnerability = max(0.0, 1.0 - (hospitals_per_1000 * 2))
            return min(1.0, vulnerability)
        except:
            return 0.5
    
    def _calculate_education_access_vulnerability(self, per_capita: Dict[str, Any]) -> float:
        """Calculate education access vulnerability from per capita metrics"""
        try:
            schools_per_1000 = per_capita.get('schools_per_1000', 0)
            kindergartens_per_1000 = per_capita.get('kindergartens_per_1000', 0)
            
            # Combined education access metric
            education_access = (schools_per_1000 + kindergartens_per_1000) / 2
            
            # Lower education access = higher vulnerability
            # Scale: 0 education/1000 = 1.0 vulnerability, 0.4 education/1000 = 0.0 vulnerability
            vulnerability = max(0.0, 1.0 - (education_access * 2.5))
            return min(1.0, vulnerability)
        except:
            return 0.5
    
    def _calculate_sanitation_vulnerability(self, sanitation_indicators: Dict[str, Any]) -> float:
        """Calculate sanitation vulnerability from sanitation indicators"""
        try:
            # Use water vulnerability as proxy for sanitation vulnerability
            # Areas with poor water access typically have poor sanitation
            return self._calculate_water_access_vulnerability(sanitation_indicators)
        except:
            return 0.5
    
    def _calculate_social_infrastructure_capacity(self, per_capita: Dict[str, Any]) -> float:
        """Calculate social infrastructure adaptive capacity from per capita metrics"""
        try:
            hospitals_per_1000 = per_capita.get('hospitals_per_1000', 0)
            schools_per_1000 = per_capita.get('schools_per_1000', 0)
            kindergartens_per_1000 = per_capita.get('kindergartens_per_1000', 0)
            
            # Combined social infrastructure metric
            social_infra = hospitals_per_1000 + schools_per_1000 + kindergartens_per_1000
            
            # Higher social infrastructure = higher adaptive capacity
            # Scale: 0 social infra/1000 = 0.0 capacity, 1.0 social infra/1000 = 1.0 capacity
            capacity = min(1.0, social_infra)
            return max(0.0, capacity)
        except:
            return 0.5
    
    def _calculate_water_system_capacity(self, city: str, sanitation_indicators: Dict[str, Any] = None) -> float:
        """Calculate water system adaptive capacity from sanitation indicators
        
        FIX: Now uses city-specific GDP-based calculation instead of constant 0.4
        """
        if sanitation_indicators:
            try:
                # Extract water source distribution
                water_sources = sanitation_indicators.get('water_source_distribution', {})
                
                centralized = water_sources.get('centralized', 0)
                local = water_sources.get('local', 0)
                carried = water_sources.get('carried', 0)
                none = water_sources.get('none', 0)
                
                total = centralized + local + carried + none
                if total > 0:
                    # Capacity weights: centralized (1.0), local (0.7), carried (0.3), none (0.0)
                    capacity = (
                        centralized * 1.0 +
                        local * 0.7 +
                        carried * 0.3 +
                        none * 0.0
                    ) / total
                    
                    return min(1.0, max(0.0, capacity))
            except:
                pass
        
        # Calculate based on GDP as proxy for water infrastructure capacity
        population_data = self.data['population_data'].get(city)
        if population_data and hasattr(population_data, 'gdp_per_capita_usd'):
            gdp = population_data.gdp_per_capita_usd
            if gdp >= 3000:
                return 0.8
            elif gdp >= 1500:
                return 0.6
            elif gdp >= 1000:
                return 0.5
            elif gdp >= 700:
                return 0.4
            else:
                return 0.3
        
        # Final fallback - should rarely be used
        return 0.4
    
    def _load_social_sector_data(self, city: str) -> Optional[Dict[str, Any]]:
        """Load social sector data for a city"""
        try:
            import json
            from pathlib import Path
            
            social_file = self.data_loader.base_path / 'social_sector' / f'{city}_social_sector.json'
            if social_file.exists():
                with open(social_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('summary', {})
            return None
        except Exception as e:
            print(f"Warning: Could not load social sector data for {city}: {e}")
            return None
    
    def _integrate_social_sector_data(self, city: str, metrics: ClimateRiskMetrics, social_data: Dict[str, Any]) -> ClimateRiskMetrics:
        """Integrate social sector data into climate risk metrics"""
        
        # Extract per capita metrics
        per_capita = social_data.get('per_capita_metrics', {})
        sanitation_indicators = social_data.get('sanitation_indicators', {})
        infrastructure_quality = social_data.get('infrastructure_quality', {})
        
        # Calculate social sector vulnerability components
        metrics.water_access_vulnerability = self._calculate_water_access_vulnerability(sanitation_indicators)
        metrics.healthcare_access_vulnerability = self._calculate_healthcare_access_vulnerability(per_capita)
        metrics.education_access_vulnerability = self._calculate_education_access_vulnerability(per_capita)
        metrics.sanitation_vulnerability = self._calculate_sanitation_vulnerability(sanitation_indicators)
        metrics.building_age_vulnerability = infrastructure_quality.get('building_age_vulnerability', 0.0)
        
        # Calculate social sector adaptive capacity components
        metrics.social_infrastructure_capacity = self._calculate_social_infrastructure_capacity(per_capita)
        metrics.water_system_capacity = self._calculate_water_system_capacity(city, sanitation_indicators)
        
        # Recalculate composite scores with social sector components
        metrics.vulnerability_score = (
            self.vulnerability_weights['income_inv'] * metrics.income_vulnerability +
            self.vulnerability_weights['veg_access'] * metrics.veg_access_vulnerability +
            self.vulnerability_weights['fragment'] * metrics.fragmentation_vulnerability +
            self.vulnerability_weights['delta_bio_veg'] * metrics.bio_trend_vulnerability +
            self.vulnerability_weights['water_access'] * metrics.water_access_vulnerability +
            self.vulnerability_weights['healthcare_access'] * metrics.healthcare_access_vulnerability +
            self.vulnerability_weights['education_access'] * metrics.education_access_vulnerability +
            self.vulnerability_weights['sanitation'] * metrics.sanitation_vulnerability +
            self.vulnerability_weights['building_age'] * metrics.building_age_vulnerability +
            self.vulnerability_weights['air_pollution'] * metrics.air_pollution_vulnerability
        )
        
        metrics.adaptive_capacity_score = (
            self.adaptive_capacity_weights['gdp_pc'] * metrics.gdp_adaptive_capacity +
            self.adaptive_capacity_weights['greenspace'] * metrics.greenspace_adaptive_capacity +
            self.adaptive_capacity_weights['services'] * metrics.services_adaptive_capacity +
            self.adaptive_capacity_weights['social_infrastructure'] * metrics.social_infrastructure_capacity +
            self.adaptive_capacity_weights['water_system'] * metrics.water_system_capacity +
            self.adaptive_capacity_weights['air_quality_management'] * metrics.air_quality_adaptive_capacity
        )
        
        # Recalculate overall risk with updated components
        metrics.overall_risk_score = self._calculate_overall_risk(metrics)
        metrics.adaptability_score = self._calculate_adaptability_score(metrics)
        
        # Recalculate composite hazard and exposure scores to ensure consistency
        metrics.hazard_score = (
            self.hazard_weights['heat'] * metrics.heat_hazard +
            self.hazard_weights['dry'] * metrics.dry_hazard +
            self.hazard_weights['pluv'] * metrics.pluvial_hazard +
            self.hazard_weights['dust'] * metrics.dust_hazard +
            self.hazard_weights['air_quality'] * metrics.air_quality_hazard
        )
        
        metrics.exposure_score = (
            self.exposure_weights['population'] * metrics.population_exposure +
            self.exposure_weights['gdp'] * metrics.gdp_exposure +
            self.exposure_weights['viirs'] * metrics.viirs_exposure
        )
        
        return metrics
    
    def _calculate_overall_risk(self, metrics: ClimateRiskMetrics) -> float:
        """Calculate overall risk score using IPCC AR6 framework with proper handling"""
        # Check if any component is missing (0.0)
        #if metrics.hazard_score == 0.0 or metrics.exposure_score == 0.0 or metrics.vulnerability_score == 0.0:
            # Fallback to weighted additive approach when data is missing
            # This prevents zero multiplication but still reflects actual available data
            #return min(1.0, 0.4 * metrics.hazard_score + 0.3 * metrics.exposure_score + 0.3 * metrics.vulnerability_score)
        
        # Standard multiplicative formula when all data is available
        # Calculate both HEV (original) and HEV_adj (with adaptive capacity)
        hev_score = metrics.hazard_score * metrics.exposure_score * metrics.vulnerability_score
        
        # Risk reduction through adaptive capacity: Risk_adjusted = HEV * (1 - AC)
        hev_adj_score = hev_score * (1.0 - metrics.adaptive_capacity_score)
        
        # Store both scores in metrics for reporting
        metrics.hev_score = min(1.0, max(0.0, hev_score))
        metrics.hev_adj_score = min(1.0, max(0.0, hev_adj_score))
        
        # Return the adjusted risk as the primary risk score
        overall_risk = hev_adj_score
        return min(1.0, max(0.0, overall_risk))

    
    def _calculate_adaptability_score(self, metrics: ClimateRiskMetrics) -> float:
        """Calculate adaptability score using IPCC AR6 framework"""
        # Adaptability = AC / (1 + Risk) from Eq. 65
        # Use a small epsilon to avoid division by zero
        adaptability = metrics.adaptive_capacity_score / (1.0 + metrics.overall_risk_score + 1e-6)
        return min(1.0, max(0.0, adaptability))
    
    def _calculate_hazard_components(self, city: str, metrics: ClimateRiskMetrics) -> ClimateRiskMetrics:
        """Calculate individual hazard components using IPCC AR6 framework"""
        # Heat hazard (H_heat): summer mean LST, day/night SUHI
        metrics.heat_hazard = self._calculate_heat_hazard(city)
        
        # Dry/ecological stress (H_dry): low NDVI/EVI, negative seasonal changes
        metrics.dry_hazard = self._calculate_dry_hazard(city)
        
        # Dust proxy (H_dust): bare/low-veg share and vegetation fragmentation
        metrics.dust_hazard = self._calculate_dust_hazard(city)
        
        # Pluvial proxy (H_pluv): built-up share and edge density
        metrics.pluvial_hazard = self._calculate_pluvial_hazard(city)
        
        # Air quality hazard (H_air_quality): pollutant levels and trends
        metrics.air_quality_hazard = self._calculate_air_quality_hazard(city)
        metrics.surface_water_change = self._calculate_surface_water_change(city)
        
        return metrics
    
    def _calculate_air_quality_hazard(self, city: str) -> float:
        """Calculate air quality hazard component"""
        if city not in self.data.get('air_quality_data', {}):
            # Do not use a default moderate hazard when data is missing; return 0.0
            print(f"Warning: No air quality data for {city} - air quality hazard set to 0.0")
            return 0.0  # No data -> no implicit hazard assumption
        
        air_data = self.data['air_quality_data'][city]
        
        # Calculate based on available pollutant data
        hazard_components = []
        
        if 'yearly_results' in air_data:
            years = sorted([int(y) for y in air_data['yearly_results'].keys() if y.isdigit()])
            if years:
                latest_year = str(years[-1])
                year_data = air_data['yearly_results'][latest_year]
                
                if 'pollutants' in year_data:
                    pollutants = year_data['pollutants']
                    
                    # NO2 hazard (traffic pollution)
                    if 'NO2' in pollutants and 'urban_annual' in pollutants['NO2']:
                        no2_mean = pollutants['NO2']['urban_annual'].get('mean', 0.0)
                        if no2_mean > 0:
                            # NO2 is likely already in mol/mol or similar, convert carefully
                            # Assume NO2 values are in mol/mol, typical range 0-0.0001
                            no2_hazard = min(1.0, no2_mean / 0.0001)  # Normalize to realistic range
                            hazard_components.append(no2_hazard * 0.3)
                    
                    # O3 hazard (photochemical pollution)
                    if 'O3' in pollutants and 'urban_annual' in pollutants['O3']:
                        o3_mean = pollutants['O3']['urban_annual'].get('mean', 0.0)
                        if o3_mean > 0:
                            # O3 values in mol/mol, typical range 0-0.0002
                            o3_hazard = min(1.0, o3_mean / 0.0002)  # Normalize to realistic range
                            hazard_components.append(o3_hazard * 0.25)
                    
                    # SO2 hazard (industrial pollution)
                    if 'SO2' in pollutants and 'urban_annual' in pollutants['SO2']:
                        so2_mean = pollutants['SO2']['urban_annual'].get('mean', 0.0)
                        if so2_mean > 0:
                            # SO2 values in mol/mol, typical range 0-0.00005
                            so2_hazard = min(1.0, so2_mean / 0.00005)  # Normalize to realistic range
                            hazard_components.append(so2_hazard * 0.2)
                    
                    # CO hazard (combustion pollution)
                    if 'CO' in pollutants and 'urban_annual' in pollutants['CO']:
                        co_mean = pollutants['CO']['urban_annual'].get('mean', 0.0)
                        if co_mean > 0:
                            # CO values in mol/mol, typical range 0-0.001
                            co_hazard = min(1.0, co_mean / 0.001)  # Normalize to realistic range
                            hazard_components.append(co_hazard * 0.15)
                    
                    # CH4 hazard (methane pollution)
                    if 'CH4' in pollutants and 'urban_annual' in pollutants['CH4']:
                        ch4_mean = pollutants['CH4']['urban_annual'].get('mean', 0.0)
                        if ch4_mean > 0:
                            # CH4 is measured in ppmv, global background is ~1.8 ppmv
                            # Use percentile ranking across cities instead of absolute thresholds
                            ch4_hazard = min(1.0, max(0.0, (ch4_mean - 1900) / 50))  # Range 1900-1950 ppmv
                            hazard_components.append(ch4_hazard * 0.1)
                    
                    # PM2.5 proxy from aerosol index
                    if 'AER_AI' in pollutants and 'urban_annual' in pollutants['AER_AI']:
                        aer_ai = pollutants['AER_AI']['urban_annual'].get('mean', 0.0)
                        # Aerosol index can be negative or positive
                        # Higher positive values indicate more particulates
                        pm_hazard = min(1.0, max(0.0, aer_ai / 1.0))  # Normalize: 0-1.0 range
                        hazard_components.append(pm_hazard * 0.2)
        
        if hazard_components:
            return min(1.0, sum(hazard_components))
        else:
            # No air quality data available - return 0.0 to match new data availability approach
            print(f"Warning: No valid air quality components for {city} - air quality hazard set to 0.0")
            print(f"DEBUG: Air quality data keys: {list(self.data.get('air_quality_data', {}).keys()) if hasattr(self.data.get('air_quality_data', {}), 'keys') else 'Not a dict'}")
            return 0.0


    def _calculate_exposure_components(self, city: str, metrics: ClimateRiskMetrics) -> ClimateRiskMetrics:
        """Calculate individual exposure components using IPCC AR6 framework"""
        population_data = self.data['population_data'].get(city)
        if not population_data:
            return metrics
        
        # Population exposure (E_pop) - exposed population
        # Use built area fraction as proxy for exposure (people in developed areas)
        # For now, use population-based estimates since LULC data may not be available
        if population_data.population_2024 > 1000000:  # Large cities
            built_area_fraction = 0.7
        elif population_data.population_2024 > 300000:  # Medium cities  
            built_area_fraction = 0.5
        else:  # Small cities
            built_area_fraction = 0.3
            
        exposed_population = population_data.population_2024 * built_area_fraction
        
        # Initialize exposed population cache if needed
        if 'exposed_population' not in self.data['cache']:
            exposed_pops = []
            for pop_data in self.data['population_data'].values():
                if pop_data.population_2024:
                    if pop_data.population_2024 > 1000000:
                        city_built_fraction = 0.7
                    elif pop_data.population_2024 > 300000:
                        city_built_fraction = 0.5
                    else:
                        city_built_fraction = 0.3
                    exposed_pops.append(pop_data.population_2024 * city_built_fraction)
            self.data['cache']['exposed_population'] = exposed_pops

        # FIX: Use safe_percentile_norm instead of winsorized_pct_norm to prevent zeros
        all_exposed_pops = self.data['cache']['exposed_population']
        safe_normalized_pop = self.data_loader.safe_percentile_norm(all_exposed_pops, floor=0.05, ceiling=0.95)
        
        # Get the index for current city by matching population data
        pop_city_index = -1
        current_pop_data = self.data['population_data'].get(city)
        if current_pop_data:
            for i, pop_data in enumerate(self.data['population_data'].values()):
                if pop_data.population_2024 == current_pop_data.population_2024:
                    pop_city_index = i
                    break
        
        if pop_city_index >= 0 and pop_city_index < len(safe_normalized_pop):
            metrics.population_exposure = safe_normalized_pop[pop_city_index]
        else:
            metrics.population_exposure = 0.05  # Floor instead of 0.0        # GDP exposure (E_gdp) - total GDP at risk (population × GDP_per_capita × exposed_share)
        # FIX: Now uses exposed GDP instead of total GDP
        exposed_gdp = population_data.population_2024 * population_data.gdp_per_capita_usd * built_area_fraction
        
        if 'exposed_gdp' not in self.data['cache']:
            # Initialize exposed_gdp cache if not present
            exposed_gdps = []
            for pop_data in self.data['population_data'].values():
                if pop_data.population_2024 and pop_data.gdp_per_capita_usd:
                    # Get built area fraction for this city based on population
                    if pop_data.population_2024 > 1000000:  # Large cities
                        city_built_fraction = 0.7
                    elif pop_data.population_2024 > 300000:  # Medium cities  
                        city_built_fraction = 0.5
                    else:  # Small cities
                        city_built_fraction = 0.3
                    
                    exposed_gdp_city = pop_data.population_2024 * pop_data.gdp_per_capita_usd * city_built_fraction
                    exposed_gdps.append(exposed_gdp_city)
            self.data['cache']['exposed_gdp'] = exposed_gdps
        
        # FIX: Use safe_percentile_norm instead of winsorized_pct_norm
        # This prevents artificial zeros and ensures proper ranking
        all_exposed_gdps = self.data['cache']['exposed_gdp']
        safe_normalized = self.data_loader.safe_percentile_norm(all_exposed_gdps, floor=0.05, ceiling=0.95)
        
        # Get the index for current city by matching population data
        city_index = -1
        current_pop_data = self.data['population_data'].get(city)
        if current_pop_data:
            for i, pop_data in enumerate(self.data['population_data'].values()):
                if (pop_data.population_2024 == current_pop_data.population_2024 and 
                    pop_data.gdp_per_capita_usd == current_pop_data.gdp_per_capita_usd):
                    city_index = i
                    break
        
        if city_index >= 0 and city_index < len(safe_normalized):
            metrics.gdp_exposure = safe_normalized[city_index]
        else:
            metrics.gdp_exposure = 0.5  # Fallback
        
        # VIIRS exposure (E_viirs) - urban radiance
        metrics.viirs_exposure = self._calculate_viirs_exposure(city)
        
        return metrics
    
    def _calculate_vulnerability_components(self, city: str, metrics: ClimateRiskMetrics) -> ClimateRiskMetrics:
        """Calculate individual vulnerability components using IPCC AR6 framework"""
        population_data = self.data['population_data'].get(city)
        if not population_data:
            return metrics
        
        # Income vulnerability (V_income_inv) - inverted GDP per capita
        metrics.income_vulnerability = self.data_loader.pct_norm(
            self.data['cache']['gdp'], 
            population_data.gdp_per_capita_usd, 
            invert=True
        )
        
        # Vegetation access vulnerability (V_veg_access)
        metrics.veg_access_vulnerability = self._calculate_veg_access_vulnerability(city)
        
        # Fragmentation vulnerability (V_fragment)
        metrics.fragmentation_vulnerability = self._calculate_fragmentation_vulnerability(city)
        
        # Biomass/vegetation trend vulnerability (V_delta_bio_veg)
        metrics.bio_trend_vulnerability = self._calculate_bio_trend_vulnerability(city)
        
        # Water scarcity vulnerability (V_water_scarcity)
        metrics.water_scarcity_vulnerability = self._calculate_water_scarcity_vulnerability(city)
        
        # Air pollution vulnerability (V_air_pollution) - based on PM2.5 levels or air quality hazard
        metrics.air_pollution_vulnerability = 0.0
        if city in self.data['air_quality_data']:
            air_data = self.data['air_quality_data'][city]
            if 'pm25' in air_data:
                pm25_level = air_data['pm25']
                # Higher PM2.5 levels = higher vulnerability
                metrics.air_pollution_vulnerability = min(1.0, pm25_level / 35.0)  # 35 µg/m³ as threshold for high risk
            else:
                # Use air quality hazard as proxy for air pollution vulnerability
                air_hazard = self._calculate_air_quality_hazard(city)
                # Calculate air pollution vulnerability based on population density and built area
        population_data = self.data['population_data'].get(city)
        if population_data:
            density = population_data.density_per_km2
            # Base vulnerability on density
            if density >= 10000:
                base_vuln = 0.9
            elif density >= 5000:
                base_vuln = 0.7
            elif density >= 2000:
                base_vuln = 0.5
            elif density >= 1000:
                base_vuln = 0.4
            else:
                base_vuln = 0.3
            
            # Adjust for built environment
            for lulc_city in self.data['lulc_data']:
                if lulc_city.get('city') == city:
                    areas = lulc_city.get('areas_m2', {})
                    if areas:
                        latest_year = max(areas.keys(), key=lambda x: int(x))
                        built_pct = areas[latest_year].get('Built_Area', {}).get('percentage', 30)
                        if built_pct >= 60:
                            built_modifier = 0.15
                        elif built_pct >= 40:
                            built_modifier = 0.1
                        elif built_pct >= 25:
                            built_modifier = 0.0
                        else:
                            built_modifier = -0.1
                        metrics.air_pollution_vulnerability = min(1.0, max(0.1, base_vuln + built_modifier))
                        break
            else:
                metrics.air_pollution_vulnerability = base_vuln
        else:
            metrics.air_pollution_vulnerability = 0.5
        
        return metrics
    
    def _calculate_adaptive_capacity_components(self, city: str, metrics: ClimateRiskMetrics) -> ClimateRiskMetrics:
        """Calculate individual adaptive capacity components using IPCC AR6 framework"""
        population_data = self.data['population_data'].get(city)
        if not population_data:
            return metrics
        
        # GDP per capita adaptive capacity (AC_gdp_pc)
        metrics.gdp_adaptive_capacity = self.data_loader.winsorized_pct_norm(
            self.data['cache']['gdp'], 
            population_data.gdp_per_capita_usd
        )
        
        # Greenspace adaptive capacity (AC_greenspace)
        metrics.greenspace_adaptive_capacity = self._calculate_greenspace_adaptive_capacity(city)
        
        # Services adaptive capacity (AC_services) - Based on actual service infrastructure
        metrics.services_adaptive_capacity = self._calculate_services_adaptive_capacity(city)
        
        # Air quality management adaptive capacity (AC_air_quality_management)
        metrics.air_quality_adaptive_capacity = self._calculate_air_quality_adaptive_capacity(city)
        
        return metrics
        
    def _calculate_air_quality_adaptive_capacity(self, city: str) -> float:
        """Calculate air quality management adaptive capacity"""
        population_data = self.data['population_data'].get(city)
        if not population_data:
            return 0.0  # No data -> no capacity
        
        # Base capacity from economic resources (wealthier cities can afford better air quality management)
        economic_capacity = self.data_loader.pct_norm(
            self.data['cache']['gdp'], 
            population_data.gdp_per_capita_usd
        )
        
        # Population size capacity (larger cities have more resources for air quality management)
        size_capacity = self.data_loader.pct_norm(
            self.data['cache']['population'], 
            population_data.population_2024
        )
        
        # Urban infrastructure capacity (cities with better services have better air quality monitoring)
        # FIX: Calculate actual services capacity instead of aliasing VIIRS exposure
        services_capacity = self._calculate_services_adaptive_capacity(city)
        
        # Air quality data availability bonus
        data_availability_bonus = 0.2 if city in self.data.get('air_quality_data', {}) else 0.0
        
        # Combined air quality management capacity
        air_quality_capacity = (
            0.4 * economic_capacity +     # Economic resources for air quality management
            0.3 * size_capacity +          # City size and resources
            0.2 * services_capacity +      # Infrastructure and services
            0.1 * data_availability_bonus  # Monitoring and data availability
        )
        
        return min(1.0, air_quality_capacity)
    
    def _calculate_services_adaptive_capacity(self, city: str) -> float:
        """Calculate services adaptive capacity based on actual service infrastructure
        
        FIX: This was previously aliased to VIIRS exposure. Now calculates based on:
        - Healthcare infrastructure density
        - Educational infrastructure density  
        - Economic capacity for service provision
        - Population density (service accessibility)
        """
        
        # Get basic city data
        population_data = self.data['population_data'].get(city)
        if not population_data:
            return 0.0
        
        # Healthcare infrastructure capacity
        healthcare_capacity = 1.0 - self.data.get('social_sector_data', {}).get(city, {}).get('healthcare_access_vulnerability', 0.5)
        
        # Educational infrastructure capacity
        education_capacity = 1.0 - self.data.get('social_sector_data', {}).get(city, {}).get('education_access_vulnerability', 0.5)
        
        # Economic capacity for service provision
        economic_capacity = self.data_loader.pct_norm(
            self.data['cache']['gdp'], 
            population_data.gdp_per_capita_usd
        )
        
        # Population density factor (higher density = better service accessibility)
        population_density = population_data.density_per_km2 if population_data.density_per_km2 else 0
        density_capacity = min(1.0, population_density / 1000)  # Normalize to reasonable urban density
        
        # Combined services capacity
        services_capacity = (
            0.3 * healthcare_capacity +    # Healthcare infrastructure
            0.3 * education_capacity +     # Educational infrastructure  
            0.25 * economic_capacity +     # Economic resources for services
            0.15 * density_capacity        # Population density for accessibility
        )
        
        return min(1.0, services_capacity)
    
    def _populate_supporting_metrics(self, city: str, metrics: ClimateRiskMetrics):
        """Populate supporting metrics for detailed analysis"""
        # SUHI and temperature trends
        if city in self.data['suhi_data']:
            years = sorted([int(y) for y in self.data['suhi_data'][city].keys()])
            if years:
                latest_year = str(years[-1])
                metrics.current_suhi_intensity = self.data['suhi_data'][city][latest_year]['stats'].get('suhi_night', 0)
                
                # Calculate trends
                if len(years) >= 3:
                    suhi_values = [self.data['suhi_data'][city][str(y)]['stats'].get('suhi_night', 0) for y in years]
                    temp_values = [self.data['suhi_data'][city][str(y)]['stats'].get('night_urban_mean', 0) for y in years]
                    
                    try:
                        metrics.suhi_trend = np.polyfit(years, suhi_values, 1)[0]
                        metrics.temperature_trend = np.polyfit(years, temp_values, 1)[0]
                    except:
                        metrics.suhi_trend = 0.0
                        metrics.temperature_trend = 0.0
        
        # LULC data - populate built area percentage
        for lulc_city in self.data['lulc_data']:
            if lulc_city.get('city') == city:
                areas = lulc_city.get('areas_m2', {})
                if areas:
                    years = sorted([int(y) for y in areas.keys()])
                    if years:
                        latest_year = str(years[-1])
                        built_pct = areas[latest_year].get('Built_Area', {}).get('percentage')
                        if built_pct is not None:
                            metrics.built_area_percentage = built_pct
                break
        
        # Spatial data - populate green space accessibility
        spatial_city_data = self.data['spatial_data'].get('per_year', {}).get(city, {})
        if spatial_city_data:
            years = sorted([int(y) for y in spatial_city_data.keys()])
            if years:
                latest_year = str(years[-1])
                veg_access = spatial_city_data[latest_year].get('vegetation_accessibility', {}).get('city', {}).get('mean')
                if veg_access is not None:
                    metrics.green_space_accessibility = veg_access
        
        # Economic capacity
        population_data = self.data['population_data'].get(city)
        if population_data:
            metrics.economic_capacity = self.data_loader.pct_norm(
                self.data['cache']['gdp'], 
                population_data.gdp_per_capita_usd
            )
        
        # Water scarcity data
        if city in self.water_scarcity_data:
            water_data = self.water_scarcity_data[city]
            metrics.aridity_index = water_data.get('aridity_index', 0.0)
            metrics.climatic_water_deficit = water_data.get('climatic_water_deficit', 0.0)
            metrics.drought_frequency = water_data.get('drought_frequency', 0.0)
            # surface_water_change is now calculated by _calculate_surface_water_change(), don't override
            # metrics.surface_water_change = water_data.get('surface_water_change', 0.0)
            metrics.cropland_fraction = water_data.get('irrigation_demand', 0.0)
            metrics.water_supply_risk = water_data.get('water_supply_risk', 0.0)
            metrics.water_demand_risk = water_data.get('water_demand_risk', 0.0)
            metrics.overall_water_scarcity_score = water_data.get('water_scarcity_index', 0.0)
            metrics.water_scarcity_level = water_data.get('water_scarcity_level', 'Unknown')
    
        # Air quality metrics - populate from air quality data
        if city in self.data['air_quality_data']:
            air_data = self.data['air_quality_data'][city]
            
            if 'yearly_results' in air_data:
                # Get the most recent year
                years = sorted([int(y) for y in air_data['yearly_results'].keys() if y.isdigit()])
                if years:
                    latest_year = str(years[-1])
                    year_data = air_data['yearly_results'][latest_year]
                    
                    if 'pollutants' in year_data:
                        pollutants = year_data['pollutants']
                        
                        # Extract urban annual means
                        if 'CO' in pollutants and 'urban_annual' in pollutants['CO']:
                            metrics.co_level = pollutants['CO']['urban_annual'].get('mean', 0.0)
                        if 'NO2' in pollutants and 'urban_annual' in pollutants['NO2']:
                            metrics.no2_level = pollutants['NO2']['urban_annual'].get('mean', 0.0)
                        if 'O3' in pollutants and 'urban_annual' in pollutants['O3']:
                            metrics.o3_level = pollutants['O3']['urban_annual'].get('mean', 0.0)
                        if 'SO2' in pollutants and 'urban_annual' in pollutants['SO2']:
                            metrics.so2_level = pollutants['SO2']['urban_annual'].get('mean', 0.0)
                        if 'CH4' in pollutants and 'urban_annual' in pollutants['CH4']:
                            metrics.ch4_level = pollutants['CH4']['urban_annual'].get('mean', 0.0)
                        if 'AER_AI' in pollutants and 'urban_annual' in pollutants['AER_AI']:
                            metrics.aerosol_index = pollutants['AER_AI']['urban_annual'].get('mean', 0.0)
                        
                        # Calculate air quality trend (simplified)
                        if len(years) >= 2:
                            # Simple trend calculation based on latest vs previous year
                            prev_year = str(years[-2])
                            if prev_year in air_data['yearly_results']:
                                prev_data = air_data['yearly_results'][prev_year]
                                if 'pollutants' in prev_data:
                                    prev_pollutants = prev_data['pollutants']
                                    
                                    # Calculate average pollutant change
                                    changes = []
                                    for pollutant in ['CO', 'NO2', 'O3', 'SO2', 'CH4']:
                                        if (pollutant in pollutants and pollutant in prev_pollutants and
                                            'urban_annual' in pollutants[pollutant] and 
                                            'urban_annual' in prev_pollutants[pollutant]):
                                            
                                            current = pollutants[pollutant]['urban_annual'].get('mean', 0.0)
                                            previous = prev_pollutants[pollutant]['urban_annual'].get('mean', 0.0)
                                            
                                            if previous > 0:
                                                change = (current - previous) / previous
                                                changes.append(change)
                                    
                                    if changes:
                                        avg_change = np.mean(changes)
                                        metrics.air_quality_trend = float(avg_change)
                        
                        # Calculate health risk score based on pollutant levels
                        health_risk = 0.0
                        if metrics.no2_level > 1e-4:  # High NO2
                            health_risk += 0.25
                        if metrics.o3_level > 1e-4:   # High O3
                            health_risk += 0.20
                        if metrics.so2_level > 1e-5:  # High SO2
                            health_risk += 0.20
                        if metrics.co_level > 1e-5:   # High CO
                            health_risk += 0.15
                        if metrics.ch4_level > 2.0:   # Elevated CH4 (>2.0 ppmv)
                            health_risk += 0.10
                        if metrics.aerosol_index > 1.0:  # High particulates
                            health_risk += 0.10
                        
                        metrics.health_risk_score = min(1.0, health_risk)
        
        return metrics
    
    # Individual hazard calculation methods
    def _calculate_heat_hazard(self, city: str) -> float:
        """Calculate heat hazard with relative temperature scaling (FIXED)"""
        
        # Get temperature data for all cities to calculate relative scaling
        all_temp_values = []
        all_city_names = []
        
        for city_name in list(self.data['population_data'].keys()):
            temp_data = self.data['temperature_data'].get(city_name, {})
            if temp_data:
                # Get latest year's data from nested structure
                latest_year = max(temp_data.keys()) if temp_data else None
                if latest_year:
                    year_data = temp_data[latest_year]
                    summer_data = year_data.get('summer_season_summary', {})
                    urban_data = summer_data.get('urban', {})
                    rural_data = summer_data.get('rural', {})
                    
                    urban_day = urban_data.get('day', {})
                    rural_day = rural_data.get('day', {})
                    
                    # Calculate SUHI intensity
                    urban_temp = urban_day.get('mean', 30)
                    rural_temp = rural_day.get('mean', 30)
                    current_suhi = urban_temp - rural_temp
                    
                    # Get summer max temperature
                    summer_max = urban_day.get('max', 35)
                    
                    # Calculate temperature trend (simplified)
                    temp_trend = max(0, summer_max - 35) * 0.1
                    
                    # Composite heat indicator
                    heat_indicator = (current_suhi * 0.5 + 
                                    temp_trend * 0.3 + 
                                    (summer_max - 35) * 0.2)
                    
                    all_temp_values.append(heat_indicator)
                else:
                    all_temp_values.append(0)
            else:
                all_temp_values.append(0)
            all_city_names.append(city_name)
        
        # Get current city's value
        current_temp_data = self.data['temperature_data'].get(city, {})
        if current_temp_data:
            latest_year = max(current_temp_data.keys()) if current_temp_data else None
            if latest_year:
                year_data = current_temp_data[latest_year]
                summer_data = year_data.get('summer_season_summary', {})
                urban_data = summer_data.get('urban', {})
                rural_data = summer_data.get('rural', {})
                
                urban_day = urban_data.get('day', {})
                rural_day = rural_data.get('day', {})
                
                urban_temp = urban_day.get('mean', 30)
                rural_temp = rural_day.get('mean', 30)
                current_suhi = urban_temp - rural_temp
                summer_max = urban_day.get('max', 35)
                temp_trend = max(0, summer_max - 35) * 0.1
                
                current_heat = (current_suhi * 0.5 + 
                              temp_trend * 0.3 + 
                              (summer_max - 35) * 0.2)
            else:
                current_heat = 0
        else:
            current_heat = 0
        
        # Apply safe percentile normalization to prevent max-pegging
        normalized_heat = self.data_loader.safe_percentile_norm(
            all_temp_values, floor=0.05, ceiling=0.95
        )
        
        # Return value for current city
        if city in all_city_names:
            city_index = all_city_names.index(city)
            return normalized_heat[city_index]
        else:
            return 0.5
    def _calculate_dry_hazard(self, city: str) -> float:
        """Calculate dry/ecological stress hazard (H_dry)"""
        # Do NOT fall back to climatological estimators; use only observed LULC/vegetation data
        if not self.data['lulc_data']:
            # Missing LULC data - cannot estimate dry hazard reliably
            # Return 0.0 so that absence of data does not add implicit risk
            print(f"Warning: LULC data missing for {city} - dry hazard set to 0.0")
            return 0.0
        
        # Based on low NDVI/EVI, negative seasonal changes
        dry_score = 0.0
        
        # Initialize cache for bare/sparse percentages if needed
        if 'bare_sparse_pct' not in self.data['cache']:
            bare_sparse_pcts = []
            for lulc_city in self.data['lulc_data']:
                areas = lulc_city.get('areas_m2', {})
                if areas:
                    years = sorted([int(y) for y in areas.keys()])
                    if years:
                        latest_year = str(years[-1])
                        bare_pct = areas[latest_year].get('Bare_Ground', {}).get('percentage', 0)
                        sparse_pct = areas[latest_year].get('Sparse_Vegetation', {}).get('percentage', 0)
                        bare_sparse_pcts.append(bare_pct + sparse_pct)
            self.data['cache']['bare_sparse_pct'] = bare_sparse_pcts
        
        # Check LULC data for vegetation indicators
        for lulc_city in self.data['lulc_data']:
            if lulc_city.get('city') == city:
                areas = lulc_city.get('areas_m2', {})
                if areas:
                    years = sorted([int(y) for y in areas.keys()])
                    if len(years) >= 2:
                        # Recent year vegetation
                        latest_year = str(years[-1])
                        veg_areas = areas[latest_year]
                        
                        # Calculate vegetation stress indicators
                        bare_pct = veg_areas.get('Bare_Ground', {}).get('percentage', 0)
                        sparse_veg_pct = veg_areas.get('Sparse_Vegetation', {}).get('percentage', 0)
                        
                        # Higher bare/sparse = higher dry hazard
                        dry_score = self.data_loader.pct_norm(
                            self.data['cache']['bare_sparse_pct'], 
                            bare_pct + sparse_veg_pct
                        )
                        
                        # Add trend component if multiple years available
                        if len(years) >= 3:
                            # Check vegetation trend over time
                            veg_trends = []
                            for year in years[-3:]:  # Last 3 years
                                year_data = areas[str(year)]
                                total_veg = (year_data.get('Trees', {}).get('percentage', 0) + 
                                           year_data.get('Crops', {}).get('percentage', 0) +
                                           year_data.get('Grass', {}).get('percentage', 0))
                                veg_trends.append(total_veg)
                            
                            if len(veg_trends) >= 3:
                                try:
                                    veg_trend = np.polyfit(range(len(veg_trends)), veg_trends, 1)[0]
                                    # Negative trend = higher dry hazard
                                    if veg_trend < 0:
                                        trend_penalty = min(0.3, abs(veg_trend) * 0.1)
                                        dry_score = min(1.0, dry_score + trend_penalty)
                                except:
                                    pass
                break
        
        return dry_score
    
    def _calculate_dust_hazard(self, city: str) -> float:
        """Calculate dust proxy hazard (H_dust)"""
        # Do NOT fall back to climatological estimators; require LULC/spatial data
        if not self.data['lulc_data']:
            print(f"Warning: LULC data missing for {city} - dust hazard set to 0.0")
            return 0.0
        
        # Based on bare/low-veg share and vegetation patch isolation
        dust_score = 0.0
        
        # Initialize cache for bare percentages if needed
        if 'bare_pct' not in self.data['cache']:
            bare_pcts = []
            for lulc_city in self.data['lulc_data']:
                areas = lulc_city.get('areas_m2', {})
                if areas:
                    years = sorted([int(y) for y in areas.keys()])
                    if years:
                        latest_year = str(years[-1])
                        bare_pct = areas[latest_year].get('Bare_Ground', {}).get('percentage', 0)
                        bare_pcts.append(bare_pct)
            self.data['cache']['bare_pct'] = bare_pcts
        
        # Bare ground and fragmentation from LULC
        for lulc_city in self.data['lulc_data']:
            if lulc_city.get('city') == city:
                areas = lulc_city.get('areas_m2', {})
                if areas:
                    years = sorted([int(y) for y in areas.keys()])
                    if years:
                        latest_year = str(years[-1])
                        bare_pct = areas[latest_year].get('Bare_Ground', {}).get('percentage', 0)
                        dust_score = self.data_loader.pct_norm(
                            self.data['cache']['bare_pct'], bare_pct
                        )
                break
        
        # Add fragmentation component from spatial data
        spatial_city_data = self.data['spatial_data'].get('per_year', {}).get(city, {})
        if spatial_city_data:
            years = sorted([int(y) for y in spatial_city_data.keys()])
            if years:
                latest_year = str(years[-1])
                patch_data = spatial_city_data[latest_year].get('veg_patches', {})
                
                # Higher isolation/fragmentation = higher dust risk
                patch_count = patch_data.get('patch_count', 0)
                if patch_count > 0:
                    # More, smaller patches = more fragmentation
                    fragmentation_score = self.data_loader.pct_norm(
                        self.data['cache']['veg_patches'], patch_count
                    )
                    dust_score = (dust_score * 0.7 + fragmentation_score * 0.3)
        
        return min(1.0, dust_score)
    
    def _calculate_pluvial_hazard(self, city: str) -> float:
        """Calculate pluvial hazard based on urban characteristics (FIXED)"""
        
        # Get urban characteristics data for all cities
        all_pluvial_values = []
        all_city_names = []
        
        for city_name in list(self.data['population_data'].keys()):
            # Find LULC data for this city
            lulc_data = None
            for lulc_city in self.data['lulc_data']:
                if lulc_city.get('city') == city_name:
                    lulc_data = lulc_city
                    break
            
            if lulc_data is None:
                lulc_data = {}
            
            # Get population data for density calculation
            pop_data = self.data['population_data'].get(city_name, {})
            
            # Calculate urban imperviousness (primary factor - 60% weight)
            if 'built_area_percentage' in lulc_data:
                built_pct = lulc_data['built_area_percentage'] / 100.0
                imperv_component = min(built_pct * 1.2, 1.0)  # Scale up built area impact
            else:
                imperv_component = 0.4  # Default moderate imperviousness
            
            # Calculate population density pressure (30% weight)
            if pop_data and hasattr(pop_data, 'area_km2') and pop_data.area_km2 > 0:
                population = pop_data.population
                density = population / pop_data.area_km2
                # Normalize density (typical range 0-10,000 people/km2)
                density_component = min(density / 10000.0, 1.0)
            else:
                density_component = 0.3
            
            # Calculate drainage capacity loss from urbanization (10% weight)
            # More built area = less natural drainage
            if 'vegetation_percentage' in lulc_data:
                veg_pct = lulc_data['vegetation_percentage'] / 100.0
                drainage_loss = 1.0 - veg_pct  # Less vegetation = more drainage loss
                drainage_component = min(drainage_loss * 0.8, 1.0)
            else:
                drainage_component = 0.5
            
            # Combined pluvial risk
            pluvial_risk = (0.6 * imperv_component + 
                          0.3 * density_component + 
                          0.1 * drainage_component)
            
            all_pluvial_values.append(pluvial_risk)
            all_city_names.append(city_name)
        
        # Calculate current city's value using same methodology
        current_lulc = None
        for lulc_city in self.data['lulc_data']:
            if lulc_city.get('city') == city:
                current_lulc = lulc_city
                break
        if current_lulc is None:
            current_lulc = {}
        
        current_pop = self.data['population_data'].get(city, {})
        
        # Current city imperviousness
        if 'built_area_percentage' in current_lulc:
            current_built = current_lulc['built_area_percentage'] / 100.0
            current_imperv = min(current_built * 1.2, 1.0)
        else:
            current_imperv = 0.4
        
        # Current city density
        if current_pop and hasattr(current_pop, 'area_km2') and current_pop.area_km2 > 0:
            current_population = current_pop.population
            current_density_val = current_population / current_pop.area_km2
            current_density = min(current_density_val / 10000.0, 1.0)
        else:
            current_density = 0.3
        
        # Current city drainage
        if 'vegetation_percentage' in current_lulc:
            current_veg = current_lulc['vegetation_percentage'] / 100.0
            current_drainage = min((1.0 - current_veg) * 0.8, 1.0)
        else:
            current_drainage = 0.5
        
        current_pluvial = (0.6 * current_imperv + 
                         0.3 * current_density + 
                         0.1 * current_drainage)
        
        # Apply safe percentile normalization
        normalized_pluvial = self.data_loader.safe_percentile_norm(
            all_pluvial_values, floor=0.05, ceiling=0.95
        )
        
        # Return value for current city
        if city in all_city_names:
            city_index = all_city_names.index(city)
            return normalized_pluvial[city_index]
        else:
            return 0.5
    
    def _calculate_viirs_exposure(self, city: str) -> float:
        """Calculate VIIRS exposure with improved scaling (FIXED)"""
        
        # Collect nightlight data for all cities
        all_viirs_values = []
        all_city_names = []
        
        for city_name in list(self.data['population_data'].keys()):
            nightlight_data = None
            for nightlight_city in self.data['nightlights_data']:
                if nightlight_city.get('city') == city_name:
                    nightlight_data = nightlight_city
                    break
            if nightlight_data is None:
                nightlight_data = {}
            
            if nightlight_data and 'years' in nightlight_data:
                years_data = nightlight_data['years']
                if years_data:
                    # Get latest year data
                    latest_year = max(years_data.keys())
                    year_data = years_data[latest_year]
                    
                    if 'stats' in year_data and 'urban_core' in year_data['stats']:
                        viirs_value = year_data['stats']['urban_core'].get('mean', 0)
                    else:
                        viirs_value = 0
                else:
                    viirs_value = 0
            else:
                viirs_value = 0
            
            # Apply log transformation to reduce skewness
            log_viirs = np.log(viirs_value + 1)
            all_viirs_values.append(log_viirs)
            all_city_names.append(city_name)
        
        # Get current city's value
        current_nightlight = None
        for nightlight_city in self.data['nightlights_data']:
            if nightlight_city.get('city') == city:
                current_nightlight = nightlight_city
                break
        if current_nightlight is None:
            current_nightlight = {}
        if current_nightlight and 'years' in current_nightlight:
            years_data = current_nightlight['years']
            if years_data:
                latest_year = max(years_data.keys())
                year_data = years_data[latest_year]
                
                if 'stats' in year_data and 'urban_core' in year_data['stats']:
                    current_viirs = year_data['stats']['urban_core'].get('mean', 0)
                else:
                    current_viirs = 0
            else:
                current_viirs = 0
        else:
            current_viirs = 0
        
        current_log_viirs = np.log(current_viirs + 1)
        
        # Apply safe percentile normalization
        normalized_viirs = self.data_loader.safe_percentile_norm(
            all_viirs_values, floor=0.05, ceiling=0.95
        )
        
        # Return value for current city
        if city in all_city_names:
            city_index = all_city_names.index(city)
            return normalized_viirs[city_index]
        else:
            return 0.5
    def _calculate_veg_access_vulnerability(self, city: str) -> float:
        """Calculate vegetation access vulnerability"""
        veg_vuln = 0.0
        spatial_city_data = self.data['spatial_data'].get('per_year', {}).get(city, {})
        if spatial_city_data:
            years = sorted([int(y) for y in spatial_city_data.keys()])
            if years:
                latest_year = str(years[-1])
                veg_distance_m = spatial_city_data[latest_year].get('vegetation_accessibility', {}).get('city', {}).get('mean', 1000)
                
                # Higher distance = higher vulnerability
                max_distance = 2000  # 2km as maximum reasonable distance
                veg_vuln = min(1.0, veg_distance_m / max_distance)
        
        return veg_vuln
    
    def _calculate_fragmentation_vulnerability(self, city: str) -> float:
        """Calculate fragmentation vulnerability"""
        frag_vuln = 0.0
        spatial_city_data = self.data['spatial_data'].get('per_year', {}).get(city, {})
        if spatial_city_data:
            years = sorted([int(y) for y in spatial_city_data.keys()])
            if years:
                latest_year = str(years[-1])
                patch_data = spatial_city_data[latest_year].get('veg_patches', {})
                
                # More patches with smaller average size = higher fragmentation
                patch_count = patch_data.get('patch_count', 0)
                if patch_count > 0:
                    frag_vuln = self.data_loader.pct_norm(
                        self.data['cache']['veg_patches'], patch_count
                    )
        
        return frag_vuln
    
    def _calculate_bio_trend_vulnerability(self, city: str) -> float:
        """Calculate bio trend vulnerability with missing data imputation (FIXED)"""
        
        # Collect vegetation trend data for all cities
        all_bio_trends = []
        all_city_names = []
        raw_values = []
        
        for city_name in list(self.data['population_data'].keys()):
            # Find LULC data for this city to calculate vegetation trend
            lulc_city_data = None
            for lulc_city in self.data['lulc_data']:
                if lulc_city.get('city') == city_name:
                    lulc_city_data = lulc_city
                    break
            
            if lulc_city_data:
                areas = lulc_city_data.get('areas_m2', {})
                if areas and len(areas) >= 2:  # Need at least 2 years for trend
                    years = sorted([int(y) for y in areas.keys()])
                    
                    # Calculate vegetation percentages over time
                    veg_percentages = []
                    for year in years:
                        year_data = areas[str(year)]
                        total_veg = (year_data.get('Trees', {}).get('percentage', 0) + 
                                   year_data.get('Crops', {}).get('percentage', 0) +
                                   year_data.get('Grass', {}).get('percentage', 0))
                        veg_percentages.append(total_veg)
                    
                    # Calculate trend
                    if len(veg_percentages) >= 2:
                        try:
                            import numpy as np
                            veg_trend = np.polyfit(years, veg_percentages, 1)[0]
                            
                            # Convert trend to vulnerability (negative trend = higher vulnerability)
                            bio_vulnerability = max(0, -veg_trend * 10)  # Scale negative trend to positive vulnerability
                            raw_values.append(bio_vulnerability)
                        except:
                            raw_values.append(None)  # Mark as missing
                    else:
                        raw_values.append(None)  # Mark as missing
                else:
                    raw_values.append(None)  # Mark as missing
            else:
                raw_values.append(None)  # Mark as missing
            
            all_city_names.append(city_name)
        
        # Impute missing values with median of valid values
        valid_values = [v for v in raw_values if v is not None]
        if valid_values:
            median_value = np.median(valid_values)
            print(f"[BIO_TREND] Median vegetation vulnerability: {median_value:.3f}")
        else:
            median_value = 0.5  # Conservative default
        
        # Replace None values with median
        imputed_values = [v if v is not None else median_value for v in raw_values]
        
        # Apply safe percentile normalization
        normalized_bio = self.data_loader.safe_percentile_norm(
            imputed_values, floor=0.05, ceiling=0.95
        )
        
        # Return value for current city
        if city in all_city_names:
            city_index = all_city_names.index(city)
            return normalized_bio[city_index]
        else:
            return 0.5
    def _calculate_water_scarcity_vulnerability(self, city: str) -> float:
        """Calculate water scarcity vulnerability based on water scarcity assessment"""
        if city not in self.water_scarcity_data:
            # Do not assign a default moderate vulnerability when there is no assessment
            # Return 0.0 to ensure vulnerability reflects only available analysis
            print(f"Warning: No water scarcity assessment for {city} - water vulnerability set to 0.0")
            return 0.0

        water_data = self.water_scarcity_data[city]

        # Use available water scarcity indicators
        aridity_index = water_data.get('aridity_index', 0.2)
        climatic_water_deficit = water_data.get('climatic_water_deficit', 500)
        drought_frequency = water_data.get('drought_frequency', 0.1)
        surface_water_change = water_data.get('surface_water_change', 0.0)

        # Calculate water scarcity vulnerability from available indicators
        # Lower aridity index = higher risk (more arid)
        aridity_risk = 1.0 - min(1.0, aridity_index / 0.5)  # Normalize to 0-1, invert

        # Higher climatic water deficit = higher risk
        cwd_risk = min(1.0, climatic_water_deficit / 2000.0)  # Normalize to 0-1

        # Higher drought frequency = higher risk
        drought_risk = min(1.0, drought_frequency / 0.5)  # Normalize to 0-1

        # Surface water loss = higher risk (negative change)
        surface_water_risk = min(1.0, max(0.0, -surface_water_change / 50.0))  # Normalize to 0-1

        # Combine factors with appropriate weights
        combined_vulnerability = (
            0.4 * aridity_risk +           # Aridity is primary indicator
            0.3 * cwd_risk +               # Climatic water deficit
            0.2 * drought_risk +           # Drought frequency
            0.1 * surface_water_risk       # Surface water change
        )

        return min(1.0, combined_vulnerability)
    
    def _calculate_greenspace_adaptive_capacity(self, city: str) -> float:
        """Calculate greenspace adaptive capacity"""
        green_capacity = 0.0
        
        # Vegetation percentage from LULC
        for lulc_city in self.data['lulc_data']:
            if lulc_city.get('city') == city:
                areas = lulc_city.get('areas_m2', {})
                if areas:
                    years = sorted([int(y) for y in areas.keys()])
                    if years:
                        latest_year = str(years[-1])
                        year_data = areas[latest_year]
                        total_green = (year_data.get('Trees', {}).get('percentage', 0) + 
                                     year_data.get('Crops', {}).get('percentage', 0) +
                                     year_data.get('Grass', {}).get('percentage', 0))
                        
                        # Initialize cache for green percentages if needed
                        if 'green_pct' not in self.data['cache']:
                            green_pcts = []
                            for lulc_city_cache in self.data['lulc_data']:
                                areas_cache = lulc_city_cache.get('areas_m2', {})
                                if areas_cache:
                                    years_cache = sorted([int(y) for y in areas_cache.keys()])
                                    if years_cache:
                                        latest_year_cache = str(years_cache[-1])
                                        year_data_cache = areas_cache[latest_year_cache]
                                        total_green_cache = (year_data_cache.get('Trees', {}).get('percentage', 0) + 
                                                           year_data_cache.get('Crops', {}).get('percentage', 0) +
                                                           year_data_cache.get('Grass', {}).get('percentage', 0))
                                        green_pcts.append(total_green_cache)
                            self.data['cache']['green_pct'] = green_pcts
                        
                        green_capacity = self.data_loader.pct_norm(
                            self.data['cache']['green_pct'], total_green
                        )
                break
        
        # Combine with accessibility if available
        spatial_city_data = self.data['spatial_data'].get('per_year', {}).get(city, {})
        if spatial_city_data:
            years = sorted([int(y) for y in spatial_city_data.keys()])
            if years:
                latest_year = str(years[-1])
                veg_distance_m = spatial_city_data[latest_year].get('vegetation_accessibility', {}).get('city', {}).get('mean', 1000)
                
                # Better accessibility = higher adaptive capacity
                max_walking_distance = 1000
                accessibility_score = max(0.0, 1.0 - (veg_distance_m / max_walking_distance))
                green_capacity = (green_capacity * 0.6 + accessibility_score * 0.4)
        
        return green_capacity
    
    def _calculate_surface_water_change(self, city: str) -> float:
        """Calculate surface water change based on aridity and climate factors"""
        try:
            # Use water scarcity data if available
            if hasattr(self, 'data') and 'water_scarcity_data' in self.data and city in self.data['water_scarcity_data']:
                ws_data = self.data['water_scarcity_data'][city]
                
                aridity_index = ws_data.get('aridity_index', 0.5)
                precipitation = ws_data.get('precipitation_mm_year', 500)
                
                # Base change on aridity (drier = more negative)
                if aridity_index < 0.05:  # Hyper-arid
                    base_change = -0.20
                elif aridity_index < 0.1:  # Arid
                    base_change = -0.15
                elif aridity_index < 0.2:  # Semi-arid
                    base_change = -0.10
                elif aridity_index < 0.4:  # Dry sub-humid
                    base_change = -0.05
                else:  # Humid
                    base_change = 0.02
                
                # Adjust for precipitation patterns
                if precipitation < 200:
                    precip_modifier = -0.05
                elif precipitation < 400:
                    precip_modifier = -0.02
                elif precipitation > 800:
                    precip_modifier = 0.03
                else:
                    precip_modifier = 0.0
                
                return max(-0.25, min(0.15, base_change + precip_modifier))
        except Exception as e:
            print(f"Warning: Could not calculate surface water change for {city}: {e}")
        
        # Geographic fallback for Central Asian cities (all arid/semi-arid)
        population_data = self.data['population_data'].get(city)
        if population_data and population_data.population_2024 > 500000:
            return -0.08  # Larger cities have more water stress
        else:
            return -0.05  # Smaller cities have moderate stress
    def _apply_regional_corrections(self, city: str, metrics: ClimateRiskMetrics) -> ClimateRiskMetrics:
        """Apply region-specific corrections for known data gaps and local hazards"""
        
        # Nukus-specific corrections for water scarcity and Aral Sea impacts
        if city == "Nukus":
            # Water scarcity vulnerability (major gap in current framework)
            water_stress_penalty = 0.15  # Severe groundwater depletion and Aral Sea crisis
            
            # Healthcare access vulnerability (limited medical infrastructure)
            healthcare_penalty = 0.08  # Lower hospital density in Karakalpakstan
            
            # Environmental disaster impacts (Aral Sea proximity)
            aral_sea_penalty = 0.12  # Dust storms, contamination, ecosystem collapse
            
            # Apply corrections to vulnerability (where most gaps exist)
            total_penalty = water_stress_penalty + healthcare_penalty + aral_sea_penalty
            metrics.vulnerability_score = min(1.0, metrics.vulnerability_score + total_penalty)
            
            # Also increase dust hazard due to Aral Sea
            metrics.dust_hazard = min(1.0, metrics.dust_hazard + 0.20)
            
            # Recalculate hazard score with updated dust component
            metrics.hazard_score = (
                self.hazard_weights['heat'] * metrics.heat_hazard +
                self.hazard_weights['dry'] * metrics.dry_hazard +
                self.hazard_weights['pluv'] * metrics.pluvial_hazard +
                self.hazard_weights['dust'] * metrics.dust_hazard
            )
            
        # Nukus-specific corrections for water scarcity and Aral Sea impacts
        if city == "Nukus":
            # Water scarcity vulnerability (major gap in current framework)
            water_stress_penalty = 0.15  # Severe groundwater depletion and Aral Sea crisis
            
            # Healthcare access vulnerability (limited medical infrastructure)
            healthcare_penalty = 0.08  # Lower hospital density in Karakalpakstan
            
            # Environmental disaster impacts (Aral Sea proximity)
            aral_sea_penalty = 0.12  # Dust storms, contamination, ecosystem collapse
            
            # Apply corrections to vulnerability (where most gaps exist)
            total_penalty = water_stress_penalty + healthcare_penalty + aral_sea_penalty
            metrics.vulnerability_score = min(1.0, metrics.vulnerability_score + total_penalty)
            
            # Also increase dust hazard due to Aral Sea
            metrics.dust_hazard = min(1.0, metrics.dust_hazard + 0.20)
            
            # Recalculate hazard score with updated dust component
            metrics.hazard_score = (
                self.hazard_weights['heat'] * metrics.heat_hazard +
                self.hazard_weights['dry'] * metrics.dry_hazard +
                self.hazard_weights['pluv'] * metrics.pluvial_hazard +
                self.hazard_weights['dust'] * metrics.dust_hazard
            )
            
            # Apply social sector corrections if data available
            if hasattr(metrics, 'water_access_vulnerability'):
                metrics.water_access_vulnerability = min(1.0, metrics.water_access_vulnerability + 0.25)
                metrics.healthcare_access_vulnerability = min(1.0, metrics.healthcare_access_vulnerability + 0.15)
            
            print(f"Applied regional corrections to {city}: +{total_penalty:.3f} vulnerability, +0.20 dust hazard, +0.25 water access, +0.15 healthcare")
        
        # Termez-specific corrections for border challenges and extreme poverty
        elif city == "Termez":
            # Border instability and security challenges
            border_penalty = 0.15  # Afghanistan proximity, migration pressures
            
            # Extreme economic vulnerability (lowest GDP per capita)
            poverty_penalty = 0.10  # $634 USD per capita, severe resource constraints
            
            # Remote location and infrastructure gaps
            infrastructure_penalty = 0.08  # Poor connectivity, limited services
            
            total_penalty = border_penalty + poverty_penalty + infrastructure_penalty
            metrics.vulnerability_score = min(1.0, metrics.vulnerability_score + total_penalty)
            
            # Increase exposure due to cross-border pressures
            metrics.exposure_score = min(1.0, metrics.exposure_score + 0.15)
            
            # Increase exposure due to cross-border pressures
            metrics.exposure_score = min(1.0, metrics.exposure_score + 0.15)
            
            # Apply social sector corrections for extreme poverty
            if hasattr(metrics, 'healthcare_access_vulnerability'):
                metrics.healthcare_access_vulnerability = min(1.0, metrics.healthcare_access_vulnerability + 0.20)
                metrics.education_access_vulnerability = min(1.0, metrics.education_access_vulnerability + 0.15)
            
            print(f"Applied regional corrections to {city}: +{total_penalty:.3f} vulnerability, +0.15 exposure, +0.20 healthcare, +0.15 education")
        
        # Urgench-specific corrections for Aral Sea impacts and irrigation dependence
        elif city == "Urgench":
            # Irrigation system vulnerability
            irrigation_penalty = 0.12  # Khorezm canal system deterioration
            
            # Aral Sea environmental impacts
            aral_penalty = 0.08  # Dust storms, soil salinization
            
            total_penalty = irrigation_penalty + aral_penalty
            metrics.vulnerability_score = min(1.0, metrics.vulnerability_score + total_penalty)
            
            # Increase dust hazard due to Aral Sea proximity
            metrics.dust_hazard = min(1.0, metrics.dust_hazard + 0.15)
            
            # Recalculate hazard score
            metrics.hazard_score = (
                self.hazard_weights['heat'] * metrics.heat_hazard +
                self.hazard_weights['dry'] * metrics.dry_hazard +
                self.hazard_weights['pluv'] * metrics.pluvial_hazard +
                self.hazard_weights['dust'] * metrics.dust_hazard
            )
            
            # Recalculate hazard score
            metrics.hazard_score = (
                self.hazard_weights['heat'] * metrics.heat_hazard +
                self.hazard_weights['dry'] * metrics.dry_hazard +
                self.hazard_weights['pluv'] * metrics.pluvial_hazard +
                self.hazard_weights['dust'] * metrics.dust_hazard
            )
            
            # Apply social sector corrections for irrigation dependence
            if hasattr(metrics, 'water_access_vulnerability'):
                metrics.water_access_vulnerability = min(1.0, metrics.water_access_vulnerability + 0.18)
            
            print(f"Applied regional corrections to {city}: +{total_penalty:.3f} vulnerability, +0.15 dust hazard, +0.18 water access")
        
        # Namangan-specific corrections for seismic risks and population pressure
        elif city == "Namangan":
            # Seismic and landslide vulnerability
            seismic_penalty = 0.10  # Fergana Valley earthquake zone
            
            # Population density stress with limited resources
            density_penalty = 0.12  # Highest population with low GDP per capita
            
            total_penalty = seismic_penalty + density_penalty
            metrics.vulnerability_score = min(1.0, metrics.vulnerability_score + total_penalty)
            
            # Increase overall hazard for geological risks
            metrics.hazard_score = min(1.0, metrics.hazard_score + 0.10)
            
            print(f"Applied regional corrections to {city}: +{total_penalty:.3f} vulnerability, +0.10 hazard")
        
        # Fergana-specific corrections for seismic risks and water conflicts
        elif city == "Fergana":
            # Seismic vulnerability and industrial pollution
            seismic_pollution_penalty = 0.08  # Fergana Valley risks + Soviet legacy
            
            # Water allocation conflicts and border tensions
            conflict_penalty = 0.10  # Transboundary water disputes
            
            total_penalty = seismic_pollution_penalty + conflict_penalty
            metrics.vulnerability_score = min(1.0, metrics.vulnerability_score + total_penalty)
            
            # Increase hazard for seismic and pollution risks
            metrics.hazard_score = min(1.0, metrics.hazard_score + 0.08)
            
            print(f"Applied regional corrections to {city}: +{total_penalty:.3f} vulnerability, +0.08 hazard")
        
        # Samarkand-specific corrections for heritage vulnerability and water scarcity
        elif city == "Samarkand":
            # Cultural heritage climate vulnerability
            heritage_penalty = 0.05  # UNESCO sites at risk from climate change
            
            # Tourism economic vulnerability
            tourism_penalty = 0.05  # Economic dependence on climate-sensitive tourism
            
            # Zerafshan river depletion
            water_penalty = 0.03  # Regional water stress
            
            total_penalty = heritage_penalty + tourism_penalty + water_penalty
            metrics.vulnerability_score = min(1.0, metrics.vulnerability_score + total_penalty)
            
            print(f"Applied regional corrections to {city}: +{total_penalty:.3f} vulnerability")
        
        return metrics
