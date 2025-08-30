#!/usr/bin/env python3
"""
Final verification of all fixes
"""

import json

def verify_fixes():
    with open('D:/Dev/Uzbekistan_URBAN_research/suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json', 'r') as f:
        data = json.load(f)

    print('FINAL VERIFICATION - Checking Fixed Values:')
    print('=' * 60)
    print()
    print('Air Quality Hazard (should be different):')
    for city in ['Tashkent', 'Nukus', 'Andijan', 'Navoiy']:
        print(f'  {city}: {data[city]["air_quality_hazard"]:.3f}')

    print()
    print('Air Pollution Vulnerability (should be different):')
    for city in ['Tashkent', 'Nukus', 'Andijan', 'Navoiy']:
        print(f'  {city}: {data[city]["air_pollution_vulnerability"]:.3f}')

    print()
    print('Water System Capacity (should be same new value):')
    for city in ['Tashkent', 'Nukus', 'Andijan', 'Navoiy']:
        print(f'  {city}: {data[city]["water_system_capacity"]:.3f}')

    print()
    print('Surface Water Change (should be different):')
    for city in ['Tashkent', 'Nukus', 'Andijan', 'Navoiy']:
        print(f'  {city}: {data[city]["surface_water_change"]:.3f}')

if __name__ == "__main__":
    verify_fixes()
