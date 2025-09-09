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
        if not self.data:
            return 0.0
            
        try:
            pop_data = self.get_population_data(city)
            if not pop_data:
                return 0.0
                
            density = pop_data.density_per_km2
            if density and density > 0:
                # Normalize population density (typical urban range: 1000-20000 people/km²)
                return self.normalize_score(density, min_val=1000.0, max_val=20000.0)
            
            return 0.0
            
        except Exception:
            return 0.0
            
    def _calculate_built_up_area(self, city: str) -> float:
        """Calculate built-up area exposure score"""
        if not self.data:
            return 0.0
            
        try:
            lulc_data = self.get_lulc_data(city)
            if lulc_data:
                # Try to extract built-up percentage from LULC data
                areas = lulc_data.get('areas_m2', {})
                if areas:
                    # Get latest year's data
                    years = sorted([y for y in areas.keys() if y.isdigit()])
                    if years:
                        latest_year = years[-1]
                        year_data = areas[latest_year]
                        built_pct = year_data.get('Built_Area', {}).get('percentage', 0)
                        if built_pct > 0:
                            return self.normalize_score(built_pct, min_val=0.0, max_val=100.0)
            
            # Fallback: Estimate based on population density
            pop_data = self.get_population_data(city)
            if pop_data and pop_data.density_per_km2:
                density = pop_data.density_per_km2
                # Higher density cities typically have more built-up area
                # Rough estimate: 1000 people/km² ≈ 20% built-up, 10000 people/km² ≈ 80% built-up
                estimated_built_pct = min(80.0, max(10.0, (density / 1000) * 20))
                return self.normalize_score(estimated_built_pct, min_val=0.0, max_val=100.0)
            
            return 0.0
            
        except Exception:
            return 0.0
            
    def _calculate_vegetation_accessibility(self, city: str) -> float:
        """Calculate vegetation accessibility score (inverse of exposure)"""
        if not self.data:
            return 0.0
            
        try:
            veg_data = self.get_vegetation_data(city)
            if veg_data:
                accessibility = veg_data.get('accessibility_score', 0.0)
                # Higher accessibility = lower exposure, so invert the score
                return 1.0 - accessibility
            
            # Fallback: Estimate based on city size and type
            pop_data = self.get_population_data(city)
            if pop_data:
                population = pop_data.population_2024
                if population:
                    # Larger cities typically have lower vegetation accessibility
                    # Small cities (<200k): high accessibility (low exposure)
                    # Large cities (>1M): low accessibility (high exposure)
                    if population < 200000:
                        accessibility_est = 0.8
                    elif population < 500000:
                        accessibility_est = 0.6
                    elif population < 1000000:
                        accessibility_est = 0.4
                    else:
                        accessibility_est = 0.2
                    
                    # Return inverse for exposure
                    return 1.0 - accessibility_est
            
            return 0.5  # Default moderate exposure
            
        except Exception:
            return 0.0
            
    def _calculate_air_quality_exposure(self, city: str) -> float:
        """Calculate air quality exposure score"""
        if not self.data:
            return 0.0
            
        try:
            air_data = self.get_air_quality_data(city)
            if air_data and 'pm2_5_avg' in air_data:
                pm25 = air_data['pm2_5_avg']
                # Normalize PM2.5 levels (WHO guideline: 5, typical urban range: 5-100 µg/m³)
                return self.normalize_score(pm25, min_val=5.0, max_val=100.0)
            
            # Fallback: Estimate based on population density and industrial activity
            pop_data = self.get_population_data(city)
            if pop_data:
                density = pop_data.density_per_km2
                if density and density > 0:
                    # Higher density typically correlates with worse air quality
                    # Additional factors for specific cities known for industry
                    base_exposure = self.normalize_score(density, min_val=1000.0, max_val=15000.0)
                    
                    # Adjust for known industrial cities
                    industrial_cities = {
                        'Navoiy': 1.3,    # Mining and processing
                        'Tashkent': 1.2,  # Capital with heavy traffic
                        'Nukus': 1.1,    # Aral Sea environmental issues
                        'Termez': 1.1,   # Border trade and activity
                    }
                    
                    multiplier = industrial_cities.get(city, 1.0)
                    return min(1.0, base_exposure * multiplier)
            
            return 0.3  # Default moderate exposure
            
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
