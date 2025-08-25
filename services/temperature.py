"""Temperature dataset loading functions (MODIS, Landsat, ASTER)."""
import ee
from typing import Optional
from .utils import DATASETS, ANALYSIS_CONFIG


def load_modis_lst(start_date: str, end_date: str, geometry: ee.Geometry) -> Optional[ee.Image]:
    """Load MODIS LST data with day and night bands.
    
    Returns a composite image with two bands:
    - LST_Day_MODIS: Daytime land surface temperature in Celsius
    - LST_Night_MODIS: Nighttime land surface temperature in Celsius
    
    The function filters for warm months and applies proper scaling and unit conversion.
    Temperature values are clamped to reasonable ranges to remove outliers.
    """
    col = (ee.ImageCollection(DATASETS['modis_lst'])
           .filterDate(start_date, end_date)
           .filterBounds(geometry)
           .filter(ee.Filter.calendarRange(ANALYSIS_CONFIG['warm_months'][0], 
                                         ANALYSIS_CONFIG['warm_months'][-1], 'month')))
    
    if col.size().getInfo() == 0:
        return None
        
    comp = col.median()
    
    try:
        band_names = comp.bandNames().getInfo()
    except Exception:
        return None
        
    # Find day and night LST bands
    day_bands = [b for b in band_names if 'Day' in b and 'LST' in b]
    night_bands = [b for b in band_names if 'Night' in b and 'LST' in b]
    
    if not day_bands or not night_bands:
        return None
    
    # Process day LST: scale from Kelvin*50 to Celsius
    lst_day = (comp.select(day_bands[0])
              .multiply(0.02)  # Scale factor to convert to Kelvin
              .subtract(273.15)  # Convert Kelvin to Celsius
              .rename('LST_Day_MODIS')
              .clamp(-20, 60))  # Remove unrealistic values
    
    # Process night LST: scale from Kelvin*50 to Celsius  
    lst_night = (comp.select(night_bands[0])
                .multiply(0.02)  # Scale factor to convert to Kelvin
                .subtract(273.15)  # Convert Kelvin to Celsius
                .rename('LST_Night_MODIS') 
                .clamp(-20, 50))  # Remove unrealistic values (night typically cooler)
    
    return ee.Image.cat([lst_day, lst_night]).clip(geometry)


def load_landsat_thermal(start_date: str, end_date: str, geometry: ee.Geometry) -> Optional[ee.Image]:
    def proc(img):
        qa = img.select('QA_PIXEL')
        mask = (qa.bitwiseAnd(1<<3).eq(0).And(qa.bitwiseAnd(1<<4).eq(0)).And(qa.bitwiseAnd(1<<5).eq(0)).And(qa.bitwiseAnd(1<<2).eq(0)))
        st = img.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('LST_Landsat').clamp(-20,60)
        return st.updateMask(mask)
    l8 = ee.ImageCollection(DATASETS['landsat8'])
    l9 = ee.ImageCollection(DATASETS['landsat9'])
    col = (l8.merge(l9).filterDate(start_date,end_date).filterBounds(geometry).filter(ee.Filter.lt('CLOUD_COVER', ANALYSIS_CONFIG['cloud_threshold'])).map(proc))
    return col.median().clip(geometry)


def load_aster_lst(start_date: str, end_date: str, geometry: ee.Geometry) -> Optional[ee.Image]:
    def calculate_aster_lst(image):
        b13 = image.select('B13')
        b14 = image.select('B14')
        lst = (b13.add(b14).divide(2).multiply(0.00862).add(0.56).subtract(273.15).rename('LST_ASTER').clamp(-20,60))
        return lst
    collection = (ee.ImageCollection(DATASETS['aster']).filterDate(start_date,end_date).filterBounds(geometry).map(calculate_aster_lst))
    size = collection.size()
    return ee.Algorithms.If(size.gt(0), collection.median(), None)
