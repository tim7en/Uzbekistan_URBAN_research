"""
Diagnostic script to analyze why Samarkand has such high adaptive capacity
Examines the components: economic capacity, green capacity, and size capacity
"""

import pandas as pd
import numpy as np
from pathlib import Path
from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService


def analyze_adaptive_capacity_components():
    """Analyze adaptive capacity components for all cities, focusing on Samarkand"""
    
    # Load data using same path detection
    repo_root = Path(__file__).resolve().parent
    candidates = [
        repo_root / "suhi_analysis_output",
        repo_root / "reports",
        Path.cwd() / "suhi_analysis_output", 
        Path.cwd() / "reports",
        repo_root
    ]
    
    base_path = None
    for c in candidates:
        if c.exists():
            base_path = c
            break
    
    if base_path is None:
        base_path = repo_root
        print(f"Warning: no suhi_analysis_output/reports folder found; using repo root: {base_path}")
    else:
        print(f"Using data base_path: {base_path}")
    
    # Initialize services
    data_loader = ClimateDataLoader(str(base_path))
    risk_assessor = IPCCRiskAssessmentService(data_loader)
    
    # Load data
    data = data_loader.load_all_data()
    
    print("\n" + "="*100)
    print("ADAPTIVE CAPACITY COMPONENT ANALYSIS")
    print("="*100)
    
    print(f"\nADAPTIVE CAPACITY FORMULA:")
    print(f"  AC = 0.5 × Economic_Capacity + 0.3 × Green_Capacity + 0.2 × Size_Capacity")
    print(f"  Where:")
    print(f"    - Economic_Capacity = percentile_norm(GDP_per_capita)")
    print(f"    - Green_Capacity = 0.7 × (veg_access/100) + 0.3 × percentile_norm(veg_patches)")
    print(f"    - Size_Capacity = percentile_norm(population)")
    
    # Analyze each city's components
    cities = list(data['population_data'].keys())
    analysis_data = []
    
    for city in cities:
        population_data = data['population_data'].get(city)
        if not population_data:
            continue
            
        # Economic component
        economic_capacity = data_loader.pct_norm(
            data['cache']['gdp'], 
            population_data.gdp_per_capita_usd
        )
        
        # Green infrastructure component
        green_capacity = 0.0
        veg_access = 0.0
        veg_access_capped = 0.0
        veg_patches = 0
        spatial_city_data = data['spatial_data'].get('per_year', {}).get(city, {})
        if spatial_city_data:
            years = sorted([int(y) for y in spatial_city_data.keys()])
            if years:
                latest_year = str(years[-1])
                veg_access = spatial_city_data[latest_year].get('vegetation_accessibility', {}).get('city', {}).get('mean', 0)
                veg_patches = spatial_city_data[latest_year].get('veg_patches', {}).get('patch_count', 0)
                
                # Cap vegetation access at 100% to ensure realistic percentages (0-100% range)
                veg_access_capped = min(100.0, max(0.0, veg_access))
                
                green_capacity = (veg_access_capped / 100) * 0.7 + data_loader.pct_norm(
                    data['cache']['veg_patches'], veg_patches
                ) * 0.3
        
        # Size component
        size_capacity = data_loader.pct_norm(
            data['cache']['population'], 
            population_data.population_2024
        )
        
        # Final adaptive capacity
        adaptive_capacity = (0.5 * economic_capacity + 0.3 * green_capacity + 
                           0.2 * size_capacity)
        adaptive_capacity = min(1.0, adaptive_capacity)
        
        analysis_data.append({
            'City': city,
            'Population': population_data.population_2024,
            'GDP_per_capita_USD': population_data.gdp_per_capita_usd,
            'Veg_Access_Pct': veg_access,
            'Veg_Access_Capped_Pct': veg_access_capped,
            'Veg_Patches': veg_patches,
            'Economic_Capacity': economic_capacity,
            'Green_Capacity': green_capacity,
            'Size_Capacity': size_capacity,
            'Total_Adaptive_Capacity': adaptive_capacity
        })
    
    df = pd.DataFrame(analysis_data)
    df = df.sort_values('Total_Adaptive_Capacity', ascending=False)
    
    # Display cache ranges for context
    print(f"\nDATA RANGES (for percentile normalization):")
    print(f"  GDP per capita: {min(data['cache']['gdp']):.0f} - {max(data['cache']['gdp']):.0f} USD")
    print(f"  Population: {min(data['cache']['population']):,} - {max(data['cache']['population']):,}")
    print(f"  Vegetation patches: {min(data['cache']['veg_patches'])} - {max(data['cache']['veg_patches'])}")
    
    print(f"\nTOP 5 CITIES BY ADAPTIVE CAPACITY:")
    display_cols = ['City', 'Total_Adaptive_Capacity', 'Economic_Capacity', 'Green_Capacity', 
                   'Size_Capacity', 'GDP_per_capita_USD', 'Population', 'Veg_Access_Pct', 'Veg_Access_Capped_Pct']
    print(df[display_cols].head().to_string(index=False, float_format='%.3f'))
    
    # Focus on Samarkand
    samarkand_data = df[df['City'] == 'Samarkand']
    if not samarkand_data.empty:
        sam = samarkand_data.iloc[0]
        print(f"\nSAMARKAND DETAILED BREAKDOWN:")
        print(f"  Total Adaptive Capacity: {sam['Total_Adaptive_Capacity']:.3f}")
        print(f"  Economic Capacity: {sam['Economic_Capacity']:.3f} (Weight: 0.5)")
        print(f"    -> GDP per capita: ${sam['GDP_per_capita_USD']:,.0f}")
        print(f"    -> GDP rank: {df['GDP_per_capita_USD'].rank(ascending=False)[samarkand_data.index[0]]:.0f}/{len(df)}")
        print(f"  Green Capacity: {sam['Green_Capacity']:.3f} (Weight: 0.3)")
        print(f"    -> Vegetation access (raw): {sam['Veg_Access_Pct']:.1f}%")
        print(f"    -> Vegetation access (capped): {sam['Veg_Access_Capped_Pct']:.1f}%")
        print(f"    -> Vegetation patches: {sam['Veg_Patches']}")
        print(f"  Size Capacity: {sam['Size_Capacity']:.3f} (Weight: 0.2)")
        print(f"    -> Population: {sam['Population']:,}")
        print(f"    -> Population rank: {df['Population'].rank(ascending=False)[samarkand_data.index[0]]:.0f}/{len(df)}")
        
        # Manual calculation verification
        manual_ac = (0.5 * sam['Economic_Capacity'] + 0.3 * sam['Green_Capacity'] + 
                    0.2 * sam['Size_Capacity'])
        print(f"  Manual calculation: 0.5×{sam['Economic_Capacity']:.3f} + 0.3×{sam['Green_Capacity']:.3f} + 0.2×{sam['Size_Capacity']:.3f} = {manual_ac:.3f}")
    
    # Compare with other high-capacity cities
    print(f"\nCOMPARISON WITH OTHER HIGH-CAPACITY CITIES:")
    top_3 = df.head(3)
    for _, row in top_3.iterrows():
        if row['City'] != 'Samarkand':
            print(f"  {row['City']}: AC={row['Total_Adaptive_Capacity']:.3f}, GDP=${row['GDP_per_capita_USD']:,.0f}, Pop={row['Population']:,}")
    
    # Check for data anomalies
    print(f"\nPOTENTIAL DATA ISSUES:")
    
    # Check for perfect scores
    perfect_scores = df[df['Total_Adaptive_Capacity'] >= 0.999]
    if not perfect_scores.empty:
        print(f"  Cities with perfect/near-perfect adaptive capacity:")
        for _, row in perfect_scores.iterrows():
            print(f"    {row['City']}: {row['Total_Adaptive_Capacity']:.3f}")
    
    # Check for extreme GDP values
    gdp_max = df['GDP_per_capita_USD'].max()
    gdp_median = df['GDP_per_capita_USD'].median()
    if gdp_max > 2 * gdp_median:
        extreme_gdp = df[df['GDP_per_capita_USD'] > 1.5 * gdp_median]
        print(f"  Cities with unusually high GDP per capita (>1.5× median):")
        for _, row in extreme_gdp.iterrows():
            print(f"    {row['City']}: ${row['GDP_per_capita_USD']:,.0f} (median: ${gdp_median:,.0f})")
    
    # Save detailed breakdown
    output_file = base_path / "climate_assessment" / "adaptive_capacity_breakdown.csv"
    df.to_csv(output_file, index=False)
    print(f"\n✓ Saved detailed breakdown to: {output_file}")
    
    print("="*100)
    
    return df


if __name__ == "__main__":
    analyze_adaptive_capacity_components()
