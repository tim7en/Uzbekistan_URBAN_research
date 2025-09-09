"""
Climate Risk Assessment Modules

This package contains modular components for IPCC AR6-based climate risk assessment.
Each module can be run independently and combined for comprehensive risk analysis.

Modules:
- base: Core data structures and base classes
- hazards: Climate hazard assessment components
- exposure: Exposure assessment components  
- vulnerability: Vulnerability assessment components
- adaptive_capacity: Adaptive capacity assessment components
- risk_calculator: Overall risk calculation and integration
- data_validator: Data validation and quality checks
"""

from .base import ClimateRiskMetrics, BaseRiskModule
from .hazards import HazardAssessment, run_hazard_assessment
from .exposure import ExposureAssessment, run_exposure_assessment
from .vulnerability import VulnerabilityAssessment, run_vulnerability_assessment
from .adaptive_capacity import AdaptiveCapacityAssessment, run_adaptive_capacity_assessment
from .risk_calculator import RiskCalculator, run_full_risk_assessment
from .data_validator import DataValidator, validate_city_data

__version__ = "1.0.0"
__all__ = [
    'ClimateRiskMetrics',
    'BaseRiskModule',
    'HazardAssessment',
    'ExposureAssessment', 
    'VulnerabilityAssessment',
    'AdaptiveCapacityAssessment',
    'RiskCalculator',
    'DataValidator',
    'run_hazard_assessment',
    'run_exposure_assessment',
    'run_vulnerability_assessment',
    'run_adaptive_capacity_assessment',
    'run_full_risk_assessment',
    'validate_city_data'
]
