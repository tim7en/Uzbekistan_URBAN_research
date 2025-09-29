"""Simple analysis summary for the new city-centered nightlight results."""
import pandas as pd
from pathlib import Path

def analyze_city_centered_results():
    """Analyze the new city-centered nightlight analysis results."""
    
    # Read the CSV data
    results_dir = Path("suhi_analysis_output/nightlight_regional_analysis")
    csv_file = results_dir / "uzbekistan_nightlight_regional_analysis.csv"
    
    if not csv_file.exists():
        print("❌ Results file not found. Please run the main analysis first.")
        return
    
    df = pd.read_csv(csv_file)
    
    print("🌃 Uzbekistan City-Centered Nightlight Analysis - Summary")
    print("=" * 60)
    print(f"📊 Data loaded: {len(df)} records")
    print(f"🏙️ Cities analyzed: {', '.join(df['city'].unique())}")
    print(f"📅 Years covered: {df['year'].min()}-{df['year'].max()}")
    
    print("\n💡 Key Insights from City-Centered Analysis:")
    print("-" * 45)
    
    # Latest year insights
    latest_year = df['year'].max()
    latest_data = df[df['year'] == latest_year].sort_values('city_to_background_ratio', ascending=False)
    
    print(f"\n🏆 City-to-Background Ratios ({latest_year}):")
    for _, row in latest_data.iterrows():
        ratio = row['city_to_background_ratio']
        city_radiance = row['city_mean_radiance']
        background_radiance = row['background_mean_radiance']
        city_radius = row['city_radius_km']
        region_radius = row['region_radius_km']
        
        print(f"  {row['city']:<10}: {ratio:.2f}x")
        print(f"    {'':>2}City radiance: {city_radiance:.1f} nW/cm²/sr")
        print(f"    {'':>2}Background: {background_radiance:.1f} nW/cm²/sr")
        print(f"    {'':>2}Analysis zones: {city_radius:.1f}km city → {region_radius:.1f}km region")
        print()
    
    # Growth trends
    print(f"📈 Temporal Changes:")
    cities = df['city'].unique()
    
    for city in cities:
        city_data = df[df['city'] == city].sort_values('year')
        if len(city_data) >= 2:
            first_ratio = city_data.iloc[0]['city_to_background_ratio']
            last_ratio = city_data.iloc[-1]['city_to_background_ratio']
            change = last_ratio - first_ratio
            change_pct = (change / first_ratio) * 100 if first_ratio != 0 else 0
            
            trend_symbol = "📈" if change > 0 else "📉" if change < 0 else "📊"
            print(f"  {city:<10}: {first_ratio:.2f} → {last_ratio:.2f} {trend_symbol} ({change:+.2f}, {change_pct:+.1f}%)")
    
    # Analysis zone comparison
    print(f"\n🗺️ Analysis Zone Characteristics ({latest_year}):")
    for _, row in latest_data.iterrows():
        city_area = 3.14159 * (row['city_radius_km'] ** 2)
        region_area = 3.14159 * (row['region_radius_km'] ** 2)
        background_area = region_area - city_area
        
        city_lit = row['city_lit_area_km2']
        background_lit = row['background_lit_area_km2']
        
        print(f"  {row['city']}:")
        print(f"    Zone areas: City {city_area:.0f}km², Background {background_area:.0f}km²")
        print(f"    Lit areas:  City {city_lit:.0f}km², Background {background_lit:.0f}km²")
        if city_area > 0:
            city_lit_pct = (city_lit / city_area) * 100
            print(f"    City lit coverage: {city_lit_pct:.1f}%")
    
    # Comparative analysis
    print(f"\n🔍 Comparative Metrics:")
    avg_city_radiance = latest_data['city_mean_radiance'].mean()
    avg_background_radiance = latest_data['background_mean_radiance'].mean()
    avg_ratio = latest_data['city_to_background_ratio'].mean()
    
    print(f"  Average city radiance: {avg_city_radiance:.1f} nW/cm²/sr")
    print(f"  Average background radiance: {avg_background_radiance:.1f} nW/cm²/sr")
    print(f"  Average city-to-background ratio: {avg_ratio:.2f}x")
    
    # Urban intensity insights
    print(f"\n🎯 Urban Development Insights:")
    highest_ratio_city = latest_data.iloc[0]
    lowest_ratio_city = latest_data.iloc[-1]
    
    print(f"  🥇 Highest urban concentration: {highest_ratio_city['city']} ({highest_ratio_city['city_to_background_ratio']:.2f}x)")
    print(f"     - Strong urban center with distinct radiance profile")
    
    print(f"  🌿 More distributed development: {lowest_ratio_city['city']} ({lowest_ratio_city['city_to_background_ratio']:.2f}x)")
    print(f"     - More balanced urban-rural radiance distribution")
    
    print(f"\n📋 Data Quality:")
    print(f"  Total city-years analyzed: {len(df)}")
    print(f"  Average regional analysis radius: {df['region_radius_km'].mean():.1f}km")
    print(f"  Analysis approach: City-centered circular zones")
    
    print(f"\n✅ Analysis complete!")
    print(f"📁 Detailed results: {csv_file}")
    print(f"📄 Full report: {results_dir / 'uzbekistan_nightlight_regional_summary.md'}")


if __name__ == '__main__':
    analyze_city_centered_results()