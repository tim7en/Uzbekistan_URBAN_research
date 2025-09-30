#!/usr/bin/env python3
"""
Create GDP Visualization Dashboard
=================================

Generate comprehensive visualizations for Uzbekistan city GDP estimates
including boxplots, trends, and summary statistics.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

def load_latest_results():
    """Load the most recent GDP estimation results"""
    data_folder = Path("./")
    
    # Find the most recent results file (exclude validation files)
    result_files = list(data_folder.glob("comprehensive_city_gdp_estimates_*.csv"))
    result_files = [f for f in result_files if "validation" not in f.name]
    
    if not result_files:
        raise FileNotFoundError("No GDP estimation results found")
    
    latest_file = sorted(result_files)[-1]
    print(f"📊 Loading results from: {latest_file}")
    
    df = pd.read_csv(latest_file)
    return df, latest_file.stem

def create_gdp_boxplot(df):
    """Create boxplot of GDP estimates by city with mean markers"""
    
    plt.figure(figsize=(16, 10))
    
    # Filter for 2024 data for cleaner visualization
    df_2024 = df[df['year'] == 2024].copy()
    df_2024 = df_2024.sort_values('ensemble_gdp_billion', ascending=False)
    
    # Create boxplot data for all years by city
    city_order = df_2024['city'].tolist()
    
    # Prepare data for boxplot (all years)
    plot_data = []
    for city in city_order:
        city_data = df[df['city'] == city]['ensemble_gdp_billion'].dropna()
        if len(city_data) > 0:
            plot_data.append(city_data.values)
        else:
            plot_data.append([0])
    
    # Create the boxplot
    ax = plt.gca()
    box_plot = ax.boxplot(plot_data, labels=city_order, patch_artist=True)
    
    # Color the boxes with a gradient
    colors = plt.cm.viridis(np.linspace(0, 1, len(city_order)))
    for patch, color in zip(box_plot['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # Add mean markers
    means = [np.mean(data) for data in plot_data]
    ax.scatter(range(1, len(city_order) + 1), means, 
              color='red', marker='D', s=50, zorder=5, label='Mean GDP')
    
    # Add 2024 values as separate markers
    gdp_2024 = [df_2024[df_2024['city'] == city]['ensemble_gdp_billion'].iloc[0] 
                if city in df_2024['city'].values else 0 for city in city_order]
    ax.scatter(range(1, len(city_order) + 1), gdp_2024, 
              color='orange', marker='o', s=80, zorder=6, label='2024 GDP')
    
    plt.title('Uzbekistan City GDP Estimates Distribution (2017-2024)\nBoxplots with Mean and 2024 Values', 
              fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Cities', fontsize=12, fontweight='bold')
    plt.ylabel('GDP (Billions USD)', fontsize=12, fontweight='bold')
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45, ha='right')
    
    # Add grid
    plt.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Add legend
    plt.legend(loc='upper right')
    
    # Adjust layout
    plt.tight_layout()
    
    return plt.gcf()

def create_gdp_trends(df):
    """Create time series plot of GDP trends"""
    
    plt.figure(figsize=(16, 10))
    
    # Get top 10 cities by 2024 GDP
    top_cities_2024 = df[df['year'] == 2024].nlargest(10, 'ensemble_gdp_billion')['city'].tolist()
    
    # Color palette
    colors = plt.cm.tab10(np.linspace(0, 1, len(top_cities_2024)))
    
    for i, city in enumerate(top_cities_2024):
        city_data = df[df['city'] == city].sort_values('year')
        
        plt.plot(city_data['year'], city_data['ensemble_gdp_billion'], 
                marker='o', linewidth=2.5, markersize=6, 
                label=city, color=colors[i])
    
    plt.title('GDP Growth Trends: Top 10 Cities (2017-2024)', 
              fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Year', fontsize=12, fontweight='bold')
    plt.ylabel('GDP (Billions USD)', fontsize=12, fontweight='bold')
    
    # Add grid
    plt.grid(True, alpha=0.3, linestyle='--')
    
    # Legend
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Format y-axis to show billions
    ax = plt.gca()
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:.1f}B'))
    
    plt.tight_layout()
    
    return plt.gcf()

def create_per_capita_analysis(df):
    """Create per capita GDP analysis"""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
    
    # 2024 per capita GDP ranking
    df_2024 = df[df['year'] == 2024].copy()
    df_2024 = df_2024.sort_values('gdp_per_capita_usd', ascending=True)
    
    # Horizontal bar chart
    bars = ax1.barh(df_2024['city'], df_2024['gdp_per_capita_usd'], 
                    color=plt.cm.plasma(np.linspace(0, 1, len(df_2024))))
    
    ax1.set_title('GDP Per Capita by City (2024)', fontsize=14, fontweight='bold')
    ax1.set_xlabel('GDP per Capita (USD)', fontsize=12)
    ax1.grid(axis='x', alpha=0.3)
    
    # Add value labels on bars
    for i, (bar, value) in enumerate(zip(bars, df_2024['gdp_per_capita_usd'])):
        ax1.text(value + 100, bar.get_y() + bar.get_height()/2, 
                f'${value:,.0f}', va='center', fontsize=10)
    
    # Per capita trends for top cities
    top_cities_pc = df_2024.nlargest(8, 'gdp_per_capita_usd')['city'].tolist()
    
    colors = plt.cm.viridis(np.linspace(0, 1, len(top_cities_pc)))
    
    for i, city in enumerate(top_cities_pc):
        city_data = df[df['city'] == city].sort_values('year')
        
        ax2.plot(city_data['year'], city_data['gdp_per_capita_usd'], 
                marker='o', linewidth=2, markersize=5, 
                label=city, color=colors[i])
    
    ax2.set_title('GDP Per Capita Trends: Top 8 Cities', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Year', fontsize=12)
    ax2.set_ylabel('GDP per Capita (USD)', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    
    return fig

def create_confidence_analysis(df):
    """Create confidence score analysis"""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Confidence distribution
    ax1.hist(df['confidence_score'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
    ax1.axvline(df['confidence_score'].mean(), color='red', linestyle='--', 
                label=f'Mean: {df["confidence_score"].mean():.3f}')
    ax1.set_title('Distribution of Confidence Scores', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Confidence Score', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # Confidence vs GDP relationship
    scatter = ax2.scatter(df['confidence_score'], df['ensemble_gdp_billion'], 
                         c=df['year'], cmap='viridis', alpha=0.6, s=50)
    
    ax2.set_title('GDP vs Confidence Score Relationship', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Confidence Score', fontsize=12)
    ax2.set_ylabel('GDP (Billions USD)', fontsize=12)
    ax2.grid(alpha=0.3)
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax2)
    cbar.set_label('Year')
    
    plt.tight_layout()
    
    return fig

def create_summary_table(df):
    """Create comprehensive summary statistics table"""
    
    # 2024 summary
    df_2024 = df[df['year'] == 2024].copy()
    
    summary_stats = df_2024.groupby('city').agg({
        'ensemble_gdp_billion': 'first',
        'gdp_per_capita_usd': 'first',
        'confidence_score': 'first'
    }).round(3)
    
    # Add growth rates (2017-2024 CAGR)
    growth_rates = {}
    for city in df_2024['city']:
        city_data = df[df['city'] == city].sort_values('year')
        if len(city_data) >= 2:
            start_gdp = city_data.iloc[0]['ensemble_gdp_billion']
            end_gdp = city_data.iloc[-1]['ensemble_gdp_billion']
            years = city_data.iloc[-1]['year'] - city_data.iloc[0]['year']
            
            if start_gdp > 0 and years > 0:
                cagr = ((end_gdp / start_gdp) ** (1/years) - 1) * 100
                growth_rates[city] = cagr
            else:
                growth_rates[city] = 0
        else:
            growth_rates[city] = 0
    
    summary_stats['cagr_2017_2024'] = summary_stats.index.map(growth_rates)
    
    # Sort by GDP
    summary_stats = summary_stats.sort_values('ensemble_gdp_billion', ascending=False)
    
    # Format for display
    summary_stats['gdp_formatted'] = summary_stats['ensemble_gdp_billion'].apply(lambda x: f"${x:.2f}B")
    summary_stats['gdp_pc_formatted'] = summary_stats['gdp_per_capita_usd'].apply(lambda x: f"${x:,.0f}")
    summary_stats['cagr_formatted'] = summary_stats['cagr_2017_2024'].apply(lambda x: f"{x:.1f}%")
    
    return summary_stats

def main():
    """Main visualization creation function"""
    print("🎨 Creating GDP Visualization Dashboard...")
    
    # Load data
    df, filename_stem = load_latest_results()
    
    # Set style
    plt.style.use('default')
    sns.set_palette("husl")
    
    # Create output directory
    output_dir = Path("./plots")
    output_dir.mkdir(exist_ok=True)
    
    # Create visualizations
    print("📊 Creating GDP boxplot...")
    fig1 = create_gdp_boxplot(df)
    fig1.savefig(output_dir / f"{filename_stem}_boxplot.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print("📈 Creating GDP trends...")
    fig2 = create_gdp_trends(df)
    fig2.savefig(output_dir / f"{filename_stem}_trends.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print("💰 Creating per capita analysis...")
    fig3 = create_per_capita_analysis(df)
    fig3.savefig(output_dir / f"{filename_stem}_per_capita.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print("🎯 Creating confidence analysis...")
    fig4 = create_confidence_analysis(df)
    fig4.savefig(output_dir / f"{filename_stem}_confidence.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # Create summary table
    print("📋 Creating summary statistics...")
    summary_stats = create_summary_table(df)
    
    # Save summary table
    summary_stats.to_csv(output_dir / f"{filename_stem}_summary_table.csv")
    
    # Print final summary
    print("\n" + "="*80)
    print("🇺🇿 FINAL UZBEKISTAN CITY GDP ESTIMATES (2024)")
    print("="*80)
    print(f"{'Rank':<4} {'City':<12} {'GDP (Bil USD)':<12} {'GDP/Capita':<12} {'CAGR 2017-24':<12} {'Confidence'}")
    print("-"*80)
    
    for i, (city, row) in enumerate(summary_stats.iterrows(), 1):
        print(f"{i:<4} {city:<12} {row['gdp_formatted']:<12} {row['gdp_pc_formatted']:<12} "
              f"{row['cagr_formatted']:<12} {row['confidence_score']:.3f}")
    
    print("-"*80)
    print(f"Total Urban GDP (2024): ${summary_stats['ensemble_gdp_billion'].sum():.2f} Billion USD")
    print(f"Average GDP per Capita: ${summary_stats['gdp_per_capita_usd'].mean():,.0f} USD")
    print(f"Average Growth Rate: {summary_stats['cagr_2017_2024'].mean():.1f}% CAGR")
    print("="*80)
    
    print(f"\n🎉 All visualizations saved to: {output_dir}/")
    print("📊 Generated files:")
    print(f"   • {filename_stem}_boxplot.png - GDP distribution boxplots")
    print(f"   • {filename_stem}_trends.png - Time series trends")
    print(f"   • {filename_stem}_per_capita.png - Per capita analysis")
    print(f"   • {filename_stem}_confidence.png - Confidence analysis")
    print(f"   • {filename_stem}_summary_table.csv - Summary statistics")
    
    return summary_stats

if __name__ == "__main__":
    summary = main()