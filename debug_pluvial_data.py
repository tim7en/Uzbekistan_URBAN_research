#!/usr/bin/env python3
"""
Debug script to check what data is available for pluvial hazard calculation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))

from climate_data_loader import ClimateDataLoader
import json

def main():
    print("="*50)
    print("DEBUGGING PLUVIAL HAZARD DATA SOURCES")
    print("="*50)
    
    loader = ClimateDataLoader(os.getcwd())
    
    print("\nLoading data...")
    loader.load_all_data()
    
    print("\n1. CHECKING AVAILABLE DATA TYPES:")
    print(f"  - Temperature data: {len(loader.temperature_data)} cities")
    print(f"  - LULC data: {len(loader.lulc_data)} cities")
    print(f"  - Spatial relationships: {'Available' if loader.spatial_relationships else 'None'}")
    print(f"  - Water scarcity: {'Available' if hasattr(loader, 'water_scarcity_data') else 'None'}")
    
    print("\n2. SAMPLE TEMPERATURE DATA STRUCTURE (for pluvial indicators):")
    if loader.temperature_data:
        sample_city = list(loader.temperature_data.keys())[0]
        temp_data = loader.temperature_data[sample_city]
        print(f"Sample city: {sample_city}")
        
        if temp_data:
            # Check if there's precipitation data in any year
            sample_year = list(temp_data.keys())[0]
            year_data = temp_data[sample_year]
            print(f"Sample year: {sample_year}")
            print(f"Year data keys: {list(year_data.keys())}")
            
            # Check summer season summary for any precipitation indicators
            summer_data = year_data.get('summer_season_summary', {})
            print(f"Summer data keys: {list(summer_data.keys())}")
            
            # Check metadata for any precipitation info
            metadata = year_data.get('metadata', {})
            print(f"Metadata: {metadata}")
    
    print("\n3. CHECKING LULC DATA FOR FLOOD-RELATED INDICATORS:")
    if loader.lulc_data:
        sample_lulc = loader.lulc_data[0]
        print(f"Sample LULC city: {sample_lulc.get('city', 'Unknown')}")
        print(f"LULC keys: {list(sample_lulc.keys())}")
        
        # Look for imperviousness or drainage indicators
        for key, value in sample_lulc.items():
            if any(term in key.lower() for term in ['water', 'built', 'urban', 'impervious', 'drainage']):
                print(f"  {key}: {value}")
    
    print("\n4. CHECKING SPATIAL RELATIONSHIPS FOR FLOOD RISK:")
    if loader.spatial_relationships:
        print("Spatial relationships keys:", list(loader.spatial_relationships.keys()))
        
        # Check if there's any flood-related spatial data
        for city_name, spatial_data in loader.spatial_relationships.items():
            if isinstance(spatial_data, dict):
                print(f"{city_name} spatial keys: {list(spatial_data.keys())}")
                break
    
    print("\n5. ALTERNATIVE PLUVIAL HAZARD CALCULATION STRATEGY:")
    print("Since temperature data doesn't contain precipitation trends,")
    print("we should calculate pluvial hazard based on:")
    print("  - Urban imperviousness (from LULC built area)")
    print("  - Drainage capacity (inverse of built density)")
    print("  - Topographic factors (if available in spatial data)")
    print("  - Population density as proxy for urban development pressure")

if __name__ == "__main__":
    main()
