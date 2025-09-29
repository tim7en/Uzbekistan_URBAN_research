"""Quick analysis summary for Uzbekistan Regional Nightlight Analysis results.

This script reads the CSV results and provides quick insights and summary statistics.
"""
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

def analyze_results(csv_path: Path):
    """Analyze the nightlight regional analysis results."""
    
    # Read the CSV data
    df = pd.read_csv(csv_path)
    
    print("🌃 Uzbekistan City-Centered Nightlight Analysis - Quick Summary")
    print("=" * 60)
    print(f"📊 Data loaded: {len(df)} records")
    print(f"🏙️ Cities analyzed: {', '.join(df['city'].unique())}")
    print(f"📅 Years covered: {df['year'].min()}-{df['year'].max()}")
    print(f"🗺️ Analysis types: City-centered circular zones")
    
    print("\n💡 Key Insights:")
    print("-" * 30)
    
    # Latest year insights
    latest_year = df['year'].max()
    latest_data = df[df['year'] == latest_year].sort_values('city_to_regional_background_ratio', ascending=False)
    
    print(f"\n🏆 City-to-Background Ratios ({latest_year}):")
    for _, row in latest_data.iterrows():
        ratio = row['city_to_regional_background_ratio']
        city_radiance = row['city_mean_radiance']
        background_radiance = row['regional_background_mean_radiance']
        city_radius = row['city_radius_km']
        admin_region = row['administrative_region']
        
        print(f"  {row['city']:<10}: {ratio:.2f}x")
        print(f"    {'':>2}City radiance: {city_radiance:.1f} nW/cm²/sr")
        print(f"    {'':>2}Background: {background_radiance:.1f} nW/cm²/sr")
        print(f"    {'':>2}Administrative region: {admin_region}")
        print(f"    {'':>2}City analysis zone: {city_radius:.1f}km radius circular buffer")
        print()
    
    # Growth trends
    print(f"📈 Temporal Changes:")
    cities = df['city'].unique()
    
    for city in cities:
        city_data = df[df['city'] == city].sort_values('year')
        if len(city_data) >= 2:
            first_ratio = city_data.iloc[0]['city_to_regional_background_ratio']
            last_ratio = city_data.iloc[-1]['city_to_regional_background_ratio']
            change = last_ratio - first_ratio
            change_pct = (change / first_ratio) * 100 if first_ratio != 0 else 0
            
            trend_symbol = "📈" if change > 0 else "📉" if change < 0 else "📊"
            print(f"  {city:<10}: {first_ratio:.2f} → {last_ratio:.2f} {trend_symbol} ({change:+.2f}, {change_pct:+.1f}%)")
    
    # Urban intensity analysis
    print(f"\n🌆 Urban Intensity Analysis ({latest_year}):")
    for _, row in latest_data.iterrows():
        city_lit_area = row['city_lit_area_km2']
        background_lit_area = row['regional_background_lit_area_km2']
        city_area = row['city_area_km2']  # Now provided directly
        admin_region_area = row.get('administrative_region_lit_area_km2', 0)
        
        city_lit_pct = (city_lit_area / city_area) * 100 if city_area > 0 else 0
        # Background area calculation not needed for admin regions
        
        print(f"  {row['city']:<10}:")
        print(f"    {'':>2}City lit coverage: {city_lit_pct:.1f}% ({city_lit_area:.1f} km²)")
        print(f"    {'':>2}Regional background lit area: {background_lit_area:.1f} km²")
    
    # Comparative analysis
    print(f"\n🔍 Comparative Metrics:")
    avg_city_radiance = latest_data['city_mean_radiance'].mean()
    avg_background_radiance = latest_data['regional_background_mean_radiance'].mean()
    avg_ratio = latest_data['city_to_regional_background_ratio'].mean()
    
    print(f"  Average city radiance: {avg_city_radiance:.1f} nW/cm²/sr")
    print(f"  Average background radiance: {avg_background_radiance:.1f} nW/cm²/sr")
    print(f"  Average city-to-background ratio: {avg_ratio:.2f}x")
    
    # Identify outliers
    print(f"\n🎯 Urban Development Insights:")
    highest_ratio_city = latest_data.iloc[0]
    lowest_ratio_city = latest_data.iloc[-1]
    
    print(f"  🥇 Highest urban concentration: {highest_ratio_city['city']} ({highest_ratio_city['city_to_regional_background_ratio']:.2f}x)")
    print(f"     - Strong urban center in {highest_ratio_city['administrative_region']}")
    
    print(f"  🌿 More distributed development: {lowest_ratio_city['city']} ({lowest_ratio_city['city_to_regional_background_ratio']:.2f}x)")
    print(f"     - More balanced urban-rural radiance distribution")
    
    # Zone size analysis
    print(f"\n🗺️ Analysis Zone Characteristics ({latest_year}):")
    for _, row in latest_data.iterrows():
        city_area = row['city_area_km2']
        admin_region = row['administrative_region']
        
        print(f"  {row['city']} ({admin_region}):")
        print(f"    City area: {city_area:.0f}km² (circular buffer)")
        print(f"    Administrative region: {admin_region}")
    
    print(f"\n📋 Data Quality:")
    print(f"  Total city-years analyzed: {len(df)}")
    print(f"  Average city analysis radius: {df['city_radius_km'].mean():.1f}km")
    print(f"  Analysis approach: City buffers + administrative regions")


def create_quick_visualization(csv_path: Path, output_dir: Path):
    """Create a quick visualization of the results."""
    
    df = pd.read_csv(csv_path)
    
    # Set up the plot style
    plt.style.use('default')
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Uzbekistan Regional Nightlight Analysis - City vs Administrative Region', fontsize=16, fontweight='bold')
    
    # Plot 1: City-to-Background Ratios Over Time
    cities = df['city'].unique()
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9', '#F8C471', '#82E0AA', '#F1948A', '#AED6F1']
    
    for i, city in enumerate(cities):
        city_data = df[df['city'] == city].sort_values('year')
        color = colors[i % len(colors)]
        axes[0, 0].plot(city_data['year'], city_data['city_to_regional_background_ratio'], 
                       marker='o', label=city, linewidth=2, color=color)
    
    axes[0, 0].set_title('City-to-Regional Background Radiance Ratios Over Time')
    axes[0, 0].set_xlabel('Year')
    axes[0, 0].set_ylabel('City/Regional Background Ratio')
    axes[0, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    axes[0, 0].grid(True, alpha=0.3)
    
    # Plot 2: Latest Year Comparison
    latest_year = df['year'].max()
    latest_data = df[df['year'] == latest_year].sort_values('city_to_regional_background_ratio', ascending=True)
    
    bars = axes[0, 1].bar(latest_data['city'], latest_data['city_to_regional_background_ratio'], 
                         color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'][:len(latest_data)])
    axes[0, 1].set_title(f'City-to-Regional Background Ratios ({latest_year})')
    axes[0, 1].set_xlabel('City')
    axes[0, 1].set_ylabel('City/Regional Background Ratio')
    axes[0, 1].tick_params(axis='x', rotation=45)
    axes[0, 1].grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        axes[0, 1].text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{height:.1f}', ha='center', va='bottom')
    
    # Plot 3: Mean Radiance Comparison
    for i, city in enumerate(cities):
        city_data = df[df['city'] == city].sort_values('year')
        color = colors[i % len(colors)]
        axes[1, 0].plot(city_data['year'], city_data['city_mean_radiance'], 
                       marker='o', label=f'{city} (City)', linewidth=2, color=color)
        axes[1, 0].plot(city_data['year'], city_data['regional_background_mean_radiance'], 
                       marker='s', label=f'{city} (Regional Bkg)', linewidth=1, 
                       linestyle='--', color=color, alpha=0.7)
    
    axes[1, 0].set_title('Mean Radiance: City vs Regional Background')
    axes[1, 0].set_xlabel('Year')
    axes[1, 0].set_ylabel('Mean Radiance (nW/cm²/sr)')
    axes[1, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    axes[1, 0].grid(True, alpha=0.3)
    
    # Plot 4: Lit Area Comparison
    for i, city in enumerate(cities):
        city_data = df[df['city'] == city].sort_values('year')
        color = colors[i % len(colors)]
        axes[1, 1].plot(city_data['year'], city_data['city_lit_area_km2'], 
                       marker='o', label=city, linewidth=2, color=color)
    
    axes[1, 1].set_title('City Lit Area Over Time')
    axes[1, 1].set_xlabel('Year')
    axes[1, 1].set_ylabel('Lit Area (km²)')
    axes[1, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save the plot
    output_file = output_dir / 'quick_analysis_overview.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"📊 Quick visualization saved: {output_file}")


def main():
    """Main function to run quick analysis."""
    
    # Define paths
    results_dir = Path("suhi_analysis_output/nightlight_regional_analysis")
    csv_file = results_dir / "uzbekistan_nightlight_regional_analysis.csv"
    
    if not csv_file.exists():
        print("❌ Results file not found. Please run the main analysis first:")
        print("   python run_uzbekistan_nightlight_regional_analysis.py")
        return 1
    
    # Run analysis
    analyze_results(csv_file)
    
    # Create visualization
    print(f"\n📈 Creating quick visualization...")
    create_quick_visualization(csv_file, results_dir)
    
    print(f"\n" + "=" * 60)
    print(f"✅ Quick analysis complete!")
    print(f"📁 Full results available in: {results_dir}")
    print(f"📄 Detailed report: {results_dir / 'uzbekistan_nightlight_regional_summary.md'}")
    
    return 0


if __name__ == '__main__':
    exit(main())