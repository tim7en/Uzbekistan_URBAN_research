#!/usr/bin/env python3
"""
Debug air quality hazard calculation to understand why all cities get 1.0
"""

from services.climate_risk_assessment import IPCCRiskAssessmentService
from services.climate_data_loader import ClimateDataLoader

def debug_air_quality_hazard():
    loader = ClimateDataLoader('D:/Dev/Uzbekistan_URBAN_research/suhi_analysis_output')
    loader.load_all_data()
    service = IPCCRiskAssessmentService(loader)
    
    print("DEBUG: Air Quality Hazard Calculation Breakdown")
    print("=" * 60)
    
    # Test cities with different characteristics
    test_cities = ['Tashkent', 'Nukus', 'Navoiy', 'Nurafshon']
    
    for city in test_cities:
        print(f"\n{city}:")
        print("-" * 30)
        
        # Get air quality data for the city
        air_quality_data = service.data.get('air_quality_data', {}).get(city, {})
        
        if not air_quality_data:
            print(f"  No air quality data for {city}")
            continue
            
        # Get the yearly results
        yearly_results = air_quality_data.get('yearly_results', {})
        if not yearly_results:
            print(f"  No yearly results for {city}")
            continue
            
        # Get the most recent year
        years = sorted([int(y) for y in yearly_results.keys() if y.isdigit()])
        if not years:
            print(f"  No valid year data for {city}")
            continue
            
        latest_year = str(years[-1])
        year_data = yearly_results[latest_year]
        
        print(f"  Latest year: {latest_year}")
        
        if 'pollutants' not in year_data:
            print(f"  No pollutants data for {city} in {latest_year}")
            continue
            
        pollutants = year_data['pollutants']
        hazard_components = []
        
        # NO2 hazard (traffic pollution)
        if 'NO2' in pollutants and 'urban_annual' in pollutants['NO2']:
            no2_mean = pollutants['NO2']['urban_annual'].get('mean', 0.0)
            if no2_mean > 0:
                # NO2 is likely already in mol/mol or similar, convert carefully
                no2_hazard = min(1.0, no2_mean / 0.0001)  # Normalize to realistic range
                component_value = no2_hazard * 0.3
                hazard_components.append(component_value)
                print(f"  NO2: {no2_mean:.6f} -> hazard {no2_hazard:.3f} -> component {component_value:.3f}")
        
        # O3 hazard (photochemical pollution)
        if 'O3' in pollutants and 'urban_annual' in pollutants['O3']:
            o3_mean = pollutants['O3']['urban_annual'].get('mean', 0.0)
            if o3_mean > 0:
                # O3 values in mol/mol, typical range 0-0.0002
                o3_hazard = min(1.0, o3_mean / 0.0002)  # Normalize to realistic range
                component_value = o3_hazard * 0.25
                hazard_components.append(component_value)
                print(f"  O3: {o3_mean:.6f} -> hazard {o3_hazard:.3f} -> component {component_value:.3f}")
        
        # SO2 hazard (industrial pollution)
        if 'SO2' in pollutants and 'urban_annual' in pollutants['SO2']:
            so2_mean = pollutants['SO2']['urban_annual'].get('mean', 0.0)
            if so2_mean > 0:
                # SO2 values in mol/mol, typical range 0-0.00005
                so2_hazard = min(1.0, so2_mean / 0.00005)  # Normalize to realistic range
                component_value = so2_hazard * 0.2
                hazard_components.append(component_value)
                print(f"  SO2: {so2_mean:.6f} -> hazard {so2_hazard:.3f} -> component {component_value:.3f}")
        
        # CO hazard (combustion pollution)
        if 'CO' in pollutants and 'urban_annual' in pollutants['CO']:
            co_mean = pollutants['CO']['urban_annual'].get('mean', 0.0)
            if co_mean > 0:
                # CO values in mol/mol, typical range 0-0.001
                co_hazard = min(1.0, co_mean / 0.001)  # Normalize to realistic range
                component_value = co_hazard * 0.15
                hazard_components.append(component_value)
                print(f"  CO: {co_mean:.6f} -> hazard {co_hazard:.3f} -> component {component_value:.3f}")
        
        # CH4 hazard (methane pollution)
        if 'CH4' in pollutants and 'urban_annual' in pollutants['CH4']:
            ch4_mean = pollutants['CH4']['urban_annual'].get('mean', 0.0)
            if ch4_mean > 0:
                # CH4 is measured in ppmv, global background is ~1.8 ppmv
                ch4_hazard = min(1.0, max(0.0, (ch4_mean - 1900) / 50))  # Range 1900-1950 ppmv
                component_value = ch4_hazard * 0.1
                hazard_components.append(component_value)
                print(f"  CH4: {ch4_mean:.1f} ppmv -> hazard {ch4_hazard:.3f} -> component {component_value:.3f}")
        
        # PM2.5 proxy from aerosol index
        if 'AER_AI' in pollutants and 'urban_annual' in pollutants['AER_AI']:
            aer_ai = pollutants['AER_AI']['urban_annual'].get('mean', 0.0)
            # Aerosol index can be negative or positive
            pm_hazard = min(1.0, max(0.0, aer_ai / 1.0))  # Normalize: 0-1.0 range
            component_value = pm_hazard * 0.2
            hazard_components.append(component_value)
            print(f"  AER_AI: {aer_ai:.6f} -> hazard {pm_hazard:.3f} -> component {component_value:.3f}")
        
        total_hazard = min(1.0, sum(hazard_components)) if hazard_components else 0.0
        print(f"  Total components: {len(hazard_components)}")
        print(f"  Sum before cap: {sum(hazard_components):.3f}")
        print(f"  Final hazard: {total_hazard:.3f}")

if __name__ == "__main__":
    debug_air_quality_hazard()
