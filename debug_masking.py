"""Debug the masking issue specifically."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

import ee
from services.gee import initialize_gee
from services.utils import UZBEKISTAN_CITIES
from services.classification import load_all_classifications

def debug_masking_issue(city='Tashkent', year=2024):
    print(f"🔍 Debugging masking issue for {city} {year}")
    print("=" * 50)
    
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
    veg_mask = band.eq(5).Or(band.eq(11))
    non_veg_mask = veg_mask.Not()
    built_mask = band.eq(7)
    
    # Calculate distance
    distance_to_veg = non_veg_mask.fastDistanceTransform(
        neighborhood=1000,
        units='meters', 
        metric='squared_euclidean'
    ).sqrt()
    
    print("\n1️⃣ Raw distance calculation (no masking):")
    raw_stats = distance_to_veg.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            ee.Reducer.min(), sharedInputs=True
        ).combine(
            ee.Reducer.max(), sharedInputs=True
        ).combine(
            ee.Reducer.count(), sharedInputs=True
        ),
        geometry=region,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
        tileScale=4
    ).getInfo()
    
    for key, value in raw_stats.items():
        if value is not None:
            print(f"   {key}: {value:.2f}")
    
    print("\n2️⃣ Distance with non-vegetation mask:")
    masked_distance = distance_to_veg.updateMask(non_veg_mask)
    masked_stats = masked_distance.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            ee.Reducer.min(), sharedInputs=True
        ).combine(
            ee.Reducer.max(), sharedInputs=True
        ).combine(
            ee.Reducer.count(), sharedInputs=True
        ),
        geometry=region,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
        tileScale=4
    ).getInfo()
    
    for key, value in masked_stats.items():
        if value is not None:
            print(f"   {key}: {value:.2f}")
    
    print("\n3️⃣ Distance with built mask:")
    built_distance = distance_to_veg.updateMask(built_mask)
    built_stats = built_distance.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            ee.Reducer.min(), sharedInputs=True
        ).combine(
            ee.Reducer.max(), sharedInputs=True
        ).combine(
            ee.Reducer.count(), sharedInputs=True
        ),
        geometry=region,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
        tileScale=4
    ).getInfo()
    
    for key, value in built_stats.items():
        if value is not None:
            print(f"   {key}: {value:.2f}")
    
    print("\n4️⃣ Alternative approach - multiply by mask:")
    # Instead of updateMask, multiply by mask
    alt_distance = distance_to_veg.multiply(built_mask)
    alt_stats = alt_distance.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            ee.Reducer.min(), sharedInputs=True
        ).combine(
            ee.Reducer.max(), sharedInputs=True
        ).combine(
            ee.Reducer.count(), sharedInputs=True
        ),
        geometry=region,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
        tileScale=4
    ).getInfo()
    
    for key, value in alt_stats.items():
        if value is not None:
            print(f"   {key}: {value:.2f}")
    
    print("\n5️⃣ Let's try a different approach - WHERE clause:")
    # Use where to only get distance values for built areas
    where_distance = ee.Image(0).where(built_mask, distance_to_veg)
    where_stats = where_distance.updateMask(built_mask).reduceRegion(
        reducer=ee.Reducer.mean().combine(
            ee.Reducer.min(), sharedInputs=True
        ).combine(
            ee.Reducer.max(), sharedInputs=True
        ).combine(
            ee.Reducer.count(), sharedInputs=True
        ),
        geometry=region,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
        tileScale=4
    ).getInfo()
    
    for key, value in where_stats.items():
        if value is not None:
            print(f"   {key}: {value:.2f}")

if __name__ == '__main__':
    debug_masking_issue('Tashkent', 2024)
