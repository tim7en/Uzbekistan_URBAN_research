#!/usr/bin/env python3
"""
Standalone script to compute comprehensive temperature statistics for all cities and years.
This generates detailed urban/rural temperature analysis with confidence intervals,
uncertainty metrics, and monthly breakdowns stored as JSON files.
"""

import sys
import os
from pathlib import Path

# Add repository root to path for local imports
repo_root = Path(__file__).parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from services.gee import initialize_gee
from services.temperature import compute_temperature_statistics
from services.utils import UZBEKISTAN_CITIES, create_output_directories
import json
import time


def run_temperature_statistics_batch(cities=None, years=None):
    """Run comprehensive temperature statistics for specified cities and years."""
    
    # Initialize Google Earth Engine using the existing service
    if not initialize_gee():
        print("❌ Failed to initialize Google Earth Engine. Exiting.")
        return
    
    # Set defaults
    if cities is None:
        cities = list(UZBEKISTAN_CITIES.keys())
    if years is None:
        years = list(range(2016, 2025))
    
    # Create output directories
    base_dirs = create_output_directories()
    
    # Summary results
    summary = {
        'total_cities': len(cities),
        'total_years': len(years),
        'successful_computations': 0,
        'failed_computations': 0,
        'results': {},
        'errors': []
    }
    
    print(f"📊 Computing temperature statistics for {len(cities)} cities and {len(years)} years...")
    
    total_combinations = len(cities) * len(years)
    current_combination = 0
    
    for city in cities:
        summary['results'][city] = {}
        
        for year in years:
            current_combination += 1
            print(f"\n🌡️  Processing {city} {year} ({current_combination}/{total_combinations})...")
            
            try:
                # Compute temperature statistics
                start_time = time.time()
                temp_stats = compute_temperature_statistics(city, year, base_dirs['base'])
                computation_time = time.time() - start_time
                
                if 'error' not in temp_stats:
                    summary['successful_computations'] += 1
                    summary['results'][city][str(year)] = {
                        'status': 'success',
                        'computation_time_seconds': round(computation_time, 2),
                        'output_file': temp_stats.get('output_file'),
                        'has_monthly_stats': bool(temp_stats.get('monthly_stats')),
                        'has_annual_summary': bool(temp_stats.get('annual_summary')),
                        'has_uncertainty': bool(temp_stats.get('uncertainty')),
                        'has_confidence_intervals': bool(temp_stats.get('confidence_intervals')),
                        'has_day_night_analysis': bool(temp_stats.get('day_night_analysis'))
                    }
                    print(f"   ✅ Success in {computation_time:.1f}s - {temp_stats.get('output_file', 'No output file')}")
                else:
                    summary['failed_computations'] += 1
                    error_msg = temp_stats.get('error', 'Unknown error')
                    summary['results'][city][str(year)] = {
                        'status': 'error',
                        'error': error_msg,
                        'computation_time_seconds': round(computation_time, 2)
                    }
                    summary['errors'].append(f"{city} {year}: {error_msg}")
                    print(f"   ❌ Failed: {error_msg}")
            
            except Exception as e:
                summary['failed_computations'] += 1
                error_msg = str(e)
                summary['results'][city][str(year)] = {
                    'status': 'exception',
                    'error': error_msg
                }
                summary['errors'].append(f"{city} {year}: {error_msg}")
                print(f"   ❌ Exception: {error_msg}")
            
            # Add small delay to avoid overwhelming Earth Engine
            time.sleep(1)
    
    # Save batch summary
    summary_file = base_dirs['base'] / 'reports' / 'temperature_statistics_batch_summary.json'
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\n📋 Batch summary saved to: {summary_file}")
    except Exception as e:
        print(f"\n⚠️  Failed to save batch summary: {e}")
    
    # Print final summary
    print(f"\n📊 Temperature Statistics Batch Complete:")
    print(f"   ✅ Successful: {summary['successful_computations']}")
    print(f"   ❌ Failed: {summary['failed_computations']}")
    print(f"   📁 Results stored in: {base_dirs['base'] / 'temperature'}")
    
    if summary['errors']:
        print(f"\n⚠️  Errors encountered:")
        for error in summary['errors'][:10]:  # Show first 10 errors
            print(f"   - {error}")
        if len(summary['errors']) > 10:
            print(f"   ... and {len(summary['errors']) - 10} more errors")
    
    return summary


def main():
    """Main function to run temperature statistics computation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Compute comprehensive temperature statistics')
    parser.add_argument('--cities', nargs='+', help='List of cities to process (default: all)')
    parser.add_argument('--years', type=int, nargs='+', help='List of years to process (default: 2016-2024)')
    parser.add_argument('--test', action='store_true', help='Run test with single city/year')
    
    args = parser.parse_args()
    
    if args.test:
        # Test run with single city/year
        cities = ['Tashkent']
        years = [2020]
        print("🧪 Running test mode with Tashkent 2020...")
    else:
        cities = args.cities
        years = args.years
    
    run_temperature_statistics_batch(cities, years)


if __name__ == '__main__':
    main()
