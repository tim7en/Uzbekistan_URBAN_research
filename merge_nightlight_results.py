#!/usr/bin/env python3
"""
Merge individual nightlight analysis JSON files into comprehensive CSV and generate analysis report.
"""

import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
from datetime import datetime

def load_all_nightlight_data(base_dir):
    """Load all individual JSON files from city folders."""
    
    results = []
    base_path = Path(base_dir)
    
    print("🔍 Scanning for nightlight analysis files...")
    
    # Find all city directories
    city_dirs = [d for d in base_path.iterdir() if d.is_dir() and d.name not in ['thumbnails']]
    
    for city_dir in city_dirs:
        city_name = city_dir.name
        print(f"  📂 Processing {city_name}...")
        
        # Find all JSON files in this city directory
        json_files = list(city_dir.glob("*_analysis.json"))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract data into flat structure for CSV
                row = {
                    'city': data['city'],
                    'year': data['year'],
                    'administrative_region': data['region_name'],
                    'analysis_approach': data['analysis_approach'],
                    'city_radius_km': data['city_radius_km'],
                    'city_area_km2': data['city_area_km2'],
                    
                    # City stats
                    'city_mean_radiance': data['city_stats']['mean'],
                    'city_median_radiance': data['city_stats']['median'],
                    'city_stddev_radiance': data['city_stats']['stdDev'],
                    'city_lit_area_km2': data['city_stats']['lit_area_km2'],
                    
                    # City buffer stats
                    'city_buffer_mean_radiance': data['city_buffer_stats']['mean'],
                    'city_buffer_lit_area_km2': data['city_buffer_stats']['lit_area_km2'],
                    
                    # Administrative region stats
                    'administrative_region_mean_radiance': data['region_stats']['mean'],
                    'administrative_region_median_radiance': data['region_stats']['median'],
                    'administrative_region_stddev_radiance': data['region_stats']['stdDev'],
                    'administrative_region_lit_area_km2': data['region_stats']['lit_area_km2'],
                    
                    # Regional background stats
                    'regional_background_mean_radiance': data['regional_background_stats']['mean'],
                    'regional_background_median_radiance': data['regional_background_stats']['median'],
                    'regional_background_lit_area_km2': data['regional_background_stats']['lit_area_km2'],
                    
                    # Ratios and differences
                    'city_to_regional_background_ratio': data['city_to_region_ratio'],
                    'city_to_full_administrative_region_ratio': data['city_to_full_region_ratio'],
                    'city_regional_background_difference': data['city_background_difference'],
                    
                    # Metadata
                    'timestamp': data['timestamp']
                }
                
                results.append(row)
                
            except Exception as e:
                print(f"    ❌ Error processing {json_file}: {e}")
                continue
    
    print(f"✅ Loaded {len(results)} analysis records")
    return results

def create_comprehensive_csv(results, output_file):
    """Convert results to DataFrame and save as CSV."""
    
    df = pd.DataFrame(results)
    
    # Sort by city and year
    df = df.sort_values(['city', 'year'])
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"💾 Comprehensive CSV saved: {output_file}")
    
    return df

def generate_analysis_report(df, output_dir):
    """Generate comprehensive analysis report and visualizations."""
    
    output_path = Path(output_dir)
    
    # Check for missing data
    print("\n🔍 Data Quality Assessment:")
    missing_data = df.isnull().sum()
    missing_cols = missing_data[missing_data > 0]
    
    if len(missing_cols) > 0:
        print("⚠️  Missing data found:")
        for col, count in missing_cols.items():
            print(f"    {col}: {count} missing values")
        
        # Show rows with missing administrative region data
        missing_admin = df[df['administrative_region_mean_radiance'].isnull()]
        if len(missing_admin) > 0:
            print("\n❗ Rows with missing administrative region data:")
            print(missing_admin[['city', 'year', 'administrative_region']].to_string(index=False))
    else:
        print("✅ No missing data found!")
    
    # Summary statistics
    print(f"\n📊 Dataset Summary:")
    print(f"   Cities: {df['city'].nunique()}")
    print(f"   Years: {df['year'].min()}-{df['year'].max()}")
    print(f"   Total records: {len(df)}")
    print(f"   Administrative regions: {df['administrative_region'].nunique()}")
    
    # Create visualizations
    plt.style.use('default')
    
    # 1. City-to-regional background ratios over time
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Plot 1: Ratios by city over time
    pivot_ratios = df.pivot(index='year', columns='city', values='city_to_regional_background_ratio')
    
    ax1 = axes[0, 0]
    for city in pivot_ratios.columns:
        ax1.plot(pivot_ratios.index, pivot_ratios[city], marker='o', label=city)
    ax1.set_title('City-to-Regional Background Ratios Over Time')
    ax1.set_xlabel('Year')
    ax1.set_ylabel('Ratio')
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Mean city radiance by city
    city_means = df.groupby('city')['city_mean_radiance'].mean().sort_values(ascending=False)
    
    ax2 = axes[0, 1]
    bars = ax2.bar(range(len(city_means)), city_means.values)
    ax2.set_title('Average City Nightlight Intensity (2017-2024)')
    ax2.set_xlabel('Cities')
    ax2.set_ylabel('Mean Radiance (nW/cm²/sr)')
    ax2.set_xticks(range(len(city_means)))
    ax2.set_xticklabels(city_means.index, rotation=45, ha='right')
    ax2.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for i, (bar, value) in enumerate(zip(bars, city_means.values)):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{value:.1f}', ha='center', va='bottom', fontsize=8)
    
    # Plot 3: Ratio distribution heatmap
    ax3 = axes[1, 0]
    pivot_heatmap = df.pivot(index='city', columns='year', values='city_to_regional_background_ratio')
    
    sns.heatmap(pivot_heatmap, annot=True, fmt='.1f', cmap='YlOrRd', ax=ax3, 
                cbar_kws={'label': 'City/Regional Ratio'})
    ax3.set_title('City-to-Regional Background Ratios Heatmap')
    ax3.set_xlabel('Year')
    ax3.set_ylabel('City')
    
    # Plot 4: Urban growth indicator (lit area over time)
    ax4 = axes[1, 1]
    
    for city in df['city'].unique():
        city_data = df[df['city'] == city].sort_values('year')
        ax4.plot(city_data['year'], city_data['city_lit_area_km2'], 
                marker='o', label=city, alpha=0.7)
    
    ax4.set_title('Urban Lit Area Growth Over Time')
    ax4.set_xlabel('Year')
    ax4.set_ylabel('City Lit Area (km²)')
    ax4.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path / 'comprehensive_nightlight_analysis.png', 
                dpi=300, bbox_inches='tight')
    plt.close()
    
    # Generate summary report
    report_file = output_path / 'nightlight_comprehensive_report.md'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"""# Uzbekistan Nightlight Analysis - Comprehensive Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Dataset Overview

- **Cities Analyzed**: {df['city'].nunique()}
- **Years Covered**: {df['year'].min()}-{df['year'].max()}
- **Total Records**: {len(df)}
- **Administrative Regions**: {df['administrative_region'].nunique()}

## Data Quality

""")
        
        if len(missing_cols) > 0:
            f.write("### ⚠️ Missing Data Issues\n\n")
            for col, count in missing_cols.items():
                f.write(f"- **{col}**: {count} missing values\n")
            
            if len(missing_admin) > 0:
                f.write("\n**Cities/Years with missing administrative region data:**\n\n")
                for _, row in missing_admin.iterrows():
                    f.write(f"- {row['city']} {row['year']}\n")
        else:
            f.write("✅ **No missing data detected**\n")
        
        f.write(f"""
## Key Findings

### Top 5 Brightest Cities (Average 2017-2024)

""")
        
        top_cities = city_means.head()
        for i, (city, radiance) in enumerate(top_cities.items(), 1):
            f.write(f"{i}. **{city}**: {radiance:.1f} nW/cm²/sr\n")
        
        f.write(f"""
### Highest City-to-Regional Contrasts

""")
        
        max_ratios = df.groupby('city')['city_to_regional_background_ratio'].max().sort_values(ascending=False).head()
        for i, (city, ratio) in enumerate(max_ratios.items(), 1):
            year = df[(df['city'] == city) & (df['city_to_regional_background_ratio'] == ratio)]['year'].iloc[0]
            f.write(f"{i}. **{city}** ({year}): {ratio:.1f}x brighter than regional background\n")
        
        f.write(f"""
## Regional Analysis

### Administrative Regions by City

""")
        
        region_mapping = df.groupby('city')['administrative_region'].first().sort_values()
        for city, region in region_mapping.items():
            f.write(f"- **{city}**: {region}\n")
        
        f.write(f"""
## Data Files

- **Comprehensive CSV**: `uzbekistan_nightlight_regional_analysis.csv`
- **Individual JSON files**: Available in city subdirectories
- **Visualizations**: `comprehensive_nightlight_analysis.png`

## Analysis Methodology

This analysis compares urban nightlight intensities at city centers (using circular buffers) 
against their respective administrative region backgrounds using:

- **Data Source**: VIIRS DNB Monthly Composites (Google Earth Engine)
- **Administrative Boundaries**: FAO GAUL Simplified 500m (2015, Level 1)
- **City Approach**: Center points + circular buffers (8-15km radius)
- **Regional Background**: Administrative boundaries excluding city buffers

""")
    
    print(f"📋 Comprehensive report generated: {report_file}")
    print(f"📈 Visualizations saved: {output_path / 'comprehensive_nightlight_analysis.png'}")

def main():
    """Main execution function."""
    
    print("🌃 Merging Uzbekistan Nightlight Analysis Results")
    print("=" * 60)
    
    # Define paths
    base_dir = "suhi_analysis_output/nightlight_regional_analysis"
    output_csv = "suhi_analysis_output/nightlight_regional_analysis/uzbekistan_nightlight_regional_analysis.csv"
    
    # Load all data
    results = load_all_nightlight_data(base_dir)
    
    if not results:
        print("❌ No analysis files found!")
        return
    
    # Create comprehensive CSV
    df = create_comprehensive_csv(results, output_csv)
    
    # Generate analysis report
    generate_analysis_report(df, Path(base_dir))
    
    print("\n✅ Merge and analysis complete!")
    print(f"📊 Final dataset: {len(df)} records from {df['city'].nunique()} cities")

if __name__ == "__main__":
    main()