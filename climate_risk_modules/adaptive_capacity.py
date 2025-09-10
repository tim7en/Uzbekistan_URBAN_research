"""
Adaptive Capacity Assessment Module

Assesses adaptive capacity components including green infrastructure,
institutional capacity, economic capacity, and social capacity.
"""

import numpy as np
from typing import Dict, Optional
import sys
import os

# Handle imports for both standalone and module usage
if __name__ == "__main__":
    # Add parent directory to path for standalone execution
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base import BaseRiskModule, DEFAULT_WEIGHTS
else:
    from .base import BaseRiskModule, DEFAULT_WEIGHTS


class AdaptiveCapacityAssessment(BaseRiskModule):
    """Adaptive capacity assessment module"""
    
    def __init__(self, data_loader=None):
        super().__init__(data_loader)
        self.weights = DEFAULT_WEIGHTS['adaptive_capacity']
        
    def calculate(self, city: str, **kwargs) -> Dict[str, float]:
        """
        Calculate adaptive capacity metrics for the given city
        
        Args:
            city: City name
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of adaptive capacity metrics
        """
        cache_key = f"adaptive_capacity_{city}"
        cached_result = self.get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result
            
        results = {
            'green_infrastructure': self._calculate_green_infrastructure(city),
            'institutional_capacity': self._calculate_institutional_capacity(city),
            'economic_capacity': self._calculate_economic_capacity(city),
            'social_capacity': self._calculate_social_capacity(city)
        }
        
        # Calculate overall adaptive capacity score
        results['adaptive_capacity_score'] = self.weighted_average(
            {k: v for k, v in results.items() if k != 'adaptive_capacity_score'},
            self.weights
        )
        
        self.set_cached_result(cache_key, results)
        return results
        
    def _calculate_green_infrastructure(self, city: str) -> float:
        """Calculate green infrastructure adaptive capacity"""
        if not self.data:
            return 0.0
            
        try:
            # Vegetation accessibility from available data
            veg_data = self.get_vegetation_data(city)
            veg_capacity = 0.0
            
            if veg_data:
                # Use overall accessibility score if available
                accessibility = veg_data.get('accessibility_score', 0)
                if accessibility > 0:
                    veg_capacity = self.normalize_score(accessibility, min_val=0.0, max_val=1.0)
                else:
                    # Calculate from population and vegetation distance
                    pop_with_veg = veg_data.get('population_with_vegetation', 0)
                    total_pop = veg_data.get('total_population', 1)
                    if total_pop > 0:
                        veg_capacity = pop_with_veg / total_pop
            
            # Green space coverage from LULC
            lulc_data = self.get_lulc_data(city)
            green_coverage = 0.0
            
            if lulc_data:
                years_data = lulc_data.get('years', {})
                if years_data:
                    # Get latest year's vegetation data
                    latest_year = max(years_data.keys())
                    year_data = years_data[latest_year]
                    veg_percentage = year_data.get('vegetation_percentage', 0)
                    if veg_percentage > 0:
                        green_coverage = self.normalize_score(veg_percentage, min_val=0.0, max_val=50.0)
            
            # If no specific vegetation data, estimate from city characteristics
            if veg_capacity == 0.0 and green_coverage == 0.0:
                pop_data = self.get_population_data(city)
                if pop_data and pop_data.population_2024:
                    population = pop_data.population_2024
                    # Smaller cities typically have more green space access
                    if population < 200000:  # Small city
                        veg_capacity = 0.6
                        green_coverage = 0.7
                    elif population < 500000:  # Medium city
                        veg_capacity = 0.4
                        green_coverage = 0.5
                    elif population < 1000000:  # Large city
                        veg_capacity = 0.3
                        green_coverage = 0.3
                    else:  # Major city
                        veg_capacity = 0.2
                        green_coverage = 0.2
            
            # Weighted green infrastructure capacity
            green_capacity = (
                0.6 * veg_capacity +
                0.4 * green_coverage
            )
            
            return min(1.0, green_capacity)
            
            return min(1.0, green_capacity)
            
        except Exception:
            return 0.0
            
    def _calculate_institutional_capacity(self, city: str) -> float:
        """Calculate institutional adaptive capacity"""
        if not self.data_loader:
            return 0.0
            
        try:
            # Economic resources as proxy for institutional capacity
            population_data = self.data_loader.get_population_data(city)
            if not population_data:
                return 0.0
                
            gdp_per_capita = getattr(population_data, 'gdp_per_capita_usd', 0)
            population = getattr(population_data, 'population_2024', 0)
            
            # Economic capacity component
            economic_component = 0.0
            if gdp_per_capita > 0:
                # Higher GDP = better institutional capacity
                economic_component = self.normalize_score(gdp_per_capita, min_val=500.0, max_val=4000.0)
            
            # City size component (larger cities often have better institutions)
            size_component = 0.0
            if population > 0:
                # Normalize population (small: 50k, large: 3M)
                size_component = self.normalize_score(population, min_val=50000.0, max_val=3000000.0)
            
            # Data availability as proxy for institutional capacity
            data_availability = 0.0
            available_datasets = 0
            total_datasets = 5  # temperature, air quality, spatial, lulc, social
            
            if self.data_loader.get_temperature_data(city):
                available_datasets += 1
            if self.data_loader.get_air_quality_data(city):
                available_datasets += 1
            if self.data_loader.get_spatial_data(city):
                available_datasets += 1
            if self.data_loader.get_lulc_data(city):
                available_datasets += 1
            if self._load_social_sector_data(city):
                available_datasets += 1
                
            data_availability = available_datasets / total_datasets
            
            # Weighted institutional capacity
            institutional_capacity = (
                0.5 * economic_component +
                0.3 * size_component +
                0.2 * data_availability
            )
            
            return min(1.0, institutional_capacity)
            
        except Exception:
            return 0.0
            
    def _calculate_economic_capacity(self, city: str) -> float:
        """Calculate economic adaptive capacity"""
        if not self.data:
            return 0.0
            
        try:
            pop_data = self.get_population_data(city)
            if not pop_data:
                return 0.0
                
            gdp_per_capita = pop_data.gdp_per_capita_usd
            population = pop_data.population_2024
            
            if not gdp_per_capita or not population or gdp_per_capita <= 0 or population <= 0:
                return 0.0
            
            # GDP per capita capacity
            per_capita_capacity = self.normalize_score(gdp_per_capita, min_val=500.0, max_val=4000.0)
            
            # Total economic capacity (GDP per capita × population)
            total_gdp = gdp_per_capita * population
            total_capacity = self.normalize_score(total_gdp, min_val=50000000.0, max_val=10000000000.0)
            
            # Economic diversity proxy (nightlight activity)
            nightlight_data = self.get_nightlight_data(city)
            activity_capacity = 0.0
            
            if nightlight_data:
                years_data = nightlight_data.get('years', {})
                if years_data:
                    # Get latest year's radiance data
                    latest_year = max(years_data.keys())
                    year_data = years_data[latest_year]
                    radiance = year_data.get('total_radiance', 0)
                    if radiance > 0:
                        activity_capacity = self.normalize_score(radiance, min_val=100.0, max_val=50000.0)
            
            # If no nightlight data, estimate from city characteristics
            if activity_capacity == 0.0:
                # Estimate economic activity from city size and type
                if population > 1000000:  # Major city
                    activity_capacity = 0.8
                elif population > 500000:  # Large city
                    activity_capacity = 0.6
                elif population > 200000:  # Medium city
                    activity_capacity = 0.4
                else:  # Small city
                    activity_capacity = 0.2
            
            # Weighted economic capacity
            economic_capacity = (
                0.5 * per_capita_capacity +
                0.3 * total_capacity +
                0.2 * activity_capacity
            )
            
            return min(1.0, economic_capacity)
            
        except Exception:
            return 0.0
            
    def _load_social_sector_data(self, city: str) -> Optional[Dict]:
        """Load social sector data for detailed analysis"""
        try:
            # Currently no social sector data available
            return None
        except Exception:
            return None
            
    def _calculate_social_capacity(self, city: str) -> float:
        """Calculate social adaptive capacity"""
        if not self.data:
            return 0.0
            
        try:
            # Education infrastructure capacity (currently not available)
            education_capacity = 0.0
            social_data = self._load_social_sector_data(city)
            
            if social_data:
                per_capita = social_data.get('per_capita_metrics', {})
                schools_per_1000 = per_capita.get('schools_per_1000')
                kindergartens_per_1000 = per_capita.get('kindergartens_per_1000')
                
                if schools_per_1000 is not None and kindergartens_per_1000 is not None:
                    education_access = (schools_per_1000 + kindergartens_per_1000) / 2
                    education_capacity = min(1.0, education_access)
            
            # Healthcare infrastructure capacity (currently not available)
            healthcare_capacity = 0.0
            if social_data:
                per_capita = social_data.get('per_capita_metrics', {})
                hospitals_per_1000 = per_capita.get('hospitals_per_1000')
                
                if hospitals_per_1000 is not None:
                    healthcare_capacity = min(1.0, hospitals_per_1000 * 2)
            
            # Population density (moderate density indicates good social connectivity)
            connectivity_capacity = 0.0
            pop_data = self.get_population_data(city)
            
            if pop_data and pop_data.population_2024:
                # Use area and population to estimate density
                population = pop_data.population_2024
                
                # For cities without explicit density, estimate from population size
                if population > 1000000:  # Major city - high but manageable density
                    connectivity_capacity = 0.8
                elif population > 500000:  # Large city - good connectivity
                    connectivity_capacity = 0.9
                elif population > 200000:  # Medium city - optimal connectivity
                    connectivity_capacity = 1.0
                else:  # Small city - lower connectivity but manageable
                    connectivity_capacity = 0.7
            
            # Economic foundation for social capacity
            economic_foundation = 0.0
            if pop_data and pop_data.gdp_per_capita_usd:
                gdp_per_capita = pop_data.gdp_per_capita_usd
                if gdp_per_capita > 0:
                    economic_foundation = self.normalize_score(gdp_per_capita, min_val=500.0, max_val=3000.0)
            
            # If no specific social data available, use population-based estimates
            if education_capacity == 0.0 and healthcare_capacity == 0.0:
                if pop_data and pop_data.population_2024:
                    population = pop_data.population_2024
                    # Larger cities typically have better social infrastructure
                    if population > 1000000:  # Major city
                        education_capacity = 0.8
                        healthcare_capacity = 0.7
                    elif population > 500000:  # Large city
                        education_capacity = 0.7
                        healthcare_capacity = 0.6
                    elif population > 200000:  # Medium city
                        education_capacity = 0.6
                        healthcare_capacity = 0.5
                    else:  # Small city
                        education_capacity = 0.4
                        healthcare_capacity = 0.4
            
            # Weighted social capacity
            social_capacity = (
                0.3 * education_capacity +
                0.3 * healthcare_capacity +
                0.2 * connectivity_capacity +
                0.2 * economic_foundation
            )
            
            return min(1.0, social_capacity)
            
        except Exception:
            return 0.0


def run_adaptive_capacity_assessment(city: str, data_loader=None) -> Dict[str, float]:
    """
    Standalone function to run adaptive capacity assessment for a city
    
    Args:
        city: City name
        data_loader: Optional data loader instance
        
    Returns:
        Dictionary of adaptive capacity assessment results
    """
    assessment = AdaptiveCapacityAssessment(data_loader)
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
        
        # Initialize data loader with correct base path
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "individual_results")
        loader = ClimateDataLoader(base_path)
        
        # Run assessment
        results = run_adaptive_capacity_assessment(city_name, loader)
        
        print(f"\nAdaptive Capacity Assessment Results for {city_name}:")
        print("=" * 50)
        for metric, value in results.items():
            print(f"{metric.replace('_', ' ').title()}: {value:.4f}")
    else:
        print("Usage: python adaptive_capacity.py <city_name>")
        print("Example: python adaptive_capacity.py Tashkent")
