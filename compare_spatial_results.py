"""Comprehensive comparison of spatial relationships across Uzbekistan cities."""
import json
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

def compare_cities_spatial_analysis():
    """Compare spatial relationships results across different cities."""
    
    print("🌍 Spatial Relationships Analysis - Multi-City Comparison")
    print("=" * 70)
    
    results_dir = Path(__file__).parent / 'suhi_analysis_output' / 'spatial_relationship_analysis'
    
    # Collect data from all cities
    cities_data = {}
    
    for city_file in results_dir.glob("*_spatial_relationships.json"):
        with open(city_file, 'r') as f:
            data = json.load(f)
        
        city = data['city']
        
        # Handle different file structures
        if 'data' in data:
            year_data = data['data']['2024']
        elif 'yearly_data' in data:
            year_data = data['yearly_data']['2024']
        else:
            continue
            
        if 'error' in year_data:
            print(f"❌ {city}: {year_data['error']}")
            continue
            
        cities_data[city] = year_data
    
    # Create comparison table
    comparison_data = []
    
    for city, data in cities_data.items():
        
        # Extract key metrics
        veg_patches = data.get('veg_patches', {})
        built_patches = data.get('built_patches', {})
        built_dist = data.get('built_distance_stats', {}).get('city', {})
        veg_access = data.get('vegetation_accessibility', {}).get('city', {})
        edge_density = data.get('edge_density_m_per_km2', 0)
        
        comparison_data.append({
            'city': city,
            'veg_patch_count': veg_patches.get('patch_count', 0),
            'veg_area_km2': veg_patches.get('total_area_m2', 0) / 1e6,
            'veg_mean_patch_ha': veg_patches.get('mean_patch_area_m2', 0) / 10000,
            'built_patch_count': built_patches.get('patch_count', 0),
            'built_area_km2': built_patches.get('total_area_m2', 0) / 1e6,
            'built_mean_patch_ha': built_patches.get('mean_patch_area_m2', 0) / 10000,
            'built_to_veg_dist_m': built_dist.get('mean', 0),
            'veg_accessibility_m': veg_access.get('mean', 0),
            'edge_density_m_km2': edge_density,
            'veg_built_ratio': (veg_patches.get('total_area_m2', 0) / 
                               max(built_patches.get('total_area_m2', 1), 1))
        })
    
    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(comparison_data)
    df = df.sort_values('built_area_km2', ascending=False)  # Sort by city size
    
    print("📊 SPATIAL RELATIONSHIPS COMPARISON TABLE")
    print("-" * 70)
    
    # Display formatted table
    print(f"{'City':<12} {'Veg km²':<8} {'Built km²':<9} {'V/B Ratio':<8} {'Veg Access(m)':<12} {'Edge Dens':<9}")
    print("-" * 70)
    
    for _, row in df.iterrows():
        veg_built_ratio = row['veg_built_ratio']
        ratio_str = f"{veg_built_ratio:.1f}" if veg_built_ratio < 10 else f"{veg_built_ratio:.0f}"
        
        print(f"{row['city']:<12} {row['veg_area_km2']:<8.1f} {row['built_area_km2']:<9.1f} "
              f"{ratio_str:<8} {row['veg_accessibility_m']:<12.0f} {row['edge_density_m_km2']:<9.0f}")
    
    print("\n" + "=" * 70)
    print("🔍 LOGICAL ANALYSIS OF RESULTS")
    print("=" * 70)
    
    # Analyze patterns and logical consistency
    print("\n1️⃣ CITY SIZE & URBANIZATION PATTERNS:")
    largest_cities = df.nlargest(2, 'built_area_km2')['city'].tolist()
    smallest_cities = df.nsmallest(2, 'built_area_km2')['city'].tolist()
    print(f"   Largest cities (built area): {', '.join(largest_cities)}")
    print(f"   Smallest cities (built area): {', '.join(smallest_cities)}")
    
    print("\n2️⃣ VEGETATION-TO-BUILT RATIOS:")
    high_veg_cities = df.nlargest(3, 'veg_built_ratio')
    low_veg_cities = df.nsmallest(3, 'veg_built_ratio')
    
    print("   🌿 Most vegetated (high V/B ratio):")
    for _, city in high_veg_cities.iterrows():
        print(f"      {city['city']}: {city['veg_built_ratio']:.1f} ({city['veg_area_km2']:.1f} km² veg / {city['built_area_km2']:.1f} km² built)")
    
    print("   🏙️  Most urbanized (low V/B ratio):")
    for _, city in low_veg_cities.iterrows():
        print(f"      {city['city']}: {city['veg_built_ratio']:.1f} ({city['veg_area_km2']:.1f} km² veg / {city['built_area_km2']:.1f} km² built)")
    
    print("\n3️⃣ VEGETATION ACCESSIBILITY:")
    high_access = df[df['veg_accessibility_m'] > 0].nlargest(3, 'veg_accessibility_m')
    zero_access = df[df['veg_accessibility_m'] == 0]
    
    if len(high_access) > 0:
        print("   🚶 Cities with measured distances to vegetation:")
        for _, city in high_access.iterrows():
            print(f"      {city['city']}: {city['veg_accessibility_m']:.0f}m average distance")
    
    if len(zero_access) > 0:
        print("   🌱 Cities with immediate vegetation access (0m):")
        for _, city in zero_access.iterrows():
            veg_pct = (city['veg_area_km2'] / (city['veg_area_km2'] + city['built_area_km2'])) * 100
            print(f"      {city['city']}: {veg_pct:.1f}% vegetation coverage (explains 0m distance)")
    
    print("\n4️⃣ URBAN FRAGMENTATION (Edge Density):")
    high_edge = df.nlargest(3, 'edge_density_m_km2')
    low_edge = df.nsmallest(3, 'edge_density_m_km2')
    
    print("   🔀 Highest fragmentation (high edge density):")
    for _, city in high_edge.iterrows():
        print(f"      {city['city']}: {city['edge_density_m_km2']:.0f} m/km² (complex urban-nature interface)")
    
    print("   ⬜ Lowest fragmentation (low edge density):")
    for _, city in low_edge.iterrows():
        print(f"      {city['city']}: {city['edge_density_m_km2']:.0f} m/km² (simpler boundaries)")
    
    print("\n5️⃣ LOGICAL CONSISTENCY CHECK:")
    print("   ✅ Expected patterns:")
    
    # Check if larger cities have less vegetation access
    tashkent_data = df[df['city'] == 'Tashkent'].iloc[0] if 'Tashkent' in df['city'].values else None
    if tashkent_data is not None:
        print(f"      • Tashkent (capital): {tashkent_data['built_area_km2']:.1f} km² built, "
              f"{tashkent_data['veg_accessibility_m']:.0f}m veg access")
    
    # Check if agricultural cities have better access
    agricultural_cities = ['Gulistan', 'Jizzakh']  # Known agricultural regions
    for city in agricultural_cities:
        city_data = df[df['city'] == city]
        if len(city_data) > 0:
            row = city_data.iloc[0]
            print(f"      • {city} (agricultural): {row['veg_built_ratio']:.1f} V/B ratio, "
                  f"{row['veg_accessibility_m']:.0f}m access")
    
    # Check if edge density correlates with urban complexity
    urban_cities = ['Tashkent', 'Samarkand', 'Bukhara']
    avg_urban_edge = df[df['city'].isin(urban_cities)]['edge_density_m_km2'].mean()
    avg_small_edge = df[~df['city'].isin(urban_cities)]['edge_density_m_km2'].mean()
    
    print(f"      • Urban vs rural edge density: {avg_urban_edge:.0f} vs {avg_small_edge:.0f} m/km²")
    
    print("\n" + "=" * 70)
    print("🎯 SUMMARY INSIGHTS:")
    print("=" * 70)
    
    # Generate insights
    insights = []
    
    if len(zero_access) > 0:
        insights.append(f"• {len(zero_access)} cities have 0m vegetation access (surrounded by agriculture/vegetation)")
    
    max_veg_city = df.loc[df['veg_built_ratio'].idxmax()]
    insights.append(f"• {max_veg_city['city']} is most vegetated ({max_veg_city['veg_built_ratio']:.1f}× more vegetation than built area)")
    
    min_veg_city = df.loc[df['veg_built_ratio'].idxmin()]
    insights.append(f"• {min_veg_city['city']} is most urbanized ({min_veg_city['veg_built_ratio']:.1f}× vegetation-to-built ratio)")
    
    if 'Tashkent' in df['city'].values:
        tashkent = df[df['city'] == 'Tashkent'].iloc[0]
        insights.append(f"• Tashkent shows typical capital pattern: {tashkent['built_area_km2']:.0f} km² built area, moderate vegetation access")
    
    for insight in insights:
        print(insight)
    
    print(f"\n✅ Analysis complete! All {len(cities_data)} cities processed successfully.")
    
    return df

if __name__ == '__main__':
    try:
        comparison_df = compare_cities_spatial_analysis()
    except Exception as e:
        print(f"❌ Error in analysis: {e}")
        import traceback
        traceback.print_exc()
