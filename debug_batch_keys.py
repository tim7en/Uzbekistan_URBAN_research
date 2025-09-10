"""Debug the exact keys being returned from batch compute."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

import ee
from services.gee import initialize_gee
from services.utils import UZBEKISTAN_CITIES
from services.classification import load_all_classifications
from services.spatial_relationships import _make_veg_mask, _make_built_mask, reduce_region

def debug_batch_keys(city='Tashkent', year=2024):
    print(f"🔍 Debugging batch compute keys for {city} {year}")
    print("=" * 60)
    
    # Initialize GEE
    ok = initialize_gee()
    if not ok:
        return
    
    # Setup region
    city_info = UZBEKISTAN_CITIES[city]
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    region = center.buffer(city_info['buffer_m'])
    scale = 100
    
    # Load ESRI data
    classifications = load_all_classifications(
        year, region, f"{year}-01-01", f"{year}-12-31",
        optimal_scales={'scale': max(200, scale)}
    )
    esri_full = classifications.get('esri_full')
    
    # Create masks
    veg_mask = _make_veg_mask(esri_full, region, scale)
    built_mask = _make_built_mask(esri_full, None, region, scale)
    
    print("🌱 Creating distance calculation...")
    
    # Fixed distance calculation
    veg_distance = veg_mask.fastDistanceTransform(
        neighborhood=int(3000 / scale),  # 30 pixels at 100m scale
        units='pixels',
        metric='squared_euclidean'
    ).sqrt().multiply(scale)  # Convert back to meters
    
    built_distance = veg_distance.updateMask(built_mask)
    
    print("📊 Testing built distance stats...")
    
    # Test the exact same reduceRegion call as in the function
    built_stats = built_distance.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            ee.Reducer.stdDev(),
            sharedInputs=True
        ).combine(
            ee.Reducer.min(),
            sharedInputs=True
        ).combine(
            ee.Reducer.max(),
            sharedInputs=True
        ),
        geometry=region,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
        tileScale=4
    )
    
    print("🔄 Getting info...")
    results = built_stats.getInfo()
    
    print("📋 Exact keys and values returned:")
    for key, value in results.items():
        print(f"   '{key}': {value} (type: {type(value)})")
    
    # Test sample
    print("\n📊 Testing sample...")
    sample = built_distance.rename('distance').sample(
        region=region,
        scale=scale,
        numPixels=50,
        geometries=False,
        tileScale=4
    ).getInfo()
    
    if sample and sample.get('features'):
        print(f"   Sample has {len(sample['features'])} features")
        first_feature = sample['features'][0]
        print(f"   First feature keys: {list(first_feature.get('properties', {}).keys())}")
        distances = [f['properties'].get('distance', 0) for f in sample['features']]
        print(f"   Distance range: {min(distances):.1f} - {max(distances):.1f}")
    else:
        print("   ❌ No sample data")

if __name__ == '__main__':
    debug_batch_keys('Tashkent', 2024)
