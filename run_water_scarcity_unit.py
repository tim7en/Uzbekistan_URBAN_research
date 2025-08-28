"""Unit runner for water scarcity assessment per city.

This script performs comprehensive water scarcity risk assessment for Uzbekistan cities
using IPCC AR6 water-related hazards and GEE-derived indicators including:

- Supply-side indicators: aridity index, climatic water deficit, drought frequency
- Surface water indicators: JRC GSW change analysis
- Demand proxies: cropland fraction, population density
- External benchmarks: WRI Aqueduct baseline water stress scores

Results are saved as JSON summaries per city and aggregated reports.
"""
import sys
from pathlib import Path

# Ensure repository root is on sys.path so local `services` package is importable
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import argparse
import json
from typing import List, Dict, Any, Optional

from services import gee
from services.utils import create_output_directories, UZBEKISTAN_CITIES
from services.water_scarcity_assessment import WaterScarcityAssessmentService
from services.climate_data_loader import ClimateDataLoader


def parse_args():
    p = argparse.ArgumentParser(description='Water Scarcity Assessment unit runner')
    p.add_argument('--assess', action='store_true', help='Run water scarcity assessment for cities')
    p.add_argument('--export-json', action='store_true', help='Export detailed results to JSON files')
    p.add_argument('--export-csv', action='store_true', help='Export results to CSV format')
    p.add_argument('--summary', action='store_true', help='Generate summary report only')
    p.add_argument('--cities', nargs='*', help='List of cities (default: all configured cities)')
    p.add_argument('--real-only', action='store_true', help='Require real GEE data; fail if GEE or fetches fail')
    p.add_argument('--output-dir', type=str, default=None, help='Custom output directory')
    p.add_argument('--verbose', action='store_true', help='Enable verbose output')
    return p.parse_args()


def main():
    args = parse_args()
    out_dirs = create_output_directories()
    base = Path(args.output_dir) if args.output_dir else out_dirs['base']

    cities = args.cities if args.cities else list(UZBEKISTAN_CITIES.keys())

    # Determine what to do - if no specific action, do assessment
    do_assess = args.assess or (not args.summary and not args.export_json and not args.export_csv)
    do_summary = args.summary
    do_export_json = args.export_json
    do_export_csv = args.export_csv

    # Initialize services
    data_loader = ClimateDataLoader(str(base))

    # Prefer GEE-backed assessment when available; fall back to simulator
    water_service = None
    try:
        gee_ok = gee.initialize_gee()
    except Exception:
        gee_ok = False

    if gee_ok:
        try:
            # Import here to avoid import-time dependency when EE not available
            from services.water_scarcity_gee import WaterScarcityGEEAssessment
            water_service = WaterScarcityGEEAssessment(data_loader)
            print("Using GEE-backed water scarcity assessment")
        except Exception as e:
            if args.real_only:
                raise
            print(f"GEE-backed assessment failed to initialize, falling back to simulator: {e}")
            water_service = WaterScarcityAssessmentService(data_loader)
    else:
        # No GEE available or initialization failed — use simulator unless real-only requested
        if args.real_only:
            raise RuntimeError('GEE not available but --real-only was requested')
        water_service = WaterScarcityAssessmentService(data_loader)

    results = []

    if do_assess:
        print(f"Running water scarcity assessment for {len(cities)} cities...")

        for city in cities:
            if args.verbose:
                print(f"Assessing water scarcity for {city}...")

            try:
                city_metrics = water_service.assess_city_water_scarcity(city)

                # Convert dataclass to dict for JSON serialization
                city_result = {
                    'city': city_metrics.city,
                    'aridity_index': city_metrics.aridity_index,
                    'climatic_water_deficit': city_metrics.climatic_water_deficit,
                    'drought_frequency': city_metrics.drought_frequency,
                    'surface_water_change': city_metrics.surface_water_change,
                    'cropland_fraction': city_metrics.cropland_fraction,
                    'population_density': city_metrics.population_density,
                    'aqueduct_bws_score': city_metrics.aqueduct_bws_score,
                    'water_supply_risk': city_metrics.water_supply_risk,
                    'water_demand_risk': city_metrics.water_demand_risk,
                    'overall_water_scarcity_score': city_metrics.overall_water_scarcity_score,
                    'water_scarcity_level': city_metrics.water_scarcity_level
                }

                results.append(city_result)

                # Save individual city results
                city_dir = base / 'water_scarcity' / city
                city_dir.mkdir(parents=True, exist_ok=True)

                city_file = city_dir / 'water_scarcity_assessment.json'
                with open(city_file, 'w', encoding='utf-8') as f:
                    json.dump(city_result, f, indent=2)

                if args.verbose:
                    print(f"  {city}: {city_metrics.water_scarcity_level} "
                          f"(Score: {city_metrics.overall_water_scarcity_score:.2f})")

            except Exception as e:
                print(f"Error assessing {city}: {e}")
                results.append({'city': city, 'error': str(e)})

    # Generate summary if requested or if assessment was run
    if do_summary or (do_assess and not do_export_json and not do_export_csv):
        print("Generating water scarcity summary...")

        try:
            summary = water_service.get_water_scarcity_summary()

            # Save summary report
            reports_dir = base / 'reports'
            reports_dir.mkdir(parents=True, exist_ok=True)

            summary_file = reports_dir / 'water_scarcity_summary.json'
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)

            print(f"Saved summary report: {summary_file}")

            # Print key findings
            if 'risk_distribution' in summary:
                print("\nWater Scarcity Risk Distribution:")
                for level, count in summary['risk_distribution'].items():
                    print(f"  {level}: {count} cities")

            if 'top_risk_cities' in summary:
                print("\nTop Risk Cities:")
                for city_info in summary['top_risk_cities'][:5]:
                    print(f"  {city_info['city']}: {city_info['score']:.2f}")

        except Exception as e:
            print(f"Error generating summary: {e}")

    # Export detailed JSON if requested
    if do_export_json and results:
        print("Exporting detailed JSON results...")

        try:
            export_file = base / 'reports' / 'water_scarcity_detailed_results.json'
            export_file.parent.mkdir(parents=True, exist_ok=True)

            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)

            print(f"Saved detailed results: {export_file}")

        except Exception as e:
            print(f"Error exporting JSON: {e}")

    # Export CSV if requested
    if do_export_csv and results:
        print("Exporting CSV results...")

        try:
            import pandas as pd

            df = pd.DataFrame(results)
            csv_file = base / 'reports' / 'water_scarcity_results.csv'
            csv_file.parent.mkdir(parents=True, exist_ok=True)

            df.to_csv(csv_file, index=False)
            print(f"Saved CSV results: {csv_file}")

        except ImportError:
            print("pandas not available for CSV export")
        except Exception as e:
            print(f"Error exporting CSV: {e}")

    print(f"\nWater scarcity assessment completed for {len([r for r in results if 'error' not in r])} cities")


if __name__ == '__main__':
    main()
