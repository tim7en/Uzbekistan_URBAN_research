#!/usr/bin/env python3
"""
Comprehensive SUHI Analysis and Visualization Tool
==================================================

This script analyzes Surface Urban Heat Island (SUHI) data from JSON files and creates
comprehensive reports with professional gridded visualizations.

Features:
- Loads and processes SUHI data from multiple cities
- Generates temporal trend analysis
- Creates comparative visualizations across cities
- Produces comprehensive statistical reports
- Exports professional-grade visualizations in grid layouts

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
import scipy.stats as stats
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio

# Configure plotting settings
warnings.filterwarnings('ignore')
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")
pio.templates.default = "plotly_white"

class SUHIAnalyzer:
    """
    Comprehensive SUHI data analyzer and visualization generator.
    """
    
    def __init__(self, data_path):
        """
        Initialize the SUHI analyzer.
        
        Args:
            data_path (str): Path to the SUHI analysis output data directory
        """
        self.data_path = Path(data_path)
        self.cities_data = {}
        self.temporal_data = {}
        self.comparative_stats = {}
        
        # Define consistent colors for each city
        self.city_colors = {
            'Tashkent': '#1f77b4', 'Samarkand': '#ff7f0e', 'Bukhara': '#2ca02c',
            'Andijan': '#d62728', 'Namangan': '#9467bd', 'Fergana': '#8c564b',
            'Nukus': '#e377c2', 'Urgench': '#7f7f7f', 'Termez': '#bcbd22',
            'Qarshi': '#17becf', 'Jizzakh': '#ff9896', 'Navoiy': '#98df8a',
            'Gulistan': '#c5b0d5', 'Nurafshon': '#c49c94'
        }
        
    def load_data(self):
        """Load all SUHI data from JSON files."""
        print("Loading SUHI data...")
        
        # Load individual city results
        for file_path in self.data_path.glob("*_2017_results.json"):
            city_name = file_path.stem.replace("_2017_results", "")
            self.cities_data[city_name] = {}
            
            # Load 2017 and 2024 data
            for year in [2017, 2024]:
                year_file = self.data_path / f"{city_name}_{year}_results.json"
                if year_file.exists():
                    with open(year_file, 'r') as f:
                        self.cities_data[city_name][year] = json.load(f)
        
        # Load temporal trend data
        for file_path in self.data_path.glob("*_annual_suhi_trends.json"):
            city_name = file_path.stem.replace("_annual_suhi_trends", "")
            with open(file_path, 'r') as f:
                self.temporal_data[city_name] = json.load(f)
        
        print(f"Loaded data for {len(self.cities_data)} cities")
        
    def calculate_comparative_statistics(self):
        """Calculate comprehensive comparative statistics across cities."""
        print("Calculating comparative statistics...")
        
        self.comparative_stats = {
            'suhi_comparison': {},
            'urban_growth': {},
            'temperature_trends': {},
            'accuracy_assessment': {}
        }
        
        # SUHI comparison statistics
        suhi_2017 = []
        suhi_2024 = []
        city_names = []
        
        for city, data in self.cities_data.items():
            if 2017 in data and 2024 in data:
                suhi_2017.append(data[2017]['suhi_analysis']['suhi'])
                suhi_2024.append(data[2024]['suhi_analysis']['suhi'])
                city_names.append(city)
        
        self.comparative_stats['suhi_comparison'] = {
            'cities': city_names,
            'suhi_2017': suhi_2017,
            'suhi_2024': suhi_2024,
            'mean_change': np.mean(np.array(suhi_2024) - np.array(suhi_2017)),
            'median_change': np.median(np.array(suhi_2024) - np.array(suhi_2017)),
            'max_increase': max(np.array(suhi_2024) - np.array(suhi_2017)),
            'max_decrease': min(np.array(suhi_2024) - np.array(suhi_2017))
        }
        
        # Urban growth analysis
        for city, data in self.cities_data.items():
            if 2017 in data and 2024 in data:
                urban_2017 = data[2017]['suhi_analysis']['urban_pixels']
                urban_2024 = data[2024]['suhi_analysis']['urban_pixels']
                growth_rate = ((urban_2024 - urban_2017) / urban_2017) * 100
                
                self.comparative_stats['urban_growth'][city] = {
                    'urban_pixels_2017': urban_2017,
                    'urban_pixels_2024': urban_2024,
                    'growth_rate_pct': growth_rate,
                    'absolute_growth': urban_2024 - urban_2017
                }
        
        # Temperature trends from temporal data
        for city, temporal in self.temporal_data.items():
            trends = temporal.get('trends', {})
            self.comparative_stats['temperature_trends'][city] = {
                'suhi_trend_per_year': trends.get('suhi_trend_per_year', 0),
                'urban_temp_trend_per_year': trends.get('urban_temp_trend_per_year', 0),
                'r_squared': trends.get('suhi_r_squared', 0),
                'p_value': trends.get('suhi_p_value', 1)
            }
    
    def create_comprehensive_report(self):
        """Generate a comprehensive statistical report."""
        print("Generating comprehensive report...")
        
        report_content = []
        report_content.append("# COMPREHENSIVE SUHI ANALYSIS REPORT")
        report_content.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_content.append("\n## EXECUTIVE SUMMARY")
        
        # Overall statistics
        suhi_changes = np.array(self.comparative_stats['suhi_comparison']['suhi_2024']) - \
                      np.array(self.comparative_stats['suhi_comparison']['suhi_2017'])
        
        report_content.append(f"- **Cities Analyzed**: {len(self.comparative_stats['suhi_comparison']['cities'])}")
        report_content.append(f"- **Average SUHI Change (2017-2024)**: {self.comparative_stats['suhi_comparison']['mean_change']:.3f}°C")
        report_content.append(f"- **Cities with Increasing SUHI**: {np.sum(suhi_changes > 0)}")
        report_content.append(f"- **Cities with Decreasing SUHI**: {np.sum(suhi_changes < 0)}")
        
        # Top performers and concerns
        cities = self.comparative_stats['suhi_comparison']['cities']
        max_increase_idx = np.argmax(suhi_changes)
        max_decrease_idx = np.argmin(suhi_changes)
        
        report_content.append(f"- **Highest SUHI Increase**: {cities[max_increase_idx]} (+{suhi_changes[max_increase_idx]:.3f}°C)")
        report_content.append(f"- **Highest SUHI Decrease**: {cities[max_decrease_idx]} ({suhi_changes[max_decrease_idx]:.3f}°C)")
        
        report_content.append("\n## DETAILED CITY ANALYSIS")
        
        # Individual city analysis
        for city in sorted(cities):
            if city in self.cities_data and 2017 in self.cities_data[city] and 2024 in self.cities_data[city]:
                data_2017 = self.cities_data[city][2017]
                data_2024 = self.cities_data[city][2024]
                
                report_content.append(f"\n### {city.upper()}")
                report_content.append(f"- **SUHI 2017**: {data_2017['suhi_analysis']['suhi']:.3f}°C ± {data_2017['suhi_analysis']['suhi_se']:.3f}")
                report_content.append(f"- **SUHI 2024**: {data_2024['suhi_analysis']['suhi']:.3f}°C ± {data_2024['suhi_analysis']['suhi_se']:.3f}")
                
                suhi_change = data_2024['suhi_analysis']['suhi'] - data_2017['suhi_analysis']['suhi']
                report_content.append(f"- **SUHI Change**: {suhi_change:.3f}°C")
                
                if city in self.comparative_stats['urban_growth']:
                    growth = self.comparative_stats['urban_growth'][city]
                    report_content.append(f"- **Urban Growth**: {growth['growth_rate_pct']:.1f}% ({growth['absolute_growth']} pixels)")
                
                if city in self.comparative_stats['temperature_trends']:
                    trends = self.comparative_stats['temperature_trends'][city]
                    report_content.append(f"- **Annual SUHI Trend**: {trends['suhi_trend_per_year']:.4f}°C/year (R² = {trends['r_squared']:.3f})")
        
        # Save report
        report_path = self.data_path.parent / "reports" / f"comprehensive_suhi_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            f.write('\n'.join(report_content))
        
        print(f"Report saved to: {report_path}")
        return report_path
    
    def create_gridded_visualizations(self):
        """Create comprehensive gridded visualizations."""
        print("Creating gridded visualizations...")
        
        # Set up the figure with subplots
        fig = plt.figure(figsize=(20, 24))
        gs = fig.add_gridspec(6, 4, hspace=0.3, wspace=0.3)
        
        # 1. SUHI Comparison 2017 vs 2024 (Top row, spans 2 columns)
        ax1 = fig.add_subplot(gs[0, :2])
        cities = self.comparative_stats['suhi_comparison']['cities']
        suhi_2017 = self.comparative_stats['suhi_comparison']['suhi_2017']
        suhi_2024 = self.comparative_stats['suhi_comparison']['suhi_2024']
        
        x = np.arange(len(cities))
        width = 0.35
        
        bars1 = ax1.bar(x - width/2, suhi_2017, width, label='2017', alpha=0.8, color='skyblue')
        bars2 = ax1.bar(x + width/2, suhi_2024, width, label='2024', alpha=0.8, color='coral')
        
        ax1.set_xlabel('Cities')
        ax1.set_ylabel('SUHI Intensity (°C)')
        ax1.set_title('SUHI Intensity Comparison: 2017 vs 2024', fontsize=14, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(cities, rotation=45, ha='right')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for bar1, bar2 in zip(bars1, bars2):
            height1 = bar1.get_height()
            height2 = bar2.get_height()
            ax1.text(bar1.get_x() + bar1.get_width()/2., height1 + 0.01,
                    f'{height1:.2f}', ha='center', va='bottom', fontsize=8)
            ax1.text(bar2.get_x() + bar2.get_width()/2., height2 + 0.01,
                    f'{height2:.2f}', ha='center', va='bottom', fontsize=8)
        
        # 2. SUHI Change Distribution (Top row, right side)
        ax2 = fig.add_subplot(gs[0, 2:])
        suhi_changes = np.array(suhi_2024) - np.array(suhi_2017)
        
        # Create histogram with color coding
        colors = ['red' if x > 0 else 'green' for x in suhi_changes]
        bars = ax2.bar(cities, suhi_changes, color=colors, alpha=0.7)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax2.set_xlabel('Cities')
        ax2.set_ylabel('SUHI Change (°C)')
        ax2.set_title('SUHI Change (2024 - 2017)', fontsize=14, fontweight='bold')
        ax2.set_xticklabels(cities, rotation=45, ha='right')
        ax2.grid(True, alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars, suhi_changes):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + (0.01 if height > 0 else -0.03),
                    f'{value:.3f}', ha='center', va='bottom' if height > 0 else 'top', fontsize=8)
        
        # 3. Urban Growth Analysis (Second row, left)
        ax3 = fig.add_subplot(gs[1, :2])
        growth_cities = []
        growth_rates = []
        
        for city, growth in self.comparative_stats['urban_growth'].items():
            growth_cities.append(city)
            growth_rates.append(growth['growth_rate_pct'])
        
        bars = ax3.bar(growth_cities, growth_rates, 
                      color=[self.city_colors.get(city, 'gray') for city in growth_cities],
                      alpha=0.8)
        ax3.set_xlabel('Cities')
        ax3.set_ylabel('Urban Growth Rate (%)')
        ax3.set_title('Urban Area Growth Rate (2017-2024)', fontsize=14, fontweight='bold')
        ax3.set_xticklabels(growth_cities, rotation=45, ha='right')
        ax3.grid(True, alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars, growth_rates):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{value:.1f}%', ha='center', va='bottom', fontsize=8)
        
        # 4. Temperature Trends Scatter Plot (Second row, right)
        ax4 = fig.add_subplot(gs[1, 2:])
        trend_cities = []
        suhi_trends = []
        urban_trends = []
        
        for city, trends in self.comparative_stats['temperature_trends'].items():
            trend_cities.append(city)
            suhi_trends.append(trends['suhi_trend_per_year'])
            urban_trends.append(trends['urban_temp_trend_per_year'])
        
        scatter = ax4.scatter(urban_trends, suhi_trends, 
                            c=[self.city_colors.get(city, 'gray') for city in trend_cities],
                            s=100, alpha=0.7, edgecolors='black', linewidth=0.5)
        
        # Add city labels
        for i, city in enumerate(trend_cities):
            ax4.annotate(city, (urban_trends[i], suhi_trends[i]), 
                        xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        ax4.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax4.axvline(x=0, color='black', linestyle='--', alpha=0.5)
        ax4.set_xlabel('Urban Temperature Trend (°C/year)')
        ax4.set_ylabel('SUHI Trend (°C/year)')
        ax4.set_title('Temperature Trends Relationship', fontsize=14, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        
        # 5-8. Individual city temporal analysis (Rows 3-4)
        selected_cities = ['Tashkent', 'Samarkand', 'Bukhara', 'Andijan']
        for i, city in enumerate(selected_cities):
            if city in self.temporal_data:
                row = 2 + i // 2
                col = (i % 2) * 2
                ax = fig.add_subplot(gs[row, col:col+2])
                
                data = self.temporal_data[city]['data']
                years = [d['year'] for d in data]
                suhi_values = [d['suhi_intensity'] for d in data]
                urban_temps = [d['urban_temp'] for d in data]
                rural_temps = [d['rural_temp'] for d in data]
                
                ax.plot(years, suhi_values, 'o-', label='SUHI Intensity', 
                       color=self.city_colors.get(city, 'blue'), linewidth=2, markersize=6)
                ax2_temp = ax.twinx()
                ax2_temp.plot(years, urban_temps, 's--', label='Urban Temp', 
                             color='red', alpha=0.7, markersize=4)
                ax2_temp.plot(years, rural_temps, '^--', label='Rural Temp', 
                             color='green', alpha=0.7, markersize=4)
                
                ax.set_xlabel('Year')
                ax.set_ylabel('SUHI Intensity (°C)', color=self.city_colors.get(city, 'blue'))
                ax2_temp.set_ylabel('Temperature (°C)', color='black')
                ax.set_title(f'{city} - Temporal SUHI Analysis', fontsize=12, fontweight='bold')
                ax.grid(True, alpha=0.3)
                
                # Combine legends
                lines1, labels1 = ax.get_legend_handles_labels()
                lines2, labels2 = ax2_temp.get_legend_handles_labels()
                ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=8)
        
        # 9. Correlation Matrix (Row 5, left)
        ax9 = fig.add_subplot(gs[4, :2])
        
        # Prepare correlation data
        corr_data = []
        for city in cities:
            if (city in self.cities_data and 2017 in self.cities_data[city] and 2024 in self.cities_data[city] and 
                city in self.comparative_stats['urban_growth'] and city in self.comparative_stats['temperature_trends']):
                
                suhi_change = (self.cities_data[city][2024]['suhi_analysis']['suhi'] - 
                              self.cities_data[city][2017]['suhi_analysis']['suhi'])
                urban_growth = self.comparative_stats['urban_growth'][city]['growth_rate_pct']
                suhi_trend = self.comparative_stats['temperature_trends'][city]['suhi_trend_per_year']
                
                corr_data.append([suhi_change, urban_growth, suhi_trend])
        
        if corr_data:
            corr_df = pd.DataFrame(corr_data, columns=['SUHI Change', 'Urban Growth %', 'SUHI Trend/Year'])
            correlation_matrix = corr_df.corr()
            
            im = ax9.imshow(correlation_matrix, cmap='coolwarm', vmin=-1, vmax=1)
            ax9.set_xticks(range(len(correlation_matrix.columns)))
            ax9.set_yticks(range(len(correlation_matrix.columns)))
            ax9.set_xticklabels(correlation_matrix.columns, rotation=45, ha='right')
            ax9.set_yticklabels(correlation_matrix.columns)
            ax9.set_title('Correlation Matrix', fontsize=12, fontweight='bold')
            
            # Add correlation values
            for i in range(len(correlation_matrix)):
                for j in range(len(correlation_matrix.columns)):
                    text = ax9.text(j, i, f'{correlation_matrix.iloc[i, j]:.2f}',
                                   ha="center", va="center", color="black", fontweight='bold')
            
            plt.colorbar(im, ax=ax9, shrink=0.8)
        
        # 10. Statistical Summary Box Plot (Row 5, right)
        ax10 = fig.add_subplot(gs[4, 2:])
        
        # Prepare box plot data
        box_data = [suhi_2017, suhi_2024, suhi_changes]
        box_labels = ['SUHI 2017', 'SUHI 2024', 'SUHI Change']
        
        bp = ax10.boxplot(box_data, labels=box_labels, patch_artist=True)
        colors = ['lightblue', 'lightcoral', 'lightgreen']
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
        
        ax10.set_ylabel('Temperature (°C)')
        ax10.set_title('SUHI Distribution Statistics', fontsize=12, fontweight='bold')
        ax10.grid(True, alpha=0.3)
        
        # 11. Accuracy Assessment Summary (Row 6, spans all columns)
        ax11 = fig.add_subplot(gs[5, :])
        
        # Collect accuracy data
        accuracy_methods = ['dynamic_world', 'esa', 'ghsl', 'modis_lc']
        accuracy_scores = {method: [] for method in accuracy_methods}
        accuracy_cities = []
        
        for city, data in self.cities_data.items():
            if 2024 in data and 'accuracy_assessment' in data[2024]:
                accuracy_cities.append(city)
                acc_data = data[2024]['accuracy_assessment']
                
                for method in accuracy_methods:
                    if f'{method}_agreement' in acc_data:
                        # Get the first value from the agreement dictionary
                        agreement_dict = acc_data[f'{method}_agreement']
                        if agreement_dict:
                            score = list(agreement_dict.values())[0]
                            accuracy_scores[method].append(score)
                        else:
                            accuracy_scores[method].append(0)
                    else:
                        accuracy_scores[method].append(0)
        
        # Create stacked bar chart
        bottom = np.zeros(len(accuracy_cities))
        colors_acc = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        
        for i, method in enumerate(accuracy_methods):
            if accuracy_scores[method]:
                ax11.bar(accuracy_cities, accuracy_scores[method], bottom=bottom, 
                        label=method.replace('_', ' ').title(), alpha=0.8, color=colors_acc[i])
                bottom += np.array(accuracy_scores[method])
        
        ax11.set_xlabel('Cities')
        ax11.set_ylabel('Agreement Score')
        ax11.set_title('Land Cover Classification Accuracy Assessment (2024)', fontsize=14, fontweight='bold')
        ax11.set_xticklabels(accuracy_cities, rotation=45, ha='right')
        ax11.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax11.grid(True, alpha=0.3)
        
        # Add overall title
        fig.suptitle('COMPREHENSIVE SUHI ANALYSIS - UZBEKISTAN URBAN RESEARCH', 
                    fontsize=18, fontweight='bold', y=0.98)
        
        # Save the comprehensive visualization
        output_path = self.data_path.parent / "visualizations" / f"comprehensive_suhi_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_path.parent.mkdir(exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"Comprehensive visualization saved to: {output_path}")
        
        plt.show()
        return output_path
    
    def create_interactive_dashboard(self):
        """Create an interactive Plotly dashboard."""
        print("Creating interactive dashboard...")
        
        # Create subplot structure
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'SUHI Comparison: 2017 vs 2024',
                'SUHI Change Distribution',
                'Urban Growth vs SUHI Change',
                'Temporal Trends - Selected Cities',
                'Temperature Correlation Analysis',
                'Accuracy Assessment Summary'
            ),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": True}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # 1. SUHI Comparison
        cities = self.comparative_stats['suhi_comparison']['cities']
        suhi_2017 = self.comparative_stats['suhi_comparison']['suhi_2017']
        suhi_2024 = self.comparative_stats['suhi_comparison']['suhi_2024']
        
        fig.add_trace(
            go.Bar(x=cities, y=suhi_2017, name='2017', marker_color='lightblue', opacity=0.8),
            row=1, col=1
        )
        fig.add_trace(
            go.Bar(x=cities, y=suhi_2024, name='2024', marker_color='lightcoral', opacity=0.8),
            row=1, col=1
        )
        
        # 2. SUHI Change
        suhi_changes = np.array(suhi_2024) - np.array(suhi_2017)
        colors = ['red' if x > 0 else 'green' for x in suhi_changes]
        
        fig.add_trace(
            go.Bar(x=cities, y=suhi_changes, marker_color=colors, opacity=0.7, name='SUHI Change'),
            row=1, col=2
        )
        
        # 3. Urban Growth vs SUHI Change
        growth_rates = []
        for city in cities:
            if city in self.comparative_stats['urban_growth']:
                growth_rates.append(self.comparative_stats['urban_growth'][city]['growth_rate_pct'])
            else:
                growth_rates.append(0)
        
        fig.add_trace(
            go.Scatter(
                x=growth_rates[:len(suhi_changes)], 
                y=suhi_changes,
                mode='markers+text',
                text=cities,
                textposition="top center",
                marker=dict(size=10, opacity=0.7),
                name='Cities'
            ),
            row=2, col=1
        )
        
        # 4. Temporal trends for selected cities
        selected_cities = ['Tashkent', 'Samarkand', 'Bukhara', 'Andijan']
        for city in selected_cities:
            if city in self.temporal_data:
                data = self.temporal_data[city]['data']
                years = [d['year'] for d in data]
                suhi_values = [d['suhi_intensity'] for d in data]
                
                fig.add_trace(
                    go.Scatter(
                        x=years, y=suhi_values,
                        mode='lines+markers',
                        name=city,
                        line=dict(color=self.city_colors.get(city, 'blue'))
                    ),
                    row=2, col=2
                )
        
        # 5. Temperature correlation heatmap
        corr_data = []
        corr_cities = []
        for city in cities:
            if (city in self.cities_data and 2017 in self.cities_data[city] and 2024 in self.cities_data[city] and 
                city in self.comparative_stats['urban_growth'] and city in self.comparative_stats['temperature_trends']):
                
                suhi_change = (self.cities_data[city][2024]['suhi_analysis']['suhi'] - 
                              self.cities_data[city][2017]['suhi_analysis']['suhi'])
                urban_growth = self.comparative_stats['urban_growth'][city]['growth_rate_pct']
                suhi_trend = self.comparative_stats['temperature_trends'][city]['suhi_trend_per_year']
                
                corr_data.append([suhi_change, urban_growth, suhi_trend])
                corr_cities.append(city)
        
        if corr_data:
            corr_df = pd.DataFrame(corr_data, columns=['SUHI Change', 'Urban Growth %', 'SUHI Trend/Year'])
            correlation_matrix = corr_df.corr()
            
            fig.add_trace(
                go.Heatmap(
                    z=correlation_matrix.values,
                    x=correlation_matrix.columns,
                    y=correlation_matrix.columns,
                    colorscale='RdBu',
                    zmid=0,
                    text=correlation_matrix.values,
                    texttemplate="%{text:.2f}",
                    textfont={"size": 12},
                    showscale=True
                ),
                row=3, col=1
            )
        
        # 6. Accuracy assessment
        accuracy_cities = []
        esa_scores = []
        ghsl_scores = []
        
        for city, data in self.cities_data.items():
            if 2024 in data and 'accuracy_assessment' in data[2024]:
                accuracy_cities.append(city)
                acc_data = data[2024]['accuracy_assessment']
                
                esa_score = 0
                if 'esa_agreement' in acc_data and acc_data['esa_agreement']:
                    esa_score = list(acc_data['esa_agreement'].values())[0]
                esa_scores.append(esa_score)
                
                ghsl_score = 0
                if 'ghsl_agreement' in acc_data and acc_data['ghsl_agreement']:
                    ghsl_score = list(acc_data['ghsl_agreement'].values())[0]
                ghsl_scores.append(ghsl_score)
        
        fig.add_trace(
            go.Bar(x=accuracy_cities, y=esa_scores, name='ESA Agreement', marker_color='lightblue'),
            row=3, col=2
        )
        fig.add_trace(
            go.Bar(x=accuracy_cities, y=ghsl_scores, name='GHSL Agreement', marker_color='lightgreen'),
            row=3, col=2
        )
        
        # Update layout
        fig.update_layout(
            title_text="Interactive SUHI Analysis Dashboard - Uzbekistan Urban Research",
            title_x=0.5,
            height=1200,
            showlegend=True,
            template="plotly_white"
        )
        
        # Update axes labels
        fig.update_xaxes(title_text="Cities", row=1, col=1)
        fig.update_yaxes(title_text="SUHI Intensity (°C)", row=1, col=1)
        fig.update_xaxes(title_text="Cities", row=1, col=2)
        fig.update_yaxes(title_text="SUHI Change (°C)", row=1, col=2)
        fig.update_xaxes(title_text="Urban Growth Rate (%)", row=2, col=1)
        fig.update_yaxes(title_text="SUHI Change (°C)", row=2, col=1)
        fig.update_xaxes(title_text="Year", row=2, col=2)
        fig.update_yaxes(title_text="SUHI Intensity (°C)", row=2, col=2)
        fig.update_xaxes(title_text="Cities", row=3, col=2)
        fig.update_yaxes(title_text="Agreement Score", row=3, col=2)
        
        # Save interactive dashboard
        output_path = self.data_path.parent / "visualizations" / f"interactive_suhi_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        output_path.parent.mkdir(exist_ok=True)
        fig.write_html(str(output_path))
        print(f"Interactive dashboard saved to: {output_path}")
        
        return output_path
    
    def export_summary_statistics(self):
        """Export comprehensive summary statistics to CSV."""
        print("Exporting summary statistics...")
        
        # Prepare comprehensive dataset
        summary_data = []
        
        for city in self.comparative_stats['suhi_comparison']['cities']:
            row = {'City': city}
            
            # SUHI data
            idx = self.comparative_stats['suhi_comparison']['cities'].index(city)
            row['SUHI_2017'] = self.comparative_stats['suhi_comparison']['suhi_2017'][idx]
            row['SUHI_2024'] = self.comparative_stats['suhi_comparison']['suhi_2024'][idx]
            row['SUHI_Change'] = row['SUHI_2024'] - row['SUHI_2017']
            
            # Urban growth data
            if city in self.comparative_stats['urban_growth']:
                growth = self.comparative_stats['urban_growth'][city]
                row['Urban_Pixels_2017'] = growth['urban_pixels_2017']
                row['Urban_Pixels_2024'] = growth['urban_pixels_2024']
                row['Urban_Growth_Rate_Pct'] = growth['growth_rate_pct']
                row['Urban_Growth_Absolute'] = growth['absolute_growth']
            
            # Temperature trends
            if city in self.comparative_stats['temperature_trends']:
                trends = self.comparative_stats['temperature_trends'][city]
                row['SUHI_Trend_Per_Year'] = trends['suhi_trend_per_year']
                row['Urban_Temp_Trend_Per_Year'] = trends['urban_temp_trend_per_year']
                row['Trend_R_Squared'] = trends['r_squared']
                row['Trend_P_Value'] = trends['p_value']
            
            # Accuracy assessment (2024)
            if city in self.cities_data and 2024 in self.cities_data[city]:
                acc_data = self.cities_data[city][2024].get('accuracy_assessment', {})
                
                if 'esa_agreement' in acc_data and acc_data['esa_agreement']:
                    row['ESA_Agreement'] = list(acc_data['esa_agreement'].values())[0]
                
                if 'ghsl_agreement' in acc_data and acc_data['ghsl_agreement']:
                    row['GHSL_Agreement'] = list(acc_data['ghsl_agreement'].values())[0]
                
                if 'modis_lc_agreement' in acc_data and acc_data['modis_lc_agreement']:
                    row['MODIS_Agreement'] = list(acc_data['modis_lc_agreement'].values())[0]
            
            summary_data.append(row)
        
        # Create DataFrame and save
        summary_df = pd.DataFrame(summary_data)
        output_path = self.data_path.parent / "reports" / f"comprehensive_summary_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output_path.parent.mkdir(exist_ok=True)
        summary_df.to_csv(output_path, index=False)
        
        print(f"Summary statistics exported to: {output_path}")
        return output_path
    
    def run_complete_analysis(self):
        """Run the complete analysis pipeline."""
        print("=" * 60)
        print("COMPREHENSIVE SUHI ANALYSIS PIPELINE")
        print("=" * 60)
        
        # Load and process data
        self.load_data()
        self.calculate_comparative_statistics()
        
        # Generate outputs
        report_path = self.create_comprehensive_report()
        viz_path = self.create_gridded_visualizations()
        dashboard_path = self.create_interactive_dashboard()
        stats_path = self.export_summary_statistics()
        
        print("\n" + "=" * 60)
        print("ANALYSIS COMPLETE!")
        print("=" * 60)
        print(f"📊 Report: {report_path}")
        print(f"📈 Visualizations: {viz_path}")
        print(f"🌐 Interactive Dashboard: {dashboard_path}")
        print(f"📋 Summary Statistics: {stats_path}")
        print("=" * 60)
        
        return {
            'report': report_path,
            'visualizations': viz_path,
            'dashboard': dashboard_path,
            'statistics': stats_path
        }


def main():
    """Main execution function."""
    # Initialize analyzer
    data_path = "suhi_analysis_output/data"
    analyzer = SUHIAnalyzer(data_path)
    
    # Run complete analysis
    results = analyzer.run_complete_analysis()
    
    return results


if __name__ == "__main__":
    results = main()
