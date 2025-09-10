"""Debug the distance calculation specifically."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

import ee
from services.gee import initialize_gee
from services.utils import UZBEKISTAN_CITIES
from services.classification import load_all_classifications

def debug_distance_calculation(city='Tashkent', year=2024):
    print(f"🔍 Debugging distance calculation for {city} {year}")
    print("=" * 50)
    
    # Initialize GEE
    ok = initialize_gee()
    if not ok:
        return
    
    # Setup region
    city_info = UZBEKISTAN_CITIES[city]
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    region = center.buffer(city_info['buffer_m'])
    scale = 200  # Use coarser scale for debugging
    
    # Load ESRI data
    classifications = load_all_classifications(
        year, region, f"{year}-01-01", f"{year}-12-31",
        optimal_scales={'scale': scale}
    )
    esri_full = classifications.get('esri_full')
    band = esri_full.select('esri_full')
    
    # Create vegetation mask (crops + rangeland)
    veg_mask = band.eq(5).Or(band.eq(11))
    
    # Create built mask  
    built_mask = band.eq(7)
    
    # Check mask statistics
    veg_stats = veg_mask.reduceRegion(ee.Reducer.sum(), region, scale, maxPixels=1e10, bestEffort=True, tileScale=4).getInfo()
    built_stats = built_mask.reduceRegion(ee.Reducer.sum(), region, scale, maxPixels=1e10, bestEffort=True, tileScale=4).getInfo()
    
    veg_pixels = veg_stats.get('esri_full', 0)
    built_pixels = built_stats.get('esri_full', 0)
    
    print(f"🌱 Vegetation pixels: {veg_pixels:.0f}")
    print(f"🏗️  Built pixels: {built_pixels:.0f}")
    
    # Test 1: Basic distance calculation
    print(f"\n1️⃣ Testing basic distance calculation...")
    
    # Distance from vegetation pixels
    distance_from_veg = veg_mask.distance(ee.Kernel.euclidean(1000, 'meters'))
    
    # Sample distances
    sample_from_veg = distance_from_veg.sample(
        region=region,
        scale=scale,
        numPixels=500,
        geometries=False,
        tileScale=4
    ).getInfo()
    
    if sample_from_veg and sample_from_veg.get('features'):
        distances = [f['properties'].get('distance', 0) for f in sample_from_veg['features']]
        distances = [d for d in distances if d is not None]
        print(f"   Distance FROM vegetation: min={min(distances):.1f}m, max={max(distances):.1f}m, mean={sum(distances)/len(distances):.1f}m")
    
    # Test 2: Fast distance transform
    print(f"\n2️⃣ Testing fastDistanceTransform...")
    
    # Create non-vegetation mask
    non_veg_mask = veg_mask.Not()
    
    # Distance TO vegetation (what we want)
    distance_to_veg = non_veg_mask.fastDistanceTransform(
        neighborhood=1000,  # Smaller radius for testing
        units='meters',
        metric='squared_euclidean'
    ).sqrt()
    
    # Sample distances TO vegetation
    sample_to_veg = distance_to_veg.sample(
        region=region,
        scale=scale,
        numPixels=500,
        geometries=False,
        tileScale=4
    ).getInfo()
    
    if sample_to_veg and sample_to_veg.get('features'):
        distances = [f['properties'].get('distance', 0) for f in sample_to_veg['features']]
        distances = [d for d in distances if d is not None]
        print(f"   Distance TO vegetation: min={min(distances):.1f}m, max={max(distances):.1f}m, mean={sum(distances)/len(distances):.1f}m")
        print(f"   Zero values: {distances.count(0)}/{len(distances)}")
    
    # Test 3: Check what pixels are actually non-vegetation
    print(f"\n3️⃣ Testing non-vegetation mask...")
    
    non_veg_stats = non_veg_mask.reduceRegion(ee.Reducer.sum(), region, scale, maxPixels=1e10, bestEffort=True, tileScale=4).getInfo()
    non_veg_pixels = non_veg_stats.get('esri_full', 0)
    print(f"   Non-vegetation pixels: {non_veg_pixels:.0f}")
    
    if non_veg_pixels == 0:
        print("   ❌ ALL pixels are vegetation - this explains 0m distances!")
        return
    
    # Test 4: Sample non-vegetation areas specifically
    print(f"\n4️⃣ Testing distance for non-vegetation areas only...")
    
    # Mask distance calculation to non-vegetation areas only
    distance_non_veg_only = distance_to_veg.updateMask(non_veg_mask)
    
    sample_non_veg = distance_non_veg_only.sample(
        region=region,
        scale=scale,
        numPixels=300,
        geometries=False,
        tileScale=4
    ).getInfo()
    
    if sample_non_veg and sample_non_veg.get('features'):
        distances = [f['properties'].get('distance', 0) for f in sample_non_veg['features']]
        distances = [d for d in distances if d is not None]
        
        if distances:
            print(f"   Non-vegetation distance stats:")
            print(f"   Min: {min(distances):.1f}m")
            print(f"   Max: {max(distances):.1f}m") 
            print(f"   Mean: {sum(distances)/len(distances):.1f}m")
            print(f"   Zero count: {distances.count(0)}/{len(distances)}")
            
            # Show some example values
            unique_distances = sorted(set(distances))[:10]
            print(f"   Sample values: {[f'{d:.1f}' for d in unique_distances]}")
        else:
            print("   ❌ No distance values found")
    else:
        print("   ❌ No sample data for non-vegetation areas")
    
    # Test 5: Check for built areas specifically
    if built_pixels > 0:
        print(f"\n5️⃣ Testing distance for built areas specifically...")
        
        distance_built_only = distance_to_veg.updateMask(built_mask)
        
        built_distance_stats = distance_built_only.reduceRegion(
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
        
        print(f"   Built area distance stats:")
        for key, value in built_distance_stats.items():
            if value is not None:
                print(f"   {key}: {value:.2f}")

if __name__ == '__main__':
    debug_distance_calculation('Tashkent', 2024)
