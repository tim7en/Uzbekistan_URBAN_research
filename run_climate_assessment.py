#!/usr/bin/env python3
"""
Urban Climate Change Adaptability Assessment Unit
Based on IPCC AR6 Climate Risk Assessment Framework

This module implements professional climate risk assessment methodologies following:
- IPCC AR6 Working Group II Chapter 13: Urban systems and other settlements
- IPCC AR6 Technical Summary: Climate Risk Assessment Framework
- Urban Climate Change Research Network (UCCRN) assessment methods

Assessment Components:
1. Hazard Assessment (Heat exposure, temperature trends)
2. Exposure Assessment (Population, infrastructure, urban morphology)
3. Vulnerability Assessment (Socio-economic factors, adaptive capacity)
4. Risk Assessment (Hazard × Exposure × Vulnerability)
5. Adaptive Capacity Assessment (Governance, technology, resources)
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import warnings

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

warnings.filterwarnings("ignore")

@dataclass
class ClimateRiskMetrics:
    """Climate risk metrics following IPCC AR6 framework"""
    # Hazard indicators
    current_suhi_intensity: float = 0.0
    suhi_trend: float = 0.0
    temperature_trend: float = 0.0
    heat_days_frequency: int = 0
    extreme_heat_threshold_exceedance: float = 0.0
    
    # Exposure indicators
    population: Optional[int] = None
    population_density: Optional[float] = None
    urban_area_km2: Optional[float] = None
    built_area_percentage: float = 0.0
    vulnerable_population_share: float = 0.0
    
    # Vulnerability indicators
    green_space_accessibility: float = 0.0
    building_material_heat_absorption: float = 0.0
    air_conditioning_penetration: float = 0.0
    poverty_index: float = 0.0
    age_vulnerability_index: float = 0.0
    
    # Adaptive capacity indicators
    governance_effectiveness: float = 0.0
    economic_resources: float = 0.0
    technological_capacity: float = 0.0
    social_capital: float = 0.0
    institutional_capacity: float = 0.0
    
    # Computed risk scores
    hazard_score: float = 0.0
    exposure_score: float = 0.0
    vulnerability_score: float = 0.0
    adaptive_capacity_score: float = 0.0
    overall_risk_score: float = 0.0
    adaptability_score: float = 0.0

@dataclass
class CityPopulationData:
    """City population and demographic data"""
    city: str
    country: str = "Uzbekistan"
    population_2020: Optional[int] = None
    population_2024: Optional[int] = None
    area_km2: Optional[float] = None
    density_per_km2: Optional[float] = None
    gdp_per_capita_usd: Optional[float] = None
    
    # Uzbekistan city populations (city proper), ~2024
    # Method: official city estimates from CityPopulation (UzStat). If a 2024 value
    # wasn't published for a city, pop_2024 is the midpoint of 2023 and 2025.
    # Areas are city administrative areas (km²), not metros.

# --- Region GRP per capita (2024) in USD (from official-sourced summary) ---
    # Values correspond to 2024 GRP-per-capita by region; see sources in comments below.
    REGION_GRP_PC_USD_2024 = {
        "Tashkent City": 7223.0,
        "Tashkent Region": 3757.0,
        "Navoi Region": 8545.0,
        "Samarkand Region": 1856.0,
        "Fergana Region": 1759.0,
        "Andijan Region": 2087.0,
        "Kashkadarya Region": 1771.0,
        "Bukhara Region": 2745.0,
        "Namangan Region": 1758.0,
        "Surkhandarya Region": 1476.0,
        "Khorezm Region": 2012.0,
        "Republic of Karakalpakstan": 1790.0,
        "Jizzakh Region": 2235.0,
        "Syrdarya Region": 2400.0,
    }

    # --- Populations for weighting (1 Jan 2024 official releases) ---
    # Used only for Tashkent weighted average across City+Region:
    TASHKENT_CITY_POP_2024 = 3_040_800     # city proper
    TASHKENT_REGION_POP_2024 = 3_051_800   # viloyat
    # Weighted GRP per capita for "Tashkent" (reflecting strong coupling with region)
    _t_city = REGION_GRP_PC_USD_2024["Tashkent City"]
    _t_region = REGION_GRP_PC_USD_2024["Tashkent Region"]
    TASHKENT_WEIGHTED_GRP_PC_USD_2024 = (
        _t_city * TASHKENT_CITY_POP_2024 + _t_region * TASHKENT_REGION_POP_2024
    ) / (TASHKENT_CITY_POP_2024 + TASHKENT_REGION_POP_2024)

    # --- Map each city to its region (viloyat) for GRP lookups ---
    CITY_TO_REGION = {
        "Tashkent": "SPECIAL_TASHKENT",  # handled separately
        "Samarkand": "Samarkand Region",
        "Bukhara": "Bukhara Region",
        "Andijan": "Andijan Region",
        "Namangan": "Namangan Region",
        "Fergana": "Fergana Region",
        "Nukus": "Republic of Karakalpakstan",
        "Urgench": "Khorezm Region",
        "Termez": "Surkhandarya Region",
        "Qarshi": "Kashkadarya Region",
        "Jizzakh": "Jizzakh Region",
        "Navoiy": "Navoi Region",
        "Gulistan": "Syrdarya Region",
        "Nurafshon": "Tashkent Region",
    }

    # --- Your base dictionary (kept as provided); we'll populate gdp_per_capita (USD, 2024) ---
    UZBEK_CITIES_DATA = {
        "Tashkent":  {"pop_2024": 3095498, "area_km2": 450.0,  "gdp_per_capita": None},
        "Samarkand": {"pop_2024": 584326,  "area_km2": 110.6,  "gdp_per_capita": None},
        "Bukhara":   {"pop_2024": 294684,  "area_km2": 104.7,  "gdp_per_capita": None},
        "Andijan":   {"pop_2024": 480240,  "area_km2": 96.86,  "gdp_per_capita": None},
        "Namangan":  {"pop_2024": 695770,  "area_km2": 168.8,  "gdp_per_capita": None},
        "Fergana":   {"pop_2024": 321429,  "area_km2": 101.9,  "gdp_per_capita": None},
        "Nukus":     {"pop_2024": 339624,  "area_km2": 215.7,  "gdp_per_capita": None},
        "Urgench":   {"pop_2024": 152816,  "area_km2": 38.14,  "gdp_per_capita": None},
        "Termez":    {"pop_2024": 201490,  "area_km2": 49.50,  "gdp_per_capita": None},
        "Qarshi":    {"pop_2024": 294832,  "area_km2": 75.92,  "gdp_per_capita": None},
        "Jizzakh":   {"pop_2024": 195781,  "area_km2": 55.41,  "gdp_per_capita": None},
        "Navoiy":    {"pop_2024": 161238,  "area_km2": 52.82,  "gdp_per_capita": None},
        "Gulistan":  {"pop_2024": 99156,   "area_km2": 31.62,  "gdp_per_capita": None},
        "Nurafshon": {"pop_2024": 55826,   "area_km2": 10.66,  "gdp_per_capita": None},
    }

    # --- Fill gdp_per_capita using region GRP per capita (USD, 2024) ---
    for city, rec in UZBEK_CITIES_DATA.items():
        region = CITY_TO_REGION.get(city)
        if region is None:
            # leave as None if we don't know where to map it
            continue
        if region == "SPECIAL_TASHKENT":
            rec["gdp_per_capita"] = round(TASHKENT_WEIGHTED_GRP_PC_USD_2024, 0)
        else:
            rec["gdp_per_capita"] = REGION_GRP_PC_USD_2024.get(region, None)

    
    def __post_init__(self):
        """Calculate derived metrics after initialization."""
        # Auto-load data for Uzbek cities if not provided
        if self.city in self.UZBEK_CITIES_DATA and not self.population_2024:
            city_data = self.UZBEK_CITIES_DATA[self.city]
            self.population_2024 = city_data["pop_2024"]
            if not self.area_km2:
                self.area_km2 = city_data["area_km2"]
            if not self.gdp_per_capita_usd:
                self.gdp_per_capita_usd = city_data["gdp_per_capita"]
        
        # Calculate density
        if self.population_2024 and self.area_km2 and self.area_km2 > 0:
            self.density_per_km2 = self.population_2024 / self.area_km2
        else:
            self.density_per_km2 = None


class IPCCClimateRiskAssessment:
    """
    Urban Climate Change Risk and Adaptability Assessment
    Following IPCC AR6 methodologies
    """
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.output_path = self.base_path / "climate_assessment"
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing SUHI and urban data
        self.suhi_data = {}
        self.lulc_data = []
        self.spatial_data = {}
        self.nightlights_data = []
        
        # Assessment results
        self.city_risk_profiles = {}
        self.population_data = {}
        
        # IPCC AR6 risk thresholds and weights
        self.risk_thresholds = {
            'heat_stress': {'low': 1.0, 'medium': 2.0, 'high': 3.0, 'very_high': 4.0},
            'temperature_trend': {'low': 0.02, 'medium': 0.05, 'high': 0.08, 'very_high': 0.12},  # °C/year
            'urban_expansion': {'low': 0.02, 'medium': 0.05, 'high': 0.08, 'very_high': 0.12}  # fraction/year
        }
        
        # Component weights for overall risk calculation (IPCC AR6 approach)
        self.component_weights = {
            'hazard': 0.3,
            'exposure': 0.25,
            'vulnerability': 0.25,
            'adaptive_capacity': 0.2  # Negative weight (higher capacity = lower risk)
        }
    
    def load_urban_data(self):
        """Load all available urban analysis data"""
        print("Loading urban climate data for risk assessment...")
        
        # Load SUHI data
        suhi_file = self.base_path / "reports" / "suhi_batch_summary.json"
        if suhi_file.exists():
            with open(suhi_file, 'r') as f:
                self.suhi_data = json.load(f)
            print(f"✓ Loaded SUHI data for {len(self.suhi_data)} cities")
        
        # Load LULC data
        lulc_file = self.base_path / "reports" / "lulc_analysis_summary.json"
        if lulc_file.exists():
            with open(lulc_file, 'r') as f:
                self.lulc_data = json.load(f)
            print(f"✓ Loaded LULC data for {len(self.lulc_data)} cities")
        
        # Load spatial relationships
        spatial_file = self.base_path / "reports" / "spatial_relationships_report.json"
        if spatial_file.exists():
            with open(spatial_file, 'r') as f:
                self.spatial_data = json.load(f)
            print(f"✓ Loaded spatial relationships data")
        
        # Load nightlights data
        nightlights_file = self.base_path / "reports" / "nightlights_summary.json"
        if nightlights_file.exists():
            with open(nightlights_file, 'r') as f:
                self.nightlights_data = json.load(f)
            print(f"✓ Loaded nightlights data for {len(self.nightlights_data)} cities")
        
        # Initialize population data for cities
        for city in self.suhi_data.keys():
            self.population_data[city] = CityPopulationData(city=city)
        
        print(f"✓ Initialized assessment for {len(self.population_data)} cities")
        
        # Initialize data cache for percentile-based normalization
        self._initialize_data_cache()
    
    def _initialize_data_cache(self):
        """Initialize data cache for percentile normalization to avoid inflated scores"""
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
                years = sorted([int(y) for y in areas.keys()])  # Fix: sort as integers
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
                years = sorted([int(y) for y in years_data.keys()])  # Fix: sort as integers
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
        
        print(f"✓ Initialized data cache for percentile normalization")

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
    
    def calculate_hazard_score(self, city: str) -> float:
        """
        Calculate climate hazard score following IPCC AR6 Chapter 13
        Focus on heat-related hazards for urban areas
        """
        if city not in self.suhi_data:
            return 0.0
        
        city_data = self.suhi_data[city]
        years = sorted([int(y) for y in city_data.keys()])
        
        if len(years) < 2:
            return 0.0
        
        # Current hazard intensity (latest year SUHI)
        latest_year = str(years[-1])
        latest_stats = city_data[latest_year]['stats']
        current_suhi = max(abs(latest_stats.get('suhi_day', 0)), 
                          abs(latest_stats.get('suhi_night', 0)))
        
        # Hazard trend (temperature and SUHI trends)
        suhi_values = []
        temp_values = []
        
        for year in years:
            year_str = str(year)
            if year_str in city_data:
                stats = city_data[year_str]['stats']
                suhi_values.append(stats.get('suhi_night', 0))
                temp_values.append(stats.get('night_urban_mean', 0))
        
        # Calculate trends with stability checks
        suhi_trend = 0.0
        temp_trend = 0.0
        if len(years) >= 4:  # More conservative: need at least 4 years for stable trend
            try:
                # Add smoothing for more stable trends
                suhi_trend = np.polyfit(years, suhi_values, 1)[0]
                temp_trend = np.polyfit(years, temp_values, 1)[0]
                
                # Bound extreme trends (outlier protection)
                suhi_trend = np.clip(suhi_trend, -0.2, 0.2)  # ±0.2°C/year max
                temp_trend = np.clip(temp_trend, -0.3, 0.3)  # ±0.3°C/year max
            except:
                suhi_trend = temp_trend = 0.0
        
        # Heat stress intensity (fix naming - this is temperature excess, not days)
        urban_temp_latest = latest_stats.get('night_urban_mean', 0)
        temp_excess_above_threshold = max(0, urban_temp_latest - 25)  # °C above comfort threshold
        
        # Hazard score calculation (0-1 scale) - more conservative normalization
        intensity_score = min(1.0, current_suhi / 6.0)  # Normalize by 6°C SUHI (more conservative)
        trend_score = min(1.0, max(0.0, (temp_trend + 0.02) / 0.1))  # Focus on temp trend, smaller range
        intensity_excess_score = min(1.0, temp_excess_above_threshold / 8.0)  # Normalize by 8°C excess
        
        # IPCC AR6 weighted combination - emphasize current conditions over trends
        hazard_score = (0.6 * intensity_score + 0.25 * trend_score + 0.15 * intensity_excess_score)
        
        return hazard_score
    
    def calculate_exposure_score(self, city: str) -> float:
        """
        Calculate exposure score based on population and infrastructure
        Following IPCC AR6 exposure assessment framework
        """
        pop_data = self.population_data.get(city)
        if not pop_data:
            return 0.0
        
        # Population exposure
        # Population exposure (percentile)
        pop_score = self.pct_norm(self._cache['population'], pop_data.population_2024, fallback=0.0)

        # Density exposure
        density_score = self.pct_norm(self._cache['density'], pop_data.density_per_km2, fallback=0.0)

        # Urban area exposure
        urban_area_score = 0.0
        for lulc_city in self.lulc_data:
            if lulc_city.get('city') == city:
                areas = lulc_city.get('areas_m2', {})
                if areas:
                    years = sorted([int(y) for y in areas.keys()])  # Fix: sort as integers
                    if years:
                        latest_year = str(years[-1])
                        built_pct = areas[latest_year].get('Built_Area', {}).get('percentage', None)
                        urban_area_score = self.pct_norm(self._cache['built_pct'], built_pct, fallback=0.0)
                break

        # Infrastructure density via nightlights
        infrastructure_score = 0.0
        for nl_city in self.nightlights_data:
            if nl_city.get('city') == city:
                yrs = nl_city.get('years', {})
                if yrs:
                    years = sorted([int(y) for y in yrs.keys()])  # Fix: sort as integers
                    if years:
                        latest_year = str(years[-1])
                        urban_nl = yrs[latest_year].get('stats', {}).get('urban_core', {}).get('mean', None)
                        infrastructure_score = self.pct_norm(self._cache['nightlights'], urban_nl, fallback=0.0)
                break
        
        # IPCC AR6 exposure score (weighted combination)
        exposure_score = (0.4 * pop_score + 0.3 * density_score + 
                         0.2 * urban_area_score + 0.1 * infrastructure_score)
        
        return exposure_score
        
    def calculate_vulnerability_score(self, city: str) -> float:
        """
        Calculate vulnerability score based on socio-economic and physical factors
        Following IPCC AR6 vulnerability assessment - FIXED VERSION
        """
        pop_data = self.population_data.get(city)
        if not pop_data:
            return 0.6  # Default medium-high vulnerability (more conservative)
        
        # Economic vulnerability (inverse of GDP per capita) - use percentile ranking
        economic_vuln = 0.6  # Conservative default
        if pop_data.gdp_per_capita_usd and self._cache['gdp']:
            # Use percentile ranking, inverted (higher GDP = lower vulnerability)
            economic_vuln = 1.0 - self.pct_norm(self._cache['gdp'], pop_data.gdp_per_capita_usd, 
                                               lo=0.2, hi=0.8, fallback=0.4)
        
        # Green space accessibility vulnerability
        green_vuln = 0.6  # Conservative default
        spatial_city_data = self.spatial_data.get('per_year', {}).get(city, {})
        if spatial_city_data:
            years = sorted([int(y) for y in spatial_city_data.keys()])  # Fix: sort as integers
            if years:
                latest_year = str(years[-1])
                veg_access = spatial_city_data[latest_year].get('vegetation_accessibility', {}).get('city', {}).get('mean')
                if veg_access is not None:
                    # More conservative: 500m=low vuln, 1500m=high vuln
                    green_vuln = min(1.0, max(0.1, (veg_access - 300) / 1200))
        
        # Urban morphology vulnerability - fix year sorting
        morphology_vuln = 0.5
        for lulc_city in self.lulc_data:
            if lulc_city.get('city') == city:
                areas = lulc_city.get('areas_m2', {})
                if areas:
                    years = sorted([int(y) for y in areas.keys()])  # Fix: sort as integers
                    if years:
                        latest_year = str(years[-1])
                        built_pct = areas[latest_year].get('Built_Area', {}).get('percentage', 50)
                        bare_ground_pct = areas[latest_year].get('Bare_Ground', {}).get('percentage', 0)
                        # More nuanced: high built area alone is not bad, impervious + bare ground is
                        morphology_vuln = min(1.0, (built_pct * 0.6 + bare_ground_pct * 1.5) / 100.0)
                break
        
        # Infrastructure age vulnerability (more realistic proxy)
        infrastructure_vuln = 0.4  # Moderate default
        if pop_data.population_2024:
            # Larger cities often have older infrastructure, but also more resources
            if pop_data.population_2024 > 1500000:
                infrastructure_vuln = 0.7  # Large cities: old infrastructure
            elif pop_data.population_2024 > 500000:
                infrastructure_vuln = 0.5  # Medium cities: mixed
            else:
                infrastructure_vuln = 0.4  # Small cities: newer but limited
        
        # IPCC AR6 vulnerability score - equal weighting
        vulnerability_score = (0.3 * economic_vuln + 0.25 * green_vuln + 
                              0.25 * morphology_vuln + 0.2 * infrastructure_vuln)
        
        return vulnerability_score
    
    def calculate_adaptive_capacity_score(self, city: str) -> float:
        """
        Calculate adaptive capacity following IPCC AR6 framework - FIXED VERSION
        Addresses inflation issues with more realistic thresholds and harmonic mean
        """
        pop_data = self.population_data.get(city)
        if not pop_data:
            return 0.2  # Default low adaptive capacity (more conservative)
        
        # 1. Economic resources - use percentile ranking, not absolute thresholds
        economic_capacity = 0.2  # Conservative default
        if pop_data.gdp_per_capita_usd and self._cache['gdp']:
            economic_capacity = self.pct_norm(self._cache['gdp'], pop_data.gdp_per_capita_usd, 
                                            lo=0.2, hi=0.8, fallback=0.2)
        
        # 2. Institutional capacity - remove double-counting, focus on population size only
        institutional_capacity = 0.2
        if pop_data.population_2024:
            # More conservative thresholds: 100k=low, 500k=medium, 1M+=high
            if pop_data.population_2024 >= 1000000:
                institutional_capacity = 0.8
            elif pop_data.population_2024 >= 500000:
                institutional_capacity = 0.6
            elif pop_data.population_2024 >= 200000:
                institutional_capacity = 0.4
            else:
                institutional_capacity = 0.3
        
        # 3. Technological capacity - use percentile ranking, more conservative threshold
        tech_capacity = 0.2
        for nl_city in self.nightlights_data:
            if nl_city.get('city') == city:
                years_data = nl_city.get('years', {})
                if years_data:
                    years = sorted([int(y) for y in years_data.keys()])  # Fix: sort as integers
                    if years:
                        latest_year = str(years[-1])
                        urban_nl = years_data[latest_year].get('stats', {}).get('urban_core', {}).get('mean')
                        if urban_nl is not None and self._cache['nightlights']:
                            tech_capacity = self.pct_norm(self._cache['nightlights'], urban_nl, 
                                                         lo=0.2, hi=0.8, fallback=0.2)
                break
        
        # 4. Green infrastructure - use percentile ranking, not absolute threshold
        green_capacity = 0.2
        spatial_city_data = self.spatial_data.get('per_year', {}).get(city, {})
        if spatial_city_data:
            years = sorted([int(y) for y in spatial_city_data.keys()])  # Fix: sort as integers
            if years:
                latest_year = str(years[-1])
                veg_patches = spatial_city_data[latest_year].get('veg_patches', {}).get('patch_count')
                if veg_patches is not None and self._cache['veg_patches']:
                    green_capacity = self.pct_norm(self._cache['veg_patches'], veg_patches, 
                                                  lo=0.2, hi=0.8, fallback=0.2)
        
        # 5. Social capital - more conservative, based on economic diversity
        social_capacity = 0.2
        if pop_data.gdp_per_capita_usd and pop_data.population_2024:
            # Combine economy and size for social cohesion proxy
            econ_factor = min(0.8, pop_data.gdp_per_capita_usd / 8000)  # Much higher threshold
            size_factor = min(0.6, pop_data.population_2024 / 800000)  # Larger threshold
            social_capacity = min(0.7, (econ_factor + size_factor) / 2)  # Cap at 0.7
        
        # CRITICAL: Penalize weak links (bottleneck) + cap median
        capacities = [economic_capacity, institutional_capacity, tech_capacity, green_capacity, social_capacity]
        # harmonic mean
        eps = 1e-6
        h = len(capacities) / sum(1.0 / max(eps, c) for c in capacities)

        # explicit bottleneck (minimum) has 30% influence
        b = min(capacities)

        # blend & cap: keep AC from clustering high; typical range ~0.2–0.7
        adaptive_capacity = 0.7 * h + 0.3 * b
        adaptive_capacity = max(0.1, min(0.7, adaptive_capacity))
        return adaptive_capacity
    
    def assess_city_climate_risk(self, city: str) -> ClimateRiskMetrics:
        """
        Comprehensive climate risk assessment for a city
        Following IPCC AR6 risk = hazard × exposure × vulnerability / adaptive_capacity
        """
        metrics = ClimateRiskMetrics()
        
        # Calculate component scores
        hazard_score = self.calculate_hazard_score(city)
        exposure_score = self.calculate_exposure_score(city)
        vulnerability_score = self.calculate_vulnerability_score(city)
        adaptive_capacity_score = self.calculate_adaptive_capacity_score(city)
        
        # Store component scores
        metrics.hazard_score = hazard_score
        metrics.exposure_score = exposure_score
        metrics.vulnerability_score = vulnerability_score
        metrics.adaptive_capacity_score = adaptive_capacity_score
        
        # IPCC AR6 risk calculation - FIXED VERSION v2
        # Less sensitive to adaptive capacity to avoid over-dampening
        base_risk = hazard_score * exposure_score * vulnerability_score
        
        # gentler AC dampening, but not too gentle
        adaptive_capacity_factor = (1.0 - 0.6 * adaptive_capacity_score)
        adaptive_capacity_factor = float(np.clip(adaptive_capacity_factor, 0.35, 0.9))
        
        overall_risk = base_risk * adaptive_capacity_factor
        metrics.overall_risk_score = float(np.clip(overall_risk, 0.0, 1.0))
        
        metrics.adaptability_score = 0.4 * adaptive_capacity_score + 0.6 * (1.0 - metrics.overall_risk_score)
        
        # Populate detailed metrics from data
        self._populate_detailed_metrics(city, metrics)
        
        return metrics
    
    def _populate_detailed_metrics(self, city: str, metrics: ClimateRiskMetrics):
        """Populate detailed metrics from available data"""
        # Population data
        pop_data = self.population_data.get(city)
        if pop_data:
            metrics.population = pop_data.population_2024
            metrics.population_density = pop_data.density_per_km2
            metrics.urban_area_km2 = pop_data.area_km2
        
        # SUHI and temperature data
        if city in self.suhi_data:
            years = sorted([int(y) for y in self.suhi_data[city].keys()])
            if years:
                latest_year = str(years[-1])
                stats = self.suhi_data[city][latest_year]['stats']
                metrics.current_suhi_intensity = max(abs(stats.get('suhi_day', 0)), 
                                                   abs(stats.get('suhi_night', 0)))
                
                # Calculate trends if enough data
                if len(years) >= 3:
                    suhi_values = [self.suhi_data[city][str(y)]['stats'].get('suhi_night', 0) for y in years]
                    temp_values = [self.suhi_data[city][str(y)]['stats'].get('night_urban_mean', 0) for y in years]
                    metrics.suhi_trend = np.polyfit(years, suhi_values, 1)[0]
                    metrics.temperature_trend = np.polyfit(years, temp_values, 1)[0]
        
        # Built area percentage
        for lulc_city in self.lulc_data:
            if lulc_city.get('city') == city:
                areas = lulc_city.get('areas_m2', {})
                if areas:
                    ly = str(max(map(int, areas.keys())))
                    metrics.built_area_percentage = areas[ly].get('Built_Area', {}).get('percentage', 0)
                break
        
        # Green space accessibility
        spatial_city_data = self.spatial_data.get('per_year', {}).get(city, {})
        if spatial_city_data:
            ly = str(max(map(int, spatial_city_data.keys())))
            metrics.green_space_accessibility = spatial_city_data[ly].get('vegetation_accessibility', {}).get('city', {}).get('mean', 0)
    
    def run_full_assessment(self) -> Dict[str, ClimateRiskMetrics]:
        """Run full climate risk assessment for all cities"""
        print("Running IPCC AR6-based climate risk assessment...")
        
        self.load_urban_data()
        
        results = {}
        for city in self.suhi_data.keys():
            print(f"Assessing {city}...")
            results[city] = self.assess_city_climate_risk(city)
        
        self.city_risk_profiles = results
        print(f"✓ Completed assessment for {len(results)} cities")
        
        # Quick distribution sanity check
        ac = [m.adaptive_capacity_score for m in results.values()]
        rk = [m.overall_risk_score for m in results.values()]
        pr = [ (r ** 0.8) * ((1 - a) ** 0.6) for r, a in zip(rk, ac) ]
        print(f"AC median={np.median(ac):.3f}  IQR=({np.quantile(ac,0.25):.3f},{np.quantile(ac,0.75):.3f})")
        print(f"Risk median={np.median(rk):.3f}  IQR=({np.quantile(rk,0.25):.3f},{np.quantile(rk,0.75):.3f})")
        print(f"Priority median={np.median(pr):.3f}  IQR=({np.quantile(pr,0.25):.3f},{np.quantile(pr,0.75):.3f})")
        
        return results
    
    def create_risk_assessment_dashboard(self):
        """Create comprehensive climate risk assessment dashboard"""
        if not self.city_risk_profiles:
            print("No risk assessment data available")
            return None
        
        # Prepare data for visualization
        cities = list(self.city_risk_profiles.keys())
        hazard_scores = [self.city_risk_profiles[city].hazard_score for city in cities]
        exposure_scores = [self.city_risk_profiles[city].exposure_score for city in cities]
        vulnerability_scores = [self.city_risk_profiles[city].vulnerability_score for city in cities]
        adaptive_capacity_scores = [self.city_risk_profiles[city].adaptive_capacity_score for city in cities]
        overall_risk_scores = [self.city_risk_profiles[city].overall_risk_score for city in cities]
        adaptability_scores = [self.city_risk_profiles[city].adaptability_score for city in cities]
        populations = [self.city_risk_profiles[city].population or 0 for city in cities]
        
        # Create comprehensive dashboard
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                "IPCC AR6 Risk Components by City",
                "Risk vs Adaptability Matrix",
                "Population-Weighted Risk Assessment",
                "Adaptive Capacity vs Overall Risk",
                "Climate Risk Classification",
                "Priority Action Matrix"
            ),
            specs=[[{"type": "bar"}, {"type": "scatter"}],
                   [{"type": "scatter"}, {"type": "scatter"}],
                   [{"type": "bar"}, {"type": "scatter"}]]
        )
        
        # Panel 1: Risk components
        fig.add_trace(go.Bar(x=cities, y=hazard_scores, name="Hazard", 
                            marker_color='red', opacity=0.7), row=1, col=1)
        fig.add_trace(go.Bar(x=cities, y=exposure_scores, name="Exposure", 
                            marker_color='orange', opacity=0.7), row=1, col=1)
        fig.add_trace(go.Bar(x=cities, y=vulnerability_scores, name="Vulnerability", 
                            marker_color='yellow', opacity=0.7), row=1, col=1)
        fig.add_trace(go.Bar(x=cities, y=adaptive_capacity_scores, name="Adaptive Capacity", 
                            marker_color='green', opacity=0.7), row=1, col=1)
        
        # Panel 2: Risk vs Adaptability
        risk_colors = ['red' if r > 0.7 else 'orange' if r > 0.4 else 'green' for r in overall_risk_scores]
        fig.add_trace(go.Scatter(
            x=overall_risk_scores, y=adaptability_scores,
            mode='markers+text', text=cities, textposition='top center',
            marker=dict(size=15, color=risk_colors, opacity=0.7),
            name="Risk-Adaptability", showlegend=False
        ), row=1, col=2)
        
        # Panel 3: Population-weighted risk
        fig.add_trace(go.Scatter(
            x=populations, y=overall_risk_scores,
            mode='markers+text', text=cities, textposition='top center',
            marker=dict(
                size=[max(5, p/50000) for p in populations],
                color=overall_risk_scores,
                colorscale='Reds',
                showscale=True,
                colorbar=dict(title="Risk Score", x=0.48)
            ),
            name="Population Risk", showlegend=False
        ), row=2, col=1)
        
        # Panel 4: Adaptive capacity vs risk
        fig.add_trace(go.Scatter(
            x=adaptive_capacity_scores, y=overall_risk_scores,
            mode='markers+text', text=cities, textposition='top center',
            marker=dict(size=12, color='blue', opacity=0.7),
            name="Capacity vs Risk", showlegend=False
        ), row=2, col=2)
        
        # Panel 5: Risk classification
        risk_categories = []
        for risk in overall_risk_scores:
            if risk < 0.3:
                risk_categories.append("Low Risk")
            elif risk < 0.5:
                risk_categories.append("Medium Risk")
            elif risk < 0.7:
                risk_categories.append("High Risk")
            else:
                risk_categories.append("Very High Risk")
        
        category_counts = pd.Series(risk_categories).value_counts()
        colors_cat = {'Low Risk': 'green', 'Medium Risk': 'yellow', 'High Risk': 'orange', 'Very High Risk': 'red'}
        
        fig.add_trace(go.Bar(
            x=category_counts.index, y=category_counts.values,
            marker_color=[colors_cat[cat] for cat in category_counts.index],
            opacity=0.7, name="Risk Categories", showlegend=False
        ), row=3, col=1)
        
        # Panel 6: Priority action matrix - QUANTILE-BASED APPROACH
        # helpers
        def qscale(series, x, lo=0.1, hi=0.9):
            s = pd.Series(series)
            a, b = s.quantile(lo), s.quantile(hi)
            if a == b: 
                return 0.5
            return float(np.clip((x - a) / (b - a), 0, 1))

        risk_q  = [qscale(overall_risk_scores, r) for r in overall_risk_scores]
        ac_gap  = [1 - a for a in adaptive_capacity_scores]  # low AC => high gap
        ac_q    = [qscale(ac_gap, g) for g in ac_gap]
        pop_q   = [qscale(populations, p) for p in populations]

        # priority scoring (geometric-ish mix)
        alpha, beta = 0.8, 0.6   # emphasis on risk, then AC gap
        priority_scores = [
            (rq ** alpha) * (aq ** beta) * (max(0.2, pq) ** 0.4)  # ensure small cities not zeroed
            for rq, aq, pq in zip(risk_q, ac_q, pop_q)
        ]
        
        # color bins
        q80 = float(pd.Series(priority_scores).quantile(0.80))
        q50 = float(pd.Series(priority_scores).quantile(0.50))
        q20 = float(pd.Series(priority_scores).quantile(0.20))

        def bucket(p):
            if p >= q80: return "Urgent"
            if p >= q50: return "High"
            if p >= q20: return "Medium"
            return "Low"

        priority_labels = [bucket(p) for p in priority_scores]
        
        color_map = {"Urgent":"darkred","High":"red","Medium":"orange","Low":"green"}
        urgency_colors = [color_map[b] for b in priority_labels]
        
        fig.add_trace(go.Scatter(
            x=priority_scores, y=populations,
            mode='markers+text', text=cities, textposition='top center',
            marker=dict(size=15, color=urgency_colors, opacity=0.85),
            name="Action Priority", showlegend=False
        ), row=3, col=2)
        
        # Add reference lines
        fig.add_hline(y=0.5, line_dash="dash", line_color="black", opacity=0.5, row=1, col=2)
        fig.add_vline(x=0.5, line_dash="dash", line_color="black", opacity=0.5, row=1, col=2)
        fig.add_vline(x=0.5, line_dash="dash", line_color="black", opacity=0.5, row=2, col=2)
        fig.add_hline(y=0.5, line_dash="dash", line_color="black", opacity=0.5, row=2, col=2)
        
        # Update layout
        fig.update_layout(
            title=dict(
                text="IPCC AR6 Urban Climate Risk Assessment Dashboard<br><sub>Uzbekistan Cities - Climate Change Adaptability Analysis</sub>",
                x=0.5, font=dict(size=18)
            ),
            height=1000, width=1400,
            showlegend=True
        )
        
        # Update axes labels
        fig.update_xaxes(title_text="Cities", row=1, col=1)
        fig.update_yaxes(title_text="Risk Component Score", row=1, col=1)
        fig.update_xaxes(title_text="Overall Risk Score", row=1, col=2)
        fig.update_yaxes(title_text="Adaptability Score", row=1, col=2)
        fig.update_xaxes(title_text="Population", row=2, col=1)
        fig.update_yaxes(title_text="Overall Risk Score", row=2, col=1)
        fig.update_xaxes(title_text="Adaptive Capacity Score", row=2, col=2)
        fig.update_yaxes(title_text="Overall Risk Score", row=2, col=2)
        fig.update_xaxes(title_text="Risk Categories", row=3, col=1)
        fig.update_yaxes(title_text="Number of Cities", row=3, col=1)
        fig.update_xaxes(title_text="Priority Score", row=3, col=2)
        fig.update_yaxes(title_text="Population", row=3, col=2)
        
        # Save
        html_file = self.output_path / "ipcc_climate_risk_assessment.html"
        png_file = self.output_path / "ipcc_climate_risk_assessment.png"
        fig.write_html(str(html_file))
        
        try:
            fig.write_image(str(png_file), width=1400, height=1000, scale=2)
        except Exception as e:
            print(f"Warning: Could not save PNG: {e}")
        
        print(f"✓ Saved climate risk assessment dashboard: {html_file.name}")
        return fig
    
    def create_adaptability_ranking_table(self):
        """Create detailed adaptability ranking table"""
        if not self.city_risk_profiles:
            return None
        
        # Extract data for quantile-based priority calculation
        cities = list(self.city_risk_profiles.keys())
        overall_risk_scores = [self.city_risk_profiles[city].overall_risk_score for city in cities]
        adaptive_capacity_scores = [self.city_risk_profiles[city].adaptive_capacity_score for city in cities]
        populations = [self.city_risk_profiles[city].population or 0 for city in cities]
        
        # Quantile-based priority calculation (same as dashboard)
        def qscale(series, x, lo=0.1, hi=0.9):
            s = pd.Series(series)
            a, b = s.quantile(lo), s.quantile(hi)
            if a == b: 
                return 0.5
            return float(np.clip((x - a) / (b - a), 0, 1))

        risk_q  = [qscale(overall_risk_scores, r) for r in overall_risk_scores]
        ac_gap  = [1 - a for a in adaptive_capacity_scores]  # low AC => high gap
        ac_q    = [qscale(ac_gap, g) for g in ac_gap]
        pop_q   = [qscale(populations, p) for p in populations]

        # priority scoring (geometric-ish mix)
        alpha, beta = 0.8, 0.6   # emphasis on risk, then AC gap
        priority_scores = [
            (rq ** alpha) * (aq ** beta) * (max(0.2, pq) ** 0.4)  # ensure small cities not zeroed
            for rq, aq, pq in zip(risk_q, ac_q, pop_q)
        ]
        
        # color bins
        q80 = float(pd.Series(priority_scores).quantile(0.80))
        q50 = float(pd.Series(priority_scores).quantile(0.50))
        q20 = float(pd.Series(priority_scores).quantile(0.20))

        def bucket(p):
            if p >= q80: return "Urgent"
            if p >= q50: return "High"
            if p >= q20: return "Medium"
            return "Low"

        priority_labels = [bucket(p) for p in priority_scores]
        
        # Prepare comprehensive data
        table_data = []
        for i, (city, metrics) in enumerate(self.city_risk_profiles.items()):
            risk_level = "Very High" if metrics.overall_risk_score > 0.7 else \
                        "High" if metrics.overall_risk_score > 0.5 else \
                        "Medium" if metrics.overall_risk_score > 0.3 else "Low"
            
            adaptability_level = "Very High" if metrics.adaptability_score > 0.7 else \
                               "High" if metrics.adaptability_score > 0.5 else \
                               "Medium" if metrics.adaptability_score > 0.3 else "Low"
            
            table_data.append({
                'City': city,
                'Population': f"{metrics.population:,}" if metrics.population else "N/A",
                'Overall Risk': f"{metrics.overall_risk_score:.3f}",
                'Risk Level': risk_level,
                'Adaptability Score': f"{metrics.adaptability_score:.3f}",
                'Adaptability Level': adaptability_level,
                'Hazard Score': f"{metrics.hazard_score:.3f}",
                'Exposure Score': f"{metrics.exposure_score:.3f}",
                'Vulnerability Score': f"{metrics.vulnerability_score:.3f}",
                'Adaptive Capacity': f"{metrics.adaptive_capacity_score:.3f}",
                'Current SUHI (°C)': f"{metrics.current_suhi_intensity:.2f}",
                'Temp Trend (°C/yr)': f"{metrics.temperature_trend:.4f}",
                'Priority Score': f"{priority_scores[i]:.3f}",
                'Action Priority': priority_labels[i]
            })
        
        # Sort by priority score (descending)
        df = pd.DataFrame(table_data).sort_values("Priority Score", ascending=False)
        
        # Create color-coded table
        def get_cell_color(value, column):
            if column in ['Risk Level', 'Action Priority']:
                if 'Very High' in value or 'Urgent' in value:
                    return 'rgba(255, 0, 0, 0.3)'
                elif 'High' in value:
                    return 'rgba(255, 165, 0, 0.3)'
                elif 'Medium' in value:
                    return 'rgba(255, 255, 0, 0.3)'
                else:
                    return 'rgba(0, 255, 0, 0.3)'
            elif column == 'Adaptability Level':
                if 'Very High' in value:
                    return 'rgba(0, 255, 0, 0.3)'
                elif 'High' in value:
                    return 'rgba(255, 255, 0, 0.3)'
                elif 'Medium' in value:
                    return 'rgba(255, 165, 0, 0.3)'
                else:
                    return 'rgba(255, 0, 0, 0.3)'
            return 'white'
        
        # Create cell colors matrix
        cell_colors = []
        for col in df.columns:
            col_colors = [get_cell_color(str(val), col) for val in df[col]]
            cell_colors.append(col_colors)
        
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=list(df.columns),
                fill_color='lightblue',
                align='center',
                font=dict(size=12, color='black'),
                height=40
            ),
            cells=dict(
                values=[df[col] for col in df.columns],
                fill_color=cell_colors,
                align='center',
                font=dict(size=10),
                height=35
            )
        )])
        
        fig.update_layout(
            title=dict(
                text="Urban Climate Change Adaptability Assessment Results<br><sub>IPCC AR6 Methodology - Ranked by Climate Risk</sub>",
                x=0.5, font=dict(size=16)
            ),
            height=600 + len(df) * 35,
            width=1600
        )
        
        # Save
        html_file = self.output_path / "adaptability_ranking_table.html"
        png_file = self.output_path / "adaptability_ranking_table.png"
        fig.write_html(str(html_file))
        
        try:
            fig.write_image(str(png_file), width=1600, height=600 + len(df) * 35, scale=2)
        except Exception as e:
            print(f"Warning: Could not save PNG: {e}")
        
        print(f"✓ Saved adaptability ranking table: {html_file.name}")
        return fig
    
    def generate_assessment_report(self):
        """Generate comprehensive assessment report"""
        if not self.city_risk_profiles:
            print("No assessment data available")
            return
        
        print("\n" + "="*80)
        print("IPCC AR6 URBAN CLIMATE RISK ASSESSMENT REPORT")
        print("="*80)
        
        # Summary statistics
        risk_scores = [metrics.overall_risk_score for metrics in self.city_risk_profiles.values()]
        adapt_scores = [metrics.adaptability_score for metrics in self.city_risk_profiles.values()]
        
        print(f"\n📊 ASSESSMENT SUMMARY:")
        print(f"   Cities Assessed: {len(self.city_risk_profiles)}")
        print(f"   Average Risk Score: {np.mean(risk_scores):.3f}")
        print(f"   Average Adaptability Score: {np.mean(adapt_scores):.3f}")
        print(f"   Highest Risk City: {max(self.city_risk_profiles.keys(), key=lambda x: self.city_risk_profiles[x].overall_risk_score)}")
        print(f"   Most Adaptable City: {max(self.city_risk_profiles.keys(), key=lambda x: self.city_risk_profiles[x].adaptability_score)}")
        
        # Risk categories
        high_risk = [city for city, metrics in self.city_risk_profiles.items() if metrics.overall_risk_score > 0.6]
        low_adaptability = [city for city, metrics in self.city_risk_profiles.items() if metrics.adaptability_score < 0.4]
        urgent_action = list(set(high_risk) & set(low_adaptability))
        
        print(f"\n🚨 HIGH PRIORITY CITIES (Risk > 0.6): {len(high_risk)}")
        for city in high_risk:
            risk = self.city_risk_profiles[city].overall_risk_score
            adapt = self.city_risk_profiles[city].adaptability_score
            print(f"   {city}: Risk={risk:.3f}, Adaptability={adapt:.3f}")
        
        print(f"\n⚠️  URGENT ACTION NEEDED: {len(urgent_action)}")
        for city in urgent_action:
            print(f"   {city}: High risk + Low adaptability")
        
        print(f"\n📈 CLIMATE TRENDS:")
        temp_trends = [metrics.temperature_trend for metrics in self.city_risk_profiles.values() if metrics.temperature_trend != 0]
        if temp_trends:
            print(f"   Average Temperature Trend: {np.mean(temp_trends):.4f} °C/year")
            warming_cities = [city for city, metrics in self.city_risk_profiles.items() if metrics.temperature_trend > 0.05]
            print(f"   Rapidly Warming Cities (>0.05°C/yr): {len(warming_cities)}")
        
        print("="*80)
    
    def run_comprehensive_assessment(self):
        """Run complete IPCC AR6-based climate assessment"""
        print("Starting comprehensive IPCC AR6 climate risk assessment...")
        
        # Run full assessment
        self.run_full_assessment()
        
        # Generate visualizations
        self.create_risk_assessment_dashboard()
        self.create_adaptability_ranking_table()
        
        # Generate report
        self.generate_assessment_report()
        
        print(f"\n✅ Assessment complete. Results saved to: {self.output_path}")
        return self.city_risk_profiles


def main():
    """Main execution function for climate risk assessment"""
    base_path = "/Users/timursabitov/Dev/Uzbekistan_URBAN_research/suhi_analysis_output"
    
    # Create assessment instance
    assessment = IPCCClimateRiskAssessment(base_path)
    
    # Run comprehensive assessment
    results = assessment.run_comprehensive_assessment()
    
    return results


if __name__ == "__main__":
    main()
