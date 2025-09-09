"""
Exposure Assessment Module

Assesses exposure to climate hazards including population density,
built-up area, vegetation accessibility, and air quality exposure.
"""

import numpy as np
from typing import Dict, Optional
from .base import BaseRiskModule, DEFAULT_WEIGHTS


class ExposureAssessment(BaseRiskModule):
    """Exposure assessment module"""
    
    def __init__(self, data_loader=None):
        super().__init__(data_loader)
        self.weights = DEFAULT_WEIGHTS['exposure']
        
    def calculate(self, city: str, **kwargs) -> Dict[str, float]:
        """
        Calculate exposure metrics for the given city
        
        Args:
            city: City name
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of exposure metrics
        """
        cache_key = f"exposure_{city}"
        cached_result = self.get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result
            
        results = {
            'population_density': self._calculate_population_density(city),
            'built_up_area': self._calculate_built_up_area(city),
            'vegetation_accessibility': self._calculate_vegetation_accessibility(city),
            'air_quality_exposure': self._calculate_air_quality_exposure(city)
        }
        
        # Calculate overall exposure score
        results['exposure_score'] = self.weighted_average(
            {k: v for k, v in results.items() if k != 'exposure_score'},
            self.weights
        )
        
        self.set_cached_result(cache_key, results)
        return results
        
    def _calculate_population_density(self, city: str) -> float:
        """Calculate population density exposure score"""
        if not self.data_loader:
            return 0.0
            
        try:
            spatial_data = self.data_loader.get_spatial_data(city)
            if not spatial_data or 'population_density' not in spatial_data:
                return 0.0
                
            pop_density = spatial_data['population_density']
            # Normalize population density (typical urban range: 1000-20000 people/km²)
            return self.normalize_score(pop_density, min_val=1000.0, max_val=20000.0)
            
        except Exception:
            return 0.0
            
    def _calculate_built_up_area(self, city: str) -> float:
        """Calculate built-up area exposure score"""
        if not self.data_loader:
            return 0.0
            
        try:
            lulc_data = self.data_loader.get_lulc_data(city)
            if not lulc_data or 'built_up_percentage' not in lulc_data:
                return 0.0
                
            built_up_pct = lulc_data['built_up_percentage']
            # Normalize built-up percentage (0-100%)
            return self.normalize_score(built_up_pct, min_val=0.0, max_val=100.0)
            
        except Exception:
            return 0.0
            
    def _calculate_vegetation_accessibility(self, city: str) -> float:
        """Calculate vegetation accessibility score (inverse of exposure)"""
        if not self.data_loader:
            return 0.0
            
        try:
            veg_data = self.data_loader.get_vegetation_data(city)
            if not veg_data or 'accessibility_score' not in veg_data:
                return 0.0
                
            accessibility = veg_data['accessibility_score']
            # Higher accessibility = lower exposure, so invert the score
            return 1.0 - self.normalize_score(accessibility, min_val=0.0, max_val=1.0)
            
        except Exception:
            return 0.0
            
    def _calculate_air_quality_exposure(self, city: str) -> float:
        """Calculate air quality exposure score"""
        if not self.data_loader:
            return 0.0
            
        try:
            air_data = self.data_loader.get_air_quality_data(city)
            if not air_data or 'pm2_5_avg' not in air_data:
                return 0.0
                
            pm25 = air_data['pm2_5_avg']
            # Normalize PM2.5 levels (WHO guideline: 5, typical urban range: 5-100 µg/m³)
            return self.normalize_score(pm25, min_val=5.0, max_val=100.0)
            
        except Exception:
            return 0.0


def run_exposure_assessment(city: str, data_loader=None) -> Dict[str, float]:
    """
    Standalone function to run exposure assessment for a city
    
    Args:
        city: City name
        data_loader: Optional data loader instance
        
    Returns:
        Dictionary of exposure assessment results
    """
    assessment = ExposureAssessment(data_loader)
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
        results = run_exposure_assessment(city_name, loader)
        
        print(f"\nExposure Assessment Results for {city_name}:")
        print("=" * 50)
        for metric, value in results.items():
            print(f"{metric.replace('_', ' ').title()}: {value:.4f}")
    else:
        print("Usage: python exposure.py <city_name>")
        print("Example: python exposure.py Tashkent")
