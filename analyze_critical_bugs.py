#!/usr/bin/env python3
"""
Critical Bug Fixes for Climate Risk Assessment
Addresses data plumbing issues, scaling problems, and methodological flaws
"""

import json
import numpy as np
from scipy.stats import spearmanr
import pandas as pd

def analyze_current_bugs():
    """First, let's confirm the bugs identified"""
    
    with open('D:/Dev/Uzbekistan_URBAN_research/suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json', 'r') as f:
        data = json.load(f)
    
    print("🔍 CONFIRMING CRITICAL BUGS")
    print("=" * 50)
    
    # Bug 1: services_adaptive_capacity ≡ viirs_exposure alias
    services_vals = [data[city]['services_adaptive_capacity'] for city in data.keys()]
    viirs_vals = [data[city]['viirs_exposure'] for city in data.keys()]
    correlation = np.corrcoef(services_vals, viirs_vals)[0,1]
    
    print(f"1. ALIAS BUG:")
    print(f"   services_adaptive_capacity vs viirs_exposure correlation: {correlation:.6f}")
    print(f"   services range: {min(services_vals):.3f} - {max(services_vals):.3f}")
    print(f"   viirs range: {min(viirs_vals):.3f} - {max(viirs_vals):.3f}")
    if correlation > 0.99:
        print("   ❌ CONFIRMED: Perfect correlation - these are identical!")
    
    # Bug 2: water_system_capacity constant
    water_vals = [data[city]['water_system_capacity'] for city in data.keys()]
    unique_water = len(set(water_vals))
    print(f"\n2. CONSTANT BUG:")
    print(f"   water_system_capacity unique values: {unique_water}")
    print(f"   All values: {water_vals[0]:.3f}")
    if unique_water == 1:
        print("   ❌ CONFIRMED: All cities have identical water_system_capacity!")
    
    # Bug 3: Risk ignores adaptive capacity
    print(f"\n3. RISK FORMULA BUG:")
    for city in ['Tashkent', 'Navoiy', 'Nurafshon']:
        city_data = data[city]
        h = city_data['hazard_score']
        e = city_data['exposure_score'] 
        v = city_data['vulnerability_score']
        ac = city_data['adaptive_capacity_score']
        risk = city_data['overall_risk_score']
        
        hev_product = h * e * v
        print(f"   {city}: H×E×V = {hev_product:.3f}, Risk = {risk:.3f}, AC = {ac:.3f}")
        print(f"      Risk uses AC? {abs(risk - hev_product) > 0.01}")
    
    # Bug 4: Tashkent maxima pegging
    tashkent = data['Tashkent']
    maxima_count = sum(1 for key, val in tashkent.items() if isinstance(val, (int, float)) and val == 1.0)
    print(f"\n4. TASHKENT MAXIMA BUG:")
    print(f"   Components at exactly 1.000: {maxima_count}")
    maxima_components = [key for key, val in tashkent.items() if isinstance(val, (int, float)) and val == 1.0]
    print(f"   Components: {maxima_components[:5]}...")
    
    # Bug 5: GDP exposure vs population exposure inconsistency
    print(f"\n5. GDP EXPOSURE BUG:")
    navoiy = data['Navoiy']
    print(f"   Navoiy GDP exposure: {navoiy['gdp_exposure']:.3f}")
    print(f"   Navoiy population exposure: {navoiy['population_exposure']:.3f}")
    print(f"   Navoiy GDP per capita: ${navoiy['gdp_per_capita_usd']:,.0f}")
    print(f"   This suggests GDP exposure uses per capita, not total GDP at risk!")
    
    # Bug 6: Air quality contradiction
    print(f"\n6. AIR QUALITY CONTRADICTION:")
    aq_hazards = [data[city]['air_quality_hazard'] for city in data.keys()]
    aq_vulns = [data[city]['air_pollution_vulnerability'] for city in data.keys()]
    aq_correlation = np.corrcoef(aq_hazards, aq_vulns)[0,1]
    print(f"   Air quality hazard vs vulnerability correlation: {aq_correlation:.3f}")
    if aq_correlation < 0.3:
        print("   ❌ CONFIRMED: Air quality hazard and vulnerability are poorly correlated!")
    
    print(f"\n7. SMALL CITY BIAS:")
    small_cities = [(city, data[city]['population'], data[city]['exposure_score']) 
                    for city in data.keys() if data[city]['population'] < 100000]
    for city, pop, exp in small_cities:
        print(f"   {city}: pop {pop:,}, exposure {exp:.3f}")

if __name__ == "__main__":
    analyze_current_bugs()
