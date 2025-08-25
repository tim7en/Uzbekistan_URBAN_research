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
    
    # IPCC AR6 Core Components
    hazard_score: float = 0.0
    exposure_score: float = 0.0
    vulnerability_score: float = 0.0
    adaptive_capacity_score: float = 0.0
    
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
        
        # IPCC AR6 risk thresholds and weights
        self.risk_thresholds = {
            'heat_stress': {'low': 1.0, 'medium': 2.0, 'high': 3.0, 'very_high': 4.0},
            'temperature_trend': {'low': 0.02, 'medium': 0.05, 'high': 0.08, 'very_high': 0.12},  # °C/year
            'urban_expansion': {'low': 0.02, 'medium': 0.05, 'high': 0.08, 'very_high': 0.12}  # fraction/year
        }
        
        # Component weights for overall risk calculation (IPCC AR6 approach)
        self.component_weights = {
            'hazard': 0.3,
            'exposure': 0.25,
            'vulnerability': 0.25,
            'adaptive_capacity': 0.2  # Negative weight (higher capacity = lower risk)
        }
    
    def assess_all_cities(self) -> Dict[str, ClimateRiskMetrics]:
        """Run full climate risk assessment for all cities"""
        print("Running IPCC AR6-based climate risk assessment...")
        
        all_cities = set(self.data['temperature_data'].keys()) | set(self.data['suhi_data'].keys())
        
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
        
        # Calculate IPCC AR6 components
        metrics.hazard_score = self.calculate_hazard_score(city)
        metrics.exposure_score = self.calculate_exposure_score(city)
        metrics.vulnerability_score = self.calculate_vulnerability_score(city)
        metrics.adaptive_capacity_score = self.calculate_adaptive_capacity_score(city)
        
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
        
        # Weighted vulnerability score
        vulnerability_score = (0.5 * gdp_vulnerability + 0.3 * built_vulnerability + 
                              0.2 * green_vulnerability)
        
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
    
    def _calculate_overall_risk(self, metrics: ClimateRiskMetrics) -> float:
        """Calculate overall risk score using IPCC AR6 framework"""
        # Risk = (Hazard × Exposure × Vulnerability) / Adaptive Capacity
        # Implemented as weighted combination to avoid zero-product issues
        
        risk_components = (
            self.component_weights['hazard'] * metrics.hazard_score +
            self.component_weights['exposure'] * metrics.exposure_score +
            self.component_weights['vulnerability'] * metrics.vulnerability_score
        )
        
        # Adaptive capacity reduces risk
        adaptive_factor = 1.0 - (self.component_weights['adaptive_capacity'] * metrics.adaptive_capacity_score)
        
        overall_risk = risk_components * adaptive_factor
        return min(1.0, max(0.0, overall_risk))
    
    def _calculate_adaptability_score(self, metrics: ClimateRiskMetrics) -> float:
        """Calculate adaptability score (inverse of vulnerability + adaptive capacity)"""
        # Higher adaptive capacity and lower vulnerability = higher adaptability
        adaptability = (metrics.adaptive_capacity_score * 0.6 + 
                       (1.0 - metrics.vulnerability_score) * 0.4)
        return min(1.0, adaptability)
    
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
