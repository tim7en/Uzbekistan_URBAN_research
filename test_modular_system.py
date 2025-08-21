"""
Test script for the new modular system
Tests configuration, imports, and basic functionality without running full analysis
"""

import sys
from pathlib import Path
import traceback

def test_imports():
    """Test that all services can be imported correctly"""
    print("🧪 Testing imports...")
    
    try:
        # Test config import
        from services.config import get_default_config, UZBEKISTAN_CITIES, DATASETS
        print("   ✅ Config import successful")
        
        # Test utils imports
        from services.utils.gee_utils import initialize_gee, test_dataset_availability
        from services.utils.output_utils import create_output_directories
        print("   ✅ Utils imports successful")
        
        # Test analysis imports
        from services.analysis.night_lights import run_comprehensive_night_lights_analysis
        from services.analysis.suhi import run_comprehensive_suhi_analysis
        from services.analysis.urban_expansion import run_comprehensive_urban_expansion_analysis
        print("   ✅ Analysis imports successful")
        
        # Test visualization imports
        from services.visualization.generators import (
            create_suhi_analysis_visualization,
            create_night_lights_visualization,
            create_urban_expansion_visualization,
            create_comprehensive_dashboard
        )
        print("   ✅ Visualization imports successful")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        traceback.print_exc()
        return False


def test_configuration():
    """Test configuration system"""
    print("\n🔧 Testing configuration...")
    
    try:
        from services.config import get_default_config, UZBEKISTAN_CITIES
        
        # Test default config
        analysis_config, gee_config = get_default_config()
        print(f"   ✅ Default resolution: {analysis_config.resolution_m}m")
        print(f"   ✅ Default years: {analysis_config.years[0]}-{analysis_config.years[-1]}")
        
        # Test testing mode
        analysis_config_test, gee_config_test = get_default_config(testing_mode=True)
        cities_test = analysis_config_test.get_cities_to_process()
        print(f"   ✅ Testing mode cities: {len(cities_test)} cities")
        print(f"   ✅ Test cities: {cities_test}")
        
        # Test different resolutions
        for resolution in [100, 500, 1000]:
            _, gee_config_res = get_default_config(resolution_m=resolution)
            print(f"   ✅ Resolution {resolution}m: scale={gee_config_res.scale}, max_pixels={gee_config_res.max_pixels}")
        
        # Test city definitions
        print(f"   ✅ Total cities defined: {len(UZBEKISTAN_CITIES)}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Configuration test failed: {e}")
        traceback.print_exc()
        return False


def test_output_structure():
    """Test output directory creation"""
    print("\n📁 Testing output structure...")
    
    try:
        from services.utils.output_utils import create_output_directories
        
        # Create test output directories
        output_dirs = create_output_directories("test_output")
        
        required_dirs = [
            'data', 'night_lights', 'temperature', 'urban_expansion',
            'raster_outputs', 'visualizations', 'statistical', 'reports'
        ]
        
        for dir_name in required_dirs:
            if dir_name in output_dirs:
                print(f"   ✅ {dir_name} directory created")
            else:
                print(f"   ❌ {dir_name} directory missing")
                return False
        
        # Clean up test directories
        import shutil
        shutil.rmtree(output_dirs['base'])
        print("   ✅ Test directories cleaned up")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Output structure test failed: {e}")
        traceback.print_exc()
        return False


def test_main_modular():
    """Test the main modular entry point (without running full analysis)"""
    print("\n🚀 Testing main modular entry point...")
    
    try:
        # Import main_modular
        import main_modular
        
        # Test that the main function exists
        if hasattr(main_modular, 'main'):
            print("   ✅ main() function found")
        else:
            print("   ❌ main() function not found")
            return False
        
        # Test that run_analysis function exists
        if hasattr(main_modular, 'run_analysis'):
            print("   ✅ run_analysis() function found")
        else:
            print("   ❌ run_analysis() function not found")
            return False
        
        print("   ✅ Main modular structure validated")
        return True
        
    except Exception as e:
        print(f"   ❌ Main modular test failed: {e}")
        traceback.print_exc()
        return False


def test_dependencies():
    """Test that required dependencies are available"""
    print("\n📦 Testing dependencies...")
    
    required_packages = [
        'pandas', 'numpy', 'matplotlib', 'seaborn', 'pathlib', 'json', 'datetime'
    ]
    
    optional_packages = [
        ('ee', 'Google Earth Engine (required for analysis)'),
        ('scipy', 'SciPy (required for advanced statistics)')
    ]
    
    all_available = True
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - REQUIRED")
            all_available = False
    
    for package, description in optional_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ⚠️ {package} - {description}")
    
    return all_available


def main():
    """Run all tests"""
    print("="*60)
    print("UZBEKISTAN URBAN RESEARCH - MODULAR SYSTEM TESTS")
    print("="*60)
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Output Structure", test_output_structure),
        ("Main Modular", test_main_modular)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The modular system is ready for use.")
        print("\nNext steps:")
        print("1. Set up Google Earth Engine authentication")
        print("2. Run: python main_modular.py")
        print("3. Check outputs in uzbekistan_urban_analysis_output/")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please fix issues before proceeding.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)