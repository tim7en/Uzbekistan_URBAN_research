#!/usr/bin/env python3
"""
DEBUG TEMPERATURE DATA STRUCTURE
================================
"""

from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService
from pathlib import Path
import json

def debug_temperature_data():
    """Debug the temperature data structure to understand why all values are -1.0"""
    
    print("DEBUG TEMPERATURE DATA STRUCTURE")
    print("=" * 50)
    
    # Initialize services
    repo_root = Path(__file__).resolve().parent
    base_path = repo_root / "suhi_analysis_output"
    
    data_loader = ClimateDataLoader(str(base_path))
    risk_assessor = IPCCRiskAssessmentService(data_loader)
    
    # Examine temperature data structure for one city
    test_city = "Tashkent"
    temp_data = risk_assessor.data['temperature_data'].get(test_city, {})
    
    print(f"\\nTEMPERATURE DATA FOR {test_city}:")
    print(f"Available keys: {list(temp_data.keys())}")
    
    # Check specific fields used in heat hazard calculation
    fields_to_check = [
        'current_suhi_intensity',
        'temperature_trend', 
        'summer_max_temp'
    ]
    
    print(f"\\nCHECKING HEAT HAZARD FIELDS:")
    for field in fields_to_check:
        value = temp_data.get(field, "NOT FOUND")
        print(f"  {field}: {value}")
    
    # Check if the data is nested by years
    if temp_data and isinstance(list(temp_data.keys())[0], int):
        print(f"\\nDATA IS NESTED BY YEARS")
        latest_year = max(temp_data.keys())
        print(f"Latest year: {latest_year}")
        print(f"Latest year data keys: {list(temp_data[latest_year].keys())}")
        
        # Show a sample of the nested structure
        print(f"\\nSAMPLE NESTED STRUCTURE:")
        print(json.dumps(temp_data[latest_year], indent=2)[:500] + "...")
    
    # Let's see what fields are actually available
    print(f"\\nFULL TEMPERATURE DATA STRUCTURE SAMPLE:")
    if temp_data:
        # Show first 10 lines of the structure
        temp_str = json.dumps(temp_data, indent=2)
        lines = temp_str.split('\\n')[:20]
        for line in lines:
            print(line)
        print("...")
    
    # Check what happens in the heat hazard calculation
    print(f"\\nSIMULATING HEAT HAZARD CALCULATION:")
    
    # This is the exact code from _calculate_heat_hazard
    current_temp = temp_data.get('current_suhi_intensity', 0)
    temp_trend = temp_data.get('temperature_trend', 0) * 10
    summer_max = temp_data.get('summer_max_temp', current_temp + 30)
    
    print(f"  current_suhi_intensity: {current_temp}")
    print(f"  temperature_trend * 10: {temp_trend}")
    print(f"  summer_max_temp: {summer_max}")
    
    heat_indicator = (current_temp * 0.5 + 
                     temp_trend * 0.3 + 
                     (summer_max - 35) * 0.2)
    
    print(f"  heat_indicator: {heat_indicator}")
    
    # Check if we need to use nested data instead
    if temp_data and isinstance(list(temp_data.keys())[0], int):
        print(f"\\nTRYING WITH NESTED DATA ACCESS:")
        latest_year = max(temp_data.keys())
        latest_data = temp_data[latest_year]
        
        # Try different field names that might exist
        possible_fields = [
            'current_suhi_intensity',
            'suhi_intensity',
            'mean_suhi',
            'summer_suhi',
            'temperature_trend',
            'trend',
            'summer_max_temp',
            'max_temp',
            'summer_temp'
        ]
        
        print(f"  Available fields in {latest_year}: {list(latest_data.keys())}")
        
        for field in possible_fields:
            if field in latest_data:
                print(f"  FOUND {field}: {latest_data[field]}")

def check_all_cities_temp_data():
    """Check temperature data for all cities to find the pattern"""
    
    print("\\n" + "=" * 50)
    print("CHECKING ALL CITIES TEMPERATURE DATA")
    print("=" * 50)
    
    # Initialize services
    repo_root = Path(__file__).resolve().parent
    base_path = repo_root / "suhi_analysis_output"
    
    data_loader = ClimateDataLoader(str(base_path))
    risk_assessor = IPCCRiskAssessmentService(data_loader)
    
    for city in ['Tashkent', 'Nukus', 'Samarkand']:
        temp_data = risk_assessor.data['temperature_data'].get(city, {})
        print(f"\\n{city}:")
        
        if temp_data:
            # Check top-level fields
            top_fields = [k for k in temp_data.keys() if not isinstance(k, int)]
            print(f"  Top-level fields: {top_fields}")
            
            # Check year-based fields
            year_fields = [k for k in temp_data.keys() if isinstance(k, int)]
            if year_fields:
                latest_year = max(year_fields)
                print(f"  Latest year: {latest_year}")
                print(f"  Year data keys: {list(temp_data[latest_year].keys())}")

if __name__ == "__main__":
    debug_temperature_data()
    check_all_cities_temp_data()
