"""
Visualization generators for analysis results
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import json


def setup_plot_style():
    """Setup consistent plot styling"""
    plt.style.use('default')
    sns.set_palette("husl")
    plt.rcParams.update({
        'figure.dpi': 300,
        'font.size': 10,
        'axes.titlesize': 12,
        'axes.labelsize': 10,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'legend.fontsize': 9
    })


def create_suhi_analysis_visualization(suhi_data: Dict, output_dir: Path) -> Path:
    """
    Create comprehensive SUHI analysis visualization
    """
    setup_plot_style()
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Surface Urban Heat Island Analysis Results', fontsize=16, fontweight='bold')
    
    # Extract data for plotting
    cities = []
    suhi_values = []
    urban_temps = []
    rural_temps = []
    
    for city_analysis in suhi_data.get('cities_analysis', []):
        for annual_result in city_analysis.get('annual_results', []):
            if 'error' not in annual_result:
                cities.append(f"{annual_result['city']}\n{annual_result['year']}")
                suhi_values.append(annual_result.get('suhi_intensity_celsius', 0))
                urban_temps.append(annual_result.get('urban_temperature_celsius', 0))
                rural_temps.append(annual_result.get('rural_temperature_celsius', 0))
    
    # 1. SUHI Intensity by City-Year
    ax1 = axes[0, 0]
    colors = ['red' if x > 2 else 'orange' if x > 0 else 'blue' for x in suhi_values]
    bars = ax1.bar(range(len(suhi_values)), suhi_values, color=colors, alpha=0.7)
    ax1.set_title('SUHI Intensity by City-Year')
    ax1.set_ylabel('SUHI Intensity (°C)')
    ax1.set_xticks(range(len(cities)))
    ax1.set_xticklabels(cities, rotation=45, ha='right')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    
    # Add value labels on bars
    for bar, value in zip(bars, suhi_values):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{value:.1f}°C', ha='center', va='bottom', fontsize=8)
    
    # 2. Urban vs Rural Temperature Comparison
    ax2 = axes[0, 1]
    ax2.scatter(rural_temps, urban_temps, alpha=0.6, s=50, c=suhi_values, cmap='RdYlBu_r')
    
    # Add diagonal line
    temp_range = [min(min(urban_temps), min(rural_temps)), max(max(urban_temps), max(rural_temps))]
    ax2.plot(temp_range, temp_range, 'k--', alpha=0.5, label='Equal Temperature')
    
    ax2.set_xlabel('Rural Temperature (°C)')
    ax2.set_ylabel('Urban Temperature (°C)')
    ax2.set_title('Urban vs Rural Temperature')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Add colorbar
    scatter = ax2.scatter(rural_temps, urban_temps, alpha=0.6, s=50, c=suhi_values, cmap='RdYlBu_r')
    plt.colorbar(scatter, ax=ax2, label='SUHI Intensity (°C)')
    
    # 3. SUHI Distribution
    ax3 = axes[1, 0]
    ax3.hist(suhi_values, bins=15, alpha=0.7, color='skyblue', edgecolor='black')
    ax3.set_xlabel('SUHI Intensity (°C)')
    ax3.set_ylabel('Frequency')
    ax3.set_title('SUHI Intensity Distribution')
    ax3.grid(True, alpha=0.3)
    
    # Add statistics text
    mean_suhi = np.mean(suhi_values)
    std_suhi = np.std(suhi_values)
    ax3.axvline(mean_suhi, color='red', linestyle='--', label=f'Mean: {mean_suhi:.2f}°C')
    ax3.legend()
    
    # 4. Summary Statistics
    ax4 = axes[1, 1]
    summary_stats = suhi_data.get('summary_statistics', {})
    
    stats_text = "SUHI ANALYSIS SUMMARY\n" + "="*25 + "\n\n"
    stats_text += f"Total Analyses: {summary_stats.get('total_analyses', 0)}\n"
    stats_text += f"Mean SUHI: {summary_stats.get('mean_suhi_all_cities', 0):.2f}°C\n"
    stats_text += f"Min SUHI: {summary_stats.get('min_suhi_observed', 0):.2f}°C\n"
    stats_text += f"Max SUHI: {summary_stats.get('max_suhi_observed', 0):.2f}°C\n"
    stats_text += f"SUHI Range: {summary_stats.get('suhi_range', 0):.2f}°C\n\n"
    stats_text += f"Cities with Strong SUHI (>2°C): {len([x for x in suhi_values if x > 2])}\n"
    stats_text += f"Cities with Cooling Effect (<0°C): {len([x for x in suhi_values if x < 0])}\n"
    
    ax4.text(0.1, 0.5, stats_text, transform=ax4.transAxes, fontsize=10,
            verticalalignment='center',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    ax4.set_title('Analysis Summary')
    ax4.axis('off')
    
    plt.tight_layout()
    
    # Save the plot
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"suhi_analysis_visualization_{timestamp}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"   📊 SUHI visualization saved: {output_file}")
    return output_file


def create_night_lights_visualization(night_lights_data: Dict, output_dir: Path) -> Path:
    """
    Create night lights analysis visualization
    """
    setup_plot_style()
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Night Lights Analysis Results', fontsize=16, fontweight='bold')
    
    # Extract data
    cities = []
    early_radiance = []
    late_radiance = []
    changes_abs = []
    changes_pct = []
    
    for city_data in night_lights_data.get('cities', []):
        if 'error' not in city_data:
            cities.append(city_data['city'])
            early_radiance.append(city_data.get('early_mean_radiance', 0))
            late_radiance.append(city_data.get('late_mean_radiance', 0))
            changes_abs.append(city_data.get('change_absolute', 0))
            changes_pct.append(city_data.get('change_percent', 0))
    
    # 1. Radiance Change by City
    ax1 = axes[0, 0]
    colors = ['green' if x > 0 else 'red' for x in changes_abs]
    bars = ax1.bar(cities, changes_abs, color=colors, alpha=0.7)
    ax1.set_title(f"Night Lights Change ({night_lights_data.get('year_early')}-{night_lights_data.get('year_late')})")
    ax1.set_ylabel('Radiance Change (nW/cm²/sr)')
    ax1.tick_params(axis='x', rotation=45)
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    
    # 2. Early vs Late Year Comparison
    ax2 = axes[0, 1]
    ax2.scatter(early_radiance, late_radiance, alpha=0.7, s=100)
    
    # Add diagonal line
    max_rad = max(max(early_radiance), max(late_radiance))
    ax2.plot([0, max_rad], [0, max_rad], 'k--', alpha=0.5, label='No Change')
    
    ax2.set_xlabel(f'{night_lights_data.get("year_early")} Radiance')
    ax2.set_ylabel(f'{night_lights_data.get("year_late")} Radiance')
    ax2.set_title('Early vs Late Year Radiance')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Add city labels
    for i, city in enumerate(cities):
        ax2.annotate(city, (early_radiance[i], late_radiance[i]), 
                    xytext=(5, 5), textcoords='offset points', fontsize=8)
    
    # 3. Percentage Change
    ax3 = axes[1, 0]
    colors = ['green' if x > 0 else 'red' for x in changes_pct]
    bars = ax3.bar(cities, changes_pct, color=colors, alpha=0.7)
    ax3.set_title('Percentage Change in Night Lights')
    ax3.set_ylabel('Change (%)')
    ax3.tick_params(axis='x', rotation=45)
    ax3.grid(True, alpha=0.3)
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    
    # 4. Country-level summary
    ax4 = axes[1, 1]
    country_data = night_lights_data.get('country', {})
    
    summary_text = "NIGHT LIGHTS SUMMARY\n" + "="*22 + "\n\n"
    
    if 'error' not in country_data:
        summary_text += f"Country Early Radiance: {country_data.get('early_mean_radiance', 0):.4f}\n"
        summary_text += f"Country Late Radiance: {country_data.get('late_mean_radiance', 0):.4f}\n\n"
    
    summary_text += f"Cities Analyzed: {len(cities)}\n"
    summary_text += f"Cities with Increase: {len([x for x in changes_abs if x > 0])}\n"
    summary_text += f"Cities with Decrease: {len([x for x in changes_abs if x < 0])}\n"
    summary_text += f"Average Change: {np.mean(changes_pct):.1f}%\n"
    summary_text += f"Max Increase: {max(changes_pct):.1f}%\n"
    summary_text += f"Max Decrease: {min(changes_pct):.1f}%\n"
    
    ax4.text(0.1, 0.5, summary_text, transform=ax4.transAxes, fontsize=10,
            verticalalignment='center',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax4.set_title('Analysis Summary')
    ax4.axis('off')
    
    plt.tight_layout()
    
    # Save the plot
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"night_lights_visualization_{timestamp}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"   🌙 Night lights visualization saved: {output_file}")
    return output_file


def create_urban_expansion_visualization(expansion_data: Dict, output_dir: Path) -> Path:
    """
    Create urban expansion analysis visualization
    """
    setup_plot_style()
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Urban Expansion Analysis Results', fontsize=16, fontweight='bold')
    
    # Extract data
    cities = []
    area_changes = []
    percent_changes = []
    start_areas = []
    end_areas = []
    
    for city_data in expansion_data.get('cities_analysis', []):
        if 'error' not in city_data:
            cities.append(city_data['city'])
            area_changes.append(city_data.get('built_area_change_km2', 0))
            percent_changes.append(city_data.get('built_area_change_percent', 0))
            start_areas.append(city_data.get('built_area_start_km2', 0))
            end_areas.append(city_data.get('built_area_end_km2', 0))
    
    # 1. Built Area Change
    ax1 = axes[0, 0]
    colors = ['green' if x > 0 else 'red' for x in area_changes]
    bars = ax1.bar(cities, area_changes, color=colors, alpha=0.7)
    ax1.set_title(f"Built Area Change ({expansion_data.get('year_start')}-{expansion_data.get('year_end')})")
    ax1.set_ylabel('Area Change (km²)')
    ax1.tick_params(axis='x', rotation=45)
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    
    # Add value labels
    for bar, value in zip(bars, area_changes):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + (0.1 if height >= 0 else -0.3),
                f'{value:.1f}', ha='center', va='bottom' if height >= 0 else 'top', fontsize=8)
    
    # 2. Start vs End Areas
    ax2 = axes[0, 1]
    x = np.arange(len(cities))
    width = 0.35
    
    bars1 = ax2.bar(x - width/2, start_areas, width, label=f'{expansion_data.get("year_start")}', 
                    color='lightblue', alpha=0.7)
    bars2 = ax2.bar(x + width/2, end_areas, width, label=f'{expansion_data.get("year_end")}', 
                    color='darkblue', alpha=0.7)
    
    ax2.set_ylabel('Built Area (km²)')
    ax2.set_title('Built Area: Start vs End')
    ax2.set_xticks(x)
    ax2.set_xticklabels(cities, rotation=45, ha='right')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. Percentage Change
    ax3 = axes[1, 0]
    colors = ['green' if x > 0 else 'red' for x in percent_changes]
    bars = ax3.bar(cities, percent_changes, color=colors, alpha=0.7)
    ax3.set_title('Relative Urban Growth Rates')
    ax3.set_ylabel('Change (%)')
    ax3.tick_params(axis='x', rotation=45)
    ax3.grid(True, alpha=0.3)
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    
    # 4. Summary Statistics
    ax4 = axes[1, 1]
    summary_stats = expansion_data.get('summary_statistics', {})
    
    stats_text = "URBAN EXPANSION SUMMARY\n" + "="*25 + "\n\n"
    stats_text += f"Cities Analyzed: {summary_stats.get('total_cities_analyzed', 0)}\n"
    stats_text += f"Total Expansion: {summary_stats.get('total_urban_expansion_km2', 0):.2f} km²\n"
    stats_text += f"Average per City: {summary_stats.get('average_expansion_per_city_km2', 0):.2f} km²\n"
    stats_text += f"Annual Rate: {summary_stats.get('expansion_rate_km2_per_year', 0):.2f} km²/year\n\n"
    stats_text += f"Cities Expanding: {len([x for x in area_changes if x > 0])}\n"
    stats_text += f"Cities Contracting: {len([x for x in area_changes if x < 0])}\n"
    stats_text += f"Max Expansion: {max(area_changes):.2f} km²\n"
    stats_text += f"Analysis Period: {expansion_data.get('analysis_period_years', 0)} years\n"
    
    ax4.text(0.1, 0.5, stats_text, transform=ax4.transAxes, fontsize=10,
            verticalalignment='center',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
    ax4.set_title('Analysis Summary')
    ax4.axis('off')
    
    plt.tight_layout()
    
    # Save the plot
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"urban_expansion_visualization_{timestamp}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"   🏗️ Urban expansion visualization saved: {output_file}")
    return output_file


def create_comprehensive_dashboard(suhi_data: Dict, night_lights_data: Dict, 
                                 expansion_data: Dict, output_dir: Path) -> Path:
    """
    Create comprehensive analysis dashboard
    """
    setup_plot_style()
    
    fig = plt.figure(figsize=(20, 16))
    fig.suptitle('Uzbekistan Urban Research - Comprehensive Analysis Dashboard', 
                fontsize=18, fontweight='bold')
    
    # Create a complex subplot layout
    gs = fig.add_gridspec(4, 4, height_ratios=[1, 1, 1, 0.8], width_ratios=[1, 1, 1, 1])
    
    # SUHI Analysis (top row)
    ax1 = fig.add_subplot(gs[0, :2])
    suhi_values = []
    suhi_cities = []
    for city_analysis in suhi_data.get('cities_analysis', []):
        for annual_result in city_analysis.get('annual_results', []):
            if 'error' not in annual_result:
                suhi_cities.append(f"{annual_result['city']}")
                suhi_values.append(annual_result.get('suhi_intensity_celsius', 0))
    
    if suhi_values:
        colors = ['red' if x > 2 else 'orange' if x > 0 else 'blue' for x in suhi_values]
        ax1.bar(range(len(suhi_values)), suhi_values, color=colors, alpha=0.7)
        ax1.set_title('Surface Urban Heat Island Intensity', fontsize=14, fontweight='bold')
        ax1.set_ylabel('SUHI (°C)')
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    
    # Night Lights Analysis (top right)
    ax2 = fig.add_subplot(gs[0, 2:])
    night_cities = []
    night_changes = []
    for city_data in night_lights_data.get('cities', []):
        if 'error' not in city_data:
            night_cities.append(city_data['city'])
            night_changes.append(city_data.get('change_percent', 0))
    
    if night_changes:
        colors = ['green' if x > 0 else 'red' for x in night_changes]
        ax2.bar(night_cities, night_changes, color=colors, alpha=0.7)
        ax2.set_title('Night Lights Change (%)', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Change (%)')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)
    
    # Urban Expansion Analysis (middle row)
    ax3 = fig.add_subplot(gs[1, :2])
    expansion_cities = []
    expansion_changes = []
    for city_data in expansion_data.get('cities_analysis', []):
        if 'error' not in city_data:
            expansion_cities.append(city_data['city'])
            expansion_changes.append(city_data.get('built_area_change_km2', 0))
    
    if expansion_changes:
        colors = ['green' if x > 0 else 'red' for x in expansion_changes]
        ax3.bar(expansion_cities, expansion_changes, color=colors, alpha=0.7)
        ax3.set_title('Urban Area Change (km²)', fontsize=14, fontweight='bold')
        ax3.set_ylabel('Area Change (km²)')
        ax3.tick_params(axis='x', rotation=45)
        ax3.grid(True, alpha=0.3)
    
    # Analysis correlation plot (middle right)
    ax4 = fig.add_subplot(gs[1, 2:])
    if len(suhi_values) == len(night_changes) == len(expansion_changes):
        ax4.scatter(expansion_changes, suhi_values, alpha=0.7, s=100, c=night_changes, cmap='RdYlGn')
        ax4.set_xlabel('Urban Expansion (km²)')
        ax4.set_ylabel('SUHI Intensity (°C)')
        ax4.set_title('Urban Expansion vs SUHI', fontsize=14, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        plt.colorbar(ax4.collections[0], ax=ax4, label='Night Lights Change (%)')
    
    # Summary statistics panel (bottom)
    ax5 = fig.add_subplot(gs[2:, :])
    
    summary_text = "COMPREHENSIVE ANALYSIS SUMMARY\n" + "="*50 + "\n\n"
    
    # SUHI Summary
    if suhi_values:
        summary_text += "🔥 SURFACE URBAN HEAT ISLAND:\n"
        summary_text += f"   • Average SUHI: {np.mean(suhi_values):.2f}°C\n"
        summary_text += f"   • Max SUHI: {max(suhi_values):.2f}°C\n"
        summary_text += f"   • Cities with strong SUHI (>2°C): {len([x for x in suhi_values if x > 2])}\n\n"
    
    # Night Lights Summary  
    if night_changes:
        summary_text += "🌙 NIGHT LIGHTS:\n"
        summary_text += f"   • Average change: {np.mean(night_changes):.1f}%\n"
        summary_text += f"   • Cities increasing: {len([x for x in night_changes if x > 0])}\n"
        summary_text += f"   • Max increase: {max(night_changes):.1f}%\n\n"
    
    # Urban Expansion Summary
    if expansion_changes:
        total_expansion = sum(expansion_changes)
        summary_text += "🏗️ URBAN EXPANSION:\n"
        summary_text += f"   • Total expansion: {total_expansion:.2f} km²\n"
        summary_text += f"   • Average per city: {np.mean(expansion_changes):.2f} km²\n"
        summary_text += f"   • Cities expanding: {len([x for x in expansion_changes if x > 0])}\n\n"
    
    # Analysis metadata
    summary_text += "📊 ANALYSIS DETAILS:\n"
    summary_text += f"   • Time period: {expansion_data.get('year_start')}-{expansion_data.get('year_end')}\n"
    summary_text += f"   • Spatial resolution: {expansion_data.get('processing_scale_m')}m\n"
    summary_text += f"   • Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    ax5.text(0.05, 0.95, summary_text, transform=ax5.transAxes, fontsize=11,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
    ax5.axis('off')
    
    plt.tight_layout()
    
    # Save the comprehensive dashboard
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"comprehensive_analysis_dashboard_{timestamp}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"   📊 Comprehensive dashboard saved: {output_file}")
    return output_file