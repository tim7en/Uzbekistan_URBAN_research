"""Runner for social sector unit: healthcare, education, and sanitation analysis.

Usage (simple):
  python run_social_sector_unit.py

It will run the service for configured cities and write
results into `suhi_analysis_output/social_sector/` with per-city JSON summaries.
"""
import sys
from pathlib import Path

# Ensure repository root is on sys.path so local `services` package is importable
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import argparse
import json
from services.social_sector import run_batch_social_analysis, save_social_analysis_results
from services.gee import initialize_gee


def main():
    p = argparse.ArgumentParser(description='Run social sector analysis')
    p.add_argument('--start-year', type=int, default=None)
    p.add_argument('--end-year', type=int, default=None)
    p.add_argument('--cities', nargs='*', help='Cities to process')
    p.add_argument('--verbose', action='store_true')
    args = p.parse_args()

    ok = initialize_gee()
    if not ok:
        print("GEE initialization failed or was cancelled. Authenticate and try again.")
        return

    results = run_batch_social_analysis(cities=args.cities, verbose=args.verbose)

    # Save results
    save_social_analysis_results(results)

    # Print summary
    print("\nSocial Sector Analysis Summary:")
    print("=" * 50)
    for city, city_results in results.items():
        if 'error' in city_results:
            print(f"{city}: ERROR - {city_results['error']}")
            continue

        summary = city_results.get('summary', {})
        print(f"{city}:")
        print(f"  Schools: {summary.get('total_schools', 0)}")
        print(f"  Hospitals: {summary.get('total_hospitals', 0)}")
        print(f"  Kindergardens: {summary.get('total_kindergardens', 0)}")
        print(f"  Student Capacity: {summary.get('total_students_capacity', 0)}")
        print(f"  Enrolled Students: {summary.get('total_students_enrolled', 0)}")

        sanitation = summary.get('sanitation_indicators', {})
        if sanitation:
            print(f"  Sanitation - Electricity: {sanitation.get('electricity_access', 0)}%, "
                  f"Water: {sanitation.get('water_access', 0)}%, "
                  f"Internet: {sanitation.get('internet_access', 0)}%")
        print()


if __name__ == '__main__':
    main()
