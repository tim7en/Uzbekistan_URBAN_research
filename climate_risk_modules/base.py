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
        
    def validate_data_availability(self, city: str, required_data: list) -> bool:
        """
        Validate that required data is available for the city
        
        Args:
            city: City name
            required_data: List of required data types
            
        Returns:
            True if all required data is available
        """
        if not self.data_loader:
            return False
            
        for data_type in required_data:
            if not hasattr(self.data_loader, f'get_{data_type}'):
                return False
                
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
