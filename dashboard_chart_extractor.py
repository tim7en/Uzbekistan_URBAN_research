#!/usr/bin/env python3
"""
Dashboard Chart Extractor
=========================

Extracts individual charts from the comprehensive dashboard and saves them
as separate Plotly files in the reporting folder.

This script recreates the dashboard components as individual, standalone charts
with proper 2017 vs 2024 labeling and professional styling.

Author: GitHub Copilot
Date: August 19, 2025
"""

import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
from pathlib import Path
import warnings
from datetime import datetime

# Configure Plotly
warnings.filterwarnings('ignore')
pio.templates.default = "plotly_white"
pio.kaleido.scope.mathjax = None

class DashboardChartExtractor:
    """
    Extracts dashboard charts and saves them as individual files.
    """
    
    def __init__(self, data_path, output_path):
        """Initialize the extractor."""
        self.data_path = Path(data_path)
        self.output_path = Path(output_path) / "dashboard_charts"
        self.output_path.mkdir(exist_ok=True)
        
        self.cities_data = {}
        self.temporal_data = {}
        self.summary_stats = {}
        
        # Dashboard color scheme
        self.colors = {
            'primary_2017': '#636EFA',      # Plotly blue
            'primary_2024': '#EF553B',      # Plotly red
            'positive': '#00CC96',          # Plotly green
            'negative': '#AB63FA',          # Plotly purple
            'neutral': '#FFA15A',           # Plotly orange
            'accent1': '#19D3F3',           # Plotly cyan
            'accent2': '#FF6692',           # Plotly pink
            'accent3': '#B6E880',           # Plotly light green
            'accent4': '#FF97FF'            # Plotly light purple
        }
        
    def load_data(self):
        """Load all SUHI data from JSON files."""
        print("Loading data for dashboard chart extraction...")
        
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
        
        self._calculate_summary_stats()
        print(f"Loaded data for {len(cities)} cities")
        
    def _calculate_summary_stats(self):
        """Calculate summary statistics."""
        self.summary_stats = {
            'suhi_comparison': {'cities': [], 'suhi_2017': [], 'suhi_2024': []},
            'urban_growth': {},
            'temperature_trends': {}
        }
        
        for city, data in self.cities_data.items():
            if 2017 in data and 2024 in data:
                # SUHI comparison
                suhi_2017 = data[2017]['suhi_analysis']['suhi']
                suhi_2024 = data[2024]['suhi_analysis']['suhi']
                
                self.summary_stats['suhi_comparison']['cities'].append(city)
                self.summary_stats['suhi_comparison']['suhi_2017'].append(suhi_2017)
                self.summary_stats['suhi_comparison']['suhi_2024'].append(suhi_2024)
                
                # Urban growth
                urban_2017 = data[2017]['suhi_analysis']['urban_pixels']
                urban_2024 = data[2024]['suhi_analysis']['urban_pixels']
                growth_rate = ((urban_2024 - urban_2017) / urban_2017) * 100
                
                self.summary_stats['urban_growth'][city] = {
                    'pixels_2017': urban_2017,
                    'pixels_2024': urban_2024,
                    'growth_rate': growth_rate
                }
        
        # Temperature trends
        for city, temporal in self.temporal_data.items():
            if 'trends' in temporal:
                trends = temporal['trends']
                self.summary_stats['temperature_trends'][city] = {
                    'suhi_trend_per_year': trends.get('suhi_trend_per_year', 0),
                    'urban_temp_trend': trends.get('urban_temp_trend_per_year', 0),
                    'r_squared': trends.get('suhi_r_squared', 0)
                }
    
    def extract_dashboard_chart_1(self):
        """Dashboard Chart 1: SUHI Comparison 2017 vs 2024"""
        print("Extracting Dashboard Chart 1: SUHI Comparison...")
        
        cities = self.summary_stats['suhi_comparison']['cities']
        suhi_2017 = self.summary_stats['suhi_comparison']['suhi_2017']
        suhi_2024 = self.summary_stats['suhi_comparison']['suhi_2024']
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=cities,
            y=suhi_2017,
            name='SUHI 2017',
            marker_color=self.colors['primary_2017'],
            opacity=0.8,
            text=[f'{val:.2f}' for val in suhi_2017],
            textposition='auto',
        ))
        
        fig.add_trace(go.Bar(
            x=cities,
            y=suhi_2024,
            name='SUHI 2024',
            marker_color=self.colors['primary_2024'],
            opacity=0.8,
            text=[f'{val:.2f}' for val in suhi_2024],
            textposition='auto',
        ))
        
        fig.update_layout(
            title='Dashboard Chart 1: SUHI Comparison 2017 vs 2024',
            xaxis_title='Cities',
            yaxis_title='SUHI Intensity (°C)',
            barmode='group',
            height=500,
            template='plotly_white',
            font=dict(size=12)
        )
        
        # Save
        html_path = self.output_path / "dashboard_01_suhi_comparison_2017_vs_2024.html"
        png_path = self.output_path / "dashboard_01_suhi_comparison_2017_vs_2024.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=900, height=500, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def extract_dashboard_chart_2(self):
        """Dashboard Chart 2: SUHI Change Distribution"""
        print("Extracting Dashboard Chart 2: SUHI Change Distribution...")
        
        cities = self.summary_stats['suhi_comparison']['cities']
        suhi_2017 = self.summary_stats['suhi_comparison']['suhi_2017']
        suhi_2024 = self.summary_stats['suhi_comparison']['suhi_2024']
        
        suhi_changes = [s24 - s17 for s17, s24 in zip(suhi_2017, suhi_2024)]
        colors = [self.colors['primary_2024'] if change > 0 else self.colors['positive'] for change in suhi_changes]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=cities,
            y=suhi_changes,
            marker_color=colors,
            opacity=0.8,
            name='SUHI Change (2024-2017)',
            text=[f'{val:+.3f}' for val in suhi_changes],
            textposition='auto',
        ))
        
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1)
        
        fig.update_layout(
            title='Dashboard Chart 2: SUHI Change Distribution (2024 - 2017)',
            xaxis_title='Cities',
            yaxis_title='SUHI Change (°C)',
            height=500,
            template='plotly_white',
            font=dict(size=12)
        )
        
        # Save
        html_path = self.output_path / "dashboard_02_suhi_change_distribution.html"
        png_path = self.output_path / "dashboard_02_suhi_change_distribution.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=900, height=500, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def extract_dashboard_chart_3(self):
        """Dashboard Chart 3: Urban Growth vs SUHI Change"""
        print("Extracting Dashboard Chart 3: Urban Growth vs SUHI Change...")
        
        cities = self.summary_stats['suhi_comparison']['cities']
        suhi_2017 = self.summary_stats['suhi_comparison']['suhi_2017']
        suhi_2024 = self.summary_stats['suhi_comparison']['suhi_2024']
        suhi_changes = [s24 - s17 for s17, s24 in zip(suhi_2017, suhi_2024)]
        
        growth_rates = []
        for city in cities:
            if city in self.summary_stats['urban_growth']:
                growth_rates.append(self.summary_stats['urban_growth'][city]['growth_rate'])
            else:
                growth_rates.append(0)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=growth_rates[:len(suhi_changes)],
            y=suhi_changes,
            mode='markers+text',
            text=cities,
            textposition="top center",
            marker=dict(
                size=12,
                color=self.colors['accent1'],
                opacity=0.7,
                line=dict(width=1, color='black')
            ),
            name='Cities',
            hovertemplate='<b>%{text}</b><br>' +
                         'Urban Growth: %{x:.1f}%<br>' +
                         'SUHI Change: %{y:.3f}°C<extra></extra>'
        ))
        
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
        fig.add_vline(x=0, line_dash="dash", line_color="black", opacity=0.5)
        
        fig.update_layout(
            title='Dashboard Chart 3: Urban Growth vs SUHI Change (2017-2024)',
            xaxis_title='Urban Growth Rate (%)',
            yaxis_title='SUHI Change (°C)',
            height=500,
            template='plotly_white',
            font=dict(size=12)
        )
        
        # Save
        html_path = self.output_path / "dashboard_03_urban_growth_vs_suhi_change.html"
        png_path = self.output_path / "dashboard_03_urban_growth_vs_suhi_change.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=900, height=500, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def extract_dashboard_chart_4(self):
        """Dashboard Chart 4: Temporal Trends - Selected Cities"""
        print("Extracting Dashboard Chart 4: Temporal Trends...")
        
        selected_cities = ['Tashkent', 'Samarkand', 'Bukhara', 'Andijan']
        
        fig = go.Figure()
        
        colors_cycle = [self.colors['primary_2017'], self.colors['primary_2024'], 
                       self.colors['positive'], self.colors['negative']]
        
        for i, city in enumerate(selected_cities):
            if city in self.temporal_data:
                data = self.temporal_data[city]['data']
                years = [d['year'] for d in data]
                suhi_values = [d['suhi_intensity'] for d in data]
                
                fig.add_trace(go.Scatter(
                    x=years,
                    y=suhi_values,
                    mode='lines+markers',
                    name=f'{city} (2017-2024)',
                    line=dict(color=colors_cycle[i % len(colors_cycle)], width=3),
                    marker=dict(size=6)
                ))
        
        fig.update_layout(
            title='Dashboard Chart 4: Temporal SUHI Trends - Selected Cities (2017-2024)',
            xaxis_title='Year',
            yaxis_title='SUHI Intensity (°C)',
            height=500,
            template='plotly_white',
            font=dict(size=12),
            hovermode='x unified'
        )
        
        # Save
        html_path = self.output_path / "dashboard_04_temporal_trends_selected_cities.html"
        png_path = self.output_path / "dashboard_04_temporal_trends_selected_cities.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=900, height=500, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def extract_dashboard_chart_5(self):
        """Dashboard Chart 5: Temperature Correlation Analysis"""
        print("Extracting Dashboard Chart 5: Temperature Correlation...")
        
        # Prepare correlation data
        cities = self.summary_stats['suhi_comparison']['cities']
        data_for_corr = []
        
        for city in cities:
            if (city in self.summary_stats['urban_growth'] and 
                city in self.summary_stats['temperature_trends']):
                
                suhi_2017 = self.summary_stats['suhi_comparison']['suhi_2017'][
                    self.summary_stats['suhi_comparison']['cities'].index(city)
                ]
                suhi_2024 = self.summary_stats['suhi_comparison']['suhi_2024'][
                    self.summary_stats['suhi_comparison']['cities'].index(city)
                ]
                suhi_change = suhi_2024 - suhi_2017
                
                urban_growth = self.summary_stats['urban_growth'][city]['growth_rate']
                suhi_trend = self.summary_stats['temperature_trends'][city]['suhi_trend_per_year']
                
                data_for_corr.append([suhi_change, urban_growth, suhi_trend])
        
        if data_for_corr:
            df = pd.DataFrame(data_for_corr, columns=['SUHI Change', 'Urban Growth %', 'SUHI Trend/Year'])
            correlation_matrix = df.corr()
            
            fig = go.Figure(data=go.Heatmap(
                z=correlation_matrix.values,
                x=correlation_matrix.columns,
                y=correlation_matrix.columns,
                colorscale='RdBu',
                zmid=0,
                text=correlation_matrix.values,
                texttemplate="%{text:.2f}",
                textfont={"size": 14},
                hoverongaps=False
            ))
            
            fig.update_layout(
                title='Dashboard Chart 5: Temperature Correlation Matrix (2017-2024)',
                height=500,
                width=600,
                template='plotly_white',
                font=dict(size=12)
            )
            
            # Save
            html_path = self.output_path / "dashboard_05_temperature_correlation_matrix.html"
            png_path = self.output_path / "dashboard_05_temperature_correlation_matrix.png"
            
            fig.write_html(str(html_path))
            fig.write_image(str(png_path), width=600, height=500, scale=2)
            
            print(f"Saved: {html_path.name}")
            return fig
    
    def extract_dashboard_chart_6(self):
        """Dashboard Chart 6: Accuracy Assessment Summary"""
        print("Extracting Dashboard Chart 6: Accuracy Assessment...")
        
        # Collect accuracy data for 2024
        accuracy_cities = []
        esa_scores = []
        ghsl_scores = []
        
        for city, data in self.cities_data.items():
            if 2024 in data and 'accuracy_assessment' in data[2024]:
                accuracy_cities.append(city)
                acc_data = data[2024]['accuracy_assessment']
                
                # ESA agreement
                esa_score = 0
                if 'esa_agreement' in acc_data and acc_data['esa_agreement']:
                    esa_score = list(acc_data['esa_agreement'].values())[0]
                esa_scores.append(esa_score)
                
                # GHSL agreement
                ghsl_score = 0
                if 'ghsl_agreement' in acc_data and acc_data['ghsl_agreement']:
                    ghsl_score = list(acc_data['ghsl_agreement'].values())[0]
                ghsl_scores.append(ghsl_score)
        
        if accuracy_cities:
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=accuracy_cities,
                y=esa_scores,
                name='ESA Agreement (2024)',
                marker_color=self.colors['primary_2017'],
                opacity=0.8
            ))
            
            fig.add_trace(go.Bar(
                x=accuracy_cities,
                y=ghsl_scores,
                name='GHSL Agreement (2024)',
                marker_color=self.colors['primary_2024'],
                opacity=0.8
            ))
            
            fig.update_layout(
                title='Dashboard Chart 6: Land Cover Accuracy Assessment (2024)',
                xaxis_title='Cities',
                yaxis_title='Agreement Score',
                height=500,
                template='plotly_white',
                font=dict(size=12),
                barmode='group'
            )
            
            # Save
            html_path = self.output_path / "dashboard_06_accuracy_assessment_2024.html"
            png_path = self.output_path / "dashboard_06_accuracy_assessment_2024.png"
            
            fig.write_html(str(html_path))
            fig.write_image(str(png_path), width=900, height=500, scale=2)
            
            print(f"Saved: {html_path.name}")
            return fig
    
    def extract_all_dashboard_charts(self):
        """Extract all dashboard charts as individual files."""
        print("=" * 80)
        print("EXTRACTING DASHBOARD CHARTS AS INDIVIDUAL FILES")
        print("=" * 80)
        
        # Load data
        self.load_data()
        
        # Extract all charts
        charts = []
        charts.append(self.extract_dashboard_chart_1())
        charts.append(self.extract_dashboard_chart_2())
        charts.append(self.extract_dashboard_chart_3())
        charts.append(self.extract_dashboard_chart_4())
        charts.append(self.extract_dashboard_chart_5())
        charts.append(self.extract_dashboard_chart_6())
        
        print("=" * 80)
        print("ALL DASHBOARD CHARTS EXTRACTED!")
        print("=" * 80)
        print(f"📁 Output directory: {self.output_path}")
        print(f"📊 Dashboard charts created: {len(list(self.output_path.glob('*.html')))} HTML + {len(list(self.output_path.glob('*.png')))} PNG")
        print("=" * 80)
        
        return charts


def main():
    """Main execution function."""
    # Set paths
    data_path = "/Users/timursabitov/Dev/Uzbekistan_URBAN_research/suhi_analysis_output/data"
    output_path = "/Users/timursabitov/Dev/Uzbekistan_URBAN_research/reporting"
    
    # Initialize extractor
    extractor = DashboardChartExtractor(data_path, output_path)
    
    # Extract all dashboard charts
    charts = extractor.extract_all_dashboard_charts()
    
    return charts


if __name__ == "__main__":
    charts = main()
