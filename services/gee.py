"""GEE initialization and dataset availability checks."""
import ee
from typing import Dict
from .utils import DATASETS, GEE_CONFIG


def initialize_gee(project_id: str = 'ee-sabitovty') -> bool:
    try:
        print("🔑 Initializing Google Earth Engine...")
        try:
            ee.Authenticate()
            print("   ✅ Authentication successful")
        except Exception as auth_error:
            print(f"   ⚠️ Authentication skipped: {auth_error}")
        ee.Initialize(project=project_id)
        _ = ee.Image(1).getInfo()
        print("✅ GEE initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ GEE initialization failed: {e}")
        return False


def test_dataset_availability() -> Dict[str, bool]:
    availability = {}
    print("🔍 Testing dataset availability...")
    try:
        esri_collection = ee.ImageCollection(DATASETS['esri_lulc'])
        size = esri_collection.size().getInfo()
        availability['esri_lulc'] = size > 0
        print(f"   📊 ESRI Global LULC: {size} images available")
    except Exception as e:
        availability['esri_lulc'] = False
        print(f"   ❌ ESRI Global LULC: {e}")

    for name in ['modis_lst','landsat8','dynamic_world']:
        try:
            collection = ee.ImageCollection(DATASETS[name]).limit(1)
            size = collection.size().getInfo()
            availability[name] = size > 0
            print(f"   📊 {name}: {'✅' if size > 0 else '❌'}")
        except Exception as e:
            availability[name] = False
            print(f"   ❌ {name}: {e}")
    return availability
