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
    adaptability_score: float = 0.0
    
    # Supporting metrics
    current_suhi_intensity: float = 0.0
    temperature_trend: float = 0.0
    suhi_trend: float = 0.0
    built_area_percentage: float = 0.0
    green_space_accessibility: float = 0.0
    economic_capacity: float = 0.0


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
            'heat': 0.60,
            'dry': 0.25,
            'pluv': 0.10,
            'dust': 0.05
        }
        
        # IPCC AR6 exposure weights (from specification)
        self.exposure_weights = {
            'population': 0.60,
            'gdp': 0.25,
            'viirs': 0.15
        }
        
        # IPCC AR6 vulnerability weights (from specification)
        self.vulnerability_weights = {
            'income_inv': 0.20,
            'veg_access': 0.12,
            'fragment': 0.08,
            'delta_bio_veg': 0.06,
            'water_scarcity': 0.22,    # Water scarcity vulnerability (critical for arid regions)
            'water_access': 0.14,      # Social sector: water infrastructure vulnerability
            'healthcare_access': 0.06, # Social sector: healthcare access vulnerability
            'education_access': 0.05,  # Social sector: education access vulnerability
            'sanitation': 0.03,        # Social sector: sanitation vulnerability
            'building_age': 0.04       # Social sector: building age and renovation vulnerability
        }
        
        # IPCC AR6 adaptive capacity weights (from specification)
        self.adaptive_capacity_weights = {
            'gdp_pc': 0.40,
            'greenspace': 0.25,
            'services': 0.15,
            'social_infrastructure': 0.15,  # Social sector: schools, hospitals per capita
            'water_system': 0.05           # Social sector: water system resilience
        }
    
    def _load_water_scarcity_data(self) -> Dict[str, Dict]:
        """Load water scarcity assessment data from the water scarcity service"""
        try:
            from .water_scarcity_gee import WaterScarcityGEEAssessment
            
            water_service = WaterScarcityGEEAssessment(self.data_loader)
            water_data = water_service.assess_all_cities_water_scarcity()
            
            # Convert to dictionary format for easy lookup
            water_dict = {}
            for city, assessment in water_data.items():
                water_dict[city] = {
                    'water_scarcity_index': assessment.overall_water_scarcity_score,
                    'drought_frequency': assessment.drought_frequency,
                    'water_stress_level': assessment.aqueduct_bws_score,
                    'irrigation_demand': assessment.cropland_fraction,
                    'surface_water_availability': assessment.surface_water_change
                }
            
            print(f"Loaded water scarcity data for {len(water_dict)} cities")
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
        
        print(f"✓ Completed assessment for {len(results)} cities")
        
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
                self.hazard_weights['dust'] * metrics.dust_hazard
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
                self.vulnerability_weights['water_scarcity'] * metrics.water_scarcity_vulnerability
            )
            
            metrics.adaptive_capacity_score = (
                self.adaptive_capacity_weights['gdp_pc'] * metrics.gdp_adaptive_capacity +
                self.adaptive_capacity_weights['greenspace'] * metrics.greenspace_adaptive_capacity +
                self.adaptive_capacity_weights['services'] * metrics.services_adaptive_capacity
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
        # Prefer temperature data over SUHI data
        city_data = self.data['temperature_data'].get(city, {})
        if not city_data:
            # Fallback to SUHI data
            city_data = self.data['suhi_data'].get(city, {})
            if not city_data:
                return 0.0
            return self._calculate_hazard_from_suhi(city, city_data)
        
        years = sorted(city_data.keys())
        if len(years) < 2:
            return 0.0
        
        # Current hazard intensity (latest year summer temperatures)
        latest_year = years[-1]
        latest_stats = city_data[latest_year]
        
        # Use summer season summary for more accurate assessment
        summer_stats = latest_stats.get('summer_season_summary', {})
        
        # Extract temperature statistics from actual data structure
        urban_day = summer_stats.get('urban', {}).get('day', {})
        urban_night = summer_stats.get('urban', {}).get('night', {})
        
        # Heat stress indicators - derive from available statistics
        mean_summer_temp = urban_day.get('mean', 25)
        max_summer_temp = urban_day.get('max', 35)
        p90_summer_temp = urban_day.get('p90', 35)  # 90th percentile as proxy for hot days
        
        # Estimate extreme heat days from percentile data
        # If p90 > 40°C, likely many extreme heat days; if max > 45°C, definitely extreme
        extreme_heat_days = 0
        very_hot_days = 0
        
        if max_summer_temp > 45:
            extreme_heat_days = 15  # Estimate based on max temp
        elif p90_summer_temp > 40:
            extreme_heat_days = 5   # Some extreme days
            
        if p90_summer_temp > 35:
            very_hot_days = 30      # Many hot days if 90th percentile > 35°C
        elif mean_summer_temp > 32:
            very_hot_days = 15      # Some hot days
        
        # Temperature trend analysis (warming rate)
        temp_trends = []
        for temp_type in ['day', 'night']:
            values = []
            years_list = []
            for year in years:
                year_data = city_data[year]
                summer_data = year_data.get('summer_season_summary', {})
                urban_data = summer_data.get('urban', {})
                temp_data = urban_data.get(temp_type, {})
                temp_val = temp_data.get('mean')
                
                if temp_val is not None:
                    values.append(temp_val)
                    years_list.append(int(year))
            
            if len(values) >= 3:
                try:
                    trend = np.polyfit(years_list, values, 1)[0]  # °C per year
                    temp_trends.append(trend)
                except:
                    temp_trends.append(0.0)
        
        avg_temp_trend = np.mean(temp_trends) if temp_trends else 0.0
        
        # IPCC AR6 hazard scoring
        # Current intensity (40% weight)
        intensity_score = 0.0
        if extreme_heat_days > 10:
            intensity_score = 1.0
        elif extreme_heat_days > 5:
            intensity_score = 0.7
        elif very_hot_days > 20:
            intensity_score = 0.5
        elif mean_summer_temp > 30:
            intensity_score = 0.3
        
        # Temperature trend (40% weight)
        trend_score = 0.0
        if avg_temp_trend > 0.08:  # Very high warming
            trend_score = 1.0
        elif avg_temp_trend > 0.05:  # High warming
            trend_score = 0.7
        elif avg_temp_trend > 0.02:  # Medium warming
            trend_score = 0.4
        elif avg_temp_trend > 0.0:  # Low warming
            trend_score = 0.2
        
        # Maximum temperature threshold (20% weight)
        max_temp_score = min(1.0, max(0.0, (max_summer_temp - 35) / 10))
        
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
        
        # Population exposure (normalized by city population distribution)
        pop_score = self.data_loader.pct_norm(
            self.data['cache']['population'], 
            population_data.population_2024
        )
        
        # Urban density exposure
        density_score = self.data_loader.pct_norm(
            self.data['cache']['density'], 
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
                            self.data['cache']['built_pct'], built_pct
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
                            self.data['cache']['nightlights'], urban_nl
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
        
        # Economic vulnerability (inverted GDP per capita)
        gdp_vulnerability = self.data_loader.pct_norm(
            self.data['cache']['gdp'], 
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
                            self.data['cache']['built_pct'], built_pct
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
        
        # Weighted vulnerability score
        vulnerability_score = (0.4 * gdp_vulnerability + 0.25 * built_vulnerability + 
                              0.15 * green_vulnerability + 0.2 * water_vulnerability)
        
        return min(1.0, vulnerability_score)
    
    def calculate_adaptive_capacity_score(self, city: str) -> float:
        """Calculate adaptive capacity score based on economic and environmental resources"""
        population_data = self.data['population_data'].get(city)
        if not population_data:
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
    
    def _calculate_water_system_capacity(self, sanitation_indicators: Dict[str, Any]) -> float:
        """Calculate water system adaptive capacity from sanitation indicators"""
        try:
            # Extract water source distribution
            water_sources = sanitation_indicators.get('water_source_distribution', {})
            
            centralized = water_sources.get('centralized', 0)
            local = water_sources.get('local', 0)
            carried = water_sources.get('carried', 0)
            none = water_sources.get('none', 0)
            
            total = centralized + local + carried + none
            if total == 0:
                return 0.5
            
            # Capacity weights: centralized (1.0), local (0.7), carried (0.3), none (0.0)
            capacity = (
                centralized * 1.0 +
                local * 0.7 +
                carried * 0.3 +
                none * 0.0
            ) / total
            
            return min(1.0, max(0.0, capacity))
        except:
            return 0.5
    
    def _load_social_sector_data(self, city: str) -> Optional[Dict[str, Any]]:
        """Load social sector data for a city"""
        try:
            import json
            from pathlib import Path
            
            social_file = Path('suhi_analysis_output/social_sector') / f'{city}_social_sector.json'
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
        metrics.water_system_capacity = self._calculate_water_system_capacity(sanitation_indicators)
        
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
            self.vulnerability_weights['building_age'] * metrics.building_age_vulnerability
        )
        
        metrics.adaptive_capacity_score = (
            self.adaptive_capacity_weights['gdp_pc'] * metrics.gdp_adaptive_capacity +
            self.adaptive_capacity_weights['greenspace'] * metrics.greenspace_adaptive_capacity +
            self.adaptive_capacity_weights['services'] * metrics.services_adaptive_capacity +
            self.adaptive_capacity_weights['social_infrastructure'] * metrics.social_infrastructure_capacity +
            self.adaptive_capacity_weights['water_system'] * metrics.water_system_capacity
        )
        
        # Recalculate overall risk with updated components
        metrics.overall_risk_score = self._calculate_overall_risk(metrics)
        metrics.adaptability_score = self._calculate_adaptability_score(metrics)
        
        # Recalculate composite hazard and exposure scores to ensure consistency
        metrics.hazard_score = (
            self.hazard_weights['heat'] * metrics.heat_hazard +
            self.hazard_weights['dry'] * metrics.dry_hazard +
            self.hazard_weights['pluv'] * metrics.pluvial_hazard +
            self.hazard_weights['dust'] * metrics.dust_hazard
        )
        
        metrics.exposure_score = (
            self.exposure_weights['population'] * metrics.population_exposure +
            self.exposure_weights['gdp'] * metrics.gdp_exposure +
            self.exposure_weights['viirs'] * metrics.viirs_exposure
        )
        
        return metrics
    
    def _calculate_overall_risk(self, metrics: ClimateRiskMetrics) -> float:
        """Calculate overall risk score using IPCC AR6 framework"""
        # Risk = H × E × V (multiplicative formula from IPCC AR6)
        overall_risk = metrics.hazard_score * metrics.exposure_score * metrics.vulnerability_score
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
        
        return metrics
    
    def _calculate_exposure_components(self, city: str, metrics: ClimateRiskMetrics) -> ClimateRiskMetrics:
        """Calculate individual exposure components using IPCC AR6 framework"""
        population_data = self.data['population_data'].get(city)
        if not population_data:
            return metrics
        
        # Population exposure (E_pop)
        metrics.population_exposure = self.data_loader.pct_norm(
            self.data['cache']['population'], 
            population_data.population_2024
        )
        
        # GDP exposure (E_gdp) - composition-weighted City GDP
        city_gdp = population_data.population_2024 * population_data.gdp_per_capita_usd
        if 'city_gdp' not in self.data['cache']:
            # Initialize city_gdp cache if not present
            city_gdps = []
            for pop_data in self.data['population_data'].values():
                if pop_data.population_2024 and pop_data.gdp_per_capita_usd:
                    city_gdps.append(pop_data.population_2024 * pop_data.gdp_per_capita_usd)
            self.data['cache']['city_gdp'] = city_gdps
        
        metrics.gdp_exposure = self.data_loader.pct_norm(
            self.data['cache']['city_gdp'], 
            city_gdp
        )
        
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
        
        return metrics
    
    def _calculate_adaptive_capacity_components(self, city: str, metrics: ClimateRiskMetrics) -> ClimateRiskMetrics:
        """Calculate individual adaptive capacity components using IPCC AR6 framework"""
        population_data = self.data['population_data'].get(city)
        if not population_data:
            return metrics
        
        # GDP per capita adaptive capacity (AC_gdp_pc)
        metrics.gdp_adaptive_capacity = self.data_loader.pct_norm(
            self.data['cache']['gdp'], 
            population_data.gdp_per_capita_usd
        )
        
        # Greenspace adaptive capacity (AC_greenspace)
        metrics.greenspace_adaptive_capacity = self._calculate_greenspace_adaptive_capacity(city)
        
        # Services adaptive capacity (AC_services) - VIIRS as proxy
        metrics.services_adaptive_capacity = self._calculate_viirs_exposure(city)
        
        return metrics
    
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
    
    # Individual hazard calculation methods
    def _calculate_heat_hazard(self, city: str) -> float:
        """Calculate heat hazard component (H_heat)"""
        # Use climatological estimation when temperature data is unavailable
        if not self.data['temperature_data'].get(city) and not self.data['suhi_data'].get(city):
            return self._estimate_climatological_heat_hazard(city)

        # Use existing heat hazard calculation from calculate_hazard_score
        return self.calculate_hazard_score(city)
    
    def _calculate_dry_hazard(self, city: str) -> float:
        """Calculate dry/ecological stress hazard (H_dry)"""
        # Use climatological estimation when LULC data is unavailable
        if not self.data['lulc_data']:
            return self._estimate_climatological_dry_hazard(city)
        
        # Based on low NDVI/EVI in summer, negative seasonal changes
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
        # Use climatological estimation when LULC data is unavailable
        if not self.data['lulc_data']:
            return self._estimate_climatological_dust_hazard(city)
        
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
        """Calculate pluvial proxy hazard (H_pluv)"""
        # Use climatological estimation when LULC data is unavailable
        if not self.data['lulc_data']:
            return self._estimate_climatological_pluvial_hazard(city)
        
        # Based on built-up share and edge density (imperviousness/flow concentration)
        pluvial_score = 0.0
        
        # Built-up percentage from LULC
        for lulc_city in self.data['lulc_data']:
            if lulc_city.get('city') == city:
                areas = lulc_city.get('areas_m2', {})
                if areas:
                    years = sorted([int(y) for y in areas.keys()])
                    if years:
                        latest_year = str(years[-1])
                        built_pct = areas[latest_year].get('Built_Area', {}).get('percentage', 0)
                        pluvial_score = self.data_loader.pct_norm(
                            self.data['cache']['built_pct'], built_pct
                        )
                break
        
        return pluvial_score
    
    def _calculate_viirs_exposure(self, city: str) -> float:
        """Calculate VIIRS exposure component"""
        viirs_score = 0.0
        for nl_city in self.data['nightlights_data']:
            if nl_city.get('city') == city:
                years_data = nl_city.get('years', {})
                if years_data:
                    years = sorted([int(y) for y in years_data.keys()])
                    if years:
                        latest_year = str(years[-1])
                        urban_nl = years_data[latest_year].get('stats', {}).get('urban_core', {}).get('mean', 0)
                        viirs_score = self.data_loader.pct_norm(
                            self.data['cache']['nightlights'], urban_nl
                        )
                break
        return viirs_score
    
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
        """Calculate biomass/vegetation trend vulnerability"""
        bio_vuln = 0.0
        
        # Check vegetation trends from LULC data
        for lulc_city in self.data['lulc_data']:
            if lulc_city.get('city') == city:
                areas = lulc_city.get('areas_m2', {})
                if areas:
                    years = sorted([int(y) for y in areas.keys()])
                    if len(years) >= 3:
                        # Calculate vegetation trend over time
                        veg_percentages = []
                        for year in years:
                            year_data = areas[str(year)]
                            total_veg = (year_data.get('Trees', {}).get('percentage', 0) + 
                                       year_data.get('Crops', {}).get('percentage', 0) +
                                       year_data.get('Grass', {}).get('percentage', 0))
                            veg_percentages.append(total_veg)
                        
                        try:
                            veg_trend = np.polyfit(years, veg_percentages, 1)[0]
                            # Negative trend = higher vulnerability
                            if veg_trend < 0:
                                bio_vuln = min(1.0, abs(veg_trend) * 2.0)  # Scale factor
                        except:
                            pass
                break
        
        return bio_vuln
    
    def _calculate_water_scarcity_vulnerability(self, city: str) -> float:
        """Calculate water scarcity vulnerability based on water scarcity assessment"""
        if city not in self.water_scarcity_data:
            return 0.5  # Default moderate vulnerability if no data

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

    def _estimate_climatological_heat_hazard(self, city: str) -> float:
        """Estimate heat hazard based on climatological knowledge of Uzbekistan"""
        from .utils import UZBEKISTAN_CITIES

        if city not in UZBEKISTAN_CITIES:
            return 0.3  # Default moderate heat hazard

        city_info = UZBEKISTAN_CITIES[city]
        lat, lon = city_info['lat'], city_info['lon']

        # Uzbekistan climate characteristics
        # Northern cities (cooler summers) vs Southern cities (hotter summers)
        # Western cities (arid) vs Eastern cities (relatively more moderate)

        base_heat_hazard = 0.0

        # Latitude-based heat intensity (southern cities hotter)
        if lat < 39.0:  # Southern cities (Termez, Qarshi, Bukhara)
            base_heat_hazard = 0.8
        elif lat < 40.5:  # Central cities (Samarkand, Jizzakh, Navoiy)
            base_heat_hazard = 0.7
        elif lat < 41.5:  # Northern cities (Tashkent, Nurafshon, Andijan)
            base_heat_hazard = 0.6
        else:  # Northernmost cities (Namangan, Fergana, Urgench)
            base_heat_hazard = 0.5

        # Longitude-based aridity adjustment (western cities more arid/hot)
        if lon < 65.0:  # Western cities (more arid)
            base_heat_hazard += 0.1
        elif lon > 70.0:  # Eastern cities (Fergana Valley - more moderate)
            base_heat_hazard -= 0.1

        # City-specific adjustments based on known climate patterns
        city_adjustments = {
            'Tashkent': 0.0,    # Capital, some urban cooling
            'Samarkand': 0.05,  # Historic city, moderate climate
            'Bukhara': 0.1,     # Desert climate, very hot
            'Khiva': 0.15,      # Arid desert climate
            'Urgench': 0.15,    # Arid desert climate
            'Nukus': 0.2,       # Extreme desert climate
            'Termez': 0.1,      # Southern desert climate
            'Qarshi': 0.1,      # Southern desert climate
            'Andijan': -0.05,   # Fergana Valley, more moderate
            'Fergana': -0.05,   # Fergana Valley, more moderate
            'Namangan': -0.05,  # Fergana Valley, more moderate
        }

        adjustment = city_adjustments.get(city, 0.0)
        heat_hazard = max(0.0, min(1.0, base_heat_hazard + adjustment))

        return heat_hazard

    def _estimate_climatological_dry_hazard(self, city: str) -> float:
        """Estimate dry/ecological hazard based on aridity patterns"""
        from .utils import UZBEKISTAN_CITIES

        if city not in UZBEKISTAN_CITIES:
            return 0.4  # Default moderate dry hazard

        city_info = UZBEKISTAN_CITIES[city]
        lat, lon = city_info['lat'], city_info['lon']

        # Aridity increases from east to west and north to south
        base_dry_hazard = 0.0

        # Longitude-based aridity (western cities more arid)
        if lon < 60.0:  # Extreme west (Nukus, Urgench)
            base_dry_hazard = 0.9
        elif lon < 65.0:  # Western cities
            base_dry_hazard = 0.8
        elif lon < 68.0:  # Central cities
            base_dry_hazard = 0.6
        elif lon < 70.0:  # Eastern cities
            base_dry_hazard = 0.4
        else:  # Fergana Valley (more precipitation)
            base_dry_hazard = 0.3

        # Latitude adjustment (southern cities slightly more arid)
        if lat < 39.0:
            base_dry_hazard += 0.1

        # City-specific adjustments
        city_adjustments = {
            'Nukus': 0.1,       # Aral Sea region, extremely arid
            'Urgench': 0.1,     # Khorezm region, very arid
            'Bukhara': 0.05,    # Kyzylkum desert influence
            'Navoiy': 0.05,     # Desert mining region
            'Andijan': -0.1,    # Fergana Valley, irrigated agriculture
            'Fergana': -0.1,    # Fergana Valley, irrigated agriculture
            'Namangan': -0.1,   # Fergana Valley, irrigated agriculture
            'Tashkent': -0.05,  # Better water infrastructure
        }

        adjustment = city_adjustments.get(city, 0.0)
        dry_hazard = max(0.0, min(1.0, base_dry_hazard + adjustment))

        return dry_hazard

    def _estimate_climatological_dust_hazard(self, city: str) -> float:
        """Estimate dust hazard based on desert proximity and wind patterns"""
        from .utils import UZBEKISTAN_CITIES

        if city not in UZBEKISTAN_CITIES:
            return 0.3  # Default moderate dust hazard

        city_info = UZBEKISTAN_CITIES[city]
        lat, lon = city_info['lat'], city_info['lon']

        # Dust hazard based on proximity to deserts and wind patterns
        base_dust_hazard = 0.0

        # Western cities near Kyzylkum and Aral Sea deserts
        if lon < 65.0:
            base_dust_hazard = 0.8
        elif lon < 68.0:
            base_dust_hazard = 0.6
        else:
            base_dust_hazard = 0.4

        # Southern cities affected by desert winds
        if lat < 39.0:
            base_dust_hazard += 0.1

        # City-specific adjustments
        city_adjustments = {
            'Nukus': 0.2,       # Near Aral Sea disaster zone
            'Urgench': 0.1,     # Khorezm desert winds
            'Bukhara': 0.1,     # Kyzylkum desert proximity
            'Navoiy': 0.1,      # Desert mining operations
            'Tashkent': -0.1,   # Urban area, less dust
            'Andijan': -0.1,    # Mountain-protected valley
            'Fergana': -0.1,    # Mountain-protected valley
            'Namangan': -0.1,   # Mountain-protected valley
        }

        adjustment = city_adjustments.get(city, 0.0)
        dust_hazard = max(0.0, min(1.0, base_dust_hazard + adjustment))

        return dust_hazard

    def _estimate_climatological_pluvial_hazard(self, city: str) -> float:
        """Estimate pluvial (heavy rain) hazard based on climate patterns"""
        from .utils import UZBEKISTAN_CITIES

        if city not in UZBEKISTAN_CITIES:
            return 0.2  # Default low pluvial hazard

        city_info = UZBEKISTAN_CITIES[city]
        lat, lon = city_info['lat'], city_info['lon']

        # Pluvial hazard based on monsoon influence and topography
        base_pluvial_hazard = 0.0

        # Eastern cities (Fergana Valley) get more precipitation
        if lon > 70.0:
            base_pluvial_hazard = 0.5
        elif lon > 68.0:
            base_pluvial_hazard = 0.3
        else:
            base_pluvial_hazard = 0.2

        # Northern cities slightly more precipitation
        if lat > 40.5:
            base_pluvial_hazard += 0.1

        # City-specific adjustments
        city_adjustments = {
            'Andijan': 0.1,     # Fergana Valley, more rainfall
            'Fergana': 0.1,     # Fergana Valley, more rainfall
            'Namangan': 0.1,    # Fergana Valley, more rainfall
            'Tashkent': 0.05,   # Moderate rainfall
            'Nukus': -0.1,      # Extremely arid
            'Urgench': -0.1,    # Very arid
            'Bukhara': -0.05,   # Desert climate
        }

        adjustment = city_adjustments.get(city, 0.0)
        pluvial_hazard = max(0.0, min(1.0, base_pluvial_hazard + adjustment))

        return pluvial_hazard
