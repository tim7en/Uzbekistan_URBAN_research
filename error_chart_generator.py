#!/usr/bin/env python3
"""
Error Analysis Chart Generator
=============================

Extracts data from the error analysis report (markdown format) and creates
comprehensive visualizations for uncertainty analysis and classification accuracy.

Features:
- Error analysis visualization (standard errors, confidence intervals)
- Classification accuracy comparisons across datasets
- Uncertainty quantification charts
- Professional Plotly visualizations

Author: GitHub Copilot
Date: August 19, 2025
"""

import re
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

class ErrorAnalysisChartGenerator:
    """
    Generates charts from error analysis report data.
    """
    
    def __init__(self, error_report_path, output_path):
        """Initialize the error chart generator."""
        self.error_report_path = Path(error_report_path)
        self.output_path = Path(output_path)
        self.output_path.mkdir(exist_ok=True)
        
        self.summary_data = []
        self.accuracy_data = []
        
        # Professional color scheme
        self.colors = {
            'suhi_2017': '#1f77b4',        # Blue for 2017
            'suhi_2024': '#ff7f0e',        # Orange for 2024
            'error_bars': '#d62728',       # Red for errors
            'confidence': '#2ca02c',       # Green for confidence
            'esa': '#9467bd',              # Purple for ESA
            'ghsl': '#8c564b',             # Brown for GHSL
            'modis': '#e377c2',            # Pink for MODIS
            'dynamic_world': '#7f7f7f',    # Gray for Dynamic World
            'high_error': '#d62728',       # Red for high error
            'low_error': '#2ca02c',        # Green for low error
            'medium_error': '#ff7f0e'      # Orange for medium error
        }
        
    def load_and_parse_error_report(self):
        """Load and parse the error report markdown file."""
        print("Loading and parsing error analysis report...")
        
        # Try different encodings to handle potential encoding issues
        encodings = ['utf-8', 'latin-1', 'cp1252', 'utf-16']
        content = None
        
        for encoding in encodings:
            try:
                with open(self.error_report_path, 'r', encoding=encoding) as f:
                    content = f.read()
                print(f"Successfully read file with {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            raise ValueError("Could not read file with any common encoding")
        
        # Parse summary statistics table
        self._parse_summary_table(content)
        
        # Parse accuracy assessments
        self._parse_accuracy_data(content)
        
        print(f"Parsed {len(self.summary_data)} summary records and {len(self.accuracy_data)} accuracy records")
        
    def _parse_summary_table(self, content):
        """Parse the summary statistics table."""
        # Find the table section
        table_match = re.search(r'\| City \| Year \|.*?\n((?:\|.*?\n)+)', content, re.DOTALL)
        if not table_match:
            print("Warning: Could not find summary table")
            return
        
        table_content = table_match.group(1)
        lines = table_content.strip().split('\n')
        
        for line in lines:
            if '|' in line and not line.strip().startswith('|---'):
                parts = [p.strip() for p in line.split('|')[1:-1]]  # Remove empty first/last
                if len(parts) >= 7:
                    try:
                        city = parts[0]
                        year = int(parts[1])
                        suhi = float(parts[2])
                        se = float(parts[3])
                        # Parse confidence interval
                        ci_text = parts[4].strip('[]')
                        ci_lower, ci_upper = map(float, ci_text.split(', '))
                        rel_error = float(parts[5])
                        urban_pixels = int(parts[6])
                        rural_pixels = int(parts[7])
                        
                        self.summary_data.append({
                            'city': city,
                            'year': year,
                            'suhi': suhi,
                            'se': se,
                            'ci_lower': ci_lower,
                            'ci_upper': ci_upper,
                            'rel_error': rel_error,
                            'urban_pixels': urban_pixels,
                            'rural_pixels': rural_pixels
                        })
                    except (ValueError, IndexError) as e:
                        print(f"Warning: Could not parse line: {line.strip()}")
                        continue
    
    def _parse_accuracy_data(self, content):
        """Parse the accuracy assessment JSON data."""
        # Find all city/year sections with JSON data
        pattern = r'### (.*?) \((\d{4})\)\n.*?```json\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for city, year, json_text in matches:
            try:
                accuracy_dict = json.loads(json_text)
                
                record = {
                    'city': city,
                    'year': int(year),
                    'dynamic_world': 0,  # Always 0 based on the data
                    'esa': 0,
                    'ghsl': 0,
                    'modis': 0
                }
                
                # Extract agreement scores
                if 'esa_agreement' in accuracy_dict and accuracy_dict['esa_agreement']:
                    record['esa'] = list(accuracy_dict['esa_agreement'].values())[0]
                
                if 'ghsl_agreement' in accuracy_dict and accuracy_dict['ghsl_agreement']:
                    record['ghsl'] = list(accuracy_dict['ghsl_agreement'].values())[0]
                
                if 'modis_lc_agreement' in accuracy_dict and accuracy_dict['modis_lc_agreement']:
                    record['modis'] = list(accuracy_dict['modis_lc_agreement'].values())[0]
                
                if 'dynamic_world_agreement' in accuracy_dict and accuracy_dict['dynamic_world_agreement']:
                    record['dynamic_world'] = list(accuracy_dict['dynamic_world_agreement'].values())[0]
                
                self.accuracy_data.append(record)
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Warning: Could not parse JSON for {city} {year}: {e}")
                continue
    
    def create_error_bars_chart(self):
        """Chart 1: SUHI with Error Bars (2017 vs 2024)"""
        print("Creating SUHI Error Bars Chart...")
        
        df = pd.DataFrame(self.summary_data)
        
        fig = go.Figure()
        
        # Group by year
        df_2017 = df[df['year'] == 2017].sort_values('city')
        df_2024 = df[df['year'] == 2024].sort_values('city')
        
        # Add 2017 data with error bars
        fig.add_trace(go.Scatter(
            x=df_2017['city'],
            y=df_2017['suhi'],
            error_y=dict(
                type='data',
                array=df_2017['se'],
                visible=True,
                color=self.colors['suhi_2017']
            ),
            mode='markers',
            marker=dict(
                size=10,
                color=self.colors['suhi_2017'],
                symbol='circle'
            ),
            name='SUHI 2017 (±SE)',
            hovertemplate='<b>%{x} (2017)</b><br>' +
                         'SUHI: %{y:.3f}°C<br>' +
                         'SE: %{error_y.array:.3f}<extra></extra>'
        ))
        
        # Add 2024 data with error bars
        fig.add_trace(go.Scatter(
            x=df_2024['city'],
            y=df_2024['suhi'],
            error_y=dict(
                type='data',
                array=df_2024['se'],
                visible=True,
                color=self.colors['suhi_2024']
            ),
            mode='markers',
            marker=dict(
                size=10,
                color=self.colors['suhi_2024'],
                symbol='square'
            ),
            name='SUHI 2024 (±SE)',
            hovertemplate='<b>%{x} (2024)</b><br>' +
                         'SUHI: %{y:.3f}°C<br>' +
                         'SE: %{error_y.array:.3f}<extra></extra>'
        ))
        
        # Add zero reference line
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
        
        fig.update_layout(
            title='SUHI Intensity with Standard Error Bars (2017 vs 2024)<br><sub>Error bars show ±1 Standard Error</sub>',
            xaxis_title='Cities',
            yaxis_title='SUHI Intensity (°C)',
            height=600,
            width=1000,
            template='plotly_white',
            font=dict(size=12),
            hovermode='closest'
        )
        
        # Save
        html_path = self.output_path / "error_01_suhi_with_error_bars_2017_vs_2024.html"
        png_path = self.output_path / "error_01_suhi_with_error_bars_2017_vs_2024.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=1000, height=600, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def create_confidence_intervals_chart(self):
        """Chart 2: 95% Confidence Intervals Comparison"""
        print("Creating Confidence Intervals Chart...")
        
        df = pd.DataFrame(self.summary_data)
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('2017 Confidence Intervals', '2024 Confidence Intervals'),
            shared_yaxes=True
        )
        
        # 2017 data
        df_2017 = df[df['year'] == 2017].sort_values('city')
        
        fig.add_trace(
            go.Scatter(
                x=df_2017['city'],
                y=df_2017['suhi'],
                error_y=dict(
                    type='data',
                    symmetric=False,
                    array=df_2017['ci_upper'] - df_2017['suhi'],
                    arrayminus=df_2017['suhi'] - df_2017['ci_lower'],
                    visible=True,
                    color=self.colors['suhi_2017']
                ),
                mode='markers',
                marker=dict(
                    size=8,
                    color=self.colors['suhi_2017']
                ),
                name='2017',
                hovertemplate='<b>%{x}</b><br>' +
                             'SUHI: %{y:.3f}°C<br>' +
                             '95% CI: [%{customdata[0]:.3f}, %{customdata[1]:.3f}]<extra></extra>',
                customdata=list(zip(df_2017['ci_lower'], df_2017['ci_upper']))
            ),
            row=1, col=1
        )
        
        # 2024 data
        df_2024 = df[df['year'] == 2024].sort_values('city')
        
        fig.add_trace(
            go.Scatter(
                x=df_2024['city'],
                y=df_2024['suhi'],
                error_y=dict(
                    type='data',
                    symmetric=False,
                    array=df_2024['ci_upper'] - df_2024['suhi'],
                    arrayminus=df_2024['suhi'] - df_2024['ci_lower'],
                    visible=True,
                    color=self.colors['suhi_2024']
                ),
                mode='markers',
                marker=dict(
                    size=8,
                    color=self.colors['suhi_2024']
                ),
                name='2024',
                hovertemplate='<b>%{x}</b><br>' +
                             'SUHI: %{y:.3f}°C<br>' +
                             '95% CI: [%{customdata[0]:.3f}, %{customdata[1]:.3f}]<extra></extra>',
                customdata=list(zip(df_2024['ci_lower'], df_2024['ci_upper']))
            ),
            row=1, col=2
        )
        
        # Add zero reference lines
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5, row=1, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5, row=1, col=2)
        
        fig.update_layout(
            title='95% Confidence Intervals for SUHI Measurements<br><sub>Error bars show 95% confidence intervals</sub>',
            height=600,
            width=1200,
            template='plotly_white',
            font=dict(size=12)
        )
        
        # Update axes
        fig.update_xaxes(title_text="Cities", row=1, col=1)
        fig.update_xaxes(title_text="Cities", row=1, col=2)
        fig.update_yaxes(title_text="SUHI Intensity (°C)", row=1, col=1)
        
        # Save
        html_path = self.output_path / "error_02_confidence_intervals_2017_vs_2024.html"
        png_path = self.output_path / "error_02_confidence_intervals_2017_vs_2024.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=1200, height=600, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def create_relative_error_chart(self):
        """Chart 3: Relative Error Analysis (2017 vs 2024)"""
        print("Creating Relative Error Chart...")
        
        df = pd.DataFrame(self.summary_data)
        
        # Cap extreme relative errors for visualization
        df['rel_error_capped'] = df['rel_error'].clip(upper=100)
        
        # Create color scale based on error magnitude
        def get_error_color(error):
            if error <= 10:
                return self.colors['low_error']
            elif error <= 30:
                return self.colors['medium_error']
            else:
                return self.colors['high_error']
        
        df_2017 = df[df['year'] == 2017].sort_values('city')
        df_2024 = df[df['year'] == 2024].sort_values('city')
        
        fig = go.Figure()
        
        # Add 2017 bars
        fig.add_trace(go.Bar(
            x=df_2017['city'],
            y=df_2017['rel_error_capped'],
            name='Relative Error 2017 (%)',
            marker_color=[get_error_color(err) for err in df_2017['rel_error_capped']],
            opacity=0.7,
            text=[f'{err:.1f}%' for err in df_2017['rel_error']],
            textposition='auto',
            hovertemplate='<b>%{x} (2017)</b><br>' +
                         'Relative Error: %{y:.1f}%<br>' +
                         'SUHI: %{customdata:.3f}°C<extra></extra>',
            customdata=df_2017['suhi']
        ))
        
        # Add 2024 bars (offset)
        fig.add_trace(go.Bar(
            x=df_2024['city'],
            y=df_2024['rel_error_capped'],
            name='Relative Error 2024 (%)',
            marker_color=[get_error_color(err) for err in df_2024['rel_error_capped']],
            opacity=0.7,
            text=[f'{err:.1f}%' for err in df_2024['rel_error']],
            textposition='auto',
            hovertemplate='<b>%{x} (2024)</b><br>' +
                         'Relative Error: %{y:.1f}%<br>' +
                         'SUHI: %{customdata:.3f}°C<extra></extra>',
            customdata=df_2024['suhi']
        ))
        
        # Add reference lines
        fig.add_hline(y=10, line_dash="dot", line_color="green", opacity=0.7,
                     annotation_text="10% (Low Error)", annotation_position="top right")
        fig.add_hline(y=30, line_dash="dot", line_color="orange", opacity=0.7,
                     annotation_text="30% (Medium Error)", annotation_position="top right")
        
        fig.update_layout(
            title='Relative Error Analysis: 2017 vs 2024<br><sub>Color coding: Green ≤10% | Orange 10-30% | Red >30%</sub>',
            xaxis_title='Cities',
            yaxis_title='Relative Error (%)',
            height=600,
            width=1000,
            template='plotly_white',
            font=dict(size=12),
            barmode='group'
        )
        
        # Save
        html_path = self.output_path / "error_03_relative_error_analysis_2017_vs_2024.html"
        png_path = self.output_path / "error_03_relative_error_analysis_2017_vs_2024.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=1000, height=600, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def create_accuracy_comparison_chart(self):
        """Chart 4: Classification Accuracy Comparison Across Datasets"""
        print("Creating Classification Accuracy Chart...")
        
        df = pd.DataFrame(self.accuracy_data)
        
        # Create subplots for each dataset
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('ESA Land Cover Agreement', 'GHSL Built-up Agreement', 
                           'MODIS Land Cover Agreement', 'Dataset Comparison (2024)'),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        # Sort cities for consistent ordering
        cities_2017 = df[df['year'] == 2017].sort_values('city')
        cities_2024 = df[df['year'] == 2024].sort_values('city')
        
        # ESA accuracy
        fig.add_trace(
            go.Bar(x=cities_2017['city'], y=cities_2017['esa'], 
                  name='ESA 2017', marker_color=self.colors['suhi_2017'], opacity=0.8),
            row=1, col=1
        )
        fig.add_trace(
            go.Bar(x=cities_2024['city'], y=cities_2024['esa'], 
                  name='ESA 2024', marker_color=self.colors['suhi_2024'], opacity=0.8),
            row=1, col=1
        )
        
        # GHSL accuracy
        fig.add_trace(
            go.Bar(x=cities_2017['city'], y=cities_2017['ghsl'], 
                  name='GHSL 2017', marker_color=self.colors['suhi_2017'], opacity=0.8, showlegend=False),
            row=1, col=2
        )
        fig.add_trace(
            go.Bar(x=cities_2024['city'], y=cities_2024['ghsl'], 
                  name='GHSL 2024', marker_color=self.colors['suhi_2024'], opacity=0.8, showlegend=False),
            row=1, col=2
        )
        
        # MODIS accuracy
        fig.add_trace(
            go.Bar(x=cities_2017['city'], y=cities_2017['modis'], 
                  name='MODIS 2017', marker_color=self.colors['suhi_2017'], opacity=0.8, showlegend=False),
            row=2, col=1
        )
        fig.add_trace(
            go.Bar(x=cities_2024['city'], y=cities_2024['modis'], 
                  name='MODIS 2024', marker_color=self.colors['suhi_2024'], opacity=0.8, showlegend=False),
            row=2, col=1
        )
        
        # Dataset comparison for 2024
        fig.add_trace(
            go.Bar(x=cities_2024['city'], y=cities_2024['esa'], 
                  name='ESA', marker_color=self.colors['esa'], opacity=0.8),
            row=2, col=2
        )
        fig.add_trace(
            go.Bar(x=cities_2024['city'], y=cities_2024['ghsl'], 
                  name='GHSL', marker_color=self.colors['ghsl'], opacity=0.8),
            row=2, col=2
        )
        fig.add_trace(
            go.Bar(x=cities_2024['city'], y=cities_2024['modis'], 
                  name='MODIS', marker_color=self.colors['modis'], opacity=0.8),
            row=2, col=2
        )
        
        fig.update_layout(
            title='Classification Accuracy Assessment: 2017 vs 2024<br><sub>Agreement scores between ESRI land cover and reference datasets</sub>',
            height=800,
            width=1200,
            template='plotly_white',
            font=dict(size=11),
            barmode='group'
        )
        
        # Update axes
        for i in range(1, 3):
            for j in range(1, 3):
                fig.update_xaxes(title_text="Cities", row=i, col=j)
                fig.update_yaxes(title_text="Agreement Score", row=i, col=j)
        
        # Save
        html_path = self.output_path / "error_04_classification_accuracy_2017_vs_2024.html"
        png_path = self.output_path / "error_04_classification_accuracy_2017_vs_2024.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=1200, height=800, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def create_uncertainty_vs_suhi_chart(self):
        """Chart 5: Uncertainty vs SUHI Magnitude Relationship"""
        print("Creating Uncertainty vs SUHI Chart...")
        
        df = pd.DataFrame(self.summary_data)
        
        fig = go.Figure()
        
        # 2017 data
        df_2017 = df[df['year'] == 2017]
        fig.add_trace(go.Scatter(
            x=np.abs(df_2017['suhi']),
            y=df_2017['se'],
            mode='markers+text',
            text=df_2017['city'],
            textposition="top center",
            marker=dict(
                size=10,
                color=self.colors['suhi_2017'],
                symbol='circle',
                opacity=0.7
            ),
            name='2017',
            hovertemplate='<b>%{text} (2017)</b><br>' +
                         'SUHI Magnitude: %{x:.3f}°C<br>' +
                         'Standard Error: %{y:.3f}<extra></extra>'
        ))
        
        # 2024 data
        df_2024 = df[df['year'] == 2024]
        fig.add_trace(go.Scatter(
            x=np.abs(df_2024['suhi']),
            y=df_2024['se'],
            mode='markers+text',
            text=df_2024['city'],
            textposition="bottom center",
            marker=dict(
                size=10,
                color=self.colors['suhi_2024'],
                symbol='square',
                opacity=0.7
            ),
            name='2024',
            hovertemplate='<b>%{text} (2024)</b><br>' +
                         'SUHI Magnitude: %{x:.3f}°C<br>' +
                         'Standard Error: %{y:.3f}<extra></extra>'
        ))
        
        # Add trendlines
        for year, color, df_year in [(2017, self.colors['suhi_2017'], df_2017), 
                                    (2024, self.colors['suhi_2024'], df_2024)]:
            if len(df_year) > 1:
                z = np.polyfit(np.abs(df_year['suhi']), df_year['se'], 1)
                p = np.poly1d(z)
                x_trend = np.linspace(0, np.abs(df_year['suhi']).max(), 100)
                fig.add_trace(go.Scatter(
                    x=x_trend,
                    y=p(x_trend),
                    mode='lines',
                    line=dict(color=color, dash='dash', width=2),
                    name=f'{year} Trend',
                    showlegend=False,
                    hovertemplate='Trend line (%d)<extra></extra>' % year
                ))
        
        fig.update_layout(
            title='Uncertainty vs SUHI Magnitude Relationship<br><sub>Standard Error vs Absolute SUHI Value</sub>',
            xaxis_title='SUHI Magnitude (|SUHI|, °C)',
            yaxis_title='Standard Error (°C)',
            height=600,
            width=1000,
            template='plotly_white',
            font=dict(size=12)
        )
        
        # Save
        html_path = self.output_path / "error_05_uncertainty_vs_suhi_magnitude.html"
        png_path = self.output_path / "error_05_uncertainty_vs_suhi_magnitude.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=1000, height=600, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def create_sample_size_analysis_chart(self):
        """Chart 6: Sample Size vs Uncertainty Analysis"""
        print("Creating Sample Size Analysis Chart...")
        
        df = pd.DataFrame(self.summary_data)
        df['total_pixels'] = df['urban_pixels'] + df['rural_pixels']
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Urban Pixels vs Standard Error', 'Total Pixels vs Relative Error'),
            column_widths=[0.5, 0.5]
        )
        
        # Urban pixels vs SE
        df_2017 = df[df['year'] == 2017]
        df_2024 = df[df['year'] == 2024]
        
        fig.add_trace(
            go.Scatter(
                x=df_2017['urban_pixels'],
                y=df_2017['se'],
                mode='markers+text',
                text=df_2017['city'],
                textposition="top center",
                marker=dict(size=8, color=self.colors['suhi_2017'], opacity=0.7),
                name='2017',
                hovertemplate='<b>%{text} (2017)</b><br>' +
                             'Urban Pixels: %{x}<br>' +
                             'Standard Error: %{y:.3f}<extra></extra>'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df_2024['urban_pixels'],
                y=df_2024['se'],
                mode='markers+text',
                text=df_2024['city'],
                textposition="bottom center",
                marker=dict(size=8, color=self.colors['suhi_2024'], opacity=0.7),
                name='2024',
                hovertemplate='<b>%{text} (2024)</b><br>' +
                             'Urban Pixels: %{x}<br>' +
                             'Standard Error: %{y:.3f}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Total pixels vs relative error
        fig.add_trace(
            go.Scatter(
                x=df_2017['total_pixels'],
                y=df_2017['rel_error'].clip(upper=100),
                mode='markers+text',
                text=df_2017['city'],
                textposition="top center",
                marker=dict(size=8, color=self.colors['suhi_2017'], opacity=0.7),
                name='2017 (RE)',
                showlegend=False,
                hovertemplate='<b>%{text} (2017)</b><br>' +
                             'Total Pixels: %{x}<br>' +
                             'Relative Error: %{customdata:.1f}%<extra></extra>',
                customdata=df_2017['rel_error']
            ),
            row=1, col=2
        )
        
        fig.add_trace(
            go.Scatter(
                x=df_2024['total_pixels'],
                y=df_2024['rel_error'].clip(upper=100),
                mode='markers+text',
                text=df_2024['city'],
                textposition="bottom center",
                marker=dict(size=8, color=self.colors['suhi_2024'], opacity=0.7),
                name='2024 (RE)',
                showlegend=False,
                hovertemplate='<b>%{text} (2024)</b><br>' +
                             'Total Pixels: %{x}<br>' +
                             'Relative Error: %{customdata:.1f}%<extra></extra>',
                customdata=df_2024['rel_error']
            ),
            row=1, col=2
        )
        
        fig.update_layout(
            title='Sample Size vs Measurement Uncertainty<br><sub>Relationship between pixel count and error metrics</sub>',
            height=600,
            width=1200,
            template='plotly_white',
            font=dict(size=12)
        )
        
        # Update axes
        fig.update_xaxes(title_text="Urban Pixels", row=1, col=1)
        fig.update_yaxes(title_text="Standard Error (°C)", row=1, col=1)
        fig.update_xaxes(title_text="Total Pixels", row=1, col=2)
        fig.update_yaxes(title_text="Relative Error (%, capped at 100)", row=1, col=2)
        
        # Save
        html_path = self.output_path / "error_06_sample_size_vs_uncertainty.html"
        png_path = self.output_path / "error_06_sample_size_vs_uncertainty.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=1200, height=600, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def create_error_summary_dashboard(self):
        """Chart 7: Error Analysis Summary Dashboard"""
        print("Creating Error Summary Dashboard...")
        
        df_summary = pd.DataFrame(self.summary_data)
        df_accuracy = pd.DataFrame(self.accuracy_data)
        
        # Create 2x2 subplot dashboard
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Error Magnitude Distribution', 'Accuracy Scores by Dataset (2024)',
                           'High vs Low Error Cities', 'Error Change (2017→2024)'),
            specs=[[{"type": "histogram"}, {"type": "box"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        # Panel 1: Error distribution histogram
        fig.add_trace(
            go.Histogram(
                x=df_summary[df_summary['year'] == 2017]['se'],
                name='SE 2017',
                opacity=0.7,
                marker_color=self.colors['suhi_2017'],
                nbinsx=10
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Histogram(
                x=df_summary[df_summary['year'] == 2024]['se'],
                name='SE 2024',
                opacity=0.7,
                marker_color=self.colors['suhi_2024'],
                nbinsx=10
            ),
            row=1, col=1
        )
        
        # Panel 2: Accuracy box plots
        df_2024_acc = df_accuracy[df_accuracy['year'] == 2024]
        
        fig.add_trace(
            go.Box(y=df_2024_acc['esa'], name='ESA', marker_color=self.colors['esa']),
            row=1, col=2
        )
        fig.add_trace(
            go.Box(y=df_2024_acc['ghsl'], name='GHSL', marker_color=self.colors['ghsl']),
            row=1, col=2
        )
        fig.add_trace(
            go.Box(y=df_2024_acc['modis'], name='MODIS', marker_color=self.colors['modis']),
            row=1, col=2
        )
        
        # Panel 3: High vs Low error cities (2024)
        df_2024 = df_summary[df_summary['year'] == 2024].sort_values('se')
        high_error_cities = df_2024.tail(5)
        low_error_cities = df_2024.head(5)
        
        fig.add_trace(
            go.Bar(
                x=low_error_cities['city'],
                y=low_error_cities['se'],
                name='Low Error',
                marker_color=self.colors['low_error'],
                opacity=0.8
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=high_error_cities['city'],
                y=high_error_cities['se'],
                name='High Error',
                marker_color=self.colors['high_error'],
                opacity=0.8
            ),
            row=2, col=1
        )
        
        # Panel 4: Error change
        df_2017 = df_summary[df_summary['year'] == 2017].set_index('city')
        df_2024 = df_summary[df_summary['year'] == 2024].set_index('city')
        
        common_cities = df_2017.index.intersection(df_2024.index)
        error_changes = []
        cities_change = []
        
        for city in common_cities:
            change = df_2024.loc[city, 'se'] - df_2017.loc[city, 'se']
            error_changes.append(change)
            cities_change.append(city)
        
        colors_change = [self.colors['high_error'] if x > 0 else self.colors['low_error'] for x in error_changes]
        
        fig.add_trace(
            go.Bar(
                x=cities_change,
                y=error_changes,
                marker_color=colors_change,
                opacity=0.8,
                name='Error Change',
                showlegend=False
            ),
            row=2, col=2
        )
        
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5, row=2, col=2)
        
        fig.update_layout(
            title='Error Analysis Summary Dashboard<br><sub>Comprehensive uncertainty assessment across all metrics</sub>',
            height=800,
            width=1200,
            template='plotly_white',
            font=dict(size=11)
        )
        
        # Update axes labels
        fig.update_xaxes(title_text="Standard Error (°C)", row=1, col=1)
        fig.update_yaxes(title_text="Frequency", row=1, col=1)
        fig.update_yaxes(title_text="Agreement Score", row=1, col=2)
        fig.update_xaxes(title_text="Cities", row=2, col=1)
        fig.update_yaxes(title_text="Standard Error (°C)", row=2, col=1)
        fig.update_xaxes(title_text="Cities", row=2, col=2)
        fig.update_yaxes(title_text="Error Change (°C)", row=2, col=2)
        
        # Save
        html_path = self.output_path / "error_07_summary_dashboard_2017_vs_2024.html"
        png_path = self.output_path / "error_07_summary_dashboard_2017_vs_2024.png"
        
        fig.write_html(str(html_path))
        fig.write_image(str(png_path), width=1200, height=800, scale=2)
        
        print(f"Saved: {html_path.name}")
        return fig
    
    def generate_all_error_charts(self):
        """Generate all error analysis charts."""
        print("=" * 80)
        print("GENERATING ERROR ANALYSIS CHARTS")
        print("=" * 80)
        
        # Load and parse data
        self.load_and_parse_error_report()
        
        # Generate all charts
        charts = []
        charts.append(self.create_error_bars_chart())
        charts.append(self.create_confidence_intervals_chart())
        charts.append(self.create_relative_error_chart())
        charts.append(self.create_accuracy_comparison_chart())
        charts.append(self.create_uncertainty_vs_suhi_chart())
        charts.append(self.create_sample_size_analysis_chart())
        charts.append(self.create_error_summary_dashboard())
        
        print("=" * 80)
        print("ALL ERROR CHARTS GENERATED!")
        print("=" * 80)
        print(f"📁 Output directory: {self.output_path}")
        print(f"📊 Error chart files created: {len(list(self.output_path.glob('*.html')))} HTML + {len(list(self.output_path.glob('*.png')))} PNG")
        print("=" * 80)
        
        return charts


def main():
    """Main execution function."""
    # Set paths
    error_report_path = "/Users/timursabitov/Dev/Uzbekistan_URBAN_research/suhi_analysis_output/error_analysis/error_report_20250819_221646.md"
    output_path = "/Users/timursabitov/Dev/Uzbekistan_URBAN_research/reporting/error_charts"
    
    # Initialize error chart generator
    generator = ErrorAnalysisChartGenerator(error_report_path, output_path)
    
    # Generate all error charts
    charts = generator.generate_all_error_charts()
    
    return charts


if __name__ == "__main__":
    charts = main()
