"""
Risk Calculator Module

Integrates all climate risk assessment components using IPCC AR6 framework
to calculate overall climate risk scores.
"""

import numpy as np
from typing import Dict, Optional
from .base import BaseRiskModule, ClimateRiskMetrics
from .hazards import HazardAssessment
from .exposure import ExposureAssessment
from .vulnerability import VulnerabilityAssessment
from .adaptive_capacity import AdaptiveCapacityAssessment


class RiskCalculator(BaseRiskModule):
    """Main risk calculator that integrates all assessment components"""
    
    def __init__(self, data_loader=None):
        super().__init__(data_loader)
        
        # Initialize component assessments
        self.hazard_assessment = HazardAssessment(data_loader)
        self.exposure_assessment = ExposureAssessment(data_loader)
        self.vulnerability_assessment = VulnerabilityAssessment(data_loader)
        self.adaptive_capacity_assessment = AdaptiveCapacityAssessment(data_loader)
        
        # IPCC AR6 overall weights for risk calculation
        self.risk_weights = {
            'hazard': 0.35,
            'exposure': 0.30,
            'vulnerability': 0.35
        }
        
    def calculate(self, city: str, **kwargs) -> ClimateRiskMetrics:
        """
        Calculate comprehensive climate risk metrics for the given city
        
        Args:
            city: City name
            **kwargs: Additional parameters
            
        Returns:
            ClimateRiskMetrics object with all calculated scores
        """
        cache_key = f"full_risk_{city}"
        cached_result = self.get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result
            
        # Initialize metrics
        metrics = ClimateRiskMetrics()
        
        # Calculate component assessments
        hazard_results = self.hazard_assessment.calculate(city, **kwargs)
        exposure_results = self.exposure_assessment.calculate(city, **kwargs)
        vulnerability_results = self.vulnerability_assessment.calculate(city, **kwargs)
        adaptive_capacity_results = self.adaptive_capacity_assessment.calculate(city, **kwargs)
        
        # Populate individual component scores
        self._populate_hazard_metrics(metrics, hazard_results)
        self._populate_exposure_metrics(metrics, exposure_results)
        self._populate_vulnerability_metrics(metrics, vulnerability_results)
        self._populate_adaptive_capacity_metrics(metrics, adaptive_capacity_results)
        
        # Calculate composite scores
        metrics.hazard_score = hazard_results['hazard_score']
        metrics.exposure_score = exposure_results['exposure_score']
        metrics.vulnerability_score = vulnerability_results['vulnerability_score']
        metrics.adaptive_capacity_score = adaptive_capacity_results['adaptive_capacity_score']
        
        # Calculate overall risk using IPCC AR6 framework
        metrics.risk_score = self._calculate_overall_risk(metrics)
        
        self.set_cached_result(cache_key, metrics)
        return metrics
        
    def _populate_hazard_metrics(self, metrics: ClimateRiskMetrics, hazard_results: Dict[str, float]):
        """Populate hazard component metrics"""
        metrics.temperature_anomaly = hazard_results.get('temperature_anomaly', 0.0)
        metrics.heat_island_intensity = hazard_results.get('heat_island_intensity', 0.0)
        metrics.temperature_trend = hazard_results.get('temperature_trend', 0.0)
        metrics.extreme_heat_days = hazard_results.get('extreme_heat_days', 0.0)
        
    def _populate_exposure_metrics(self, metrics: ClimateRiskMetrics, exposure_results: Dict[str, float]):
        """Populate exposure component metrics"""
        metrics.population_density = exposure_results.get('population_density', 0.0)
        metrics.built_up_area = exposure_results.get('built_up_area', 0.0)
        metrics.vegetation_accessibility = exposure_results.get('vegetation_accessibility', 0.0)
        metrics.air_quality_exposure = exposure_results.get('air_quality_exposure', 0.0)
        
    def _populate_vulnerability_metrics(self, metrics: ClimateRiskMetrics, vulnerability_results: Dict[str, float]):
        """Populate vulnerability component metrics"""
        metrics.social_vulnerability = vulnerability_results.get('social_vulnerability', 0.0)
        metrics.infrastructure_vulnerability = vulnerability_results.get('infrastructure_vulnerability', 0.0)
        metrics.health_vulnerability = vulnerability_results.get('health_vulnerability', 0.0)
        metrics.economic_vulnerability = vulnerability_results.get('economic_vulnerability', 0.0)
        
    def _populate_adaptive_capacity_metrics(self, metrics: ClimateRiskMetrics, adaptive_capacity_results: Dict[str, float]):
        """Populate adaptive capacity component metrics"""
        metrics.green_infrastructure = adaptive_capacity_results.get('green_infrastructure', 0.0)
        metrics.institutional_capacity = adaptive_capacity_results.get('institutional_capacity', 0.0)
        metrics.economic_capacity = adaptive_capacity_results.get('economic_capacity', 0.0)
        metrics.social_capacity = adaptive_capacity_results.get('social_capacity', 0.0)
        
    def _calculate_overall_risk(self, metrics: ClimateRiskMetrics) -> float:
        """
        Calculate overall risk using IPCC AR6 framework
        
        Risk = f(Hazard, Exposure, Vulnerability, Adaptive Capacity)
        
        Standard approach: Risk = (H × E × V) × (1 - AC)
        Where AC reduces the base risk (H × E × V)
        """
        # Base risk from hazard, exposure, and vulnerability
        base_risk = (
            self.risk_weights['hazard'] * metrics.hazard_score +
            self.risk_weights['exposure'] * metrics.exposure_score +
            self.risk_weights['vulnerability'] * metrics.vulnerability_score
        )
        
        # Alternative multiplicative approach for comparison
        multiplicative_risk = (
            metrics.hazard_score * 
            metrics.exposure_score * 
            metrics.vulnerability_score
        )
        
        # Use weighted approach as primary, multiplicative as secondary
        if base_risk > 0 and multiplicative_risk > 0:
            # Blend both approaches
            combined_risk = 0.7 * base_risk + 0.3 * multiplicative_risk
        else:
            # Fallback to weighted approach when multiplicative gives zero
            combined_risk = base_risk
        
        # Apply adaptive capacity reduction
        # Higher adaptive capacity reduces risk
        risk_reduction_factor = 1.0 - (metrics.adaptive_capacity_score * 0.8)  # Max 80% reduction
        
        final_risk = combined_risk * risk_reduction_factor
        
        return min(1.0, max(0.0, final_risk))
        
    def calculate_priority_score(self, metrics: ClimateRiskMetrics) -> float:
        """
        Calculate intervention priority score
        
        Priority = Risk^α × (1 - Adaptive_Capacity)^β
        Where α emphasizes high-risk areas and β emphasizes low adaptive capacity
        """
        α = 0.8  # Risk emphasis factor
        β = 0.6  # Adaptive capacity emphasis factor
        
        risk_component = metrics.risk_score ** α
        capacity_gap = (1.0 - metrics.adaptive_capacity_score) ** β
        
        priority = risk_component * capacity_gap
        
        return min(1.0, max(0.0, priority))
        
    def generate_risk_summary(self, city: str) -> Dict[str, any]:
        """
        Generate comprehensive risk assessment summary
        
        Args:
            city: City name
            
        Returns:
            Dictionary with risk assessment summary
        """
        metrics = self.calculate(city)
        priority_score = self.calculate_priority_score(metrics)
        
        # Risk level categorization
        if metrics.risk_score >= 0.75:
            risk_level = "Very High"
        elif metrics.risk_score >= 0.5:
            risk_level = "High"
        elif metrics.risk_score >= 0.25:
            risk_level = "Medium"
        else:
            risk_level = "Low"
        
        # Adaptive capacity level
        if metrics.adaptive_capacity_score >= 0.75:
            capacity_level = "High"
        elif metrics.adaptive_capacity_score >= 0.5:
            capacity_level = "Medium"
        else:
            capacity_level = "Low"
        
        # Priority level
        if priority_score >= 0.75:
            priority_level = "Very High"
        elif priority_score >= 0.5:
            priority_level = "High"
        elif priority_score >= 0.25:
            priority_level = "Medium"
        else:
            priority_level = "Low"
        
        return {
            'city': city,
            'risk_score': metrics.risk_score,
            'risk_level': risk_level,
            'priority_score': priority_score,
            'priority_level': priority_level,
            'components': {
                'hazard_score': metrics.hazard_score,
                'exposure_score': metrics.exposure_score,
                'vulnerability_score': metrics.vulnerability_score,
                'adaptive_capacity_score': metrics.adaptive_capacity_score,
                'adaptive_capacity_level': capacity_level
            },
            'detailed_metrics': metrics
        }


def run_full_risk_assessment(city: str, data_loader=None) -> Dict[str, any]:
    """
    Standalone function to run full climate risk assessment for a city
    
    Args:
        city: City name
        data_loader: Optional data loader instance
        
    Returns:
        Dictionary with comprehensive risk assessment results
    """
    calculator = RiskCalculator(data_loader)
    return calculator.generate_risk_summary(city)


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
        
        # Run full assessment
        results = run_full_risk_assessment(city_name, loader)
        
        print(f"\nClimate Risk Assessment Summary for {city_name}")
        print("=" * 60)
        print(f"Overall Risk Score: {results['risk_score']:.4f} ({results['risk_level']})")
        print(f"Priority Score: {results['priority_score']:.4f} ({results['priority_level']})")
        print()
        print("Component Scores:")
        print("-" * 30)
        components = results['components']
        print(f"Hazard Score: {components['hazard_score']:.4f}")
        print(f"Exposure Score: {components['exposure_score']:.4f}")
        print(f"Vulnerability Score: {components['vulnerability_score']:.4f}")
        print(f"Adaptive Capacity: {components['adaptive_capacity_score']:.4f} ({components['adaptive_capacity_level']})")
        
        # Show individual component details if requested
        if len(sys.argv) > 2 and sys.argv[2] == "--detailed":
            print("\nDetailed Component Breakdown:")
            print("-" * 40)
            metrics = results['detailed_metrics']
            
            print("Hazard Components:")
            print(f"  Temperature Anomaly: {metrics.temperature_anomaly:.4f}")
            print(f"  Heat Island Intensity: {metrics.heat_island_intensity:.4f}")
            print(f"  Temperature Trend: {metrics.temperature_trend:.4f}")
            print(f"  Extreme Heat Days: {metrics.extreme_heat_days:.4f}")
            
            print("\nExposure Components:")
            print(f"  Population Density: {metrics.population_density:.4f}")
            print(f"  Built-up Area: {metrics.built_up_area:.4f}")
            print(f"  Vegetation Accessibility: {metrics.vegetation_accessibility:.4f}")
            print(f"  Air Quality Exposure: {metrics.air_quality_exposure:.4f}")
            
            print("\nVulnerability Components:")
            print(f"  Social Vulnerability: {metrics.social_vulnerability:.4f}")
            print(f"  Infrastructure Vulnerability: {metrics.infrastructure_vulnerability:.4f}")
            print(f"  Health Vulnerability: {metrics.health_vulnerability:.4f}")
            print(f"  Economic Vulnerability: {metrics.economic_vulnerability:.4f}")
            
            print("\nAdaptive Capacity Components:")
            print(f"  Green Infrastructure: {metrics.green_infrastructure:.4f}")
            print(f"  Institutional Capacity: {metrics.institutional_capacity:.4f}")
            print(f"  Economic Capacity: {metrics.economic_capacity:.4f}")
            print(f"  Social Capacity: {metrics.social_capacity:.4f}")
            
    else:
        print("Usage: python risk_calculator.py <city_name> [--detailed]")
        print("Example: python risk_calculator.py Tashkent")
        print("Example: python risk_calculator.py Tashkent --detailed")
