#!/usr/bin/env python3
"""
Debug air pollution vulnerability calculation for Nurafshon vs Navoiy
"""

import json

def debug_air_pollution():
    with open('D:/Dev/Uzbekistan_URBAN_research/suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json', 'r') as f:
        data = json.load(f)

    print('DEBUG: Why does Nurafshon have lower air pollution vulnerability?')
    print('=' * 65)

    for city in ['Nurafshon', 'Navoiy']:
        city_data = data[city]
        
        # Calculate expected air pollution vulnerability manually
        population = city_data['population']
        # Need to find area - let's extract from built_area_percentage calculation
        built_area_pct = city_data['built_area_percentage']
        
        print(f'\n{city}:')
        print(f'  Population: {population:,}')
        print(f'  Built area %: {built_area_pct:.1f}%')
        print(f'  Air quality hazard: {city_data["air_quality_hazard"]:.3f}')
        print(f'  Air pollution vulnerability: {city_data["air_pollution_vulnerability"]:.3f}')
        
        # The contradiction
        if city == 'Nurafshon':
            print(f'  -> Higher air quality hazard but LOWER air pollution vulnerability?')
        else:
            print(f'  -> Lower air quality hazard but HIGHER air pollution vulnerability?')

    print('\n' + '=' * 65)
    print('CONCLUSION: This seems contradictory!')
    print('Nurafshon has:')
    print('- HIGHER air quality hazard (0.956 vs 0.844)')
    print('- But LOWER air pollution vulnerability (0.300 vs 0.500)')
    print('- This suggests the vulnerability calculation may be flawed')
    print('\nNavoiy should likely rank higher due to:')
    print('- Much better economic capacity (GDP $4,816 vs $1,972)')
    print('- Lower air quality hazard')
    print('- But assessment gives Nurafshon credit for low exposure (small city bias)')

if __name__ == "__main__":
    debug_air_pollution()
