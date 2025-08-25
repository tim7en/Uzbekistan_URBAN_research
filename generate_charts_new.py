#!/usr/bin/env python3
"""
Comprehensive Chart Generator for Uzbekistan URBAN Research SUHI Analysis
- Load data from multiple JSON sources (SUHI, LULC, Nightlights, Temperature, Spatial)
- Generate meaningful visualizations with confidence intervals
- Support temporal analysis across all available years
- Create publication-ready charts
"""

import json
import os
from pathlib import Path
from datetime import datetime
import warnings
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import plotly.express as px

# ----------------------------
# Plotly config
# ----------------------------
warnings.filterwarnings("ignore")
pio.templates.default = "plotly_white"

# Kaleido availability check (for PNG exports)
_KALEIDO_OK = True
try:
    import kaleido  # noqa: F401
except Exception:
    _KALEIDO_OK = False


def safe_write_image(fig, path, width, height, scale):
    """Write PNG if kaleido is available; otherwise skip without crashing."""
    if not _KALEIDO_OK:
        print(f"Warning: Kaleido not available, skipping PNG export for {path}")
        return False
    try:
        fig.write_image(str(path), width=width, height=height, scale=scale)
        return True
    except Exception as e:
        print(f"Warning: Failed to save PNG {path}: {e}")
        return False


# ----------------------------
# Helper Functions
# ----------------------------
def safe_get(data: dict, key: str, default=None):
    """Safely get a value from nested dictionary"""
    try:
        return data.get(key, default)
    except (AttributeError, TypeError):
        return default


def safe_float(value, default=None):
    """Safely convert value to float"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


class ComprehensiveChartGenerator:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.output_path = self.base_path / "plots"
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Data containers
        self.suhi_data = {}
        self.lulc_data = []
        self.nightlights_data = []
        self.temperature_data = {}
        self.spatial_data = {}
        
        # Analysis results
        self.cities = set()
        self.years = set()
        
        # Color palettes
        self.city_colors = {
            "Tashkent": "#1f77b4", "Samarkand": "#ff7f0e", "Bukhara": "#2ca02c",
            "Andijan": "#d62728", "Namangan": "#9467bd", "Fergana": "#8c564b",
            "Nukus": "#e377c2", "Urgench": "#7f7f7f", "Termez": "#bcbd22",
            "Qarshi": "#17becf", "Jizzakh": "#ff9896", "Navoiy": "#98df8a",
            "Gulistan": "#c5b0d5", "Nurafshon": "#c49c94"
        }
        
        self.suhi_colors = {
            "day": "#ff6b35",
            "night": "#004e89",
            "positive": "#d62728",
            "negative": "#2ca02c",
            "neutral": "#7f7f7f"
        }
        
    def load_all_data(self):
        """Load all available data sources"""
        print("Loading comprehensive SUHI analysis data...")
        
        # Load SUHI batch summary
        suhi_file = self.base_path / "reports" / "suhi_batch_summary.json"
        if suhi_file.exists():
            with open(suhi_file, 'r') as f:
                self.suhi_data = json.load(f)
            print(f"✓ Loaded SUHI data for {len(self.suhi_data)} cities")
            
            # Extract cities and years
            for city, years_data in self.suhi_data.items():
                self.cities.add(city)
                for year in years_data.keys():
                    self.years.add(int(year))
        
        # Load LULC analysis summary
        lulc_file = self.base_path / "reports" / "lulc_analysis_summary.json"
        if lulc_file.exists():
            with open(lulc_file, 'r') as f:
                self.lulc_data = json.load(f)
            print(f"✓ Loaded LULC data for {len(self.lulc_data)} cities")
        
        # Load nightlights summary
        nightlights_file = self.base_path / "reports" / "nightlights_summary.json"
        if nightlights_file.exists():
            with open(nightlights_file, 'r') as f:
                self.nightlights_data = json.load(f)
            print(f"✓ Loaded nightlights data for {len(self.nightlights_data)} cities")
        
        # Load spatial relationships
        spatial_file = self.base_path / "reports" / "spatial_relationships_report.json"
        if spatial_file.exists():
            with open(spatial_file, 'r') as f:
                self.spatial_data = json.load(f)
            print(f"✓ Loaded spatial relationships data")
        
        # Load temperature data
        temp_dir = self.base_path / "temperature"
        if temp_dir.exists():
            for city_dir in temp_dir.iterdir():
                if city_dir.is_dir():
                    city = city_dir.name
                    self.temperature_data[city] = {}
                    for temp_file in city_dir.glob("*_temperature_stats_*.json"):
                        year_str = temp_file.name.split('_')[-1].replace('.json', '')
                        try:
                            year = int(year_str)
                            with open(temp_file, 'r') as f:
                                self.temperature_data[city][year] = json.load(f)
                        except (ValueError, json.JSONDecodeError):
                            continue
            print(f"✓ Loaded temperature data for {len(self.temperature_data)} cities")
        
        self.years = sorted(list(self.years))
        self.cities = sorted(list(self.cities))
        print(f"✓ Analysis scope: {len(self.cities)} cities, {len(self.years)} years ({min(self.years)}-{max(self.years)})")

    def create_suhi_trends_with_confidence(self):
        """Create SUHI trends over time with confidence intervals"""
        if not self.suhi_data:
            print("No SUHI data available")
            return None
            
        # Create subplots for day and night SUHI
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=("Daytime SUHI Trends with 95% Confidence Intervals", 
                          "Nighttime SUHI Trends with 95% Confidence Intervals"),
            vertical_spacing=0.1
        )
        
        for i, (city, city_data) in enumerate(self.suhi_data.items()):
            if len(city_data) < 2:  # Need at least 2 years for trends
                continue
                
            years = []
            suhi_day = []
            suhi_night = []
            suhi_day_ci_lower = []
            suhi_day_ci_upper = []
            suhi_night_ci_lower = []
            suhi_night_ci_upper = []
            
            for year, data in sorted(city_data.items()):
                years.append(int(year))
                stats = data.get('stats', {})
                
                # Day SUHI
                suhi_day.append(stats.get('suhi_day', 0))
                
                # Night SUHI
                suhi_night.append(stats.get('suhi_night', 0))
                
                # Confidence intervals (calculate from uncertainty data)
                unc_day = stats.get('uncertainty_day', {})
                unc_night = stats.get('uncertainty_night', {})
                
                # Day CI (urban - rural with propagated uncertainty)
                urban_day_ci = unc_day.get('urban_core', {}).get('ci95', [0, 0])
                rural_day_ci = unc_day.get('rural_ring', {}).get('ci95', [0, 0])
                day_ci_range = max(abs(urban_day_ci[1] - urban_day_ci[0]), abs(rural_day_ci[1] - rural_day_ci[0]))
                suhi_day_ci_lower.append(stats.get('suhi_day', 0) - day_ci_range/2)
                suhi_day_ci_upper.append(stats.get('suhi_day', 0) + day_ci_range/2)
                
                # Night CI
                urban_night_ci = unc_night.get('urban_core', {}).get('ci95', [0, 0])
                rural_night_ci = unc_night.get('rural_ring', {}).get('ci95', [0, 0])
                night_ci_range = max(abs(urban_night_ci[1] - urban_night_ci[0]), abs(rural_night_ci[1] - rural_night_ci[0]))
                suhi_night_ci_lower.append(stats.get('suhi_night', 0) - night_ci_range/2)
                suhi_night_ci_upper.append(stats.get('suhi_night', 0) + night_ci_range/2)
            
            color = self.city_colors.get(city, f"hsl({i*30}, 70%, 50%)")
            
            # Day SUHI with confidence bands
            fig.add_trace(go.Scatter(
                x=years, y=suhi_day_ci_upper,
                fill=None, mode='lines', line_color='rgba(0,0,0,0)',
                showlegend=False, name=f'{city} CI Upper'
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=years, y=suhi_day_ci_lower,
                fill='tonexty', mode='lines', line_color='rgba(0,0,0,0)',
                name=f'{city} 95% CI', fillcolor=color.replace('rgb', 'rgba').replace(')', ', 0.2)'),
                showlegend=False
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=years, y=suhi_day, mode='lines+markers',
                name=f'{city}', line=dict(color=color, width=2),
                marker=dict(size=6)
            ), row=1, col=1)
            
            # Night SUHI with confidence bands
            fig.add_trace(go.Scatter(
                x=years, y=suhi_night_ci_upper,
                fill=None, mode='lines', line_color='rgba(0,0,0,0)',
                showlegend=False
            ), row=2, col=1)
            
            fig.add_trace(go.Scatter(
                x=years, y=suhi_night_ci_lower,
                fill='tonexty', mode='lines', line_color='rgba(0,0,0,0)',
                fillcolor=color.replace('rgb', 'rgba').replace(')', ', 0.2)'),
                showlegend=False
            ), row=2, col=1)
            
            fig.add_trace(go.Scatter(
                x=years, y=suhi_night, mode='lines+markers',
                line=dict(color=color, width=2), marker=dict(size=6),
                showlegend=False
            ), row=2, col=1)
        
        # Add zero reference lines
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5, row=1, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5, row=2, col=1)
        
        fig.update_layout(
            title=dict(
                text="Surface Urban Heat Island (SUHI) Temporal Trends with Uncertainty<br><sub>Uzbekistan Urban Centers (2016-2024)</sub>",
                x=0.5, font=dict(size=18)
            ),
            height=800, width=1200,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        fig.update_xaxes(title_text="Year", row=2, col=1)
        fig.update_yaxes(title_text="SUHI Daytime (°C)", row=1, col=1)
        fig.update_yaxes(title_text="SUHI Nighttime (°C)", row=2, col=1)
        
        # Save
        html_file = self.output_path / "01_suhi_trends_with_confidence.html"
        png_file = self.output_path / "01_suhi_trends_with_confidence.png"
        fig.write_html(str(html_file))
        safe_write_image(fig, png_file, width=1200, height=800, scale=2)
        print(f"✓ Saved SUHI trends chart: {html_file.name}")
        return fig

    def create_urban_heat_comparison(self):
        """Compare urban vs rural temperatures with error bars"""
        if not self.suhi_data:
            return None
            
        cities = []
        urban_day = []
        rural_day = []
        urban_night = []
        rural_night = []
        urban_day_err = []
        rural_day_err = []
        urban_night_err = []
        rural_night_err = []
        
        # Use latest year data
        latest_year = str(max(self.years))
        
        for city, city_data in self.suhi_data.items():
            if latest_year not in city_data:
                continue
                
            data = city_data[latest_year]
            stats = data.get('stats', {})
            
            cities.append(city)
            urban_day.append(stats.get('day_urban_mean', 0))
            rural_day.append(stats.get('day_rural_mean', 0))
            urban_night.append(stats.get('night_urban_mean', 0))
            rural_night.append(stats.get('night_rural_mean', 0))
            
            # Error bars from uncertainty
            unc_day = stats.get('uncertainty_day', {})
            unc_night = stats.get('uncertainty_night', {})
            
            urban_day_err.append(unc_day.get('urban_core', {}).get('stdError', 0))
            rural_day_err.append(unc_day.get('rural_ring', {}).get('stdError', 0))
            urban_night_err.append(unc_night.get('urban_core', {}).get('stdError', 0))
            rural_night_err.append(unc_night.get('rural_ring', {}).get('stdError', 0))
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=(f"Daytime Temperatures ({latest_year})", f"Nighttime Temperatures ({latest_year})"),
            shared_yaxes=False
        )
        
        # Daytime comparison
        fig.add_trace(go.Bar(
            x=cities, y=urban_day, name="Urban Core",
            error_y=dict(type='data', array=urban_day_err, visible=True),
            marker_color=self.suhi_colors['day'], opacity=0.8
        ), row=1, col=1)
        
        fig.add_trace(go.Bar(
            x=cities, y=rural_day, name="Rural Ring",
            error_y=dict(type='data', array=rural_day_err, visible=True),
            marker_color="#ffb366", opacity=0.8
        ), row=1, col=1)
        
        # Nighttime comparison
        fig.add_trace(go.Bar(
            x=cities, y=urban_night, name="Urban Core",
            error_y=dict(type='data', array=urban_night_err, visible=True),
            marker_color=self.suhi_colors['night'], opacity=0.8,
            showlegend=False
        ), row=1, col=2)
        
        fig.add_trace(go.Bar(
            x=cities, y=rural_night, name="Rural Ring",
            error_y=dict(type='data', array=rural_night_err, visible=True),
            marker_color="#66b3ff", opacity=0.8,
            showlegend=False
        ), row=1, col=2)
        
        fig.update_layout(
            title=dict(
                text=f"Urban vs Rural Temperature Comparison ({latest_year})<br><sub>Land Surface Temperature with Standard Error Bars</sub>",
                x=0.5, font=dict(size=18)
            ),
            height=600, width=1200,
            barmode='group'
        )
        
        fig.update_xaxes(title_text="Cities", row=1, col=1)
        fig.update_xaxes(title_text="Cities", row=1, col=2)
        fig.update_yaxes(title_text="Temperature (°C)", row=1, col=1)
        fig.update_yaxes(title_text="Temperature (°C)", row=1, col=2)
        
        # Save
        html_file = self.output_path / "02_urban_rural_temperature_comparison.html"
        png_file = self.output_path / "02_urban_rural_temperature_comparison.png"
        fig.write_html(str(html_file))
        safe_write_image(fig, png_file, width=1200, height=600, scale=2)
        print(f"✓ Saved temperature comparison chart: {html_file.name}")
        return fig

    def create_lulc_change_analysis(self):
        """Analyze land use land cover changes over time"""
        if not self.lulc_data:
            return None
            
        # Focus on Built_Area and vegetation classes
        years_range = [min(self.years), max(self.years)]
        
        cities = []
        built_area_change = []
        crops_change = []
        trees_change = []
        water_change = []
        
        for city_data in self.lulc_data:
            city = city_data.get('city')
            areas = city_data.get('areas_m2', {})
            
            if str(years_range[0]) in areas and str(years_range[1]) in areas:
                cities.append(city)
                
                # Calculate percentage changes
                start_data = areas[str(years_range[0])]
                end_data = areas[str(years_range[1])]
                
                def calc_change(class_name):
                    start_pct = start_data.get(class_name, {}).get('percentage', 0)
                    end_pct = end_data.get(class_name, {}).get('percentage', 0)
                    return end_pct - start_pct
                
                built_area_change.append(calc_change('Built_Area'))
                crops_change.append(calc_change('Crops'))
                trees_change.append(calc_change('Trees'))
                water_change.append(calc_change('Water'))
        
        fig = go.Figure()
        
        # Create stacked bar chart
        fig.add_trace(go.Bar(
            x=cities, y=built_area_change, name="Built Area",
            marker_color="#d62728", opacity=0.8
        ))
        
        fig.add_trace(go.Bar(
            x=cities, y=crops_change, name="Crops",
            marker_color="#2ca02c", opacity=0.8
        ))
        
        fig.add_trace(go.Bar(
            x=cities, y=trees_change, name="Trees",
            marker_color="#8c564b", opacity=0.8
        ))
        
        fig.add_trace(go.Bar(
            x=cities, y=water_change, name="Water",
            marker_color="#17becf", opacity=0.8
        ))
        
        # Add zero reference line
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
        
        fig.update_layout(
            title=dict(
                text=f"Land Use Land Cover Changes ({years_range[0]}-{years_range[1]})<br><sub>Percentage Point Changes in Area Coverage</sub>",
                x=0.5, font=dict(size=18)
            ),
            xaxis_title="Cities",
            yaxis_title="Change in Coverage (%)",
            height=600, width=1000,
            barmode='relative'
        )
        
        # Save
        html_file = self.output_path / "03_lulc_change_analysis.html"
        png_file = self.output_path / "03_lulc_change_analysis.png"
        fig.write_html(str(html_file))
        safe_write_image(fig, png_file, width=1000, height=600, scale=2)
        print(f"✓ Saved LULC change analysis: {html_file.name}")
        return fig

    def create_nightlights_vs_suhi(self):
        """Correlate nighttime lights with SUHI intensity"""
        if not self.nightlights_data or not self.suhi_data:
            return None
            
        # Prepare data for correlation
        data_points = []
        
        for city_data in self.nightlights_data:
            city = city_data.get('city')
            years_data = city_data.get('years', {})
            
            if city not in self.suhi_data:
                continue
                
            for year_str, night_data in years_data.items():
                if year_str not in self.suhi_data[city]:
                    continue
                    
                # Nightlights urban-rural difference
                stats = night_data.get('stats', {})
                urban_nl = stats.get('urban_core', {}).get('mean', 0)
                rural_nl = stats.get('rural_ring', {}).get('mean', 0)
                nl_difference = urban_nl - rural_nl
                
                # SUHI night
                suhi_stats = self.suhi_data[city][year_str].get('stats', {})
                suhi_night = suhi_stats.get('suhi_night', 0)
                
                data_points.append({
                    'city': city,
                    'year': int(year_str),
                    'nightlights_diff': nl_difference,
                    'suhi_night': suhi_night,
                    'urban_nl': urban_nl,
                    'rural_nl': rural_nl
                })
        
        if not data_points:
            return None
            
        df = pd.DataFrame(data_points)
        
        # Create scatter plot
        fig = go.Figure()
        
        for city in df['city'].unique():
            city_data = df[df['city'] == city]
            color = self.city_colors.get(city, "#7f7f7f")
            
            fig.add_trace(go.Scatter(
                x=city_data['nightlights_diff'],
                y=city_data['suhi_night'],
                mode='markers',
                name=city,
                marker=dict(
                    color=color,
                    size=8,
                    opacity=0.7,
                    line=dict(width=1, color='white')
                ),
                text=city_data['year'],
                hovertemplate=f"<b>{city}</b><br>" +
                            "Year: %{text}<br>" +
                            "Nightlights Diff: %{x:.2f}<br>" +
                            "SUHI Night: %{y:.2f}°C<extra></extra>"
            ))
        
        # Add trend line
        if len(df) > 2:
            z = np.polyfit(df['nightlights_diff'], df['suhi_night'], 1)
            p = np.poly1d(z)
            x_trend = np.linspace(df['nightlights_diff'].min(), df['nightlights_diff'].max(), 100)
            
            fig.add_trace(go.Scatter(
                x=x_trend, y=p(x_trend),
                mode='lines',
                name=f'Trend (R² = {np.corrcoef(df["nightlights_diff"], df["suhi_night"])[0,1]**2:.3f})',
                line=dict(color='red', dash='dash', width=2)
            ))
        
        fig.update_layout(
            title=dict(
                text="Nighttime Lights vs SUHI Nighttime Intensity<br><sub>Urban-Rural Difference in Nighttime Lights vs Nighttime SUHI</sub>",
                x=0.5, font=dict(size=18)
            ),
            xaxis_title="Nighttime Lights Difference (Urban - Rural)",
            yaxis_title="SUHI Nighttime Intensity (°C)",
            height=600, width=1000
        )
        
        # Save
        html_file = self.output_path / "04_nightlights_vs_suhi.html"
        png_file = self.output_path / "04_nightlights_vs_suhi.png"
        fig.write_html(str(html_file))
        safe_write_image(fig, png_file, width=1000, height=600, scale=2)
        print(f"✓ Saved nightlights vs SUHI analysis: {html_file.name}")
        return fig

    def create_spatial_relationships_dashboard(self):
        """Create comprehensive spatial relationships analysis"""
        if not self.spatial_data:
            return None
            
        per_year_data = self.spatial_data.get('per_year', {})
        if not per_year_data:
            return None
            
        # Create 2x2 subplot
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "Vegetation Accessibility vs Built Distance",
                "Vegetation Patch Isolation Changes",
                "Urban Patch Size Distribution",
                "Vegetation Patch Count Changes"
            ),
            specs=[[{"type": "scatter"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        # Collect data for each analysis
        cities = []
        veg_access_2016 = []
        veg_access_2024 = []
        built_dist_2016 = []
        built_dist_2024 = []
        veg_isolation_2016 = []
        veg_isolation_2024 = []
        veg_patches_2016 = []
        veg_patches_2024 = []
        built_patch_size_2016 = []
        built_patch_size_2024 = []
        
        for city, city_data in per_year_data.items():
            if '2016' in city_data and '2024' in city_data:
                cities.append(city)
                
                # Vegetation accessibility
                veg_access_2016.append(city_data['2016'].get('vegetation_accessibility', {}).get('city', {}).get('mean', 0))
                veg_access_2024.append(city_data['2024'].get('vegetation_accessibility', {}).get('city', {}).get('mean', 0))
                
                # Built distance
                built_dist_2016.append(city_data['2016'].get('built_distance_stats', {}).get('city', {}).get('mean', 0))
                built_dist_2024.append(city_data['2024'].get('built_distance_stats', {}).get('city', {}).get('mean', 0))
                
                # Vegetation isolation
                veg_isolation_2016.append(city_data['2016'].get('veg_patch_isolation_mean_m', 0))
                veg_isolation_2024.append(city_data['2024'].get('veg_patch_isolation_mean_m', 0))
                
                # Patch counts
                veg_patches_2016.append(city_data['2016'].get('veg_patches', {}).get('patch_count', 0))
                veg_patches_2024.append(city_data['2024'].get('veg_patches', {}).get('patch_count', 0))
                
                # Built patch sizes
                built_patch_size_2016.append(city_data['2016'].get('built_patches', {}).get('mean_patch_area_m2', 0))
                built_patch_size_2024.append(city_data['2024'].get('built_patches', {}).get('mean_patch_area_m2', 0))
        
        # Panel 1: Vegetation Accessibility vs Built Distance (2024)
        for i, city in enumerate(cities):
            color = self.city_colors.get(city, f"hsl({i*30}, 70%, 50%)")
            fig.add_trace(go.Scatter(
                x=[veg_access_2024[i]], y=[built_dist_2024[i]],
                mode='markers+text', text=[city], textposition='top center',
                marker=dict(size=10, color=color, opacity=0.7),
                name=city, showlegend=False
            ), row=1, col=1)
        
        # Panel 2: Vegetation Isolation Changes
        isolation_change = [v24 - v16 for v24, v16 in zip(veg_isolation_2024, veg_isolation_2016)]
        colors = ['red' if x > 0 else 'green' for x in isolation_change]
        fig.add_trace(go.Bar(
            x=cities, y=isolation_change,
            marker_color=colors, opacity=0.7,
            name="Isolation Change", showlegend=False
        ), row=1, col=2)
        
        # Panel 3: Built Patch Sizes
        fig.add_trace(go.Bar(
            x=cities, y=built_patch_size_2016,
            name="2016", marker_color="#1f77b4", opacity=0.7
        ), row=2, col=1)
        fig.add_trace(go.Bar(
            x=cities, y=built_patch_size_2024,
            name="2024", marker_color="#ff7f0e", opacity=0.7
        ), row=2, col=1)
        
        # Panel 4: Vegetation Patch Count Changes
        patch_change = [v24 - v16 for v24, v16 in zip(veg_patches_2024, veg_patches_2016)]
        colors = ['green' if x > 0 else 'red' for x in patch_change]
        fig.add_trace(go.Bar(
            x=cities, y=patch_change,
            marker_color=colors, opacity=0.7,
            name="Patch Count Change", showlegend=False
        ), row=2, col=2)
        
        # Update layout
        fig.update_layout(
            title=dict(
                text="Spatial Relationships Analysis Dashboard (2016-2024)<br><sub>Urban Green Space Accessibility and Fragmentation Metrics</sub>",
                x=0.5, font=dict(size=18)
            ),
            height=800, width=1200
        )
        
        # Update axes
        fig.update_xaxes(title_text="Vegetation Accessibility (m)", row=1, col=1)
        fig.update_yaxes(title_text="Built Distance (m)", row=1, col=1)
        fig.update_xaxes(title_text="Cities", row=1, col=2)
        fig.update_yaxes(title_text="Isolation Change (m)", row=1, col=2)
        fig.update_xaxes(title_text="Cities", row=2, col=1)
        fig.update_yaxes(title_text="Mean Patch Area (m²)", row=2, col=1)
        fig.update_xaxes(title_text="Cities", row=2, col=2)
        fig.update_yaxes(title_text="Patch Count Change", row=2, col=2)
        
        # Add reference lines
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5, row=1, col=2)
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5, row=2, col=2)
        
        # Save
        html_file = self.output_path / "05_spatial_relationships_dashboard.html"
        png_file = self.output_path / "05_spatial_relationships_dashboard.png"
        fig.write_html(str(html_file))
        safe_write_image(fig, png_file, width=1200, height=800, scale=2)
        print(f"✓ Saved spatial relationships dashboard: {html_file.name}")
        return fig

    def create_comprehensive_suhi_analysis(self):
        """Create comprehensive SUHI analysis with multiple variables"""
        if not self.suhi_data:
            return None
            
        # Prepare comprehensive dataset
        analysis_data = []
        
        for city, city_data in self.suhi_data.items():
            for year_str, data in city_data.items():
                year = int(year_str)
                stats = data.get('stats', {})
                
                row = {
                    'city': city,
                    'year': year,
                    'suhi_day': stats.get('suhi_day', 0),
                    'suhi_night': stats.get('suhi_night', 0),
                    'suhi_day_night_diff': stats.get('suhi_day_night_diff', 0),
                    'day_stronger_than_night': stats.get('day_stronger_than_night', False),
                    'urban_day_temp': stats.get('day_urban_mean', 0),
                    'rural_day_temp': stats.get('day_rural_mean', 0),
                    'urban_night_temp': stats.get('night_urban_mean', 0),
                    'rural_night_temp': stats.get('night_rural_mean', 0)
                }
                analysis_data.append(row)
        
        if not analysis_data:
            return None
            
        df = pd.DataFrame(analysis_data)
        
        # Create comprehensive analysis figure
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                "SUHI Day vs Night Intensity",
                "Day-Night SUHI Difference Distribution",
                "Urban Temperature Evolution",
                "SUHI Intensity Distribution by City",
                "Temperature Range Analysis",
                "SUHI Seasonal Patterns"
            ),
            specs=[[{"type": "scatter"}, {"type": "histogram"}],
                   [{"type": "scatter"}, {"type": "box"}],
                   [{"type": "bar"}, {"type": "scatter"}]]
        )
        
        # Panel 1: Day vs Night SUHI
        for city in df['city'].unique():
            city_data = df[df['city'] == city]
            color = self.city_colors.get(city, "#7f7f7f")
            
            fig.add_trace(go.Scatter(
                x=city_data['suhi_day'], y=city_data['suhi_night'],
                mode='markers', name=city,
                marker=dict(color=color, size=6, opacity=0.7),
                text=city_data['year'],
                hovertemplate=f"<b>{city}</b><br>Year: %{{text}}<br>Day SUHI: %{{x:.2f}}°C<br>Night SUHI: %{{y:.2f}}°C<extra></extra>"
            ), row=1, col=1)
        
        # Add diagonal line
        min_val = min(df['suhi_day'].min(), df['suhi_night'].min())
        max_val = max(df['suhi_day'].max(), df['suhi_night'].max())
        fig.add_trace(go.Scatter(
            x=[min_val, max_val], y=[min_val, max_val],
            mode='lines', line=dict(color='black', dash='dash'),
            name='Equal Day/Night', showlegend=False
        ), row=1, col=1)
        
        # Panel 2: Day-Night Difference Distribution
        fig.add_trace(go.Histogram(
            x=df['suhi_day_night_diff'], name="Day-Night Diff",
            marker_color="steelblue", opacity=0.7, showlegend=False
        ), row=1, col=2)
        
        # Panel 3: Urban Temperature Evolution
        avg_temps = df.groupby('year')[['urban_day_temp', 'urban_night_temp']].mean().reset_index()
        fig.add_trace(go.Scatter(
            x=avg_temps['year'], y=avg_temps['urban_day_temp'],
            mode='lines+markers', name='Urban Day Temp',
            line=dict(color='red', width=2), showlegend=False
        ), row=2, col=1)
        fig.add_trace(go.Scatter(
            x=avg_temps['year'], y=avg_temps['urban_night_temp'],
            mode='lines+markers', name='Urban Night Temp',
            line=dict(color='blue', width=2), showlegend=False
        ), row=2, col=1)
        
        # Panel 4: SUHI Distribution by City
        for city in df['city'].unique():
            city_data = df[df['city'] == city]
            fig.add_trace(go.Box(
                y=city_data['suhi_night'], name=city,
                marker_color=self.city_colors.get(city, "#7f7f7f"),
                showlegend=False
            ), row=2, col=2)
        
        # Panel 5: Temperature Range Analysis
        df['temp_range_urban'] = df['urban_day_temp'] - df['urban_night_temp']
        df['temp_range_rural'] = df['rural_day_temp'] - df['rural_night_temp']
        
        avg_ranges = df.groupby('city')[['temp_range_urban', 'temp_range_rural']].mean()
        fig.add_trace(go.Bar(
            x=avg_ranges.index, y=avg_ranges['temp_range_urban'],
            name='Urban Range', marker_color='orange', opacity=0.7, showlegend=False
        ), row=3, col=1)
        fig.add_trace(go.Bar(
            x=avg_ranges.index, y=avg_ranges['temp_range_rural'],
            name='Rural Range', marker_color='lightblue', opacity=0.7, showlegend=False
        ), row=3, col=1)
        
        # Panel 6: SUHI vs Temperature Range
        fig.add_trace(go.Scatter(
            x=df['temp_range_urban'], y=df['suhi_night'],
            mode='markers', marker=dict(color='purple', size=5, opacity=0.6),
            name='SUHI vs Urban Range', showlegend=False
        ), row=3, col=2)
        
        # Update layout
        fig.update_layout(
            title=dict(
                text="Comprehensive SUHI Analysis Dashboard<br><sub>Multi-dimensional Analysis of Urban Heat Island Patterns</sub>",
                x=0.5, font=dict(size=18)
            ),
            height=1000, width=1200,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        # Update axes labels
        fig.update_xaxes(title_text="SUHI Day (°C)", row=1, col=1)
        fig.update_yaxes(title_text="SUHI Night (°C)", row=1, col=1)
        fig.update_xaxes(title_text="Day-Night Difference (°C)", row=1, col=2)
        fig.update_yaxes(title_text="Frequency", row=1, col=2)
        fig.update_xaxes(title_text="Year", row=2, col=1)
        fig.update_yaxes(title_text="Temperature (°C)", row=2, col=1)
        fig.update_yaxes(title_text="SUHI Night (°C)", row=2, col=2)
        fig.update_xaxes(title_text="Cities", row=3, col=1)
        fig.update_yaxes(title_text="Temperature Range (°C)", row=3, col=1)
        fig.update_xaxes(title_text="Urban Temp Range (°C)", row=3, col=2)
        fig.update_yaxes(title_text="SUHI Night (°C)", row=3, col=2)
        
        # Save
        html_file = self.output_path / "06_comprehensive_suhi_analysis.html"
        png_file = self.output_path / "06_comprehensive_suhi_analysis.png"
        fig.write_html(str(html_file))
        safe_write_image(fig, png_file, width=1200, height=1000, scale=2)
        print(f"✓ Saved comprehensive SUHI analysis: {html_file.name}")
        return fig

    def create_summary_statistics_table(self):
        """Create a comprehensive summary statistics table"""
        if not self.suhi_data:
            return None
            
        # Prepare summary data
        summary_data = []
        
        for city, city_data in self.suhi_data.items():
            # Get earliest and latest year data
            years = sorted([int(y) for y in city_data.keys()])
            if len(years) < 2:
                continue
                
            earliest_year = str(years[0])
            latest_year = str(years[-1])
            
            earliest_data = city_data[earliest_year]['stats']
            latest_data = city_data[latest_year]['stats']
            
            # Calculate changes
            suhi_day_change = latest_data.get('suhi_day', 0) - earliest_data.get('suhi_day', 0)
            suhi_night_change = latest_data.get('suhi_night', 0) - earliest_data.get('suhi_night', 0)
            
            summary_data.append({
                'City': city,
                'Years Analyzed': f"{years[0]}-{years[-1]}",
                f'SUHI Day {years[0]} (°C)': f"{earliest_data.get('suhi_day', 0):.2f}",
                f'SUHI Day {years[-1]} (°C)': f"{latest_data.get('suhi_day', 0):.2f}",
                'SUHI Day Change (°C)': f"{suhi_day_change:+.2f}",
                f'SUHI Night {years[0]} (°C)': f"{earliest_data.get('suhi_night', 0):.2f}",
                f'SUHI Night {years[-1]} (°C)': f"{latest_data.get('suhi_night', 0):.2f}",
                'SUHI Night Change (°C)': f"{suhi_night_change:+.2f}",
                'Dominant Period': 'Night' if latest_data.get('suhi_night', 0) > abs(latest_data.get('suhi_day', 0)) else 'Day'
            })
        
        if not summary_data:
            return None
            
        df = pd.DataFrame(summary_data)
        
        # Create table visualization
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=list(df.columns),
                fill_color='lightblue',
                align='center',
                font=dict(size=12, color='black')
            ),
            cells=dict(
                values=[df[col] for col in df.columns],
                fill_color='white',
                align='center',
                font=dict(size=11)
            )
        )])
        
        fig.update_layout(
            title=dict(
                text="SUHI Analysis Summary Statistics<br><sub>Temporal Changes in Urban Heat Island Intensity</sub>",
                x=0.5, font=dict(size=16)
            ),
            height=400 + len(df) * 25,
            width=1200
        )
        
        # Save
        html_file = self.output_path / "07_summary_statistics_table.html"
        png_file = self.output_path / "07_summary_statistics_table.png"
        fig.write_html(str(html_file))
        safe_write_image(fig, png_file, width=1200, height=400 + len(df) * 25, scale=2)
        print(f"✓ Saved summary statistics table: {html_file.name}")
        return fig

    def generate_all_charts(self):
        """Generate all comprehensive charts"""
        print("="*80)
        print("COMPREHENSIVE SUHI ANALYSIS CHART GENERATION")
        print("="*80)
        
        # Load all data
        self.load_all_data()
        
        if not any([self.suhi_data, self.lulc_data, self.nightlights_data, self.spatial_data]):
            print("❌ No data available for analysis")
            return
        
        # Generate all charts
        charts = []
        
        print("\n📊 Generating charts...")
        charts.append(self.create_suhi_trends_with_confidence())
        charts.append(self.create_urban_heat_comparison())
        charts.append(self.create_lulc_change_analysis())
        charts.append(self.create_nightlights_vs_suhi())
        charts.append(self.create_spatial_relationships_dashboard())
        charts.append(self.create_comprehensive_suhi_analysis())
        charts.append(self.create_summary_statistics_table())
        
        # Count outputs
        html_count = len(list(self.output_path.glob("*.html")))
        png_count = len(list(self.output_path.glob("*.png")))
        
        print("\n" + "="*80)
        print("✅ CHART GENERATION COMPLETE")
        print("="*80)
        print(f"📁 Output Directory: {self.output_path}")
        print(f"📊 Generated Files: {html_count} HTML + {png_count} PNG")
        print(f"🏙️  Cities Analyzed: {len(self.cities)}")
        print(f"📅 Years Covered: {min(self.years)}-{max(self.years)}")
        print("="*80)
        
        return charts


def main():
    """Main execution function"""
    # Set base path to the suhi_analysis_output directory
    base_path = "/Users/timursabitov/Dev/Uzbekistan_URBAN_research/suhi_analysis_output"
    
    # Create generator and run analysis
    generator = ComprehensiveChartGenerator(base_path)
    charts = generator.generate_all_charts()
    
    return charts


if __name__ == "__main__":
    main()
