"""
Earth Engine utilities and authentication
"""

import ee
from typing import Dict, Any


def initialize_gee() -> bool:
    """
    Initialize Google Earth Engine with proper authentication
    Returns True if successful, False otherwise
    """
    try:
        print("🔑 Initializing Google Earth Engine...")
        ee.Initialize(project='ee-sabitovty')
        print("✅ Google Earth Engine initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ GEE Authentication failed: {e}")
        try:
            print("Attempting interactive authentication...")
            ee.Authenticate()
            ee.Initialize(project='ee-sabitovty')
            print("✅ Google Earth Engine initialized successfully after authentication!")
            return True
        except Exception as e2:
            print(f"❌ Authentication still failed: {e2}")
            return False


def test_dataset_availability() -> Dict[str, bool]:
    """Test availability of key datasets"""
    from .config import DATASETS
    
    print("\n🔍 Testing dataset availability...")
    status = {}
    
    for name, dataset_id in DATASETS.items():
        try:
            if "ImageCollection" in str(type(ee.ImageCollection(dataset_id))):
                collection = ee.ImageCollection(dataset_id)
                size = collection.size().getInfo()
                status[name] = True
                print(f"   ✅ {name}: {size} images")
            else:
                # Single image dataset
                image = ee.Image(dataset_id)
                bands = image.bandNames().getInfo()
                status[name] = True
                print(f"   ✅ {name}: {len(bands)} bands")
        except Exception as e:
            status[name] = False
            print(f"   ❌ {name}: {str(e)[:100]}...")
    
    return status


class RateLimiter:
    """Simple rate limiter to avoid GEE quota issues"""
    def __init__(self, min_interval=2):
        self.min_interval = min_interval
        self.last_call = 0
    
    def wait(self):
        import time
        current_time = time.time()
        time_since_last = current_time - self.last_call
        if time_since_last < self.min_interval:
            time.sleep(self.min_interval - time_since_last)
        self.last_call = time.time()


# Global rate limiter instance
rate_limiter = RateLimiter()