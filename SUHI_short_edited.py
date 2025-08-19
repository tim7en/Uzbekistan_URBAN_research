"""
COMPREHENSIVE SURFACE URBAN HEAT ISLAND (SUHI) ANALYSIS FOR UZBEKISTAN CITIES
================================================================================
This script performs a multi-source remote sensing analysis of urban heat islands
across major Uzbekistan cities using Google Earth Engine.

Analysis Components:
1. Multi-dataset urban classification with accuracy assessment 
2. High-resolution temperature analysis from multiple sensors
3. Vegetation index calculation from Landsat 8/9
4. Pixel-by-pixel SUHI computation
5. Urban expansion impact assessment
6. Comprehensive error reporting
"""

# ================================================================================
# SECTION 1: IMPORTS AND CONFIGURATION
# ================================================================================

import ee
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
import warnings
import time
import json
from typing import Dict, List, Tuple, Optional, Any, Union
import os
import glob
try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("⚠️ SciPy not available - trend analysis will be limited")

warnings.filterwarnings('ignore')

# ================================================================================
# SECTION 2: STUDY AREA DEFINITION AND CONSTANTS
# ================================================================================
class RateLimiter:
    """Simple rate limiter to avoid GEE quota issues"""
    def __init__(self, min_interval=2):
        self.min_interval = min_interval
        self.last_call = 0
    
    def wait(self):
        current = time.time()
        elapsed = current - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()

# Create global rate limiter
rate_limiter = RateLimiter(min_interval=3)  # 3 seconds between heavy operations

# Define all major Uzbekistan cities with their coordinates and analysis buffers
UZBEKISTAN_CITIES = {
    # National capital
    "Tashkent":   {"lat": 41.2995, "lon": 69.2401, "buffer_m": 15000, "type": "capital"},
    
    # Republic capital
    "Nukus":      {"lat": 42.4731, "lon": 59.6103, "buffer_m": 10000, "type": "republic_capital"},
    
    # Regional capitals and major cities
    "Andijan":    {"lat": 40.7821, "lon": 72.3442, "buffer_m": 12000, "type": "regional_capital"},
    "Bukhara":    {"lat": 39.7748, "lon": 64.4286, "buffer_m": 10000, "type": "regional_capital"},
    "Samarkand":  {"lat": 39.6542, "lon": 66.9597, "buffer_m": 12000, "type": "regional_capital"},
    "Namangan":   {"lat": 40.9983, "lon": 71.6726, "buffer_m": 12000, "type": "regional_capital"},
    "Jizzakh":    {"lat": 40.1158, "lon": 67.8422, "buffer_m": 8000,  "type": "regional_capital"},
    "Qarshi":     {"lat": 38.8606, "lon": 65.7887, "buffer_m": 8000,  "type": "regional_capital"},
    "Navoiy":     {"lat": 40.1030, "lon": 65.3686, "buffer_m": 10000, "type": "regional_capital"},
    "Termez":     {"lat": 37.2242, "lon": 67.2783, "buffer_m": 8000,  "type": "regional_capital"},
    "Gulistan":   {"lat": 40.4910, "lon": 68.7810, "buffer_m": 8000,  "type": "regional_capital"},
    "Nurafshon":  {"lat": 41.0167, "lon": 69.3417, "buffer_m": 8000,  "type": "city"},
    "Fergana":    {"lat": 40.3842, "lon": 71.7843, "buffer_m": 12000, "type": "regional_capital"},
    "Urgench":    {"lat": 41.5506, "lon": 60.6317, "buffer_m": 10000, "type": "regional_capital"},
}

# Analysis parameters
ANALYSIS_CONFIG = {
    "years": list(range(2016, 2024)),  # 2016-2024
    "warm_months": [6, 7, 8],  # June-August for peak SUHI
    "target_resolution_m": 100,  # Target spatial resolution in meters
    "esri_weight": 0.5,  # ESRI classification weight (50%)
    "rural_buffer_km": 25,  # Rural reference ring distance
    "min_urban_pixels": 10,  # Minimum pixels for valid urban area
    "min_rural_pixels": 25,  # Minimum pixels for valid rural area
    "cloud_threshold": 20,  # Maximum cloud cover percentage
    "water_occurrence_threshold": 25,  # JRC water occurrence threshold
}

# Dataset IDs and configurations  
DATASETS = {
    "esri_lulc": "projects/sat-io/open-datasets/landcover/ESRI_Global-LULC_10m_TS",
    "dynamic_world": "GOOGLE/DYNAMICWORLD/V1",
    "ghsl": "JRC/GHSL/P2023A/GHS_BUILT_S/2020",
    "esa_worldcover": "ESA/WorldCover/v200/2021",
    "modis_lc": "MODIS/061/MCD12Q1",
    "modis_lst": "MODIS/061/MOD11A2",
    "landsat8": "LANDSAT/LC08/C02/T1_L2",
    "landsat9": "LANDSAT/LC09/C02/T1_L2",
    "aster": "ASTER/AST_L1T_003",
    "water": "JRC/GSW1_4/GlobalSurfaceWater",
}

# Google Earth Engine computation limits
GEE_CONFIG = {
    "max_pixels": 5e8,  # Maximum pixels for reduceRegion operations
    "scale": 10,        # Default scale for high-resolution data (ESRI)
    "scale_modis": 1000, # Scale for MODIS data
    "scale_landsat": 30, # Scale for Landsat data
    "best_effort": True, # Use bestEffort for large computations
}

# ESRI Landcover Classification Classes
ESRI_CLASSES = {
    1: 'Water',
    2: 'Trees',
    4: 'Flooded_Vegetation',
    5: 'Crops',
    7: 'Built_Area',
    8: 'Bare_Ground',
    9: 'Snow_Ice',
    10: 'Clouds',
    11: 'Rangeland'
}

def get_optimal_scale_for_city(city_name: str, analysis_phase: str = "default") -> Dict[str, Union[int, float]]:
    """
    Get optimal processing scales based on city size and analysis phase to avoid memory issues.
    
    Args:
        city_name: Name of the city
        analysis_phase: Analysis phase - "default", "detailed_validation", "fallback"
        
    Returns:
        Dictionary with optimal scales for different datasets
    """
    city_info = UZBEKISTAN_CITIES[city_name]
    buffer_m = city_info['buffer_m']
    
    # Base scales depending on analysis phase
    if analysis_phase == "detailed_validation":
        # Use coarser resolution for detailed validation to avoid memory issues
        if buffer_m >= 15000:  # Large cities like Tashkent
            return {
                'scale': 200,  # 200m for landcover classifications
                'scale_modis': 1000,
                'scale_landsat': 200,  # 200m for Landsat
                'tileScale': 16,
                'maxPixels': 5e7
            }
        elif buffer_m >= 12000:  # Medium-large cities
            return {
                'scale': 200,  # Also use 200m for medium cities
                'scale_modis': 1000,
                'scale_landsat': 200,
                'tileScale': 16,
                'maxPixels': 5e7
            }
        else:  # Smaller cities - still need aggressive scaling
            return {
                'scale': 150,  # 150m for smaller cities
                'scale_modis': 1000,
                'scale_landsat': 150,
                'tileScale': 8,
                'maxPixels': 1e8
            }
    
    elif analysis_phase == "fallback":
        # Ultra-conservative settings for fallback
        return {
            'scale': 500,  # 500m for extreme fallback
            'scale_modis': 2000,  # Even coarser MODIS
            'scale_landsat': 500,
            'tileScale': 32,
            'maxPixels': 1e7
        }
    
    else:  # Default phase (Phases 1 & 2)
        # Larger cities need coarser resolution to avoid memory issues
        if buffer_m >= 15000:  # Large cities like Tashkent
            return {
                'scale': 30,  # Use 30m instead of 10m for classifications
                'scale_modis': 1000,
                'scale_landsat': 60,  # Double Landsat resolution
                'tileScale': 8,
                'maxPixels': 1e8
            }
        elif buffer_m >= 12000:  # Medium-large cities
            return {
                'scale': 20,
                'scale_modis': 1000,
                'scale_landsat': 30,
                'tileScale': 4,
                'maxPixels': 5e8
            }
        else:  # Smaller cities
            return {
                'scale': 10,
                'scale_modis': 1000,
                'scale_landsat': 30,
                'tileScale': 2,
                'maxPixels': 1e9
            }

def test_dataset_availability() -> Dict[str, bool]:
    """
    Test availability of key datasets before running analysis.
    
    Returns:
        Dictionary of dataset availability status
    """
    availability = {}
    
    print("🔍 Testing dataset availability...")
    
    # Test ESRI dataset specifically
    try:
        esri_collection = ee.ImageCollection(DATASETS["esri_lulc"])
        size = esri_collection.size().getInfo()
        availability['esri_lulc'] = size > 0
        print(f"   📊 ESRI Global LULC: {size} images available")
        
        # Test specific years
        for year in [2017, 2020, 2024]:
            try:
                start = ee.Date.fromYMD(year, 1, 1)
                end   = ee.Date.fromYMD(year, 12, 31)
                year_size = esri_collection.filterDate(start, end).size().getInfo()
                print(f"      {year}: {year_size} images")
            except Exception as e:
                print(f"      {year}: Error - {e}")
                
    except Exception as e:
        availability['esri_lulc'] = False
        print(f"   ❌ ESRI Global LULC: {e}")
    
    # Test other key datasets
    test_datasets = ['modis_lst', 'landsat8', 'dynamic_world']
    
    for name in test_datasets:
        try:
            if name == 'modis_lst':
                collection = ee.ImageCollection(DATASETS[name]).limit(1)
            elif name == 'landsat8':
                collection = ee.ImageCollection(DATASETS[name]).limit(1)
            elif name == 'dynamic_world':
                collection = ee.ImageCollection(DATASETS[name]).limit(1)
            
            size = collection.size().getInfo()
            availability[name] = size > 0
            print(f"   📊 {name}: {'✅' if size > 0 else '❌'}")
            
        except Exception as e:
            availability[name] = False
            print(f"   ❌ {name}: {e}")
    
    return availability

# ================================================================================
# SECTION 3: INITIALIZATION AND SETUP
# ================================================================================

def initialize_gee(project_id: str = 'ee-sabitovty') -> bool:
    """
    Initialize Google Earth Engine with specified project.
    
    Args:
        project_id: GEE project ID
        
    Returns:
        Success status
    """
    try:
        print("🔑 Initializing Google Earth Engine...")
        
        # Try to authenticate first
        try:
            ee.Authenticate()
            print("   ✅ Authentication successful")
        except Exception as auth_error:
            print(f"   ⚠️ Authentication skipped: {auth_error}")
        
        # Initialize with project
        ee.Initialize(project=project_id)
        
        # Test the connection
        test = ee.Image(1).getInfo()
        
        print("✅ GEE initialized successfully!")
        return True
        
    except Exception as e:
        print(f"❌ GEE initialization failed: {e}")
        print("   Try running: ee.Authenticate() in a Python shell first")
        return False

def create_output_directories() -> Dict[str, Path]:
    try:
        base_root = Path(__file__).parent
    except NameError:
        base_root = Path.cwd()
    base_dir = base_root / "suhi_analysis_output"
    sub = ["data","classification","temperature","vegetation","visualizations","reports","error_analysis"]
    dirs = {'base': base_dir, **{k: base_dir / k for k in sub}}
    for p in dirs.values(): p.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output directories created: {base_dir}")
    return dirs

# ================================================================================
# SECTION 4: URBAN CLASSIFICATION LOADING AND ACCURACY ASSESSMENT
# ================================================================================

def load_esri_classification(year: int, geometry: ee.Geometry) -> ee.Image:
    """
    Load ESRI Global Land Use Land Cover classification for specified year.
    ESRI provides annual data from 2017-2024, allowing year-specific analysis.
    
    Args:
        year: Target year
        geometry: Area of interest
        
    Returns:
        ESRI classification image or None if not available
    """
    try:
        # Use the correct ESRI dataset path
        esri_lulc_ts = ee.ImageCollection("projects/sat-io/open-datasets/landcover/ESRI_Global-LULC_10m_TS")
        
        # ESRI provides annual data 2017-2024
        if year < 2017:
            print(f"   ⚠️ Year {year} predates ESRI data, using 2017")
            year = 2017
        elif year > 2024:
            print(f"   ⚠️ Year {year} beyond ESRI data, using 2024")
            year = 2024
        
        # Method 1: Filter by date range (most reliable, following working reference)
        try:
            start_date = ee.Date.fromYMD(year, 1, 1)
            end_date = ee.Date.fromYMD(year, 12, 31)
            
            # Filter by date and create composite
            year_composite = (esri_lulc_ts
                             .filterDate(start_date, end_date)
                             .filterBounds(geometry)
                             .mosaic())  # Use mosaic() like in working reference
            
            # Check if we got any data
            pixel_count = year_composite.select([0]).reduceRegion(
                reducer=ee.Reducer.count(),
                geometry=geometry,
                scale=100,
                maxPixels=1e6
            )
            
            count = pixel_count.getInfo()
            if count and list(count.values())[0] > 0:
                # The ESRI data has values 1-11, clip to geometry
                clipped_image = year_composite.clip(geometry)
                
                print(f"   ✅ ESRI {year} loaded successfully (Method 1)")
                return clipped_image
                
        except Exception as method1_error:
            print(f"   ⚠️ Method 1 failed: {method1_error}")
        
        # Method 2: Filter by year property
        try:
            year_collection = esri_lulc_ts.filter(ee.Filter.eq('year', year))
            size = year_collection.size().getInfo()
            
            if size > 0:
                year_image = year_collection.first()
                clipped_image = year_image.clip(geometry)
                
                print(f"   ✅ ESRI {year} loaded successfully (Method 2)")
                return clipped_image
                    
        except Exception as method2_error:
            print(f"   ⚠️ Method 2 failed: {method2_error}")
        
        # Method 3: Get the latest available image
        try:
            latest_image = esri_lulc_ts.sort('system:time_start', False).first()
            clipped_image = latest_image.clip(geometry)
            
            print(f"   ✅ ESRI latest image loaded as fallback for {year} (Method 3)")
            return clipped_image
                
        except Exception as method3_error:
            print(f"   ⚠️ Method 3 failed: {method3_error}")
        
        print(f"   ❌ No ESRI data found for year {year}")
        return None
        
    except Exception as e:
        print(f"   ❌ Error loading ESRI classification for year {year}: {e}")
        return None


def load_all_classifications(year: int, geometry: ee.Geometry, 
                           start_date: str, end_date: str, 
                           optimal_scales: Optional[Dict[str, Union[int, float]]] = None) -> Dict[str, ee.Image]:
    """
    Load all available urban classification datasets.
    
    Args:
        year: Target year
        geometry: Area of interest
        start_date: Start date for temporal filtering
        end_date: End date for temporal filtering
        optimal_scales: Optional scaling parameters for memory optimization
        
    Returns:
        Dictionary of classification images
    """
    if optimal_scales is None:
        optimal_scales = {'scale': GEE_CONFIG['scale'], 'maxPixels': GEE_CONFIG['max_pixels']}
    
    scale = int(optimal_scales.get('scale', GEE_CONFIG['scale']) or GEE_CONFIG['scale'])
    max_pixels = optimal_scales.get('maxPixels', GEE_CONFIG['max_pixels']) or GEE_CONFIG['max_pixels']
    
    classifications = {}
    
    # 1. ESRI Global LULC (10m) - Primary classification
    try:
        esri = load_esri_classification(year, geometry)
        if esri is not None:
            # Resample to target scale if different from native resolution
            if scale > 10:
                esri_resampled = esri.reproject(
                    crs='EPSG:4326',
                    scale=scale
                ).eq(7).rename('esri_built')
                print(f"   ✅ ESRI classification loaded (resampled to {scale}m)")
            else:
                esri_resampled = esri.eq(7).rename('esri_built')
                print("   ✅ ESRI classification loaded")
            classifications['esri'] = esri_resampled
    except Exception as e:
        print(f"   ⚠️ ESRI unavailable: {e}")
    
    # 2. Dynamic World (10m) - Built probability
    try:
        dw = (ee.ImageCollection(DATASETS["dynamic_world"])
              .filterDate(start_date, end_date)
              .filterBounds(geometry)
              .select('built')
              .median())
        
        # Resample if needed
        if scale > 10:
            dw_resampled = dw.reproject(crs='EPSG:4326', scale=scale).rename('dw_built')
            print(f"   ✅ Dynamic World loaded (resampled to {scale}m)")
        else:
            dw_resampled = dw.rename('dw_built')
            print("   ✅ Dynamic World loaded")
        classifications['dynamic_world'] = dw_resampled
    except Exception as e:
        print(f"   ⚠️ Dynamic World unavailable: {e}")
    
    # 3. Global Human Settlement Layer (10m)
    try:
        ghsl = ee.Image(DATASETS["ghsl"]).select('built_surface')
        # Normalize to 0-1 range and resample if needed
        if scale > 10:
            ghsl_resampled = (ghsl.divide(100)
                            .reproject(crs='EPSG:4326', scale=scale)
                            .rename('ghsl_built')
                            .clip(geometry))
            print(f"   ✅ GHSL loaded (resampled to {scale}m)")
        else:
            ghsl_resampled = ghsl.divide(100).rename('ghsl_built').clip(geometry)
            print("   ✅ GHSL loaded")
        classifications['ghsl'] = ghsl_resampled
    except Exception as e:
        print(f"   ⚠️ GHSL unavailable: {e}")
    
    # 4. ESA WorldCover (10m)
    try:
        esa = ee.Image(DATASETS["esa_worldcover"]).select('Map')
        # Built-up class is 50, resample if needed
        if scale > 10:
            esa_resampled = (esa.eq(50)
                           .reproject(crs='EPSG:4326', scale=scale)
                           .rename('esa_built')
                           .clip(geometry))
            print(f"   ✅ ESA WorldCover loaded (resampled to {scale}m)")
        else:
            esa_resampled = esa.eq(50).rename('esa_built').clip(geometry)
            print("   ✅ ESA WorldCover loaded")
        classifications['esa'] = esa_resampled
    except Exception as e:
        print(f"   ⚠️ ESA WorldCover unavailable: {e}")
    
    # 5. MODIS Land Cover (500m) - Coarse resolution fallback
    try:
        modis_lc = (ee.ImageCollection(DATASETS["modis_lc"])
                   .filterDate(f'{year}-01-01', f'{year+1}-01-01')
                   .first()
                   .select('LC_Type1'))
        # Urban class is 13, already coarse so no need to resample further
        classifications['modis_lc'] = modis_lc.eq(13).rename('modis_urban').clip(geometry)
        print("   ✅ MODIS Land Cover loaded")
    except Exception as e:
        print(f"   ⚠️ MODIS Land Cover unavailable: {e}")
    
    return classifications

def assess_classification_accuracy(classifications: Dict[str, ee.Image], 
                                  geometry: ee.Geometry) -> ee.Dictionary:
    """
    Assess agreement between different classification datasets.
    
    Args:
        classifications: Dictionary of classification images
        geometry: Area of interest
        
    Returns:
        Accuracy metrics as ee.Dictionary
    """
    if len(classifications) < 2:
        return ee.Dictionary({'accuracy_assessment': 'Insufficient data'})
    
    # Use ESRI as reference if available
    if 'esri' in classifications:
        reference = classifications['esri']
    else:
        # Use consensus of available classifications
        # Handle potential issues with ee.Image.cat()
        classification_list = list(classifications.values())
        if len(classification_list) == 1:
            reference = classification_list[0]
        else:
            try:
                stack = ee.Image.cat(classification_list)
                reference = stack.reduce(ee.Reducer.mode())
            except Exception:
                # Fallback to first classification if cat fails
                reference = classification_list[0]
    
    # Calculate agreement metrics
    metrics = {}
    for name, classification in classifications.items():
        if name != 'esri':
            try:
                # Calculate confusion matrix elements
                agreement = classification.eq(reference)
                metrics[f'{name}_agreement'] = agreement.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=geometry,
                    scale=GEE_CONFIG['scale'],
                    maxPixels=GEE_CONFIG['max_pixels'],
                    bestEffort=GEE_CONFIG['best_effort']
                )
            except Exception as e:
                print(f"     ⚠️ Error calculating agreement for {name}: {e}")
                metrics[f'{name}_agreement'] = ee.Dictionary({'error': str(e)})
    
    return ee.Dictionary(metrics)

# ================================================================================
# SECTION 5: CREATE URBAN AND RURAL BUFFERS
# ================================================================================

def create_analysis_zones(city_info: Dict, esri_urban: ee.Image = None) -> Dict[str, ee.Geometry]:
    """
    Create urban core and rural reference zones for a city.
    
    Args:
        city_info: City configuration dictionary
        esri_urban: Optional ESRI urban classification for refinement
        
    Returns:
        Dictionary with urban_core and rural_ring geometries
    """
    # Create center point
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    
    # Urban core zone
    urban_buffer = center.buffer(city_info['buffer_m'])
    
    # Rural reference ring
    rural_outer = center.buffer(city_info['buffer_m'] + ANALYSIS_CONFIG['rural_buffer_km'] * 1000)
    rural_ring = rural_outer.difference(urban_buffer)
    
    # Apply small erosion to avoid edge effects
    erosion_distance = 100  # meters
    urban_core = urban_buffer.buffer(-erosion_distance)
    rural_ring_clean = rural_ring.buffer(-erosion_distance)
    
    zones = {
        'urban_core': urban_core,
        'rural_ring': rural_ring_clean,
        'full_extent': rural_outer
    }
    
    return zones

# ================================================================================
# SECTION 6: TEMPERATURE DATA LOADING (MODIS, LANDSAT, ASTER)
# ================================================================================

def load_modis_lst(start_date: str, end_date: str, geometry: ee.Geometry) -> ee.Image:
    col = (ee.ImageCollection(DATASETS["modis_lst"])
           .filterDate(start_date, end_date)
           .filterBounds(geometry)
           .filter(ee.Filter.calendarRange(ANALYSIS_CONFIG['warm_months'][0],
                                           ANALYSIS_CONFIG['warm_months'][-1], 'month')))
    comp = col.median()
    
    # Get dynamic band names
    band_names = comp.bandNames().getInfo()
    print(f"     📊 Available MODIS LST bands: {band_names}")
    
    # Find day and night LST bands
    day_bands = [b for b in band_names if 'Day' in b and 'LST' in b]
    night_bands = [b for b in band_names if 'Night' in b and 'LST' in b]
    
    if day_bands and night_bands:
        lst_day = comp.select(day_bands[0]).multiply(0.02).subtract(273.15).rename('LST_Day_MODIS').clamp(-20, 60)
        lst_night = comp.select(night_bands[0]).multiply(0.02).subtract(273.15).rename('LST_Night_MODIS').clamp(-20, 50)
        return ee.Image.cat([lst_day, lst_night]).clip(geometry)
    else:
        print(f"     ⚠️ Could not find Day/Night LST bands in: {band_names}")
        return None


def load_landsat_thermal(start_date: str, end_date: str, geometry: ee.Geometry) -> ee.Image:
    def proc(img):
        qa = img.select('QA_PIXEL')
        mask = (qa.bitwiseAnd(1<<3).eq(0)    # cloud
                .And(qa.bitwiseAnd(1<<4).eq(0))  # shadow
                .And(qa.bitwiseAnd(1<<5).eq(0))  # snow
                .And(qa.bitwiseAnd(1<<2).eq(0))) # cirrus
        st = img.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('LST_Landsat').clamp(-20, 60)
        return st.updateMask(mask)
    l8 = ee.ImageCollection(DATASETS["landsat8"])
    l9 = ee.ImageCollection(DATASETS["landsat9"])
    col = (l8.merge(l9).filterDate(start_date, end_date).filterBounds(geometry)
           .filter(ee.Filter.lt('CLOUD_COVER', ANALYSIS_CONFIG['cloud_threshold'])).map(proc))
    return col.median().clip(geometry)


def load_aster_lst(start_date: str, end_date: str, geometry: ee.Geometry) -> ee.Image:
    """
    Load and process ASTER thermal data.
    
    Args:
        start_date: Start date
        end_date: End date
        geometry: Area of interest
        
    Returns:
        ASTER LST image
    """
    def calculate_aster_lst(image):
        """Calculate LST from ASTER thermal bands."""
        # Thermal infrared bands
        b13 = image.select('B13')  # 10.25-10.95 μm
        b14 = image.select('B14')  # 10.95-11.65 μm
        
        # Simple split-window algorithm
        lst = (b13.add(b14)
               .divide(2)
               .multiply(0.00862)  # Conversion factor
               .add(0.56)
               .subtract(273.15)
               .rename('LST_ASTER')
               .clamp(-20, 60))
        
        return lst
    
    collection = (ee.ImageCollection(DATASETS["aster"])
                  .filterDate(start_date, end_date)
                  .filterBounds(geometry)
                  .map(calculate_aster_lst))
    
    # Return median if available
    size = collection.size()
    return ee.Algorithms.If(size.gt(0), collection.median(), None)

# ================================================================================
# SECTION 7: VEGETATION INDEX CALCULATION
# ================================================================================

def calculate_vegetation_indices(start_date: str, end_date: str, 
                                geometry: ee.Geometry, 
                                target_scale: int = 30) -> ee.Image:
    """
    Calculate vegetation indices from Landsat 8/9 with optional resampling.
    
    Args:
        start_date: Start date
        end_date: End date
        geometry: Area of interest
        target_scale: Target resolution in meters for resampling (default 30m)
        
    Returns:
        Image with NDVI, NDBI, and NDWI bands
    """
    def process_landsat_sr(image):
        """Process Landsat surface reflectance and calculate indices."""
        # QA masking
        qa = image.select('QA_PIXEL')
        mask = (qa.bitwiseAnd(1<<3).eq(0)  # Cloud
                .And(qa.bitwiseAnd(1<<4).eq(0)))  # Cloud shadow
        
        # Apply scale factors
        optical = image.select(['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7'])
        optical = optical.multiply(0.0000275).add(-0.2).clamp(0, 1)
        
        # Calculate indices
        ndvi = optical.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
        ndbi = optical.normalizedDifference(['SR_B6', 'SR_B5']).rename('NDBI')
        ndwi = optical.normalizedDifference(['SR_B3', 'SR_B5']).rename('NDWI')
        
        result = ee.Image.cat([ndvi, ndbi, ndwi]).updateMask(mask)
        
        # Resample if target scale is different from native 30m
        if target_scale != 30:
            result = result.reproject(crs='EPSG:4326', scale=target_scale)
        
        return result
    
    # Combine Landsat 8 and 9
    l8 = ee.ImageCollection(DATASETS["landsat8"])
    l9 = ee.ImageCollection(DATASETS["landsat9"])
    
    collection = (l8.merge(l9)
                  .filterDate(start_date, end_date)
                  .filterBounds(geometry)
                  .filter(ee.Filter.lt('CLOUD_COVER', ANALYSIS_CONFIG['cloud_threshold']))
                  .map(process_landsat_sr))
    
    # Return median composite
    return collection.median()

# ================================================================================
# SECTION 8: PIXEL-BY-PIXEL SUHI COMPUTATION
# ================================================================================

def compute_pixel_suhi(urban_mask, rural_mask, lst_image, zones):
    # Pick first band dynamically (works for MODIS/Landsat/etc.)
    band = lst_image.bandNames().get(0)

    stats = lst_image.updateMask(rural_mask).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=zones['rural_ring'],
        # Use the LST native scale when possible; MODIS is 1000 m
        scale=GEE_CONFIG.get('scale_modis', ANALYSIS_CONFIG['target_resolution_m']),
        maxPixels=GEE_CONFIG['max_pixels'],
        bestEffort=GEE_CONFIG['best_effort']
    )

    rural_mean = ee.Number(stats.get(ee.String(band)))
    rural_reference = ee.Image.constant(rural_mean).rename('rural_mean').toFloat()

    return (lst_image.select([ee.String(band)]).toFloat()
            .subtract(rural_reference)
            .updateMask(urban_mask)
            .rename('SUHI_pixel'))


def compute_zonal_suhi(zones: Dict[str, ee.Geometry], lst_image: ee.Image,
                       classifications: Dict[str, ee.Image]) -> Dict[str, Any]:
    """
    Compute SUHI with optimized memory usage and error handling.
    """
    # Create consensus urban mask
    if 'esri' in classifications and len(classifications) > 1:
        w = ANALYSIS_CONFIG['esri_weight']
        urban_mask = classifications['esri'].multiply(w)
        other_w = (1 - w) / (len(classifications) - 1)
        for name, img in classifications.items():
            if name != 'esri':
                urban_mask = urban_mask.add(img.multiply(other_w))
    else:
        weight = 1.0 / max(1, len(classifications))
        urban_mask = ee.Image.constant(0)
        for img in classifications.values():
            urban_mask = urban_mask.add(img.multiply(weight))

    # Binary masks
    urban_mask = urban_mask.gt(0.5)
    rural_mask = urban_mask.Not()

    if lst_image is None:
        return {'error': 'No LST data available'}

    # Use explicit band and scale for MODIS day LST
    band = 'LST_Day_MODIS'
    scale = GEE_CONFIG['scale_modis']

    # Use separate reducers to avoid memory issues
    try:
        # Urban statistics - use tileScale to handle large computations
        urban_mean = lst_image.select(band).updateMask(urban_mask).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=zones['urban_core'],
            scale=scale,
            maxPixels=GEE_CONFIG['max_pixels'],
            bestEffort=True,
            tileScale=4  # Increase tile scale to handle memory
        )
        
        urban_stdDev = lst_image.select(band).updateMask(urban_mask).reduceRegion(
            reducer=ee.Reducer.stdDev(),
            geometry=zones['urban_core'],
            scale=scale,
            maxPixels=GEE_CONFIG['max_pixels'],
            bestEffort=True,
            tileScale=4
        )
        
        urban_count = lst_image.select(band).updateMask(urban_mask).reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=zones['urban_core'],
            scale=scale,
            maxPixels=GEE_CONFIG['max_pixels'],
            bestEffort=True,
            tileScale=4
        )
        
        # Rural statistics
        rural_mean = lst_image.select(band).updateMask(rural_mask).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=zones['rural_ring'],
            scale=scale,
            maxPixels=GEE_CONFIG['max_pixels'],
            bestEffort=True,
            tileScale=4
        )
        
        rural_stdDev = lst_image.select(band).updateMask(rural_mask).reduceRegion(
            reducer=ee.Reducer.stdDev(),
            geometry=zones['rural_ring'],
            scale=scale,
            maxPixels=GEE_CONFIG['max_pixels'],
            bestEffort=True,
            tileScale=4
        )
        
        rural_count = lst_image.select(band).updateMask(rural_mask).reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=zones['rural_ring'],
            scale=scale,
            maxPixels=GEE_CONFIG['max_pixels'],
            bestEffort=True,
            tileScale=4
        )
        
        # Combine results
        urban_stats = {
            f'{band}_mean': urban_mean.get(band).getInfo(),
            f'{band}_stdDev': urban_stdDev.get(band).getInfo(),
            f'{band}_count': urban_count.get(band).getInfo()
        }
        
        rural_stats = {
            f'{band}_mean': rural_mean.get(band).getInfo(),
            f'{band}_stdDev': rural_stdDev.get(band).getInfo(),
            f'{band}_count': rural_count.get(band).getInfo()
        }
        
        return {'urban_stats': urban_stats, 'rural_stats': rural_stats}
        
    except Exception as e:
        print(f"     ⚠️ Error in reduceRegion: {e}")
        # Try with even more conservative settings
        try:
            # Increase scale to reduce memory usage
            fallback_scale = scale * 2
            
            urban_mean = lst_image.select(band).updateMask(urban_mask).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=zones['urban_core'],
                scale=fallback_scale,
                maxPixels=1e7,  # Reduce max pixels
                bestEffort=True,
                tileScale=8  # Further increase tile scale
            )
            
            rural_mean = lst_image.select(band).updateMask(rural_mask).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=zones['rural_ring'],
                scale=fallback_scale,
                maxPixels=1e7,
                bestEffort=True,
                tileScale=8
            )
            
            # Simplified stats for fallback
            urban_stats = {
                f'{band}_mean': urban_mean.get(band).getInfo(),
                f'{band}_stdDev': 0,  # No std dev in fallback
                f'{band}_count': 0
            }
            
            rural_stats = {
                f'{band}_mean': rural_mean.get(band).getInfo(),
                f'{band}_stdDev': 0,
                f'{band}_count': 0
            }
            
            print(f"     ⚠️ Using fallback computation with scale={fallback_scale}")
            return {'urban_stats': urban_stats, 'rural_stats': rural_stats}
            
        except Exception as fallback_error:
            print(f"     ❌ Fallback also failed: {fallback_error}")
            return {'error': f'Computation failed: {str(e)}'}



# ================================================================================
# SECTION 9: ERROR ANALYSIS AND REPORTING
# ================================================================================

def calculate_error_metrics(urban_stats: Dict, rural_stats: Dict) -> Union[Dict[str, float], Dict[str, str]]:
    """
    Calculate error metrics and confidence intervals for SUHI.
    
    Args:
        urban_stats: Urban zone statistics
        rural_stats: Rural zone statistics
        
    Returns:
        Dictionary of error metrics or error message
    """
    # Extract values with safe defaults
    urban_mean = urban_stats.get('LST_Day_MODIS_mean', None)
    urban_std = urban_stats.get('LST_Day_MODIS_stdDev', 0)
    urban_count = urban_stats.get('LST_Day_MODIS_count', 0)
    
    rural_mean = rural_stats.get('LST_Day_MODIS_mean', None)
    rural_std = rural_stats.get('LST_Day_MODIS_stdDev', 0)
    rural_count = rural_stats.get('LST_Day_MODIS_count', 0)
    
    if urban_mean is None or rural_mean is None:
        return {'error': 'Insufficient data'}
    
    # Calculate SUHI
    suhi = float(urban_mean) - float(rural_mean)
    
    # Calculate standard error
    if urban_count > 0 and rural_count > 0:
        urban_se = float(urban_std) / np.sqrt(float(urban_count))
        rural_se = float(rural_std) / np.sqrt(float(rural_count))
        
        # Combined standard error
        suhi_se = np.sqrt(urban_se**2 + rural_se**2)
        
        # 95% confidence interval
        ci_95 = 1.96 * suhi_se
        
        # Relative error
        relative_error = (suhi_se / abs(suhi) * 100) if suhi != 0 else np.inf
    else:
        suhi_se = np.inf
        ci_95 = np.inf
        relative_error = np.inf
    
    return {
        'suhi': suhi,
        'suhi_se': suhi_se,
        'ci_95_lower': suhi - ci_95,
        'ci_95_upper': suhi + ci_95,
        'relative_error_pct': relative_error,
        'urban_pixels': int(urban_count) if urban_count else 0,
        'rural_pixels': int(rural_count) if rural_count else 0,
        'urban_std': float(urban_std),
        'rural_std': float(rural_std)
    }

def compute_day_night_suhi(zones: Dict[str, ee.Geometry], lst_day: ee.Image, 
                          lst_night: ee.Image, classifications: Dict[str, ee.Image]) -> Dict[str, Any]:
    """
    Compute day vs night SUHI analysis with both MODIS LST bands.
    """
    print(f"   📊 Computing day vs night SUHI analysis...")
    
    # Apply rate limiting
    rate_limiter.wait()
    
    # Create consensus urban mask
    if 'esri' in classifications and len(classifications) > 1:
        w = ANALYSIS_CONFIG['esri_weight']
        urban_mask = classifications['esri'].multiply(w)
        other_w = (1 - w) / (len(classifications) - 1)
        for name, img in classifications.items():
            if name != 'esri':
                urban_mask = urban_mask.add(img.multiply(other_w))
    else:
        weight = 1.0 / max(1, len(classifications))
        urban_mask = ee.Image.constant(0)
        for img in classifications.values():
            urban_mask = urban_mask.add(img.multiply(weight))
    
    urban_mask = urban_mask.gt(0.5)
    rural_mask = urban_mask.Not()
    
    scale = GEE_CONFIG['scale_modis']
    results = {}
    
    # Process day and night with dynamic band detection
    for time_period, lst_image in [
        ('day', lst_day),
        ('night', lst_night)
    ]:
        if lst_image is None:
            results[time_period] = {'error': f'No {time_period} LST data available'}
            continue
        
        try:
            # Get actual band names dynamically
            band_names = lst_image.bandNames().getInfo()
            print(f"     📊 Available {time_period} LST bands: {band_names}")
            
            # Use the first available band (should be the LST band)
            band_name = band_names[0] if band_names else f'LST_{time_period.title()}_MODIS'
            
            # Convert to Celsius
            lst_celsius = lst_image.select(band_name).multiply(0.02).subtract(273.15)
            
            # Urban statistics
            urban_stats = lst_celsius.updateMask(urban_mask).reduceRegion(
                reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), None, True).combine(ee.Reducer.count(), None, True),
                geometry=zones['urban_core'],
                scale=scale,
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=True,
                tileScale=4
            )
            
            # Rural statistics
            rural_stats = lst_celsius.updateMask(rural_mask).reduceRegion(
                reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), None, True).combine(ee.Reducer.count(), None, True),
                geometry=zones['rural_ring'],
                scale=scale,
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=True,
                tileScale=4
            )
            
            # Extract values
            urban_mean = urban_stats.get(f'{band_name}_mean').getInfo()
            urban_std = urban_stats.get(f'{band_name}_stdDev').getInfo()
            urban_count = urban_stats.get(f'{band_name}_count').getInfo()
            
            rural_mean = rural_stats.get(f'{band_name}_mean').getInfo()
            rural_std = rural_stats.get(f'{band_name}_stdDev').getInfo()
            rural_count = rural_stats.get(f'{band_name}_count').getInfo()
            
            # Calculate SUHI
            suhi = urban_mean - rural_mean if urban_mean and rural_mean else None
            
            results[time_period] = {
                'urban_mean': urban_mean,
                'urban_std': urban_std,
                'urban_count': urban_count,
                'rural_mean': rural_mean,
                'rural_std': rural_std,
                'rural_count': rural_count,
                'suhi': suhi,
                'band': band_name
            }
            
        except Exception as e:
            print(f"     ⚠️ Error computing {time_period} SUHI: {e}")
            results[time_period] = {'error': str(e)}
    
    # Calculate day-night differences
    if 'day' in results and 'night' in results and 'error' not in results['day'] and 'error' not in results['night']:
        day_suhi = results['day']['suhi']
        night_suhi = results['night']['suhi']
        
        if day_suhi is not None and night_suhi is not None:
            results['day_night_difference'] = {
                'suhi_difference': day_suhi - night_suhi,
                'day_stronger': day_suhi > night_suhi,
                'magnitude_ratio': day_suhi / night_suhi if night_suhi != 0 else np.inf
            }
    
    return results

def analyze_esri_landcover_changes(city_name: str, start_year: int = 2017, 
                                  end_year: int = 2024) -> Dict[str, Any]:
    """
    Analyze ESRI landcover changes over time for urban expansion assessment.
    
    Args:
        city_name: Name of the city
        start_year: Starting year (default 2017)
        end_year: Ending year (default 2024)
        
    Returns:
        Dictionary containing landcover change analysis
    """
    print(f"   🏗️ Analyzing ESRI landcover changes {start_year}-{end_year}...")
    
    city_info = UZBEKISTAN_CITIES[city_name]
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    buffer_m = city_info['buffer_m']
    region = center.buffer(buffer_m)
    
    results = {}
    yearly_stats = {}
    
    # Analyze each year
    for year in range(start_year, end_year + 1):
        try:
            # Load ESRI data for the year
            esri_image = load_esri_classification(year, region)
            
            if esri_image is None:
                print(f"     ⚠️ No ESRI data for {year}")
                continue
            
            # Get actual band names dynamically
            band_names = esri_image.bandNames().getInfo()
            print(f"     📊 Available ESRI bands for {year}: {band_names}")
            
            # Use the first available band (should be the ESRI landcover band)
            band_name = band_names[0] if band_names else 'b1'
            
            # Calculate landcover areas using dynamic band name
            landcover_stats = esri_image.select(band_name).reduceRegion(
                reducer=ee.Reducer.frequencyHistogram(),
                geometry=region,
                scale=30,  # Use 30m for efficiency
                maxPixels=1e8,
                bestEffort=True
            )
            
            # Extract histogram
            histogram = landcover_stats.get(band_name).getInfo()
            
            # Convert to meaningful landcover areas
            landcover_areas = {}
            total_pixels = sum(histogram.values()) if histogram else 0
            
            if histogram and total_pixels > 0:
                for class_id, pixel_count in histogram.items():
                    class_name = ESRI_CLASSES.get(int(class_id), f'Unknown_{class_id}')
                    area_km2 = (pixel_count * 30 * 30) / 1000000  # Convert to km²
                    landcover_areas[class_name] = {
                        'area_km2': area_km2,
                        'percentage': (pixel_count / total_pixels) * 100
                    }
            
            yearly_stats[year] = landcover_areas
            
        except Exception as e:
            print(f"     ⚠️ Error analyzing {year}: {e}")
            yearly_stats[year] = {'error': str(e)}
    
    # Calculate changes between start and end years
    if start_year in yearly_stats and end_year in yearly_stats:
        if 'error' not in yearly_stats[start_year] and 'error' not in yearly_stats[end_year]:
            changes = {}
            
            # Find all unique landcover classes
            all_classes = set(yearly_stats[start_year].keys()) | set(yearly_stats[end_year].keys())
            
            for class_name in all_classes:
                start_area = yearly_stats[start_year].get(class_name, {}).get('area_km2', 0)
                end_area = yearly_stats[end_year].get(class_name, {}).get('area_km2', 0)
                
                changes[class_name] = {
                    'start_area_km2': start_area,
                    'end_area_km2': end_area,
                    'change_km2': end_area - start_area,
                    'change_percent': ((end_area - start_area) / start_area * 100) if start_area > 0 else np.inf
                }
            
            results['landcover_changes'] = changes
    
    results['yearly_stats'] = yearly_stats
    results['analysis_period'] = f"{start_year}-{end_year}"
    
    return results

# ================================================================================
# SECTION 10: ANNUAL ESRI-BASED TEMPORAL ANALYSIS
# ================================================================================

def analyze_annual_urban_expansion(city_name: str, start_year: int = 2017, 
                                  end_year: int = 2024) -> pd.DataFrame:
    """
    Analyze year-by-year urban expansion using annual ESRI data (2017-2024).
    
    Args:
        city_name: Name of the city
        start_year: Starting year for analysis (default 2017)
        end_year: Ending year for analysis (default 2024)
        
    Returns:
        DataFrame with annual urban area statistics
    """
    city_info = UZBEKISTAN_CITIES[city_name]
    zones = create_analysis_zones(city_info)
    
    # Prepare results storage
    annual_data = []
    
    print(f"   📊 Analyzing {city_name} annual expansion ({start_year}-{end_year})")
    
    for year in range(start_year, end_year + 1):
        try:
            # Load ESRI classification for this specific year
            esri_image = load_esri_classification(year, zones['full_extent'])
            
            # Check if image loaded successfully
            if esri_image is None:
                print(f"     ❌ Error processing {year}: No ESRI data available")
                continue
            
            # Extract built area (class 7) - the image should be single band
            built_mask = esri_image.eq(7)
            
            # Calculate total built area using the approach from the working reference
            pixel_area = ee.Image.pixelArea()
            total_Built_Area = built_mask.multiply(pixel_area).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=zones['urban_core'],
                scale=GEE_CONFIG['scale'],
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=GEE_CONFIG['best_effort']
            )
            
            # Calculate built area in extended region for sprawl analysis
            extended_Built_Area = built_mask.multiply(pixel_area).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=zones['full_extent'],
                scale=GEE_CONFIG['scale'],
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=GEE_CONFIG['best_effort']
            )
            
            # Calculate urban density (built pixels / total pixels)
            built_pixels = built_mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=zones['urban_core'],
                scale=GEE_CONFIG['scale'],
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=GEE_CONFIG['best_effort']
            )
            
            # Get computed values - use the approach from working reference
            try:
                # Get all available results first
                area_result = total_Built_Area.getInfo()
                extended_result = extended_Built_Area.getInfo()
                pixel_result = built_pixels.getInfo()
                
                #print(f"     🔍 Debug - Area result: {area_result}")
                #print(f"     🔍 Debug - Pixel result: {pixel_result}")
                
                # In the working reference, after multiplication with pixelArea,
                # the band name should be the same as the original ESRI band
                # Let's try to get the band name from the original image
                original_band_names = esri_image.bandNames().getInfo()
                #print(f"     🔍 Debug - Original band names: {original_band_names}")
                
                if area_result and len(area_result) > 0:
                    # Try different possible keys
                    area_keys = list(area_result.keys())
                    #print(f"     🔍 Debug - Available area keys: {area_keys}")
                    
                    # Use the first available key
                    area_key = area_keys[0];
                    
                    # Extract values
                    Built_Area_m2 = area_result.get(area_key, 0)
                    Built_Area_km2 = Built_Area_m2 / 1e6  # Convert to km²
                    
                    extended_area_m2 = extended_result.get(area_key, 0) if extended_result else 0
                    extended_area_km2 = extended_area_m2 / 1e6
                    
                    built_pixel_count = pixel_result.get(area_key, 0) if pixel_result else 0
                    
                    # Calculate total area for density
                    total_area_m2 = zones['urban_core'].area().getInfo()
                    total_area_km2 = total_area_m2 / 1e6
                    urban_density = (Built_Area_km2 / total_area_km2 * 100) if total_area_km2 > 0 else 0
                    
                    annual_data.append({
                        'city': city_name,
                        'year': year,
                        'Built_Area_core_km2': Built_Area_km2,
                        'Built_Area_extended_km2': extended_area_km2,
                        'built_pixels': built_pixel_count,
                        'urban_density_pct': urban_density,
                        'analysis_area_km2': total_area_km2,
                        'area_key_used': area_key,  # For debugging
                        'debug_area_m2': Built_Area_m2  # For debugging
                    })
                    
                    print(f"     ✅ {year}: {Built_Area_km2:.2f} km² built area (from {Built_Area_m2:.0f} m²)")
                else:
                    print(f"     ❌ Error processing {year}: No data in reduction result")
                    print(f"        Area result: {area_result}")
                    continue
                
            except Exception as compute_error:
                print(f"     ❌ Error computing values for {year}: {compute_error}")
                continue
            
        except Exception as e:
            print(f"     ❌ Error processing {year}: {e}")
            continue
    
    # Convert to DataFrame and calculate year-over-year changes
    df = pd.DataFrame(annual_data)
    
    if len(df) > 1:
        # Calculate annual growth rates
        df['annual_growth_km2'] = df['Built_Area_core_km2'].diff()
        df['annual_growth_pct'] = df['Built_Area_core_km2'].pct_change() * 100
        df['density_change_pct'] = df['urban_density_pct'].diff()
        
        # Calculate cumulative growth from baseline
        baseline_area = df['Built_Area_core_km2'].iloc[0]
        df['cumulative_growth_km2'] = df['Built_Area_core_km2'] - baseline_area
        df['cumulative_growth_pct'] = (df['Built_Area_core_km2'] / baseline_area - 1) * 100
    
    return df


def analyze_annual_suhi_trends(city_name: str, years: List[int]) -> Dict:
    """
    Analyze SUHI trends using year-specific ESRI urban masks.
    """
    city_info = UZBEKISTAN_CITIES[city_name]
    zones = create_analysis_zones(city_info)
    
    annual_suhi = []
    
    print(f"   🌡️ Analyzing annual SUHI trends for {city_name}")
    
    for year in years:
        try:
            # Load year-specific ESRI classification
            esri_image = load_esri_classification(year, zones['full_extent'])
            
            if esri_image is None:
                print(f"     ⚠️ No ESRI data for {year}")
                continue
            
            # Get the actual band name from the loaded image
            band_names = esri_image.bandNames().getInfo()
            if not band_names:
                print(f"     ⚠️ No bands found in ESRI image for {year}")
                continue
            
            # Use the first (and usually only) band
            actual_band = band_names[0]
            print(f"     🔍 Debug - Using band '{actual_band}' for {year}")
            
            # CREATE BUILT MASK - THIS WAS MISSING!
            built_mask = esri_image.select(actual_band).eq(7)  # <-- ADD THIS LINE
            

            # Load temperature data for this year
            start_date = f'{year}-01-01'
            end_date = f'{year}-12-31'
            
            modis_lst = load_modis_lst(start_date, end_date, zones['full_extent'])
            
            if modis_lst is None:
                print(f"     ⚠️ No temperature data for {year}")
                continue
            

            # Calculate SUHI using year-specific urban mask
            urban_temp = modis_lst.select('LST_Day_MODIS').updateMask(built_mask).reduceRegion(
                reducer=ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True),
                geometry=zones['urban_core'],
                scale=GEE_CONFIG['scale_modis'],
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=GEE_CONFIG['best_effort']
            )
            
            # Rural temperature (non-built areas)
            rural_mask = built_mask.Not()
            rural_temp = modis_lst.select('LST_Day_MODIS').updateMask(rural_mask).reduceRegion(
                reducer=ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True),
                geometry=zones['rural_ring'],
                scale=GEE_CONFIG['scale_modis'],
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=GEE_CONFIG['best_effort']
            )
            
            # Get values
            urban_mean = ee.Number(urban_temp.get('LST_Day_MODIS_mean')).getInfo()
            urban_count = ee.Number(urban_temp.get('LST_Day_MODIS_count')).getInfo()
            rural_mean = ee.Number(rural_temp.get('LST_Day_MODIS_mean')).getInfo()
            rural_count = ee.Number(rural_temp.get('LST_Day_MODIS_count')).getInfo()
            
            if urban_mean is not None and rural_mean is not None:
                suhi = urban_mean - rural_mean
                
                annual_suhi.append({
                    'city': city_name,
                    'year': year,
                    'urban_temp': urban_mean,
                    'rural_temp': rural_mean,
                    'suhi_intensity': suhi,
                    'urban_pixels': urban_count,
                    'rural_pixels': rural_count,
                    'band_used': actual_band  # For debugging
                })
                
                print(f"     ✅ {year}: SUHI = {suhi:.2f}°C (using band '{actual_band}')")
            
        except Exception as e:
            print(f"     ❌ Error processing SUHI for {year}: {e}")
            continue
    
    # Calculate trends
    df = pd.DataFrame(annual_suhi)
    
    trends = {
        'city': city_name,
        'years_analyzed': len(df),
        'data': df.to_dict('records') if len(df) > 0 else [],
        'trends': {}
    }
    
    if len(df) > 2:
        # Calculate linear trends only if scipy is available
        if SCIPY_AVAILABLE:
            try:
                from scipy import stats
                
                # SUHI trend
                if 'suhi_intensity' in df.columns:
                    slope, intercept, r_value, p_value, std_err = stats.linregress(df['year'], df['suhi_intensity'])
                    trends['trends']['suhi_trend_per_year'] = slope
                    trends['trends']['suhi_r_squared'] = r_value**2
                    trends['trends']['suhi_p_value'] = p_value
                
                # Urban temperature trend
                if 'urban_temp' in df.columns:
                    slope, intercept, r_value, p_value, std_err = stats.linregress(df['year'], df['urban_temp'])
                    trends['trends']['urban_temp_trend_per_year'] = slope
                    trends['trends']['urban_temp_r_squared'] = r_value**2
            except ImportError:
                trends['trends']['note'] = 'Trend analysis requires scipy package'
        else:
            trends['trends']['note'] = 'Trend analysis requires scipy package'
    
    return trends

def create_temporal_expansion_report(cities: List[str], 
                                   output_dir: Path) -> pd.DataFrame:
    """
    Create comprehensive temporal expansion report using annual ESRI data.
    
    Args:
        cities: List of cities to analyze
        output_dir: Output directory for reports
        
    Returns:
        Combined DataFrame with all cities' temporal data
    """
    all_temporal_data = []
    
    print("🔄 Creating temporal expansion report...")
    
    for city in cities:
        try:
            # Get annual expansion data
            annual_df = analyze_annual_urban_expansion(city, 2017, 2024)
            
            # Only append if we have data
            if not annual_df.empty:
                all_temporal_data.append(annual_df)
                
                # Save individual city report
                city_file = output_dir / f'{city}_annual_expansion_2017_2024.csv'
                annual_df.to_csv(city_file, index=False)
                
                print(f"   ✅ {city}: {len(annual_df)} years analyzed")
            else:
                print(f"   ⚠️ {city}: No data collected")
            
        except Exception as e:
            print(f"   ❌ Error analyzing {city}: {e}")
            continue
    
    # Combine all data
    if all_temporal_data:
        combined_df = pd.concat(all_temporal_data, ignore_index=True)
        
        # Save combined report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_file = output_dir / f'all_cities_temporal_expansion_{timestamp}.csv'
        combined_df.to_csv(combined_file, index=False)
        
        # Create summary statistics only if we have data with 'city' column
        if 'city' in combined_df.columns and len(combined_df) > 0:
            summary_stats = combined_df.groupby('city').agg({
                'Built_Area_core_km2': ['first', 'last', 'mean'],
                'annual_growth_km2': 'mean',
                'annual_growth_pct': 'mean',
                'urban_density_pct': ['first', 'last'],
                'cumulative_growth_pct': 'last'
            }).round(3)
            
            summary_file = output_dir / f'expansion_summary_statistics_{timestamp}.csv'
            summary_stats.to_csv(summary_file)
            
            print(f"📊 Temporal expansion reports saved:")
            print(f"   - Combined data: {combined_file}")
            print(f"   - Summary statistics: {summary_file}")
        else:
            print(f"📊 Combined data saved: {combined_file}")
            print(f"   ⚠️ No summary statistics (insufficient data)")
        
        return combined_df
    else:
        print("   ⚠️ No temporal data collected for any city")
        return pd.DataFrame()

# ================================================================================
# SECTION 11: URBAN EXPANSION ANALYSIS (UPDATED)
# ================================================================================

def analyze_urban_expansion(city_name: str, start_year: int, end_year: int) -> Dict:
    """
    Analyze urban expansion between two time periods.
    """
    city_info = UZBEKISTAN_CITIES[city_name]
    zones = create_analysis_zones(city_info)
    
    # Load ESRI classifications for both years
    esri_start = load_esri_classification(start_year, zones['full_extent'])
    esri_end = load_esri_classification(end_year, zones['full_extent'])
    
    if esri_start is None or esri_end is None:
        return {
            'city': city_name,
            'start_year': start_year,
            'end_year': end_year,
            'error': 'ESRI data not available for one or both years'
        }
    
    # Get actual band names dynamically
    start_bands = esri_start.bandNames().getInfo()
    end_bands = esri_end.bandNames().getInfo()
    print(f"     📊 Start year bands: {start_bands}, End year bands: {end_bands}")
    
    start_band = start_bands[0] if start_bands else 'b1'
    end_band = end_bands[0] if end_bands else 'b1'
    
    # Extract built area (class 7) using dynamic band names
    built_start = esri_start.select(start_band).eq(7)
    built_end = esri_end.select(end_band).eq(7)
    
    # Calculate areas
    pixel_area = ee.Image.pixelArea()
    
    area_start = built_start.multiply(pixel_area).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=zones['urban_core'],
        scale=GEE_CONFIG['scale'],
        maxPixels=GEE_CONFIG['max_pixels'],
        bestEffort=GEE_CONFIG['best_effort']
    )
    
    area_end = built_end.multiply(pixel_area).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=zones['urban_core'],
        scale=GEE_CONFIG['scale'],
        maxPixels=GEE_CONFIG['max_pixels'],
        bestEffort=GEE_CONFIG['best_effort']
    )
    
    # Use dynamic band names for area calculation
    area_start_km2 = ee.Number(area_start.get(start_band)).divide(1e6).getInfo()
    area_end_km2 = ee.Number(area_end.get(end_band)).divide(1e6).getInfo()
    expansion_km2 = area_end_km2 - area_start_km2
    expansion_pct = (expansion_km2 / area_start_km2 * 100) if area_start_km2 > 0 else 0
    
    return {
        'city': city_name,
        'start_year': start_year,
        'end_year': end_year,
        'area_start_km2': area_start_km2,
        'area_end_km2': area_end_km2,
        'expansion_km2': expansion_km2,
        'expansion_pct': expansion_pct
    }

# ================================================================================
# SECTION 11: LANDCOVER CHANGE ANALYSIS
# ================================================================================

def analyze_landcover_changes(city_name: str, start_year: int, end_year: int) -> pd.DataFrame:
    """
    Analyze land cover changes with transition matrix and error estimation.
    """
    city_info = UZBEKISTAN_CITIES[city_name]
    zones = create_analysis_zones(city_info)
    
    # Load ESRI classifications
    esri_start = load_esri_classification(start_year, zones['urban_core'])
    esri_end = load_esri_classification(end_year, zones['urban_core'])
    
    if esri_start is None or esri_end is None:
        return pd.DataFrame()  # Return empty DataFrame if no data
    
    # Get actual band names
    start_bands = esri_start.bandNames().getInfo()
    end_bands = esri_end.bandNames().getInfo()
    
    if not start_bands or not end_bands:
        return pd.DataFrame()
    
    start_band = start_bands[0]
    end_band = end_bands[0]
    
    # Calculate transition matrix
    results = []
    
    for from_class, from_name in ESRI_CLASSES.items():
        for to_class, to_name in ESRI_CLASSES.items():
            # Create transition mask using actual band names
            transition = esri_start.select(start_band).eq(from_class).And(esri_end.select(end_band).eq(to_class))
            
            # Calculate area
            area = transition.multiply(ee.Image.pixelArea()).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=zones['urban_core'],
                scale=GEE_CONFIG['scale'],
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=GEE_CONFIG['best_effort']
            )
            
            # Get the area value using actual band name
            area_km2 = ee.Number(area.get(start_band)).divide(1e6).getInfo()
            
            results.append({
                'from_class': from_name,
                'to_class': to_name,
                'area_km2': area_km2
            })
    
    # Create transition matrix DataFrame
    df = pd.DataFrame(results)
    transition_matrix = df.pivot(index='from_class', columns='to_class', values='area_km2').fillna(0.0)
    transition_matrix['total_from'] = transition_matrix.sum(axis=1)
    transition_matrix.loc['total_to'] = transition_matrix.sum(axis=0)
    
    # Calculate error as percentage of unchanged pixels (diagonal)
    try:
        total_area_val = transition_matrix.loc['total_to', 'total_from']
        total_area = pd.to_numeric(total_area_val, errors='coerce')
        if pd.isna(total_area):
            total_area = 0.0
    except:
        total_area = 0.0
    
    # Calculate unchanged area (diagonal sum) with proper type handling
    unchanged_values = []
    for cls in ESRI_CLASSES.values():
        if cls in transition_matrix.index and cls in transition_matrix.columns:
            try:
                val = transition_matrix.loc[cls, cls]
                val_numeric = pd.to_numeric(val, errors='coerce')
                if pd.notna(val_numeric):
                    unchanged_values.append(val_numeric)
            except:
                continue
    
    unchanged_area = sum(unchanged_values) if unchanged_values else 0.0
    
    accuracy_pct = (unchanged_area / total_area) * 100 if total_area > 0 else 0.0
    error_pct = 100.0 - accuracy_pct
    
    # Add metadata
    transition_matrix.attrs = {
        'city': city_name,
        'start_year': start_year,
        'end_year': end_year,
        'accuracy_pct': accuracy_pct,
        'error_pct': error_pct
    }
    
    return transition_matrix

# ================================================================================
# SECTION 12: COMPREHENSIVE ANALYSIS PIPELINE
# ================================================================================

def run_comprehensive_analysis(city_name: str, year: int) -> Dict:
    """
    Run complete SUHI analysis for a city and year with optimized settings for detailed validation.
    
    Args:
        city_name: Name of the city
        year: Analysis year
        
    Returns:
        Comprehensive analysis results
    """
    print(f"\n🔍 Analyzing {city_name} for {year}")
    
    city_info = UZBEKISTAN_CITIES[city_name]
    
    # Get optimal scales for detailed validation phase
    optimal_scales = get_optimal_scale_for_city(city_name, "detailed_validation")
    scale = int(optimal_scales['scale'])
    
    print(f"   📏 Using {scale}m resolution for classifications (detailed validation mode)")
    
    zones = create_analysis_zones(city_info)
    
    # Define date range
    start_date = f'{year}-01-01'
    end_date = f'{year}-12-31'
    
    # Step 1: Load all classifications with optimized scaling
    print("   📊 Loading classification datasets...")
    classifications = load_all_classifications(year, zones['full_extent'], 
                                              start_date, end_date, optimal_scales)
    
    # Step 2: Assess classification accuracy (simplified for memory)
    print("   🎯 Assessing classification accuracy...")
    try:
        accuracy_metrics = assess_classification_accuracy(classifications, zones['urban_core'])
    except Exception as e:
        print(f"     ⚠️ Accuracy assessment failed: {e}")
        accuracy_metrics = ee.Dictionary({'error': 'Memory limit exceeded'})
    
    # Step 3: Load temperature data
    print("   🌡️ Loading temperature data...")
    try:
        modis_lst = load_modis_lst(start_date, end_date, zones['full_extent'])
    except Exception as e:
        print(f"     ⚠️ MODIS LST loading failed: {e}")
        modis_lst = None
    
    # Skip other temperature sources for memory optimization in detailed validation
    print("   ⚠️ Skipping Landsat/ASTER for memory optimization")
    landsat_lst = None
    aster_lst = None
    
    # Step 4: Calculate vegetation indices (with coarser resolution)
    print("   🌱 Calculating vegetation indices...")
    try:
        vegetation = calculate_vegetation_indices(start_date, end_date, zones['full_extent'], 
                                                target_scale=int(optimal_scales['scale_landsat']))
    except Exception as e:
        print(f"                                 ⚠️ Vegetation calculation failed: {e}")
        vegetation = None
    
    # Step 5: Compute SUHI with optimized settings
    print("   🔥 Computing SUHI...")
    try:
        # Temporarily update GEE_CONFIG with optimal scales
        original_config = GEE_CONFIG.copy()
        GEE_CONFIG.update({
            'scale': optimal_scales['scale'],
            'max_pixels': optimal_scales['maxPixels']
        })
        
        suhi_stats = compute_zonal_suhi(zones, modis_lst, classifications)
        
        # Restore original config
        GEE_CONFIG.update(original_config)
        
    except Exception as e:
        print(f"     ⚠️ SUHI computation failed: {e}")
        # Try with fallback settings
        try:
            print("     🔄 Attempting fallback computation...")
            fallback_scales = get_optimal_scale_for_city(city_name, "fallback")
            GEE_CONFIG.update(fallback_scales)
            
            suhi_stats = compute_zonal_suhi(zones, modis_lst, classifications)
            
            # Restore original config
            GEE_CONFIG.update(original_config)
            print(f"     ✅ Fallback successful with {fallback_scales['scale']}m resolution")
            
        except Exception as fallback_error:
            print(f"     ❌ Fallback also failed: {fallback_error}")
            suhi_stats = {'error': 'All computation methods failed'}
            # Restore original config
            GEE_CONFIG.update(original_config)
    
    # Step 6: Calculate error metrics
    print("   📈 Calculating error metrics...")
    if 'error' not in suhi_stats and isinstance(suhi_stats.get('urban_stats'), dict) and isinstance(suhi_stats.get('rural_stats'), dict):
        try:
            error_metrics = calculate_error_metrics(suhi_stats['urban_stats'], 
                                                   suhi_stats['rural_stats'])
        except Exception as e:
            print(f"     ⚠️ Error metrics calculation failed: {e}")
            error_metrics = {'error': f'Error metrics failed: {str(e)}'}
    else:
        error_metrics = {'error': suhi_stats.get('error', 'SUHI computation failed')}

    # Step 6.5: Day/Night SUHI Analysis
    print("   🌙 Computing day vs night SUHI analysis...")
    day_night_analysis = {}
    if modis_lst is not None:
        try:
            # Load MODIS LST Day and Night separately
            modis_collection = ee.ImageCollection("MODIS/061/MOD11A2") \
                .filterBounds(zones['full_extent']) \
                .filterDate(start_date, end_date)
            
            if modis_collection.size().getInfo() > 0:
                modis_composite = modis_collection.mean()
                
                # Get dynamic band names
                modis_bands = modis_composite.bandNames().getInfo()
                print(f"     📊 Available MODIS bands: {modis_bands}")
                
                # Find day and night LST bands
                day_bands = [b for b in modis_bands if 'Day' in b and 'LST' in b]
                night_bands = [b for b in modis_bands if 'Night' in b and 'LST' in b]
                
                if day_bands and night_bands:
                    # Get day and night LST images
                    lst_day = modis_composite.select(day_bands[0])
                    lst_night = modis_composite.select(night_bands[0])
                    
                    # Rename bands to match expected format
                    lst_day = lst_day.rename('LST_Day_MODIS')
                    lst_night = lst_night.rename('LST_Night_MODIS')
                    
                    day_night_analysis = compute_day_night_suhi(zones, lst_day, lst_night, classifications)
                else:
                    print(f"     ⚠️ Could not find Day/Night LST bands in: {modis_bands}")
                    day_night_analysis = {'error': 'Day/Night LST bands not found'}
                
        except Exception as e:
            print(f"     ⚠️ Day/night analysis failed: {e}")
            day_night_analysis = {'error': str(e)}

    # Step 6.6: ESRI Landcover Change Analysis - FIXED YEAR RANGE
    print("   🏗️ Analyzing ESRI landcover changes...")
    landcover_changes = {}
    try:
        # For a specific year analysis, compare with baseline (2017) and 2020
        # This makes more sense than arbitrary ±3 years
        if year <= 2020:
            # For early years, compare 2017 baseline and 2020
            analysis_start = 2017
            analysis_end = 2020
        else:
            # For recent years, compare 2020 with current/latest
            analysis_start = 2020
            analysis_end = min(2024, year)
        
        print(f"     📅 Analyzing landcover changes from {analysis_start} to {analysis_end}")
        landcover_changes = analyze_esri_landcover_changes(city_name, analysis_start, analysis_end)
    except Exception as e:
        print(f"     ⚠️ Landcover change analysis failed: {e}")
        landcover_changes = {'error': str(e)}

    # Step 7: Extract vegetation statistics (simplified)
    if vegetation is not None:
        try:
            veg_stats = vegetation.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=zones['urban_core'],
                scale=optimal_scales['scale_landsat'],
                maxPixels=optimal_scales['maxPixels'],
                bestEffort=True,
                tileScale=optimal_scales.get('tileScale', 4)
            ).getInfo()
        except Exception as e:
            print(f"     ⚠️ Vegetation statistics failed: {e}")
            veg_stats = {'error': 'Failed to extract vegetation stats'}
    else:
        veg_stats = {'note': 'Vegetation analysis skipped'}
    
    # Compile results
    results = {
        'city': city_name,
        'year': year,
        'processing_scale': optimal_scales['scale'],
        'classifications_available': list(classifications.keys()),
        'accuracy_assessment': accuracy_metrics.getInfo() if accuracy_metrics else {},
        'suhi_analysis': error_metrics,
        'day_night_analysis': day_night_analysis,
        'landcover_changes': landcover_changes,
        'vegetation_indices': veg_stats,
        'urban_stats': suhi_stats.get('urban_stats', {}),
        'rural_stats': suhi_stats.get('rural_stats', {}),
        'optimization_note': f'Processed at {optimal_scales["scale"]}m resolution for memory optimization'
    }
    
    return results

# ================================================================================
# SECTION 13: REPORTING AND VISUALIZATION
# ================================================================================

# ================================================================================
# SECTION 13: ENHANCED VISUALIZATION AND REPORTING
# ================================================================================

def create_day_night_comparison_plot(day_night_results: Dict, city_name: str, year: int, 
                                    output_dir: Path) -> None:
    """
    Create visualization comparing day vs night SUHI intensities.
    
    Args:
        day_night_results: Results from day/night SUHI analysis
        city_name: Name of the city
        year: Analysis year
        output_dir: Output directory for plots
    """
    if 'error' in day_night_results or 'day' not in day_night_results or 'night' not in day_night_results:
        print(f"     ⚠️ Insufficient data for day/night comparison")
        return
    
    day_data = day_night_results['day']
    night_data = day_night_results['night']
    
    if 'error' in day_data or 'error' in night_data:
        print(f"     ⚠️ Error in day/night data")
        return
    
    # Create comparison plot
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    
    # Day vs Night SUHI comparison
    periods = ['Day', 'Night']
    suhi_values = [day_data.get('suhi', 0), night_data.get('suhi', 0)]
    colors = ['#ff6b6b', '#4ecdc4']
    
    ax1.bar(periods, suhi_values, color=colors, alpha=0.7)
    ax1.set_ylabel('SUHI Intensity (K)')
    ax1.set_title(f'{city_name} Day vs Night SUHI ({year})')
    ax1.grid(True, alpha=0.3)
    
    # Urban temperatures
    urban_temps = [day_data.get('urban_mean', 0), night_data.get('urban_mean', 0)]
    rural_temps = [day_data.get('rural_mean', 0), night_data.get('rural_mean', 0)]
    
    x = np.arange(len(periods))
    width = 0.35
    
    ax2.bar(x - width/2, urban_temps, width, label='Urban', color='#ff6b6b', alpha=0.7)
    ax2.bar(x + width/2, rural_temps, width, label='Rural', color='#4ecdc4', alpha=0.7)
    ax2.set_ylabel('LST (K)')
    ax2.set_title('Urban vs Rural Temperatures')
    ax2.set_xticks(x)
    ax2.set_xticklabels(periods)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Temperature difference analysis
    if 'day_night_difference' in day_night_results:
        diff_data = day_night_results['day_night_difference']
        
        categories = ['SUHI Difference\n(Day-Night)', 'Day Stronger?', 'Magnitude Ratio']
        values = [
            diff_data.get('suhi_difference', 0),
            1 if diff_data.get('day_stronger', False) else 0,
            min(diff_data.get('magnitude_ratio', 0), 10)  # Cap for visualization
        ]
        
        ax3.bar(categories[:1], values[:1], color='#ffa726', alpha=0.7)
        ax3.set_ylabel('Temperature Difference (K)')
        ax3.set_title('Day-Night SUHI Difference')
        ax3.grid(True, alpha=0.3)
        
        # Summary statistics
        stats_text = f"""
        Day SUHI: {day_data.get('suhi', 0):.2f} K
        Night SUHI: {night_data.get('suhi', 0):.2f} K
        Difference: {diff_data.get('suhi_difference', 0):.2f} K
        Day Stronger: {'Yes' if diff_data.get('day_stronger', False) else 'No'}
        """
        
        ax4.text(0.1, 0.5, stats_text, transform=ax4.transAxes, fontsize=10,
                verticalalignment='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        ax4.set_title('Analysis Summary')
        ax4.axis('off')
    
    plt.tight_layout()
    
    # Save plot
    output_file = output_dir / f"{city_name}_day_night_suhi_{year}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"     💾 Day/night comparison saved: {output_file}")

def create_landcover_change_visualization(landcover_data: Dict, city_name: str, 
                                        output_dir: Path) -> None:
    """
    Create visualization of landcover changes over time.
    
    Args:
        landcover_data: Results from ESRI landcover analysis
        city_name: Name of the city
        output_dir: Output directory for plots
    """
    if 'error' in landcover_data or 'yearly_stats' not in landcover_data:
        print(f"     ⚠️ Insufficient data for landcover visualization")
        return
    
    yearly_stats = landcover_data['yearly_stats']
    
    # Filter out error years
    valid_years = {year: data for year, data in yearly_stats.items() 
                   if isinstance(data, dict) and 'error' not in data}
    
    if len(valid_years) < 2:
        print(f"     ⚠️ Insufficient valid years for landcover visualization")
        return
    
    # Extract key landcover classes
    key_classes = ['Built_Area', 'Trees', 'Crops', 'Grass', 'Bare_Ground']
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Time series of key landcover classes
    years = sorted(valid_years.keys())
    for class_name in key_classes:
        areas = []
        for year in years:
            year_data = valid_years[year]
            area = year_data.get(class_name, {}).get('area_km2', 0)
            areas.append(area)
        
        if any(a > 0 for a in areas):  # Only plot if there's data
            ax1.plot(years, areas, marker='o', label=class_name, linewidth=2)
    
    ax1.set_xlabel('Year')
    ax1.set_ylabel('Area (km²)')
    ax1.set_title(f'{city_name} Landcover Changes Over Time')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Landcover change summary (if changes are available)
    if 'landcover_changes' in landcover_data:
        changes = landcover_data['landcover_changes']
        
        class_names = []
        change_values = []
        colors = []
        
        for class_name, change_data in changes.items():
            if isinstance(change_data, dict) and 'change_km2' in change_data:
                change_km2 = change_data['change_km2']
                if abs(change_km2) > 0.1:  # Only show significant changes
                    class_names.append(class_name.replace('_', ' '))
                    change_values.append(change_km2)
                    colors.append('#ff6b6b' if change_km2 > 0 else '#4ecdc4')
        
        if class_names:
            bars = ax2.barh(class_names, change_values, color=colors, alpha=0.7)
            ax2.set_xlabel('Change in Area (km²)')
            ax2.set_title(f'Landcover Changes ({landcover_data.get("analysis_period", "N/A")})')
            ax2.grid(True, alpha=0.3)
            
            # Add value labels on bars
            for bar, value in zip(bars, change_values):
                ax2.text(value + (0.01 * max(abs(v) for v in change_values)), 
                        bar.get_y() + bar.get_height()/2, 
                        f'{value:.1f}', ha='left' if value >= 0 else 'right', 
                        va='center', fontsize=9)
    
    plt.tight_layout()
    
    # Save plot
    output_file = output_dir / f"{city_name}_landcover_changes.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"     💾 Landcover changes visualization saved: {output_file}")

def generate_comprehensive_report(all_results: List[Dict], output_dir: Path) -> None:
    """
    Generate comprehensive report with all new analysis components.
    
    Args:
        all_results: List of all analysis results
        output_dir: Output directory for reports
    """
    report_file = output_dir / "COMPREHENSIVE_SUHI_ANALYSIS_REPORT.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# COMPREHENSIVE SUHI ANALYSIS REPORT\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Cities Analyzed:** {len(set(r['city'] for r in all_results))}\n")
        f.write(f"**Total Analyses:** {len(all_results)}\n\n")
        
        # Summary statistics
        f.write("## ANALYSIS SUMMARY\n\n")
        
        # Group by city
        city_groups = {}
        for result in all_results:
            city = result['city']
            if city not in city_groups:
                city_groups[city] = []
            city_groups[city].append(result)
        
        for city, city_results in city_groups.items():
            f.write(f"### {city}\n\n")
            
            # Basic SUHI statistics
            suhi_values = []
            day_night_ratios = []
            landcover_changes = []
            
            for result in city_results:
                # Extract SUHI values
                if 'suhi_analysis' in result and 'suhi' in result['suhi_analysis']:
                    suhi_values.append(result['suhi_analysis']['suhi'])
                
                # Extract day/night ratios
                if 'day_night_analysis' in result and 'day_night_difference' in result['day_night_analysis']:
                    diff_data = result['day_night_analysis']['day_night_difference']
                    if 'magnitude_ratio' in diff_data:
                        day_night_ratios.append(diff_data['magnitude_ratio'])
                
                # Extract landcover change data
                if 'landcover_changes' in result and 'landcover_changes' in result['landcover_changes']:
                    changes = result['landcover_changes']['landcover_changes']
                    if 'Built_Area' in changes:
                        built_change = changes['Built_Area'].get('change_km2', 0)
                        landcover_changes.append(built_change)
            
            # Write statistics
            if suhi_values:
                f.write(f"- **Average SUHI:** {np.mean(suhi_values):.2f} C (±{np.std(suhi_values):.2f})\n")
                f.write(f"- **SUHI Range:** {min(suhi_values):.2f} - {max(suhi_values):.2f} C\n")
            
            if day_night_ratios:
                valid_ratios = [r for r in day_night_ratios if not np.isinf(r)]
                if valid_ratios:
                    f.write(f"- **Day/Night SUHI Ratio:** {np.mean(valid_ratios):.2f} (±{np.std(valid_ratios):.2f})\n")
            
            if landcover_changes:
                total_change = sum(landcover_changes)
                f.write(f"- **Built Area Change:** {total_change:.2f} km² over analysis period\n")
            
            f.write(f"- **Years Analyzed:** {len(city_results)}\n")
            f.write(f"- **Processing Scale:** {city_results[0].get('processing_scale', 'Unknown')}m\n\n")
        
        # Detailed results
        f.write("## DETAILED RESULTS\n\n")
        
        for result in all_results:
            f.write(f"### {result['city']} - {result['year']}\n\n")
            
            # SUHI Analysis
            if 'suhi_analysis' in result:
                suhi_data = result['suhi_analysis']
                if 'error' not in suhi_data:
                    f.write(f"**SUHI Intensity:** {suhi_data.get('suhi', 'N/A'):.2f} °C\n")
                    f.write(f"**Confidence Interval:** [{suhi_data.get('ci_95_lower', 'N/A'):.2f}, {suhi_data.get('ci_95_upper', 'N/A'):.2f}] °C\n")
                    f.write(f"**Relative Error:** {suhi_data.get('relative_error_pct', 'N/A'):.1f}%\n")
                else:
                    f.write(f"**SUHI Analysis:** Error - {suhi_data.get('error', 'Unknown error')}\n")
            
            # Day/Night Analysis
            if 'day_night_analysis' in result:
                day_night = result['day_night_analysis']
                if 'error' not in day_night and 'day' in day_night and 'night' in day_night:
                    day_suhi = day_night['day'].get('suhi', 0)
                    night_suhi = day_night['night'].get('suhi', 0)
                    f.write(f"**Day SUHI:** {day_suhi:.2f} °C\n")
                    f.write(f"**Night SUHI:** {night_suhi:.2f} °C\n")

                    if 'day_night_difference' in day_night:
                        diff = day_night['day_night_difference']
                        f.write(f"**Day-Night Difference:** {diff.get('suhi_difference', 0):.2f} °C\n")
                        f.write(f"**Day Stronger:** {'Yes' if diff.get('day_stronger', False) else 'No'}\n")
            
            # Landcover Changes
            if 'landcover_changes' in result and 'landcover_changes' in result['landcover_changes']:
                changes = result['landcover_changes']['landcover_changes']
                f.write(f"**Landcover Changes:**\n")
                for lc_class, change_data in changes.items():
                    if isinstance(change_data, dict) and abs(change_data.get('change_km2', 0)) > 0.1:
                        f.write(f"  - {lc_class}: {change_data['change_km2']:.2f} km² ({change_data.get('change_percent', 0):.1f}%)\n")
            
            f.write("\n")
        
        f.write("\n---\n")
        f.write("*Report generated by Enhanced SUHI Analysis System*\n")
    
    print(f"📄 Comprehensive report saved: {report_file}")

def generate_error_report(results: List[Dict], output_dir: Path) -> None:
    """
    Generate comprehensive error report with confidence intervals.
    
    Args:
        results: List of analysis results
        output_dir: Output directory for report
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f'error_report_{timestamp}.md'
    
    with open(report_path, 'w') as f:
        f.write("# SUHI Analysis Error Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Summary Statistics\n\n")
        
        # Create summary table
        f.write("| City | Year | SUHI (°C) | SE | 95% CI | Rel. Error (%) | Urban Pixels | Rural Pixels |\n")
        f.write("|------|------|-----------|----|---------|--------------:|-------------:|-------------:|\n")
        
        for result in results:
            if 'suhi_analysis' in result and 'suhi' in result['suhi_analysis']:
                suhi = result['suhi_analysis']
                f.write(f"| {result['city']} | {result['year']} | "
                       f"{suhi['suhi']:.2f} | {suhi['suhi_se']:.3f} | "
                       f"[{suhi['ci_95_lower']:.2f}, {suhi['ci_95_upper']:.2f}] | "
                       f"{suhi['relative_error_pct']:.1f} | "
                       f"{suhi['urban_pixels']} | {suhi['rural_pixels']} |\n")
        
        f.write("\n## Classification Accuracy\n\n")
        
        for result in results:
            if 'accuracy_assessment' in result:
                f.write(f"### {result['city']} ({result['year']})\n")
                f.write(f"Classifications available: {', '.join(result['classifications_available'])}\n")
                f.write("```json\n")
                f.write(json.dumps(result['accuracy_assessment'], indent=2))
                f.write("\n```\n\n")
    
    print(f"📊 Error report saved to: {report_path}")

def generate_landcover_change_table(city_changes: Dict[str, pd.DataFrame], 
                                   output_dir: Path) -> None:
    """
    Generate land cover change summary table with error percentages.
    
    Args:
        city_changes: Dictionary of city transition matrices
        output_dir: Output directory
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create summary DataFrame
    summary = []
    
    for city, matrix in city_changes.items():
        # Extract key transitions
        if hasattr(matrix, 'attrs'):
            # Calculate total built gain with safe numeric conversion
            built_gain_values = []
            for cls in matrix.index:
                if (cls != 'Built_Area' and cls != 'total_to' and 
                    'Built_Area' in matrix.columns):
                    try:
                        val = matrix.loc[cls, 'Built_Area']
                        val_numeric = pd.to_numeric(val, errors='coerce')
                        if pd.notna(val_numeric):
                            built_gain_values.append(val_numeric)
                    except:
                        continue
            
            total_built_gain = sum(built_gain_values) if built_gain_values else 0.0
            
            summary.append({
                'City': matrix.attrs['city'],
                'Period': f"{matrix.attrs['start_year']}-{matrix.attrs['end_year']}",
                'Accuracy (%)': f"{matrix.attrs['accuracy_pct']:.1f}",
                'Error (%)': f"{matrix.attrs['error_pct']:.1f}",
                'Crops→Built': matrix.loc['Crops', 'Built_Area'] if 'Crops' in matrix.index else 0,
                'Bare→Built': matrix.loc['Bare_Ground', 'Built_Area'] if 'Bare_Ground' in matrix.index else 0,
                'Total Built Gain': total_built_gain
            })
    
    summary_df = pd.DataFrame(summary)
    
    # Save to CSV
    csv_path = output_dir / f'landcover_changes_summary_{timestamp}.csv'
    summary_df.to_csv(csv_path, index=False)
    
    # Save to Excel with full matrices
    excel_path = output_dir / f'landcover_changes_detailed_{timestamp}.xlsx'
    with pd.ExcelWriter(excel_path) as writer:
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        for city, matrix in city_changes.items():
            # Limit sheet name to 31 characters
            sheet_name = city[:31] if len(city) > 31 else city
            matrix.to_excel(writer, sheet_name=sheet_name)
    
    print(f"📊 Land cover change tables saved:")
    print(f"   - Summary: {csv_path}")
    print(f"   - Detailed: {excel_path}")

# ================================================================================
# SECTION 14: MAIN EXECUTION
# ================================================================================

def main():
    """
    Main execution function for comprehensive SUHI analysis.
    """
    print("="*80)
    print("COMPREHENSIVE SURFACE URBAN HEAT ISLAND ANALYSIS FOR UZBEKISTAN")
    print("="*80)
    
    # Initialize GEE
    if not initialize_gee():
        print("\n❌ Cannot proceed without Google Earth Engine access")
        return
    
    # Test dataset availability
    dataset_status = test_dataset_availability()
    
    # Create output directories
    output_dirs = create_output_directories()
    
    # Analysis configuration
    analysis_years = ANALYSIS_CONFIG['years']
    
    # Process cities in batches to avoid memory issues
    all_cities = list(UZBEKISTAN_CITIES.keys())
    
    # For production, process all cities; for testing, limit to 3
    TESTING_MODE = False  # Set to False for full analysis
    if TESTING_MODE:
        cities_to_process = all_cities[:3]  # Only first 3 cities for testing
        print(f"\n⚠️ TESTING MODE: Processing only {len(cities_to_process)} cities")
    else:
        cities_to_process = all_cities
    
    print(f"\n📍 Cities to analyze: {len(cities_to_process)}")
    print(f"📅 Years to analyze: {analysis_years[0]}-{analysis_years[-1]}")
    
    # Store results
    all_results = []
    annual_suhi_trends = []
    
    # Phase 1: Annual ESRI-based temporal analysis
    print("\n" + "="*60)
    print("PHASE 1: ANNUAL ESRI TEMPORAL ANALYSIS (2017-2024)")
    print("="*60)
    
    try:
        temporal_data = create_temporal_expansion_report(cities_to_process, output_dirs['reports'])
        
        if temporal_data.empty:
            print("⚠️ No temporal data collected")
    except Exception as e:
        print(f"❌ Error in Phase 1: {e}")
    
    # Phase 2: Annual SUHI trends
    print("\n" + "="*60)
    print("PHASE 2: ANNUAL SUHI TRENDS WITH ESRI MASKS")
    print("="*60)
    
    esri_years = list(range(2017, 2025))
    
    for city in cities_to_process:
        try:
            # Apply rate limiting
            rate_limiter.wait()
            
            suhi_trends = analyze_annual_suhi_trends(city, esri_years)
            annual_suhi_trends.append(suhi_trends)
            
            # Save individual city SUHI trends
            city_trends_file = output_dirs['data'] / f'{city}_annual_suhi_trends.json'
            with open(city_trends_file, 'w') as f:
                json.dump(suhi_trends, f, indent=2)
            
            print(f"✅ SUHI trends completed for {city}")
            
        except Exception as e:
            print(f"❌ Error analyzing SUHI trends for {city}: {e}")
            continue
    
    # Phase 3: Detailed analysis for key years
    print("\n" + "="*60)
    print("PHASE 3: DETAILED VALIDATION ANALYSIS")
    print("="*60)
    
    # Analyze only 2017 and 2024 for comparison
    validation_years = [2017, 2024]
    
    for city in cities_to_process:
        for year in validation_years:
            try:
                # Apply rate limiting
                rate_limiter.wait()
                
                results = run_comprehensive_analysis(city, year)
                all_results.append(results)
                
                # Save intermediate results
                city_file = output_dirs['data'] / f'{city}_{year}_results.json'
                with open(city_file, 'w') as f:
                    json.dump(results, f, indent=2)
                
                print(f"   ✅ Completed: {city} ({year})")
                
            except Exception as e:
                print(f"   ❌ Error analyzing {city} ({year}): {e}")
                continue
    
    # Generate reports and visualizations
    print("\n📊 Generating reports and visualizations...")
    
    if all_results:
        generate_error_report(all_results, output_dirs['error_analysis'])
        generate_comprehensive_report(all_results, output_dirs['reports'])
        
        # Generate visualizations for each result
        for result in all_results:
            # Generate day/night comparison plots
            if 'day_night_analysis' in result and result['day_night_analysis']:
                try:
                    create_day_night_comparison_plot(
                        result['day_night_analysis'],
                        result['city'],
                        result['year'],
                        output_dirs['visualizations']
                    )
                except Exception as e:
                    print(f"     ⚠️ Error creating day/night plot for {result['city']}: {e}")
            
            # Generate landcover change visualizations - ADDED
            if 'landcover_changes' in result and result['landcover_changes']:
                try:
                    create_landcover_change_visualization(
                        result['landcover_changes'],
                        result['city'],
                        output_dirs['visualizations']
                    )
                    print(f"     ✅ Landcover visualization created for {result['city']}")
                except Exception as e:
                    print(f"     ⚠️ Error creating landcover plot for {result['city']}: {e}")
    
    # Phase 4: Create comparison visualizations across cities - ADDED
    print("\n📊 Creating comparative visualizations...")
    
    # Create a comprehensive landcover change comparison
    if all_results:
        try:
            create_multi_city_landcover_comparison(all_results, output_dirs['visualizations'])
        except Exception as e:
            print(f"   ⚠️ Error creating multi-city comparison: {e}")
    
    # Final summary
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    
    successful_analyses = len([r for r in all_results if r])
    cities_analyzed = len(set([r['city'] for r in all_results if r and 'city' in r]))
    
    print(f"✅ Cities analyzed: {cities_analyzed}")
    print(f"✅ Total analyses: {successful_analyses}")
    print(f"✅ Output directory: {output_dirs['base']}")
    
    if TESTING_MODE:
        print("\n⚠️ TESTING MODE ACTIVE - Set TESTING_MODE=False for full analysis")
    
    print("="*80)

def create_multi_city_landcover_comparison(all_results: List[Dict], output_dir: Path) -> None:
    """
    Create a comparison visualization of landcover changes across multiple cities.
    
    Args:
        all_results: List of all analysis results
        output_dir: Output directory for visualizations
    """
    print("   📊 Creating multi-city landcover comparison...")
    
    # Extract landcover change data for all cities
    city_changes = {}
    
    for result in all_results:
        if 'landcover_changes' not in result or 'error' in result['landcover_changes']:
            continue 
        
        city = result['city']
        year = result['year']
        landcover_data = result['landcover_changes']
        
        if 'landcover_changes' in landcover_data:
            changes = landcover_data['landcover_changes']
            
            # Get Built_Area change specifically
            if 'Built_Area' in changes:
                built_change = changes['Built_Area']
                
                if city not in city_changes:
                    city_changes[city] = {}
                
                city_changes[city][year] = {
                    'built_change_km2': built_change.get('change_km2', 0),
                    'built_change_pct': built_change.get('change_percent', 0),
                    'start_area': built_change.get('start_area_km2', 0),
                    'end_area': built_change.get('end_area_km2', 0),
                    'period': landcover_data.get('analysis_period', 'Unknown')
                }
    
    if not city_changes:
        print("     ⚠️ No landcover change data available for comparison")
        return
    
    # Create comparison plot
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    
    # 1. Built area changes by city
    cities = []
    changes_km2 = []
    periods = []
    
    for city, years_data in city_changes.items():
        for year, data in years_data.items():
            cities.append(f"{city}\n({data['period']})")
            changes_km2.append(data['built_change_km2'])
            periods.append(data['period'])
    
    colors = ['#ff6b6b' if c > 0 else '#4ecdc4' for c in changes_km2]
    bars = ax1.barh(cities, changes_km2, color=colors, alpha=0.7)
    ax1.set_xlabel('Built Area Change (km²)')
    ax1.set_title('Urban Expansion Across Uzbekistan Cities')
    ax1.grid(True, alpha=0.3)
    
    # Add value labels
    for bar, value in zip(bars, changes_km2):
        ax1.text(value + (0.01 * max(abs(v) for v in changes_km2) if changes_km2 else 0), 
                bar.get_y() + bar.get_height()/2, 
                f'{value:.1f}', ha='left' if value >= 0 else 'right', 
                va='center', fontsize=9)
    
    # 2. Percentage changes
    changes_pct = []
    for city, years_data in city_changes.items():
        for year, data in years_data.items():
            changes_pct.append(data['built_change_pct'])
    
    ax2.barh(cities, changes_pct, color=['#ffa726' if c > 0 else '#26a69a' for c in changes_pct], alpha=0.7)
    ax2.set_xlabel('Built Area Change (%)')
    ax2.set_title('Relative Urban Growth Rates')
    ax2.grid(True, alpha=0.3)
    
    # 3. Start vs End areas comparison
    city_names = list(city_changes.keys())
    start_areas = []
    end_areas = []
    
    for city in city_names:
        # Get the most recent year data
        years = list(city_changes[city].keys())
        if years:
            latest_year = max(years)
            start_areas.append(city_changes[city][latest_year]['start_area'])
            end_areas.append(city_changes[city][latest_year]['end_area'])
    
    x = np.arange(len(city_names))
    width = 0.35
    
    bars1 = ax3.bar(x - width/2, start_areas, width, label='Start Period', color='#3498db', alpha=0.7)
    bars2 = ax3.bar(x + width/2, end_areas, width, label='End Period', color='#e74c3c', alpha=0.7)
    
    ax3.set_ylabel('Built Area (km²)')
    ax3.set_title('Built Area: Before vs After')
    ax3.set_xticks(x)
    ax3.set_xticklabels(city_names, rotation=45, ha='right')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. Summary statistics table
    summary_text = "LANDCOVER CHANGE SUMMARY\n" + "="*30 + "\n\n"
    
    total_expansion = sum(changes_km2)
    avg_expansion = np.mean(changes_km2) if changes_km2 else 0
    max_expansion_idx = np.argmax(np.abs(changes_km2)) if changes_km2 else 0
    max_expansion_city = cities[max_expansion_idx].split('\n')[0] if cities else 'N/A'
    
    summary_text += f"Total Built Area Change: {total_expansion:.2f} km²\n"
    summary_text += f"Average Change per City: {avg_expansion:.2f} km²\n"
    summary_text += f"Largest Change: {max_expansion_city}\n"
    summary_text += f"Cities Analyzed: {len(city_names)}\n"
    
    ax4.text(0.1, 0.5, summary_text, transform=ax4.transAxes, fontsize=11,
            verticalalignment='center', 
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    ax4.set_title('Analysis Summary')
    ax4.axis('off')
    
    plt.suptitle('Uzbekistan Urban Landcover Changes - Comparative Analysis', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    # Save plot
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"multi_city_landcover_comparison_{timestamp}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"     💾 Multi-city comparison saved: {output_file}")

if __name__ == "__main__":
    main()