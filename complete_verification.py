#!/usr/bin/env python3
"""
Complete verification of all fixes
"""

import json

def complete_verification():
    with open('D:/Dev/Uzbekistan_URBAN_research/suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json', 'r') as f:
        data = json.load(f)

    print('COMPLETE VERIFICATION - All Fixed Values:')
    print('=' * 60)
    cities = ['Tashkent', 'Nukus', 'Andijan', 'Navoiy', 'Samarkand', 'Namangan']

    print('Air Quality Hazard (different values):')
    for city in cities:
        print(f'  {city}: {data[city]["air_quality_hazard"]:.3f}')

    print()
    print('Surface Water Change (different values):')
    for city in cities:
        print(f'  {city}: {data[city]["surface_water_change"]:.3f}')

    print()
    print('Air Pollution Vulnerability (different values):')
    for city in cities:
        print(f'  {city}: {data[city]["air_pollution_vulnerability"]:.3f}')

    print()
    print('Water System Capacity (same improved fallback):')
    for city in cities:
        print(f'  {city}: {data[city]["water_system_capacity"]:.3f}')

if __name__ == "__main__":
    complete_verification()
