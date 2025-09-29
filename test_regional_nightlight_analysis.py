"""Test script for the regional nightlight analysis to verify functionality.

This script runs a small subset of the analysis to test:
1. Google Earth Engine connectivity
2. Regional boundary retrieval
3. VIIRS data loading
4. Basic statistics computation

Run this before executing the full analysis.
"""
import sys
from pathlib import Path

# Ensure repository root is on sys.path so local `services` package is importable
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from services import gee
from services.utils import UZBEKISTAN_CITIES, create_output_directories
from run_uzbekistan_nightlight_regional_analysis import (
    get_region_geometry, 
    load_viirs_monthly_for_year,
    compute_nightlight_statistics,
    CITY_TO_REGION_MAP,
    UZBEKISTAN_REGIONS
)


def test_gee_connection():
    """Test Google Earth Engine initialization."""
    print("🧪 Testing Google Earth Engine connection...")
    success = gee.initialize_gee()
    if success:
        print("✅ GEE initialization successful")
        return True
    else:
        print("❌ GEE initialization failed")
        return False


def test_regional_boundaries():
    """Test regional boundary retrieval."""
    print("\n🧪 Testing regional boundary retrieval...")
    
    test_regions = ["Andijan Region", "Bukhara Region", "Tashkent City"]
    
    for region_name in test_regions:
        try:
            print(f"  Testing {region_name}...")
            geometry = get_region_geometry(region_name)
            
            # Basic validation - check if we got a geometry
            if geometry:
                print(f"    ✅ Retrieved geometry for {region_name}")
            else:
                print(f"    ❌ Failed to get geometry for {region_name}")
                return False
                
        except Exception as e:
            print(f"    ❌ Error getting geometry for {region_name}: {e}")
            return False
    
    print("✅ Regional boundary retrieval successful")
    return True


def test_viirs_data_loading():
    """Test VIIRS data loading for a small region."""
    print("\n🧪 Testing VIIRS data loading...")
    
    try:
        # Use Tashkent as test case (smallest region)
        region_geometry = get_region_geometry("Tashkent City")
        
        print("  Loading VIIRS data for 2024...")
        viirs_image = load_viirs_monthly_for_year(2024, region_geometry)
        
        if viirs_image:
            band_names = viirs_image.bandNames().getInfo()
            print(f"    ✅ VIIRS image loaded with bands: {band_names}")
            return viirs_image, region_geometry
        else:
            print("    ❌ Failed to load VIIRS image")
            return None, None
            
    except Exception as e:
        print(f"    ❌ Error loading VIIRS data: {e}")
        return None, None


def test_statistics_computation(viirs_image, geometry):
    """Test statistics computation."""
    print("\n🧪 Testing statistics computation...")
    
    try:
        print("  Computing nightlight statistics...")
        stats = compute_nightlight_statistics(viirs_image, geometry, scale=1000)
        
        if 'error' in stats:
            print(f"    ❌ Error in statistics: {stats['error']}")
            return False
        
        print("    ✅ Statistics computed successfully:")
        for key, value in stats.items():
            if value is not None:
                print(f"      {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Error computing statistics: {e}")
        return False


def test_city_analysis():
    """Test complete city analysis workflow."""
    print("\n🧪 Testing complete city analysis workflow...")
    
    try:
        # Test with Andijan (smaller city)
        city_name = "Andijan"
        year = 2024
        
        print(f"  Testing analysis for {city_name} ({year})...")
        
        # Get city info and region
        city_info = UZBEKISTAN_CITIES.get(city_name)
        if not city_info:
            print(f"    ❌ City {city_name} not found")
            return False
        
        region_name = CITY_TO_REGION_MAP.get(city_name)
        if not region_name:
            print(f"    ❌ Region not found for {city_name}")
            return False
        
        print(f"    City: {city_name}, Region: {region_name}")
        
        # Create geometries
        import ee
        city_center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
        city_buffer = city_center.buffer(city_info['buffer_m'])
        region_geometry = get_region_geometry(region_name)
        
        # Load VIIRS data
        viirs_image = load_viirs_monthly_for_year(year, region_geometry)
        
        # Compute statistics for city
        city_stats = compute_nightlight_statistics(viirs_image, city_buffer, scale=500)
        
        # Compute statistics for region
        region_stats = compute_nightlight_statistics(viirs_image, region_geometry, scale=1000)
        
        print("    ✅ City analysis completed:")
        print(f"      City mean radiance: {city_stats.get('mean')}")
        print(f"      Region mean radiance: {region_stats.get('mean')}")
        
        if city_stats.get('mean') and region_stats.get('mean'):
            ratio = city_stats['mean'] / region_stats['mean']
            print(f"      City/Region ratio: {ratio:.2f}")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Error in city analysis: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Regional Nightlight Analysis Test Suite")
    print("=" * 50)
    
    # Test 1: GEE Connection
    if not test_gee_connection():
        print("\n❌ Tests failed at GEE connection")
        return 1
    
    # Test 2: Regional Boundaries
    if not test_regional_boundaries():
        print("\n❌ Tests failed at regional boundaries")
        return 1
    
    # Test 3: VIIRS Data Loading
    viirs_image, geometry = test_viirs_data_loading()
    if viirs_image is None:
        print("\n❌ Tests failed at VIIRS data loading")
        return 1
    
    # Test 4: Statistics Computation
    if not test_statistics_computation(viirs_image, geometry):
        print("\n❌ Tests failed at statistics computation")
        return 1
    
    # Test 5: Complete City Analysis
    if not test_city_analysis():
        print("\n❌ Tests failed at city analysis")
        return 1
    
    print("\n" + "=" * 50)
    print("✅ All tests passed! Regional nightlight analysis is ready to run.")
    print("\nNext steps:")
    print("1. Run the full analysis: python run_uzbekistan_nightlight_regional_analysis.py")
    print("2. Or run with specific parameters, e.g.:")
    print("   python run_uzbekistan_nightlight_regional_analysis.py --cities Tashkent Andijan --start-year 2020")
    
    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)