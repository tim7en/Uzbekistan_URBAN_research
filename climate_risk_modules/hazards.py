"""
Climate Hazards Assessment Module

Assesses climate hazards including temperature anomalies, heat island effects,
temperature trends, and extreme heat events.
"""

import numpy as np
from typing import Dict, Optional
from .base import BaseRiskModule, DEFAULT_WEIGHTS, TEMPERATURE_THRESHOLDS


class HazardAssessment(BaseRiskModule):
    """Climate hazard assessment module"""
    
    def __init__(self, data_loader=None):
        super().__init__(data_loader)
        self.weights = DEFAULT_WEIGHTS['hazard']
        
    def calculate(self, city: str, **kwargs) -> Dict[str, float]:
        """
        Calculate hazard metrics for the given city
        
        Args:
            city: City name
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of hazard metrics
        """
        cache_key = f"hazard_{city}"
        cached_result = self.get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result
            
        results = {
            'temperature_anomaly': self._calculate_temperature_anomaly(city),
            'heat_island_intensity': self._calculate_heat_island_intensity(city),
            'temperature_trend': self._calculate_temperature_trend(city),
            'extreme_heat_days': self._calculate_extreme_heat_days(city)
        }
        
        # Calculate overall hazard score
        results['hazard_score'] = self.weighted_average(
            {k: v for k, v in results.items() if k != 'hazard_score'},
            self.weights
        )
        
        self.set_cached_result(cache_key, results)
        return results
        
    def _calculate_temperature_anomaly(self, city: str) -> float:
        """Calculate temperature anomaly score"""
        if not self.data:
            return 0.0
            
        try:
            temp_data = self.get_temperature_data(city)
            if not temp_data:
                return 0.0
                
            # For now, use basic temperature analysis from population data
            # This will be enhanced when actual temperature data is available
            pop_data = self.get_population_data(city)
            if not pop_data:
                return 0.0
                
            # Use latitude as proxy for temperature anomaly risk
            # Cities in southern Uzbekistan (lower latitude) are generally hotter
            # This is a placeholder until real temperature data is available
            city_coords = {
                'Termez': 37.2, 'Qarshi': 38.9, 'Bukhara': 39.8, 'Nukus': 42.5,
                'Tashkent': 41.3, 'Samarkand': 39.7, 'Navoiy': 40.1, 'Jizzakh': 40.1,
                'Fergana': 40.4, 'Namangan': 41.0, 'Andijan': 40.8, 'Gulistan': 40.5,
                'Urgench': 41.6, 'Nurafshon': 41.2
            }
            
            latitude = city_coords.get(city, 40.0)  # Default to central Uzbekistan
            # Lower latitude = higher temperature risk
            # Normalize: Termez (37.2) = 1.0, Nukus (42.5) = 0.0
            anomaly_score = max(0.0, (42.5 - latitude) / (42.5 - 37.2))
            return min(1.0, anomaly_score)
            
        except Exception:
            return 0.0
            
    def _calculate_heat_island_intensity(self, city: str) -> float:
        """Calculate urban heat island intensity score"""
        if not self.data:
            return 0.0
            
        try:
            suhi_data = self.get_suhi_data(city)
            if suhi_data:
                # Use real SUHI data when available
                intensity = suhi_data.get('intensity', 0.0)
                threshold = TEMPERATURE_THRESHOLDS['heat_island_threshold']
                
                if intensity >= threshold:
                    return self.normalize_score(intensity, min_val=threshold, max_val=8.0)
                else:
                    return self.normalize_score(intensity, min_val=0.0, max_val=threshold) * 0.5
            
            # Fallback: Use population density as proxy for heat island effect
            pop_data = self.get_population_data(city)
            if not pop_data:
                return 0.0
                
            density = pop_data.density_per_km2
            if density > 0:
                # Higher density typically correlates with stronger heat island
                # Normalize density: 1000 people/km² = 0.2, 10000+ people/km² = 1.0
                heat_island_proxy = min(1.0, max(0.1, (density - 1000) / 9000))
                return heat_island_proxy
                
            return 0.0
            
        except Exception:
            return 0.0
            
    def _calculate_temperature_trend(self, city: str) -> float:
        """Calculate temperature trend score"""
        if not self.data:
            return 0.0
            
        try:
            temp_stats = self.get_temperature_data(city)
            if temp_stats and 'trend_per_year' in temp_stats:
                trend = temp_stats['trend_per_year']
                threshold = TEMPERATURE_THRESHOLDS['trend_significance']
                
                if trend >= threshold:
                    return self.normalize_score(trend, min_val=threshold, max_val=0.5)
                else:
                    return 0.0
            
            # Fallback: Use global warming trend estimate for Central Asia
            # IPCC estimates suggest warming of 0.2-0.3°C per decade in Central Asia
            global_trend = 0.025  # 0.25°C per decade = 0.025°C per year
            return self.normalize_score(global_trend, min_val=0.0, max_val=0.05)
            
        except Exception:
            return 0.0
            
    def _calculate_extreme_heat_days(self, city: str) -> float:
        """Calculate extreme heat days score"""
        if not self.data:
            return 0.0
            
        try:
            temp_stats = self.get_temperature_data(city)
            if temp_stats and 'extreme_heat_days' in temp_stats:
                extreme_days = temp_stats['extreme_heat_days']
                return self.normalize_score(extreme_days, min_val=0.0, max_val=100.0)
            
            # Fallback: Estimate based on city location and climate knowledge
            # Southern cities typically have more extreme heat days
            city_heat_estimates = {
                'Termez': 45,    # Hottest city, near Afghan border
                'Qarshi': 35,    # Central south, very hot summers
                'Bukhara': 30,   # Central, hot and dry
                'Nukus': 25,     # Northern, but continental climate
                'Tashkent': 20,  # Capital, moderate
                'Samarkand': 28, # Central, historically hot
                'Navoiy': 32,    # Desert location
                'Jizzakh': 22,   # Central, moderate
                'Fergana': 18,   # Valley, more temperate
                'Namangan': 15,  # Northern valley
                'Andijan': 16,   # Eastern valley
                'Gulistan': 25,  # Steppe region
                'Urgench': 28,   # Western, continental
                'Nurafshon': 18  # Near Tashkent
            }
            
            estimated_days = city_heat_estimates.get(city, 20)  # Default estimate
            return self.normalize_score(estimated_days, min_val=0.0, max_val=50.0)
            
        except Exception:
            return 0.0


def run_hazard_assessment(city: str, data_loader=None) -> Dict[str, float]:
    """
    Standalone function to run hazard assessment for a city
    
    Args:
        city: City name
        data_loader: Optional data loader instance
        
    Returns:
        Dictionary of hazard assessment results
    """
    assessment = HazardAssessment(data_loader)
    return assessment.calculate(city)


if __name__ == "__main__":
    import sys
    import os
    
    # Add parent directory to path to import data loader
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from services.climate_data_loader import ClimateDataLoader
    
    # Example usage
    if len(sys.argv) > 1:
        city_name = sys.argv[1]
        
        # Initialize data loader
        loader = ClimateDataLoader()
        
        # Run assessment
        results = run_hazard_assessment(city_name, loader)
        
        print(f"\nHazard Assessment Results for {city_name}:")
        print("=" * 50)
        for metric, value in results.items():
            print(f"{metric.replace('_', ' ').title()}: {value:.4f}")
    else:
        print("Usage: python hazards.py <city_name>")
        print("Example: python hazards.py Tashkent")
