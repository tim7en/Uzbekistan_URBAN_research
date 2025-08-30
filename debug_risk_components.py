#!/usr/bin/env python3
"""
Debug script to check component values in the assessment and identify why overall_risk is 0.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))

from climate_risk_assessment import IPCCRiskAssessmentService
from climate_data_loader import ClimateDataLoader
import json

def debug_component_values():
    print("="*50)
    print("DEBUGGING RISK COMPONENT VALUES")
    print("="*50)
    
    # Initialize the assessment service
    base_path = "suhi_analysis_output"
    data_loader = ClimateDataLoader(base_path)
    data_loader.load_all_data()
    
    assessment_service = IPCCRiskAssessmentService(data_loader)
    
    # Test on a few cities to see component breakdown
    test_cities = ['Tashkent', 'Nukus', 'Navoiy']
    
    for city in test_cities:
        print(f"\n{'='*40}")
        print(f"DEBUGGING COMPONENTS FOR {city.upper()}")
        print(f"{'='*40}")
        
        try:
            # Run assessment for this city
            metrics = assessment_service.assess_city_climate_risk(city)
            
            print(f"\nHAZARD COMPONENTS:")
            print(f"  Heat Hazard: {metrics.heat_hazard:.4f}")
            print(f"  Pluvial Hazard: {metrics.pluvial_hazard:.4f}")
            print(f"  Dry Hazard: {metrics.dry_hazard:.4f}")
            print(f"  Dust Hazard: {metrics.dust_hazard:.4f}")
            print(f"  AGGREGATE Hazard Score: {metrics.hazard_score:.4f}")
            
            print(f"\nEXPOSURE COMPONENTS:")
            print(f"  VIIRS Exposure: {metrics.viirs_exposure:.4f}")
            print(f"  Population Exposure: {metrics.population_exposure:.4f}")
            print(f"  GDP Exposure: {metrics.gdp_exposure:.4f}")
            print(f"  AGGREGATE Exposure Score: {metrics.exposure_score:.4f}")
            
            print(f"\nVULNERABILITY COMPONENTS:")
            print(f"  Bio Trend Vulnerability: {metrics.bio_trend_vulnerability:.4f}")
            print(f"  Fragmentation Vulnerability: {metrics.fragmentation_vulnerability:.4f}")
            print(f"  Income Vulnerability: {metrics.income_vulnerability:.4f}")
            print(f"  Air Pollution Vulnerability: {metrics.air_pollution_vulnerability:.4f}")
            print(f"  AGGREGATE Vulnerability Score: {metrics.vulnerability_score:.4f}")
            
            print(f"\nADAPTIVE CAPACITY COMPONENTS:")
            print(f"  Economic Capacity: {metrics.economic_capacity:.4f}")
            print(f"  AGGREGATE Adaptive Capacity: {metrics.adaptive_capacity_score:.4f}")
            
            print(f"\nRISK CALCULATION:")
            print(f"  H × E × V = {metrics.hazard_score:.4f} × {metrics.exposure_score:.4f} × {metrics.vulnerability_score:.4f} = {metrics.hazard_score * metrics.exposure_score * metrics.vulnerability_score:.6f}")
            print(f"  (1 - AC) = (1 - {metrics.adaptive_capacity_score:.4f}) = {1 - metrics.adaptive_capacity_score:.4f}")
            print(f"  Risk = H×E×V×(1-AC) = {(metrics.hazard_score * metrics.exposure_score * metrics.vulnerability_score * (1 - metrics.adaptive_capacity_score)):.6f}")
            print(f"  FINAL Overall Risk Score: {metrics.overall_risk_score:.6f}")
            
            # Check for zero components
            zero_components = []
            if metrics.hazard_score == 0.0:
                zero_components.append("Hazard")
            if metrics.exposure_score == 0.0:
                zero_components.append("Exposure")
            if metrics.vulnerability_score == 0.0:
                zero_components.append("Vulnerability")
            if metrics.adaptive_capacity_score == 1.0:
                zero_components.append("Adaptive Capacity (AC=1.0 means 1-AC=0)")
            
            if zero_components:
                print(f"\n❌ ZERO COMPONENTS FOUND: {', '.join(zero_components)}")
                print("This explains why overall risk = 0!")
            else:
                print(f"\n✅ No zero components found")
                
        except Exception as e:
            print(f"ERROR assessing {city}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_component_values()
