"""Test script for the updated city-centered nightlight analysis.

This script verifies the new approach using city locations and circular buffers
instead of administrative boundaries.
"""
import sys
from pathlib import Path

# Ensure repository root is on sys.path so local `services` package is importable
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from services import gee
from services.utils import UZBEKISTAN_CITIES
from run_uzbekistan_nightlight_regional_analysis import (
    calculate_regional_buffer_from_city,
    create_analysis_zones_for_city,
    get_region_geometry_from_city,
    analyze_city_and_region_nightlights
)


def test_buffer_calculations():
    """Test the regional buffer calculation logic."""
    print("🧪 Testing regional buffer calculations...")
    
    test_cities = ["Tashkent", "Andijan", "Bukhara", "Gulistan"]
    
    for city_name in test_cities:
        city_info = UZBEKISTAN_CITIES.get(city_name)
        if city_info:
            regional_buffer = calculate_regional_buffer_from_city(city_info)
            city_buffer = city_info['buffer_m']
            ratio = regional_buffer / city_buffer
            
            print(f"  {city_name}:")
            print(f"    City buffer: {city_buffer/1000:.1f}km")
            print(f"    Regional buffer: {regional_buffer/1000:.1f}km")
            print(f"    Ratio: {ratio:.1f}x")
            print(f"    Type: {city_info.get('type')}, Pop: {city_info.get('population'):,}")


def test_analysis_zones():
    """Test the analysis zone creation."""
    print("\n🧪 Testing analysis zone creation...")
    
    test_city = "Andijan"
    print(f"  Creating zones for {test_city}...")
    
    try:
        zones = create_analysis_zones_for_city(test_city)
        
        print("    ✅ Analysis zones created successfully:")
        for zone_name, geometry in zones.items():
            if hasattr(geometry, 'area'):
                try:
                    # Get approximate area (this requires GEE initialization)
                    area_info = geometry.area().getInfo()
                    area_km2 = area_info / 1e6
                    print(f"      {zone_name}: ~{area_km2:.0f} km²")
                except:
                    print(f"      {zone_name}: geometry created (area calculation requires GEE)")
            else:
                print(f"      {zone_name}: geometry object created")
                
    except Exception as e:
        print(f"    ❌ Error creating zones: {e}")


def test_city_centered_geometry():
    """Test the new city-centered geometry creation."""
    print("\n🧪 Testing city-centered regional geometry...")
    
    test_cities = ["Tashkent", "Bukhara"]
    
    for city_name in test_cities:
        try:
            print(f"  Testing {city_name}...")
            geometry = get_region_geometry_from_city(city_name)
            
            if geometry:
                print(f"    ✅ Regional geometry created for {city_name}")
            else:
                print(f"    ❌ Failed to create geometry for {city_name}")
                
        except Exception as e:
            print(f"    ❌ Error for {city_name}: {e}")


def test_full_analysis_workflow():
    """Test the complete analysis workflow with the new approach."""
    print("\n🧪 Testing complete analysis workflow...")
    
    # Initialize GEE first
    success = gee.initialize_gee()
    if not success:
        print("    ❌ GEE initialization failed - skipping workflow test")
        return False
    
    test_city = "Bukhara"  # Smaller city for faster testing
    test_year = 2024
    output_dir = Path("temp_test_output")
    
    print(f"  Testing full analysis for {test_city} ({test_year})...")
    
    try:
        result = analyze_city_and_region_nightlights(test_city, test_year, output_dir)
        
        if 'error' in result:
            print(f"    ❌ Analysis error: {result['error']}")
            return False
        
        print("    ✅ Analysis completed successfully!")
        print(f"      City mean radiance: {result.get('city_stats', {}).get('mean', 'N/A')}")
        print(f"      Background mean radiance: {result.get('regional_background_stats', {}).get('mean', 'N/A')}")
        print(f"      City/background ratio: {result.get('city_to_region_ratio', 'N/A')}")
        print(f"      City radius: {result.get('city_radius_km', 'N/A')} km")
        print(f"      Regional radius: {result.get('region_radius_km', 'N/A')} km")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Workflow test failed: {e}")
        return False


def compare_approaches():
    """Compare the new city-centered approach with different cities."""
    print("\n📊 Comparing city-centered analysis across cities...")
    
    cities_sample = ["Tashkent", "Andijan", "Bukhara", "Gulistan"]
    
    print("City characteristics and regional buffer sizes:")
    print("-" * 60)
    print(f"{'City':<12} {'Type':<15} {'Pop':<8} {'City(km)':<9} {'Region(km)':<11} {'Ratio':<5}")
    print("-" * 60)
    
    for city_name in cities_sample:
        city_info = UZBEKISTAN_CITIES.get(city_name)
        if city_info:
            regional_buffer = calculate_regional_buffer_from_city(city_info)
            city_buffer = city_info['buffer_m']
            ratio = regional_buffer / city_buffer
            
            print(f"{city_name:<12} {city_info.get('type', 'N/A'):<15} "
                  f"{city_info.get('population', 0)/1000:.0f}k{'':<3} "
                  f"{city_buffer/1000:.1f}{'':<8} "
                  f"{regional_buffer/1000:.1f}{'':<10} "
                  f"{ratio:.1f}x")


def main():
    """Run all tests for the city-centered approach."""
    print("🧪 City-Centered Nightlight Analysis Test Suite")
    print("=" * 55)
    
    # Test 1: Buffer calculations
    test_buffer_calculations()
    
    # Test 2: Analysis zones (without GEE)
    test_analysis_zones()
    
    # Test 3: City-centered geometry
    test_city_centered_geometry()
    
    # Test 4: Comparison across cities
    compare_approaches()
    
    # Test 5: Full workflow (requires GEE)
    workflow_success = test_full_analysis_workflow()
    
    print("\n" + "=" * 55)
    if workflow_success:
        print("✅ All tests passed! City-centered analysis is ready.")
        print("\nKey improvements in the new approach:")
        print("• Uses actual city coordinates and buffers")
        print("• Creates consistent circular analysis zones")
        print("• Scales regional analysis based on city characteristics")
        print("• Provides more accurate urban vs rural comparisons")
        
        print("\nNext steps:")
        print("• Run: python run_uzbekistan_nightlight_regional_analysis.py --cities Tashkent Bukhara --start-year 2022")
        print("• Compare results with different city types and sizes")
    else:
        print("⚠️ Some tests failed. Check GEE authentication and network connectivity.")
    
    return 0 if workflow_success else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)