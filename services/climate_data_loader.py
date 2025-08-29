"""
Climate data loading service for IPCC AR6 assessment
Handles loading and preprocessing of urban climate data from various sources
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class CityPopulationData:
    """Population and socioeconomic data for a city"""
    city: str
    population_2024: Optional[int] = None
    density_per_km2: Optional[float] = None
    gdp_per_capita_usd: Optional[float] = None
    urban_area_km2: Optional[float] = None
    
    def __post_init__(self):
        # Default population estimates for Uzbekistan cities (2024 estimates)
        default_populations = {
            'Tashkent': 3000000, 'Samarkand': 550000, 'Namangan': 500000,
            'Andijan': 450000, 'Nukus': 350000, 'Bukhara': 320000,
            'Fergana': 300000, 'Qarshi': 280000, 'Kokand': 250000,
            'Margilan': 220000, 'Urgench': 200000, 'Jizzakh': 180000,
            'Termez': 170000, 'Navoiy': 150000, 'Gulistan': 120000,
            'Nurafshon': 100000
        }
        
        # Default GDP estimates (lower-middle income country, urban premium)
        default_gdp = {
            'Tashkent': 3500, 'Samarkand': 2200, 'Namangan': 2000,
            'Andijan': 2100, 'Nukus': 1800, 'Bukhara': 2400,
            'Fergana': 2000, 'Qarshi': 2300, 'Kokand': 1900,
            'Margilan': 1850, 'Urgench': 2100, 'Jizzakh': 1950,
            'Termez': 2200, 'Navoiy': 2800, 'Gulistan': 1800,
            'Nurafshon': 2600
        }
        
        if not self.population_2024:
            self.population_2024 = default_populations.get(self.city, 100000)
        if not self.gdp_per_capita_usd:
            self.gdp_per_capita_usd = default_gdp.get(self.city, 2000)
        if not self.density_per_km2:
            # Estimate density based on population (typical Central Asian urban density)
            self.density_per_km2 = max(1000, self.population_2024 / 50)  # persons/km²


# --- Region GRP per capita (2024) in USD (from official-sourced summary) ---
REGION_GRP_PC_USD_2024 = {
    "Tashkent City": 7223.0,
    "Tashkent Region": 3757.0,
    "Navoi Region": 8545.0,
    "Samarkand Region": 1856.0,
    "Fergana Region": 1759.0,
    "Andijan Region": 2087.0,
    "KashKadarya Region": 1771.0,
    "Bukhara Region": 2745.0,
    "Namangan Region": 1758.0,
    "Surkhandarya Region": 1476.0,
    "Khorezm Region": 2012.0,
    "Republic of Karakalpakstan": 1790.0,
    "Jizzakh Region": 2235.0,
    "Syrdarya Region": 2400.0,
}

# --- Populations for weighting (1 Jan 2024 official releases) ---
TASHKENT_CITY_POP_2024 = 3040800
TASHKENT_REGION_POP_2024 = 3051800

# Weighted GRP per capita for "Tashkent" (reflecting strong coupling with region)
_t_city = REGION_GRP_PC_USD_2024.get("Tashkent City", None)
_t_region = REGION_GRP_PC_USD_2024.get("Tashkent Region", None)
if _t_city is not None and _t_region is not None:
    TASHKENT_WEIGHTED_GRP_PC_USD_2024 = (
        _t_city * TASHKENT_CITY_POP_2024 + _t_region * TASHKENT_REGION_POP_2024
    ) / (TASHKENT_CITY_POP_2024 + TASHKENT_REGION_POP_2024)
else:
    TASHKENT_WEIGHTED_GRP_PC_USD_2024 = None

# Map each city to its region (viloyat) for GRP lookups
CITY_TO_REGION = {
    "Tashkent": "SPECIAL_TASHKENT",
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
    "Nurafshon": "Tashkent Region",
}

# Base city data with actual GDP per capita from official data
UZBEK_CITIES_DATA = {
    "Tashkent":   {"pop_2024": 3058400, "area_km2": 450.0,  "gdp_per_capita": 3323.1},
    "Samarkand":  {"pop_2024": 585200,  "area_km2": 110.6,  "gdp_per_capita": 883.9},
    "Bukhara":    {"pop_2024": 269500,  "area_km2": 104.7,  "gdp_per_capita": 1135.5},
    "Andijan":    {"pop_2024": 480800,  "area_km2": 96.86,  "gdp_per_capita": 917.8},
    "Namangan":   {"pop_2024": 696500,  "area_km2": 168.8,  "gdp_per_capita": 745.6},
    "Fergana":    {"pop_2024": 321800,  "area_km2": 101.9,  "gdp_per_capita": 810.2},
    "Nukus":      {"pop_2024": 339200,  "area_km2": 215.7,  "gdp_per_capita": 865.4},
    "Urgench":    {"pop_2024": 153100,  "area_km2": 38.14,  "gdp_per_capita": 823.9},
    "Termez":     {"pop_2024": 201600,  "area_km2": 49.50,  "gdp_per_capita": 633.9},
    "Qarshi":     {"pop_2024": 295600,  "area_km2": 75.92,  "gdp_per_capita": 787.3},
    "Jizzakh":    {"pop_2024": 195800,  "area_km2": 55.41,  "gdp_per_capita": 948.0},
    "Navoiy":     {"pop_2024": 161300,  "area_km2": 52.82,  "gdp_per_capita": 4816.3},
    "Gulistan":   {"pop_2024": 77300,   "area_km2": 31.62,  "gdp_per_capita": 1112.6},
    "Nurafshon":  {"pop_2024": 56200,   "area_km2": 10.66,  "gdp_per_capita": 1972.3},
}

class ClimateDataLoader:
    """Service for loading and preprocessing climate assessment data"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.suhi_data = {}
        self.lulc_data = []
        self.spatial_data = {}
        self.nightlights_data = []
        self.temperature_data = {}
        self.population_data = {}
        self._cache = {}
        
    def load_all_data(self) -> Dict[str, Any]:
        """Load all available urban analysis data and return summary"""
        print("Loading urban climate data for risk assessment...")
        
        # Load each data type
        self._load_temperature_data()
        self._load_suhi_data()
        self._load_lulc_data()
        self._load_spatial_data()
        self._load_nightlights_data()
        self._initialize_population_data()
        self._initialize_data_cache()
        
        return {
            'temperature_data': self.temperature_data,
            'suhi_data': self.suhi_data,
            'lulc_data': self.lulc_data,
            'spatial_data': self.spatial_data,
            'nightlights_data': self.nightlights_data,
            'population_data': self.population_data,
            'cache': self._cache
        }
    
    def _load_temperature_data(self):
        """Load temperature statistics data (preferred over SUHI for detailed analysis)"""
        self.temperature_data = {}
        temp_dir = self.base_path / "temperature"
        
        if temp_dir.exists():
            for city_dir in temp_dir.iterdir():
                if city_dir.is_dir():
                    city_name = city_dir.name
                    self.temperature_data[city_name] = {}
                    
                    # Load all years for this city
                    for temp_file in city_dir.glob("*_temperature_stats_*.json"):
                        year_match = temp_file.stem.split('_')[-1]
                        try:
                            year = int(year_match)
                            with open(temp_file, 'r') as f:
                                self.temperature_data[city_name][year] = json.load(f)
                        except (ValueError, json.JSONDecodeError) as e:
                            print(f"Warning: Could not load {temp_file}: {e}")
            
            print(f"[OK] Loaded temperature data for {len(self.temperature_data)} cities")
    
    def _load_suhi_data(self):
        """Load SUHI data as fallback"""
        suhi_file = self.base_path / "reports" / "suhi_batch_summary.json"
        if suhi_file.exists():
            with open(suhi_file, 'r') as f:
                self.suhi_data = json.load(f)
            print(f"[OK] Loaded SUHI data for {len(self.suhi_data)} cities")
        else:
            print("⚠️ SUHI data not found, using temperature data only")
    
    def _load_lulc_data(self):
        """Load LULC (Land Use Land Cover) data"""
        lulc_file = self.base_path / "reports" / "lulc_analysis_summary.json"
        if lulc_file.exists():
            with open(lulc_file, 'r') as f:
                self.lulc_data = json.load(f)
            print(f"[OK] Loaded LULC data for {len(self.lulc_data)} cities")
        else:
            print("⚠️ LULC data not found")
    
    def _load_spatial_data(self):
        """Load spatial relationships data"""
        spatial_file = self.base_path / "reports" / "spatial_relationships_report.json"
        if spatial_file.exists():
            with open(spatial_file, 'r') as f:
                self.spatial_data = json.load(f)
            print(f"[OK] Loaded spatial relationships data")
        else:
            print("⚠️ Spatial relationships data not found")
    
    def _load_nightlights_data(self):
        """Load nightlights data"""
        nightlights_file = self.base_path / "reports" / "nightlights_summary.json"
        if nightlights_file.exists():
            with open(nightlights_file, 'r') as f:
                self.nightlights_data = json.load(f)
            print(f"[OK] Loaded nightlights data for {len(self.nightlights_data)} cities")
        else:
            print("⚠️ Nightlights data not found")
    
    def _initialize_population_data(self):
        """Initialize population data for cities using user-provided data"""
        from .utils import UZBEKISTAN_CITIES
        
        # First try to load supplemental population data from Excel (for cities not in UZBEK_CITIES_DATA)
        supplemental_pop_data = self._load_user_population_data()
        
        # Initialize population data for all cities in UZBEKISTAN_CITIES
        for city, info in UZBEKISTAN_CITIES.items():
            # Use user-provided data from UZBEK_CITIES_DATA if available
            if city in UZBEK_CITIES_DATA:
                user_data = UZBEK_CITIES_DATA[city]
                pop = user_data['pop_2024']
                gdp = user_data['gdp_per_capita']
                area = user_data.get('area_km2')
                print(f"[USER DATA] {city}: {pop:,.0f} people, GDP: ${gdp:,.0f}, Area: {area:.1f} km²")
            # Use supplemental Excel data if available
            elif city in supplemental_pop_data:
                pop = supplemental_pop_data[city]['population']
                gdp = supplemental_pop_data[city]['gdp_per_capita']
                area = None
                print(f"[EXCEL DATA] {city}: {pop:,.0f} people, GDP: ${gdp:,.0f}")
            # Fallback to hardcoded values
            else:
                pop = info.get('population')
                gdp = 2000  # Default GDP per capita for Uzbekistan
                area = None
                print(f"[HARDCODED] {city}: {pop:,.0f} people, GDP: ${gdp:,.0f}")
            
            cp = CityPopulationData(city=city,
                                    population_2024=pop,
                                    gdp_per_capita_usd=gdp,
                                    urban_area_km2=area)
            
            self.population_data[city] = cp

        print(f"[OK] Initialized assessment for {len(self.population_data)} cities using user-provided data")
    
    def _load_user_population_data(self):
        """Load user-provided population data from Excel file"""
        import pandas as pd
        import os
        
        user_data = {}
        
        try:
            excel_path = os.path.join(self.base_path, 'ExternalData', 'uzbekistan_pop_grp.xlsx')
            if not os.path.exists(excel_path):
                print("[WARNING] User population data file not found, using hardcoded values")
                return user_data
            
            # Read the Excel file
            pop_df = pd.read_excel(excel_path)
            
            # City to region mapping for Uzbekistan cities
            city_region_mapping = {
                'Tashkent': ['Tashkent city', 'Tashkent region'],
                'Samarkand': ['Samarkand region'],
                'Bukhara': ['Bukhara region'],
                'Andijan': ['Andijan region'],
                'Namangan': ['Namangan region'],
                'Fergana': ['Fergana region'],
                'Nukus': ['Republic of Karakalpakstan'],
                'Urgench': ['Khorezm region'],
                'Jizzakh': ['Jizzakh region'],
                'Qarshi': ['Kashkadarya region'],
                'Navoiy': ['Navoi region'],
                'Termez': ['Surkhandarya region'],
                'Gulistan': ['Syrdarya region'],
                'Nurafshon': ['Tashkent region']  # Nurafshon is in Tashkent region
            }
            
            # Extract population data (assuming population is in thousands)
            for city, regions in city_region_mapping.items():
                for region in regions:
                    # Look for the region in the first column
                    matches = pop_df[pop_df.iloc[:, 0].astype(str).str.contains(region.replace(' region', '').replace(' Republic of ', ''), case=False, na=False)]
                    
                    if not matches.empty:
                        # Get the population value (assuming it's in column 1, in thousands)
                        pop_value = matches.iloc[0, 1]  # Population in thousands
                        if pd.notna(pop_value):
                            # Convert to actual population (multiply by 1000)
                            actual_pop = float(pop_value) * 1000
                            
                            # Estimate GDP per capita (using regional averages)
                            gdp_estimates = {
                                'Tashkent': 4000,  # Capital city
                                'Samarkand': 2500,  # Historic city
                                'Bukhara': 2200,    # Tourism-dependent
                                'Andijan': 2000,    # Agricultural region
                                'Namangan': 1900,   # Industrial region
                                'Fergana': 1800,    # Agricultural valley
                                'Nukus': 1600,      # Remote region
                                'Urgench': 1700,    # Agricultural region
                                'Jizzakh': 1800,    # Mixed economy
                                'Qarshi': 1900,     # Agricultural
                                'Navoiy': 2800,     # Mining region
                                'Termez': 1700,     # Border region
                                'Gulistan': 1600,   # Agricultural
                                'Nurafshon': 3500   # Suburban to capital
                            }
                            
                            user_data[city] = {
                                'population': int(actual_pop),
                                'gdp_per_capita': gdp_estimates.get(city, 2000)
                            }
                            break  # Use first match found
            
            if user_data:
                print(f"[SUCCESS] Loaded user population data for {len(user_data)} cities")
            else:
                print("[WARNING] No user population data could be extracted from Excel file")
            
        except Exception as e:
            print(f"[ERROR] Failed to load user population data: {e}")
        
        return user_data
    
    def _initialize_data_cache(self):
        """Initialize data cache for percentile-based normalization"""
        self._cache = {}
        
        # Cache all population values for percentile normalization
        populations = []
        densities = []
        gdp_values = []
        
        for city_data in self.population_data.values():
            if city_data.population_2024:
                populations.append(city_data.population_2024)
            if city_data.density_per_km2:
                densities.append(city_data.density_per_km2)
            if city_data.gdp_per_capita_usd:
                gdp_values.append(city_data.gdp_per_capita_usd)
        
        self._cache['population'] = populations
        self._cache['density'] = densities
        self._cache['gdp'] = gdp_values
        
        # Cache built area percentages
        built_pcts = []
        for lulc_city in self.lulc_data:
            areas = lulc_city.get('areas_m2', {})
            if areas:
                years = sorted([int(y) for y in areas.keys()])
                if years:
                    latest_year = str(years[-1])
                    built_pct = areas[latest_year].get('Built_Area', {}).get('percentage')
                    if built_pct is not None:
                        built_pcts.append(built_pct)
        
        self._cache['built_pct'] = built_pcts
        
        # Cache nightlights values
        nightlights = []
        veg_patch_counts = []
        
        for nl_city in self.nightlights_data:
            years_data = nl_city.get('years', {})
            if years_data:
                years = sorted([int(y) for y in years_data.keys()])
                if years:
                    latest_year = str(years[-1])
                    urban_nl = years_data[latest_year].get('stats', {}).get('urban_core', {}).get('mean')
                    if urban_nl is not None:
                        nightlights.append(urban_nl)
        
        # Cache vegetation patch counts for green capacity
        for city in self.population_data.keys():
            spatial_city_data = self.spatial_data.get('per_year', {}).get(city, {})
            if spatial_city_data:
                years = sorted([int(y) for y in spatial_city_data.keys()])
                if years:
                    latest_year = str(years[-1])
                    veg_patches = spatial_city_data[latest_year].get('veg_patches', {}).get('patch_count', 0)
                    if veg_patches > 0:
                        veg_patch_counts.append(veg_patches)
        
        self._cache['nightlights'] = nightlights
        self._cache['veg_patches'] = veg_patch_counts
        
        print(f"[OK] Initialized data cache for percentile normalization")
    
    @staticmethod
    def pct_norm(values, x, lo=0.1, hi=0.9, invert=False, fallback=0.0):
        """
        Percentile-based [0,1] scaling with winsorization.
        More conservative percentiles (10th-90th) to avoid inflation.
        """
        try:
            s = pd.Series([v for v in values if v is not None and np.isfinite(v)])
            if s.empty or x is None or not np.isfinite(x):
                return fallback
            a, b = s.quantile(lo), s.quantile(hi)
            if a == b:
                return fallback
            z = (np.clip(x, a, b) - a) / (b - a)
            return 1 - z if invert else z
        except Exception:
            return fallback
