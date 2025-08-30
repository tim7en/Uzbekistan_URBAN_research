#!/usr/bin/env python3
"""
Test risk formula fix - should now include adaptive capacity
"""

from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService

def test_risk_formula_fix():
    """Test if risk formula now includes adaptive capacity"""
    
    print("Testing Risk Formula Fix")
    print("=" * 60)
    
    try:
        # Initialize services
        base_path = "D:\\Dev\\Uzbekistan_URBAN_research"
        data_loader = ClimateDataLoader(base_path)
        assessment_service = IPCCRiskAssessmentService(data_loader)
        
        # Get city list
        cities = list(assessment_service.data['population_data'].keys())
        
        # Test risk calculation for a few cities
        test_cities = ["Tashkent", "Nukus", "Navoiy", "Termez"]
        
        print("Risk Formula Analysis:")
        print("-" * 50)
        print(f"{'City':<12} {'H':<6} {'E':<6} {'V':<6} {'AC':<6} {'HEV':<6} {'HEV_adj':<8} {'Risk':<6}")
        print("-" * 50)
        
        for city in test_cities:
            if city in cities:
                # Run assessment for this city
                result = assessment_service.assess_city_climate_risk(city)
                
                h = result.hazard_score
                e = result.exposure_score
                v = result.vulnerability_score
                ac = result.adaptive_capacity_score
                hev = result.hev_score
                hev_adj = result.hev_adj_score
                risk = result.overall_risk_score
                
                print(f"{city:<12} {h:<6.3f} {e:<6.3f} {v:<6.3f} {ac:<6.3f} {hev:<6.3f} {hev_adj:<8.3f} {risk:<6.3f}")
                
                # Verify the formula
                expected_hev = h * e * v
                expected_hev_adj = hev * (1.0 - ac)
                
                if abs(hev - expected_hev) > 0.001:
                    print(f"  ❌ HEV calculation error: expected {expected_hev:.6f}, got {hev:.6f}")
                elif abs(hev_adj - expected_hev_adj) > 0.001:
                    print(f"  ❌ HEV_adj calculation error: expected {expected_hev_adj:.6f}, got {hev_adj:.6f}")
                elif abs(risk - hev_adj) > 0.001:
                    print(f"  ❌ Risk should equal HEV_adj: expected {hev_adj:.6f}, got {risk:.6f}")
                else:
                    reduction = ((hev - hev_adj) / hev * 100) if hev > 0 else 0
                    print(f"  ✅ Formula correct. Risk reduced by {reduction:.1f}% due to adaptive capacity")
        
        print("\nFormula Verification:")
        print("- HEV = H × E × V (original IPCC risk)")
        print("- HEV_adj = HEV × (1 - AC) (risk adjusted for adaptive capacity)")
        print("- Risk = HEV_adj (primary risk score)")
        print()
        
        # Test impact of adaptive capacity
        print("Adaptive Capacity Impact Analysis:")
        print("-" * 40)
        
        ac_values = [0.2, 0.5, 0.8]  # Low, Medium, High adaptive capacity
        base_hev = 0.6  # Example base risk
        
        print(f"Base HEV Risk: {base_hev:.3f}")
        for ac in ac_values:
            adjusted_risk = base_hev * (1.0 - ac)
            reduction = (1.0 - adjusted_risk/base_hev) * 100
            print(f"  AC = {ac:.1f}: Risk = {adjusted_risk:.3f} (reduced by {reduction:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_risk_formula_fix()
