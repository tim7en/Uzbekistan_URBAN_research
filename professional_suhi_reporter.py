#!/usr/bin/env python3
"""
SUHI Analysis Report Generator
=============================

A focused script for generating professional reports and visualizations
from SUHI analysis data with emphasis on clean, gridded layouts.

Features:
- Professional gridded visualizations
- Comprehensive statistical reports
- Export-ready figures
- Clean, publication-quality outputs

Author: GitHub Copilot
Date: August 19, 2025
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
from datetime import datetime

# Configure plotting for professional output
warnings.filterwarnings('ignore')
plt.style.use('default')
sns.set_palette("husl")

# Set matplotlib to use a clean style
plt.rcParams.update({
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.labelsize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 9,
    'figure.titlesize': 14,
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'DejaVu Sans'],
    'axes.grid': True,
    'grid.alpha': 0.3,
    'axes.spines.top': False,
    'axes.spines.right': False
})

class ProfessionalSUHIReporter:
    """
    Professional SUHI analysis reporter with focus on clean visualizations.
    """
    
    def __init__(self, data_directory):
        """Initialize the reporter with data directory path."""
        self.data_path = Path(data_directory)
        self.output_path = self.data_path.parent
        self.cities_data = {}
        self.temporal_data = {}
        
        # Professional color scheme
        self.colors = {
            'primary': '#2E86AB',
            'secondary': '#A23B72', 
            'accent1': '#F18F01',
            'accent2': '#C73E1D',
            'neutral': '#6C757D',
            'success': '#28A745',
            'warning': '#FFC107',
            'info': '#17A2B8'
        }
        
    def load_all_data(self):
        """Load all SUHI data from JSON files."""
        print("Loading SUHI data files...")
        
        # Get all cities from the data files
        cities = set()
        for file_path in self.data_path.glob("*_2017_results.json"):
            city_name = file_path.stem.replace("_2017_results", "")
            cities.add(city_name)
        
        # Load data for each city
        for city in cities:
            self.cities_data[city] = {}
            
            # Load 2017 and 2024 results
            for year in [2017, 2024]:
                file_path = self.data_path / f"{city}_{year}_results.json"
                if file_path.exists():
                    with open(file_path, 'r') as f:
                        self.cities_data[city][year] = json.load(f)
            
            # Load temporal trends
            trends_file = self.data_path / f"{city}_annual_suhi_trends.json"
            if trends_file.exists():
                with open(trends_file, 'r') as f:
                    self.temporal_data[city] = json.load(f)
        
        print(f"Loaded data for {len(cities)} cities")
        return len(cities)
    
    def generate_summary_statistics(self):
        """Generate comprehensive summary statistics."""
        stats = {
            'cities_analyzed': len(self.cities_data),
            'suhi_changes': [],
            'urban_growth': [],
            'temperature_trends': [],
            'city_rankings': {}
        }
        
        for city, data in self.cities_data.items():
            if 2017 in data and 2024 in data:
                # SUHI change calculation
                suhi_2017 = data[2017]['suhi_analysis']['suhi']
                suhi_2024 = data[2024]['suhi_analysis']['suhi']
                suhi_change = suhi_2024 - suhi_2017
                
                stats['suhi_changes'].append({
                    'city': city,
                    'suhi_2017': suhi_2017,
                    'suhi_2024': suhi_2024,
                    'change': suhi_change,
                    'change_pct': (suhi_change / suhi_2017) * 100
                })
                
                # Urban growth calculation
                urban_2017 = data[2017]['suhi_analysis']['urban_pixels']
                urban_2024 = data[2024]['suhi_analysis']['urban_pixels']
                growth_rate = ((urban_2024 - urban_2017) / urban_2017) * 100
                
                stats['urban_growth'].append({
                    'city': city,
                    'pixels_2017': urban_2017,
                    'pixels_2024': urban_2024,
                    'growth_rate': growth_rate
                })
        
        # Add temporal trends
        for city, temporal in self.temporal_data.items():
            if 'trends' in temporal:
                trends = temporal['trends']
                stats['temperature_trends'].append({
                    'city': city,
                    'suhi_trend_per_year': trends.get('suhi_trend_per_year', 0),
                    'urban_temp_trend': trends.get('urban_temp_trend_per_year', 0),
                    'r_squared': trends.get('suhi_r_squared', 0)
                })
        
        # Calculate rankings
        if stats['suhi_changes']:
            # Highest SUHI increase
            max_increase = max(stats['suhi_changes'], key=lambda x: x['change'])
            stats['city_rankings']['highest_suhi_increase'] = max_increase
            
            # Lowest SUHI (best performance)
            min_change = min(stats['suhi_changes'], key=lambda x: x['change'])
            stats['city_rankings']['lowest_suhi_change'] = min_change
            
            # Highest urban growth
            if stats['urban_growth']:
                max_growth = max(stats['urban_growth'], key=lambda x: x['growth_rate'])
                stats['city_rankings']['highest_urban_growth'] = max_growth
        
        self.summary_stats = stats
        return stats
    
    def create_professional_grid_visualization(self):
        """Create a professional 6-panel grid visualization."""
        print("Creating professional grid visualization...")
        
        # Create figure with professional layout
        fig, axes = plt.subplots(3, 2, figsize=(16, 18))
        fig.suptitle('SUHI Analysis - Uzbekistan Urban Centers\nComprehensive Assessment Report', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        # Flatten axes for easy iteration
        axes = axes.flatten()
        
        # Panel 1: SUHI Comparison (2017 vs 2024)
        ax = axes[0]
        cities = [item['city'] for item in self.summary_stats['suhi_changes']]
        suhi_2017 = [item['suhi_2017'] for item in self.summary_stats['suhi_changes']]
        suhi_2024 = [item['suhi_2024'] for item in self.summary_stats['suhi_changes']]
        
        x = np.arange(len(cities))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, suhi_2017, width, label='2017', 
                      color=self.colors['primary'], alpha=0.8)
        bars2 = ax.bar(x + width/2, suhi_2024, width, label='2024', 
                      color=self.colors['secondary'], alpha=0.8)
        
        ax.set_xlabel('Cities')
        ax.set_ylabel('SUHI Intensity (°C)')
        ax.set_title('A. SUHI Intensity: 2017 vs 2024 Comparison', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(cities, rotation=45, ha='right')
        ax.legend()
        
        # Add value labels on bars
        for bar in bars1:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                   f'{height:.2f}', ha='center', va='bottom', fontsize=8)
        for bar in bars2:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                   f'{height:.2f}', ha='center', va='bottom', fontsize=8)
        
        # Panel 2: SUHI Change Distribution
        ax = axes[1]
        changes = [item['change'] for item in self.summary_stats['suhi_changes']]
        colors_change = [self.colors['accent2'] if x > 0 else self.colors['success'] for x in changes]
        
        bars = ax.bar(cities, changes, color=colors_change, alpha=0.8)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax.set_xlabel('Cities')
        ax.set_ylabel('SUHI Change (°C)')
        ax.set_title('B. SUHI Change Distribution (2024 - 2017)', fontweight='bold')
        ax.set_xticklabels(cities, rotation=45, ha='right')
        
        # Add value labels
        for bar, value in zip(bars, changes):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., 
                   height + (0.01 if height > 0 else -0.03),
                   f'{value:.3f}', ha='center', 
                   va='bottom' if height > 0 else 'top', fontsize=8)
        
        # Panel 3: Urban Growth Analysis
        ax = axes[2]
        growth_cities = [item['city'] for item in self.summary_stats['urban_growth']]
        growth_rates = [item['growth_rate'] for item in self.summary_stats['urban_growth']]
        
        bars = ax.bar(growth_cities, growth_rates, color=self.colors['accent1'], alpha=0.8)
        ax.set_xlabel('Cities')
        ax.set_ylabel('Urban Growth Rate (%)')
        ax.set_title('C. Urban Area Expansion Rate (2017-2024)', fontweight='bold')
        ax.set_xticklabels(growth_cities, rotation=45, ha='right')
        
        # Add value labels
        for bar, value in zip(bars, growth_rates):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.2,
                   f'{value:.1f}%', ha='center', va='bottom', fontsize=8)
        
        # Panel 4: Temperature Trends Scatter Plot
        ax = axes[3]
        if self.summary_stats['temperature_trends']:
            trend_cities = [item['city'] for item in self.summary_stats['temperature_trends']]
            suhi_trends = [item['suhi_trend_per_year'] for item in self.summary_stats['temperature_trends']]
            urban_trends = [item['urban_temp_trend'] for item in self.summary_stats['temperature_trends']]
            r_squared = [item['r_squared'] for item in self.summary_stats['temperature_trends']]
            
            # Size points by R-squared values
            sizes = [max(50, r*200) for r in r_squared]
            
            scatter = ax.scatter(urban_trends, suhi_trends, c=r_squared, 
                               s=sizes, alpha=0.7, cmap='viridis', 
                               edgecolors='black', linewidth=0.5)
            
            # Add city labels
            for i, city in enumerate(trend_cities):
                ax.annotate(city, (urban_trends[i], suhi_trends[i]), 
                           xytext=(5, 5), textcoords='offset points', fontsize=7)
            
            ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
            ax.axvline(x=0, color='black', linestyle='--', alpha=0.5)
            ax.set_xlabel('Urban Temperature Trend (°C/year)')
            ax.set_ylabel('SUHI Trend (°C/year)')
            ax.set_title('D. Annual Temperature Trends Relationship', fontweight='bold')
            
            # Add colorbar
            cbar = plt.colorbar(scatter, ax=ax, shrink=0.8)
            cbar.set_label('R² Value', rotation=270, labelpad=20)
        
        # Panel 5: Box Plot Statistics
        ax = axes[4]
        data_to_plot = [
            [item['suhi_2017'] for item in self.summary_stats['suhi_changes']],
            [item['suhi_2024'] for item in self.summary_stats['suhi_changes']],
            [item['change'] for item in self.summary_stats['suhi_changes']]
        ]
        labels = ['SUHI 2017', 'SUHI 2024', 'SUHI Change']
        
        bp = ax.boxplot(data_to_plot, labels=labels, patch_artist=True)
        colors_box = [self.colors['primary'], self.colors['secondary'], self.colors['info']]
        for patch, color in zip(bp['boxes'], colors_box):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax.set_ylabel('Temperature (°C)')
        ax.set_title('E. SUHI Statistical Distribution', fontweight='bold')
        
        # Panel 6: Top Performers Summary
        ax = axes[5]
        ax.axis('off')  # Turn off axes for text panel
        
        # Create summary text
        summary_text = "F. KEY FINDINGS SUMMARY\\n\\n"
        
        if 'highest_suhi_increase' in self.summary_stats['city_rankings']:
            max_inc = self.summary_stats['city_rankings']['highest_suhi_increase']
            summary_text += f"🔺 Highest SUHI Increase:\\n   {max_inc['city']}: +{max_inc['change']:.3f}°C\\n\\n"
        
        if 'lowest_suhi_change' in self.summary_stats['city_rankings']:
            min_change = self.summary_stats['city_rankings']['lowest_suhi_change']
            summary_text += f"🔽 Best SUHI Performance:\\n   {min_change['city']}: {min_change['change']:.3f}°C\\n\\n"
        
        if 'highest_urban_growth' in self.summary_stats['city_rankings']:
            max_growth = self.summary_stats['city_rankings']['highest_urban_growth']
            summary_text += f"🏙️ Highest Urban Growth:\\n   {max_growth['city']}: {max_growth['growth_rate']:.1f}%\\n\\n"
        
        # Calculate overall statistics
        avg_change = np.mean([item['change'] for item in self.summary_stats['suhi_changes']])
        avg_growth = np.mean([item['growth_rate'] for item in self.summary_stats['urban_growth']])
        
        summary_text += f"📊 Average SUHI Change: {avg_change:.3f}°C\\n"
        summary_text += f"📈 Average Urban Growth: {avg_growth:.1f}%\\n\\n"
        
        summary_text += f"📋 Cities Analyzed: {self.summary_stats['cities_analyzed']}\\n"
        summary_text += f"📅 Analysis Period: 2017-2024"
        
        ax.text(0.05, 0.95, summary_text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', fontfamily='monospace',
               bbox=dict(boxstyle='round,pad=0.5', facecolor=self.colors['neutral'], alpha=0.1))
        
        # Adjust layout
        plt.tight_layout()
        plt.subplots_adjust(top=0.94)
        
        # Save figure
        output_file = self.output_path / "reports" / f"professional_suhi_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_file.parent.mkdir(exist_ok=True)
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        
        print(f"Professional visualization saved: {output_file}")
        plt.show()
        
        return output_file
    
    def create_temporal_analysis_grid(self):
        """Create a temporal analysis grid for selected cities."""
        print("Creating temporal analysis visualization...")
        
        # Select top 6 cities for temporal analysis
        selected_cities = list(self.temporal_data.keys())[:6]
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Temporal SUHI Analysis - Selected Uzbekistan Cities (2017-2024)', 
                    fontsize=16, fontweight='bold')
        
        axes = axes.flatten()
        
        for i, city in enumerate(selected_cities):
            if i >= 6:  # Limit to 6 cities
                break
                
            ax = axes[i]
            
            if city in self.temporal_data:
                data = self.temporal_data[city]['data']
                years = [d['year'] for d in data]
                suhi_values = [d['suhi_intensity'] for d in data]
                urban_temps = [d['urban_temp'] for d in data]
                rural_temps = [d['rural_temp'] for d in data]
                
                # Plot SUHI intensity
                line1 = ax.plot(years, suhi_values, 'o-', label='SUHI Intensity', 
                               color=self.colors['primary'], linewidth=2.5, markersize=6)
                
                # Create secondary y-axis for temperatures
                ax2 = ax.twinx()
                line2 = ax2.plot(years, urban_temps, 's--', label='Urban Temp', 
                                color=self.colors['accent2'], alpha=0.8, markersize=4)
                line3 = ax2.plot(years, rural_temps, '^--', label='Rural Temp', 
                                color=self.colors['success'], alpha=0.8, markersize=4)
                
                # Formatting
                ax.set_xlabel('Year')
                ax.set_ylabel('SUHI Intensity (°C)', color=self.colors['primary'])
                ax2.set_ylabel('Temperature (°C)', color='black')
                ax.set_title(f'{city}', fontweight='bold', fontsize=12)
                
                # Combine legends
                lines = line1 + line2 + line3
                labels = [l.get_label() for l in lines]
                ax.legend(lines, labels, loc='upper left', fontsize=8)
                
                # Add trend line
                if len(years) > 2:
                    z = np.polyfit(years, suhi_values, 1)
                    p = np.poly1d(z)
                    ax.plot(years, p(years), "--", alpha=0.5, color='red', linewidth=1)
                    
                    # Add trend annotation
                    trend = z[0]
                    ax.text(0.05, 0.95, f'Trend: {trend:.4f}°C/year', 
                           transform=ax.transAxes, fontsize=8,
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        # Hide unused subplots
        for i in range(len(selected_cities), 6):
            axes[i].axis('off')
        
        plt.tight_layout()
        
        # Save figure
        output_file = self.output_path / "reports" / f"temporal_suhi_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_file.parent.mkdir(exist_ok=True)
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        
        print(f"Temporal analysis saved: {output_file}")
        plt.show()
        
        return output_file
    
    def generate_detailed_report(self):
        """Generate a detailed markdown report."""
        print("Generating detailed report...")
        
        report_lines = []
        report_lines.append("# COMPREHENSIVE SUHI ANALYSIS REPORT")
        report_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**Analysis Period:** 2017-2024")
        report_lines.append(f"**Cities Analyzed:** {self.summary_stats['cities_analyzed']}")
        report_lines.append("")
        
        # Executive Summary
        report_lines.append("## EXECUTIVE SUMMARY")
        report_lines.append("")
        
        avg_change = np.mean([item['change'] for item in self.summary_stats['suhi_changes']])
        increasing_cities = sum(1 for item in self.summary_stats['suhi_changes'] if item['change'] > 0)
        decreasing_cities = sum(1 for item in self.summary_stats['suhi_changes'] if item['change'] < 0)
        
        report_lines.append(f"- **Average SUHI Change:** {avg_change:.3f}°C")
        report_lines.append(f"- **Cities with Increasing SUHI:** {increasing_cities}")
        report_lines.append(f"- **Cities with Decreasing SUHI:** {decreasing_cities}")
        report_lines.append("")
        
        if 'highest_suhi_increase' in self.summary_stats['city_rankings']:
            max_inc = self.summary_stats['city_rankings']['highest_suhi_increase']
            report_lines.append(f"- **Highest SUHI Increase:** {max_inc['city']} (+{max_inc['change']:.3f}°C)")
        
        if 'lowest_suhi_change' in self.summary_stats['city_rankings']:
            min_change = self.summary_stats['city_rankings']['lowest_suhi_change']
            report_lines.append(f"- **Best SUHI Performance:** {min_change['city']} ({min_change['change']:.3f}°C)")
        
        report_lines.append("")
        
        # Detailed City Analysis
        report_lines.append("## DETAILED CITY ANALYSIS")
        report_lines.append("")
        
        # Sort cities by SUHI change for reporting
        sorted_cities = sorted(self.summary_stats['suhi_changes'], 
                              key=lambda x: x['change'], reverse=True)
        
        for city_data in sorted_cities:
            city = city_data['city']
            report_lines.append(f"### {city.upper()}")
            report_lines.append("")
            report_lines.append(f"- **SUHI 2017:** {city_data['suhi_2017']:.3f}°C")
            report_lines.append(f"- **SUHI 2024:** {city_data['suhi_2024']:.3f}°C")
            report_lines.append(f"- **Change:** {city_data['change']:.3f}°C ({city_data['change_pct']:.1f}%)")
            
            # Add urban growth data
            urban_data = next((item for item in self.summary_stats['urban_growth'] 
                             if item['city'] == city), None)
            if urban_data:
                report_lines.append(f"- **Urban Growth:** {urban_data['growth_rate']:.1f}%")
                report_lines.append(f"- **Urban Pixels 2017:** {urban_data['pixels_2017']:,}")
                report_lines.append(f"- **Urban Pixels 2024:** {urban_data['pixels_2024']:,}")
            
            # Add temporal trend data
            trend_data = next((item for item in self.summary_stats['temperature_trends'] 
                             if item['city'] == city), None)
            if trend_data:
                report_lines.append(f"- **Annual SUHI Trend:** {trend_data['suhi_trend_per_year']:.4f}°C/year")
                report_lines.append(f"- **Trend R²:** {trend_data['r_squared']:.3f}")
            
            report_lines.append("")
        
        # Statistical Summary
        report_lines.append("## STATISTICAL SUMMARY")
        report_lines.append("")
        
        suhi_2017_values = [item['suhi_2017'] for item in self.summary_stats['suhi_changes']]
        suhi_2024_values = [item['suhi_2024'] for item in self.summary_stats['suhi_changes']]
        change_values = [item['change'] for item in self.summary_stats['suhi_changes']]
        
        report_lines.append("### SUHI Intensity Statistics")
        report_lines.append("")
        report_lines.append("| Metric | 2017 | 2024 | Change |")
        report_lines.append("|--------|------|------|--------|")
        report_lines.append(f"| Mean | {np.mean(suhi_2017_values):.3f}°C | {np.mean(suhi_2024_values):.3f}°C | {np.mean(change_values):.3f}°C |")
        report_lines.append(f"| Median | {np.median(suhi_2017_values):.3f}°C | {np.median(suhi_2024_values):.3f}°C | {np.median(change_values):.3f}°C |")
        report_lines.append(f"| Std Dev | {np.std(suhi_2017_values):.3f}°C | {np.std(suhi_2024_values):.3f}°C | {np.std(change_values):.3f}°C |")
        report_lines.append(f"| Min | {np.min(suhi_2017_values):.3f}°C | {np.min(suhi_2024_values):.3f}°C | {np.min(change_values):.3f}°C |")
        report_lines.append(f"| Max | {np.max(suhi_2017_values):.3f}°C | {np.max(suhi_2024_values):.3f}°C | {np.max(change_values):.3f}°C |")
        report_lines.append("")
        
        # Recommendations
        report_lines.append("## RECOMMENDATIONS")
        report_lines.append("")
        
        # Cities with highest increase need attention
        high_increase_cities = [item for item in sorted_cities if item['change'] > avg_change + np.std(change_values)]
        if high_increase_cities:
            report_lines.append("### Priority Cities for Intervention")
            report_lines.append("")
            for city in high_increase_cities:
                report_lines.append(f"- **{city['city']}**: SUHI increased by {city['change']:.3f}°C, requires immediate attention")
            report_lines.append("")
        
        # Cities with good performance
        good_performance_cities = [item for item in sorted_cities if item['change'] < 0]
        if good_performance_cities:
            report_lines.append("### Cities with Improving SUHI Performance")
            report_lines.append("")
            for city in good_performance_cities:
                report_lines.append(f"- **{city['city']}**: SUHI decreased by {abs(city['change']):.3f}°C, study best practices")
            report_lines.append("")
        
        # Save report
        output_file = self.output_path / "reports" / f"detailed_suhi_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\\n'.join(report_lines))
        
        print(f"Detailed report saved: {output_file}")
        return output_file
    
    def export_data_tables(self):
        """Export comprehensive data tables to CSV."""
        print("Exporting data tables...")
        
        # Create comprehensive dataset
        all_data = []
        
        for city_data in self.summary_stats['suhi_changes']:
            city = city_data['city']
            row = {
                'City': city,
                'SUHI_2017_C': city_data['suhi_2017'],
                'SUHI_2024_C': city_data['suhi_2024'],
                'SUHI_Change_C': city_data['change'],
                'SUHI_Change_Percent': city_data['change_pct']
            }
            
            # Add urban growth data
            urban_data = next((item for item in self.summary_stats['urban_growth'] 
                             if item['city'] == city), None)
            if urban_data:
                row.update({
                    'Urban_Pixels_2017': urban_data['pixels_2017'],
                    'Urban_Pixels_2024': urban_data['pixels_2024'],
                    'Urban_Growth_Rate_Percent': urban_data['growth_rate']
                })
            
            # Add temporal trend data
            trend_data = next((item for item in self.summary_stats['temperature_trends'] 
                             if item['city'] == city), None)
            if trend_data:
                row.update({
                    'SUHI_Trend_Per_Year_C': trend_data['suhi_trend_per_year'],
                    'Urban_Temp_Trend_Per_Year_C': trend_data['urban_temp_trend'],
                    'Trend_R_Squared': trend_data['r_squared']
                })
            
            all_data.append(row)
        
        # Create DataFrame and save
        df = pd.DataFrame(all_data)
        output_file = self.output_path / "reports" / f"comprehensive_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output_file.parent.mkdir(exist_ok=True)
        df.to_csv(output_file, index=False)
        
        print(f"Data export saved: {output_file}")
        return output_file
    
    def run_complete_analysis(self):
        """Run the complete professional analysis pipeline."""
        print("="*80)
        print("PROFESSIONAL SUHI ANALYSIS PIPELINE")
        print("="*80)
        
        # Load data and generate statistics
        self.load_all_data()
        self.generate_summary_statistics()
        
        # Create visualizations and reports
        viz_file = self.create_professional_grid_visualization()
        temporal_file = self.create_temporal_analysis_grid()
        report_file = self.generate_detailed_report()
        data_file = self.export_data_tables()
        
        print("\\n" + "="*80)
        print("ANALYSIS COMPLETE - ALL OUTPUTS GENERATED")
        print("="*80)
        print(f"📊 Professional Visualization: {viz_file.name}")
        print(f"📈 Temporal Analysis: {temporal_file.name}")
        print(f"📋 Detailed Report: {report_file.name}")
        print(f"💾 Data Export: {data_file.name}")
        print("="*80)
        
        return {
            'visualization': viz_file,
            'temporal': temporal_file,
            'report': report_file,
            'data': data_file
        }


def main():
    """Main execution function."""
    # Initialize the professional reporter
    data_path = "/Users/timursabitov/Dev/Uzbekistan_URBAN_research/suhi_analysis_output/data"
    reporter = ProfessionalSUHIReporter(data_path)
    
    # Run complete analysis
    results = reporter.run_complete_analysis()
    
    return results


if __name__ == "__main__":
    # Run the analysis
    results = main()
    print("\\nAnalysis pipeline completed successfully!")
