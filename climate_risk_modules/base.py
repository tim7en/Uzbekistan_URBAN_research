"""
Base module for climate risk assessment

Contains core data structures and base classes used across all risk assessment modules.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import numpy as np


@dataclass
class ClimateRiskMetrics:
    """Core data structure for storing climate risk assessment metrics"""
    
    # Hazard components
    temperature_anomaly: float = 0.0
    heat_island_intensity: float = 0.0
    temperature_trend: float = 0.0
    extreme_heat_days: float = 0.0
    
    # Exposure components  
    population_density: float = 0.0
    built_up_area: float = 0.0
    vegetation_accessibility: float = 0.0
    air_quality_exposure: float = 0.0
    
    # Vulnerability components
    social_vulnerability: float = 0.0
    infrastructure_vulnerability: float = 0.0
    health_vulnerability: float = 0.0
    economic_vulnerability: float = 0.0
    
    # Adaptive capacity components
    green_infrastructure: float = 0.0
    institutional_capacity: float = 0.0
    economic_capacity: float = 0.0
    social_capacity: float = 0.0
    
    # Aggregated scores
    hazard_score: float = 0.0
    exposure_score: float = 0.0
    vulnerability_score: float = 0.0
    adaptive_capacity_score: float = 0.0
    risk_score: float = 0.0


class BaseRiskModule(ABC):
    """Abstract base class for all risk assessment modules"""
    
    def __init__(self, data_loader=None):
        self.data_loader = data_loader
        self.cache = {}
        
        # Load all data if data_loader is provided
        if self.data_loader:
            self.data = self.data_loader.load_all_data()
        else:
            self.data = {}
        
    @abstractmethod
    def calculate(self, city: str, **kwargs) -> Dict[str, float]:
        """
        Calculate component metrics for the given city
        
        Args:
            city: City name
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of calculated metrics
        """
        pass
    
    def clear_cache(self):
        """Clear the module cache"""
        self.cache.clear()
        
    def get_cached_result(self, key: str) -> Optional[Any]:
        """Get cached result by key"""
        return self.cache.get(key)
        
    def set_cached_result(self, key: str, value: Any):
        """Set cached result"""
        self.cache[key] = value
        
    def get_population_data(self, city: str):
        """Get population data for city"""
        return self.data.get('population_data', {}).get(city)
        
    def get_temperature_data(self, city: str):
        """Get temperature data for city"""
        return self.data.get('temperature_data', {}).get(city)
        
    def get_suhi_data(self, city: str):
        """Get SUHI data for city"""
        return self.data.get('suhi_data', {}).get(city)
        
    def get_lulc_data(self, city: str):
        """Get LULC data for city"""
        lulc_list = self.data.get('lulc_data', [])
        for lulc_item in lulc_list:
            if lulc_item.get('city') == city:
                return lulc_item
        return None
        
    def get_spatial_data(self, city: str):
        """Get spatial data for city"""
        spatial_data = self.data.get('spatial_data', {})
        return spatial_data.get('per_year', {}).get(city)
        
    def get_air_quality_data(self, city: str):
        """Get air quality data for city"""
        return self.data.get('air_quality_data', {}).get(city)
        
    def get_nightlight_data(self, city: str):
        """Get nightlight data for city"""
        nightlight_list = self.data.get('nightlights_data', [])
        for nl_item in nightlight_list:
            if nl_item.get('city') == city:
                return nl_item
        return None
        
    def get_vegetation_data(self, city: str):
        """Get vegetation data for city"""
        spatial_data = self.get_spatial_data(city)
        if spatial_data:
            # Get latest year's vegetation accessibility data
            years = sorted([int(y) for y in spatial_data.keys()])
            if years:
                latest_year = str(years[-1])
                year_data = spatial_data[latest_year]
                veg_accessibility = year_data.get('vegetation_accessibility', {})
                city_veg = veg_accessibility.get('city', {})
                
                if city_veg:
                    mean_distance = city_veg.get('mean', 1000)  # meters
                    # Convert to accessibility score (closer = better)
                    max_distance = 1000  # 1km threshold
                    accessibility_score = max(0.0, 1.0 - (mean_distance / max_distance))
                    return {'accessibility_score': accessibility_score}
        return None
        
    def validate_data_availability(self, city: str, required_data: list) -> bool:
        """
        Validate that required data is available for the city
        
        Args:
            city: City name
            required_data: List of required data types
            
        Returns:
            True if all required data is available
        """
        if not self.data:
            return False
            
        for data_type in required_data:
            if data_type == 'population_data':
                if not self.get_population_data(city):
                    return False
            elif data_type == 'temperature_data':
                if not self.get_temperature_data(city):
                    return False
            elif data_type == 'lulc_data':
                if not self.get_lulc_data(city):
                    return False
            elif data_type == 'spatial_data':
                if not self.get_spatial_data(city):
                    return False
            # Add other data type checks as needed
                
        return True
        
    @staticmethod
    def normalize_score(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """
        Normalize a score to 0-1 range
        
        Args:
            value: Value to normalize
            min_val: Minimum expected value
            max_val: Maximum expected value
            
        Returns:
            Normalized value between 0 and 1
        """
        if max_val <= min_val:
            return 0.0
            
        normalized = (value - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, normalized))
        
    @staticmethod
    def weighted_average(values: Dict[str, float], weights: Dict[str, float]) -> float:
        """
        Calculate weighted average of values
        
        Args:
            values: Dictionary of values
            weights: Dictionary of weights (should sum to 1.0)
            
        Returns:
            Weighted average
        """
        if not values or not weights:
            return 0.0
            
        total = 0.0
        total_weight = 0.0
        
        for key, value in values.items():
            if key in weights:
                weight = weights[key]
                total += value * weight
                total_weight += weight
                
        return total / total_weight if total_weight > 0 else 0.0


# Configuration constants
DEFAULT_WEIGHTS = {
    'hazard': {
        'temperature_anomaly': 0.3,
        'heat_island_intensity': 0.3,
        'temperature_trend': 0.2,
        'extreme_heat_days': 0.2
    },
    'exposure': {
        'population_density': 0.4,
        'built_up_area': 0.3,
        'vegetation_accessibility': 0.2,
        'air_quality_exposure': 0.1
    },
    'vulnerability': {
        'social_vulnerability': 0.3,
        'infrastructure_vulnerability': 0.25,
        'health_vulnerability': 0.25,
        'economic_vulnerability': 0.2
    },
    'adaptive_capacity': {
        'green_infrastructure': 0.4,
        'institutional_capacity': 0.25,
        'economic_capacity': 0.2,
        'social_capacity': 0.15
    }
}

# Temperature thresholds (city-specific, no regional adjustments)
TEMPERATURE_THRESHOLDS = {
    'extreme_heat_celsius': 35.0,  # Days above this temperature
    'heat_island_threshold': 2.0,  # Significant UHI intensity
    'trend_significance': 0.1      # Minimum temperature trend per year
}
