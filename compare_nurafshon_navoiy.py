#!/usr/bin/env python3
"""
Detailed comparison of Nurafshon vs Navoiy adaptive capacity
"""

import json

def compare_cities():
    with open('D:/Dev/Uzbekistan_URBAN_research/suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json', 'r') as f:
        data = json.load(f)

    print('DETAILED COMPARISON: Nurafshon vs Navoiy')
    print('=' * 50)

    nurafshon = data['Nurafshon']
    navoiy = data['Navoiy']

    print('\nADAPTABILITY SCORES:')
    print(f'Nurafshon adaptability: {nurafshon["adaptability_score"]:.3f}')
    print(f'Navoiy adaptability:    {navoiy["adaptability_score"]:.3f}')

    print('\nOVERALL RISK SCORES:')
    print(f'Nurafshon risk: {nurafshon["overall_risk_score"]:.3f}')
    print(f'Navoiy risk:    {navoiy["overall_risk_score"]:.3f}')

    print('\nHAZARD COMPONENTS:')
    print(f'                    Nurafshon  Navoiy')
    print(f'Heat hazard:        {nurafshon["heat_hazard"]:.3f}     {navoiy["heat_hazard"]:.3f}')
    print(f'Air quality hazard: {nurafshon["air_quality_hazard"]:.3f}     {navoiy["air_quality_hazard"]:.3f}')
    print(f'Dry hazard:         {nurafshon["dry_hazard"]:.3f}     {navoiy["dry_hazard"]:.3f}')
    print(f'Dust hazard:        {nurafshon["dust_hazard"]:.3f}     {navoiy["dust_hazard"]:.3f}')
    print(f'Pluvial hazard:     {nurafshon["pluvial_hazard"]:.3f}     {navoiy["pluvial_hazard"]:.3f}')

    print('\nVULNERABILITY COMPONENTS:')
    print(f'                           Nurafshon  Navoiy')
    print(f'Income vulnerability:      {nurafshon["income_vulnerability"]:.3f}     {navoiy["income_vulnerability"]:.3f}')
    print(f'Air pollution vulnerability: {nurafshon["air_pollution_vulnerability"]:.3f}     {navoiy["air_pollution_vulnerability"]:.3f}')
    print(f'Healthcare access vuln:    {nurafshon["healthcare_access_vulnerability"]:.3f}     {navoiy["healthcare_access_vulnerability"]:.3f}')
    print(f'Education access vuln:     {nurafshon["education_access_vulnerability"]:.3f}     {navoiy["education_access_vulnerability"]:.3f}')

    print('\nADAPTIVE CAPACITY COMPONENTS:')
    print(f'                          Nurafshon  Navoiy')
    print(f'GDP adaptive capacity:    {nurafshon["gdp_adaptive_capacity"]:.3f}     {navoiy["gdp_adaptive_capacity"]:.3f}')
    print(f'Air quality adapt cap:    {nurafshon["air_quality_adaptive_capacity"]:.3f}     {navoiy["air_quality_adaptive_capacity"]:.3f}')
    print(f'Social infrastructure:    {nurafshon["social_infrastructure_capacity"]:.3f}     {navoiy["social_infrastructure_capacity"]:.3f}')
    print(f'Services adapt capacity:  {nurafshon["services_adaptive_capacity"]:.3f}     {navoiy["services_adaptive_capacity"]:.3f}')

    print('\nCITY CHARACTERISTICS:')
    print(f'                    Nurafshon     Navoiy')
    print(f'Population:         {nurafshon["population"]:,}      {navoiy["population"]:,}')
    print(f'GDP per capita:     ${nurafshon["gdp_per_capita_usd"]:,.0f}       ${navoiy["gdp_per_capita_usd"]:,.0f}')

if __name__ == "__main__":
    compare_cities()
