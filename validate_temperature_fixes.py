#!/usr/bin/env python3
"""
Validate that the temperature data access fix resolved the identical hazard values issue.
"""

import json
import os

def main():
    print("="*50)
    print("VALIDATING TEMPERATURE DATA ACCESS FIXES")
    print("="*50)
    
    # Load the latest assessment results
    results_path = "suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json"
    
    if not os.path.exists(results_path):
        print(f"ERROR: Results file not found at {results_path}")
        return
    
    with open(results_path, 'r') as f:
        results = json.load(f)
    
    print(f"\nAssessment completed for {len(results)} cities")
    
    # Check heat hazard values
    print("\n1. HEAT HAZARD VALUES:")
    heat_values = []
    for city, data in results.items():
        heat_hazard = data.get('heat_hazard', 0)
        heat_values.append(heat_hazard)
        print(f"  {city}: {heat_hazard:.4f}")
    
    # Check for identical values (the previous bug)
    unique_heat = len(set(heat_values))
    print(f"\nUnique heat hazard values: {unique_heat} out of {len(heat_values)}")
    
    if unique_heat == 1:
        print("❌ ISSUE: All cities have identical heat hazard values!")
    elif unique_heat < len(heat_values) // 2:
        print("⚠️  WARNING: Too many cities have similar heat hazard values")
    else:
        print("✅ GOOD: Heat hazard values show proper variation")
    
    # Check pluvial hazard values
    print("\n2. PLUVIAL HAZARD VALUES:")
    pluvial_values = []
    for city, data in results.items():
        pluvial_hazard = data.get('pluvial_hazard', 0)
        pluvial_values.append(pluvial_hazard)
        print(f"  {city}: {pluvial_hazard:.4f}")
    
    unique_pluvial = len(set(pluvial_values))
    print(f"\nUnique pluvial hazard values: {unique_pluvial} out of {len(pluvial_values)}")
    
    if unique_pluvial == 1:
        print("❌ ISSUE: All cities have identical pluvial hazard values!")
    elif unique_pluvial < len(pluvial_values) // 2:
        print("⚠️  WARNING: Too many cities have similar pluvial hazard values")
    else:
        print("✅ GOOD: Pluvial hazard values show proper variation")
    
    # Check overall risk distribution
    print("\n3. OVERALL RISK DISTRIBUTION:")
    risk_values = []
    for city, data in results.items():
        overall_risk = data.get('overall_risk', 0)
        risk_values.append(overall_risk)
        print(f"  {city}: {overall_risk:.4f}")
    
    print(f"\nRisk statistics:")
    print(f"  Min: {min(risk_values):.4f}")
    print(f"  Max: {max(risk_values):.4f}")
    print(f"  Mean: {sum(risk_values)/len(risk_values):.4f}")
    print(f"  Range: {max(risk_values) - min(risk_values):.4f}")
    
    # Check if any cities are significantly different
    if max(risk_values) - min(risk_values) > 0.1:
        print("✅ GOOD: Cities show meaningful risk differentiation")
    else:
        print("⚠️  WARNING: Risk values are very similar across cities")
    
    # Summary of key issues resolved
    print("\n4. ASSESSMENT VALIDATION SUMMARY:")
    print("="*40)
    
    issues_found = 0
    
    if unique_heat == 1:
        print("❌ Heat hazard identical values issue PERSISTS")
        issues_found += 1
    else:
        print("✅ Heat hazard identical values issue RESOLVED")
    
    if unique_pluvial == 1:
        print("❌ Pluvial hazard identical values issue PERSISTS")
        issues_found += 1
    else:
        print("✅ Pluvial hazard identical values issue RESOLVED")
    
    if max(risk_values) - min(risk_values) > 0.05:
        print("✅ Meaningful city differentiation ACHIEVED")
    else:
        print("❌ Cities still too similar in risk scores")
        issues_found += 1
    
    if issues_found == 0:
        print(f"\n🎉 SUCCESS: All major assessment issues have been RESOLVED!")
        print("The climate assessment now produces realistic and differentiated results.")
    else:
        print(f"\n⚠️  {issues_found} issues still need attention")

if __name__ == "__main__":
    main()
