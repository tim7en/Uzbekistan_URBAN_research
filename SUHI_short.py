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
    "years": list(range(2016, 2025)),  # 2016-2024
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
    "max_pixels": 1e9,  # Maximum pixels for reduceRegion operations
    "scale": 10,        # Default scale for high-resolution data (ESRI)
    "scale_modis": 1000, # Scale for MODIS data
    "scale_landsat": 30, # Scale for Landsat data
    "best_effort": True, # Use bestEffort for large computations
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

# Land cover class definitions
ESRI_CLASSES = {
    1: 'Water',
    2: 'Trees',
    4: 'Flooded_vegetation',
    5: 'Crops',
    7: 'Built_area',  # Urban class
    8: 'Bare_ground',
    9: 'Snow_ice',
    10: 'Clouds',
    11: 'Rangeland'
}

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
        
        # Create date range for the year
        start_date = ee.Date.fromYMD(year, 1, 1)
        end_date = ee.Date.fromYMD(year, 12, 31)
        
        # Filter by date and create composite
        year_composite = (esri_lulc_ts
                         .filterDate(start_date, end_date)
                         .filterBounds(geometry)
                         .mosaic())  # Use mosaic() instead of first()
        
        # Check if we got any data
        pixel_count = year_composite.select([0]).reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=geometry,
            scale=100,
            maxPixels=1e6
        )
        
        count = pixel_count.getInfo()
        if not count or list(count.values())[0] == 0:
            print(f"   ❌ No ESRI data found for year {year}")
            return None
        
        # The ESRI data has values 1-11 as per the remapping in JS example
        # No need to select band by name, it's already a single band
        clipped_image = year_composite.clip(geometry)
        
        print(f"   ✅ ESRI {year} loaded successfully")
        return clipped_image
        
    except Exception as e:
        print(f"   ❌ Error loading ESRI classification for year {year}: {e}")
        return None


def load_all_classifications(year: int, geometry: ee.Geometry, 
                           start_date: str, end_date: str) -> Dict[str, ee.Image]:
    """
    Load all available urban classification datasets.
    
    Args:
        year: Target year
        geometry: Area of interest
        start_date: Start date for temporal filtering
        end_date: End date for temporal filtering
        
    Returns:
        Dictionary of classification images
    """
    classifications = {}
    
    # 1. ESRI Global LULC (10m) - Primary classification
    try:
        esri = load_esri_classification(year, geometry)
        if esri is not None:
            # Extract built area (class 7 according to the JS example)
            # Built Area is value 7 in original, 5 in remapped
            classifications['esri'] = esri.eq(7).rename('esri_built')
            print("   ✅ ESRI classification loaded")
    except Exception as e:
        print(f"   ⚠️ ESRI unavailable: {e}")
    
    # 2. Dynamic World (10m) - Built probability
    try:
        dw = (ee.ImageCollection(DATASETS["dynamic_world"])
              .filterDate(start_date, end_date)
              .filterBounds(geometry)
              .select('built')
              .median())
        classifications['dynamic_world'] = dw.rename('dw_built')
        print("   ✅ Dynamic World loaded")
    except Exception as e:
        print(f"   ⚠️ Dynamic World unavailable: {e}")
    
    # 3. Global Human Settlement Layer (10m)
    try:
        ghsl = ee.Image(DATASETS["ghsl"]).select('built_surface')
        # Normalize to 0-1 range
        classifications['ghsl'] = ghsl.divide(100).rename('ghsl_built').clip(geometry)
        print("   ✅ GHSL loaded")
    except Exception as e:
        print(f"   ⚠️ GHSL unavailable: {e}")
    
    # 4. ESA WorldCover (10m)
    try:
        esa = ee.Image(DATASETS["esa_worldcover"]).select('Map')
        # Built-up class is 50
        classifications['esa'] = esa.eq(50).rename('esa_built').clip(geometry)
        print("   ✅ ESA WorldCover loaded")
    except Exception as e:
        print(f"   ⚠️ ESA WorldCover unavailable: {e}")
    
    # 5. MODIS Land Cover (500m) - Coarse resolution fallback
    try:
        modis_lc = (ee.ImageCollection(DATASETS["modis_lc"])
                   .filterDate(f'{year}-01-01', f'{year+1}-01-01')
                   .first()
                   .select('LC_Type1'))
        # Urban class is 13
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
        stack = ee.Image.cat(list(classifications.values()))
        reference = stack.reduce(ee.Reducer.mode())
    
    # Calculate agreement metrics
    metrics = {}
    for name, classification in classifications.items():
        if name != 'esri':
            # Calculate confusion matrix elements
            agreement = classification.eq(reference)
            metrics[f'{name}_agreement'] = agreement.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=GEE_CONFIG['scale'],
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=GEE_CONFIG['best_effort']
            )
    
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
    lst_day = comp.select('LST_Day_1km').multiply(0.02).subtract(273.15).rename('LST_Day_MODIS').clamp(-20, 60)
    lst_night = comp.select('LST_Night_1km').multiply(0.02).subtract(273.15).rename('LST_Night_MODIS').clamp(-20, 50)
    return ee.Image.cat([lst_day, lst_night]).clip(geometry)


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
                                geometry: ee.Geometry) -> ee.Image:
    """
    Calculate vegetation indices from Landsat 8/9.
    
    Args:
        start_date: Start date
        end_date: End date
        geometry: Area of interest
        
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
        
        return ee.Image.cat([ndvi, ndbi, ndwi]).updateMask(mask)
    
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

def compute_pixel_suhi(urban_mask, rural_mask, lst_image):
    band = lst_image.bandNames().get(0)  # assume single band or take 'LST_Day_MODIS'
    stats = lst_image.updateMask(rural_mask).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=rural_mask.geometry(),
        scale=ANALYSIS_CONFIG['target_resolution_m'],
        maxPixels=GEE_CONFIG['max_pixels'],
        bestEffort=GEE_CONFIG['best_effort']
    )
    rural_mean = ee.Number(stats.get(ee.String(band)))  # extract number
    rural_reference = ee.Image.constant(rural_mean).rename('rural_mean').toFloat()
    suhi = lst_image.select([ee.String(band)]).toFloat().subtract(rural_reference).updateMask(urban_mask)
    return suhi.rename('SUHI_pixel')

def compute_zonal_suhi(zones: Dict[str, ee.Geometry], lst_image: ee.Image,
                       classifications: Dict[str, ee.Image]) -> Dict[str, Any]:
    # consensus urban mask (guarded weighting)
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

    # choose scale by dataset
    band = 'LST_Day_MODIS'
    scale = GEE_CONFIG['scale_modis']  # Use MODIS scale (1000m)

    # build reducer once
    base_reducer = (ee.Reducer.mean()
                    .combine(ee.Reducer.stdDev(), sharedInputs=True)
                    .combine(ee.Reducer.count(), sharedInputs=True))

    urban_stats = (lst_image.select(band)
        .updateMask(urban_mask)
        .reduceRegion(
            reducer=base_reducer,
            geometry=zones['urban_core'],
            scale=scale,
            maxPixels=GEE_CONFIG['max_pixels'],
            bestEffort=GEE_CONFIG['best_effort']
        ))

    rural_stats = (lst_image.select(band)
        .updateMask(rural_mask)
        .reduceRegion(
            reducer=base_reducer,
            geometry=zones['rural_ring'],
            scale=scale,
            maxPixels=GEE_CONFIG['max_pixels'],
            bestEffort=GEE_CONFIG['best_effort']
        ))

    return {'urban_stats': urban_stats.getInfo(), 'rural_stats': rural_stats.getInfo()}


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
            
            # Extract built area (class 7) - no need to select band
            built_mask = esri_image.eq(7)
            
            # Calculate total built area
            pixel_area = ee.Image.pixelArea()
            total_built_area = built_mask.multiply(pixel_area).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=zones['urban_core'],
                scale=GEE_CONFIG['scale'],
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=GEE_CONFIG['best_effort']
            )
            
            # Calculate built area in extended region for sprawl analysis
            extended_built_area = built_mask.multiply(pixel_area).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=zones['full_extent'],
                scale=GEE_CONFIG['scale'],
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=GEE_CONFIG['best_effort']
            )
            
            # Calculate urban density (built pixels / total pixels)
            total_pixels = zones['urban_core'].area().divide(100)  # 10m pixels
            built_pixels = built_mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=zones['urban_core'],
                scale=GEE_CONFIG['scale'],
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=GEE_CONFIG['best_effort']
            )
            
            # Get computed values with error handling
            try:
                # For single band images, the key is usually 'constant' or the first key
                area_keys = total_built_area.getInfo().keys()
                area_key = list(area_keys)[0] if area_keys else None
                
                if area_key:
                    built_area_km2 = total_built_area.get(area_key)
                    built_area_km2 = ee.Number(built_area_km2).divide(1e6).getInfo()
                    
                    extended_area_km2 = extended_built_area.get(area_key)
                    extended_area_km2 = ee.Number(extended_area_km2).divide(1e6).getInfo() if extended_area_km2 else 0
                    
                    built_pixel_count = built_pixels.get(area_key)
                    built_pixel_count = ee.Number(built_pixel_count).getInfo() if built_pixel_count else 0
                else:
                    print(f"     ❌ Error processing {year}: No data in reduction result")
                    continue
                
                total_pixel_count = total_pixels.getInfo()
                
                urban_density = (built_pixel_count / total_pixel_count * 100) if total_pixel_count > 0 else 0
                
                annual_data.append({
                    'city': city_name,
                    'year': year,
                    'built_area_core_km2': built_area_km2,
                    'built_area_extended_km2': extended_area_km2,
                    'built_pixels': built_pixel_count,
                    'urban_density_pct': urban_density,
                    'analysis_area_km2': total_pixel_count / 10000,  # Convert to km2
                })
                
                print(f"     ✅ {year}: {built_area_km2:.2f} km² built area")
                
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
        df['annual_growth_km2'] = df['built_area_core_km2'].diff()
        df['annual_growth_pct'] = df['built_area_core_km2'].pct_change() * 100
        df['density_change_pct'] = df['urban_density_pct'].diff()
        
        # Calculate cumulative growth from baseline
        baseline_area = df['built_area_core_km2'].iloc[0]
        df['cumulative_growth_km2'] = df['built_area_core_km2'] - baseline_area
        df['cumulative_growth_pct'] = (df['built_area_core_km2'] / baseline_area - 1) * 100
    
    return df
def analyze_annual_suhi_trends(city_name: str, years: List[int]) -> Dict:
    """
    Analyze SUHI trends using year-specific ESRI urban masks.
    
    Args:
        city_name: Name of the city
        years: List of years to analyze
        
    Returns:
        Dictionary with annual SUHI trends and statistics
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
                
            built_mask = esri_image.eq(7)
            
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
                    'rural_pixels': rural_count
                })
                
                print(f"     ✅ {year}: SUHI = {suhi:.2f}°C")
            
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
                'built_area_core_km2': ['first', 'last', 'mean'],
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
    
    Args:
        city_name: Name of the city
        start_year: Baseline year
        end_year: Target year
        
    Returns:
        Urban expansion statistics
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
    
    # Get band names for area calculations
    start_band = esri_start.bandNames().getInfo()[0]
    end_band = esri_end.bandNames().getInfo()[0]
    
    # Extract built area
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
    
    # Calculate expansion using the correct band names
    area_start_km2 = ee.Number(area_start.get(start_band)).divide(1e6)
    area_end_km2 = ee.Number(area_end.get(end_band)).divide(1e6)
    expansion_km2 = area_end_km2.subtract(area_start_km2)
    expansion_pct = expansion_km2.divide(area_start_km2).multiply(100)
    
    return {
        'city': city_name,
        'start_year': start_year,
        'end_year': end_year,
        'area_start_km2': area_start_km2.getInfo(),
        'area_end_km2': area_end_km2.getInfo(),
        'expansion_km2': expansion_km2.getInfo(),
        'expansion_pct': expansion_pct.getInfo()
    }

# ================================================================================
# SECTION 11: LANDCOVER CHANGE ANALYSIS
# ================================================================================

def analyze_landcover_changes(city_name: str, start_year: int, end_year: int) -> pd.DataFrame:
    """
    Analyze land cover changes with transition matrix and error estimation.
    
    Args:
        city_name: Name of the city
        start_year: Baseline year
        end_year: Target year
        
    Returns:
        DataFrame with land cover change statistics
    """
    city_info = UZBEKISTAN_CITIES[city_name]
    zones = create_analysis_zones(city_info)
    
    # Load ESRI classifications
    esri_start = load_esri_classification(start_year, zones['urban_core'])
    esri_end = load_esri_classification(end_year, zones['urban_core'])
    
    # Calculate transition matrix
    results = []
    
    for from_class, from_name in ESRI_CLASSES.items():
        for to_class, to_name in ESRI_CLASSES.items():
            # Create transition mask
            transition = esri_start.eq(from_class).And(esri_end.eq(to_class))
            
            # Calculate area
            area = transition.multiply(ee.Image.pixelArea()).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=zones['urban_core'],
                scale=GEE_CONFIG['scale'],
                maxPixels=GEE_CONFIG['max_pixels'],
                bestEffort=GEE_CONFIG['best_effort']
            )
            
            # Get the area value using the correct band name
            band_names = esri_start.bandNames().getInfo()
            if len(band_names) > 0:
                area_band = band_names[0]
                area_km2 = ee.Number(area.get(area_band)).divide(1e6).getInfo()
            else:
                area_km2 = 0
            
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
    Run complete SUHI analysis for a city and year.
    
    Args:
        city_name: Name of the city
        year: Analysis year
        
    Returns:
        Comprehensive analysis results
    """
    print(f"\n🔍 Analyzing {city_name} for {year}")
    
    city_info = UZBEKISTAN_CITIES[city_name]
    zones = create_analysis_zones(city_info)
    
    # Define date range
    start_date = f'{year}-01-01'
    end_date = f'{year}-12-31'
    
    # Step 1: Load all classifications
    print("   📊 Loading classification datasets...")
    classifications = load_all_classifications(year, zones['full_extent'], 
                                              start_date, end_date)
    
    # Step 2: Assess classification accuracy
    print("   🎯 Assessing classification accuracy...")
    accuracy_metrics = assess_classification_accuracy(classifications, zones['urban_core'])
    
    # Step 3: Load temperature data
    print("   🌡️ Loading temperature data...")
    modis_lst = load_modis_lst(start_date, end_date, zones['full_extent'])
    landsat_lst = load_landsat_thermal(start_date, end_date, zones['full_extent'])
    aster_lst = load_aster_lst(start_date, end_date, zones['full_extent'])
    
    # Combine temperature sources
    temp_sources = [modis_lst]
    if isinstance(landsat_lst, ee.image.Image):
        temp_sources.append(landsat_lst)
    if aster_lst is not None and isinstance(aster_lst, ee.image.Image):
        temp_sources.append(aster_lst)
    combined_lst = ee.Image.cat(temp_sources)
    
    # Step 4: Calculate vegetation indices
    print("   🌱 Calculating vegetation indices...")
    vegetation = calculate_vegetation_indices(start_date, end_date, zones['full_extent'])
    
    # Step 5: Compute SUHI with zonal statistics
    print("   🔥 Computing SUHI...")
    suhi_stats = compute_zonal_suhi(zones, modis_lst, classifications)
    
    # Step 6: Calculate error metrics
    print("   📈 Calculating error metrics...")
    error_metrics = calculate_error_metrics(suhi_stats['urban_stats'], 
                                           suhi_stats['rural_stats'])
    
    # Step 7: Extract vegetation statistics
    if vegetation is not None:
        veg_stats = vegetation.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=zones['urban_core'],
            scale=GEE_CONFIG['scale_landsat'],
            maxPixels=GEE_CONFIG['max_pixels'],
            bestEffort=GEE_CONFIG['best_effort']
        ).getInfo()
    else:
        veg_stats = {}
    
    # Compile results
    results = {
        'city': city_name,
        'year': year,
        'classifications_available': list(classifications.keys()),
        'accuracy_assessment': accuracy_metrics.getInfo() if accuracy_metrics else {},
        'suhi_analysis': error_metrics,
        'vegetation_indices': veg_stats,
        'urban_stats': suhi_stats['urban_stats'],
        'rural_stats': suhi_stats['rural_stats']
    }
    
    return results

# ================================================================================
# SECTION 13: REPORTING AND VISUALIZATION
# ================================================================================

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
                if (cls != 'Built_area' and cls != 'total_to' and 
                    'Built_area' in matrix.columns):
                    try:
                        val = matrix.loc[cls, 'Built_area']
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
                'Crops→Built': matrix.loc['Crops', 'Built_area'] if 'Crops' in matrix.index else 0,
                'Bare→Built': matrix.loc['Bare_ground', 'Built_area'] if 'Bare_ground' in matrix.index else 0,
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
        print("Please run the following in a Python shell to authenticate:")
        print("   import ee")
        print("   ee.Authenticate()")
        print("   ee.Initialize(project='your-project-id')")
        return
    
    # Test dataset availability
    dataset_status = test_dataset_availability()
    
    if not dataset_status.get('esri_lulc', False):
        print("\n⚠️ ESRI Global LULC dataset not available!")
        print("   This is required for temporal analysis")
        print("   Proceeding with available datasets only...")
    
    # Create output directories
    output_dirs = create_output_directories()
    
    # Analysis configuration
    analysis_years = ANALYSIS_CONFIG['years']
    cities = list(UZBEKISTAN_CITIES.keys())
    
    print(f"\n📍 Cities to analyze: {len(cities)}")
    print(f"📅 Years to analyze: {analysis_years[0]}-{analysis_years[-1]}")
    print(f"📅 ESRI annual data: 2017-2024 (year-by-year analysis)")
    print(f"🎯 Target resolution: {ANALYSIS_CONFIG['target_resolution_m']}m")
    print(f"⚖️ ESRI classification weight: {ANALYSIS_CONFIG['esri_weight']*100}%")
    
    # Store results
    all_results = []
    landcover_changes = {}
    expansion_results = []
    annual_suhi_trends = []
    
    # Phase 1: Annual ESRI-based temporal analysis (2017-2024)
    print("\n" + "="*60)
    print("PHASE 1: ANNUAL ESRI TEMPORAL ANALYSIS (2017-2024)")
    print("="*60)
    
    try:
        # Create comprehensive temporal expansion report
        temporal_data = create_temporal_expansion_report(cities[:3], output_dirs['reports'])  # Limit for testing
        
        if temporal_data.empty:
            print("⚠️ No temporal data collected - checking GEE connection issues")
            print("   This might be due to:")
            print("   - ESRI dataset unavailable or changed")
            print("   - Network connectivity issues")
            print("   - Google Earth Engine quota limits")
            print("   - Authentication problems")
        
    except Exception as e:
        print(f"❌ Error in Phase 1: {e}")
        print("   Continuing to Phase 2...")
    
    # Phase 2: Annual SUHI trends using year-specific ESRI masks
    print("\n" + "="*60)
    print("PHASE 2: ANNUAL SUHI TRENDS WITH ESRI MASKS")
    print("="*60)
    
    esri_years = list(range(2017, 2025))  # 2017-2024 where ESRI data is available
    
    for city in cities[:3]:  # Limit to first 3 cities for testing
        try:
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
    
    # Phase 3: Detailed analysis for specific years (for validation)
    print("\n" + "="*60)
    print("PHASE 3: DETAILED VALIDATION ANALYSIS")
    print("="*60)
    
    # Run analysis for each city and year
    for city in cities[:2]:  # Limit to first 2 cities for testing
        for year in [2019, 2024]:  # Analyze 2019 and 2024 for comparison
            try:
                # Run comprehensive analysis
                results = run_comprehensive_analysis(city, year)
                all_results.append(results)
                
                # Save intermediate results
                city_file = output_dirs['data'] / f'{city}_{year}_results.json'
                with open(city_file, 'w') as f:
                    json.dump(results, f, indent=2)
                
                print(f"   ✅ Completed: {city} ({year})")
                
                # Add delay to avoid rate limits
                time.sleep(2)
                
            except Exception as e:
                print(f"   ❌ Error analyzing {city} ({year}): {e}")
                continue
        
        # Analyze urban expansion (2019-2024) - This is now supplemented by annual data
        try:
            expansion = analyze_urban_expansion(city, 2019, 2024)
            expansion_results.append(expansion)
            print(f"   📈 Urban expansion {city}: {expansion['expansion_km2']:.2f} km²")
        except Exception as e:
            print(f"   ❌ Error analyzing expansion for {city}: {e}")
        
        # Analyze land cover changes
        try:
            lc_changes = analyze_landcover_changes(city, 2019, 2024)
            landcover_changes[city] = lc_changes
            print(f"   🗺️ Land cover change accuracy {city}: {lc_changes.attrs['accuracy_pct']:.1f}%")
        except Exception as e:
            print(f"   ❌ Error analyzing land cover for {city}: {e}")
    
    # Generate reports
    print("\n📊 Generating comprehensive reports...")
    
    # Error report
    if all_results:
        generate_error_report(all_results, output_dirs['error_analysis'])
    else:
        print("   ⚠️ No results available for error report")
    
    # Land cover change tables
    if landcover_changes:
        generate_landcover_change_table(landcover_changes, output_dirs['reports'])
    else:
        print("   ⚠️ No land cover changes data available")
    
    # Save expansion results (both traditional and annual)
    if expansion_results:
        expansion_df = pd.DataFrame(expansion_results)
        expansion_path = output_dirs['reports'] / 'urban_expansion_summary.csv'
        expansion_df.to_csv(expansion_path, index=False)
        print(f"📊 Urban expansion summary saved to: {expansion_path}")
    else:
        print("   ⚠️ No expansion results available")
    
    # Save annual SUHI trends
    if annual_suhi_trends:
        trends_file = output_dirs['reports'] / 'annual_suhi_trends_summary.json'
        with open(trends_file, 'w') as f:
            json.dump(annual_suhi_trends, f, indent=2)
        print(f"📊 Annual SUHI trends saved to: {trends_file}")
        
        # Create SUHI trends CSV for easier analysis
        suhi_trend_data = []
        for city_trends in annual_suhi_trends:
            for record in city_trends.get('data', []):
                suhi_trend_data.append(record)
        
        if suhi_trend_data:
            suhi_df = pd.DataFrame(suhi_trend_data)
            suhi_csv = output_dirs['reports'] / 'annual_suhi_data.csv'
            suhi_df.to_csv(suhi_csv, index=False)
            print(f"📊 Annual SUHI data CSV saved to: {suhi_csv}")
        else:
            print("   ⚠️ No SUHI trend data to save")
    else:
        print("   ⚠️ No SUHI trends data available")
    
    # Final summary with enhanced temporal analysis
    print("\n" + "="*80)
    print("COMPREHENSIVE ANALYSIS COMPLETE")
    print("="*80)
    
    successful_analyses = len([r for r in all_results if r])
    cities_analyzed = len(set([r['city'] for r in all_results if r and 'city' in r]))
    
    print(f"✅ Cities analyzed: {cities_analyzed}")
    print(f"✅ Total analyses: {successful_analyses}")
    print(f"✅ Annual ESRI temporal data: 2017-2024 (8 years)")
    print(f"✅ SUHI trend analyses: {len(annual_suhi_trends)} cities")
    print(f"✅ Output directory: {output_dirs['base']}")
    
    if successful_analyses > 0:
        print("\n📈 Key Improvements with Annual ESRI Data:")
        print("   • Year-by-year urban expansion tracking (2017-2024)")
        print("   • Annual SUHI trends with evolving urban masks")
        print("   • Improved temporal resolution for change detection")
        print("   • Enhanced accuracy with year-specific classifications")
    else:
        print("\n⚠️ Analysis completed with limited success")
        print("   Please check GEE authentication and dataset availability")
    
    print("="*80)

if __name__ == "__main__":
    main()