#!/usr/bin/env python3
"""
Quick check of the saved JSON to see what components are actually calculated.
"""

import json
import os

def main():
    print("="*50)
    print("ANALYZING SAVED ASSESSMENT RESULTS")
    print("="*50)
    
    # Load the results
    results_path = "suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json"
    
    if not os.path.exists(results_path):
        print(f"ERROR: Results file not found at {results_path}")
        return
    
    with open(results_path, 'r') as f:
        results = json.load(f)
    
    # Check a sample city to see all available components
    sample_city = list(results.keys())[0]
    sample_data = results[sample_city]
    
    print(f"\nSample city: {sample_city}")
    print(f"Available fields: {list(sample_data.keys())}")
    
    print(f"\nDetailed component breakdown for {sample_city}:")
    for key, value in sample_data.items():
        if isinstance(value, (int, float)):
            print(f"  {key}: {value:.6f}")
        else:
            print(f"  {key}: {value}")
    
    # Check if pluvial hazard calculation is producing variation
    print(f"\nPLUVIAL HAZARD DEBUG:")
    print("Cities with built_area data:")
    for city, data in results.items():
        print(f"  {city}: pluvial_hazard={data.get('pluvial_hazard', 'missing'):.4f}")
    
    # Check overall aggregation
    print(f"\nAGGREGATION CHECK:")
    for city, data in results.items():
        h = data.get('hazard_score', 0)
        e = data.get('exposure_score', 0) 
        v = data.get('vulnerability_score', 0)
        ac = data.get('adaptive_capacity_score', 0)
        
        print(f"{city}:")
        print(f"  H={h:.4f}, E={e:.4f}, V={v:.4f}, AC={ac:.4f}")
        print(f"  H×E×V = {h*e*v:.6f}")
        print(f"  (1-AC) = {1-ac:.4f}")
        print(f"  H×E×V×(1-AC) = {h*e*v*(1-ac):.6f}")
        
        if h == 0 or e == 0 or v == 0:
            print(f"  ❌ ZERO COMPONENT DETECTED!")
        if ac == 1.0:
            print(f"  ❌ ADAPTIVE CAPACITY = 1.0 (Risk reduction = 100%)")
        print()

if __name__ == "__main__":
    main()
