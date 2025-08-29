"""Utility constants and helpers for SUHI analysis."""
from pathlib import Path
import time
import numpy as np
from typing import Dict, Union
from pathlib import Path
import ee

# Rate limiter
class RateLimiter:
    def __init__(self, min_interval=2):
        self.min_interval = min_interval
        self.last_call = 0
    def wait(self):
        current = time.time()
        elapsed = current - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()

# City list and configs (extracted from monolith)
UZBEKISTAN_CITIES = {
    "Tashkent":   {"lat": 41.2995, "lon": 69.2401, "buffer_m": 15000, "type": "capital", "population": 3058400},
    "Nukus":      {"lat": 42.4731, "lon": 59.6103, "buffer_m": 10000, "type": "republic_capital", "population": 339200},
    "Andijan":    {"lat": 40.7821, "lon": 72.3442, "buffer_m": 12000, "type": "regional_capital", "population": 480800},
    "Bukhara":    {"lat": 39.7748, "lon": 64.4286, "buffer_m": 10000, "type": "regional_capital", "population": 269500},
    "Samarkand":  {"lat": 39.6542, "lon": 66.9597, "buffer_m": 12000, "type": "regional_capital", "population": 585200},
    "Namangan":   {"lat": 40.9983, "lon": 71.6726, "buffer_m": 12000, "type": "regional_capital", "population": 696500},
    "Jizzakh":    {"lat": 40.1158, "lon": 67.8422, "buffer_m": 8000,  "type": "regional_capital", "population": 195800},
    "Qarshi":     {"lat": 38.8606, "lon": 65.7887, "buffer_m": 8000,  "type": "regional_capital", "population": 295600},
    "Navoiy":     {"lat": 40.1030, "lon": 65.3686, "buffer_m": 10000, "type": "regional_capital", "population": 161300},
    "Termez":     {"lat": 37.2242, "lon": 67.2783, "buffer_m": 8000,  "type": "regional_capital", "population": 201600},
    "Gulistan":   {"lat": 40.4910, "lon": 68.7810, "buffer_m": 8000,  "type": "regional_capital", "population": 77300},
    "Nurafshon":  {"lat": 41.0167, "lon": 69.3417, "buffer_m": 8000, "type": "city", "population": 56200},
    "Fergana":    {"lat": 40.3842, "lon": 71.7843, "buffer_m": 12000, "type": "regional_capital", "population": 321800},
    "Urgench":    {"lat": 41.5506, "lon": 60.6317, "buffer_m": 10000, "type": "regional_capital", "population": 153100},
}


ANALYSIS_CONFIG = {
    "years": list(range(2016, 2025)),  # Updated to include 2024
    "warm_months": [6,7,8],
    "target_resolution_m": 100,
    "esri_weight": 0.5,
    "rural_buffer_km": 25,
    "min_urban_pixels": 10,
    "min_rural_pixels": 25,
    "cloud_threshold": 20,
    "water_occurrence_threshold": 25,
}

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
    # Nighttime lights datasets
    "viirs_monthly": "NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG",
    "dmsp_ols": "NOAA/DMSP-OLS/NIGHTTIME_LIGHTS",
    # Sentinel air quality datasets (using NRTI collections with available data)
    # Prefer OFFL (final) collections for historical analysis; fall back to NRTI if needed
    "sentinel5p_no2": "COPERNICUS/S5P/OFFL/L3_NO2",
    "sentinel5p_o3": "COPERNICUS/S5P/OFFL/L3_O3",
    "sentinel5p_so2": "COPERNICUS/S5P/OFFL/L3_SO2",
    "sentinel5p_co": "COPERNICUS/S5P/OFFL/L3_CO",
    "sentinel5p_ch4": "COPERNICUS/S5P/OFFL/L3_CH4",  # OFFL may have limited coverage; use carefully
    "sentinel5p_aerosol": "COPERNICUS/S5P/OFFL/L3_AER_AI",
    "sentinel2_aod": "COPERNICUS/S2_SR_HARMONIZED",
    "sentinel3_olci": "COPERNICUS/S3/OLCI",
}

GEE_CONFIG = {
    "max_pixels": 5e8,
    "scale": 10,
    "scale_modis": 1000,
    "scale_landsat": 30,
    "scale_s5p": 7500,  # 🔥 OPTIMIZATION: Proper S5P scale (7-10km footprint)
    "best_effort": True,
    "tile_scale": 4,    # 🔥 OPTIMIZATION: Better tile scaling for S5P
}

ESRI_CLASSES = {
    1: 'Water', 2: 'Trees', 4: 'Flooded_Vegetation', 5: 'Crops', 7: 'Built_Area',
    8: 'Bare_Ground', 9: 'Snow_Ice', 10: 'Clouds', 11: 'Rangeland'
}


def get_optimal_scale_for_city(city_name: str, analysis_phase: str = "default") -> Dict[str, Union[int, float]]:
    city_info = UZBEKISTAN_CITIES[city_name]
    buffer_m = city_info['buffer_m']
    if analysis_phase == "detailed_validation":
        if buffer_m >= 15000:
            return {'scale':200,'scale_modis':1000,'scale_landsat':200,'tileScale':16,'maxPixels':5e7}
        elif buffer_m >= 12000:
            return {'scale':200,'scale_modis':1000,'scale_landsat':200,'tileScale':16,'maxPixels':5e7}
        else:
            return {'scale':150,'scale_modis':1000,'scale_landsat':150,'tileScale':8,'maxPixels':1e8}
    elif analysis_phase == "fallback":
        return {'scale':500,'scale_modis':2000,'scale_landsat':500,'tileScale':32,'maxPixels':1e7}
    else:
        if buffer_m >= 15000:
            return {'scale':30,'scale_modis':1000,'scale_landsat':60,'tileScale':8,'maxPixels':1e8}
        elif buffer_m >= 12000:
            return {'scale':20,'scale_modis':1000,'scale_landsat':30,'tileScale':4,'maxPixels':5e8}
        else:
            return {'scale':10,'scale_modis':1000,'scale_landsat':30,'tileScale':2,'maxPixels':1e9}


def create_output_directories() -> Dict[str, Path]:
    try:
        base_root = Path(__file__).parent.parent
    except Exception:
        base_root = Path.cwd()
    base_dir = base_root / "suhi_analysis_output"
    sub = ["data","classification","temperature","vegetation","visualizations","reports","error_analysis"]
    dirs = {'base': base_dir, **{k: base_dir / k for k in sub}}
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output directories created: {base_dir}")
    return dirs


def make_json_safe(v):
    """Recursively convert common EE objects and non-JSON types to JSON-serializable Python types.

    This helper attempts to call getInfo() on Earth Engine objects when available
    and falls back to safe Python casts. It is intentionally permissive to avoid
    write-time failures when saving analysis summaries.
    """
    try:
        import ee as _ee
    except Exception:
        _ee = None

    # primitive types
    if v is None or isinstance(v, (str, bool, int, float)):
        return v
    # containers
    if isinstance(v, dict):
        return {k: make_json_safe(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [make_json_safe(x) for x in v]

    # Earth Engine types
    if _ee is not None:
        try:
            if isinstance(v, (_ee.Number, _ee.String, _ee.List, _ee.Dictionary)):
                try:
                    info = v.getInfo()
                    return make_json_safe(info)
                except Exception:
                    return str(v)
            if isinstance(v, (_ee.Image, _ee.Geometry, _ee.FeatureCollection, _ee.Feature)):
                return str(v)
        except Exception:
            # If ee is not behaving as expected, continue to fallbacks
            pass

    # numpy scalars
    try:
        import numpy as _np
        if isinstance(v, (_np.floating, _np.integer)):
            return float(v)
    except Exception:
        pass

    # final fallbacks
    try:
        return float(v)
    except Exception:
        try:
            return str(v)
        except Exception:
            return None


def create_analysis_zones(city_info: Dict, erosion_distance: int = 100) -> Dict[str, ee.Geometry]:
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    urban_buffer = center.buffer(city_info['buffer_m'])
    rural_outer = center.buffer(city_info['buffer_m'] + ANALYSIS_CONFIG['rural_buffer_km'] * 1000)
    rural_ring = rural_outer.difference(urban_buffer)
    urban_core = urban_buffer.buffer(-erosion_distance)
    rural_ring_clean = rural_ring.buffer(-erosion_distance)
    return {'urban_core': urban_core, 'rural_ring': rural_ring_clean, 'full_extent': rural_outer}


# Global rate limiter for pipeline
rate_limiter = RateLimiter(min_interval=3)
