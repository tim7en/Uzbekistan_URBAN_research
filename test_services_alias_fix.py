#!/usr/bin/env python3
"""
Test to verify that services_adaptive_capacity alias bug is fixed
"""

import json
import numpy as np
from scipy.stats import pearsonr

def load_assessment_results():
    """Load the climate risk assessment results"""
    try:
        with open('climate_risk_assessment_results.json', 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print("ERROR: climate_risk_assessment_results.json not found")
        return None

def test_services_alias_fix():
    """Test if the services adaptive capacity alias bug is fixed"""
    
    print("Testing Services Adaptive Capacity Alias Fix")
    print("=" * 60)
    
    # Load existing results to compare
    data = load_assessment_results()
    if not data:
        print("Cannot test - no existing results file found")
        return
    
    # Extract old services_adaptive_capacity and viirs_exposure values
    cities = list(data['city_assessments'].keys())
    old_services = []
    viirs_exposure = []
    
    for city in cities:
        assessment = data['city_assessments'][city]
        old_services.append(assessment['adaptive_capacity']['services_adaptive_capacity'])
        viirs_exposure.append(assessment['exposure']['viirs_exposure'])
    
    # Calculate correlation
    if len(old_services) > 2:
        correlation, p_value = pearsonr(old_services, viirs_exposure)
        print(f"Old services_adaptive_capacity vs viirs_exposure correlation: {correlation:.6f}")
        print(f"P-value: {p_value:.6f}")
        
        if abs(correlation) > 0.99:
            print("❌ ALIAS BUG STILL EXISTS - Perfect correlation detected!")
        else:
            print("✅ Good - No perfect correlation detected")
    
    print("\nOld Services Adaptive Capacity values:")
    for city, val in zip(cities, old_services):
        print(f"  {city:12}: {val:.3f}")
    
    print("\nVIIRS Exposure values (for comparison):")
    for city, val in zip(cities, viirs_exposure):
        print(f"  {city:12}: {val:.3f}")
    
    # Now run new assessment to check fix
    print("\n" + "=" * 60)
    print("Running NEW assessment to verify fix...")
    
    try:
        from services.climate_data_loader import ClimateDataLoader
        from services.climate_risk_assessment import IPCCRiskAssessmentService
        
        # Initialize services
        data_loader = ClimateDataLoader()
        assessment_service = IPCCRiskAssessmentService(data_loader)
        
        # Test with one city first
        test_city = "Tashkent"
        print(f"\nTesting new services_adaptive_capacity calculation for {test_city}:")
        
        # Load data
        data_loader.load_all_data()
        
        # Calculate new services adaptive capacity
        new_services_value = assessment_service._calculate_services_adaptive_capacity(test_city)
        old_services_value = [val for city, val in zip(cities, old_services) if city == test_city][0]
        
        print(f"Old services_adaptive_capacity: {old_services_value:.6f}")
        print(f"New services_adaptive_capacity: {new_services_value:.6f}")
        print(f"Change: {new_services_value - old_services_value:+.6f}")
        
        if abs(new_services_value - old_services_value) > 0.001:
            print("✅ SUCCESS - Services adaptive capacity calculation has changed!")
        else:
            print("❌ WARNING - Values are very similar, fix may not be working")
            
    except Exception as e:
        print(f"❌ ERROR running new assessment: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_services_alias_fix()
