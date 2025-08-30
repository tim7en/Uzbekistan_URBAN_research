#!/usr/bin/env python3
"""
Test GDP exposure fix - should now use exposed GDP instead of total GDP
"""

from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService

def test_gdp_exposure_fix():
    """Test if GDP exposure now properly reflects exposed GDP vs total GDP"""
    
    print("Testing GDP Exposure Fix")
    print("=" * 60)
    
    try:
        # Initialize services
        base_path = "D:\\Dev\\Uzbekistan_URBAN_research"
        data_loader = ClimateDataLoader(base_path)
        assessment_service = IPCCRiskAssessmentService(data_loader)
        
        # Get city list
        cities = list(assessment_service.data['population_data'].keys())
        
        # Test GDP exposure for key cities
        test_cities = ["Tashkent", "Navoiy", "Nukus", "Urgench"]
        
        print("GDP Exposure Analysis:")
        print("-" * 70)
        print(f"{'City':<12} {'Pop':<8} {'GDP/cap':<8} {'Total GDP':<12} {'Exp GDP':<12} {'GDP Exp':<8}")
        print("-" * 70)
        
        results = []
        for city in test_cities:
            if city in cities:
                # Get population data
                pop_data = assessment_service.data['population_data'].get(city)
                pop = pop_data.population_2024
                gdp_pc = pop_data.gdp_per_capita_usd
                total_gdp = pop * gdp_pc
                
                # Run assessment
                result = assessment_service.assess_city_climate_risk(city)
                gdp_exposure = result.gdp_exposure
                
                # Calculate expected exposed GDP (using built area proxy)
                if pop > 1000000:  # Large cities
                    built_fraction = 0.7
                elif pop > 300000:  # Medium cities  
                    built_fraction = 0.5
                else:  # Small cities
                    built_fraction = 0.3
                
                exposed_gdp = total_gdp * built_fraction
                
                print(f"{city:<12} {pop/1000:<8.0f}K ${gdp_pc:<7.0f} ${total_gdp/1e9:<11.1f}B ${exposed_gdp/1e9:<11.1f}B {gdp_exposure:<8.3f}")
                
                results.append({
                    'city': city,
                    'population': pop,
                    'gdp_per_capita': gdp_pc,
                    'total_gdp': total_gdp,
                    'exposed_gdp': exposed_gdp,
                    'gdp_exposure': gdp_exposure
                })
        
        print("\nExpected vs Actual Results:")
        print("-" * 50)
        
        # Find cities with highest/lowest exposure
        max_exp_city = max(results, key=lambda x: x['gdp_exposure'])
        min_exp_city = min(results, key=lambda x: x['gdp_exposure'])
        
        print(f"Highest GDP exposure: {max_exp_city['city']} ({max_exp_city['gdp_exposure']:.3f})")
        print(f"Lowest GDP exposure:  {min_exp_city['city']} ({min_exp_city['gdp_exposure']:.3f})")
        
        # Check if Tashkent has highest exposure (expected)
        tashkent_result = next((r for r in results if r['city'] == 'Tashkent'), None)
        navoiy_result = next((r for r in results if r['city'] == 'Navoiy'), None)
        
        if tashkent_result and navoiy_result:
            print(f"\nKey Comparison:")
            print(f"Tashkent exposed GDP: ${tashkent_result['exposed_gdp']/1e9:.1f}B → exposure: {tashkent_result['gdp_exposure']:.3f}")
            print(f"Navoiy exposed GDP:   ${navoiy_result['exposed_gdp']/1e9:.1f}B → exposure: {navoiy_result['gdp_exposure']:.3f}")
            
            if tashkent_result['gdp_exposure'] > navoiy_result['gdp_exposure']:
                print("✅ SUCCESS: Tashkent now has higher GDP exposure than Navoiy (as expected)")
            else:
                print("❌ ISSUE: Navoiy still has higher exposure than Tashkent")
                
        # Check correlation with total GDP vs GDP per capita
        import numpy as np
        from scipy.stats import pearsonr
        
        total_gdps = [r['total_gdp'] for r in results]
        gdp_per_capitas = [r['gdp_per_capita'] for r in results]
        exposures = [r['gdp_exposure'] for r in results]
        
        corr_total, _ = pearsonr(total_gdps, exposures)
        corr_per_capita, _ = pearsonr(gdp_per_capitas, exposures)
        
        print(f"\nCorrelation Analysis:")
        print(f"GDP exposure vs Total GDP:     {corr_total:.6f}")
        print(f"GDP exposure vs GDP per capita: {corr_per_capita:.6f}")
        
        if corr_total > 0.6 and corr_per_capita < 0.4:
            print("✅ SUCCESS: GDP exposure now correlates with total GDP, not per capita")
        elif corr_per_capita > corr_total:
            print("❌ ISSUE: Still correlates more with per capita than total GDP")
        else:
            print("⚠️  MIXED: Check if exposed fraction is working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_gdp_exposure_fix()
