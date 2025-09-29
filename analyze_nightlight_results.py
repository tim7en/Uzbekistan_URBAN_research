#!/usr/bin/env python3
"""
Analyze nightlight results for Uzbekistan cities.
Updated to work with the comprehensive merged dataset.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def load_nightlight_data():
    """Load the comprehensive nightlight analysis results."""
    csv_path = "suhi_analysis_output/nightlight_regional_analysis/uzbekistan_nightlight_regional_analysis.csv"
    
    try:
        df = pd.read_csv(csv_path)
        print(f"✅ Loaded nightlight data: {len(df)} records from {df['city'].nunique()} cities")
        print(f"   Years: {df['year'].min()}-{df['year'].max()}")
        return df
    except FileNotFoundError:
        print(f"❌ Data file not found: {csv_path}")
        print("   Please run the nightlight analysis first.")
        return None

def analyze_temporal_trends(df):
    """Analyze temporal trends in nightlight data."""
    
    print("\n🔍 Temporal Trends Analysis")
    print("=" * 50)
    
    # Calculate year-over-year growth rates
    growth_data = []
    
    for city in df['city'].unique():
        city_data = df[df['city'] == city].sort_values('year')
        
        if len(city_data) > 1:
            # Calculate growth rate in city mean radiance
            first_year = city_data.iloc[0]
            last_year = city_data.iloc[-1]
            
            years_span = last_year['year'] - first_year['year']
            radiance_growth = ((last_year['city_mean_radiance'] / first_year['city_mean_radiance']) ** (1/years_span) - 1) * 100
            
            # Calculate growth in lit area
            area_growth = ((last_year['city_lit_area_km2'] / first_year['city_lit_area_km2']) ** (1/years_span) - 1) * 100
            
            growth_data.append({
                'city': city,
                'radiance_annual_growth': radiance_growth,
                'lit_area_annual_growth': area_growth,
                'start_radiance': first_year['city_mean_radiance'],
                'end_radiance': last_year['city_mean_radiance'],
                'start_area': first_year['city_lit_area_km2'],
                'end_area': last_year['city_lit_area_km2']
            })
    
    growth_df = pd.DataFrame(growth_data)
    
    print("📈 Annual Growth Rates (2017-2024):")
    print("\nNightlight Intensity Growth:")
    top_radiance_growth = growth_df.nlargest(5, 'radiance_annual_growth')
    for _, row in top_radiance_growth.iterrows():
        print(f"  {row['city']}: {row['radiance_annual_growth']:.1f}% annually")
    
    print("\nLit Area Expansion:")
    top_area_growth = growth_df.nlargest(5, 'lit_area_annual_growth')
    for _, row in top_area_growth.iterrows():
        print(f"  {row['city']}: {row['lit_area_annual_growth']:.1f}% annually")
    
    return growth_df

def analyze_urban_intensity(df):
    """Analyze urban nightlight intensity patterns."""
    
    print("\n🌆 Urban Intensity Analysis")
    print("=" * 50)
    
    # Calculate average metrics by city
    city_stats = df.groupby('city').agg({
        'city_mean_radiance': 'mean',
        'city_to_regional_background_ratio': 'mean',
        'city_lit_area_km2': 'mean',
        'administrative_region': 'first'
    }).round(1)
    
    city_stats = city_stats.sort_values('city_mean_radiance', ascending=False)
    
    print("🏙️  Top Cities by Mean Nightlight Intensity (2017-2024 average):")
    for i, (city, stats) in enumerate(city_stats.head(10).iterrows(), 1):
        print(f"  {i:2d}. {city:12s}: {stats['city_mean_radiance']:5.1f} nW/cm²/sr (Region: {stats['administrative_region']})")
    
    print("\n🌟 Highest City-to-Regional Contrast (average):")
    city_contrast = city_stats.sort_values('city_to_regional_background_ratio', ascending=False)
    for i, (city, stats) in enumerate(city_contrast.head(5).iterrows(), 1):
        print(f"  {i}. {city}: {stats['city_to_regional_background_ratio']:.1f}x brighter than regional background")
    
    return city_stats

def analyze_regional_patterns(df):
    """Analyze patterns by administrative region."""
    
    print("\n🗺️  Regional Patterns Analysis")
    print("=" * 50)
    
    # Group by administrative region
    regional_stats = df.groupby('administrative_region').agg({
        'city_mean_radiance': ['mean', 'count'],
        'city_to_regional_background_ratio': 'mean',
        'administrative_region_mean_radiance': 'mean'
    }).round(2)
    
    regional_stats.columns = ['avg_city_radiance', 'num_cities', 'avg_contrast_ratio', 'regional_background']
    regional_stats = regional_stats.sort_values('avg_city_radiance', ascending=False)
    
    print("📊 Administrative Regions by Urban Development:")
    for region, stats in regional_stats.iterrows():
        print(f"  {region}")
        print(f"    Cities: {stats['num_cities']}")
        print(f"    Avg City Intensity: {stats['avg_city_radiance']:.1f} nW/cm²/sr")
        print(f"    Avg Contrast Ratio: {stats['avg_contrast_ratio']:.1f}x")
        print(f"    Regional Background: {stats['regional_background']:.2f} nW/cm²/sr")
        print()

def check_data_anomalies(df):
    """Check for data anomalies and interesting patterns."""
    
    print("\n🔍 Data Quality and Anomalies Check")
    print("=" * 50)
    
    # Check for missing data
    missing_data = df.isnull().sum()
    if missing_data.sum() > 0:
        print("⚠️  Missing data found:")
        for col, count in missing_data[missing_data > 0].items():
            print(f"    {col}: {count} missing values")
    else:
        print("✅ No missing data detected")
    
    # Check for extreme values
    print("\n📊 Data Range Summary:")
    print(f"City Mean Radiance: {df['city_mean_radiance'].min():.1f} - {df['city_mean_radiance'].max():.1f} nW/cm²/sr")
    print(f"City-to-Regional Ratio: {df['city_to_regional_background_ratio'].min():.1f}x - {df['city_to_regional_background_ratio'].max():.1f}x")
    print(f"City Lit Area: {df['city_lit_area_km2'].min():.1f} - {df['city_lit_area_km2'].max():.1f} km²")
    
    # Find extreme ratios
    print(f"\n🌟 Extreme Urban-Rural Contrasts:")
    extreme_ratios = df.nlargest(3, 'city_to_regional_background_ratio')
    for _, row in extreme_ratios.iterrows():
        print(f"  {row['city']} ({row['year']}): {row['city_to_regional_background_ratio']:.1f}x ratio")

def create_visualizations(df):
    """Create comprehensive visualizations."""
    
    print("\n📈 Creating Visualizations")
    print("=" * 50)
    
    output_dir = Path("suhi_analysis_output/nightlight_regional_analysis")
    
    # Set style
    plt.style.use('default')
    sns.set_palette("husl")
    
    # Create figure with subplots - increased size for better visibility
    fig, axes = plt.subplots(2, 3, figsize=(24, 16))
    fig.suptitle('Uzbekistan Urban Nightlight Analysis (2017-2024)', fontsize=18, fontweight='bold')
    
    # 1. Time series of top cities
    ax1 = axes[0, 0]
    top_cities = df.groupby('city')['city_mean_radiance'].mean().nlargest(8).index
    
    for city in top_cities:
        city_data = df[df['city'] == city].sort_values('year')
        ax1.plot(city_data['year'], city_data['city_mean_radiance'], 
                marker='o', linewidth=2, label=city)
    
    ax1.set_title('Nightlight Intensity Trends - Top Cities')
    ax1.set_xlabel('Year')
    ax1.set_ylabel('Mean Radiance (nW/cm²/sr)')
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    # 2. City-to-regional ratios heatmap
    ax2 = axes[0, 1]
    pivot_ratios = df.pivot(index='city', columns='year', values='city_to_regional_background_ratio')
    
    # Ensure all cities are visible - use smaller annotation font for better fit
    sns.heatmap(pivot_ratios, annot=True, fmt='.1f', cmap='YlOrRd', ax=ax2,
                cbar_kws={'label': 'City/Regional Ratio'}, annot_kws={'size': 8})
    ax2.set_title('Urban-Rural Contrast Ratios (All 14 Cities)', fontsize=12)
    ax2.set_xlabel('Year')
    ax2.set_ylabel('City')
    # Rotate y-axis labels for better readability
    ax2.set_yticklabels(ax2.get_yticklabels(), rotation=0, fontsize=9)
    
    # 3. Urban area growth
    ax3 = axes[0, 2]
    for city in top_cities:
        city_data = df[df['city'] == city].sort_values('year')
        ax3.plot(city_data['year'], city_data['city_lit_area_km2'], 
                marker='s', linewidth=2, label=city, alpha=0.8)
    
    ax3.set_title('Urban Lit Area Growth')
    ax3.set_xlabel('Year')
    ax3.set_ylabel('Lit Area (km²)')
    ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    # 4. Average intensity by city (bar chart)
    ax4 = axes[1, 0]
    city_means = df.groupby('city')['city_mean_radiance'].mean().sort_values(ascending=True)
    
    bars = ax4.barh(range(len(city_means)), city_means.values, 
                    color=plt.cm.viridis(np.linspace(0, 1, len(city_means))))
    ax4.set_title('Average Nightlight Intensity by City (2017-2024)')
    ax4.set_xlabel('Mean Radiance (nW/cm²/sr)')
    ax4.set_yticks(range(len(city_means)))
    ax4.set_yticklabels(city_means.index)
    ax4.grid(True, alpha=0.3, axis='x')
    
    # Add value labels
    for i, (bar, value) in enumerate(zip(bars, city_means.values)):
        ax4.text(value + 0.5, bar.get_y() + bar.get_height()/2,
                f'{value:.1f}', ha='left', va='center', fontsize=8)
    
    # 5. Scatter: Intensity vs Urban Area
    ax5 = axes[1, 1]
    
    # Use 2024 data for scatter plot
    recent_data = df[df['year'] == 2024]
    
    scatter = ax5.scatter(recent_data['city_lit_area_km2'], 
                         recent_data['city_mean_radiance'],
                         s=100, alpha=0.7, c=recent_data['city_to_regional_background_ratio'],
                         cmap='plasma')
    
    # Add city labels
    for _, row in recent_data.iterrows():
        ax5.annotate(row['city'], (row['city_lit_area_km2'], row['city_mean_radiance']),
                    xytext=(5, 5), textcoords='offset points', fontsize=8)
    
    ax5.set_title('Urban Intensity vs Area (2024)')
    ax5.set_xlabel('Lit Area (km²)')
    ax5.set_ylabel('Mean Radiance (nW/cm²/sr)')
    ax5.grid(True, alpha=0.3)
    
    # Add colorbar for scatter plot
    cbar = plt.colorbar(scatter, ax=ax5)
    cbar.set_label('City/Regional Ratio')
    
    # 6. Regional comparison
    ax6 = axes[1, 2]
    
    # Group by region and calculate stats
    regional_summary = df.groupby('administrative_region').agg({
        'city_mean_radiance': 'mean',
        'administrative_region_mean_radiance': 'mean'
    }).sort_values('city_mean_radiance', ascending=True)
    
    x_pos = np.arange(len(regional_summary))
    
    # Create grouped bar chart
    width = 0.35
    bars1 = ax6.barh(x_pos - width/2, regional_summary['city_mean_radiance'], 
                     width, label='City Average', alpha=0.8)
    bars2 = ax6.barh(x_pos + width/2, regional_summary['administrative_region_mean_radiance'], 
                     width, label='Regional Background', alpha=0.8)
    
    ax6.set_title('City vs Regional Background Comparison')
    ax6.set_xlabel('Mean Radiance (nW/cm²/sr)')
    ax6.set_yticks(x_pos)
    ax6.set_yticklabels([name.replace(' Region', '').replace(' City', '') 
                        for name in regional_summary.index], fontsize=8)
    ax6.legend()
    ax6.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    
    # Save visualization
    output_file = output_dir / 'detailed_nightlight_analysis.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"📊 Detailed visualizations saved: {output_file}")

def main():
    """Main analysis function."""
    
    print("🌃 Uzbekistan Nightlight Results Analysis")
    print("=" * 60)
    
    # Load data
    df = load_nightlight_data()
    if df is None:
        return
    
    # Perform analyses
    growth_stats = analyze_temporal_trends(df)
    city_stats = analyze_urban_intensity(df)
    analyze_regional_patterns(df)
    check_data_anomalies(df)
    create_visualizations(df)
    
    print("\n✅ Analysis Complete!")
    print("📊 Check the output directory for visualizations and reports")

if __name__ == "__main__":
    main()