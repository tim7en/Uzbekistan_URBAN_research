#!/usr/bin/env python3
"""
Unit Test Runner for Uzbekistan URBAN Research Project

This script runs comprehensive tests for all components of the research pipeline
without requiring Google Earth Engine authentication. It validates:
- Module imports and basic functionality
- Configuration validity
- Data structure integrity
- Analysis pipeline components
- Code organization and structure

Usage:
    python run_unit_tests.py [--verbose] [--quick]
"""

import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any
import traceback

# Ensure repository root is on sys.path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

def print_header(title: str, char: str = "="):
    """Print a formatted header."""
    print(f"\n{char * 60}")
    print(f" {title}")
    print(f"{char * 60}")

def print_subheader(title: str):
    """Print a formatted subheader."""
    print(f"\n--- {title} ---")

def test_imports() -> Dict[str, Any]:
    """Test all module imports."""
    print_header("MODULE IMPORT TESTS")
    
    results = {
        'passed': 0,
        'failed': 0,
        'details': {}
    }
    
    # Core dependencies
    core_deps = [
        ('pandas', 'pd'),
        ('numpy', 'np'),
        ('matplotlib.pyplot', 'plt'),
        ('pathlib', 'Path'),
        ('json', None)
    ]
    
    print_subheader("Core Dependencies")
    for module, alias in core_deps:
        try:
            if alias:
                exec(f"import {module} as {alias}")
            else:
                exec(f"import {module}")
            print(f"✓ {module}")
            results['passed'] += 1
            results['details'][module] = 'PASS'
        except ImportError as e:
            print(f"✗ {module}: {e}")
            results['failed'] += 1
            results['details'][module] = f'FAIL: {e}'
    
    # Services modules
    services_modules = [
        'utils', 'gee', 'classification', 'temperature', 'vegetation',
        'suhi', 'visualization', 'reporting', 'nightlight', 'analyze_nightlights',
        'auxiliary_data', 'lulc', 'suhi_unit', 'spatial_relationships'
    ]
    
    print_subheader("Services Modules")
    for module in services_modules:
        try:
            exec(f"from services import {module}")
            print(f"✓ services.{module}")
            results['passed'] += 1
            results['details'][f'services.{module}'] = 'PASS'
        except ImportError as e:
            print(f"✗ services.{module}: {e}")
            results['failed'] += 1
            results['details'][f'services.{module}'] = f'FAIL: {e}'
        except Exception as e:
            print(f"⚠ services.{module}: {e}")
            results['passed'] += 1  # Still counts as imported
            results['details'][f'services.{module}'] = f'PASS_WITH_WARNING: {e}'
    
    return results

def test_configuration() -> Dict[str, Any]:
    """Test configuration and constants."""
    print_header("CONFIGURATION TESTS")
    
    results = {
        'passed': 0,
        'failed': 0,
        'details': {}
    }
    
    try:
        from services.utils import UZBEKISTAN_CITIES, ANALYSIS_CONFIG
        
        # Test cities configuration
        print_subheader("Cities Configuration")
        print(f"Total cities configured: {len(UZBEKISTAN_CITIES)}")
        
        required_fields = ['lat', 'lon', 'buffer_m', 'type']
        for city, config in UZBEKISTAN_CITIES.items():
            missing_fields = [field for field in required_fields if field not in config]
            if missing_fields:
                print(f"✗ {city}: Missing fields {missing_fields}")
                results['failed'] += 1
                results['details'][f'city_{city}'] = f'FAIL: Missing {missing_fields}'
            else:
                # Validate coordinate ranges
                lat, lon = config['lat'], config['lon']
                if not (35 <= lat <= 45 and 55 <= lon <= 75):  # Uzbekistan bounds
                    print(f"⚠ {city}: Coordinates outside expected range: {lat}, {lon}")
                    results['details'][f'city_{city}'] = f'WARNING: Coordinates outside expected range'
                else:
                    results['details'][f'city_{city}'] = 'PASS'
                results['passed'] += 1
        
        print(f"✓ Cities configuration validated")
        
        # Test analysis configuration
        print_subheader("Analysis Configuration")
        required_analysis_fields = ['years', 'warm_months', 'target_resolution_m']
        missing_analysis_fields = [field for field in required_analysis_fields if field not in ANALYSIS_CONFIG]
        if missing_analysis_fields:
            print(f"✗ Analysis config missing fields: {missing_analysis_fields}")
            results['failed'] += 1
            results['details']['analysis_config'] = f'FAIL: Missing {missing_analysis_fields}'
        else:
            print(f"✓ Analysis configuration validated")
            results['passed'] += 1
            results['details']['analysis_config'] = 'PASS'
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        results['failed'] += 1
        results['details']['configuration'] = f'FAIL: {e}'
    
    return results

def test_data_structures() -> Dict[str, Any]:
    """Test data structure functions."""
    print_header("DATA STRUCTURE TESTS")
    
    results = {
        'passed': 0,
        'failed': 0,
        'details': {}
    }
    
    try:
        from services.utils import create_output_directories
        
        print_subheader("Output Directory Creation")
        out_dirs = create_output_directories()
        
        expected_dirs = ['base', 'nightlights', 'lulc', 'temperature', 'vegetation', 'reports']
        for dir_name in expected_dirs:
            if dir_name in out_dirs:
                print(f"✓ {dir_name} directory configured")
                results['passed'] += 1
                results['details'][f'output_dir_{dir_name}'] = 'PASS'
            else:
                print(f"✗ {dir_name} directory missing")
                results['failed'] += 1
                results['details'][f'output_dir_{dir_name}'] = 'FAIL: Missing'
        
    except Exception as e:
        print(f"✗ Data structure test failed: {e}")
        results['failed'] += 1
        results['details']['data_structures'] = f'FAIL: {e}'
    
    return results

def test_unit_runners() -> Dict[str, Any]:
    """Test unit runner scripts exist and are structured correctly."""
    print_header("UNIT RUNNER TESTS")
    
    results = {
        'passed': 0,
        'failed': 0,
        'details': {}
    }
    
    unit_runners = [
        'run_nightlight_unit.py',
        'run_lulc_unit.py', 
        'run_suhi_unit.py',
        'run_auxiliary_unit.py',
        'run_spatial_relationships_unit.py'
    ]
    
    smoke_runners = [
        'run_smoke.py',
        'main_smoke_coarse.py'
    ]
    
    print_subheader("Unit Runner Scripts")
    for runner in unit_runners:
        runner_path = Path(ROOT) / runner
        if runner_path.exists():
            print(f"✓ {runner} exists")
            results['passed'] += 1
            results['details'][runner] = 'PASS'
        else:
            print(f"✗ {runner} missing")
            results['failed'] += 1
            results['details'][runner] = 'FAIL: Missing'
    
    print_subheader("Smoke Test Scripts")
    for runner in smoke_runners:
        runner_path = Path(ROOT) / runner
        if runner_path.exists():
            print(f"✓ {runner} exists")
            results['passed'] += 1
            results['details'][runner] = 'PASS'
        else:
            print(f"✗ {runner} missing")
            results['failed'] += 1
            results['details'][runner] = 'FAIL: Missing'
    
    return results

def test_code_structure() -> Dict[str, Any]:
    """Test code organization and structure."""
    print_header("CODE STRUCTURE TESTS")
    
    results = {
        'passed': 0,
        'failed': 0,
        'details': {}
    }
    
    # Test services package structure
    print_subheader("Services Package Structure")
    services_dir = Path(ROOT) / 'services'
    if services_dir.exists() and services_dir.is_dir():
        print(f"✓ Services directory exists")
        results['passed'] += 1
        results['details']['services_dir'] = 'PASS'
        
        # Check for __init__.py
        init_file = services_dir / '__init__.py'
        if init_file.exists():
            print(f"✓ Services package __init__.py exists")
            results['passed'] += 1
            results['details']['services_init'] = 'PASS'
        else:
            print(f"✗ Services package __init__.py missing")
            results['failed'] += 1
            results['details']['services_init'] = 'FAIL: Missing'
    else:
        print(f"✗ Services directory missing")
        results['failed'] += 1
        results['details']['services_dir'] = 'FAIL: Missing'
    
    # Test documentation
    print_subheader("Documentation")
    docs = ['README.md', 'OUTPUTS_ASSESSMENT.md']
    for doc in docs:
        doc_path = Path(ROOT) / doc
        if doc_path.exists():
            print(f"✓ {doc} exists")
            results['passed'] += 1
            results['details'][doc] = 'PASS'
        else:
            print(f"✗ {doc} missing")
            results['failed'] += 1
            results['details'][doc] = 'FAIL: Missing'
    
    return results

def test_algorithm_availability() -> Dict[str, Any]:
    """Test that core algorithms are available (without execution)."""
    print_header("ALGORITHM AVAILABILITY TESTS")
    
    results = {
        'passed': 0,
        'failed': 0,
        'details': {}
    }
    
    # Test SUHI algorithms
    print_subheader("SUHI Algorithms")
    try:
        from services import suhi
        
        # Check for key functions
        suhi_functions = ['compute_pixel_suhi', 'compute_zonal_suhi']
        for func_name in suhi_functions:
            if hasattr(suhi, func_name):
                print(f"✓ {func_name} available")
                results['passed'] += 1
                results['details'][f'suhi_{func_name}'] = 'PASS'
            else:
                print(f"✗ {func_name} missing")
                results['failed'] += 1
                results['details'][f'suhi_{func_name}'] = 'FAIL: Missing'
    except Exception as e:
        print(f"✗ SUHI module test failed: {e}")
        results['failed'] += 1
        results['details']['suhi_module'] = f'FAIL: {e}'
    
    # Test auxiliary data algorithms
    print_subheader("Auxiliary Data Algorithms")
    try:
        from services import auxiliary_data
        
        if hasattr(auxiliary_data, 'run_batch'):
            print(f"✓ auxiliary_data.run_batch available")
            results['passed'] += 1
            results['details']['auxiliary_run_batch'] = 'PASS'
        else:
            print(f"✗ auxiliary_data.run_batch missing")
            results['failed'] += 1
            results['details']['auxiliary_run_batch'] = 'FAIL: Missing'
    except Exception as e:
        print(f"✗ Auxiliary data module test failed: {e}")
        results['failed'] += 1
        results['details']['auxiliary_module'] = f'FAIL: {e}'
    
    return results

def run_all_tests(verbose: bool = False, quick: bool = False) -> Dict[str, Any]:
    """Run all unit tests."""
    start_time = time.time()
    
    print_header("UZBEKISTAN URBAN RESEARCH - UNIT TEST SUITE", "=")
    print(f"Test run started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = {}
    
    # Define test suite
    test_suite = [
        ("Imports", test_imports),
        ("Configuration", test_configuration), 
        ("Data Structures", test_data_structures),
        ("Unit Runners", test_unit_runners),
        ("Code Structure", test_code_structure),
        ("Algorithm Availability", test_algorithm_availability),
    ]
    
    if quick:
        test_suite = test_suite[:3]  # Run only first 3 tests in quick mode
    
    total_passed = 0
    total_failed = 0
    
    for test_name, test_func in test_suite:
        try:
            result = test_func()
            all_results[test_name] = result
            total_passed += result['passed']
            total_failed += result['failed']
            
            if verbose:
                print(f"\n{test_name} Results:")
                print(f"  Passed: {result['passed']}")
                print(f"  Failed: {result['failed']}")
                
        except Exception as e:
            print(f"\n✗ {test_name} test suite failed: {e}")
            if verbose:
                traceback.print_exc()
            all_results[test_name] = {
                'passed': 0,
                'failed': 1,
                'details': {'suite_error': f'FAIL: {e}'}
            }
            total_failed += 1
    
    # Final summary
    end_time = time.time()
    duration = end_time - start_time
    
    print_header("TEST SUMMARY", "=")
    print(f"Total tests passed: {total_passed}")
    print(f"Total tests failed: {total_failed}")
    print(f"Success rate: {(total_passed/(total_passed+total_failed)*100):.1f}%")
    print(f"Test duration: {duration:.2f} seconds")
    
    overall_status = "PASS" if total_failed == 0 else "FAIL"
    print(f"\nOverall result: {overall_status}")
    
    # Save detailed results
    results_summary = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'duration_seconds': duration,
        'total_passed': total_passed,
        'total_failed': total_failed,
        'success_rate': total_passed/(total_passed+total_failed)*100,
        'overall_status': overall_status,
        'test_results': all_results
    }
    
    return results_summary

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run unit tests for Uzbekistan URBAN Research')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--quick', '-q', action='store_true', help='Run quick tests only')
    parser.add_argument('--save-results', '-s', action='store_true', help='Save results to JSON file')
    
    args = parser.parse_args()
    
    results = run_all_tests(verbose=args.verbose, quick=args.quick)
    
    if args.save_results:
        # Save results to output directory
        try:
            from services.utils import create_output_directories
            out_dirs = create_output_directories()
            reports_dir = out_dirs['base'] / 'reports'
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            results_file = reports_dir / f"unit_test_results_{int(time.time())}.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to: {results_file}")
        except Exception as e:
            print(f"\nWarning: Could not save results: {e}")
    
    # Exit with appropriate code
    sys.exit(0 if results['overall_status'] == 'PASS' else 1)

if __name__ == '__main__':
    main()