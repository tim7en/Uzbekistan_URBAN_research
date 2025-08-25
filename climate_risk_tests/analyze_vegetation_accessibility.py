"""
Analyze vegetation accessibility data and its interpretation issues.
This script examines the actual vegetation accessibility values and 
proposes improvements for vulnerability calculations.
"""

import json
import numpy as np
import pandas as pd
from typing import Dict, List, Any

def load_spatial_data():
    """Load and examine spatial relationships data"""
    try:
        with open('suhi_analysis_output/reports/spatial_relationships_report.json', 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print("Spatial data file not found")
        return None

def analyze_vegetation_accessibility():
    """Analyze vegetation accessibility values across all cities"""
    
    data = load_spatial_data()
    if not data:
        return
    
    print("VEGETATION ACCESSIBILITY ANALYSIS")
    print("=" * 50)
    
    all_veg_access = []
    city_stats = []
    
    for city, years_data in data.get('per_year', {}).items():
        print(f"\n--- {city} ---")
        
        for year, year_data in years_data.items():
            veg_access_data = year_data.get('vegetation_accessibility', {}).get('city', {})
            if veg_access_data:
                mean_distance = veg_access_data.get('mean', 0)
                stddev = veg_access_data.get('stdDev', 0)
                count = veg_access_data.get('count', 0)
                
                print(f"  {year}: Mean distance to vegetation: {mean_distance:.1f}m")
                print(f"        Std dev: {stddev:.1f}m, Sample count: {count:,}")
                
                all_veg_access.append(mean_distance)
                city_stats.append({
                    'city': city,
                    'year': year,
                    'mean_distance_m': mean_distance,
                    'stddev_m': stddev,
                    'count': count
                })
    
    # Overall statistics
    print(f"\nOVERALL STATISTICS:")
    print(f"Number of city-year observations: {len(all_veg_access)}")
    print(f"Mean distance to vegetation: {np.mean(all_veg_access):.1f}m")
    print(f"Range: {np.min(all_veg_access):.1f}m - {np.max(all_veg_access):.1f}m")
    print(f"Standard deviation: {np.std(all_veg_access):.1f}m")
    
    # Current problematic conversion
    print(f"\nCURRENT PROBLEMATIC CONVERSION (treating as percentages):")
    for stat in city_stats[-5:]:  # Show last 5 examples
        distance = stat['mean_distance_m']
        # This is what currently happens - distance treated as percentage
        wrong_percentage = min(100.0, max(0.0, distance))
        print(f"  {stat['city']} ({stat['year']}): {distance:.1f}m → 'capped' at {wrong_percentage:.1f}%")
    
    return city_stats

def propose_vegetation_accessibility_improvements():
    """Propose better methods for converting vegetation distance to vulnerability scores"""
    
    print(f"\nIMPROVED VEGETATION ACCESSIBILITY SCORING")
    print("=" * 50)
    
    city_stats = analyze_vegetation_accessibility()
    if not city_stats:
        return
    
    # Extract latest year data for each city
    latest_data = {}
    for stat in city_stats:
        city = stat['city']
        year = int(stat['year'])
        if city not in latest_data or year > int(latest_data[city]['year']):
            latest_data[city] = stat
    
    print(f"\nPROPOSED SCORING METHODS:")
    print("-" * 30)
    
    distances = [stat['mean_distance_m'] for stat in latest_data.values()]
    
    print(f"\n1. INVERSE DISTANCE METHOD (Better accessibility = closer vegetation)")
    print("   Formula: accessibility_score = max(0, 1 - (distance / max_reasonable_distance))")
    print("   Where max_reasonable_distance = 1000m (10-minute walk)")
    
    max_reasonable_distance = 1000  # 1km as reasonable walking distance
    
    for city, stat in latest_data.items():
        distance = stat['mean_distance_m']
        # Better method: inverse distance scaling
        accessibility_score = max(0.0, 1.0 - (distance / max_reasonable_distance))
        vulnerability_contribution = 1.0 - accessibility_score  # Higher distance = higher vulnerability
        
        print(f"   {city:12}: {distance:5.0f}m → Accessibility: {accessibility_score:.3f}, "
              f"Vulnerability: {vulnerability_contribution:.3f}")
    
    print(f"\n2. PERCENTILE-BASED METHOD (Relative accessibility)")
    print("   Formula: accessibility_score = percentile_rank(distances, inverted)")
    
    # Convert distances to percentile ranks (inverted - shorter distance = higher percentile)
    distances_array = np.array(distances)
    for city, stat in latest_data.items():
        distance = stat['mean_distance_m']
        # Percentile rank but inverted (shorter distances get higher scores)
        percentile = (1.0 - (np.sum(distances_array <= distance) / len(distances_array)))
        vulnerability_contribution = 1.0 - percentile
        
        print(f"   {city:12}: {distance:5.0f}m → Accessibility: {percentile:.3f}, "
              f"Vulnerability: {vulnerability_contribution:.3f}")
    
    print(f"\n3. LOGARITHMIC DECAY METHOD (Gradual accessibility decrease)")
    print("   Formula: accessibility_score = exp(-distance / decay_constant)")
    
    decay_constant = 300  # 300m decay constant
    
    for city, stat in latest_data.items():
        distance = stat['mean_distance_m']
        # Exponential decay model
        accessibility_score = np.exp(-distance / decay_constant)
        vulnerability_contribution = 1.0 - accessibility_score
        
        print(f"   {city:12}: {distance:5.0f}m → Accessibility: {accessibility_score:.3f}, "
              f"Vulnerability: {vulnerability_contribution:.3f}")

def analyze_other_green_space_indicators():
    """Examine other green space metrics that could improve vulnerability assessment"""
    
    print(f"\nOTHER GREEN SPACE INDICATORS FOR VULNERABILITY")
    print("=" * 50)
    
    data = load_spatial_data()
    if not data:
        return
    
    print(f"\nAvailable green space metrics:")
    print("1. Vegetation patch count - Number of separate green areas")
    print("2. Mean patch area - Average size of green spaces")
    print("3. Vegetation patch isolation - Distance between green patches")
    print("4. Built distance stats - How close people are to built areas")
    
    # Analyze latest year for each city
    for city, years_data in data.get('per_year', {}).items():
        years = sorted([int(y) for y in years_data.keys()])
        if not years:
            continue
            
        latest_year = str(years[-1])
        year_data = years_data[latest_year]
        
        print(f"\n--- {city} ({latest_year}) ---")
        
        # Vegetation metrics
        veg_patches = year_data.get('veg_patches', {})
        patch_count = veg_patches.get('patch_count', 0)
        mean_patch_area = veg_patches.get('mean_patch_area_m2', 0)
        
        # Accessibility metrics
        veg_access = year_data.get('vegetation_accessibility', {}).get('city', {}).get('mean', 0)
        veg_isolation = year_data.get('veg_patch_isolation_mean_m', 0)
        
        # Built environment pressure
        built_distance = year_data.get('built_distance_stats', {}).get('city', {}).get('mean', 0)
        
        print(f"  Green space availability:")
        print(f"    Vegetation patches: {patch_count}")
        print(f"    Avg patch size: {mean_patch_area/10000:.1f} hectares")
        print(f"    Distance to vegetation: {veg_access:.0f}m")
        print(f"    Patch isolation: {veg_isolation:.0f}m")
        print(f"  Urban pressure:")
        print(f"    Distance to built areas: {built_distance:.0f}m")
        
        # Calculate comprehensive green space vulnerability
        # Normalize metrics (lower is better for vulnerability)
        patch_density_score = min(1.0, patch_count / 100)  # Normalize by reasonable max
        patch_size_score = min(1.0, (mean_patch_area / 10000) / 50)  # Normalize by 50 hectares
        accessibility_score = max(0.0, 1.0 - (veg_access / 1000))  # 1km max reasonable distance
        connectivity_score = max(0.0, 1.0 - (veg_isolation / 2000))  # 2km max isolation
        
        # Composite green infrastructure score (higher = better green infrastructure)
        green_infra_score = (0.3 * patch_density_score + 0.2 * patch_size_score + 
                           0.3 * accessibility_score + 0.2 * connectivity_score)
        
        # Vulnerability is inverse of green infrastructure quality
        green_vulnerability = 1.0 - green_infra_score
        
        print(f"  Composite scores:")
        print(f"    Green infrastructure quality: {green_infra_score:.3f}")
        print(f"    Green space vulnerability: {green_vulnerability:.3f}")

def recommend_implementation():
    """Provide specific recommendations for improving vulnerability calculation"""
    
    print(f"\nIMPLEMENTATION RECOMMENDATIONS")
    print("=" * 50)
    
    print("""
ISSUE IDENTIFIED:
- Current code treats vegetation accessibility (distance in meters) as percentages
- Values like 334.6m are being interpreted as 334.6% and capped at 100%
- This completely misrepresents the relationship between distance and vulnerability

RECOMMENDED FIXES:

1. IMMEDIATE FIX - Update climate_risk_assessment.py:
   
   Current problematic code:
   veg_access = min(100.0, max(0.0, veg_access))  # Wrong - treats meters as %
   green_vulnerability = max(0.0, 1.0 - (veg_access / 100))  # Wrong division
   
   Corrected code:
   # Convert distance to accessibility score (closer = better)
   max_walking_distance = 1000  # 1km reasonable walking distance
   accessibility_score = max(0.0, 1.0 - (veg_access / max_walking_distance))
   green_vulnerability = 1.0 - accessibility_score  # Further vegetation = higher vulnerability

2. ENHANCED GREEN SPACE VULNERABILITY (Comprehensive method):
   
   def calculate_green_space_vulnerability(self, city: str, spatial_data: dict) -> float:
       # Multiple green space indicators
       patch_count = spatial_data.get('veg_patches', {}).get('patch_count', 0)
       mean_patch_area = spatial_data.get('veg_patches', {}).get('mean_patch_area_m2', 0)
       veg_distance = spatial_data.get('vegetation_accessibility', {}).get('city', {}).get('mean', 1000)
       patch_isolation = spatial_data.get('veg_patch_isolation_mean_m', 2000)
       
       # Convert to vulnerability indicators (0 = best, 1 = worst)
       distance_vuln = min(1.0, veg_distance / 1000)  # 1km max
       isolation_vuln = min(1.0, patch_isolation / 2000)  # 2km max isolation
       quantity_vuln = max(0.0, 1.0 - (patch_count / 100))  # 100 patches ideal
       size_vuln = max(0.0, 1.0 - ((mean_patch_area/10000) / 50))  # 50 hectares ideal
       
       # Weighted combination
       green_vulnerability = (0.4 * distance_vuln + 0.3 * isolation_vuln + 
                            0.2 * quantity_vuln + 0.1 * size_vuln)
       
       return min(1.0, green_vulnerability)

3. VALIDATION BENEFITS:
   - Realistic vulnerability scores based on actual walking distances
   - Cities with distant vegetation (500m+) get appropriate vulnerability scores
   - Cities with close vegetation (100m-) get lower vulnerability
   - Multiple indicators provide robust assessment

4. SCIENTIFIC JUSTIFICATION:
   - 1km walking distance aligns with urban planning guidelines
   - Patch connectivity affects ecosystem services
   - Patch size affects cooling effectiveness
   - Multiple metrics reduce single-indicator bias
""")

if __name__ == "__main__":
    analyze_vegetation_accessibility()
    propose_vegetation_accessibility_improvements() 
    analyze_other_green_space_indicators()
    recommend_implementation()
