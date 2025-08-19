#!/usr/bin/env python3
"""
Individual Chart Generator for SUHI Analysis
============================================

Creates separate Plotly charts for comprehensive SUHI analysis reporting.
Each chart is exported as both HTML and PNG for maximum flexibility.

Features:
- Individual Plotly charts for each analysis component
- 2017 vs 2024 comparisons clearly indicated
- Professional styling and export options
- Dedicated reporting folder organization

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

class SUHIChartGenerator:
    """
    Individual chart generator for SUHI analysis reporting.
    """
    
    def __init__(self, data_path, output_path):
        """Initialize the chart generator."""
        self.data_path = Path(data_path)
        self.output_path = Path(output_path)
        self.output_path.mkdir(exist_ok=True)
        
        self.cities_data = {}
        self.temporal_data = {}
        self.summary_stats = {}
        
        # Professional color palette
        self.colors = {
            'primary_2017': '#1f77b4',      # Blue for 2017
            'primary_2024': '#ff7f0e',      # Orange for 2024
            'positive': '#d62728',          # Red for increases
            'negative': '#2ca02c',          # Green for decreases
            'neutral': '#7f7f7f',           # Gray for neutral
            'accent1': '#9467bd',           # Purple
            'accent2': '#8c564b',           # Brown
            'accent3': '#e377c2',           # Pink
            'accent4': '#17becf'            # Cyan
        }
        
        # City-specific colors for consistency
        self.city_colors = {
            'Tashkent': '#1f77b4', 'Samarkand': '#ff7f0e', 'Bukhara': '#2ca02c',
            'Andijan': '#d62728', 'Namangan': '#9467bd', 'Fergana': '#8c564b',
            'Nukus': '#e377c2', 'Urgench': '#7f7f7f', 'Termez': '#bcbd22',
            'Qarshi': '#17becf', 'Jizzakh': '#ff9896', 'Navoiy': '#98df8a',
            'Gulistan': '#c5b0d5', 'Nurafshon': '#c49c94'
        }
        
    def load_data(self):
        """Load all SUHI data from JSON files."""
        print("Loading SUHI data for chart generation...")
        
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
        """Calculate summary statistics for analysis."""
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
    
    def create_suhi_comparison_chart(self):
        """Chart 1: SUHI Intensity Comparison 2017 vs 2024"""
        print("Creating SUHI Comparison Chart...")
        
        cities = self.summary_stats['suhi_comparison']['cities']
        suhi_2017 = self.summary_stats['suhi_comparison']['suhi_2017']
        suhi_2024 = self.summary_stats['suhi_comparison']['suhi_2024']
        
        fig = go.Figure()
        
        # Add 2017 bars
        fig.add_trace(go.Bar(
            x=cities,
            y=suhi_2017,
            name='SUHI 2017',
            marker_color=self.colors['primary_2017'],
            opacity=0.8,
            text=[f'{val:.2f}°C' for val in suhi_2017],
            textposition='auto',
        ))
        
        # Add 2024 bars
        fig.add_trace(go.Bar(
            x=cities,
            y=suhi_2024,
            name='SUHI 2024',
            marker_color=self.colors['primary_2024'],
            opacity=0.8,
            text=[f'{val:.2f}°C' for val in suhi_2024],
            textposition='auto',
        ))
        
        # Update layout
        fig.update_layout(
            title={
                'text': 'SUHI Intensity Comparison: 2017 vs 2024<br><sub>Uzbekistan Urban Centers</sub>',
                'x': 0.5,
                'font': {'size': 18}
            },
            xaxis_title='Cities',
            yaxis_title='SUHI Intensity (°C)',
            barmode='group',
            height=600,
            width=1000,
            font=dict(size=12),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            template='plotly_white'
        )
        
        # Add zero line
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
        
        # Save as HTML and PNG
        html_path = self.output_path / "01_suhi_comparison_2017_vs_2024.html"
        png_path = self.output_path / "01_suhi_comparison_2017_vs_2024.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=1000, height=600, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def create_suhi_change_chart(self):
        """Chart 2: SUHI Change Distribution (2024 - 2017)"""
        print("Creating SUHI Change Chart...")
        
        cities = self.summary_stats['suhi_comparison']['cities']
        suhi_2017 = self.summary_stats['suhi_comparison']['suhi_2017']
        suhi_2024 = self.summary_stats['suhi_comparison']['suhi_2024']
        
        suhi_changes = [s24 - s17 for s17, s24 in zip(suhi_2017, suhi_2024)]
        
        # Color based on increase/decrease
        colors = [self.colors['positive'] if change > 0 else self.colors['negative'] 
                 for change in suhi_changes]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=cities,
            y=suhi_changes,
            marker_color=colors,
            opacity=0.8,
            text=[f'{val:+.3f}°C' for val in suhi_changes],
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>SUHI Change: %{y:.3f}°C<extra></extra>'
        ))
        
        # Add zero line
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1)
        
        fig.update_layout(
            title={
                'text': 'SUHI Change Distribution (2024 - 2017)<br><sub>Red: Increase | Green: Decrease</sub>',
                'x': 0.5,
                'font': {'size': 18}
            },
            xaxis_title='Cities',
            yaxis_title='SUHI Change (°C)',
            height=600,
            width=1000,
            font=dict(size=12),
            template='plotly_white'
        )
        
        # Save as HTML and PNG
        html_path = self.output_path / "02_suhi_change_distribution_2017_to_2024.html"
        png_path = self.output_path / "02_suhi_change_distribution_2017_to_2024.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=1000, height=600, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def create_urban_growth_chart(self):
        """Chart 3: Urban Growth Analysis (2017-2024)"""
        print("Creating Urban Growth Chart...")
        
        growth_cities = []
        growth_rates = []
        pixels_2017 = []
        pixels_2024 = []
        
        for city, growth in self.summary_stats['urban_growth'].items():
            growth_cities.append(city)
            growth_rates.append(growth['growth_rate'])
            pixels_2017.append(growth['pixels_2017'])
            pixels_2024.append(growth['pixels_2024'])
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Urban Growth Rate (%)', 'Urban Area (Pixels): 2017 vs 2024'),
            column_widths=[0.4, 0.6]
        )
        
        # Growth rate bar chart
        fig.add_trace(
            go.Bar(
                x=growth_cities,
                y=growth_rates,
                name='Growth Rate',
                marker_color=[self.city_colors.get(city, self.colors['neutral']) for city in growth_cities],
                opacity=0.8,
                text=[f'{val:.1f}%' for val in growth_rates],
                textposition='auto',
            ),
            row=1, col=1
        )
        
        # Urban pixels comparison
        fig.add_trace(
            go.Bar(
                x=growth_cities,
                y=pixels_2017,
                name='Urban Pixels 2017',
                marker_color=self.colors['primary_2017'],
                opacity=0.8,
            ),
            row=1, col=2
        )
        
        fig.add_trace(
            go.Bar(
                x=growth_cities,
                y=pixels_2024,
                name='Urban Pixels 2024',
                marker_color=self.colors['primary_2024'],
                opacity=0.8,
            ),
            row=1, col=2
        )
        
        fig.update_layout(
            title={
                'text': 'Urban Area Expansion Analysis: 2017-2024<br><sub>Growth Rates and Absolute Changes</sub>',
                'x': 0.5,
                'font': {'size': 18}
            },
            height=600,
            width=1200,
            font=dict(size=12),
            template='plotly_white',
            barmode='group'
        )
        
        # Update axes
        fig.update_xaxes(title_text="Cities", row=1, col=1)
        fig.update_yaxes(title_text="Growth Rate (%)", row=1, col=1)
        fig.update_xaxes(title_text="Cities", row=1, col=2)
        fig.update_yaxes(title_text="Urban Pixels", row=1, col=2)
        
        # Save as HTML and PNG
        html_path = self.output_path / "03_urban_growth_analysis_2017_to_2024.html"
        png_path = self.output_path / "03_urban_growth_analysis_2017_to_2024.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=1200, height=600, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def create_temperature_trends_chart(self):
        """Chart 4: Temperature Trends Relationship"""
        print("Creating Temperature Trends Chart...")
        
        trend_cities = []
        suhi_trends = []
        urban_trends = []
        r_squared = []
        
        for city, trends in self.summary_stats['temperature_trends'].items():
            trend_cities.append(city)
            suhi_trends.append(trends['suhi_trend_per_year'])
            urban_trends.append(trends['urban_temp_trend'])
            r_squared.append(trends['r_squared'])
        
        # Size points by R-squared values
        sizes = [max(10, r*100) for r in r_squared]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=urban_trends,
            y=suhi_trends,
            mode='markers+text',
            text=trend_cities,
            textposition="top center",
            marker=dict(
                size=sizes,
                color=r_squared,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="R² Value"),
                line=dict(width=1, color='black'),
                opacity=0.8
            ),
            hovertemplate='<b>%{text}</b><br>' +
                         'Urban Temp Trend: %{x:.4f}°C/year<br>' +
                         'SUHI Trend: %{y:.4f}°C/year<br>' +
                         'R²: %{marker.color:.3f}<extra></extra>',
            name='Cities'
        ))
        
        # Add reference lines
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
        fig.add_vline(x=0, line_dash="dash", line_color="black", opacity=0.5)
        
        fig.update_layout(
            title={
                'text': 'Temperature Trends Relationship (2017-2024)<br><sub>Point size indicates R² value strength</sub>',
                'x': 0.5,
                'font': {'size': 18}
            },
            xaxis_title='Urban Temperature Trend (°C/year)',
            yaxis_title='SUHI Trend (°C/year)',
            height=600,
            width=1000,
            font=dict(size=12),
            template='plotly_white'
        )
        
        # Save as HTML and PNG
        html_path = self.output_path / "04_temperature_trends_relationship_2017_2024.html"
        png_path = self.output_path / "04_temperature_trends_relationship_2017_2024.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=1000, height=600, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def create_temporal_analysis_charts(self):
        """Chart 5: Individual city temporal analysis (separate charts)"""
        print("Creating Individual City Temporal Charts...")
        
        # Create individual charts for each city
        for city, temporal in self.temporal_data.items():
            if 'data' not in temporal:
                continue
                
            data = temporal['data']
            years = [d['year'] for d in data]
            suhi_values = [d['suhi_intensity'] for d in data]
            urban_temps = [d['urban_temp'] for d in data]
            rural_temps = [d['rural_temp'] for d in data]
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # SUHI intensity line
            fig.add_trace(
                go.Scatter(
                    x=years,
                    y=suhi_values,
                    mode='lines+markers',
                    name='SUHI Intensity',
                    line=dict(color=self.city_colors.get(city, self.colors['primary_2017']), width=3),
                    marker=dict(size=8)
                ),
                secondary_y=False,
            )
            
            # Urban temperature
            fig.add_trace(
                go.Scatter(
                    x=years,
                    y=urban_temps,
                    mode='lines+markers',
                    name='Urban Temperature',
                    line=dict(color=self.colors['primary_2024'], width=2, dash='dash'),
                    marker=dict(size=6, symbol='square')
                ),
                secondary_y=True,
            )
            
            # Rural temperature
            fig.add_trace(
                go.Scatter(
                    x=years,
                    y=rural_temps,
                    mode='lines+markers',
                    name='Rural Temperature',
                    line=dict(color=self.colors['negative'], width=2, dash='dash'),
                    marker=dict(size=6, symbol='triangle-up')
                ),
                secondary_y=True,
            )
            
            # Add trend line for SUHI
            if len(years) > 2:
                z = np.polyfit(years, suhi_values, 1)
                p = np.poly1d(z)
                fig.add_trace(
                    go.Scatter(
                        x=years,
                        y=p(years),
                        mode='lines',
                        name=f'SUHI Trend ({z[0]:.4f}°C/year)',
                        line=dict(color='red', width=2, dash='dot'),
                        opacity=0.7
                    ),
                    secondary_y=False,
                )
            
            # Set axis titles
            fig.update_xaxes(title_text="Year")
            fig.update_yaxes(title_text="SUHI Intensity (°C)", secondary_y=False)
            fig.update_yaxes(title_text="Temperature (°C)", secondary_y=True)
            
            fig.update_layout(
                title={
                    'text': f'{city} - Temporal SUHI Analysis (2017-2024)<br><sub>SUHI Evolution and Temperature Trends</sub>',
                    'x': 0.5,
                    'font': {'size': 16}
                },
                height=500,
                width=900,
                font=dict(size=11),
                template='plotly_white',
                hovermode='x unified'
            )
            
            # Save individual city chart
            html_path = self.output_path / f"05_temporal_{city.lower()}_2017_2024.html"
            png_path = self.output_path / f"05_temporal_{city.lower()}_2017_2024.png"
            
            fig.write_html(str(html_path))
            fig.write_image(str(png_path), width=900, height=500, scale=2)
        
        print(f"Saved temporal charts for {len(self.temporal_data)} cities")
    
    def create_correlation_matrix_chart(self):
        """Chart 6: Correlation Matrix of Key Variables"""
        print("Creating Correlation Matrix Chart...")
        
        # Prepare data for correlation
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
                
                data_for_corr.append({
                    'SUHI_2017': suhi_2017,
                    'SUHI_2024': suhi_2024,
                    'SUHI_Change': suhi_change,
                    'Urban_Growth_Rate': urban_growth,
                    'SUHI_Trend_Per_Year': suhi_trend
                })
        
        if data_for_corr:
            df = pd.DataFrame(data_for_corr)
            correlation_matrix = df.corr()
            
            fig = go.Figure(data=go.Heatmap(
                z=correlation_matrix.values,
                x=correlation_matrix.columns,
                y=correlation_matrix.columns,
                colorscale='RdBu',
                zmid=0,
                text=correlation_matrix.values,
                texttemplate="%{text:.3f}",
                textfont={"size": 12},
                hoverongaps=False,
                hovertemplate='<b>%{y}</b> vs <b>%{x}</b><br>Correlation: %{z:.3f}<extra></extra>'
            ))
            
            fig.update_layout(
                title={
                    'text': 'Correlation Matrix: SUHI Variables (2017-2024)<br><sub>Relationships between key metrics</sub>',
                    'x': 0.5,
                    'font': {'size': 18}
                },
                height=600,
                width=700,
                font=dict(size=12),
                template='plotly_white'
            )
            
            # Save as HTML and PNG
            html_path = self.output_path / "06_correlation_matrix_2017_2024.html"
            png_path = self.output_path / "06_correlation_matrix_2017_2024.png"
            
            fig.write_html(str(html_path))
            fig.write_image(str(png_path), width=700, height=600, scale=2)
            
            print(f"Saved: {html_path.name}")
            return fig
    
    def create_statistical_summary_chart(self):
        """Chart 7: Statistical Summary Box Plots"""
        print("Creating Statistical Summary Chart...")
        
        suhi_2017 = self.summary_stats['suhi_comparison']['suhi_2017']
        suhi_2024 = self.summary_stats['suhi_comparison']['suhi_2024']
        suhi_changes = [s24 - s17 for s17, s24 in zip(suhi_2017, suhi_2024)]
        
        fig = go.Figure()
        
        # Box plots for each variable
        fig.add_trace(go.Box(
            y=suhi_2017,
            name='SUHI 2017',
            marker_color=self.colors['primary_2017'],
            boxpoints='all',
            jitter=0.3,
            pointpos=-1.8
        ))
        
        fig.add_trace(go.Box(
            y=suhi_2024,
            name='SUHI 2024',
            marker_color=self.colors['primary_2024'],
            boxpoints='all',
            jitter=0.3,
            pointpos=-1.8
        ))
        
        fig.add_trace(go.Box(
            y=suhi_changes,
            name='SUHI Change (2024-2017)',
            marker_color=self.colors['accent1'],
            boxpoints='all',
            jitter=0.3,
            pointpos=-1.8
        ))
        
        fig.update_layout(
            title={
                'text': 'SUHI Statistical Distribution (2017-2024)<br><sub>Box plots showing quartiles and outliers</sub>',
                'x': 0.5,
                'font': {'size': 18}
            },
            yaxis_title='Temperature (°C)',
            height=600,
            width=800,
            font=dict(size=12),
            template='plotly_white'
        )
        
        # Add zero line for reference
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
        
        # Save as HTML and PNG
        html_path = self.output_path / "07_statistical_summary_2017_2024.html"
        png_path = self.output_path / "07_statistical_summary_2017_2024.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=800, height=600, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def create_accuracy_assessment_chart(self):
        """Chart 8: Accuracy Assessment Summary"""
        print("Creating Accuracy Assessment Chart...")
        
        # Collect accuracy data for 2024
        accuracy_cities = []
        esa_scores = []
        ghsl_scores = []
        modis_scores = []
        
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
                
                # MODIS agreement
                modis_score = 0
                if 'modis_lc_agreement' in acc_data and acc_data['modis_lc_agreement']:
                    modis_score = list(acc_data['modis_lc_agreement'].values())[0]
                modis_scores.append(modis_score)
        
        if accuracy_cities:
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=accuracy_cities,
                y=esa_scores,
                name='ESA Land Cover',
                marker_color=self.colors['primary_2017'],
                opacity=0.8
            ))
            
            fig.add_trace(go.Bar(
                x=accuracy_cities,
                y=ghsl_scores,
                name='GHSL Built-up',
                marker_color=self.colors['primary_2024'],
                opacity=0.8
            ))
            
            fig.add_trace(go.Bar(
                x=accuracy_cities,
                y=modis_scores,
                name='MODIS Land Cover',
                marker_color=self.colors['negative'],
                opacity=0.8
            ))
            
            fig.update_layout(
                title={
                    'text': 'Land Cover Classification Accuracy Assessment (2024)<br><sub>Agreement scores across different datasets</sub>',
                    'x': 0.5,
                    'font': {'size': 18}
                },
                xaxis_title='Cities',
                yaxis_title='Agreement Score',
                height=600,
                width=1000,
                font=dict(size=12),
                template='plotly_white',
                barmode='group'
            )
            
            # Save as HTML and PNG
            html_path = self.output_path / "08_accuracy_assessment_2024.html"
            png_path = self.output_path / "08_accuracy_assessment_2024.png"
            
            fig.write_html(str(html_path))
            fig.write_image(str(png_path), width=1000, height=600, scale=2)
            
            print(f"Saved: {html_path.name}")
            return fig
    
    def create_comprehensive_overview_chart(self):
        """Chart 9: Comprehensive Overview Dashboard"""
        print("Creating Comprehensive Overview Chart...")
        
        # Create a multi-panel overview
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'SUHI Comparison (2017 vs 2024)',
                'Urban Growth vs SUHI Change',
                'Top 5 SUHI Increases',
                'Top 5 SUHI Improvements'
            ),
            specs=[[{"type": "bar"}, {"type": "scatter"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        cities = self.summary_stats['suhi_comparison']['cities']
        suhi_2017 = self.summary_stats['suhi_comparison']['suhi_2017']
        suhi_2024 = self.summary_stats['suhi_comparison']['suhi_2024']
        suhi_changes = [s24 - s17 for s17, s24 in zip(suhi_2017, suhi_2024)]
        
        # Panel 1: SUHI Comparison
        fig.add_trace(
            go.Bar(x=cities[:7], y=suhi_2017[:7], name='2017', 
                  marker_color=self.colors['primary_2017'], opacity=0.8),
            row=1, col=1
        )
        fig.add_trace(
            go.Bar(x=cities[:7], y=suhi_2024[:7], name='2024', 
                  marker_color=self.colors['primary_2024'], opacity=0.8),
            row=1, col=1
        )
        
        # Panel 2: Urban Growth vs SUHI Change
        growth_rates = []
        for city in cities:
            if city in self.summary_stats['urban_growth']:
                growth_rates.append(self.summary_stats['urban_growth'][city]['growth_rate'])
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
                name='Cities',
                showlegend=False
            ),
            row=1, col=2
        )
        
        # Panel 3: Top 5 SUHI Increases
        city_change_pairs = list(zip(cities, suhi_changes))
        top_increases = sorted(city_change_pairs, key=lambda x: x[1], reverse=True)[:5]
        
        fig.add_trace(
            go.Bar(
                x=[pair[0] for pair in top_increases],
                y=[pair[1] for pair in top_increases],
                marker_color=self.colors['positive'],
                opacity=0.8,
                name='Increases',
                showlegend=False
            ),
            row=2, col=1
        )
        
        # Panel 4: Top 5 SUHI Improvements (decreases)
        top_decreases = sorted(city_change_pairs, key=lambda x: x[1])[:5]
        
        fig.add_trace(
            go.Bar(
                x=[pair[0] for pair in top_decreases],
                y=[pair[1] for pair in top_decreases],
                marker_color=self.colors['negative'],
                opacity=0.8,
                name='Improvements',
                showlegend=False
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title={
                'text': 'SUHI Analysis Overview: 2017-2024<br><sub>Comprehensive Summary Dashboard</sub>',
                'x': 0.5,
                'font': {'size': 20}
            },
            height=800,
            width=1200,
            font=dict(size=10),
            template='plotly_white',
            showlegend=True
        )
        
        # Update axes
        fig.update_xaxes(title_text="Cities", row=1, col=1)
        fig.update_yaxes(title_text="SUHI (°C)", row=1, col=1)
        fig.update_xaxes(title_text="Urban Growth (%)", row=1, col=2)
        fig.update_yaxes(title_text="SUHI Change (°C)", row=1, col=2)
        fig.update_xaxes(title_text="Cities", row=2, col=1)
        fig.update_yaxes(title_text="SUHI Change (°C)", row=2, col=1)
        fig.update_xaxes(title_text="Cities", row=2, col=2)
        fig.update_yaxes(title_text="SUHI Change (°C)", row=2, col=2)
        
        # Save as HTML and PNG
        html_path = self.output_path / "09_comprehensive_overview_2017_2024.html"
        png_path = self.output_path / "09_comprehensive_overview_2017_2024.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=1200, height=800, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def generate_all_charts(self):
        """Generate all individual charts."""
        print("=" * 80)
        print("GENERATING INDIVIDUAL PLOTLY CHARTS")
        print("=" * 80)
        
        # Load data
        self.load_data()
        
        # Generate all charts
        charts = []
        charts.append(self.create_suhi_comparison_chart())
        charts.append(self.create_suhi_change_chart())
        charts.append(self.create_urban_growth_chart())
        charts.append(self.create_temperature_trends_chart())
        self.create_temporal_analysis_charts()  # Multiple charts
        charts.append(self.create_correlation_matrix_chart())
        charts.append(self.create_statistical_summary_chart())
        charts.append(self.create_accuracy_assessment_chart())
        charts.append(self.create_comprehensive_overview_chart())
        
        print("=" * 80)
        print("ALL CHARTS GENERATED SUCCESSFULLY!")
        print("=" * 80)
        print(f"📁 Output directory: {self.output_path}")
        print(f"📊 Total chart files created: {len(list(self.output_path.glob('*.html')))} HTML + {len(list(self.output_path.glob('*.png')))} PNG")
        print("=" * 80)
        
        return charts


def main():
    """Main execution function."""
    # Set paths
    data_path = "/Users/timursabitov/Dev/Uzbekistan_URBAN_research/suhi_analysis_output/data"
    output_path = "/Users/timursabitov/Dev/Uzbekistan_URBAN_research/reporting"
    
    # Initialize chart generator
    generator = SUHIChartGenerator(data_path, output_path)
    
    # Generate all charts
    charts = generator.generate_all_charts()
    
    return charts


if __name__ == "__main__":
    charts = main()
