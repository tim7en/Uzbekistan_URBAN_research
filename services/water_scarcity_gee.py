"""GEE-backed water scarcity data loader and assessment wrapper.

This module provides a class `WaterScarcityGEEAssessment` that mirrors the
API of `WaterScarcityAssessmentService` but loads indicators from Earth Engine
collections (CHIRPS, ERA5, JRC GSW, WorldCover) when available.

The implementations use EE client calls and include local JSON caching so
re-runs don't always hit GEE. If the `ee` library or authentication is not
available the class raises a clear RuntimeError.

Note: This file is written to be safe and readable; you can replace dataset
IDs with your preferred collections or asset paths.
"""
from pathlib import Path
import json
import numpy as np
from dataclasses import dataclass
from typing import Dict, Any

try:
    import ee
except Exception:
    ee = None

from services.water_scarcity_assessment import WaterScarcityMetrics
from services.utils import UZBEKISTAN_CITIES
import math

CACHE_DIR = Path('suhi_analysis_output') / 'data' / 'water_scarcity'
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class WaterScarcityGEEAssessment:
    """Load water indicators from GEE and compute water scarcity scores.

    Public methods:
      - assess_city_water_scarcity(city) -> WaterScarcityMetrics
      - get_water_scarcity_summary() -> dict
      - export_water_scarcity_data(output_path)

    Requires EE to be initialized externally (via services.gee.initialize_gee()).
    """

    # Default dataset IDs (replace if you prefer other collections)
    DATASETS = {
        'chirps': 'UCSB-CHG/CHIRPS/DAILY',
        'era5': 'ECMWF/ERA5/DAILY',
        'jrc_gsw': 'JRC/GSW1_4/GlobalSurfaceWater',
        'worldcover': 'ESA/WorldCover/v200',  # Fixed: v200 is the latest
        'gpw': 'CIESIN/GPWv411/GPW_UNWPP-Adjusted_Population_Density/gpw_v4_unwpp-adjusted_population_density_rev11_2020_30_sec',
    }

    def __init__(self, data_loader):
        if ee is None:
            raise RuntimeError('Earth Engine python API not available in this environment')
        self.data_loader = data_loader
        self.water_data: Dict[str, WaterScarcityMetrics] = {}
        # Prefer authoritative city coordinates from utils
        self.city_definitions = {}
        for city, v in UZBEKISTAN_CITIES.items():
            self.city_definitions[city] = {
                "lon": v['lon'], 
                "lat": v['lat'], 
                'urban_radius_m': v.get('buffer_m', 8000)
            }
        
        # Load existing LULC data for cropland fraction
        self.lulc_data = self._load_existing_lulc_data()
        
        # Load existing population/area data
        self.city_population_data = self._load_city_population_data()
    
    def _load_existing_lulc_data(self):
        """Load existing LULC analysis data for cropland fraction"""
        lulc_file = Path('suhi_analysis_output') / 'reports' / 'lulc_analysis_summary.json'
        lulc_data = {}
        
        if lulc_file.exists():
            try:
                with open(lulc_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for city_entry in data:
                    city = city_entry.get('city')
                    if city:
                        lulc_data[city] = {}
                        areas_m2 = city_entry.get('areas_m2', {})
                        
                        # Get latest year data
                        if areas_m2:
                            latest_year = max(areas_m2.keys(), key=int)
                            crops_data = areas_m2[latest_year].get('Crops', {})
                            cropland_pct = crops_data.get('percentage', 0.0)
                            lulc_data[city]['cropland_fraction'] = cropland_pct / 100.0  # Convert to fraction
                            
            except Exception as e:
                print(f"Warning: Could not load LULC data: {e}")
        
        return lulc_data
    
    def _load_city_population_data(self):
        """Load population and area data from climate data loader"""
        # Import here to avoid circular imports
        from services.climate_data_loader import UZBEK_CITIES_DATA
        
        pop_data = {}
        for city, data in UZBEK_CITIES_DATA.items():
            pop_data[city] = {
                'population': data.get('pop_2024', 100000),
                'area_km2': data.get('area_km2', 50.0),
                'density': data.get('pop_2024', 100000) / data.get('area_km2', 50.0) if data.get('area_km2', 50.0) > 0 else 1000.0
            }
        
        return pop_data

    def _cache_path(self, city: str) -> Path:
        return CACHE_DIR / f"{city.replace(' ', '_')}_water_indicators.json"

    def _load_cached(self, city: str):
        p = self._cache_path(city)
        if p.exists():
            try:
                return json.loads(p.read_text(encoding='utf-8'))
            except Exception:
                return None
        return None

    def _save_cached(self, city: str, data: Dict[str, Any]):
        p = self._cache_path(city)
        with open(p, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, indent=2)

    def _fetch_city_indicators(self, city: str) -> Dict[str, Any]:
        """Fetch indicators for a single city from GEE and return a JSON-serializable dict.

        Indicators produced:
          - aridity_index (P/PET, median multi-year)
          - climatic_water_deficit (proxy, mm/yr)
          - drought_frequency (fraction months with very low precip)
          - surface_water_change (percent change from JRC GSW)
          - cropland_fraction (percent from WorldCover)
          - population_density (GPW 2020 estimate)
          - aqueduct_bws_score (if available via local lookup it's left as None)
        """
        # Try cache first
        cached = self._load_cached(city)
        if cached:
            return cached

        # Use optimized EE workflow: build monthly time series server-side, one getInfo() call
        try:
            # Create a point geometry from data_loader city definitions when available
            if city in self.city_definitions:
                cd = self.city_definitions[city]
                geom = ee.Geometry.Point([cd['lon'], cd['lat']])
                lat = float(cd.get('lat', 0.0))
            else:
                # Fallback: try to use a city centroid from utils mapping
                geom = ee.Geometry.Point([0, 0])
                lat = 0.0

            # Collections
            chirps = ee.ImageCollection(self.DATASETS['chirps']).filterDate('2001-01-01', '2020-12-31')
            era5 = ee.ImageCollection(self.DATASETS['era5']).select(['mean_2m_air_temperature'])
            jrc = ee.Image(self.DATASETS['jrc_gsw']).select('occurrence')
            worldcover = ee.Image(self.DATASETS['worldcover'])
            gpw = ee.Image(self.DATASETS['gpw']).select('population_density')

            # Use circular buffer, not bounds (smaller area)
            buf = geom.buffer(5000)

            # Build monthly images server-side (240 months: 2001-01 to 2020-12)
            months = ee.List.sequence(0, 239)

            def month_img(m):
                m = ee.Number(m)
                start = ee.Date('2001-01-01').advance(m, 'month')
                end = start.advance(1, 'month')
                # Monthly precipitation total
                p = chirps.filterDate(start, end).sum().rename('P')
                # Monthly mean temperature
                t = era5.filterDate(start, end).mean().rename('T')
                return p.addBands(t).set({'start': start, 'month': m})

            monthly = ee.ImageCollection(months.map(month_img))

            # Reduce to region once per image, collect on server
            def region_stats(img):
                stats = img.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=buf,
                    scale=2500,  # coarser scale for speed
                    bestEffort=True,
                    maxPixels=1e9
                )
                return ee.Feature(None, stats).set({'month': img.get('month')})

            fc = monthly.map(region_stats)

            # Pull arrays in ONE getInfo() call
            P_array = fc.aggregate_array('P')
            T_array = fc.aggregate_array('T')  # Kelvin
            month_array = fc.aggregate_array('month')

            vals = ee.Dictionary({
                'P': P_array,
                'T': T_array,
                'months': month_array
            }).getInfo()

            # Extract to Python lists
            monthly_precip = [float(x) if x is not None else 0.0 for x in vals['P']]
            monthly_temp_k = [float(x) if x is not None else 273.15 for x in vals['T']]

            if len(monthly_precip) != 240 or len(monthly_temp_k) != 240:
                # Fill missing values with reasonable defaults
                while len(monthly_precip) < 240:
                    monthly_precip.append(0.0)
                while len(monthly_temp_k) < 240:
                    monthly_temp_k.append(273.15 + 15.0)  # 15°C default
                
                # Trim if too many (shouldn't happen but be safe)
                monthly_precip = monthly_precip[:240]
                monthly_temp_k = monthly_temp_k[:240]

            # Convert temp to Celsius
            monthly_temp_c = [t - 273.15 for t in monthly_temp_k]

            # Compute PET and water balance locally (fast)
            days_in_month = [31,28,31,30,31,30,31,31,30,31,30,31]
            monthly_pet = []
            D_values = []  # Palmer Drought Severity Index proxy

            # Compute annual heat index I for each year
            for yy in range(2001, 2021):
                year_idx = (yy - 2001) * 12
                temps_year = monthly_temp_c[year_idx:year_idx+12]

                I = 0.0
                for T in temps_year:
                    if T > 0:
                        I += (T / 5.0) ** 1.514

                a = (6.75e-7) * (I ** 3) - (7.71e-5) * (I ** 2) + (1.792e-2) * I + 0.49239 if I > 0 else 0.0

                for m_idx in range(12):
                    T = temps_year[m_idx]
                    m = m_idx + 1
                    P = monthly_precip[year_idx + m_idx]

                    if T <= 0 or I <= 0:
                        pet = 0.0
                    else:
                        # Daylength correction for Thornthwaite
                        day_of_year = sum(days_in_month[:m-1]) + 15
                        decl = 23.45 * math.sin(2 * math.pi * (284 + day_of_year) / 365.0) * math.pi / 180.0
                        lat_rad = float(lat) * math.pi / 180.0
                        cos_omega = -math.tan(lat_rad) * math.tan(decl)
                        cos_omega = max(-1.0, min(1.0, cos_omega))
                        omega = math.acos(cos_omega)
                        daylength = 2.0 * omega * 24.0 / (2.0 * math.pi)
                        daylength_factor = max(0.1, min(2.0, daylength / 12.0))

                        pet_month = 16.0 * ((10.0 * T / I) ** a) if I > 0 else 0.0
                        pet = pet_month * (days_in_month[m-1] / 30.0) * daylength_factor

                    monthly_pet.append(pet)
                    D_values.append(P - pet)

            # Compute annual averages
            n_years = 20
            mean_annual_precip = sum(monthly_precip) / n_years
            mean_annual_pet = sum(monthly_pet) / n_years
            aridity_index = float(max(0.001, min(1.0, mean_annual_precip / max(1e-6, mean_annual_pet))))

            # Climatic water deficit (average annual unmet demand)
            cwd_total = 0.0
            for p, pet in zip(monthly_precip, monthly_pet):
                if pet > p:
                    cwd_total += (pet - p)
            climatic_water_deficit = float(cwd_total / n_years)

            # Drought frequency using PDSI proxy (z-score of D values)
            import statistics
            mean_D = statistics.mean(D_values)
            stdev_D = statistics.pstdev(D_values) if len(D_values) > 1 else 0.0
            drought_months = 0
            for D in D_values:
                z = (D - mean_D) / stdev_D if stdev_D > 0 else 0.0
                if z < -1.0:  # PDSI < -1 indicates drought
                    drought_months += 1
            drought_frequency = float(drought_months / len(D_values))

            # Fetch one-off indicators with single calls - use larger buffer for land cover
            land_buf = geom.buffer(10000)  # Larger buffer for land cover data
            
            try:
                jrc_occurrence = jrc.reduceRegion(
                    ee.Reducer.mean(), buf, 2500,
                    bestEffort=True, maxPixels=1e9
                )
                jrc_val = float(jrc_occurrence.get('occurrence').getInfo()) if jrc_occurrence.get('occurrence') else 0.0
            except Exception as e:
                print(f"Warning: JRC data failed for {city}: {e}")
                jrc_val = 0.0

            try:
                # WorldCover 2020 uses 'Map' band with class values
                wc_result = worldcover.reduceRegion(
                    ee.Reducer.frequencyHistogram(), land_buf, 100,
                    bestEffort=True, maxPixels=1e9
                )
                hist = wc_result.getInfo()
                if 'Map' in hist:
                    class_counts = hist['Map']
                    total_pixels = sum(class_counts.values())
                    # Class 40 = cropland in ESA WorldCover
                    cropland_pixels = class_counts.get('40', 0)
                    cropland_fraction = float(cropland_pixels) / float(total_pixels) if total_pixels > 0 else 0.0
                    print(f"Debug {city}: WorldCover total_pixels={total_pixels}, cropland_pixels={cropland_pixels}, fraction={cropland_fraction}")
                else:
                    print(f"Debug {city}: WorldCover 'Map' band not found in result")
                    cropland_fraction = 0.0
            except Exception as e:
                print(f"Warning: WorldCover data failed for {city}: {e}")
                cropland_fraction = 0.0

            # Override with existing LULC data if available (preferred over WorldCover)
            existing_cropland = self.lulc_data.get(city, {}).get('cropland_fraction', None)
            if existing_cropland is not None:
                cropland_fraction = existing_cropland
                print(f"Debug {city}: Using existing LULC cropland fraction={cropland_fraction}")

            try:
                # GPW v411 uses 'population_density' band
                pop_result = gpw.reduceRegion(
                    ee.Reducer.mean(), land_buf, 1000,
                    bestEffort=True, maxPixels=1e9
                )
                pop_val = float(pop_result.get('population_density').getInfo()) if pop_result.get('population_density') else 100.0
                print(f"Debug {city}: GPW population_density={pop_val}")
            except Exception as e:
                print(f"Warning: GPW data failed for {city}: {e}")
                pop_val = 100.0

            # Override with existing population data if available (preferred over GPW)
            existing_pop_data = self.city_population_data.get(city, {})
            if existing_pop_data:
                pop_val = existing_pop_data.get('density', pop_val)
                print(f"Debug {city}: Using existing population density={pop_val}")

            indicators = {
                'aridity_index': aridity_index,
                'climatic_water_deficit': climatic_water_deficit,
                'drought_frequency': drought_frequency,
                'surface_water_change': -float(jrc_val),  # negative = loss
                'cropland_fraction': float(cropland_fraction),
                'population_density': float(pop_val),
                'aqueduct_bws_score': None
            }

            # Cache and return
            self._save_cached(city, indicators)
            return indicators

        except Exception as e:
            # If GEE calls fail, raise a runtime error so caller can fallback
            raise RuntimeError(f"GEE data fetch failed for {city}: {e}")

    def _compute_scores(self, raw: Dict[str, Any], city: str) -> WaterScarcityMetrics:
        # Map raw indicators into normalized risk components and final score
        ai = raw.get('aridity_index', 0.2)
        cwd = raw.get('climatic_water_deficit', 500)
        df = raw.get('drought_frequency', 0.1)
        swc = raw.get('surface_water_change', -10)
        cropland = raw.get('cropland_fraction', 0.1)
        pop = raw.get('population_density', 100)
        aqu = raw.get('aqueduct_bws_score', 3.0) if raw.get('aqueduct_bws_score') is not None else 3.0

        # Normalize each into 0-1 (simple robust scaling using plausible bounds)
        def norm(x, low, high):
            return float(max(0.0, min(1.0, (x - low) / (high - low)))) if high > low else 0.0

        ai_s = 1.0 - norm(ai, 0.05, 0.5)  # lower AI -> higher risk
        cwd_s = norm(cwd, 0, 1000)
        df_s = norm(df, 0.0, 0.5)
        swc_s = norm(-swc, 0, 100)  # negative change increases risk
        cropland_s = norm(cropland, 0.0, 0.5)
        pop_s = norm(pop, 50, 1000)
        aqu_s = norm(aqu, 1.0, 5.0)

        supply = 0.6 * (ai_s * 0.4 + cwd_s * 0.4 + df_s * 0.2) + 0.4 * swc_s
        demand = 0.7 * cropland_s + 0.3 * pop_s
        overall = 0.6 * supply + 0.4 * demand

        level = 'Low'
        if overall >= 0.7:
            level = 'Critical'
        elif overall >= 0.5:
            level = 'High'
        elif overall >= 0.3:
            level = 'Moderate'

        return WaterScarcityMetrics(
            city=city,
            aridity_index=ai,
            climatic_water_deficit=cwd,
            drought_frequency=df,
            surface_water_change=swc,
            cropland_fraction=cropland,
            population_density=pop,
            aqueduct_bws_score=aqu,
            water_supply_risk=float(supply),
            water_demand_risk=float(demand),
            overall_water_scarcity_score=float(overall),
            water_scarcity_level=level
        )

    def assess_city_water_scarcity(self, city: str) -> WaterScarcityMetrics:
        # Try cached WaterScarcityMetrics first
        if city in self.water_data:
            return self.water_data[city]
        # Try cached raw indicators
        try:
            raw = self._fetch_city_indicators(city)
            metrics = self._compute_scores(raw, city)
            self.water_data[city] = metrics
            return metrics
        except Exception as e:
            # Bubble up to caller so that fallback to simulator can occur
            raise

    def assess_all_cities_water_scarcity(self) -> Dict[str, WaterScarcityMetrics]:
        # Use all cities from UZBEKISTAN_CITIES for comprehensive assessment
        city_list = list(UZBEKISTAN_CITIES.keys())
        results = {}
        for city in city_list:
            try:
                results[city] = self.assess_city_water_scarcity(city)
            except Exception as e:
                print(f"Warning: Failed to assess {city}: {e}")
                continue
        return results

    def get_water_scarcity_summary(self) -> Dict[str, Any]:
        assessed = self.assess_all_cities_water_scarcity()
        scores = [m.overall_water_scarcity_score for m in assessed.values()]
        return {
            'total_cities': len(assessed),
            'average_water_scarcity_score': float(np.mean(scores)) if scores else None,
            'median_water_scarcity_score': float(np.median(scores)) if scores else None,
            'max_water_scarcity_score': float(np.max(scores)) if scores else None,
            'min_water_scarcity_score': float(np.min(scores)) if scores else None,
            'top_risk_cities': sorted([{'city': c, 'score': assessed[c].overall_water_scarcity_score} for c in assessed], key=lambda x: x['score'], reverse=True)[:5]
        }

    def export_water_scarcity_data(self, output_path: str):
        out = {}
        for c, m in self.water_data.items():
            out[c] = m.__dict__
        p = Path(output_path) / 'water_scarcity_gee_export.json'
        with open(p, 'w', encoding='utf-8') as fh:
            json.dump(out, fh, indent=2)
        print(f"✓ Exported GEE water scarcity data to {p}")
