"""
Land surface temperature data processing
"""

import ee
from typing import Dict, Optional, Tuple
from ..config import DATASETS, GEEConfig
from ..utils.gee_utils import rate_limiter


def load_modis_lst(start_date: str, end_date: str, geometry: ee.Geometry, 
                   gee_config: GEEConfig) -> Optional[ee.Image]:
    """
    Load and process MODIS Land Surface Temperature data
    """
    try:
        print("   🌡️ Loading MODIS LST data...")
        
        collection = (ee.ImageCollection(DATASETS["modis_lst"])
                     .filterDate(start_date, end_date)
                     .filterBounds(geometry)
                     .select(['LST_Day_1km', 'LST_Night_1km', 'QC_Day', 'QC_Night']))
        
        # Apply quality filtering
        def apply_qa_mask(image):
            qa_day = image.select('QC_Day')
            qa_night = image.select('QC_Night')
            
            # LST produced, good quality
            good_quality_day = qa_day.bitwiseAnd(0x03).eq(0)  # Bits 0-1 = 00
            good_quality_night = qa_night.bitwiseAnd(0x03).eq(0)
            
            return image.updateMask(good_quality_day.And(good_quality_night))
        
        # Filter and mosaic
        filtered = collection.map(apply_qa_mask)
        
        if filtered.size().getInfo() == 0:
            print("   ⚠️ No valid MODIS LST images found")
            return None
        
        # Create median composite and convert to Celsius
        composite = filtered.median()
        lst_celsius = composite.select(['LST_Day_1km', 'LST_Night_1km']).multiply(0.02).subtract(273.15)
        
        # Rename bands for clarity
        lst_final = lst_celsius.select(['LST_Day_1km', 'LST_Night_1km'], 
                                     ['LST_Day', 'LST_Night']).clip(geometry)
        
        print(f"   ✅ MODIS LST loaded ({filtered.size().getInfo()} images)")
        return lst_final
        
    except Exception as e:
        print(f"   ❌ MODIS LST loading failed: {e}")
        return None


def calculate_suhi(lst_image: ee.Image, urban_mask: ee.Image, rural_mask: ee.Image,
                   gee_config: GEEConfig) -> Dict:
    """
    Calculate Surface Urban Heat Island intensity
    """
    try:
        # Calculate urban and rural temperature statistics
        urban_stats = lst_image.select('LST_Day').reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.stdDev(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.count(),
                sharedInputs=True
            ),
            geometry=urban_mask.geometry(),
            scale=gee_config.scale_modis,
            maxPixels=gee_config.max_pixels,
            bestEffort=gee_config.best_effort
        ).getInfo()
        
        rural_stats = lst_image.select('LST_Day').reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.stdDev(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.count(),
                sharedInputs=True
            ),
            geometry=rural_mask.geometry(),
            scale=gee_config.scale_modis,
            maxPixels=gee_config.max_pixels,
            bestEffort=gee_config.best_effort
        ).getInfo()
        
        # Calculate SUHI intensity
        urban_temp = urban_stats.get('LST_Day_mean', 0)
        rural_temp = rural_stats.get('LST_Day_mean', 0)
        
        if urban_temp != 0 and rural_temp != 0:
            suhi_intensity = urban_temp - rural_temp
            
            return {
                'suhi_intensity': suhi_intensity,
                'urban_temperature': urban_temp,
                'rural_temperature': rural_temp,
                'urban_std': urban_stats.get('LST_Day_stdDev', 0),
                'rural_std': rural_stats.get('LST_Day_stdDev', 0),
                'urban_pixel_count': urban_stats.get('LST_Day_count', 0),
                'rural_pixel_count': rural_stats.get('LST_Day_count', 0)
            }
        else:
            return {'error': 'Invalid temperature data'}
            
    except Exception as e:
        return {'error': f'SUHI calculation failed: {str(e)}'}


def export_raster(image: ee.Image, geometry: ee.Geometry, filename: str, 
                  scale: int, output_dir) -> bool:
    """
    Export Earth Engine image as GeoTIFF raster
    """
    try:
        # Create export task
        task = ee.batch.Export.image.toDrive(
            image=image,
            description=filename,
            scale=scale,
            region=geometry,
            maxPixels=1e13,
            crs='EPSG:4326'
        )
        
        # Start the task
        task.start()
        
        print(f"   📤 Export task started for {filename}")
        print(f"   📋 Task ID: {task.id}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Export failed for {filename}: {e}")
        return False