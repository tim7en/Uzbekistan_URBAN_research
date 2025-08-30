#!/usr/bin/env python3
"""
Test winsorized percentile scaling fix - should reduce max-pegging
"""

from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService

def test_winsorized_scaling_fix():
    """Test if winsorized scaling reduces components hitting 1.000"""
    
    print("Testing Winsorized Percentile Scaling Fix")
    print("=" * 60)
    
    try:
        # Initialize services
        base_path = "D:\\Dev\\Uzbekistan_URBAN_research"
        data_loader = ClimateDataLoader(base_path)
        assessment_service = IPCCRiskAssessmentService(data_loader)
        
        # Get city list
        cities = list(assessment_service.data['population_data'].keys())
        
        # Test key components for max-pegging
        target_components = [
            'gdp_exposure', 'population_exposure', 'gdp_adaptive_capacity'
        ]
        
        print("Max-Pegging Analysis (Components at 1.000):")
        print("-" * 50)
        
        city_results = {}
        component_maxima = {comp: [] for comp in target_components}
        
        for city in cities:
            result = assessment_service.assess_city_climate_risk(city)
            city_results[city] = result
            
            # Check for components at 1.000
            for comp in target_components:
                value = getattr(result, comp, 0)
                component_maxima[comp].append(value)
                if abs(value - 1.0) < 0.001:  # Close to 1.000
                    print(f"  {city}: {comp} = {value:.6f} (MAX)")
        
        print(f"\nComponent Distribution Analysis:")
        print("-" * 40)
        
        for comp in target_components:
            values = component_maxima[comp]
            max_count = sum(1 for v in values if abs(v - 1.0) < 0.001)
            min_val = min(values)
            max_val = max(values)
            unique_count = len(set([round(v, 3) for v in values]))
            
            print(f"{comp}:")
            print(f"  Range: {min_val:.3f} to {max_val:.3f}")
            print(f"  Cities at 1.000: {max_count}/{len(values)} ({max_count/len(values)*100:.1f}%)")
            print(f"  Unique values: {unique_count}")
            
            if max_count == 0:
                print(f"  ✅ No max-pegging detected")
            elif max_count <= 2:
                print(f"  ⚠️  Limited max-pegging")
            else:
                print(f"  ❌ Significant max-pegging")
            print()
        
        # Test Tashkent specifically
        print("Tashkent Component Analysis:")
        print("-" * 30)
        tashkent_result = city_results.get('Tashkent')
        if tashkent_result:
            print(f"GDP exposure: {tashkent_result.gdp_exposure:.6f}")
            print(f"Population exposure: {tashkent_result.population_exposure:.6f}")
            print(f"GDP adaptive capacity: {tashkent_result.gdp_adaptive_capacity:.6f}")
            
            # Count components at 1.000
            all_components = [
                'gdp_exposure', 'population_exposure', 'gdp_adaptive_capacity',
                'hazard_score', 'exposure_score', 'vulnerability_score',
                'overall_risk_score', 'hev_score', 'hev_adj_score'
            ]
            
            max_pegged_count = 0
            for comp in all_components:
                value = getattr(tashkent_result, comp, 0)
                if abs(value - 1.0) < 0.001:
                    max_pegged_count += 1
            
            print(f"\nTashkent components at 1.000: {max_pegged_count}/{len(all_components)}")
            
            if max_pegged_count <= 3:
                print("✅ Significant reduction in max-pegging achieved")
            elif max_pegged_count <= 6:
                print("⚠️  Moderate improvement in max-pegging")
            else:
                print("❌ Max-pegging still excessive")
        
        # Test the winsorized function directly
        print(f"\nWinsorized Function Test:")
        print("-" * 30)
        test_values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]  # Value 100 is extreme
        
        normal_result = data_loader.pct_norm(test_values, 100)
        winsorized_result = data_loader.winsorized_pct_norm(test_values, 100)
        
        print(f"Normal pct_norm(100): {normal_result:.6f}")
        print(f"Winsorized pct_norm(100): {winsorized_result:.6f}")
        
        if winsorized_result < normal_result:
            print("✅ Winsorized scaling working - extreme values capped")
        else:
            print("❌ Winsorized scaling may not be working properly")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_winsorized_scaling_fix()
