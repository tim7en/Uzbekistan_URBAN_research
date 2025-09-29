"""Quick test to check GAUL region names for Uzbekistan."""
import sys
from pathlib import Path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import ee
from services import gee

def test_gaul_regions():
    """Test what region names are available in GAUL for Uzbekistan."""
    
    # Initialize GEE
    success = gee.initialize_gee()
    if not success:
        print("❌ GEE init failed")
        return
    
    print("🗺️ Checking GAUL administrative regions for Uzbekistan...")
    
    try:
        # Load FAO GAUL administrative boundaries
        gaul = ee.FeatureCollection("FAO/GAUL_SIMPLIFIED_500m/2015/level1")
        
        # Filter for Uzbekistan regions
        uzbekistan_regions = gaul.filter(ee.Filter.eq('ADM0_NAME', 'Uzbekistan'))
        
        # Get all region names
        region_names = uzbekistan_regions.aggregate_array('ADM1_NAME').getInfo()
        
        print(f"✅ Found {len(region_names)} regions:")
        for i, name in enumerate(sorted(region_names)):
            print(f"  {i+1:2d}. {name}")
            
        # Test specific regions
        test_regions = ['Samarqand', 'Buxoro', 'Tashkent', 'Toshkent']
        
        print(f"\n🧪 Testing specific region queries:")
        for test_name in test_regions:
            try:
                region_feature = uzbekistan_regions.filter(ee.Filter.eq('ADM1_NAME', test_name)).first()
                if region_feature is not None:
                    geometry = region_feature.geometry()
                    area = geometry.area().getInfo()
                    print(f"  ✅ {test_name}: Found (area: {area/1e6:.0f} km²)")
                else:
                    print(f"  ❌ {test_name}: Not found")
            except Exception as e:
                print(f"  ❌ {test_name}: Error - {e}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    test_gaul_regions()