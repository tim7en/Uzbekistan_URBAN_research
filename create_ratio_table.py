#!/usr/bin/env python3
"""
Create a comprehensive table of urban-to-rural nightlight ratios by city and year
for comparison with regional GRP data.
"""

import pandas as pd
import numpy as np

def create_ratio_table():
    """Create formatted table of urban-to-rural ratios by city and year"""
    
    # Load the comprehensive dataset
    csv_path = 'suhi_analysis_output/nightlight_regional_analysis/uzbekistan_nightlight_regional_analysis.csv'
    
    try:
        df = pd.read_csv(csv_path)
        print(f"✅ Loaded nightlight data: {len(df)} records")
        
        # Create pivot table with cities as rows, years as columns
        ratio_pivot = df.pivot_table(
            index='city', 
            columns='year', 
            values='city_to_regional_background_ratio',
            fill_value=np.nan
        )
        
        # Sort cities by 2024 ratio (descending) for ranking
        ratio_pivot_sorted = ratio_pivot.sort_values(by=2024, ascending=False, na_position='last')
        
        # Create formatted table
        print("\n" + "="*100)
        print("🌟 UZBEKISTAN URBAN-TO-RURAL NIGHTLIGHT INTENSITY RATIOS (2017-2024)")
        print("="*100)
        print("📊 Ranked by 2024 Urban Development Intensity")
        print("💡 Higher ratios = stronger urban concentration vs regional background")
        print("-"*100)
        
        # Format headers
        header = "Rank | City" + " "*12 + "| " + " | ".join([f"{year:>6}" for year in range(2017, 2025)])
        print(header)
        print("-"*100)
        
        # Print each city's data with ranking
        for rank, (city, row) in enumerate(ratio_pivot_sorted.iterrows(), 1):
            city_name = f"{city:<15}"
            year_values = []
            for year in range(2017, 2025):
                if year in row.index and not pd.isna(row[year]):
                    year_values.append(f"{row[year]:>6.1f}")
                else:
                    year_values.append(f"{'--':>6}")
            
            values_str = " | ".join(year_values)
            print(f"{rank:>3}. | {city_name} | {values_str}")
        
        print("-"*100)
        
        # Summary statistics
        print("\n📈 SUMMARY STATISTICS")
        print("="*50)
        
        # Average ratios by year
        yearly_means = ratio_pivot.mean().round(1)
        print("\n🗓️ National Average Urban-Rural Ratio by Year:")
        for year in range(2017, 2025):
            if year in yearly_means.index:
                print(f"   {year}: {yearly_means[year]:.1f}x")
        
        # Top performers by year
        print("\n🏆 Highest Urban Concentration Each Year:")
        for year in range(2017, 2025):
            if year in ratio_pivot.columns:
                top_city = ratio_pivot[year].idxmax()
                top_ratio = ratio_pivot[year].max()
                if not pd.isna(top_ratio):
                    print(f"   {year}: {top_city} ({top_ratio:.1f}x)")
        
        # Growth analysis
        print("\n📊 Urban Development Growth (2017-2024):")
        if 2017 in ratio_pivot.columns and 2024 in ratio_pivot.columns:
            cities_with_both = ratio_pivot.dropna(subset=[2017, 2024])
            growth = ((cities_with_both[2024] - cities_with_both[2017]) / cities_with_both[2017] * 100).sort_values(ascending=False)
            
            print("\n🚀 Fastest Growing Urban Concentrations:")
            for city in growth.head(5).index:
                growth_pct = growth[city]
                ratio_2017 = cities_with_both.loc[city, 2017]
                ratio_2024 = cities_with_both.loc[city, 2024]
                print(f"   {city}: {growth_pct:+.1f}% ({ratio_2017:.1f}x → {ratio_2024:.1f}x)")
        else:
            print("   Data for 2017 or 2024 not available for growth analysis")
        
        # Export for GRP comparison
        print("\n💾 EXPORT FOR GRP ANALYSIS")
        print("="*40)
        
        # Save as CSV for analysis
        output_csv = 'urban_rural_ratios_for_grp_comparison.csv'
        ratio_pivot_sorted.to_csv(output_csv)
        print(f"📄 Saved detailed CSV: {output_csv}")
        
        # Create administrative region summary
        region_summary = df.groupby(['administrative_region', 'year'])['city_to_regional_background_ratio'].mean().reset_index()
        region_pivot = region_summary.pivot_table(
            index='administrative_region',
            columns='year', 
            values='city_to_regional_background_ratio',
            fill_value=np.nan
        )
        
        output_region_csv = 'regional_ratios_for_grp_comparison.csv'
        region_pivot.to_csv(output_region_csv)
        print(f"🗺️ Saved regional CSV: {output_region_csv}")
        
        print(f"\n✅ Table creation complete!")
        print(f"📊 Ready for GRP comparison analysis")
        
        return ratio_pivot_sorted, region_pivot
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find {csv_path}")
        print("💡 Please run the nightlight analysis first")
        return None, None
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return None, None

if __name__ == "__main__":
    city_ratios, region_ratios = create_ratio_table()