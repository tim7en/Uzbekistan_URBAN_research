#!/usr/bin/env python3
"""
Test script to examine ESRI Global Land Cover dataset structure
"""

import ee

def main():
    print("🔍 Testing ESRI Global Land Cover Dataset")
    print("="*50)
    
    try:
        # Initialize GEE
        ee.Initialize(project='ee-sabitovty')
        print("✅ GEE initialized")
        
        # Test the ESRI dataset
        esri_path = "projects/sat-io/open-datasets/landcover/ESRI_Global-LULC_10m_TS"
        collection = ee.ImageCollection(esri_path)
        
        print(f"📊 Collection size: {collection.size().getInfo()}")
        
        # Get first image
        first_image = collection.first()
        print(f"📋 Band names: {first_image.bandNames().getInfo()}")
        
        # Try to get image info
        try:
            info = first_image.getInfo()
            print(f"📝 Image properties keys: {list(info.get('properties', {}).keys())}")
            
            # Look for year information
            props = info.get('properties', {})
            if 'year' in props:
                print(f"📅 Year property: {props['year']}")
            if 'system:time_start' in props:
                import datetime
                timestamp = props['system:time_start'] / 1000
                date = datetime.datetime.fromtimestamp(timestamp)
                print(f"📅 Date: {date}")
                
        except Exception as e:
            print(f"⚠️ Could not get full image info: {e}")
        
        # Test with a specific location (Tashkent)
        point = ee.Geometry.Point([69.2401, 41.2995])
        small_area = point.buffer(1000)
        
        # Sample the image
        sample = first_image.sample(region=small_area, scale=10, numPixels=10)
        sample_data = sample.getInfo()
        
        print(f"📍 Sample data from Tashkent area:")
        for feature in sample_data['features'][:5]:  # Show first 5 samples
            props = feature['properties']
            print(f"   {props}")
        
        # Try to get unique values in the first band
        band_name = first_image.bandNames().getInfo()[0]
        print(f"🔢 Getting unique values for band '{band_name}'...")
        
        # Get a histogram to see value distribution
        hist = first_image.select(band_name).reduceRegion(
            reducer=ee.Reducer.frequencyHistogram(),
            geometry=small_area,
            scale=30,
            maxPixels=1e6,  # Increase maxPixels
            bestEffort=True  # Add bestEffort flag
        )
        
        hist_data = hist.getInfo()
        if band_name in hist_data:
            values = hist_data[band_name]
            print(f"📊 Value distribution (top 10):")
            sorted_values = sorted(values.items(), key=lambda x: int(x[1]), reverse=True)[:10]
            for value, count in sorted_values:
                print(f"   Value {value}: {count} pixels")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
