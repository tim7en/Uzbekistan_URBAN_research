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
                print("No water scarcity data files found - water scarcity vulnerability will be 0.0 for all cities")
            
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
        
        # No regional corrections - use only real data
        
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
        """Calculate water access vulnerability from sanitation indicators - no defaults"""
        if not sanitation_indicators:
            return 0.0
            
        try:
            # Extract water source distribution
            water_sources = sanitation_indicators.get('water_sources', {})
            if not water_sources:
                return 0.0
            
            # Get electricity access percentage
            electricity_access_pct = sanitation_indicators.get('electricity_access')
            if electricity_access_pct is None:
                return 0.0
            
            # Calculate vulnerability based on water source quality
            # Higher vulnerability for carried/none sources, lower for centralized
            centralized = water_sources.get('centralized', 0)
            local = water_sources.get('local', 0)
            carried = water_sources.get('carried', 0)
            none = water_sources.get('none', 0)
            
            total = centralized + local + carried + none
            if total == 0:
                return 0.0  # No data available
            
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
        except Exception as e:
            print(f"Warning: Error calculating water access vulnerability: {e}")
            return 0.0  # No defaults when calculation fails
    
    def _calculate_healthcare_access_vulnerability(self, per_capita: Dict[str, Any]) -> float:
        """Calculate healthcare access vulnerability from per capita metrics - no defaults"""
        if not per_capita:
            return 0.0
            
        try:
            hospitals_per_1000 = per_capita.get('hospitals_per_1000')
            if hospitals_per_1000 is None:
                return 0.0
            
            # Lower healthcare access = higher vulnerability
            # Scale: 0 hospitals/1000 = 1.0 vulnerability, 0.5 hospitals/1000 = 0.0 vulnerability
            vulnerability = max(0.0, 1.0 - (hospitals_per_1000 * 2))
            return min(1.0, vulnerability)
        except Exception as e:
            print(f"Warning: Error calculating healthcare access vulnerability: {e}")
            return 0.0
    
    def _calculate_education_access_vulnerability(self, per_capita: Dict[str, Any]) -> float:
        """Calculate education access vulnerability from per capita metrics - no defaults"""
        if not per_capita:
            return 0.0
            
        try:
            schools_per_1000 = per_capita.get('schools_per_1000')
            kindergartens_per_1000 = per_capita.get('kindergartens_per_1000')
            
            if schools_per_1000 is None or kindergartens_per_1000 is None:
                return 0.0
            
            # Combined education access metric
            education_access = (schools_per_1000 + kindergartens_per_1000) / 2
            
            # Lower education access = higher vulnerability
            # Scale: 0 education/1000 = 1.0 vulnerability, 0.4 education/1000 = 0.0 vulnerability
            vulnerability = max(0.0, 1.0 - (education_access * 2.5))
            return min(1.0, vulnerability)
        except Exception as e:
            print(f"Warning: Error calculating education access vulnerability: {e}")
            return 0.0
    
    def _calculate_sanitation_vulnerability(self, sanitation_indicators: Dict[str, Any]) -> float:
        """Calculate sanitation vulnerability from sanitation indicators"""
        try:
            # Use water vulnerability as proxy for sanitation vulnerability
            # Areas with poor water access typically have poor sanitation
            return self._calculate_water_access_vulnerability(sanitation_indicators)
        except:
            return 0.5
    
    def _calculate_social_infrastructure_capacity(self, per_capita: Dict[str, Any]) -> float:
        """Calculate social infrastructure adaptive capacity from per capita metrics - no defaults"""
        if not per_capita:
            return 0.0
            
        try:
            hospitals_per_1000 = per_capita.get('hospitals_per_1000')
            schools_per_1000 = per_capita.get('schools_per_1000')
            kindergartens_per_1000 = per_capita.get('kindergartens_per_1000')
            
            if (hospitals_per_1000 is None or schools_per_1000 is None or 
                kindergartens_per_1000 is None):
                return 0.0
            
            # Combined social infrastructure metric
            social_infra = hospitals_per_1000 + schools_per_1000 + kindergartens_per_1000
            
            # Higher social infrastructure = higher adaptive capacity
            # Scale: 0 social infra/1000 = 0.0 capacity, 1.0 social infra/1000 = 1.0 capacity
            capacity = min(1.0, social_infra)
            return max(0.0, capacity)
        except Exception as e:
            print(f"Warning: Error calculating social infrastructure capacity: {e}")
            return 0.0
    
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
        # Use real GDP data instead of default 0.4
        population_data = self.data['population_data'].get(city)
        if population_data and hasattr(population_data, 'gdp_per_capita_usd') and population_data.gdp_per_capita_usd:
            gdp = population_data.gdp_per_capita_usd
            # Use real GDP ranges instead of arbitrary thresholds
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
        
        # No fallback - return 0.0 when no real data is available
        return 0.0
    
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
                # Calculate air pollution vulnerability based on population density and built area
                # Only use real data - no default air quality hazard when data is missing
                air_hazard = self._calculate_air_quality_hazard(city)
                if air_hazard > 0:
                    metrics.air_pollution_vulnerability = min(1.0, air_hazard * 0.8)  # Scale down hazard to vulnerability
                else:
                    metrics.air_pollution_vulnerability = 0.0  # No data = no vulnerability assumption
        # Calculate air pollution vulnerability based on population density and built area
        # Only use real data when population data is available
        if not population_data:
            metrics.air_pollution_vulnerability = 0.0
            return metrics
            
        density = population_data.density_per_km2
        # Base vulnerability on density - only use real data
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
        
        # Adjust for built environment from real LULC data
        built_modifier = 0.0
        for lulc_city in self.data['lulc_data']:
            if lulc_city.get('city') == city:
                areas = lulc_city.get('areas_m2', {})
                if areas:
                    latest_year = max(areas.keys(), key=lambda x: int(x))
                    built_pct = areas[latest_year].get('Built_Area', {}).get('percentage')
                    if built_pct is not None:  # Only adjust if real data exists
                        if built_pct >= 60:
                            built_modifier = 0.15
                        elif built_pct >= 40:
                            built_modifier = 0.1
                        elif built_pct >= 25:
                            built_modifier = 0.0
                        else:
                            built_modifier = -0.1
                break
        
        metrics.air_pollution_vulnerability = min(1.0, max(0.0, base_vuln + built_modifier))
        
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

        # Try to load real social sector data first
        social_data = self._load_social_sector_data(city)
        if social_data:
            # Healthcare infrastructure capacity from real data
            per_capita = social_data.get('per_capita_metrics', {})
            healthcare_capacity = 1.0 - self._calculate_healthcare_access_vulnerability(per_capita)
            
            # Educational infrastructure capacity from real data  
            education_capacity = 1.0 - self._calculate_education_access_vulnerability(per_capita)
        else:
            # No social sector data available - return 0.0 to avoid assumptions
            healthcare_capacity = 0.0
            education_capacity = 0.0

        # Economic capacity for service provision - use real GDP data only
        if population_data.gdp_per_capita_usd:
            economic_capacity = self.data_loader.pct_norm(
                self.data['cache']['gdp'], 
                population_data.gdp_per_capita_usd
            )
        else:
            economic_capacity = 0.0

        # Population density factor (higher density = better service accessibility)
        # Use real density data only
        if population_data.density_per_km2:
            population_density = population_data.density_per_km2
            density_capacity = min(1.0, population_density / 1000)  # Normalize to reasonable urban density
        else:
            density_capacity = 0.0

        # Combined services capacity - only when real data is available
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
        """Calculate heat hazard using only real temperature data - no defaults or fallbacks"""
        return self.calculate_hazard_score(city)
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
        """Calculate pluvial hazard based on urban characteristics using only real data"""
        if not self.data['lulc_data']:
            print(f"Warning: LULC data missing for {city} - pluvial hazard set to 0.0")
            return 0.0
        
        # Find LULC data for this city
        current_lulc = None
        for lulc_city in self.data['lulc_data']:
            if lulc_city.get('city') == city:
                current_lulc = lulc_city
                break
        
        if not current_lulc:
            print(f"Warning: No LULC data for {city} - pluvial hazard set to 0.0")
            return 0.0
        
        # Get population data
        population_data = self.data['population_data'].get(city)
        if not population_data:
            print(f"Warning: No population data for {city} - pluvial hazard set to 0.0")
            return 0.0
        
        # Calculate based on real LULC data
        areas = current_lulc.get('areas_m2', {})
        if not areas:
            print(f"Warning: No area data in LULC for {city} - pluvial hazard set to 0.0")
            return 0.0
        
        years = sorted([int(y) for y in areas.keys()])
        if not years:
            print(f"Warning: No year data in LULC for {city} - pluvial hazard set to 0.0")
            return 0.0
        
        latest_year = str(years[-1])
        year_data = areas[latest_year]
        
        # Urban imperviousness (primary factor - 60% weight)
        built_pct = year_data.get('Built_Area', {}).get('percentage', 0) / 100.0
        imperv_component = min(built_pct * 1.2, 1.0)  # Scale up built area impact
        
        # Population density pressure (30% weight)
        if population_data.density_per_km2:
            density = population_data.density_per_km2
            density_component = min(density / 10000.0, 1.0)
        else:
            density_component = 0.0
        
        # Drainage capacity loss from urbanization (10% weight)
        trees_pct = year_data.get('Trees', {}).get('percentage', 0) / 100.0
        grass_pct = year_data.get('Grass', {}).get('percentage', 0) / 100.0
        crops_pct = year_data.get('Crops', {}).get('percentage', 0) / 100.0
        veg_pct = trees_pct + grass_pct + crops_pct
        
        drainage_loss = 1.0 - veg_pct  # Less vegetation = more drainage loss
        drainage_component = min(drainage_loss * 0.8, 1.0)
        
        # Combined pluvial risk
        pluvial_risk = (0.6 * imperv_component + 
                       0.3 * density_component + 
                       0.1 * drainage_component)
        
        return min(1.0, pluvial_risk)
    
    def _calculate_viirs_exposure(self, city: str) -> float:
        """Calculate VIIRS exposure using only real nightlight data"""
        # Find nightlight data for this city
        current_nightlight = None
        for nightlight_city in self.data['nightlights_data']:
            if nightlight_city.get('city') == city:
                current_nightlight = nightlight_city
                break
        
        if not current_nightlight:
            print(f"Warning: No nightlight data for {city} - VIIRS exposure set to 0.0")
            return 0.0
        
        years_data = current_nightlight.get('years', {})
        if not years_data:
            print(f"Warning: No year data in nightlights for {city} - VIIRS exposure set to 0.0")
            return 0.0
        
        # Get latest year data
        latest_year = max(years_data.keys())
        year_data = years_data[latest_year]
        
        if 'stats' not in year_data or 'urban_core' not in year_data['stats']:
            print(f"Warning: No urban core stats in nightlights for {city} - VIIRS exposure set to 0.0")
            return 0.0
        
        viirs_value = year_data['stats']['urban_core'].get('mean', 0)
        if viirs_value <= 0:
            return 0.0
        
        # Initialize cache for VIIRS values if needed
        if 'viirs_values' not in self.data['cache']:
            viirs_values = []
            for nl_city in self.data['nightlights_data']:
                if 'years' in nl_city:
                    nl_years = nl_city['years']
                    if nl_years:
                        nl_latest = max(nl_years.keys())
                        nl_data = nl_years[nl_latest]
                        if 'stats' in nl_data and 'urban_core' in nl_data['stats']:
                            viirs_val = nl_data['stats']['urban_core'].get('mean', 0)
                            # Apply log transformation to reduce skewness
                            log_viirs = np.log(viirs_val + 1)
                            viirs_values.append(log_viirs)
            self.data['cache']['viirs_values'] = viirs_values
        
        # Apply log transformation to current value
        current_log_viirs = np.log(viirs_value + 1)
        
        # Use percentile normalization
        if len(self.data['cache']['viirs_values']) > 0:
            return self.data_loader.pct_norm(
                self.data['cache']['viirs_values'], 
                current_log_viirs
            )
        else:
            return 0.0
    def _calculate_veg_access_vulnerability(self, city: str) -> float:
        """Calculate vegetation access vulnerability using only real spatial data"""
        spatial_city_data = self.data['spatial_data'].get('per_year', {}).get(city, {})
        if not spatial_city_data:
            print(f"Warning: No spatial data for {city} - vegetation access vulnerability set to 0.0")
            return 0.0
        
        years = sorted([int(y) for y in spatial_city_data.keys()])
        if not years:
            print(f"Warning: No year data in spatial data for {city} - vegetation access vulnerability set to 0.0")
            return 0.0
        
        latest_year = str(years[-1])
        veg_access_data = spatial_city_data[latest_year].get('vegetation_accessibility', {}).get('city', {})
        if not veg_access_data or 'mean' not in veg_access_data:
            print(f"Warning: No vegetation accessibility data for {city} - vegetation access vulnerability set to 0.0")
            return 0.0
        
        veg_distance_m = veg_access_data['mean']
        
        # Higher distance = higher vulnerability (no arbitrary defaults)
        max_distance = 2000  # 2km as maximum reasonable distance
        veg_vuln = min(1.0, veg_distance_m / max_distance)
        
        return veg_vuln
    
    def _calculate_fragmentation_vulnerability(self, city: str) -> float:
        """Calculate fragmentation vulnerability using only real spatial data"""
        spatial_city_data = self.data['spatial_data'].get('per_year', {}).get(city, {})
        if not spatial_city_data:
            print(f"Warning: No spatial data for {city} - fragmentation vulnerability set to 0.0")
            return 0.0
        
        years = sorted([int(y) for y in spatial_city_data.keys()])
        if not years:
            print(f"Warning: No year data in spatial data for {city} - fragmentation vulnerability set to 0.0")
            return 0.0
        
        latest_year = str(years[-1])
        patch_data = spatial_city_data[latest_year].get('veg_patches', {})
        if not patch_data or 'patch_count' not in patch_data:
            print(f"Warning: No vegetation patch data for {city} - fragmentation vulnerability set to 0.0")
            return 0.0
        
        # More patches with smaller average size = higher fragmentation
        patch_count = patch_data['patch_count']
        if patch_count <= 0:
            return 0.0
        
        # Initialize cache for patch counts if needed
        if 'veg_patches' not in self.data['cache']:
            patch_counts = []
            for spatial_city in self.data['spatial_data'].get('per_year', {}).values():
                if spatial_city:
                    latest_spatial_year = max(spatial_city.keys()) if spatial_city else None
                    if latest_spatial_year:
                        patches = spatial_city[latest_spatial_year].get('veg_patches', {})
                        if 'patch_count' in patches:
                            patch_counts.append(patches['patch_count'])
            self.data['cache']['veg_patches'] = patch_counts
        
        if len(self.data['cache']['veg_patches']) > 0:
            frag_vuln = self.data_loader.pct_norm(
                self.data['cache']['veg_patches'], patch_count
            )
        else:
            frag_vuln = 0.0
        
        return frag_vuln
    
    def _calculate_bio_trend_vulnerability(self, city: str) -> float:
        """Calculate bio trend vulnerability using only real LULC data"""
        # Find LULC data for this city
        lulc_city_data = None
        for lulc_city in self.data['lulc_data']:
            if lulc_city.get('city') == city:
                lulc_city_data = lulc_city
                break
        
        if not lulc_city_data:
            print(f"Warning: No LULC data for {city} - bio trend vulnerability set to 0.0")
            return 0.0
        
        areas = lulc_city_data.get('areas_m2', {})
        if not areas or len(areas) < 2:  # Need at least 2 years for trend
            print(f"Warning: Insufficient temporal LULC data for {city} - bio trend vulnerability set to 0.0")
            return 0.0
        
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
        try:
            veg_trend = np.polyfit(years, veg_percentages, 1)[0]
            
            # Convert trend to vulnerability (negative trend = higher vulnerability)
            # Scale the trend appropriately
            bio_vulnerability = max(0.0, -veg_trend * 10)  # Scale negative trend to positive vulnerability
            return min(1.0, bio_vulnerability)
        except:
            print(f"Warning: Could not calculate vegetation trend for {city} - bio trend vulnerability set to 0.0")
            return 0.0
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
        """Calculate greenspace adaptive capacity using only real LULC and spatial data"""
        green_capacity = 0.0
        
        # Get vegetation percentage from real LULC data
        lulc_data_found = False
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
                        
                        if len(self.data['cache']['green_pct']) > 0:
                            green_capacity = self.data_loader.pct_norm(
                                self.data['cache']['green_pct'], total_green
                            )
                            lulc_data_found = True
                break
        
        if not lulc_data_found:
            print(f"Warning: No LULC data for {city} - using accessibility only")
        
        # Combine with accessibility if available
        spatial_city_data = self.data['spatial_data'].get('per_year', {}).get(city, {})
        if spatial_city_data:
            years = sorted([int(y) for y in spatial_city_data.keys()])
            if years:
                latest_year = str(years[-1])
                veg_access_data = spatial_city_data[latest_year].get('vegetation_accessibility', {}).get('city', {})
                if 'mean' in veg_access_data:
                    veg_distance_m = veg_access_data['mean']
                    
                    # Better accessibility = higher adaptive capacity
                    max_walking_distance = 1000
                    accessibility_score = max(0.0, 1.0 - (veg_distance_m / max_walking_distance))
                    
                    if lulc_data_found:
                        green_capacity = (green_capacity * 0.6 + accessibility_score * 0.4)
                    else:
                        green_capacity = accessibility_score
        
        if not lulc_data_found and not spatial_city_data:
            print(f"Warning: No vegetation data for {city} - greenspace capacity set to 0.0")
            return 0.0
        
        return green_capacity
    
    def _calculate_surface_water_change(self, city: str) -> float:
        """Calculate surface water change based on real water scarcity data only"""
        if not hasattr(self, 'water_scarcity_data') or city not in self.water_scarcity_data:
            print(f"Warning: No water scarcity data for {city} - surface water change set to 0.0")
            return 0.0
        
        try:
            ws_data = self.water_scarcity_data[city]
            
            # Check for actual surface water change data
            surface_water_change = ws_data.get('surface_water_availability')
            if surface_water_change is not None:
                return max(-0.25, min(0.15, surface_water_change))
            
            # Calculate from aridity and precipitation if available
            aridity_index = ws_data.get('aridity_index')
            precipitation = ws_data.get('precipitation_mm_year')
            
            if aridity_index is None or precipitation is None:
                print(f"Warning: Insufficient water data for {city} - surface water change set to 0.0")
                return 0.0
            
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
            return 0.0
