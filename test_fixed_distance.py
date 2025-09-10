"""Test the fixed distance calculation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

import ee
from services.gee import initialize_gee
from services.utils import UZBEKISTAN_CITIES
from services.classification import load_all_classifications

def test_fixed_distance(city='Tashkent', year=2024):
    print(f"🧪 Testing FIXED distance calculation for {city} {year}")
    print("=" * 60)
    
    # Initialize GEE
    ok = initialize_gee()
    if not ok:
        return
    
    # Setup region
    city_info = UZBEKISTAN_CITIES[city]
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    region = center.buffer(city_info['buffer_m'])
    scale = 200
    
    # Load ESRI data
    classifications = load_all_classifications(
        year, region, f"{year}-01-01", f"{year}-12-31",
        optimal_scales={'scale': scale}
    )
    esri_full = classifications.get('esri_full')
    band = esri_full.select('esri_full')
    
    # Create masks
    veg_mask = band.eq(5).Or(band.eq(11))  # Crops + Rangeland
    built_mask = band.eq(7)  # Built areas
    
    print(f"🌱 Testing OLD method (BROKEN)...")
    # OLD WAY (broken)
    old_distance = veg_mask.Not().fastDistanceTransform(
        neighborhood=int(3000 / scale),
        units='pixels',
        metric='squared_euclidean'
    ).sqrt().multiply(scale)
    
    old_built_distance = old_distance.updateMask(built_mask)
    old_stats = old_built_distance.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.max(), sharedInputs=True),
        geometry=region,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
        tileScale=4
    ).getInfo()
    
    print(f"   OLD - Mean: {old_stats.get('distance_mean', 0):.1f}m, Max: {old_stats.get('distance_max', 0):.1f}m")
    
    print(f"\n🎯 Testing NEW method (FIXED)...")
    # NEW WAY (fixed)
    new_distance = veg_mask.fastDistanceTransform(
        neighborhood=int(3000 / scale),
        units='pixels', 
        metric='squared_euclidean'
    ).sqrt().multiply(scale)
    
    new_built_distance = new_distance.updateMask(built_mask)
    new_stats = new_built_distance.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.max(), sharedInputs=True),
        geometry=region,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
        tileScale=4
    ).getInfo()
    
    print(f"   NEW - Mean: {new_stats.get('distance_mean', 0):.1f}m, Max: {new_stats.get('distance_max', 0):.1f}m")
    
    # Test sampling
    print(f"\n📊 Sampling built area distances (NEW method)...")
    sample = new_built_distance.sample(
        region=region,
        scale=scale,
        numPixels=500,
        geometries=False,
        tileScale=4
    ).getInfo()
    
    if sample and sample.get('features'):
        distances = [f['properties'].get('distance', 0) for f in sample['features']]
        distances = [d for d in distances if d is not None and d > 0]
        
        if distances:
            print(f"   Sample stats: min={min(distances):.1f}m, max={max(distances):.1f}m, mean={sum(distances)/len(distances):.1f}m")
            print(f"   Non-zero samples: {len(distances)}/{len(sample['features'])}")
            
            # Show distribution
            bins = [0, 100, 200, 500, 1000, 2000, 5000]
            for i in range(len(bins)-1):
                count = len([d for d in distances if bins[i] <= d < bins[i+1]])
                print(f"   {bins[i]}-{bins[i+1]}m: {count} pixels")
        else:
            print("   ❌ No positive distances found")
    else:
        print("   ❌ No sample data")

if __name__ == '__main__':
    for city in ['Tashkent', 'Gulistan', 'Nukus']:
        test_fixed_distance(city, 2024)
        print()
