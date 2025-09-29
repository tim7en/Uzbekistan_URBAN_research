#!/usr/bin/env python3
"""
Test heatmap visualization to debug the issue.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load data
df = pd.read_csv('suhi_analysis_output/nightlight_regional_analysis/uzbekistan_nightlight_regional_analysis.csv')

# Create pivot for heatmap
pivot_ratios = df.pivot(index='city', columns='year', values='city_to_regional_background_ratio')

print(f"Pivot shape: {pivot_ratios.shape}")
print(f"Cities: {len(pivot_ratios.index)}")
print(f"Years: {len(pivot_ratios.columns)}")
print("\nSample data:")
print(pivot_ratios.head())

# Create simple heatmap test
plt.figure(figsize=(12, 10))
sns.heatmap(pivot_ratios, annot=True, fmt='.1f', cmap='YlOrRd', 
            cbar_kws={'label': 'City/Regional Ratio'})
plt.title('Urban-Rural Contrast Ratios - All Cities Test')
plt.xlabel('Year')
plt.ylabel('City')
plt.tight_layout()
plt.savefig('suhi_analysis_output/nightlight_regional_analysis/heatmap_test.png', 
            dpi=300, bbox_inches='tight')
plt.close()

print("\nTest heatmap saved as heatmap_test.png")
print("All cities should be visible in this heatmap.")