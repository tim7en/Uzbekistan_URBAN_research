#!/usr/bin/env python3
"""
Run assessment with fixed services adaptive capacity and verify the alias bug is resolved
"""

import json
import numpy as np
from scipy.stats import pearsonr
from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService

def run_and_test_fixed_assessment():
    """Run assessment with fix and test for alias bug resolution"""
    
    print("Running Climate Risk Assessment with Services Adaptive Capacity Fix")
    print("=" * 70)
    
    try:
        # Initialize services
        base_path = "D:\\Dev\\Uzbekistan_URBAN_research"
        data_loader = ClimateDataLoader(base_path)
        assessment_service = IPCCRiskAssessmentService(data_loader)
        
        # Get city list from assessment service data
        cities = list(assessment_service.data['population_data'].keys())
        print(f"Cities to assess: {', '.join(cities)}")
        
        # Run assessment for each city
        services_adaptive_capacity = []
        viirs_exposure = []
        
        print("\nRunning assessments...")
        for city in cities:
            print(f"  Assessing {city}...")
            
            # Calculate components
            services_ac = assessment_service._calculate_services_adaptive_capacity(city)
            viirs_exp = assessment_service._calculate_viirs_exposure(city)
            
            services_adaptive_capacity.append(services_ac)
            viirs_exposure.append(viirs_exp)
            
            print(f"    Services AC: {services_ac:.6f}, VIIRS Exposure: {viirs_exp:.6f}")
        
        # Test for alias bug
        print("\n" + "=" * 70)
        print("ALIAS BUG TEST")
        print("=" * 70)
        
        if len(services_adaptive_capacity) > 2:
            correlation, p_value = pearsonr(services_adaptive_capacity, viirs_exposure)
            print(f"Services Adaptive Capacity vs VIIRS Exposure correlation: {correlation:.6f}")
            print(f"P-value: {p_value:.6f}")
            
            if abs(correlation) > 0.99:
                print("❌ ALIAS BUG STILL EXISTS - Perfect correlation detected!")
            elif abs(correlation) > 0.8:
                print("⚠️  WARNING - High correlation detected, potential remaining issue")
            else:
                print("✅ SUCCESS - Alias bug appears to be fixed!")
        
        # Show detailed comparison
        print("\nDetailed Results:")
        print(f"{'City':<12} {'Services AC':<12} {'VIIRS Exp':<12} {'Difference':<12}")
        print("-" * 50)
        
        for city, sac, vexp in zip(cities, services_adaptive_capacity, viirs_exposure):
            diff = abs(sac - vexp)
            print(f"{city:<12} {sac:<12.6f} {vexp:<12.6f} {diff:<12.6f}")
        
        # Summary statistics
        print(f"\nSummary Statistics:")
        print(f"Services AC - Mean: {np.mean(services_adaptive_capacity):.6f}, Std: {np.std(services_adaptive_capacity):.6f}")
        print(f"VIIRS Exp   - Mean: {np.mean(viirs_exposure):.6f}, Std: {np.std(viirs_exposure):.6f}")
        print(f"Correlation: {correlation:.6f}")
        
        # Test individual components
        print(f"\n" + "=" * 70)
        print("COMPONENT BREAKDOWN FOR TASHKENT")
        print("=" * 70)
        
        if "Tashkent" in cities:
            print("Testing services adaptive capacity calculation components...")
            
            # Get Tashkent data
            pop_data = assessment_service.data['population_data'].get('Tashkent')
            social_data = assessment_service.data.get('social_sector_data', {}).get('Tashkent', {})
            
            print(f"Population: {pop_data.population_2024 if pop_data else 'N/A'}")
            print(f"Density: {pop_data.density_per_km2 if pop_data else 'N/A'} people/km²")
            print(f"Urban area: {pop_data.urban_area_km2 if pop_data else 'N/A'} km²")
            print(f"GDP per capita: ${pop_data.gdp_per_capita_usd if pop_data else 'N/A'}")
            
            healthcare_vuln = social_data.get('healthcare_access_vulnerability', 0.5)
            education_vuln = social_data.get('education_access_vulnerability', 0.5)
            
            print(f"Healthcare vulnerability: {healthcare_vuln}")
            print(f"Education vulnerability: {education_vuln}")
            print(f"Healthcare capacity: {1.0 - healthcare_vuln}")
            print(f"Education capacity: {1.0 - education_vuln}")
            
            if pop_data:
                density = pop_data.density_per_km2 if pop_data.density_per_km2 else 0
                print(f"Population density: {density:.2f} people/km²")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    run_and_test_fixed_assessment()
