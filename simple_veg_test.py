"""Simple vegetation test to verify our data is working."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

import ee
from services.gee import initialize_gee
from services.utils import UZBEKISTAN_CITIES
from services.classification import load_all_classifications

def simple_veg_test(city='Gulistan', year=2024):
    print(f"🧪 Simple vegetation test for {city} {year}")
    print("-" * 40)
    
    # Initialize GEE
    ok = initialize_gee()
    if not ok:
        return
    
    # Setup region
    city_info = UZBEKISTAN_CITIES[city]
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    region = center.buffer(city_info['buffer_m'])
    scale = 200  # Use coarser scale for speed
    
    # Load ESRI data
    classifications = load_all_classifications(
        year, region, f"{year}-01-01", f"{year}-12-31",
        optimal_scales={'scale': scale}
    )
    esri_full = classifications.get('esri_full')
    
    if esri_full is None:
        print("❌ No ESRI data")
        return
    
    print("✅ ESRI data loaded")
    
    # Test individual classes step by step
    band = esri_full.select('esri_full')
    
    # Test class 5 (Crops)
    crops_mask = band.eq(5)
    crops_stats = crops_mask.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
        tileScale=4
    ).getInfo()
    
    crops_pixels = crops_stats.get('esri_full', 0)
    print(f"🌾 Crops (class 5): {crops_pixels:.0f} pixels")
    
    # Test class 11 (Rangeland)
    rangeland_mask = band.eq(11)
    rangeland_stats = rangeland_mask.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
        tileScale=4
    ).getInfo()
    
    rangeland_pixels = rangeland_stats.get('esri_full', 0)
    print(f"🌿 Rangeland (class 11): {rangeland_pixels:.0f} pixels")
    
    # Test combined vegetation mask
    veg_mask = crops_mask.Or(rangeland_mask)
    veg_stats = veg_mask.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
        tileScale=4
    ).getInfo()
    
    total_veg_pixels = veg_stats.get('esri_full', 0)
    print(f"🌱 Total vegetation: {total_veg_pixels:.0f} pixels")
    
    # Get total area for percentage
    total_stats = band.reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=region,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
        tileScale=4
    ).getInfo()
    
    total_pixels = total_stats.get('esri_full', 0)
    veg_percentage = (total_veg_pixels / total_pixels * 100) if total_pixels > 0 else 0
    
    print(f"📊 Total: {total_veg_pixels:.0f}/{total_pixels:.0f} pixels ({veg_percentage:.1f}% vegetation)")
    
    # Now test the distance calculation
    if total_veg_pixels > 0:
        print(f"\n🔄 Testing distance calculation...")
        
        # Distance TO vegetation (from non-vegetation pixels)
        veg_distance = veg_mask.Not().fastDistanceTransform(
            neighborhood=3000,
            units='meters',
            metric='squared_euclidean'
        ).sqrt()
        
        # Sample some distances for non-vegetation areas
        non_veg_mask = veg_mask.Not()
        accessibility_distance = veg_distance.updateMask(non_veg_mask)
        
        distance_stats = accessibility_distance.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                ee.Reducer.min(), sharedInputs=True
            ).combine(
                ee.Reducer.max(), sharedInputs=True
            ),
            geometry=region,
            scale=scale,
            maxPixels=1e10,
            bestEffort=True,
            tileScale=4
        ).getInfo()
        
        print(f"📏 Vegetation accessibility stats:")
        for key, value in distance_stats.items():
            if value is not None:
                print(f"   {key}: {value:.1f}m")
    else:
        print("❌ No vegetation found for distance calculation")

if __name__ == '__main__':
    cities = ['Gulistan', 'Tashkent', 'Nukus', 'Samarkand']
    
    for city in cities:
        simple_veg_test(city, 2024)
        print()
