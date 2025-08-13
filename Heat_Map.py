#!/usr/bin/env python3
"""
Final 3D Temperature Mapping with Real Basemap Layers
=====================================================
Creates professional 3D temperature maps like Tirana reference with:
- Real OpenStreetMap basemap with street details
- Semi-transparent temperature overlay
- Professional 3D styling and exact colormap match
- Ultra-high resolution and real satellite data
"""

import ee
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle, Polygon
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.io.img_tiles import OSM, GoogleTiles
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib.patches as mpatches
from datetime import datetime, timedelta
import json
from pathlib import Path
import time
import warnings
import math
from scipy import stats
warnings.filterwarnings('ignore')

# Configuration
ANALYSIS_START_YEAR = 2016
ANALYSIS_END_YEAR = 2024
TARGET_RESOLUTION = 150  # High resolution for detail
WARM_SEASON_MONTHS = [6, 7, 8]  # Summer (June, July, August)
MAX_CLOUD_COVER = 20
STATISTICAL_CONFIDENCE = 0.95  # 95% confidence interval

# Comprehensive Uzbekistan cities for temperature analysis
CITIES = {
    # National capital (separate admin unit)
    "Tashkent": {
        "lat": 41.2995, 
        "lon": 69.2401, 
        "buffer_km": 15,
        "description": "National Capital - Urban heat island analysis"
    },
    
    # Republic capital
    "Nukus": {
        "lat": 42.4731, 
        "lon": 59.6103, 
        "buffer_km": 10,
        "description": "Karakalpakstan Republic Capital - Aral Sea impact"
    },
    
    # Regional capitals - Major cities
    "Samarkand": {
        "lat": 39.6542, 
        "lon": 66.9597, 
        "buffer_km": 12,
        "description": "Historical Capital - UNESCO World Heritage site"
    },
    "Bukhara": {
        "lat": 39.7748, 
        "lon": 64.4286, 
        "buffer_km": 10,
        "description": "Ancient Silk Road City - Historic center"
    },
    "Andijan": {
        "lat": 40.7821, 
        "lon": 72.3442, 
        "buffer_km": 12,
        "description": "Fergana Valley - Industrial center"
    },
    "Namangan": {
        "lat": 40.9983, 
        "lon": 71.6726, 
        "buffer_km": 12,
        "description": "Fergana Valley - Agricultural region"
    },
    "Fergana": {
        "lat": 40.3842, 
        "lon": 71.7843, 
        "buffer_km": 12,
        "description": "Fergana Valley - Oil refining center"
    },
    "Urgench": {
        "lat": 41.5506, 
        "lon": 60.6317, 
        "buffer_km": 10,
        "description": "Khorezm Region - Cotton production center"
    },
    "Qarshi": {
        "lat": 38.8606, 
        "lon": 65.7887, 
        "buffer_km": 8,
        "description": "Kashkadarya Region - Gas processing hub"
    },
    "Termez": {
        "lat": 37.2242, 
        "lon": 67.2783, 
        "buffer_km": 8,
        "description": "Surxondaryo Region - Border city with Afghanistan"
    },
    "Navoiy": {
        "lat": 40.1030, 
        "lon": 65.3686, 
        "buffer_km": 10,
        "description": "Mining and metallurgy center - Uranium production"
    },
    "Jizzakh": {
        "lat": 40.1158, 
        "lon": 67.8422, 
        "buffer_km": 8,
        "description": "Agricultural region - Cotton and grain"
    },
    "Gulistan": {
        "lat": 40.4910, 
        "lon": 68.7810, 
        "buffer_km": 8,
        "description": "Sirdaryo Region - Agricultural center"
    },
    "Nurafshon": {
        "lat": 41.0167, 
        "lon": 69.3417, 
        "buffer_km": 8,
        "description": "Tashkent Region - Satellite city"
    }
}

def calculate_trend_significance(trend, trend_std, years_span, confidence_level=0.95):
    """
    Calculate statistical significance of temperature trends
    
    Parameters:
    - trend: trend in °C/year
    - trend_std: standard deviation of trend
    - years_span: number of years in analysis
    - confidence_level: confidence level for statistical test
    
    Returns:
    - dict with significance statistics
    """
    # Degrees of freedom (conservative estimate)
    df = years_span - 2
    
    # Calculate t-statistic
    if trend_std > 0:
        t_stat = trend / trend_std
        
        # Critical t-value for two-tailed test
        alpha = 1 - confidence_level
        try:
            from scipy import stats
            t_critical = stats.t.ppf(1 - alpha/2, df)
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))
        except ImportError:
            # Approximate critical values for common confidence levels
            if confidence_level == 0.95:
                t_critical = 2.306 if df < 5 else (2.228 if df < 10 else 2.0)
            else:
                t_critical = 2.0  # Conservative estimate
            p_value = None
        
        # Determine significance
        is_significant = abs(t_stat) > t_critical
        
        # Calculate confidence interval
        margin_error = t_critical * trend_std
        ci_lower = trend - margin_error
        ci_upper = trend + margin_error
        
    else:
        t_stat = 0
        t_critical = 0
        p_value = 1.0
        is_significant = False
        ci_lower = trend
        ci_upper = trend
    
    return {
        't_statistic': t_stat,
        't_critical': t_critical,
        'p_value': p_value,
        'is_significant': is_significant,
        'confidence_interval': (ci_lower, ci_upper),
        'degrees_freedom': df,
        'significance_level': 'Significant' if is_significant else 'Not significant'
    }

def get_city_boundaries(city_name, city_info, buffer_km=None):
    """
    Get city administrative boundaries using Google Earth Engine
    
    Parameters:
    - city_name: Name of the city
    - city_info: City information dictionary
    - buffer_km: Optional buffer around city center if boundaries not found
    
    Returns:
    - ee.FeatureCollection of city boundaries or None
    """
    print(f"   🗺️ Retrieving administrative boundaries for {city_name}...")
    
    try:
        # Try multiple administrative boundary datasets
        datasets_to_try = [
            'FAO/GAUL/2015/level2',  # Sub-national administrative boundaries
            'FAO/GAUL/2015/level1',  # National administrative boundaries
            'USDOS/LSIB_SIMPLE/2017'  # Large Scale International Boundary
        ]
        
        city_point = ee.Geometry.Point([city_info['lon'], city_info['lat']])
        
        for dataset in datasets_to_try:
            try:
                admin_boundaries = ee.FeatureCollection(dataset)
                
                # Filter by country (Uzbekistan)
                uzbekistan_filter = admin_boundaries.filter(
                    ee.Filter.or_(
                        ee.Filter.eq('ADM0_NAME', 'Uzbekistan'),
                        ee.Filter.eq('COUNTRY_NA', 'Uzbekistan'),
                        ee.Filter.eq('COUNTRY', 'Uzbekistan')
                    )
                )
                
                # Find boundaries that contain the city point
                city_boundaries = uzbekistan_filter.filterBounds(city_point)
                
                # Additional filtering by city name if possible
                if city_boundaries.size().getInfo() > 0:
                    # Try to match city name
                    name_filters = [
                        ee.Filter.stringContains('ADM2_NAME', city_name),
                        ee.Filter.stringContains('ADM1_NAME', city_name),
                        ee.Filter.stringContains('NAME', city_name)
                    ]
                    
                    for name_filter in name_filters:
                        try:
                            named_boundaries = city_boundaries.filter(name_filter)
                            if named_boundaries.size().getInfo() > 0:
                                print(f"   ✅ Found named boundaries for {city_name} in {dataset}")
                                return named_boundaries.first().geometry()
                        except:
                            continue
                    
                    # If no name match, use the boundary containing the point
                    if city_boundaries.size().getInfo() > 0:
                        print(f"   ✅ Found geographic boundaries for {city_name} in {dataset}")
                        return city_boundaries.first().geometry()
                        
            except Exception as e:
                print(f"   ⚠️ Dataset {dataset} unavailable: {e}")
                continue
        
        # If no administrative boundaries found, create approximate city boundary
        print(f"   ⚠️ No administrative boundaries found, creating approximate boundary...")
        buffer_distance = (buffer_km or city_info['buffer_km']) * 1000  # Convert to meters
        approximate_boundary = city_point.buffer(buffer_distance * 0.7)  # 70% of analysis buffer
        
        return approximate_boundary
        
    except Exception as e:
        print(f"   ❌ Error getting boundaries for {city_name}: {e}")
        return None

def extract_boundary_coordinates(boundary_geometry):
    """
    Extract coordinate arrays from Earth Engine geometry for plotting
    
    Parameters:
    - boundary_geometry: ee.Geometry object
    
    Returns:
    - List of coordinate arrays for plotting
    """
    try:
        # Get coordinates from the geometry
        coords_info = boundary_geometry.coordinates().getInfo()
        
        boundary_coords = []
        
        if boundary_geometry.type().getInfo() == 'Polygon':
            # Handle polygon geometry
            for ring in coords_info:
                lons = [coord[0] for coord in ring]
                lats = [coord[1] for coord in ring]
                boundary_coords.append((lons, lats))
                
        elif boundary_geometry.type().getInfo() == 'MultiPolygon':
            # Handle multipolygon geometry
            for polygon in coords_info:
                for ring in polygon:
                    lons = [coord[0] for coord in ring]
                    lats = [coord[1] for coord in ring]
                    boundary_coords.append((lons, lats))
        
        return boundary_coords
        
    except Exception as e:
        print(f"   ⚠️ Error extracting boundary coordinates: {e}")
        return []

def authenticate_gee():
    """Initialize Google Earth Engine"""
    try:
        print("🔑 Initializing Google Earth Engine...")
        ee.Initialize(project='ee-sabitovty')
        print("✅ Google Earth Engine authenticated!")
        return True
    except Exception as e:
        print(f"❌ GEE Authentication failed: {e}")
        return False

def get_working_landsat_composite(region, start_year, end_year, months):
    """
    Get multi-year Landsat thermal composite with scientific statistical analysis
    Calculates average summer temperatures across multiple years (2016-2024)
    """
    print(f"🛰️ Creating multi-year Landsat thermal composite ({start_year}-{end_year})...")
    
    # Landsat 8 and 9 Collection 2 Level 2
    l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
    l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
    
    # Combine collections for entire period
    landsat = l8.merge(l9)
    
    # Filter for the entire analysis period and region
    start_date = f"{start_year}-01-01"
    end_date = f"{end_year}-12-31"
    landsat = landsat.filterDate(start_date, end_date).filterBounds(region)
    
    # Apply cloud masking
    def mask_clouds(image):
        qa = image.select('QA_PIXEL')
        # Bits 3 and 4 are cloud and cloud shadow
        cloud_mask = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0))
        return image.updateMask(cloud_mask)
    
    # Filter by cloud cover and apply cloud masking
    landsat_filtered = landsat.filter(ee.Filter.lt('CLOUD_COVER', MAX_CLOUD_COVER)).map(mask_clouds)
    
    # Filter for summer months only across all years
    def filter_summer_months(image):
        month = ee.Date(image.get('system:time_start')).get('month')
        return ee.Algorithms.If(ee.List(months).contains(month), image, None)
    
    summer_landsat = landsat_filtered.map(filter_summer_months, True).filter(ee.Filter.notNull(['system:time_start']))
    
    size = summer_landsat.size().getInfo()
    print(f"   📊 Found {size} Landsat summer images after cloud filtering ({start_year}-{end_year})")
    
    if size == 0:
        print("   ❌ No valid Landsat summer images found")
        return None
    
    # Calculate Land Surface Temperature with temporal aggregation
    def calculate_lst(image):
        # Get thermal band (Band 10 for Landsat 8/9)
        thermal = image.select('ST_B10')
        
        # Convert to Celsius (Landsat Collection 2 is in Kelvin * 0.00341802 + 149.0)
        lst_celsius = thermal.multiply(0.00341802).add(149.0).subtract(273.15)
        
        # Add year and month as properties for temporal analysis
        date = ee.Date(image.get('system:time_start'))
        year = date.get('year')
        month = date.get('month')
        
        return lst_celsius.rename('LST').set({
            'year': year,
            'month': month,
            'system:time_start': image.get('system:time_start')
        })
    
    # Apply LST calculation
    lst_collection = summer_landsat.map(calculate_lst)
    
    # Calculate multi-year summer average with statistics
    mean_composite = lst_collection.mean().clip(region).rename('LST_mean')
    std_composite = lst_collection.reduce(ee.Reducer.stdDev()).clip(region).rename('LST_stdDev')
    count_composite = lst_collection.count().clip(region).rename('LST_count')
    
    # Calculate temporal trend (slope of temperature over years)
    def add_year_band(image):
        year = ee.Date(image.get('system:time_start')).get('year')
        return image.addBands(ee.Image.constant(year).rename('year').toFloat())
    
    lst_with_year = lst_collection.map(add_year_band)
    trend_composite = lst_with_year.select(['year', 'LST']).reduce(
        ee.Reducer.linearFit()
    ).clip(region)
    
    # Combine all statistics
    final_composite = mean_composite.addBands([
        std_composite,
        count_composite, 
        trend_composite.select('scale').rename('LST_trend'),
        trend_composite.select('offset').rename('LST_intercept')
    ])
    
    print(f"   ✅ Multi-year statistical composite created with trend analysis")
    print(f"   📈 Temporal span: {end_year - start_year + 1} years")
    print(f"   🌡️ Season: Summer months {months}")
    
    return final_composite

def sample_temperature_for_3d(composite, region, city_name, analysis_period):
    """
    Sample multi-year temperature data with statistical analysis for 3D visualization
    """
    print(f"   🔄 Sampling multi-year temperature data for 3D visualization of {city_name}...")
    print(f"   📊 Analysis period: {analysis_period['start_year']}-{analysis_period['end_year']}")
    
    try:
        # Get region bounds
        bounds_info = region.bounds().getInfo()
        coords = bounds_info['coordinates'][0]
        min_lon, min_lat = coords[0]
        max_lon, max_lat = coords[2]
        
        # Create high-resolution sampling grid for 3D detail
        n_points = 65
        lon_points = np.linspace(min_lon, max_lon, n_points)
        lat_points = np.linspace(min_lat, max_lat, n_points)
        
        # Create feature collection for sampling
        points = []
        for i, lat in enumerate(lat_points):
            for j, lon in enumerate(lon_points):
                points.append(ee.Feature(ee.Geometry.Point([lon, lat]), 
                                       {'lat_idx': i, 'lon_idx': j}))
        
        points_fc = ee.FeatureCollection(points)
        
        # Sample all statistical bands at once
        sampled = composite.sampleRegions(
            collection=points_fc,
            scale=TARGET_RESOLUTION,
            geometries=True,
            tileScale=4
        ).getInfo()
        
        if not sampled or 'features' not in sampled:
            print("   ❌ No sampling results")
            return None
        
        # Initialize grids for all statistical measures
        temps_mean = np.full((n_points, n_points), np.nan)
        temps_std = np.full((n_points, n_points), np.nan)
        temps_count = np.full((n_points, n_points), np.nan)
        temps_trend = np.full((n_points, n_points), np.nan)
        
        valid_count = 0
        
        # Process results
        for feature in sampled['features']:
            props = feature['properties']
            
            if ('LST_mean' in props and props['LST_mean'] is not None and
                'LST_stdDev' in props and props['LST_stdDev'] is not None):
                
                temp_mean = props['LST_mean']
                temp_std = props['LST_stdDev']
                temp_count = props.get('LST_count', 0)
                temp_trend = props.get('LST_trend', 0)
                
                lat_idx = props['lat_idx']
                lon_idx = props['lon_idx']
                
                # Filter realistic temperatures and ensure sufficient observations
                if (5 <= temp_mean <= 65 and temp_std >= 0 and 
                    temp_count >= 3):  # At least 3 observations
                    
                    temps_mean[lat_idx, lon_idx] = temp_mean
                    temps_std[lat_idx, lon_idx] = temp_std
                    temps_count[lat_idx, lon_idx] = temp_count
                    temps_trend[lat_idx, lon_idx] = temp_trend
                    valid_count += 1
        
        print(f"   📊 Valid multi-year temperature points: {valid_count}/{n_points*n_points}")
        
        if valid_count < 500:
            print(f"   ❌ Insufficient valid data for statistical analysis ({valid_count} points)")
            return None
        
        # Create coordinate grids
        LON, LAT = np.meshgrid(lon_points, lat_points)
        
        # Enhanced interpolation for smooth surfaces
        if np.any(np.isnan(temps_mean)):
            print("   🔄 Applying statistical interpolation...")
            
            valid_mask = ~np.isnan(temps_mean)
            if np.sum(valid_mask) > 50:
                try:
                    from scipy.interpolate import griddata
                    
                    valid_lons = LON[valid_mask]
                    valid_lats = LAT[valid_mask]
                    valid_means = temps_mean[valid_mask]
                    valid_stds = temps_std[valid_mask]
                    valid_trends = temps_trend[valid_mask]
                    
                    # Interpolate all statistical measures
                    temps_mean = griddata(
                        (valid_lons.flatten(), valid_lats.flatten()),
                        valid_means.flatten(), (LON, LAT),
                        method='cubic', fill_value=np.nanmean(valid_means)
                    )
                    
                    temps_std = griddata(
                        (valid_lons.flatten(), valid_lats.flatten()),
                        valid_stds.flatten(), (LON, LAT),
                        method='cubic', fill_value=np.nanmean(valid_stds)
                    )
                    
                    temps_trend = griddata(
                        (valid_lons.flatten(), valid_lats.flatten()),
                        valid_trends.flatten(), (LON, LAT),
                        method='cubic', fill_value=np.nanmean(valid_trends)
                    )
                    
                    print("   ✅ Statistical interpolation applied")
                    
                except ImportError:
                    print("   ⚠️ Scipy not available, using mean fill")
                    temps_mean = np.where(np.isnan(temps_mean), np.nanmean(temps_mean), temps_mean)
                    temps_std = np.where(np.isnan(temps_std), np.nanmean(temps_std), temps_std)
                    temps_trend = np.where(np.isnan(temps_trend), np.nanmean(temps_trend), temps_trend)
        
        # Calculate comprehensive statistics
        temp_min, temp_max = np.nanmin(temps_mean), np.nanmax(temps_mean)
        temp_mean_avg = np.nanmean(temps_mean)
        temp_spatial_std = np.nanstd(temps_mean)
        temporal_std_avg = np.nanmean(temps_std)
        trend_avg = np.nanmean(temps_trend)
        
        # Statistical significance of trend
        trend_std = np.nanstd(temps_trend)
        years_span = analysis_period['end_year'] - analysis_period['start_year'] + 1
        
        # Calculate trend significance
        trend_significance = calculate_trend_significance(
            trend_avg, trend_std, years_span, STATISTICAL_CONFIDENCE
        )
        
        print(f"   📊 Multi-year temperature statistics ({analysis_period['start_year']}-{analysis_period['end_year']}):")
        print(f"      Spatial Range: {temp_min:.1f}°C to {temp_max:.1f}°C")
        print(f"      Spatial Mean ± SD: {temp_mean_avg:.1f}°C ± {temp_spatial_std:.1f}°C")
        print(f"      Temporal Variability: ±{temporal_std_avg:.1f}°C (avg year-to-year)")
        print(f"      Temperature Trend: {trend_avg:.3f}°C/year ± {trend_std:.3f}°C/year")
        print(f"      Total warming over {years_span} years: {trend_avg * years_span:.2f}°C")
        print(f"      Trend Significance: {trend_significance['significance_level']}")
        print(f"      95% Confidence Interval: [{trend_significance['confidence_interval'][0]:.3f}, {trend_significance['confidence_interval'][1]:.3f}] °C/year")
        
        return {
            'lons': LON,
            'lats': LAT,
            'temperatures': temps_mean,
            'temperature_std': temps_std,
            'temperature_trend': temps_trend,
            'temperature_count': temps_count,
            'bounds': [min_lon, min_lat, max_lon, max_lat],
            'n_valid': valid_count,
            'temp_range': (temp_min, temp_max),
            'temp_mean': temp_mean_avg,
            'temp_spatial_std': temp_spatial_std,
            'temp_temporal_std': temporal_std_avg,
            'temp_trend': trend_avg,
            'temp_trend_std': trend_std,
            'trend_significance': trend_significance,
            'years_span': years_span,
            'total_points': n_points * n_points,
            'analysis_period': analysis_period
        }
        
    except Exception as e:
        print(f"   ❌ Multi-year sampling error: {e}")
        return None

def create_professional_gis_map(temp_data, city_name, city_info, city_boundaries=None):
    """
    Create professional GIS temperature map with advanced cartographic design and city boundaries
    """
    print(f"   🎨 Creating professional GIS map with city boundaries for {city_name}...")
    
    # Create high-quality publication figure with professional layout
    plt.style.use('default')
    fig = plt.figure(figsize=(24, 18), dpi=300, facecolor='white')
    
    # Create main map subplot (larger for prominence)
    gs = fig.add_gridspec(3, 4, height_ratios=[0.1, 1, 0.15], width_ratios=[1, 1, 1, 0.3], 
                         hspace=0.15, wspace=0.1)
    
    # Main map
    ax_main = fig.add_subplot(gs[1, :3], projection=ccrs.PlateCarree())
    
    # Overview map (smaller inset)
    ax_overview = fig.add_subplot(gs[1, 3], projection=ccrs.PlateCarree())
    
    # Title area
    ax_title = fig.add_subplot(gs[0, :])
    ax_title.axis('off')
    
    # Legend and info area
    ax_info = fig.add_subplot(gs[2, :])
    ax_info.axis('off')
    
    # Get data
    lons = temp_data['lons']
    lats = temp_data['lats']
    temps = temp_data['temperatures']
    bounds = temp_data['bounds']
    temp_min, temp_max = temp_data['temp_range']
    
    # === MAIN MAP SETUP ===
    projection = ccrs.PlateCarree()
    
    # Set precise extent with professional margins
    extent_buffer = 0.008
    main_extent = [
        bounds[0] - extent_buffer, bounds[2] + extent_buffer,
        bounds[1] - extent_buffer, bounds[3] + extent_buffer
    ]
    ax_main.set_extent(main_extent, crs=projection)
    
    # === PROFESSIONAL BASEMAP ===
    try:
        # High-quality basemap with multiple layers
        osm_tiles = OSM()
        ax_main.add_image(osm_tiles, 15, alpha=0.85)  # Very high zoom for detail
        print("   ✅ Added high-resolution OpenStreetMap basemap")
    except Exception as e:
        print(f"   ⚠️ OSM unavailable, creating professional cartographic base...")
        
        # Professional cartographic base layers
        ax_main.add_feature(cfeature.LAND, alpha=0.95, color='#f5f5f5', zorder=1)
        ax_main.add_feature(cfeature.OCEAN, alpha=0.95, color='#e8f4f8', zorder=1)
        ax_main.add_feature(cfeature.COASTLINE, alpha=0.8, color='#2c5aa0', linewidth=1.2, zorder=4)
        ax_main.add_feature(cfeature.BORDERS, alpha=0.7, color='#666666', linewidth=1.5, zorder=4)
        ax_main.add_feature(cfeature.RIVERS, alpha=0.8, color='#4da6ff', linewidth=1.8, zorder=3)
        ax_main.add_feature(cfeature.LAKES, alpha=0.8, color='#4da6ff', zorder=3)
        
        # Add urban grid pattern for professional look
        grid_lons = np.linspace(bounds[0], bounds[2], 30)
        grid_lats = np.linspace(bounds[1], bounds[3], 30)
        
        for i, lon in enumerate(grid_lons):
            alpha = 0.4 if i % 3 == 0 else 0.2  # Major/minor grid
            linewidth = 0.8 if i % 3 == 0 else 0.4
            ax_main.axvline(lon, color='white', alpha=alpha, linewidth=linewidth, zorder=2)
        
        for i, lat in enumerate(grid_lats):
            alpha = 0.4 if i % 3 == 0 else 0.2
            linewidth = 0.8 if i % 3 == 0 else 0.4
            ax_main.axhline(lat, color='white', alpha=alpha, linewidth=linewidth, zorder=2)
    
    # === ADVANCED TEMPERATURE VISUALIZATION ===
    # Professional scientific colormap
    professional_colors = [
        '#2166ac',  # Deep blue (coolest)
        '#4393c3',  # Blue
        '#92c5de',  # Light blue
        '#d1e5f0',  # Very light blue
        '#f7f7f7',  # Near white
        '#fdbf6f',  # Light orange
        '#ff7f00',  # Orange
        '#e31a1c',  # Red
        '#800026'   # Dark red (hottest)
    ]
    
    professional_cmap = mcolors.LinearSegmentedColormap.from_list(
        'professional_thermal', professional_colors, N=512
    )
    
    # Ultra-high resolution contour levels
    n_levels = 100
    temp_levels = np.linspace(temp_min, temp_max, n_levels)
    
    # Main temperature surface with professional styling
    temp_surface = ax_main.contourf(
        lons, lats, temps,
        levels=temp_levels,
        cmap=professional_cmap,
        alpha=0.8,
        extend='both',
        antialiased=True,
        transform=projection,
        zorder=10
    )
    
    # Add professional contour lines
    contour_lines = ax_main.contour(
        lons, lats, temps,
        levels=temp_levels[::10],  # Every 10th level
        colors='white',
        alpha=0.6,
        linewidths=0.5,
        antialiased=True,
        transform=projection,
        zorder=12
    )
    
    # Add contour labels for key isotherms
    label_levels = temp_levels[::20]  # Every 20th level
    contour_labels = ax_main.clabel(contour_lines, label_levels, 
                                   inline=True, fontsize=9, fmt='%1.0f°C',
                                   colors='white', zorder=13)
    
    # === CITY BOUNDARIES OVERLAY ===
    if city_boundaries:
        print(f"   🗺️ Adding city administrative boundaries...")
        try:
            boundary_coords = extract_boundary_coordinates(city_boundaries)
            
            for i, (boundary_lons, boundary_lats) in enumerate(boundary_coords):
                if len(boundary_lons) > 2:  # Valid polygon
                    # Main boundary line
                    ax_main.plot(
                        boundary_lons, boundary_lats,
                        color='red', linewidth=3, 
                        linestyle='-', alpha=0.9,
                        transform=projection, zorder=20,
                        label='City Boundary' if i == 0 else ""
                    )
                    
                    # Add boundary highlight
                    ax_main.plot(
                        boundary_lons, boundary_lats,
                        color='white', linewidth=5, 
                        linestyle='-', alpha=0.6,
                        transform=projection, zorder=19
                    )
                    
                    # Optional: Add subtle fill
                    if i == 0:  # Only for the main boundary
                        ax_main.fill(
                            boundary_lons, boundary_lats,
                            color='red', alpha=0.1,
                            transform=projection, zorder=8
                        )
            
            print(f"   ✅ City boundaries added successfully")
            
        except Exception as e:
            print(f"   ⚠️ Error adding city boundaries: {e}")
    else:
        print(f"   ⚠️ No city boundaries available")
    
    # === PROFESSIONAL MARKERS AND ANNOTATIONS ===
    # City center with professional styling
    ax_main.plot(
        city_info['lon'], city_info['lat'],
        marker='*', markersize=45,
        color='gold', markeredgecolor='black',
        markeredgewidth=3, zorder=25,
        transform=projection
    )
    
    # Add city name annotation
    ax_main.annotate(
        city_name,
        xy=(city_info['lon'], city_info['lat']),
        xytext=(10, 10), textcoords='offset points',
        fontsize=14, fontweight='bold',
        color='black',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9, edgecolor='black'),
        zorder=26, transform=projection
    )
    
    # === OVERVIEW MAP ===
    # Country/region context
    overview_extent = [
        bounds[0] - 2, bounds[2] + 2,
        bounds[1] - 2, bounds[3] + 2
    ]
    ax_overview.set_extent(overview_extent, crs=projection)
    
    # Overview basemap
    ax_overview.add_feature(cfeature.LAND, alpha=0.9, color='#e8e8e8')
    ax_overview.add_feature(cfeature.OCEAN, alpha=0.9, color='#d6e8f5')
    ax_overview.add_feature(cfeature.BORDERS, alpha=0.8, color='#666666', linewidth=1)
    ax_overview.add_feature(cfeature.COASTLINE, alpha=0.8, color='#2c5aa0', linewidth=1)
    
    # Highlight study area
    study_area = Rectangle(
        (bounds[0], bounds[1]), 
        bounds[2] - bounds[0], 
        bounds[3] - bounds[1],
        linewidth=3, edgecolor='red', facecolor='red', alpha=0.3,
        transform=projection, zorder=20
    )
    ax_overview.add_patch(study_area)
    
    # Overview city marker
    ax_overview.plot(
        city_info['lon'], city_info['lat'],
        marker='o', markersize=8,
        color='red', markeredgecolor='black',
        markeredgewidth=1, zorder=25,
        transform=projection
    )
    
    # Overview title
    ax_overview.set_title('Study Area Location', fontsize=12, fontweight='bold', pad=10)
    
    # === PROFESSIONAL COLORBAR ===
    # Create custom colorbar axis
    cbar_ax = fig.add_axes([0.77, 0.25, 0.02, 0.5])  # [left, bottom, width, height]
    
    cbar = plt.colorbar(temp_surface, cax=cbar_ax, shrink=0.8)
    cbar.set_label(
        'Land Surface Temperature (°C)',
        fontsize=14, fontweight='bold',
        labelpad=20
    )
    
    # Professional colorbar ticks
    temp_range_span = temp_max - temp_min
    if temp_range_span > 15:
        tick_interval = 5
    elif temp_range_span > 10:
        tick_interval = 2
    else:
        tick_interval = 1
    
    cbar_ticks = np.arange(
        int(temp_min), 
        int(temp_max) + 1, 
        tick_interval
    )
    cbar.set_ticks(cbar_ticks)
    cbar.set_ticklabels([f'{temp:.0f}°' for temp in cbar_ticks])
    cbar.ax.tick_params(labelsize=12, colors='black')
    
    # === PROFESSIONAL TITLE AND METADATA ===
    analysis_period = temp_data['analysis_period']
    
    # Main title
    main_title = f'Multi-Year Summer Land Surface Temperature Analysis\n{city_name}, Uzbekistan ({analysis_period["start_year"]}-{analysis_period["end_year"]})'
    ax_title.text(0.5, 0.7, main_title, ha='center', va='center',
                 fontsize=20, fontweight='bold', transform=ax_title.transAxes)
    
    # Subtitle
    subtitle = f'Average summer (June-August) temperatures with {temp_data["years_span"]}-year temporal trend analysis'
    ax_title.text(0.5, 0.3, subtitle, ha='center', va='center',
                 fontsize=14, style='italic', color='#2c5aa0', transform=ax_title.transAxes)
    
    # === PROFESSIONAL GRID AND LABELS ===
    # Enhanced gridlines for main map
    gl = ax_main.gridlines(
        draw_labels=True, alpha=0.5,
        linestyle='-', linewidth=0.8,
        color='gray', zorder=5
    )
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {'size': 11, 'color': 'black', 'weight': 'bold'}
    gl.ylabel_style = {'size': 11, 'color': 'black', 'weight': 'bold'}
    
    # Coordinate labels
    ax_main.set_xlabel('Longitude (°E)', fontsize=13, fontweight='bold', labelpad=10)
    ax_main.set_ylabel('Latitude (°N)', fontsize=13, fontweight='bold', labelpad=10)
    
    # === PROFESSIONAL INFORMATION PANEL ===
    analysis_period = temp_data['analysis_period']
    trend_sig = temp_data['trend_significance']
    ci_lower, ci_upper = trend_sig['confidence_interval']
    
    # Multi-column layout for information
    info_text_left = (
        f'📊 DATA SPECIFICATIONS\n'
        f'• Satellite: Landsat 8/9 Collection 2 Level 2\n'
        f'• Temporal: Summer {analysis_period["start_year"]}-{analysis_period["end_year"]} ({temp_data["years_span"]} years)\n'
        f'• Spatial Resolution: {TARGET_RESOLUTION}m\n'
        f'• Valid Observations: {temp_data["n_valid"]:,}/{temp_data["total_points"]:,} points\n'
        f'• Cloud Cover: <{MAX_CLOUD_COVER}%\n'
        f'• Administrative Boundaries: {"Included" if city_boundaries else "Approximate"}'
    )
    
    info_text_center = (
        f'🌡️ TEMPERATURE STATISTICS\n'
        f'• Spatial Range: {temp_data["temp_range"][0]:.1f}°C - {temp_data["temp_range"][1]:.1f}°C\n'
        f'• Spatial Mean: {temp_data["temp_mean"]:.1f}°C ± {temp_data["temp_spatial_std"]:.1f}°C\n'
        f'• Temporal Variability: ±{temp_data["temp_temporal_std"]:.1f}°C (year-to-year)\n'
        f'• Temperature Range: {temp_data["temp_range"][1] - temp_data["temp_range"][0]:.1f}°C\n'
        f'• Hottest Areas: {temp_data["temp_range"][1]:.1f}°C\n'
        f'• Urban Heat Pattern: {"Detected" if temp_data["temp_range"][1] - temp_data["temp_range"][0] > 10 else "Moderate"}'
    )
    
    info_text_right = (
        f'📈 TREND ANALYSIS\n'
        f'• Temporal Trend: {temp_data["temp_trend"]:.3f}°C/year\n'
        f'• Statistical Significance: {trend_sig["significance_level"]}\n'
        f'• 95% Confidence Interval: [{ci_lower:.3f}, {ci_upper:.3f}] °C/year\n'
        f'• Total Change: {temp_data["temp_trend"] * temp_data["years_span"]:.2f}°C over {temp_data["years_span"]} years\n'
        f'• Analysis Method: Linear regression with significance testing\n'
        f'• Boundary Source: {"Administrative" if city_boundaries else "Geometric"}'
    )
    
    # Add information boxes
    ax_info.text(0.02, 0.5, info_text_left, ha='left', va='center',
                fontsize=10, transform=ax_info.transAxes,
                bbox=dict(boxstyle='round,pad=0.8', facecolor='lightblue', alpha=0.8, edgecolor='navy'))
    
    ax_info.text(0.35, 0.5, info_text_center, ha='left', va='center',
                fontsize=10, transform=ax_info.transAxes,
                bbox=dict(boxstyle='round,pad=0.8', facecolor='lightgreen', alpha=0.8, edgecolor='darkgreen'))
    
    ax_info.text(0.68, 0.5, info_text_right, ha='left', va='center',
                fontsize=10, transform=ax_info.transAxes,
                bbox=dict(boxstyle='round,pad=0.8', facecolor='lightyellow', alpha=0.8, edgecolor='orange'))
    
    # Add legend for map elements
    legend_elements = [
        mpatches.Patch(color='gold', label='City Center'),
    ]
    
    if city_boundaries:
        legend_elements.append(
            mpatches.Patch(color='red', label='City Administrative Boundary')
        )
    
    # Add temperature legend
    legend_elements.extend([
        mpatches.Patch(color='#2166ac', label=f'Cool Areas (~{temp_min:.0f}°C)'),
        mpatches.Patch(color='#800026', label=f'Hot Areas (~{temp_max:.0f}°C)')
    ])
    
    # Place legend on the map
    ax_main.legend(handles=legend_elements, loc='upper right', 
                  bbox_to_anchor=(0.98, 0.98), fontsize=11,
                  fancybox=True, shadow=True, ncol=1)
    
    # === PROFESSIONAL SCALE BAR ===
    scale_km = 5
    scale_deg = scale_km / 111.0
    scale_x = bounds[2] - (bounds[2] - bounds[0]) * 0.15
    scale_y = bounds[1] + (bounds[3] - bounds[1]) * 0.08
    
    # Professional scale bar with caps
    ax_main.plot(
        [scale_x - scale_deg/2, scale_x + scale_deg/2],
        [scale_y, scale_y],
        color='black', linewidth=6, zorder=30,
        transform=projection
    )
    
    # Scale bar caps
    cap_height = (bounds[3] - bounds[1]) * 0.005
    ax_main.plot([scale_x - scale_deg/2, scale_x - scale_deg/2],
                [scale_y - cap_height, scale_y + cap_height],
                color='black', linewidth=6, zorder=30, transform=projection)
    ax_main.plot([scale_x + scale_deg/2, scale_x + scale_deg/2],
                [scale_y - cap_height, scale_y + cap_height],
                color='black', linewidth=6, zorder=30, transform=projection)
    
    # Scale bar text
    ax_main.text(
        scale_x, scale_y + (bounds[3] - bounds[1]) * 0.025,
        f'{scale_km} km',
        ha='center', va='bottom',
        fontsize=12, fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9),
        zorder=30, transform=projection
    )
    
    # === NORTH ARROW ===
    arrow_x = bounds[2] - (bounds[2] - bounds[0]) * 0.08
    arrow_y = bounds[3] - (bounds[3] - bounds[1]) * 0.12
    
    ax_main.annotate('N', xy=(arrow_x, arrow_y), xytext=(arrow_x, arrow_y + 0.01),
                    arrowprops=dict(arrowstyle='->', lw=3, color='black'),
                    fontsize=16, fontweight='bold', ha='center',
                    transform=projection, zorder=30)
    
    # === PROFESSIONAL LAYOUT FINISHING ===
    # Set aspect ratios
    ax_main.set_aspect('equal', adjustable='box')
    ax_overview.set_aspect('equal', adjustable='box')
    
    # Remove overview ticks for cleaner look
    ax_overview.set_xticks([])
    ax_overview.set_yticks([])
    
    # Add professional border to main map
    for spine in ax_main.spines.values():
        spine.set_edgecolor('black')
        spine.set_linewidth(2)
    
    print("   ✅ Professional GIS map created with advanced cartographic design")
    
    return fig
    
    # Get data
    lons = temp_data['lons']
    lats = temp_data['lats']
    temps = temp_data['temperatures']
    bounds = temp_data['bounds']
    temp_min, temp_max = temp_data['temp_range']
    
    # Set precise extent
    extent_buffer = 0.005  # Small buffer for framing
    ax.set_extent([
        bounds[0] - extent_buffer, bounds[2] + extent_buffer,
        bounds[1] - extent_buffer, bounds[3] + extent_buffer
    ], crs=projection)
    
    # Add real basemap with street networks
    try:
        # OpenStreetMap tiles for street detail
        osm_tiles = OSM()
        ax.add_image(osm_tiles, 14, alpha=0.8)  # High zoom for street detail
        print("   ✅ Added detailed OpenStreetMap basemap with streets")
        
    except Exception as e:
        print(f"   ⚠️ OSM error: {e}, using cartographic features...")
        # Fallback to enhanced cartographic features
        ax.add_feature(cfeature.LAND, alpha=0.9, color='#f8f8f8')
        ax.add_feature(cfeature.OCEAN, alpha=0.9, color='#e6f3ff') 
        ax.add_feature(cfeature.RIVERS, alpha=0.7, color='#4da6ff', linewidth=1)
        ax.add_feature(cfeature.ROADS, alpha=0.5, color='#cccccc', linewidth=0.8)
        ax.add_feature(cfeature.BORDERS, alpha=0.8, color='#999999', linewidth=1)
        
        # Add street-like grid for urban feel
        grid_lons = np.linspace(bounds[0], bounds[2], 25)
        grid_lats = np.linspace(bounds[1], bounds[3], 25)
        
        for lon in grid_lons[::2]:
            ax.axvline(lon, color='white', alpha=0.3, linewidth=0.5, zorder=5)
        for lat in grid_lats[::2]:
            ax.axhline(lat, color='white', alpha=0.3, linewidth=0.5, zorder=5)
        
        print("   ✅ Added enhanced cartographic basemap with street simulation")
    
    # Create exact Tirana colormap
    tirana_exact_colors = [
        '#25589c',  # Dark blue (coolest - like 25°C)
        '#4b79bc',  # Medium blue
        '#7199dc',  # Light blue  
        '#96b9fc',  # Very light blue
        '#bcdaff',  # Pale blue
        '#e1f0ff',  # Almost white blue
        '#ffffff',  # Pure white (neutral ~27-28°C)
        '#fff5e6',  # Very light cream
        '#ffe0b3',  # Light peach
        '#ffcc80',  # Peach
        '#ffb84d',  # Light orange
        '#ffa31a',  # Orange (like 29°C)
        '#e68900',  # Dark orange
        '#cc7700',  # Red-orange
        '#b36600'   # Deep red-orange (hottest)
    ]
    
    # Create ultra-smooth colormap
    tirana_exact_cmap = mcolors.LinearSegmentedColormap.from_list(
        'tirana_exact', tirana_exact_colors, N=1024
    )
    
    # Ultra-high resolution contour levels for 3D smoothness
    n_levels = 80
    temp_levels = np.linspace(temp_min, temp_max, n_levels)
    
    # Main temperature surface with exact Tirana transparency
    temp_surface = ax.contourf(
        lons, lats, temps,
        levels=temp_levels,
        cmap=tirana_exact_cmap,
        alpha=0.75,  # Exact transparency like Tirana
        extend='both',
        antialiased=True,
        transform=projection
    )
    
    # Add very subtle white contour lines for 3D definition
    contour_lines = ax.contour(
        lons, lats, temps,
        levels=temp_levels[::8],  # Every 8th level
        colors='white',
        alpha=0.25,
        linewidths=0.3,
        antialiased=True,
        transform=projection
    )
    
    # City center marker exactly like Tirana
    ax.plot(
        city_info['lon'], city_info['lat'],
        marker='*', markersize=35,
        color='white', markeredgecolor='black',
        markeredgewidth=3, zorder=25,
        transform=projection
    )
    
    # Professional colorbar exactly like Tirana
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="2%", pad=0.1, axes_class=plt.Axes)
    
    cbar = plt.colorbar(temp_surface, cax=cax, shrink=0.9)
    cbar.set_label(
        'Ambient air temperature',
        fontsize=14, fontweight='bold',
        labelpad=15
    )
    
    # Colorbar ticks like Tirana (25°C, 27°C, 29°C)
    if temp_min <= 25 and temp_max >= 29:
        cbar_ticks = [25, 27, 29]
    else:
        # Adaptive ticks for our data
        tick_range = temp_max - temp_min
        if tick_range > 10:
            cbar_ticks = [
                int(temp_min + 1),
                int((temp_min + temp_max) / 2),
                int(temp_max - 1)
            ]
        else:
            cbar_ticks = [temp_min, (temp_min + temp_max) / 2, temp_max]
    
    cbar.set_ticks(cbar_ticks)
    cbar.set_ticklabels([f'{temp:.0f}°C' for temp in cbar_ticks])
    cbar.ax.tick_params(labelsize=12, colors='black')
    
    # Multi-year analysis title format
    analysis_period = temp_data['analysis_period']
    main_title = f'Multi-Year Summer Temperature Analysis ({analysis_period["start_year"]}-{analysis_period["end_year"]})\\n' \
                f'Relationship between Air Temperatures and Ground Cover in {city_name}, Uzbekistan'
    
    subtitle = f'A: Average summer ambient air temperature in {city_name}, Uzbekistan\\n' \
              f'({analysis_period["start_year"]}-{analysis_period["end_year"]}) with temporal trend analysis'
    
    # Set titles with exact positioning
    fig.suptitle(main_title, fontsize=18, fontweight='bold', y=0.95, x=0.5)
    ax.set_title(subtitle, fontsize=13, pad=25, loc='left', color='#1f4e79')
    
    # Coordinate labels
    ax.set_xlabel('Longitude (°E)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Latitude (°N)', fontsize=12, fontweight='bold')
    
    # Enhanced gridlines
    gl = ax.gridlines(
        draw_labels=True, alpha=0.3,
        linestyle='--', linewidth=0.5,
        color='gray', zorder=2
    )
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {'size': 10, 'color': 'black'}
    gl.ylabel_style = {'size': 10, 'color': 'black'}
    
    # Analysis boundary (dashed like Tirana)
    buffer_deg = city_info['buffer_km'] / 111.0
    center_lon, center_lat = city_info['lon'], city_info['lat']
    
    boundary_coords = [
        [center_lon - buffer_deg, center_lat - buffer_deg],
        [center_lon + buffer_deg, center_lat - buffer_deg],
        [center_lon + buffer_deg, center_lat + buffer_deg],
        [center_lon - buffer_deg, center_lat + buffer_deg],
        [center_lon - buffer_deg, center_lat - buffer_deg]
    ]
    
    boundary_lons = [coord[0] for coord in boundary_coords]
    boundary_lats = [coord[1] for coord in boundary_coords]
    
    ax.plot(
        boundary_lons, boundary_lats,
        color='navy', linestyle='--',
        linewidth=2.5, alpha=0.8,
        transform=projection, zorder=20
    )
    
    # Professional technical information with multi-year statistics
    analysis_period = temp_data['analysis_period']
    trend_sig = temp_data['trend_significance']
    ci_lower, ci_upper = trend_sig['confidence_interval']
    
    info_text = (
        f'Data: Landsat 8/9 Thermal (Summer {analysis_period["start_year"]}-{analysis_period["end_year"]})\\n'
        f'Resolution: {TARGET_RESOLUTION}m | Multi-year Average\\n'
        f'Valid Points: {temp_data["n_valid"]:,}/{temp_data["total_points"]:,}\\n'
        f'Spatial Range: {temp_data["temp_range"][0]:.1f}°C - {temp_data["temp_range"][1]:.1f}°C\\n'
        f'Mean ± SD: {temp_data["temp_mean"]:.1f}°C ± {temp_data["temp_spatial_std"]:.1f}°C\\n'
        f'Temporal Trend: {temp_data["temp_trend"]:.3f}°C/year ({trend_sig["significance_level"]})\\n'
        f'95% CI: [{ci_lower:.3f}, {ci_upper:.3f}] °C/year\\n'
        f'Total Change: {temp_data["temp_trend"] * temp_data["years_span"]:.2f}°C over {temp_data["years_span"]} years'
    )
    
    ax.text(
        0.02, 0.02, info_text,
        transform=ax.transAxes,
        fontsize=10, verticalalignment='bottom',
        bbox=dict(
            boxstyle='round,pad=0.6',
            facecolor='white',
            alpha=0.95,
            edgecolor='darkblue',
            linewidth=1
        ),
        zorder=30
    )
    
    # Professional scale bar
    scale_km = 5
    scale_deg = scale_km / 111.0
    scale_x = bounds[2] - (bounds[2] - bounds[0]) * 0.12
    scale_y = bounds[1] + (bounds[3] - bounds[1]) * 0.05
    
    # Scale bar with caps
    ax.plot(
        [scale_x - scale_deg/2, scale_x + scale_deg/2],
        [scale_y, scale_y],
        color='black', linewidth=5, zorder=30,
        transform=projection
    )
    
    # Scale bar text
    ax.text(
        scale_x, scale_y + (bounds[3] - bounds[1]) * 0.02,
        f'{scale_km} km',
        ha='center', va='bottom',
        fontsize=11, fontweight='bold',
        zorder=30, transform=projection
    )
    
    # Exact aspect ratio
    ax.set_aspect('equal', adjustable='box')
    
    # Final layout
    plt.tight_layout()
    
    return fig

def main():
    """Main execution function for multi-year temperature analysis"""
    print("🗺️ PROFESSIONAL GIS TEMPERATURE MAPPING WITH ADVANCED CARTOGRAPHIC DESIGN")
    print("=" * 85)
    print(f"📅 Analysis Period: {ANALYSIS_START_YEAR}-{ANALYSIS_END_YEAR} ({ANALYSIS_END_YEAR - ANALYSIS_START_YEAR + 1} years)")
    print(f"🎯 High Resolution: {TARGET_RESOLUTION}m")
    print(f"🏙️ Cities: {', '.join(CITIES.keys())}")
    print(f"🌡️ Season: Summer (months {WARM_SEASON_MONTHS})")
    print(f"� Statistical Analysis: Mean, Std Dev, Temporal Trends")
    print(f"�🗺️ Basemap: Real OpenStreetMap with street networks")
    print(f"🎨 Style: Scientific visualization with trend analysis")
    print("=" * 80)
    
    # Initialize Google Earth Engine
    if not authenticate_gee():
        return
    
    # Create output directory
    output_dir = Path('professional_gis_maps')
    output_dir.mkdir(exist_ok=True)
    
    # Analysis period configuration
    analysis_period = {
        'start_year': ANALYSIS_START_YEAR,
        'end_year': ANALYSIS_END_YEAR,
        'months': WARM_SEASON_MONTHS
    }
    
    # Track overall statistics
    successful_cities = []
    failed_cities = []
    temperature_summary = {}
    
    print(f"\n🗺️ Processing {len(CITIES)} cities across Uzbekistan...")
    
    # Process each city
    for i, (city_name, city_info) in enumerate(CITIES.items(), 1):
        print(f"\n{'='*60}")
        print(f"🌍 [{i}/{len(CITIES)}] Processing {city_name}")
        print(f"   📍 {city_info['description']}")
        print(f"   📍 Location: {city_info['lat']:.4f}°N, {city_info['lon']:.4f}°E")
        print(f"   📊 Buffer zone: {city_info['buffer_km']} km")
        
        try:
            # Create analysis region
            center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
            region = center.buffer(city_info['buffer_km'] * 1000)
            
            # Get multi-year satellite data composite
            composite = get_working_landsat_composite(
                region, ANALYSIS_START_YEAR, ANALYSIS_END_YEAR, WARM_SEASON_MONTHS
            )
            
            if composite is None:
                print(f"   ❌ No satellite data available for {city_name}")
                failed_cities.append(city_name)
                continue
            
            # Sample temperature for statistical analysis
            print(f"   🔄 Processing temperature analysis...")
            temp_data = sample_temperature_for_3d(composite, region, city_name, analysis_period)
            
            if temp_data is None:
                print(f"   ❌ Failed to sample temperature data for {city_name}")
                failed_cities.append(city_name)
                continue
            
            # Get city administrative boundaries
            city_boundaries = get_city_boundaries(city_name, city_info)
            
            # Store temperature summary
            temperature_summary[city_name] = {
                'mean_temp': temp_data['temp_mean'],
                'spatial_std': temp_data['temp_spatial_std'],
                'temp_trend': temp_data['temp_trend'],
                'trend_significant': temp_data['trend_significance']['is_significant'],
                'temp_range': temp_data['temp_range'],
                'has_boundaries': city_boundaries is not None
            }
            
            # Create professional GIS visualization with city boundaries
            print(f"   🎨 Creating professional GIS map with administrative boundaries...")
            fig = create_professional_gis_map(temp_data, city_name, city_info, city_boundaries)
            
            # Save professional map
            output_path = output_dir / f'{city_name.lower()}_professional_gis_analysis_{ANALYSIS_START_YEAR}_{ANALYSIS_END_YEAR}.png'
            fig.savefig(
                str(output_path),
                dpi=300,
                bbox_inches='tight',
                facecolor='white',
                edgecolor='none',
                format='png',
                pad_inches=0.1
            )
            
            print(f"   ✅ Professional GIS map saved: {output_path.name}")
            
            # Detailed scientific assessment
            trend_sig = temp_data['trend_significance']
            if trend_sig['is_significant']:
                print(f"   📈 SIGNIFICANT trend: {temp_data['temp_trend']:.3f}°C/year")
                print(f"   🔥 Total change: {temp_data['temp_trend'] * temp_data['years_span']:.2f}°C over {temp_data['years_span']} years")
            else:
                print(f"   📊 No significant trend: {temp_data['temp_trend']:.3f}°C/year (natural variability)")
            
            successful_cities.append(city_name)
            plt.close(fig)
            
            # Brief pause to avoid overwhelming the system
            time.sleep(0.5)
            
        except Exception as e:
            print(f"   ❌ Error processing {city_name}: {e}")
            failed_cities.append(city_name)
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\\n🎉 COMPREHENSIVE UZBEKISTAN TEMPERATURE ANALYSIS COMPLETE!")
    print(f"📁 Analysis results saved in: {output_dir.absolute()}")
    print(f"✅ Successfully processed: {len(successful_cities)}/{len(CITIES)} cities")
    
    if successful_cities:
        print(f"\n📊 TEMPERATURE SUMMARY ACROSS UZBEKISTAN:")
        
        # Sort cities by mean temperature
        sorted_cities = sorted(temperature_summary.items(), 
                             key=lambda x: x[1]['mean_temp'], reverse=True)
        
        print(f"   � HOTTEST CITIES (Average Summer Temperature):")
        for i, (city, data) in enumerate(sorted_cities[:5], 1):
            trend_indicator = "📈" if data['trend_significant'] else "📊"
            print(f"      {i}. {city}: {data['mean_temp']:.1f}°C ± {data['spatial_std']:.1f}°C {trend_indicator}")
        
        print(f"\n   ❄️ COOLEST CITIES:")
        for i, (city, data) in enumerate(sorted_cities[-3:], 1):
            trend_indicator = "📈" if data['trend_significant'] else "📊"
            print(f"      {i}. {city}: {data['mean_temp']:.1f}°C ± {data['spatial_std']:.1f}°C {trend_indicator}")
        
        # Cities with significant trends
        significant_trends = [(city, data) for city, data in temperature_summary.items() 
                            if data['trend_significant']]
        
        if significant_trends:
            print(f"\n   📈 CITIES WITH SIGNIFICANT WARMING TRENDS:")
            for city, data in significant_trends:
                print(f"      • {city}: {data['temp_trend']:.3f}°C/year")
        else:
            print(f"\n   📊 NO CITIES SHOW STATISTICALLY SIGNIFICANT TRENDS")
            print(f"      Natural variability dominates climate signal")
    
    if failed_cities:
        print(f"\n❌ Failed to process: {', '.join(failed_cities)}")
    
    print(f"\n🌡️ Period analyzed: {ANALYSIS_START_YEAR}-{ANALYSIS_END_YEAR} ({ANALYSIS_END_YEAR - ANALYSIS_START_YEAR + 1} years)")
    print(f"📈 Methodology: Multi-year statistical analysis with trend detection")
    print(f"🎨 Output: Professional GIS maps with scientific rigor")
    print(f"🗺️ Coverage: Complete Uzbekistan regional analysis")

if __name__ == "__main__":
    main()
