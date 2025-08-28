#!/usr/bin/env python3
"""
Test script for integrated water scarcity and climate risk assessment
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService

def test_integrated_assessment():
    """Test the integrated water scarcity and climate risk assessment"""
    print("Testing integrated water scarcity and climate risk assessment...")

    # Initialize data loader and assessment service
    base_path = os.path.dirname(os.path.abspath(__file__))
    data_loader = ClimateDataLoader(base_path)
    assessment_service = IPCCRiskAssessmentService(data_loader)

    # Test cities
    test_cities = ['Tashkent', 'Urgench', 'Nurafshon', 'Samarkand']

    print(f"\n{'City':<12} {'Water Scarcity':<15} {'Climate Risk':<12} {'Overall Risk':<12} {'Hazard':<8} {'Exposure':<9} {'Adaptive':<9}")
    print("-" * 85)

    for city in test_cities:
        try:
            # Get integrated assessment
            metrics = assessment_service.assess_city_climate_risk(city)

            # Get water scarcity data
            water_data = assessment_service.water_scarcity_data.get(city, {})

            water_scarcity = water_data.get('water_scarcity_index', 0.0) if water_data else 0.0

            print(f"{city:<12} {water_scarcity:.3f}          {metrics.vulnerability_score:.3f}      {metrics.overall_risk_score:.3f}     {metrics.hazard_score:.3f}  {metrics.exposure_score:.3f}  {metrics.adaptive_capacity_score:.3f}")

        except Exception as e:
            print(f"{city:<12} Error: {str(e)}")

    print("\nIntegration test completed!")

if __name__ == "__main__":
    test_integrated_assessment()
