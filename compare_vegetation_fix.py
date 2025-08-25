"""
Compare vulnerability and adaptive capacity scores before and after vegetation accessibility fix
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))

from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService

def compare_vegetation_fix():
    """Compare key cities before/after vegetation accessibility fix"""
    
    # Initialize services
    base_path = "suhi_analysis_output"
    data_loader = ClimateDataLoader(base_path=base_path)
    assessment_service = IPCCRiskAssessmentService(data_loader)
    
    # Test key cities
    test_cities = ['Andijan', 'Bukhara', 'Tashkent', 'Samarkand', 'Nurafshon']
    
    print("VEGETATION ACCESSIBILITY FIX - IMPACT ANALYSIS")
    print("=" * 60)
    
    for city in test_cities:
        print(f"\n--- {city} ---")
        
        # Get spatial data
        spatial_data = assessment_service.data['spatial_data'].get('per_year', {}).get(city, {})
        if spatial_data:
            years = sorted([int(y) for y in spatial_data.keys()])
            if years:
                latest_year = str(years[-1])
                veg_distance = spatial_data[latest_year].get('vegetation_accessibility', {}).get('city', {}).get('mean', 1000)
                
                # OLD METHOD (incorrect - treated distance as percentage)
                old_veg_access = min(100.0, max(0.0, veg_distance))
                old_green_vuln = max(0.0, 1.0 - (old_veg_access / 100))
                old_green_capacity = (old_veg_access / 100) * 0.7
                
                # NEW METHOD (correct - distance-based)
                max_walking_distance = 1000
                new_accessibility = max(0.0, 1.0 - (veg_distance / max_walking_distance))
                new_green_vuln = 1.0 - new_accessibility
                new_green_capacity = new_accessibility * 0.7
                
                print(f"  Distance to vegetation: {veg_distance:.1f}m")
                print(f"  OLD (incorrect): Treated as {old_veg_access:.1f}% → Green vuln: {old_green_vuln:.3f}")
                print(f"  NEW (correct):   Accessibility: {new_accessibility:.3f} → Green vuln: {new_green_vuln:.3f}")
                print(f"  GREEN VULNERABILITY CHANGE: {old_green_vuln:.3f} → {new_green_vuln:.3f} ({new_green_vuln-old_green_vuln:+.3f})")
                
                # Calculate actual scores
                vulnerability_score = assessment_service.calculate_vulnerability_score(city)
                adaptive_capacity_score = assessment_service.calculate_adaptive_capacity_score(city)
                
                print(f"  Final Vulnerability Score: {vulnerability_score:.3f}")
                print(f"  Final Adaptive Capacity Score: {adaptive_capacity_score:.3f}")

if __name__ == "__main__":
    compare_vegetation_fix()
