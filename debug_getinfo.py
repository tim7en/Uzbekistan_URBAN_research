"""Debug what the getInfo() is actually returning."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

import ee
from services.gee import initialize_gee
from services.utils import UZBEKISTAN_CITIES
from services.classification import load_all_classifications

def debug_getinfo_results(city='Tashkent', year=2024):
    print(f"🔍 Debugging getInfo() results for {city} {year}")
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
    band = esri_full.select('esri_full')
    
    # Create masks
    veg_mask = band.eq(5).Or(band.eq(11))  # Crops + Rangeland
    built_mask = band.eq(7)  # Built areas
    
    print("🌱 Creating distance calculation...")
    
    # Fixed distance calculation
    veg_distance = veg_mask.fastDistanceTransform(
        neighborhood=int(3000 / scale),  # 30 pixels at 100m scale
        units='pixels',
        metric='squared_euclidean'
    ).sqrt().multiply(scale)  # Convert back to meters
    
    built_distance = veg_distance.updateMask(built_mask)
    
    print("📊 Testing basic reduceRegion...")
    
    # Test basic stats
    basic_stats = built_distance.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            ee.Reducer.max(),
            sharedInputs=True
        ).combine(
            ee.Reducer.min(),
            sharedInputs=True
        ).combine(
            ee.Reducer.count(),
            sharedInputs=True
        ),
        geometry=region,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
        tileScale=4
    )
    
    print("🔄 Calling getInfo()...")
    results = basic_stats.getInfo()
    
    print("📋 Raw results from getInfo():")
    print(results)
    
    print("\n🎯 Checking individual values:")
    for key, value in results.items():
        print(f"   {key}: {value} (type: {type(value)})")
    
    # Test with a direct distance calculation for comparison
    print("\n🧪 Testing direct distance sample...")
    sample = built_distance.sample(
        region=region,
        scale=scale,
        numPixels=100,
        geometries=False,
        tileScale=4
    ).getInfo()
    
    if sample and sample.get('features'):
        distances = [f['properties'].get('distance', 0) for f in sample['features']]
        print(f"   Sample distances: {distances[:10]}...")  # First 10
        print(f"   Non-zero count: {len([d for d in distances if d > 0])}/{len(distances)}")
        if any(d > 0 for d in distances):
            non_zero = [d for d in distances if d > 0]
            print(f"   Non-zero range: {min(non_zero):.1f} - {max(non_zero):.1f}")
    else:
        print("   ❌ No sample data")

if __name__ == '__main__':
    debug_getinfo_results('Tashkent', 2024)
