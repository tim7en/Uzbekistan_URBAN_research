#!/usr/bin/env python3
"""
DEBUG CITY NAME MATCHING IN HAZARD CALCULATIONS
===============================================
"""

from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService
from pathlib import Path

def debug_city_names():
    """Debug city name matching in hazard calculations"""
    
    print("DEBUG CITY NAME MATCHING")
    print("=" * 50)
    
    # Initialize services
    repo_root = Path(__file__).resolve().parent
    base_path = repo_root / "suhi_analysis_output"
    
    data_loader = ClimateDataLoader(str(base_path))
    risk_assessor = IPCCRiskAssessmentService(data_loader)
    
    # Check city names across data sources
    print("\\nCITY NAMES BY DATA SOURCE:")
    
    pop_cities = list(risk_assessor.data['population_data'].keys())
    temp_cities = list(risk_assessor.data['temperature_data'].keys())
    lulc_cities = [city.get('city') for city in risk_assessor.data['lulc_data']]
    
    print(f"Population data: {pop_cities}")
    print(f"Temperature data: {temp_cities}")
    print(f"LULC data: {lulc_cities}")
    
    # Check for mismatches
    all_cities = set(pop_cities + temp_cities + lulc_cities)
    
    print(f"\\nCHECKING FOR MISMATCHES:")
    mismatches = []
    for city in all_cities:
        in_pop = city in pop_cities
        in_temp = city in temp_cities
        in_lulc = city in lulc_cities
        
        if not (in_pop and in_temp and in_lulc):
            mismatches.append(f"{city}: Pop={in_pop}, Temp={in_temp}, LULC={in_lulc}")
    
    if mismatches:
        for mismatch in mismatches:
            print(f"WARNING: {mismatch}")
    else:
        print("All cities found in all data sources")
    
    # Test heat hazard calculation for one city
    test_city = pop_cities[0]
    print(f"\\nTESTING HEAT HAZARD FOR {test_city}:")
    
    # Add debug info to see what's happening in the calculation
    temp_data = risk_assessor.data['temperature_data'].get(test_city, {})
    print(f"Temperature data available: {bool(temp_data)}")
    if temp_data:
        print(f"Temperature data keys: {temp_data.keys()}")
    
    heat_hazard = risk_assessor._calculate_heat_hazard(test_city)
    print(f"Heat hazard result: {heat_hazard}")
    
    # Test pluvial hazard calculation
    print(f"\\nTESTING PLUVIAL HAZARD FOR {test_city}:")
    pluvial_hazard = risk_assessor._calculate_pluvial_hazard(test_city)
    print(f"Pluvial hazard result: {pluvial_hazard}")
    
    # Check what happens with city name list in heat hazard
    print(f"\\nDEBUGGING HEAT HAZARD CITY NAME MATCHING:")
    all_temp_values = []
    all_city_names = []
    
    for city_name in list(risk_assessor.data['population_data'].keys()):
        temp_data = risk_assessor.data['temperature_data'].get(city_name, {})
        if temp_data:
            current_temp = temp_data.get('current_suhi_intensity', 0)
            temp_trend = temp_data.get('temperature_trend', 0) * 10
            summer_max = temp_data.get('summer_max_temp', current_temp + 30)
            
            heat_indicator = (current_temp * 0.5 + 
                            temp_trend * 0.3 + 
                            (summer_max - 35) * 0.2)
            
            all_temp_values.append(heat_indicator)
            all_city_names.append(city_name)
        else:
            all_temp_values.append(0)
            all_city_names.append(city_name)
    
    print(f"City names in heat calculation: {all_city_names}")
    print(f"Test city '{test_city}' in list: {test_city in all_city_names}")
    
    if test_city in all_city_names:
        city_index = all_city_names.index(test_city)
        print(f"City index: {city_index}")
        print(f"Raw heat value: {all_temp_values[city_index]}")
    
    print("\\nALL TEMPERATURE VALUES:")
    for i, (city_name, temp_val) in enumerate(zip(all_city_names, all_temp_values)):
        print(f"  {city_name}: {temp_val:.6f}")

if __name__ == "__main__":
    debug_city_names()
