#!/usr/bin/env python3
"""
Test the critical fixes applied to the climate assessment.
Verify that the red flags have been resolved.
"""

import json
import numpy as np
import pandas as pd

def test_gdp_exposure_fix():
    """Test if GDP exposure now properly reflects total GDP at risk"""
    print("=" * 80)
    print("TESTING GDP EXPOSURE FIX")
    print("=" * 80)
    
    # Run assessment to get new results
    import subprocess
    result = subprocess.run(['python', 'run_climate_assessment_modular.py'], 
                          capture_output=True, text=True)
    
    if result.returncode != 0:
        print("❌ Assessment failed to run")
        print(result.stderr)
        return False
    
    # Load new results
    with open('suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json', 'r') as f:
        results = json.load(f)
    
    # Test Tashkent vs Navoiy ratio
    tashkent_data = results['Tashkent']
    navoiy_data = results['Navoiy']
    
    tashkent_total_gdp = tashkent_data['population'] * tashkent_data['gdp_per_capita_usd']
    navoiy_total_gdp = navoiy_data['population'] * navoiy_data['gdp_per_capita_usd']
    
    actual_gdp_ratio = navoiy_total_gdp / tashkent_total_gdp
    exposure_ratio = navoiy_data['gdp_exposure'] / tashkent_data['gdp_exposure']
    
    print(f"Tashkent Total GDP: ${tashkent_total_gdp/1e9:.2f}B")
    print(f"Navoiy Total GDP:   ${navoiy_total_gdp/1e9:.2f}B")
    print(f"Actual GDP ratio:   {actual_gdp_ratio:.1%}")
    print(f"Exposure ratio:     {exposure_ratio:.1%}")
    
    # Check if exposure ratio is more reasonable (within 2x of actual ratio)
    if abs(exposure_ratio / actual_gdp_ratio - 1) < 1.0:  # Within 100% error
        print("✅ GDP exposure ratio is now reasonable")
        return True
    else:
        print(f"❌ GDP exposure ratio still problematic (expected ~{actual_gdp_ratio:.1%}, got {exposure_ratio:.1%})")
        return False

def test_zero_exposure_fix():
    """Test if artificial zeros have been eliminated"""
    print("\n" + "=" * 80)
    print("TESTING ZERO EXPOSURE FIX")
    print("=" * 80)
    
    with open('suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json', 'r') as f:
        results = json.load(f)
    
    zero_cities = []
    for city_name, data in results.items():
        pop_exp = data['population_exposure']
        gdp_exp = data['gdp_exposure']
        
        if pop_exp <= 0.01 or gdp_exp <= 0.01:  # Allow small floor values
            zero_cities.append({
                'city': city_name,
                'pop_exposure': pop_exp,
                'gdp_exposure': gdp_exp,
                'population': data['population']
            })
    
    print(f"Cities with near-zero exposure (≤ 0.01):")
    for city_data in zero_cities:
        print(f"  {city_data['city']:12} | Pop: {city_data['population']:>8,} | "
              f"PopExp: {city_data['pop_exposure']:.3f} | GDPExp: {city_data['gdp_exposure']:.3f}")
    
    if len(zero_cities) == 0:
        print("✅ No cities have near-zero exposure")
        return True
    elif all(city['pop_exposure'] >= 0.05 and city['gdp_exposure'] >= 0.05 for city in zero_cities):
        print("✅ All exposure values are above safe floor (0.05)")
        return True
    else:
        print(f"❌ {len(zero_cities)} cities still have problematic exposure values")
        return False

def test_max_pegging_reduction():
    """Test if max-pegging has been reduced"""
    print("\n" + "=" * 80)
    print("TESTING MAX-PEGGING REDUCTION")
    print("=" * 80)
    
    with open('suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json', 'r') as f:
        results = json.load(f)
    
    max_pegged_components = {}
    
    for city_name, data in results.items():
        city_maxes = []
        
        # Check key components for exact 1.000 values
        components_to_check = [
            'population_exposure', 'gdp_exposure', 'viirs_exposure',
            'heat_hazard', 'pluvial_hazard', 'air_quality_hazard',
            'gdp_adaptive_capacity', 'services_adaptive_capacity'
        ]
        
        for component in components_to_check:
            if component in data and data[component] >= 0.99:  # Allow some floating point tolerance
                city_maxes.append(component)
        
        if city_maxes:
            max_pegged_components[city_name] = city_maxes
    
    print("Cities with components ≥ 0.99 (max-pegged):")
    total_max_components = 0
    for city, components in max_pegged_components.items():
        print(f"  {city:12} | {len(components):2} components: {', '.join(components[:3])}")
        if len(components) > 3:
            print(f"                ... and {len(components)-3} more")
        total_max_components += len(components)
    
    if total_max_components <= 5:  # Allow some maxima but not excessive
        print(f"✅ Max-pegging reduced to {total_max_components} components across all cities")
        return True
    else:
        print(f"❌ Still {total_max_components} max-pegged components across all cities")
        return False

def test_missing_data_handling():
    """Test if missing data artifacts have been fixed"""
    print("\n" + "=" * 80)
    print("TESTING MISSING DATA HANDLING")
    print("=" * 80)
    
    with open('suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json', 'r') as f:
        results = json.load(f)
    
    # Check for specific problematic values
    problematic_values = []
    
    # Nukus bio trend vulnerability should not be 0.000
    nukus_bio = results['Nukus'].get('bio_trend_vulnerability', None)
    if nukus_bio is not None and nukus_bio <= 0.01:
        problematic_values.append(f"Nukus bio_trend_vulnerability = {nukus_bio:.3f}")
    
    # Check for zero adaptive capacity
    zero_adaptive_cities = []
    for city_name, data in results.items():
        gdp_adaptive = data.get('gdp_adaptive_capacity', None)
        if gdp_adaptive is not None and gdp_adaptive <= 0.01:
            zero_adaptive_cities.append(city_name)
    
    if zero_adaptive_cities:
        problematic_values.append(f"Cities with gdp_adaptive_capacity ≤ 0.01: {', '.join(zero_adaptive_cities)}")
    
    if not problematic_values:
        print("✅ No missing data artifacts detected")
        return True
    else:
        print("❌ Missing data artifacts still present:")
        for issue in problematic_values:
            print(f"  - {issue}")
        return False

def main():
    """Run comprehensive test of critical fixes"""
    print("TESTING CRITICAL RED FLAG FIXES")
    print("Verifying that all major issues have been resolved")
    print("=" * 80)
    
    tests = [
        ("GDP Exposure Fix", test_gdp_exposure_fix),
        ("Zero Exposure Fix", test_zero_exposure_fix),
        ("Max-Pegging Reduction", test_max_pegging_reduction),
        ("Missing Data Handling", test_missing_data_handling)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("CRITICAL FIX TEST SUMMARY")
    print("=" * 80)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} | {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(tests)} tests passed ({passed/len(tests)*100:.1f}%)")
    
    if passed == len(tests):
        print("🎉 ALL CRITICAL FIXES SUCCESSFUL!")
    elif passed >= len(tests) * 0.75:
        print("⚠️  Most fixes successful, minor issues remain")
    else:
        print("❌ Significant issues still present")

if __name__ == "__main__":
    main()
