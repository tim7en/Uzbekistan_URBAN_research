"""Comprehensive nightlight analysis for Uzbekistan cities and regions (2017-2024).

This script analyzes VIIRS nightlight data comparing:
- City centers + buffer zones vs their containing regional averages
- Complete temporal coverage from 2017 to 2024
- All major Uzbekistan regions including Andijan, Bukhara, Navoi, etc.

Results                f\"{city_name}_{year}_city_vs_administrative_region\"include CSV exports, trend plots, and detailed reporting.
"""
import sys
from pathlib import Path
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Optional, Tuple
import datetime

# Ensure repository root is on sys.path so local `services` package is importable
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import argparse
import ee
from services import gee
from services.utils import (
    UZBEKISTAN_CITIES, DATASETS, ANALYSIS_CONFIG, 
    create_output_directories, rate_limiter, make_json_safe
)

# Regional analysis configuration based on city-centered circular buffers
# This approach uses the actual city locations and creates regional analysis zones
# around each city rather than using administrative boundaries

def calculate_regional_buffer_from_city(city_info: Dict[str, Any], regional_buffer_factor: float = 3.0) -> int:
    """Calculate regional buffer size based on city characteristics.
    
    Args:
        city_info: City configuration from UZBEKISTAN_CITIES
        regional_buffer_factor: Multiplier to determine regional extent (default: 3x city buffer)
    
    Returns:
        Regional buffer radius in meters
    """
    base_buffer = city_info['buffer_m']
    population = city_info.get('population', 100000)
    city_type = city_info.get('type', 'city')
    
    # Adjust regional buffer based on city characteristics
    if city_type == 'capital':
        regional_buffer = base_buffer * 4.0  # Larger region for capital
    elif city_type == 'republic_capital':
        regional_buffer = base_buffer * 3.5  # Larger for republic capital
    elif city_type == 'regional_capital':
        regional_buffer = base_buffer * 3.0  # Standard for regional capitals
    else:
        regional_buffer = base_buffer * 2.5  # Smaller for other cities
    
    # Population-based adjustment
    if population > 1000000:
        regional_buffer *= 1.3
    elif population > 500000:
        regional_buffer *= 1.2
    elif population > 200000:
        regional_buffer *= 1.1
    
    return int(regional_buffer)

# Map cities to their regions for analysis
CITY_TO_REGION_MAP = {
    "Tashkent": "Tashkent Region",  # Use Tashkent Region instead of Tashkent City for meaningful regional comparison
    "Samarkand": "Samarkand Region",
    "Bukhara": "Bukhara Region",
    "Andijan": "Andijan Region",
    "Namangan": "Namangan Region",
    "Fergana": "Fergana Region",
    "Nukus": "Republic of Karakalpakstan",
    "Urgench": "Khorezm Region",
    "Termez": "Surkhandarya Region",
    "Qarshi": "KashKadarya Region",
    "Jizzakh": "Jizzakh Region",
    "Navoiy": "Navoi Region",
    "Gulistan": "Syrdarya Region",
    "Nurafshon": "Tashkent Region"
}


def get_region_administrative_boundary(city_name: str) -> ee.Geometry:
    """Get actual administrative boundary for the region containing the city.
    
    Uses FAO GAUL administrative boundaries to get the proper regional geometry
    instead of circular buffers around cities.
    
    Args:
        city_name: Name of the city from UZBEKISTAN_CITIES
    
    Returns:
        ee.Geometry: Administrative boundary of the region containing the city
    """
    try:
        region_name = CITY_TO_REGION_MAP.get(city_name)
        if not region_name:
            raise ValueError(f"No region mapping found for city {city_name}")
        
        # Load FAO GAUL administrative boundaries
        gaul = ee.FeatureCollection("FAO/GAUL_SIMPLIFIED_500m/2015/level1")
        
        # Filter for Uzbekistan regions
        uzbekistan_regions = gaul.filter(ee.Filter.eq('ADM0_NAME', 'Uzbekistan'))
        
        # Map city region names to GAUL ADM1_NAME
        gaul_region_map = {
            "Tashkent City": "Tashkent city",
            "Tashkent Region": "Tashkent", 
            "Samarkand Region": "Samarkand",
            "Bukhara Region": "Bukhara",
            "Andijan Region": "Andijan",
            "Namangan Region": "Namangan",
            "Fergana Region": "Fergana",
            "Republic of Karakalpakstan": "Karakalpakstan",
            "Khorezm Region": "Khorezm",
            "Surkhandarya Region": "Surkhandarya",
            "KashKadarya Region": "Kashkadarya",
            "Jizzakh Region": "Jizzakh",
            "Navoi Region": "Navoiy",
            "Syrdarya Region": "Sirdarya"
        }
        
        gaul_name = gaul_region_map.get(region_name, region_name)
        
        # Get the specific region boundary
        region_feature = uzbekistan_regions.filter(ee.Filter.eq('ADM1_NAME', gaul_name)).first()
        region_geometry = region_feature.geometry()
        
        print(f"Retrieved administrative boundary for {city_name} → {region_name} ({gaul_name})")
        
        return region_geometry
        
    except Exception as e:
        print(f"Error getting administrative boundary for {city_name}: {e}")
        # Fallback: create a large buffer around the city
        city_info = UZBEKISTAN_CITIES.get(city_name, {"lat": 41.0, "lon": 69.0})
        fallback_center = ee.Geometry.Point([city_info.get('lon', 69.0), city_info.get('lat', 41.0)])
        return fallback_center.buffer(75000)  # 75km fallback buffer


def create_analysis_zones_for_city(city_name: str) -> Dict[str, ee.Geometry]:
    """Create comprehensive analysis zones for a city using proper geometries.
    
    Creates analysis zones:
    - City core: Urban center with configured buffer (city-centered circular)
    - City buffer: Slightly larger urban area (city-centered circular)
    - Regional area: Actual administrative boundary of the region
    - Rural background: Regional administrative area excluding city buffer
    
    Args:
        city_name: Name of the city from UZBEKISTAN_CITIES
    
    Returns:
        Dict with geometry zones for analysis
    """
    city_info = UZBEKISTAN_CITIES.get(city_name)
    if not city_info:
        raise ValueError(f"City {city_name} not found")
    
    # City center point
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    
    # City zones - use circular buffers around city center
    city_core_radius = city_info['buffer_m']
    city_buffer_radius = int(city_core_radius * 1.2)  # Slightly larger
    
    # Regional zone - use actual administrative boundary
    regional_boundary = get_region_administrative_boundary(city_name)
    
    # Create geometries
    zones = {
        'city_core': center.buffer(city_core_radius),
        'city_buffer': center.buffer(city_buffer_radius),
        'regional_area': regional_boundary,
    }
    
    # Rural background (regional administrative area minus city buffer)
    zones['rural_background'] = zones['regional_area'].difference(zones['city_buffer'])
    
    return zones


def load_viirs_monthly_for_year(year: int, geometry: ee.Geometry) -> ee.Image:
    """Load VIIRS monthly composite for a year and return median image."""
    start = f"{year}-01-01"
    end = f"{year}-12-31"
    
    collection = ee.ImageCollection(DATASETS['viirs_monthly']).filterDate(start, end).filterBounds(geometry)
    
    # Get median composite and clip to geometry
    median_image = collection.median().clip(geometry)
    
    return median_image


def compute_nightlight_statistics(image: ee.Image, geometry: ee.Geometry, 
                                scale: int = 500, max_pixels: int = int(1e8)) -> Dict[str, Any]:
    """Compute comprehensive nightlight statistics for a geometry."""
    rate_limiter.wait()
    
    try:
        # Compute basic statistics
        stats = image.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.stdDev(), 
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.count(), 
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.median(), 
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.minMax(), 
                sharedInputs=True
            ),
            geometry=geometry,
            scale=scale,
            maxPixels=max_pixels,
            bestEffort=True
        )
        
        result = stats.getInfo()
        
        # Extract values (handle different band naming conventions)
        band_names = image.bandNames().getInfo()
        band_name = band_names[0] if band_names else 'avg_rad'
        
        processed_stats = {
            'mean': result.get(f'{band_name}_mean', None),
            'median': result.get(f'{band_name}_median', None),
            'stdDev': result.get(f'{band_name}_stdDev', None),
            'count': result.get(f'{band_name}_count', None),
            'min': result.get(f'{band_name}_min', None),
            'max': result.get(f'{band_name}_max', None)
        }
        
        # Compute lit area (areas above threshold)
        lit_threshold = 1.0
        lit_mask = image.gt(lit_threshold)
        lit_area = lit_mask.multiply(ee.Image.pixelArea()).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=scale,
            maxPixels=max_pixels,
            bestEffort=True
        ).getInfo()
        
        # Convert to km²
        band_key = list(lit_area.keys())[0] if lit_area else None
        if band_key and lit_area[band_key]:
            processed_stats['lit_area_km2'] = lit_area[band_key] / 1e6
        else:
            processed_stats['lit_area_km2'] = None
        
        return processed_stats
        
    except Exception as e:
        return {'error': str(e)}


def analyze_city_and_region_nightlights(city_name: str, year: int, 
                                      output_dir: Path) -> Dict[str, Any]:
    """Analyze nightlights for a city using city-centered circular analysis zones."""
    print(f"Analyzing {city_name} ({year})...")
    
    result = {
        'city': city_name,
        'year': year,
        'timestamp': datetime.datetime.utcnow().isoformat()
    }
    
    try:
        # Get city info
        city_info = UZBEKISTAN_CITIES.get(city_name)
        if not city_info:
            result['error'] = f"City {city_name} not found"
            return result
        
        # Create analysis zones based on city location
        analysis_zones = create_analysis_zones_for_city(city_name)
        
        # Load VIIRS data for the regional area
        viirs_image = load_viirs_monthly_for_year(year, analysis_zones['regional_area'])
        
        # Compute statistics for different zones
        city_stats = compute_nightlight_statistics(viirs_image, analysis_zones['city_core'])
        city_buffer_stats = compute_nightlight_statistics(viirs_image, analysis_zones['city_buffer'])
        region_stats = compute_nightlight_statistics(viirs_image, analysis_zones['regional_area'], scale=1000)
        rural_background_stats = compute_nightlight_statistics(viirs_image, analysis_zones['rural_background'], scale=1000)
        
        # Calculate zone characteristics
        region_name = CITY_TO_REGION_MAP.get(city_name, f"{city_name} Region")
        
        # Calculate areas for reporting
        city_area_km2 = (3.14159 * (city_info['buffer_m'] / 1000) ** 2)
        
        result.update({
            'region_name': region_name,
            'city_radius_km': city_info['buffer_m'] / 1000,
            'city_area_km2': city_area_km2,
            'analysis_approach': 'city_center_administrative_region',
            'city_stats': city_stats,
            'city_buffer_stats': city_buffer_stats,
            'region_stats': region_stats,
            'regional_background_stats': rural_background_stats
        })
        
        # Calculate key metrics using city core vs regional background
        if (city_stats.get('mean') is not None and 
            rural_background_stats.get('mean') is not None and 
            rural_background_stats['mean'] != 0):
            result['city_to_region_ratio'] = city_stats['mean'] / rural_background_stats['mean']
        
        # Calculate city vs full region ratio for comparison
        if (city_stats.get('mean') is not None and 
            region_stats.get('mean') is not None and 
            region_stats['mean'] != 0):
            result['city_to_full_region_ratio'] = city_stats['mean'] / region_stats['mean']
        
        # Urban-rural contrast
        if (city_stats.get('mean') is not None and 
            rural_background_stats.get('mean') is not None):
            result['city_background_difference'] = (city_stats['mean'] - 
                                                 rural_background_stats['mean'])
        
        # Generate thumbnail showing the analysis zones
        try:
            # Use regional area for thumbnail to show context
            thumbnail_radius = int(city_info['buffer_m'] * 2.5)  # Show city + some regional context
            thumbnail_path = create_nightlight_thumbnail(
                viirs_image, city_info['lon'], city_info['lat'], 
                thumbnail_radius, output_dir, 
                f"{city_name}_{year}_regional_zones"
            )
            result['thumbnail'] = str(thumbnail_path) if thumbnail_path else None
        except Exception as e:
            result['thumbnail_error'] = str(e)
        
        return result
        
    except Exception as e:
        result['error'] = str(e)
        return result


def create_nightlight_thumbnail(image: ee.Image, center_lon: float, center_lat: float, 
                              buffer_m: int, out_path: Path, file_name: str) -> Optional[Path]:
    """Generate a PNG thumbnail for nightlight visualization."""
    try:
        # Create visualization
        vis_params = {
            'min': 0,
            'max': 50,
            'palette': ['black','#0d0887','#6a00a8','#b12a90','#e16462','#fca636','#f0f921']
        }
        
        bands = image.bandNames().getInfo()
        band = bands[0] if bands else None
        if band:
            vis = image.select([band]).visualize(**vis_params)
        else:
            vis = image.visualize(**vis_params)
        
        # Define region for thumbnail
        region = ee.Geometry.Point([center_lon, center_lat]).buffer(buffer_m).bounds().getInfo()['coordinates']
        
        # Get thumbnail URL and download
        url = vis.getThumbURL({'region': region, 'dimensions': 1024, 'format': 'png'})
        
        import requests
        out_path.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, timeout=60)
        
        if r.status_code == 200:
            thumb_path = out_path / f"{file_name}.png"
            with open(thumb_path, 'wb') as f:
                f.write(r.content)
            return thumb_path
        else:
            print(f"Failed to download thumbnail: HTTP {r.status_code}")
            return None
            
    except Exception as e:
        print(f"Error creating thumbnail: {e}")
        return None


def run_comprehensive_analysis(cities: List[str], years: List[int], 
                             output_base: Path) -> List[Dict[str, Any]]:
    """Run comprehensive nightlight analysis for cities and years."""
    results = []
    
    # Create output directories
    analysis_dir = output_base / 'nightlight_regional_analysis'
    thumbnails_dir = analysis_dir / 'thumbnails'
    analysis_dir.mkdir(parents=True, exist_ok=True)
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    
    total_analyses = len(cities) * len(years)
    current_analysis = 0
    
    for city in cities:
        for year in years:
            current_analysis += 1
            print(f"Processing {current_analysis}/{total_analyses}: {city} {year}")
            
            try:
                result = analyze_city_and_region_nightlights(city, year, thumbnails_dir)
                results.append(result)
                
                # Save individual result
                city_dir = analysis_dir / city
                city_dir.mkdir(parents=True, exist_ok=True)
                result_file = city_dir / f"{city}_{year}_analysis.json"
                
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(make_json_safe(result), f, indent=2)
                
            except Exception as e:
                error_result = {
                    'city': city,
                    'year': year,
                    'error': str(e),
                    'timestamp': datetime.datetime.utcnow().isoformat()
                }
                results.append(error_result)
                print(f"Error analyzing {city} {year}: {e}")
    
    return results


def export_results_to_csv(results: List[Dict[str, Any]], output_path: Path) -> None:
    """Export analysis results to CSV format for easy analysis."""
    csv_data = []
    
    for result in results:
        if 'error' in result:
            continue
            
        row = {
            'city': result.get('city'),
            'year': result.get('year'),
            'administrative_region': result.get('region_name'),
            'analysis_approach': result.get('analysis_approach', 'city_center_administrative_region'),
            'city_radius_km': result.get('city_radius_km'),
            'city_area_km2': result.get('city_area_km2'),
            'city_mean_radiance': result.get('city_stats', {}).get('mean'),
            'city_median_radiance': result.get('city_stats', {}).get('median'),
            'city_stddev_radiance': result.get('city_stats', {}).get('stdDev'),
            'city_lit_area_km2': result.get('city_stats', {}).get('lit_area_km2'),
            'city_buffer_mean_radiance': result.get('city_buffer_stats', {}).get('mean'),
            'city_buffer_lit_area_km2': result.get('city_buffer_stats', {}).get('lit_area_km2'),
            'administrative_region_mean_radiance': result.get('region_stats', {}).get('mean'),
            'administrative_region_median_radiance': result.get('region_stats', {}).get('median'),
            'administrative_region_stddev_radiance': result.get('region_stats', {}).get('stdDev'),
            'administrative_region_lit_area_km2': result.get('region_stats', {}).get('lit_area_km2'),
            'regional_background_mean_radiance': result.get('regional_background_stats', {}).get('mean'),
            'regional_background_median_radiance': result.get('regional_background_stats', {}).get('median'),
            'regional_background_lit_area_km2': result.get('regional_background_stats', {}).get('lit_area_km2'),
            'city_to_regional_background_ratio': result.get('city_to_region_ratio'),
            'city_to_full_administrative_region_ratio': result.get('city_to_full_region_ratio'),
            'city_regional_background_difference': result.get('city_background_difference')
        }
        csv_data.append(row)
    
    df = pd.DataFrame(csv_data)
    df.to_csv(output_path, index=False)
    print(f"Results exported to CSV: {output_path}")


def create_analysis_plots(results: List[Dict[str, Any]], output_dir: Path) -> None:
    """Create comprehensive visualization plots for the analysis."""
    # Prepare data for plotting
    plot_data = []
    
    for result in results:
        if 'error' in result:
            continue
            
        city_mean = result.get('city_stats', {}).get('mean')
        region_mean = result.get('region_stats', {}).get('mean') 
        ratio = result.get('city_to_region_ratio')
        
        if city_mean is not None and region_mean is not None and ratio is not None:
            plot_data.append({
                'city': result.get('city'),
                'year': result.get('year'),
                'region': result.get('region_name'),
                'city_mean': city_mean,
                'region_mean': region_mean,
                'ratio': ratio,
                'city_lit_area': result.get('city_stats', {}).get('lit_area_km2'),
                'region_lit_area': result.get('region_stats', {}).get('lit_area_km2')
            })
    
    if not plot_data:
        print("No valid data for plotting")
        return
    
    df = pd.DataFrame(plot_data)
    
    # Set up the plotting style
    plt.style.use('seaborn-v0_8')
    
    # 1. City vs Region comparison over time
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # Plot 1: Mean radiance comparison
    cities = df['city'].unique()
    for city in cities:
        city_data = df[df['city'] == city].sort_values('year')
        axes[0, 0].plot(city_data['year'], city_data['city_mean'], 
                       marker='o', label=f'{city} (City)', linewidth=2)
        axes[0, 0].plot(city_data['year'], city_data['region_mean'], 
                       marker='s', label=f'{city} (Region)', linestyle='--', alpha=0.7)
    
    axes[0, 0].set_title('Mean Radiance: City vs Regional Background (2017-2024)')
    axes[0, 0].set_xlabel('Year')
    axes[0, 0].set_ylabel('Mean Radiance (nW/cm²/sr)')
    axes[0, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    axes[0, 0].grid(True, alpha=0.3)
    
    # Plot 2: City-to-Region ratio over time
    for city in cities:
        city_data = df[df['city'] == city].sort_values('year')
        axes[0, 1].plot(city_data['year'], city_data['ratio'], 
                       marker='o', label=city, linewidth=2)
    
    axes[0, 1].set_title('City-to-Background Radiance Ratio (2017-2024)')
    axes[0, 1].set_xlabel('Year')
    axes[0, 1].set_ylabel('City/Background Ratio')
    axes[0, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Plot 3: Lit area comparison
    for city in cities:
        city_data = df[df['city'] == city].sort_values('year')
        if city_data['city_lit_area'].notna().any():
            axes[1, 0].plot(city_data['year'], city_data['city_lit_area'], 
                           marker='o', label=f'{city} (City)', linewidth=2)
    
    axes[1, 0].set_title('City Lit Area Over Time (2017-2024)')
    axes[1, 0].set_xlabel('Year')
    axes[1, 0].set_ylabel('Lit Area (km²)')
    axes[1, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    axes[1, 0].grid(True, alpha=0.3)
    
    # Plot 4: Regional distribution of ratios
    latest_year = df['year'].max()
    latest_data = df[df['year'] == latest_year]
    
    axes[1, 1].bar(latest_data['city'], latest_data['ratio'], 
                  color='skyblue', alpha=0.7)
    axes[1, 1].set_title(f'City-to-Background Ratios ({latest_year})')
    axes[1, 1].set_xlabel('City')
    axes[1, 1].set_ylabel('City/Background Ratio')
    axes[1, 1].tick_params(axis='x', rotation=45)
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'nightlight_analysis_comprehensive.png', 
                dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Regional comparison heatmap
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    
    # Create pivot table for heatmap
    pivot_data = df.pivot_table(values='ratio', index='city', columns='year', aggfunc='mean')
    
    sns.heatmap(pivot_data, annot=True, fmt='.2f', cmap='YlOrRd', 
                cbar_kws={'label': 'City/Region Ratio'}, ax=ax)
    ax.set_title('City-to-Region Radiance Ratios Over Time')
    ax.set_xlabel('Year')
    ax.set_ylabel('City')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'nightlight_ratio_heatmap.png', 
                dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Analysis plots saved in {output_dir}")


def generate_summary_report(results: List[Dict[str, Any]], output_dir: Path) -> Path:
    """Generate comprehensive markdown summary report."""
    report_path = output_dir / 'uzbekistan_nightlight_regional_summary.md'
    
    # Calculate summary statistics
    successful_analyses = [r for r in results if 'error' not in r]
    failed_analyses = [r for r in results if 'error' in r]
    
    # Create summary data
    summary_data = []
    for result in successful_analyses:
        city_mean = result.get('city_stats', {}).get('mean')
        region_mean = result.get('region_stats', {}).get('mean')
        ratio = result.get('city_to_region_ratio')
        
        if all(x is not None for x in [city_mean, region_mean, ratio]):
            summary_data.append({
                'city': result.get('city'),
                'year': result.get('year'),
                'region': result.get('region_name'),
                'city_mean': city_mean,
                'region_mean': region_mean,
                'ratio': ratio
            })
    
    df = pd.DataFrame(summary_data)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('# Uzbekistan Nightlight Regional Analysis Report\n\n')
        f.write(f'**Generated:** {datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}\n\n')
        f.write(f'**Analysis Period:** 2017-2024\n\n')
        f.write(f'**Total Analyses:** {len(results)}\n')
        f.write(f'**Successful:** {len(successful_analyses)}\n')
        f.write(f'**Failed:** {len(failed_analyses)}\n\n')
        
        f.write('## Overview\n\n')
        f.write('This report presents a comprehensive analysis of nighttime lights in Uzbekistan, ')
        f.write('comparing urban centers with their surrounding regional contexts from 2017 to 2024. ')
        f.write('The analysis uses VIIRS DNB monthly composites to examine:\n\n')
        f.write('- City + buffer zone radiance vs regional averages\n')
        f.write('- Temporal trends in urban vs regional development\n')
        f.write('- Comparative growth patterns across regions\n\n')
        
        if not df.empty:
            f.write('## Key Findings\n\n')
            
            # Latest year statistics
            latest_year = df['year'].max()
            latest_data = df[df['year'] == latest_year]
            
            f.write(f'### {latest_year} City-to-Region Ratios\n\n')
            for _, row in latest_data.iterrows():
                f.write(f'- **{row["city"]}** ({row["region"]}): {row["ratio"]:.2f}x\n')
            f.write('\n')
            
            # Trends analysis
            f.write('### Growth Trends (2017-2024)\n\n')
            for city in df['city'].unique():
                city_data = df[df['city'] == city].sort_values('year')
                if len(city_data) >= 2:
                    first_ratio = city_data.iloc[0]['ratio']
                    last_ratio = city_data.iloc[-1]['ratio']
                    change = last_ratio - first_ratio
                    change_pct = (change / first_ratio) * 100 if first_ratio != 0 else 0
                    
                    f.write(f'- **{city}**: {first_ratio:.2f} → {last_ratio:.2f} ')
                    f.write(f'({change:+.2f}, {change_pct:+.1f}%)\n')
            f.write('\n')
        
        f.write('## Methodology\n\n')
        f.write('### Data Sources\n')
        f.write(f'- **Nightlight Data:** VIIRS DNB Monthly Composites ({DATASETS["viirs_monthly"]})\n')
        f.write('- **Administrative Boundaries:** FAO GAUL Simplified 500m (2015)\n')
        f.write('- **Temporal Coverage:** January 2017 - December 2024\n\n')
        
        f.write('### Analysis Zones\n')
        f.write('- **City Core:** Urban center with configured buffer (circular: 8-15km radius)\n')
        f.write('- **City Buffer:** Extended urban area (1.2x city core, circular)\n')
        f.write('- **Administrative Region:** Actual regional administrative boundary (FAO GAUL)\n')
        f.write('- **Regional Background:** Administrative region excluding city buffer\n\n')
        
        f.write('### Metrics Calculated\n')
        f.write('- Mean radiance (nanoWatts/cm²/sr)\n')
        f.write('- Median radiance\n')
        f.write('- Standard deviation\n')
        f.write('- Lit area (km² above 1.0 threshold)\n')
        f.write('- City-to-region ratio\n')
        f.write('- City-background difference\n\n')
        
        f.write('## Visualizations\n\n')
        f.write('![Comprehensive Analysis](nightlight_analysis_comprehensive.png)\n\n')
        f.write('![Ratio Heatmap](nightlight_ratio_heatmap.png)\n\n')
        
        if failed_analyses:
            f.write('## Analysis Issues\n\n')
            f.write('The following analyses encountered errors:\n\n')
            for failure in failed_analyses:
                f.write(f'- {failure.get("city")} {failure.get("year")}: {failure.get("error")}\n')
            f.write('\n')
        
        f.write('## Data Files\n\n')
        f.write('- `uzbekistan_nightlight_regional_analysis.csv` - Complete results dataset\n')
        f.write('- Individual city JSON files in subdirectories\n')
        f.write('- Thumbnail images in `thumbnails/` directory\n\n')
    
    return report_path


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Uzbekistan Regional Nightlight Analysis')
    parser.add_argument('--cities', nargs='*', 
                       help='List of cities (default: all configured cities)')
    parser.add_argument('--start-year', type=int, default=2017,
                       help='Start year for analysis (default: 2017)')
    parser.add_argument('--end-year', type=int, default=2024,
                       help='End year for analysis (default: 2024)')
    parser.add_argument('--output-dir', type=Path,
                       help='Custom output directory (default: suhi_analysis_output)')
    parser.add_argument('--skip-thumbnails', action='store_true',
                       help='Skip thumbnail generation to speed up analysis')
    return parser.parse_args()


def main():
    """Main execution function."""
    print("🌃 Uzbekistan Regional Nightlight Analysis (2017-2024)")
    print("🏙️ Cities: Center point + circular buffers")
    print("🗺️ Regions: Administrative boundaries (FAO GAUL)")
    print("=" * 65)
    
    # Parse arguments
    args = parse_arguments()
    
    # Initialize Google Earth Engine (using same approach as nightlight_unit)
    success = gee.initialize_gee()
    if not success:
        print("❌ GEE init failed — aborting nightlight run")
        return 1
    
    print("✅ Google Earth Engine initialized")
    
    # Setup parameters
    years = list(range(args.start_year, args.end_year + 1))
    cities = args.cities if args.cities else list(UZBEKISTAN_CITIES.keys())
    
    # Create output directories
    if args.output_dir:
        output_base = args.output_dir
    else:
        output_dirs = create_output_directories()
        output_base = output_dirs['base']
    
    print(f"📊 Analyzing {len(cities)} cities over {len(years)} years ({len(cities) * len(years)} total analyses)")
    print(f"🏙️ Cities: {', '.join(cities)}")
    print(f"📅 Years: {years[0]}-{years[-1]}")
    print(f"📁 Output: {output_base}")
    
    # Run comprehensive analysis
    print("\n🔄 Starting analysis...")
    results = run_comprehensive_analysis(cities, years, output_base)
    
    # Create analysis output directory
    analysis_dir = output_base / 'nightlight_regional_analysis'
    analysis_dir.mkdir(parents=True, exist_ok=True)
    
    # Save complete results
    results_file = analysis_dir / 'complete_results.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(make_json_safe(results), f, indent=2)
    print(f"💾 Complete results saved: {results_file}")
    
    # Export to CSV
    csv_file = analysis_dir / 'uzbekistan_nightlight_regional_analysis.csv'
    export_results_to_csv(results, csv_file)
    
    # Create plots
    print("📈 Creating analysis plots...")
    create_analysis_plots(results, analysis_dir)
    
    # Generate summary report
    print("📄 Generating summary report...")
    report_path = generate_summary_report(results, analysis_dir)
    print(f"📋 Summary report: {report_path}")
    
    # Print summary
    successful = len([r for r in results if 'error' not in r])
    failed = len([r for r in results if 'error' in r])
    
    print(f"\n✅ Analysis complete!")
    print(f"✅ Successful analyses: {successful}")
    if failed > 0:
        print(f"❌ Failed analyses: {failed}")
    print(f"📁 Results directory: {analysis_dir}")
    
    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)