#!/usr/bin/env python3
"""
Test water system capacity fix - should now vary by city GDP instead of constant 0.4
"""

from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService

def test_water_system_capacity_fix():
    """Test if water system capacity is now city-specific instead of constant 0.4"""
    
    print("Testing Water System Capacity Fix")
    print("=" * 60)
    
    try:
        # Initialize services
        base_path = "D:\\Dev\\Uzbekistan_URBAN_research"
        data_loader = ClimateDataLoader(base_path)
        assessment_service = IPCCRiskAssessmentService(data_loader)
        
        # Get city list
        cities = list(assessment_service.data['population_data'].keys())
        
        # Test water system capacity calculation for each city
        water_capacities = []
        gdp_values = []
        
        print("Water System Capacity by City:")
        print("-" * 40)
        
        for city in cities:
            # Get GDP data
            pop_data = assessment_service.data['population_data'].get(city)
            gdp = pop_data.gdp_per_capita_usd if pop_data else 0
            
            # Calculate water system capacity
            water_capacity = assessment_service._calculate_water_system_capacity(city)
            
            water_capacities.append(water_capacity)
            gdp_values.append(gdp)
            
            print(f"{city:12}: {water_capacity:.3f} (GDP: ${gdp:,.0f})")
        
        # Check if values vary
        unique_values = len(set(water_capacities))
        min_capacity = min(water_capacities)
        max_capacity = max(water_capacities)
        
        print(f"\nSummary:")
        print(f"Unique values: {unique_values}")
        print(f"Range: {min_capacity:.3f} to {max_capacity:.3f}")
        print(f"Standard deviation: {__import__('numpy').std(water_capacities):.6f}")
        
        if unique_values == 1 and water_capacities[0] == 0.4:
            print("❌ BUG STILL EXISTS - All values are constant 0.4")
        elif unique_values == 1:
            print(f"⚠️  WARNING - All values are constant {water_capacities[0]}")
        else:
            print("✅ SUCCESS - Water system capacity now varies by city!")
            
        # Test correlation with GDP
        if len(water_capacities) > 2:
            from scipy.stats import pearsonr
            correlation, p_value = pearsonr(gdp_values, water_capacities)
            print(f"Correlation with GDP: {correlation:.6f} (p={p_value:.6f})")
            
            if correlation > 0.5:
                print("✅ Good - Positive correlation with GDP as expected")
            else:
                print("⚠️  Note - Weak correlation with GDP")
        
        # Show GDP tiers
        print(f"\nGDP-based Expected Capacities:")
        print(f"GDP ≥ $3,000: 0.8 capacity")
        print(f"GDP ≥ $1,500: 0.6 capacity") 
        print(f"GDP ≥ $1,000: 0.5 capacity")
        print(f"GDP ≥ $700:   0.4 capacity")
        print(f"GDP < $700:   0.3 capacity")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_water_system_capacity_fix()
