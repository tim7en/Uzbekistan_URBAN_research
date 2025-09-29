#!/usr/bin/env python3
"""
Create a dedicated large heatmap showing all cities clearly.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def create_detailed_heatmap():
    """Create a large, clear heatmap of all cities and years."""
    
    # Load data
    df = pd.read_csv('suhi_analysis_output/nightlight_regional_analysis/uzbekistan_nightlight_regional_analysis.csv')
    
    # Create pivot for heatmap
    pivot_ratios = df.pivot(index='city', columns='year', values='city_to_regional_background_ratio')
    
    print(f"Creating heatmap for {len(pivot_ratios.index)} cities and {len(pivot_ratios.columns)} years")
    
    # Create large figure for detailed heatmap
    plt.figure(figsize=(12, 10))
    
    # Create heatmap with clear annotations
    sns.heatmap(pivot_ratios, 
                annot=True, 
                fmt='.1f', 
                cmap='YlOrRd',
                cbar_kws={'label': 'City-to-Regional Background Ratio'},
                square=False,
                linewidths=0.5,
                annot_kws={'size': 10})
    
    plt.title('Uzbekistan Cities: Urban-Rural Nightlight Contrast Ratios (2017-2024)', 
              fontsize=14, fontweight='bold', pad=20)
    plt.xlabel('Year', fontsize=12)
    plt.ylabel('City', fontsize=12)
    
    # Ensure all city names are visible
    plt.xticks(rotation=0)
    plt.yticks(rotation=0)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save high-quality version
    output_path = 'suhi_analysis_output/nightlight_regional_analysis/detailed_heatmap_all_cities.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Detailed heatmap saved: {output_path}")
    
    # Also create summary statistics
    print(f"\n📊 Heatmap Summary:")
    print(f"Cities included: {', '.join(sorted(pivot_ratios.index))}")
    print(f"Years covered: {pivot_ratios.columns.min()}-{pivot_ratios.columns.max()}")
    print(f"Ratio range: {pivot_ratios.min().min():.1f}x - {pivot_ratios.max().max():.1f}x")
    
    # Show highest and lowest contrast cities
    avg_ratios = pivot_ratios.mean(axis=1).sort_values(ascending=False)
    print(f"\nTop 5 highest contrast cities (average):")
    for i, (city, ratio) in enumerate(avg_ratios.head().items(), 1):
        print(f"  {i}. {city}: {ratio:.1f}x")
    
    print(f"\nLowest contrast cities:")
    for i, (city, ratio) in enumerate(avg_ratios.tail(3).items(), 1):
        print(f"  {city}: {ratio:.1f}x")

if __name__ == "__main__":
    create_detailed_heatmap()