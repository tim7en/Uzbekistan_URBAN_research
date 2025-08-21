"""Vegetation index calculations from Landsat."""
import ee
from .utils import DATASETS, ANALYSIS_CONFIG


def calculate_vegetation_indices(start_date: str, end_date: str, geometry: ee.Geometry, target_scale: int = 30):
    def process_landsat_sr(image):
        qa = image.select('QA_PIXEL')
        mask = (qa.bitwiseAnd(1<<3).eq(0).And(qa.bitwiseAnd(1<<4).eq(0)))
        optical = image.select(['SR_B2','SR_B3','SR_B4','SR_B5','SR_B6','SR_B7'])
        optical = optical.multiply(0.0000275).add(-0.2).clamp(0,1)
        ndvi = optical.normalizedDifference(['SR_B5','SR_B4']).rename('NDVI')
        ndbi = optical.normalizedDifference(['SR_B6','SR_B5']).rename('NDBI')
        ndwi = optical.normalizedDifference(['SR_B3','SR_B5']).rename('NDWI')
        result = ee.Image.cat([ndvi, ndbi, ndwi]).updateMask(mask)
        if target_scale != 30:
            result = result.reproject(crs='EPSG:4326', scale=target_scale)
        return result
    l8 = ee.ImageCollection(DATASETS['landsat8'])
    l9 = ee.ImageCollection(DATASETS['landsat9'])
    collection = (l8.merge(l9).filterDate(start_date,end_date).filterBounds(geometry).filter(ee.Filter.lt('CLOUD_COVER', ANALYSIS_CONFIG['cloud_threshold'])).map(process_landsat_sr))
    return collection.median()
