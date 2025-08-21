"""
Configuration management for Uzbekistan Urban Research Project
"""

from typing import Dict, List, Union
from pathlib import Path

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

# Analysis parameters - now configurable
class AnalysisConfig:
    def __init__(self, 
                 years: List[int] = None,
                 resolution_m: int = 500,
                 testing_mode: bool = False,
                 test_cities_count: int = 3):
        
        self.years = years or list(range(2017, 2025))  # 2017-2024
        self.warm_months = [6, 7, 8]  # June-August for peak SUHI
        self.resolution_m = resolution_m  # User-configurable resolution
        self.testing_mode = testing_mode
        self.test_cities_count = test_cities_count
        
        # Analysis parameters
        self.esri_weight = 0.5  # ESRI classification weight (50%)
        self.rural_buffer_km = 25  # Rural reference ring distance
        self.min_urban_pixels = 10  # Minimum pixels for valid urban area
        self.min_rural_pixels = 25  # Minimum pixels for valid rural area
        self.cloud_threshold = 20  # Maximum cloud cover percentage
        self.water_occurrence_threshold = 25  # JRC water occurrence threshold
    
    def get_cities_to_process(self) -> List[str]:
        """Get list of cities to process based on configuration"""
        all_cities = list(UZBEKISTAN_CITIES.keys())
        if self.testing_mode:
            return all_cities[:self.test_cities_count]
        return all_cities

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

# Google Earth Engine computation limits - configurable by resolution
class GEEConfig:
    def __init__(self, resolution_m: int = 500):
        self.resolution_m = resolution_m
        
        # Adjust scales based on resolution
        if resolution_m >= 500:
            self.max_pixels = 1e9
            self.scale = resolution_m
            self.scale_modis = 1000
            self.scale_landsat = max(30, resolution_m)
        elif resolution_m >= 100:
            self.max_pixels = 5e8
            self.scale = resolution_m
            self.scale_modis = 1000
            self.scale_landsat = max(30, resolution_m)
        else:
            self.max_pixels = 1e8
            self.scale = max(10, resolution_m)
            self.scale_modis = 1000
            self.scale_landsat = 30
            
        self.best_effort = True

# ESRI Landcover Classification Classes
ESRI_CLASSES = {
    1: "Water",
    2: "Trees", 
    3: "Grass",
    4: "Flooded_Vegetation",
    5: "Crops",
    6: "Scrub_Shrub",
    7: "Built",
    8: "Bare",
    9: "Snow_Ice",
    10: "Clouds",
    11: "Rangeland"
}

def get_default_config(resolution_m: int = 500, testing_mode: bool = False) -> tuple:
    """Get default configuration for analysis"""
    analysis_config = AnalysisConfig(
        resolution_m=resolution_m,
        testing_mode=testing_mode
    )
    gee_config = GEEConfig(resolution_m=resolution_m)
    
    return analysis_config, gee_config