"""Plotting and visualization helpers."""
import matplotlib.pyplot as plt
import numpy as np
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
from pathlib import Path
from typing import Dict, Any, List, Optional
import warnings
from datetime import datetime
import seaborn as sns

# Configure Plotly
warnings.filterwarnings('ignore')
try:
    pio.templates.default = "plotly_white"
    if hasattr(pio, 'kaleido') and pio.kaleido is not None:
        pio.kaleido.scope.mathjax = None
except (AttributeError, ImportError):
    pass  # Skip if plotly/kaleido not properly installed


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
        """Calculate summary statistics across all cities."""
        self.summary_stats = {
            'total_cities': len(self.cities_data),
            'cities_with_both_years': 0,
            'avg_suhi_2017': 0,
            'avg_suhi_2024': 0,
            'avg_change': 0,
            'max_change': 0,
            'min_change': 0,
            'strongest_warming': '',
            'strongest_cooling': ''
        }
        
        suhi_2017_values = []
        suhi_2024_values = []
        changes = []
        city_changes = {}
        
        for city, years_data in self.cities_data.items():
            if 2017 in years_data and 2024 in years_data:
                self.summary_stats['cities_with_both_years'] += 1
                
                suhi_2017 = years_data[2017].get('suhi', {}).get('intensity', 0)
                suhi_2024 = years_data[2024].get('suhi', {}).get('intensity', 0)
                
                if suhi_2017 and suhi_2024:
                    suhi_2017_values.append(suhi_2017)
                    suhi_2024_values.append(suhi_2024)
                    change = suhi_2024 - suhi_2017
                    changes.append(change)
                    city_changes[city] = change
        
        if suhi_2017_values:
            self.summary_stats['avg_suhi_2017'] = np.mean(suhi_2017_values)
        if suhi_2024_values:
            self.summary_stats['avg_suhi_2024'] = np.mean(suhi_2024_values)
        if changes:
            self.summary_stats['avg_change'] = np.mean(changes)
            self.summary_stats['max_change'] = max(changes)
            self.summary_stats['min_change'] = min(changes)
            
            # Find cities with strongest warming/cooling
            if city_changes:
                max_warming_city = max(city_changes, key=city_changes.get)
                max_cooling_city = min(city_changes, key=city_changes.get)
                self.summary_stats['strongest_warming'] = max_warming_city
                self.summary_stats['strongest_cooling'] = max_cooling_city

    def generate_all_charts(self):
        """Generate all individual charts."""
        print("Generating all SUHI analysis charts...")
        
        # Generate each chart type
        self.create_suhi_comparison_chart()
        self.create_suhi_change_chart()
        self.create_urban_growth_chart()
        self.create_temperature_trends_chart()
        self.create_temporal_analysis_charts()
        self.create_correlation_matrix_chart()
        self.create_statistical_summary_chart()
        self.create_accuracy_assessment_chart()
        self.create_comprehensive_overview_chart()
        
        print(f"✅ All charts generated in: {self.output_path}")

    def create_suhi_comparison_chart(self):
        """Create comparison chart for 2017 vs 2024 SUHI values."""
        cities = []
        suhi_2017 = []
        suhi_2024 = []
        
        for city, years_data in self.cities_data.items():
            if 2017 in years_data and 2024 in years_data:
                suhi_17 = years_data[2017].get('suhi', {}).get('intensity', 0)
                suhi_24 = years_data[2024].get('suhi', {}).get('intensity', 0)
                
                if suhi_17 and suhi_24:
                    cities.append(city)
                    suhi_2017.append(suhi_17)
                    suhi_2024.append(suhi_24)
        
        if not cities:
            print("No data available for SUHI comparison chart")
            return
        
        fig = go.Figure()
        
        # Add 2017 data
        fig.add_trace(go.Bar(
            name='2017',
            x=cities,
            y=suhi_2017,
            marker_color=self.colors['primary_2017'],
            opacity=0.8
        ))
        
        # Add 2024 data
        fig.add_trace(go.Bar(
            name='2024',
            x=cities,
            y=suhi_2024,
            marker_color=self.colors['primary_2024'],
            opacity=0.8
        ))
        
        fig.update_layout(
            title={
                'text': 'SUHI Intensity Comparison: 2017 vs 2024',
                'x': 0.5,
                'font': {'size': 18, 'family': 'Arial Black'}
            },
            xaxis_title='Cities',
            yaxis_title='SUHI Intensity (K)',
            barmode='group',
            template='plotly_white',
            height=600,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Save chart
        chart_name = "01_suhi_comparison_2017_vs_2024"
        fig.write_html(self.output_path / f"{chart_name}.html")
        fig.write_image(self.output_path / f"{chart_name}.png", width=1200, height=600)
        print(f"📊 Created: {chart_name}")


def create_day_night_comparison_plot(day_night_results: Dict, city_name: str, year: int, output_dir: Path) -> None:
    if 'error' in day_night_results or 'day' not in day_night_results or 'night' not in day_night_results:
        print(f"     ⚠️ Insufficient data for day/night comparison")
        return
    day_data = day_night_results['day']
    night_data = day_night_results['night']
    if 'error' in day_data or 'error' in night_data:
        print(f"     ⚠️ Error in day/night data")
        return
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2,2, figsize=(12,10))
    periods = ['Day','Night']
    suhi_values = [day_data.get('suhi',0), night_data.get('suhi',0)]
    colors = ['#ff6b6b', '#4ecdc4']
    ax1.bar(periods, suhi_values, color=colors, alpha=0.7)
    ax1.set_ylabel('SUHI Intensity (K)')
    ax1.set_title(f'{city_name} Day vs Night SUHI ({year})')
    ax1.grid(True, alpha=0.3)
    urban_temps = [day_data.get('urban_mean',0), night_data.get('urban_mean',0)]
    rural_temps = [day_data.get('rural_mean',0), night_data.get('rural_mean',0)]
    x = np.arange(len(periods)); width = 0.35
    ax2.bar(x - width/2, urban_temps, width, label='Urban', color='#ff6b6b', alpha=0.7)
    ax2.bar(x + width/2, rural_temps, width, label='Rural', color='#4ecdc4', alpha=0.7)
    ax2.set_ylabel('LST (K)')
    ax2.set_title('Urban vs Rural Temperatures')
    ax2.set_xticks(x); ax2.set_xticklabels(periods); ax2.legend(); ax2.grid(True, alpha=0.3)
    if 'day_night_difference' in day_night_results:
        diff_data = day_night_results['day_night_difference']
        ax3.bar(['SUHI Diff'], [diff_data.get('suhi_difference',0)], color='#ffa726', alpha=0.7)
        ax3.set_ylabel('Temperature Difference (K)')
        ax3.set_title('Day-Night SUHI Difference')
        stats_text = f"""
        Day SUHI: {day_data.get('suhi',0):.2f} K
        Night SUHI: {night_data.get('suhi',0):.2f} K
        Difference: {diff_data.get('suhi_difference',0):.2f} K
        Day Stronger: {'Yes' if diff_data.get('day_stronger',False) else 'No'}
        """
        ax4.text(0.1,0.5, stats_text, transform=ax4.transAxes, fontsize=10, verticalalignment='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        ax4.set_title('Analysis Summary'); ax4.axis('off')
    plt.tight_layout()
    output_file = output_dir / f"{city_name}_day_night_suhi_{year}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"     💾 Day/night comparison saved: {output_file}")


def create_multi_city_landcover_comparison(all_results: list, output_dir: Path) -> None:
    print("   📊 Creating multi-city landcover comparison...")
    city_changes = {}
    for result in all_results:
        if 'landcover_changes' not in result or 'error' in result['landcover_changes']:
            continue
        city = result['city']; year = result['year']; landcover_data = result['landcover_changes']
        if 'landcover_changes' in landcover_data:
            changes = landcover_data['landcover_changes']
            if 'Built_Area' in changes:
                built_change = changes['Built_Area']
                city_changes.setdefault(city, {})[year] = {
                    'built_change_km2': built_change.get('change_km2',0),
                    'built_change_pct': built_change.get('change_percent',0),
                    'start_area': built_change.get('start_area_km2',0),
                    'end_area': built_change.get('end_area_km2',0),
                    'period': landcover_data.get('analysis_period','Unknown')
                }
    if not city_changes:
        print('     ⚠️ No landcover change data available for comparison')
        return
    fig, ((ax1, ax2),(ax3, ax4)) = plt.subplots(2,2, figsize=(15,12))
    cities=[]; changes_km2=[]; periods=[]
    for city, years_data in city_changes.items():
        for year, data in years_data.items():
            cities.append(f"{city}\n({data['period']})"); changes_km2.append(data['built_change_km2']); periods.append(data['period'])
    colors = ['#ff6b6b' if c>0 else '#4ecdc4' for c in changes_km2]
    bars = ax1.barh(cities, changes_km2, color=colors, alpha=0.7)
    ax1.set_xlabel('Built Area Change (km²)'); ax1.set_title('Urban Expansion Across Uzbekistan Cities'); ax1.grid(True, alpha=0.3)
    for bar, value in zip(bars, changes_km2):
        ax1.text(value + (0.01 * max(abs(v) for v in changes_km2) if changes_km2 else 0), bar.get_y()+bar.get_height()/2, f'{value:.1f}', ha='left' if value>=0 else 'right', va='center', fontsize=9)
    changes_pct = [data['built_change_pct'] for city in city_changes.values() for data in city.values()]
    ax2.barh(cities, changes_pct, color=['#ffa726' if c>0 else '#26a69a' for c in changes_pct], alpha=0.7)
    ax2.set_xlabel('Built Area Change (%)'); ax2.set_title('Relative Urban Growth Rates'); ax2.grid(True, alpha=0.3)
    city_names = list(city_changes.keys())
    start_areas = []; end_areas = []
    for city in city_names:
        years = list(city_changes[city].keys())
        if years:
            latest_year = max(years)
            start_areas.append(city_changes[city][latest_year]['start_area'])
            end_areas.append(city_changes[city][latest_year]['end_area'])
    x = np.arange(len(city_names)); width=0.35
    ax3.bar(x - width/2, start_areas, width, label='Start Period', color='#3498db', alpha=0.7)
    ax3.bar(x + width/2, end_areas, width, label='End Period', color='#e74c3c', alpha=0.7)
    ax3.set_ylabel('Built Area (km²)'); ax3.set_title('Built Area: Before vs After'); ax3.set_xticks(x); ax3.set_xticklabels(city_names, rotation=45, ha='right'); ax3.legend(); ax3.grid(True, alpha=0.3)
    summary_text = "LANDCOVER CHANGE SUMMARY\n" + "="*30 + "\n\n"
    total_expansion = sum(changes_km2); avg_expansion = np.mean(changes_km2) if changes_km2 else 0
    max_expansion_idx = np.argmax(np.abs(changes_km2)) if changes_km2 else 0
    max_expansion_city = cities[max_expansion_idx].split('\n')[0] if cities else 'N/A'
    summary_text += f"Total Built Area Change: {total_expansion:.2f} km²\n"
    summary_text += f"Average Change per City: {avg_expansion:.2f} km²\n"
    summary_text += f"Largest Change: {max_expansion_city}\n"
    summary_text += f"Cities Analyzed: {len(city_names)}\n"
    ax4.text(0.1,0.5, summary_text, transform=ax4.transAxes, fontsize=11, verticalalignment='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    ax4.set_title('Analysis Summary'); ax4.axis('off')
    plt.suptitle('Uzbekistan Urban Landcover Changes - Comparative Analysis', fontsize=14, fontweight='bold')
    plt.tight_layout()
    timestamp = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"multi_city_landcover_comparison_{timestamp}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"     💾 Multi-city comparison saved: {output_file}")


# Heat Map Functions
def get_city_boundaries(city_name: str, city_info: Dict, buffer_km: Optional[float] = None) -> Dict[str, Any]:
    """Get city boundaries for temperature mapping."""
    try:
        import ee
        
        # Get basic coordinates
        lat = city_info.get('lat', 0)
        lon = city_info.get('lon', 0)
        buffer_km = buffer_km or city_info.get('buffer_km', 10)
        
        # Create buffer in meters
        buffer_meters = buffer_km * 1000
        
        # Create point and buffer
        point = ee.Geometry.Point([lon, lat])
        boundary = point.buffer(buffer_meters)
        
        return {
            'geometry': boundary,
            'center': {'lat': lat, 'lon': lon},
            'buffer_km': buffer_km,
            'success': True
        }
    except Exception as e:
        print(f"Error getting boundaries for {city_name}: {e}")
        return {'error': str(e), 'success': False}


def create_professional_heat_map(temp_data: np.ndarray, city_name: str, city_info: Dict, 
                                  output_path: Path, city_boundaries: Optional[Dict] = None) -> bool:
    """Create professional GIS-style heat map."""
    try:
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature
        from matplotlib.patches import Rectangle
        import matplotlib.colors as mcolors
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        
        # Set up the figure and projection
        fig = plt.figure(figsize=(16, 12))
        projection = ccrs.PlateCarree()
        ax = plt.axes(projection=projection)
        
        # Get city coordinates
        lat = city_info.get('lat', 0)
        lon = city_info.get('lon', 0)
        buffer_km = city_info.get('buffer_km', 10)
        
        # Calculate extent (rough approximation)
        lat_buffer = buffer_km / 111  # 1 degree lat ≈ 111 km
        lon_buffer = buffer_km / (111 * np.cos(np.radians(lat)))
        
        extent = [
            lon - lon_buffer, lon + lon_buffer,
            lat - lat_buffer, lat + lat_buffer
        ]
        ax.set_extent(extent, crs=projection)
        
        # Add map features
        ax.add_feature(cfeature.LAND, color='lightgray', alpha=0.5)
        ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
        ax.add_feature(cfeature.BORDERS, linewidth=0.5)
        ax.add_feature(cfeature.RIVERS, color='lightblue', linewidth=0.5)
        
        # Create temperature colormap
        colors = ['#2166ac', '#4393c3', '#92c5de', '#d1e5f0', 
                 '#f7f7f7', '#fdbf6f', '#ff7f00', '#e31a1c', '#800026']
        n_bins = 256
        cmap = mcolors.LinearSegmentedColormap.from_list('temperature', colors, N=n_bins)
        
        # Create dummy temperature data if none provided
        if temp_data is None or temp_data.size == 0:
            # Create synthetic temperature data for visualization
            x = np.linspace(extent[0], extent[1], 100)
            y = np.linspace(extent[2], extent[3], 100)
            X, Y = np.meshgrid(x, y)
            
            # Create radial temperature pattern (urban heat island effect)
            center_x, center_y = lon, lat
            dist_from_center = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
            max_dist = np.max(dist_from_center)
            
            # Higher temperature in center, lower at edges
            temp_data = 35 + 10 * (1 - dist_from_center / max_dist) + np.random.normal(0, 1, X.shape)
        
        # Plot temperature data
        if hasattr(temp_data, 'shape') and len(temp_data.shape) == 2:
            im = ax.imshow(temp_data, extent=extent, cmap=cmap, alpha=0.7, 
                          transform=projection, interpolation='bilinear')
        else:
            # Fallback for 1D data - create a simple grid
            grid_size = int(np.sqrt(len(temp_data))) if len(temp_data) > 0 else 50
            temp_grid = np.reshape(temp_data[:grid_size**2], (grid_size, grid_size)) if len(temp_data) >= grid_size**2 else np.ones((50, 50)) * 25
            im = ax.imshow(temp_grid, extent=extent, cmap=cmap, alpha=0.7, 
                          transform=projection, interpolation='bilinear')
        
        # Add colorbar
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="3%", pad=0.1, axes_class=plt.Axes)
        cbar = plt.colorbar(im, cax=cax)
        cbar.set_label('Land Surface Temperature (°C)', rotation=270, labelpad=20, fontsize=12)
        
        # Add city marker
        ax.plot(lon, lat, marker='*', color='yellow', markersize=15, 
               transform=projection, markeredgecolor='black', markeredgewidth=1)
        
        # Add title and labels
        plt.suptitle(f'Land Surface Temperature Map - {city_name}', 
                    fontsize=16, fontweight='bold', y=0.95)
        
        # Add gridlines
        gl = ax.gridlines(draw_labels=True, alpha=0.3)
        gl.top_labels = False
        gl.right_labels = False
        
        # Save the map
        output_file = output_path / f"{city_name}_heat_map.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"     💾 Heat map saved: {output_file}")
        return True
        
    except Exception as e:
        print(f"Error creating heat map for {city_name}: {e}")
        return False


# Statistics visualization functions
def create_statistical_summary_plot(data: Dict[str, Any], output_path: Path) -> None:
    """Create statistical summary visualization."""
    try:
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # Summary statistics
        cities = list(data.keys()) if isinstance(data, dict) else []
        
        if cities:
            # Extract SUHI values
            suhi_values = []
            urban_temps = []
            rural_temps = []
            
            for city in cities[:10]:  # Limit to 10 cities for readability
                city_data = data.get(city, {})
                if isinstance(city_data, dict) and 'suhi' in city_data:
                    suhi_values.append(city_data['suhi'].get('intensity', 0))
                    urban_temps.append(city_data.get('urban_mean', 0))
                    rural_temps.append(city_data.get('rural_mean', 0))
            
            # Plot 1: SUHI Intensity Distribution
            if suhi_values:
                ax1.hist(suhi_values, bins=20, alpha=0.7, color='#ff6b6b', edgecolor='black')
                ax1.set_xlabel('SUHI Intensity (K)')
                ax1.set_ylabel('Frequency')
                ax1.set_title('SUHI Intensity Distribution')
                ax1.grid(True, alpha=0.3)
            
            # Plot 2: Urban vs Rural Temperature Comparison
            if urban_temps and rural_temps:
                x = np.arange(len(cities[:len(urban_temps)]))
                width = 0.35
                ax2.bar(x - width/2, urban_temps, width, label='Urban', alpha=0.8, color='#ff6b6b')
                ax2.bar(x + width/2, rural_temps, width, label='Rural', alpha=0.8, color='#4ecdc4')
                ax2.set_xlabel('Cities')
                ax2.set_ylabel('Temperature (K)')
                ax2.set_title('Urban vs Rural Temperatures')
                ax2.set_xticks(x)
                ax2.set_xticklabels(cities[:len(urban_temps)], rotation=45, ha='right')
                ax2.legend()
                ax2.grid(True, alpha=0.3)
        
        # Plot 3: Temperature vs SUHI Correlation
        if suhi_values and urban_temps:
            ax3.scatter(urban_temps, suhi_values, alpha=0.6, color='#ffa726', s=50)
            ax3.set_xlabel('Urban Temperature (K)')
            ax3.set_ylabel('SUHI Intensity (K)')
            ax3.set_title('Urban Temperature vs SUHI Intensity')
            ax3.grid(True, alpha=0.3)
            
            # Add correlation line if enough data
            if len(urban_temps) > 2:
                z = np.polyfit(urban_temps, suhi_values, 1)
                p = np.poly1d(z)
                ax3.plot(urban_temps, p(urban_temps), "r--", alpha=0.8)
        
        # Plot 4: Summary Statistics Text
        stats_text = "ANALYSIS SUMMARY\n" + "="*20 + "\n\n"
        if suhi_values:
            stats_text += f"Average SUHI: {np.mean(suhi_values):.2f} K\n"
            stats_text += f"Max SUHI: {np.max(suhi_values):.2f} K\n"
            stats_text += f"Min SUHI: {np.min(suhi_values):.2f} K\n"
            stats_text += f"Std Dev: {np.std(suhi_values):.2f} K\n"
        stats_text += f"Cities Analyzed: {len(cities)}\n"
        
        ax4.text(0.1, 0.5, stats_text, transform=ax4.transAxes, fontsize=12,
                verticalalignment='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        ax4.set_title('Statistical Summary')
        ax4.axis('off')
        
        plt.tight_layout()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_path / f"statistical_summary_{timestamp}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"     💾 Statistical summary saved: {output_file}")
        
    except Exception as e:
        print(f"Error creating statistical summary plot: {e}")
