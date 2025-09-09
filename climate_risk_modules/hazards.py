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
        if not self.data_loader:
            return 0.0
            
        try:
            temp_data = self.data_loader.get_temperature_data(city)
            if not temp_data or 'anomaly' not in temp_data:
                return 0.0
                
            anomaly = temp_data['anomaly']
            # Normalize anomaly (typical range: -2 to +4°C)
            return self.normalize_score(anomaly, min_val=-2.0, max_val=4.0)
            
        except Exception:
            return 0.0
            
    def _calculate_heat_island_intensity(self, city: str) -> float:
        """Calculate urban heat island intensity score"""
        if not self.data_loader:
            return 0.0
            
        try:
            suhi_data = self.data_loader.get_suhi_data(city)
            if not suhi_data or 'intensity' not in suhi_data:
                return 0.0
                
            intensity = suhi_data['intensity']
            threshold = TEMPERATURE_THRESHOLDS['heat_island_threshold']
            
            # Score based on threshold exceedance
            if intensity >= threshold:
                # Normalize above threshold (range: 2-8°C)
                return self.normalize_score(intensity, min_val=threshold, max_val=8.0)
            else:
                # Below threshold gets partial score
                return self.normalize_score(intensity, min_val=0.0, max_val=threshold) * 0.5
                
        except Exception:
            return 0.0
            
    def _calculate_temperature_trend(self, city: str) -> float:
        """Calculate temperature trend score"""
        if not self.data_loader:
            return 0.0
            
        try:
            temp_stats = self.data_loader.get_temperature_stats(city)
            if not temp_stats or 'trend_per_year' not in temp_stats:
                return 0.0
                
            trend = temp_stats['trend_per_year']
            threshold = TEMPERATURE_THRESHOLDS['trend_significance']
            
            # Score based on positive warming trends
            if trend >= threshold:
                # Normalize warming trend (range: 0.1-0.5°C/year)
                return self.normalize_score(trend, min_val=threshold, max_val=0.5)
            else:
                return 0.0  # No warming or cooling gets 0 score
                
        except Exception:
            return 0.0
            
    def _calculate_extreme_heat_days(self, city: str) -> float:
        """Calculate extreme heat days score"""
        if not self.data_loader:
            return 0.0
            
        try:
            temp_stats = self.data_loader.get_temperature_stats(city)
            if not temp_stats or 'extreme_heat_days' not in temp_stats:
                return 0.0
                
            extreme_days = temp_stats['extreme_heat_days']
            # Normalize extreme heat days (range: 0-365 days)
            return self.normalize_score(extreme_days, min_val=0.0, max_val=100.0)
            
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
