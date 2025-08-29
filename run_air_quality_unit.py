"""Unit runner for Sentinel-based air quality assessment.

This script performs comprehensive air quality monitoring using Sentinel satellites:
- Sentinel-5P: NO2, O3, SO2, CO, CH4, Aerosol Index
- Multi-year trend analysis and seasonal patterns
- Health impact assessment and policy recommendations
- Urban vs rural pollution comparisons

Data is automatically saved in the following structure:
- air_quality/{city}/air_quality_{year}.json (yearly results)
- air_quality/{city}/air_quality_assessment.json (combined assessment)
- air_quality/air_quality_summary_{start_year}_{end_year}.json (summary report)

Usage: python run_air_quality_unit.py --cities Tashkent --start-year 2019 --end-year 2024
"""
import sys
from pathlib import Path

# Ensure repository root is on sys.path so local `services` package is importable
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import argparse
import json
from datetime import datetime

from services.gee import initialize_gee
from services.air_quality import run_city_air_quality_analysis
from services.utils import UZBEKISTAN_CITIES, create_output_directories


def parse_args():
    p = argparse.ArgumentParser(description='Sentinel air quality assessment unit runner')
    p.add_argument('--assess', action='store_true', help='Run air quality assessment for cities (default if no action specified)')
    p.add_argument('--cities', nargs='*', help='List of cities (default: all configured cities)')
    p.add_argument('--start-year', type=int, default=2019, help='Start year for analysis (Sentinel-5P data starts ~2018)')
    p.add_argument('--end-year', type=int, default=2024, help='End year for analysis')
    p.add_argument('--pollutants', nargs='*',
                   choices=['NO2', 'O3', 'SO2', 'CO', 'CH4', 'AER_AI'],
                   default=['CO', 'CH4', 'AER_AI', 'NO2', 'O3', 'SO2'],
                   help='Pollutants to analyze (default: CO, CH4, AER_AI - reliable for Central Asia)')
    p.add_argument('--export-json', action='store_true', help='Export additional detailed results to JSON files (data is always saved per city/year)')
    p.add_argument('--summary', action='store_true', help='Generate comprehensive summary report')
    p.add_argument('--real-only', action='store_true', help='Require real satellite data; fail if GEE or fetches fail')
    p.add_argument('--output-dir', type=str, default=None, help='Custom output directory')
    p.add_argument('--verbose', action='store_true', help='Enable verbose output')
    return p.parse_args()


def main():
    args = parse_args()

    # Initialize Google Earth Engine
    ok = initialize_gee()
    if not ok:
        print('❌ GEE initialization failed. Please resolve authentication issues.')
        if args.real_only:
            return 1
        print('   Use --real-only flag to require successful GEE connection.')
        return 1

    # Setup output directories
    out_dirs = create_output_directories()
    base = Path(args.output_dir) if args.output_dir else out_dirs['base']
    air_quality_dir = base / 'air_quality'
    air_quality_dir.mkdir(parents=True, exist_ok=True)

    # Get cities to analyze
    cities = args.cities if args.cities else list(UZBEKISTAN_CITIES.keys())
    start_year = args.start_year
    end_year = args.end_year

    # Determine what to do - if no specific action, do assessment
    do_assess = args.assess or (not args.summary and not args.export_json)

    print("🌍 Sentinel Air Quality Assessment")
    print("=" * 50)
    print(f"   Cities: {', '.join(cities)}")
    print(f"   Period: {start_year}-{end_year}")
    print(f"   Pollutants: {', '.join(args.pollutants)}")
    print(f"   Output: {air_quality_dir}")
    print()

    if not do_assess:
        print("No assessment action specified. Use --assess to run analysis.")
        return 0

    all_results = {}
    summary_stats = {
        'total_cities': len(cities),
        'analysis_period': f"{start_year}-{end_year}",
        'pollutants_analyzed': args.pollutants,
        'cities_completed': 0,
        'cities_failed': 0,
        'processing_summary': {},
        'key_findings': [],
        'recommendations': []
    }

    # Analyze each city
    for city in cities:
        print(f"🏙️  Analyzing {city}...")
        try:
            # Run comprehensive air quality analysis
            city_results = run_city_air_quality_analysis(
                base_path=base,
                city_name=city,
                start_year=start_year,
                end_year=end_year
            )

            all_results[city] = city_results
            summary_stats['cities_completed'] += 1

            # Extract processing summary
            if 'summary' in city_results:
                summary = city_results['summary']
                
                # Track data quality
                if 'data_quality_summary' in summary:
                    quality = summary['data_quality_summary']
                    if 'average_score' in quality:
                        if 'data_quality_scores' not in summary_stats:
                            summary_stats['data_quality_scores'] = []
                        summary_stats['data_quality_scores'].append(quality['average_score'])

                # Collect key findings
                if 'key_findings' in summary:
                    for finding in summary['key_findings']:
                        summary_stats['key_findings'].append(f"{city}: {finding}")

                # Collect recommendations
                if 'recommendations' in summary:
                    for rec in summary['recommendations']:
                        if rec not in summary_stats['recommendations']:
                            summary_stats['recommendations'].append(rec)

            print(f"   ✅ {city} analysis completed")

            # Save individual city results - ALWAYS save (not just when --export-json)
            city_dir = air_quality_dir / city
            city_dir.mkdir(parents=True, exist_ok=True)

            # Save yearly results as separate files
            for year, year_data in city_results.get('yearly_results', {}).items():
                if 'error' not in year_data:
                    year_file = city_dir / f"air_quality_{year}.json"
                    with open(year_file, 'w', encoding='utf-8') as f:
                        json.dump(year_data, f, indent=2, ensure_ascii=False)
                    if args.verbose:
                        print(f"   💾 Saved {year} results to {year_file}")

            # Save combined assessment file (like water scarcity)
            combined_file = city_dir / "air_quality_assessment.json"
            with open(combined_file, 'w', encoding='utf-8') as f:
                json.dump(city_results, f, indent=2, ensure_ascii=False)
            print(f"   💾 Saved combined assessment to {combined_file}")

            # Save individual city results in old format if --export-json is specified
            if args.export_json:
                city_file = air_quality_dir / f"{city}_air_quality_{start_year}_{end_year}.json"
                with open(city_file, 'w', encoding='utf-8') as f:
                    json.dump(city_results, f, indent=2, ensure_ascii=False)
                print(f"   💾 Saved detailed results to {city_file}")

        except Exception as e:
            print(f"   ❌ Failed to analyze {city}: {e}")
            summary_stats['cities_failed'] += 1
            all_results[city] = {'error': str(e)}
            if args.verbose:
                import traceback
                traceback.print_exc()

    # Generate summary report
    if args.summary or summary_stats['cities_completed'] > 0:
        summary_file = air_quality_dir / f"air_quality_summary_{start_year}_{end_year}.json"

        # Calculate overall statistics
        if summary_stats.get('data_quality_scores'):
            import numpy as np
            avg_score = float(np.mean(summary_stats['data_quality_scores']))
            summary_stats['overall_data_quality'] = {
                'average_score': avg_score,
                'min_score': float(np.min(summary_stats['data_quality_scores'])),
                'max_score': float(np.max(summary_stats['data_quality_scores'])),
                'quality_rating': 'excellent' if avg_score >= 0.8 else 'good' if avg_score >= 0.6 else 'fair' if avg_score >= 0.4 else 'poor'
            }

        # Create comprehensive summary report
        summary_report = {
            'analysis_metadata': {
                'timestamp': datetime.now().isoformat(),
                'satellite_data': 'Sentinel-5P (NO2, O3, SO2, CO, AER_AI)',
                'spatial_resolution': '~5.5 km x 3.5 km (Sentinel-5P)',
                'temporal_resolution': 'Daily composites',
                'analysis_period': summary_stats['analysis_period'],
                'processing_method': 'Server-side Earth Engine computations'
            },
            'summary_statistics': summary_stats,
            'city_results': all_results
        }

        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_report, f, indent=2, ensure_ascii=False)

        print(f"\n📊 Summary report saved to {summary_file}")

    # Print final summary
    print("\n🎯 Air Quality Assessment Complete!")
    print("=" * 50)
    print(f"   Cities analyzed: {summary_stats['cities_completed']}")
    if summary_stats['cities_failed'] > 0:
        print(f"   Cities failed: {summary_stats['cities_failed']}")

    if summary_stats.get('data_quality_scores'):
        import numpy as np
        avg_quality = float(np.mean(summary_stats['data_quality_scores']))
        print(f"   Average data quality: {avg_quality:.2f}")

    # Print key findings (first 5)
    if summary_stats['key_findings']:
        print(f"\n🔍 Key Findings ({len(summary_stats['key_findings'])}):")
        for finding in summary_stats['key_findings'][:5]:
            print(f"   • {finding}")
        if len(summary_stats['key_findings']) > 5:
            print(f"   ... and {len(summary_stats['key_findings']) - 5} more")

    # Print recommendations (first 3)
    if summary_stats['recommendations']:
        print(f"\n💡 Recommendations ({len(summary_stats['recommendations'])}):")
        for rec in summary_stats['recommendations'][:3]:
            print(f"   • {rec}")
        if len(summary_stats['recommendations']) > 3:
            print(f"   ... and {len(summary_stats['recommendations']) - 3} more")

    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
