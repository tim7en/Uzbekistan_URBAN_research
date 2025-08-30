#!/usr/bin/env python3
"""
Focused test to investigate why Nurafshan has exposure score of 0.
"""

import json
import os
from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService

def investigate_nurafshan_exposure():
    """Investigate why Nurafshan has exposure score of 0"""
    
    print("="*80)
    print("INVESTIGATING NURAFSHAN EXPOSURE SCORE = 0")
    print("="*80)
    
    city = "Nurafshon"
    
    # Initialize services
    loader = ClimateDataLoader("suhi_analysis_output")
    service = IPCCRiskAssessmentService(loader)
    
    print("\n1. CHECKING POPULATION DATA:")
    print("-" * 40)
    population_data = service.data['population_data'].get(city)
    if population_data:
        print(f"✅ Population data found:")
        print(f"   Population: {population_data.population_2024:,}")
        print(f"   GDP per capita: ${population_data.gdp_per_capita_usd:,}")
        print(f"   Density: {population_data.density_per_km2:.1f} people/km²")
    else:
        print(f"❌ No population data found for {city}")
        
    print("\n2. CHECKING DATA CACHE:")
    print("-" * 40)
    if 'cache' in service.data:
        cache = service.data['cache']
        print(f"✅ Cache exists with keys: {list(cache.keys())}")
        if 'population' in cache:
            print(f"   Population cache has {len(cache['population'])} values")
            print(f"   Population range: {min(cache['population']):.0f} - {max(cache['population']):.0f}")
        if 'density' in cache:
            print(f"   Density cache has {len(cache['density'])} values")
            print(f"   Density range: {min(cache['density']):.1f} - {max(cache['density']):.1f}")
    else:
        print("❌ No cache found - this would cause exposure score = 0")
        
    print("\n3. CHECKING LULC DATA:")
    print("-" * 40)
    lulc_found = False
    for lulc_city in service.data['lulc_data']:
        if lulc_city.get('city') == city:
            lulc_found = True
            areas = lulc_city.get('areas_m2', {})
            print(f"✅ LULC data found for {city}")
            print(f"   Years available: {list(areas.keys())}")
            if areas:
                latest_year = max(areas.keys(), key=lambda x: int(x))
                built_pct = areas[latest_year].get('Built_Area', {}).get('percentage', 0)
                print(f"   Built area % ({latest_year}): {built_pct}%")
            break
    if not lulc_found:
        print(f"❌ No LULC data found for {city}")
        
    print("\n4. CHECKING NIGHTLIGHTS DATA:")
    print("-" * 40)
    nl_found = False
    for nl_city in service.data['nightlights_data']:
        if nl_city.get('city') == city:
            nl_found = True
            years_data = nl_city.get('years', {})
            print(f"✅ Nightlights data found for {city}")
            print(f"   Years available: {list(years_data.keys())}")
            if years_data:
                latest_year = max(years_data.keys(), key=lambda x: int(x))
                urban_nl = years_data[latest_year].get('stats', {}).get('urban_core', {}).get('mean', 0)
                print(f"   Urban nightlight intensity ({latest_year}): {urban_nl}")
            break
    if not nl_found:
        print(f"❌ No nightlights data found for {city}")
        
    print("\n5. RUNNING EXPOSURE CALCULATION:")
    print("-" * 40)
    try:
        exposure_score = service.calculate_exposure_score(city)
        print(f"🎯 Exposure Score: {exposure_score:.3f}")
        
        # Manual calculation to debug
        if population_data and 'cache' in service.data:
            cache = service.data['cache']
            
            print("\n🧮 MANUAL EXPOSURE BREAKDOWN:")
            
            # Population score
            if 'population' in cache:
                pop_score = loader.pct_norm(cache['population'], population_data.population_2024)
                print(f"   Population score: {pop_score:.3f}")
            else:
                pop_score = 0
                print(f"   Population score: 0 (no cache)")
            
            # Density score
            if 'density' in cache:
                density_score = loader.pct_norm(cache['density'], population_data.density_per_km2)
                print(f"   Density score: {density_score:.3f}")
            else:
                density_score = 0
                print(f"   Density score: 0 (no cache)")
            
            # Built score
            built_score = 0
            for lulc_city in service.data['lulc_data']:
                if lulc_city.get('city') == city:
                    areas = lulc_city.get('areas_m2', {})
                    if areas:
                        years = sorted([int(y) for y in areas.keys()])
                        if years:
                            latest_year = str(years[-1])
                            built_pct = areas[latest_year].get('Built_Area', {}).get('percentage', 0)
                            if 'built_pct' in cache:
                                built_score = loader.pct_norm(cache['built_pct'], built_pct)
                            print(f"   Built score: {built_score:.3f} (built_pct: {built_pct}%)")
                    break
            if built_score == 0:
                print(f"   Built score: 0 (no data or cache)")
            
            # Nightlight score
            nightlight_score = 0
            for nl_city in service.data['nightlights_data']:
                if nl_city.get('city') == city:
                    years_data = nl_city.get('years', {})
                    if years_data:
                        years = sorted([int(y) for y in years_data.keys()])
                        if years:
                            latest_year = str(years[-1])
                            urban_nl = years_data[latest_year].get('stats', {}).get('urban_core', {}).get('mean', 0)
                            if 'nightlights' in cache:
                                nightlight_score = loader.pct_norm(cache['nightlights'], urban_nl)
                            print(f"   Nightlight score: {nightlight_score:.3f} (intensity: {urban_nl})")
                    break
            if nightlight_score == 0:
                print(f"   Nightlight score: 0 (no data or cache)")
            
            # Weighted calculation
            manual_exposure = (0.4 * pop_score + 0.25 * density_score + 
                             0.2 * built_score + 0.15 * nightlight_score)
            print(f"\n   Manual calculation: 0.4×{pop_score:.3f} + 0.25×{density_score:.3f} + 0.2×{built_score:.3f} + 0.15×{nightlight_score:.3f}")
            print(f"   = {manual_exposure:.3f}")
            print(f"   Final (min(1.0, value)): {min(1.0, manual_exposure):.3f}")
            
    except Exception as e:
        print(f"❌ Error calculating exposure: {e}")
        
    print("\n6. CHECKING PERCENTILE NORMALIZATION CACHE:")
    print("-" * 40)
    if 'cache' in service.data:
        cache = service.data['cache']
        for key in ['population', 'density', 'built_pct', 'nightlights']:
            if key in cache:
                values = cache[key]
                print(f"✅ {key}: {len(values)} values, range: {min(values):.2f} - {max(values):.2f}")
                if population_data:
                    if key == 'population':
                        val = population_data.population_2024
                    elif key == 'density':
                        val = population_data.density_per_km2
                    else:
                        continue
                    pct = loader.pct_norm(values, val)
                    print(f"   {city} value: {val:.2f}, percentile: {pct:.3f}")
            else:
                print(f"❌ {key}: not in cache")
    
    print("\n7. RUNNING FULL ASSESSMENT:")
    print("-" * 40)
    try:
        result = service.assess_city_climate_risk(city)
        print(f"🎯 FULL RESULTS:")
        print(f"   Hazard: {result['hazard_score']:.3f}")
        print(f"   Exposure: {result['exposure_score']:.3f}")
        print(f"   Vulnerability: {result['vulnerability_score']:.3f}")
        print(f"   Adaptive Capacity: {result['adaptive_capacity_score']:.3f}")
        print(f"   Risk: {result['risk_score']:.3f}")
    except Exception as e:
        print(f"❌ Error in full assessment: {e}")

if __name__ == "__main__":
    investigate_nurafshan_exposure()
