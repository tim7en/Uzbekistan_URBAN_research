"""Runner script: batch nightlight analysis (VIIRS) for selected Uzbekistan cities.

Generates thumbnails, per-city statistics JSON, histograms and a short markdown
report describing spatial and temporal characteristics of the used datasets.
"""
import sys
from pathlib import Path

# Ensure repository root is on sys.path so local `services` package is importable
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import argparse
import json
from services import analyze_nightlights, gee
from services import nightlight
from services.utils import create_output_directories, UZBEKISTAN_CITIES, ANALYSIS_CONFIG


def parse_args():
    p = argparse.ArgumentParser(description='Nightlight unit runner')
    p.add_argument('--generate', action='store_true', help='Run nightlight generation')
    p.add_argument('--save-local-geotiff', action='store_true', help='Save local GeoTIFF files')
    p.add_argument('--export-drive', action='store_true', help='Export to Google Drive')
    p.add_argument('--analyze', action='store_true', help='Run nightlight analysis')
    p.add_argument('--cities', nargs='*', help='List of cities (default: all configured cities)')
    p.add_argument('--start-year', type=int, default=2016)
    p.add_argument('--end-year', type=int, default=2024)
    return p.parse_args()


def main():
    args = parse_args()
    out_dirs = create_output_directories()
    success = gee.initialize_gee()
    if not success:
        print("GEE init failed — aborting nightlight run")
        return

    years = list(range(args.start_year, args.end_year + 1))
    # Process all configured cities by default
    cities = args.cities if args.cities else list(UZBEKISTAN_CITIES.keys())

    # Run batch that computes stats in EE and writes one JSON per city
    summaries = nightlight.run_batch_viirs(cities, years, out_dirs['base'])
    # Save a compact summary aggregating per-city JSON paths
    out_file = out_dirs['base'] / 'nightlights_summary.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(summaries, f, indent=2)
    print(f"Saved nightlight summary: {out_file}")

    # Create a simple report with dataset metadata
    report_md = out_dirs['base'] / 'nightlights_report.md'
    with open(report_md, 'w', encoding='utf-8') as f:
        f.write('# Nightlights Analysis Report\n')
        f.write('## Datasets used\n')
        f.write('- VIIRS Monthly: DATASET id = ' + str(nightlight.DATASETS.get('viirs_monthly', 'UNKNOWN')) + '\n')
        f.write('- DMSP OLS (if available): DATASET id = ' + str(nightlight.DATASETS.get('dmsp_ols', 'UNKNOWN')) + '\n')
        f.write('\n')
        f.write('## Temporal coverage\n')
        f.write(f'- Years analyzed: {years[0]} to {years[-1]} (annual median composites)\n')
        f.write('\n')
        f.write('## Spatial resolution (typical)\n')
        f.write('- VIIRS Monthly: native ~500 m to 750 m depending on product; thumbnails exported at ~1024 px per city extent.\n')
        f.write('- DMSP OLS: coarse ~2.7 km (legacy).\n')
        f.write('\n')
        f.write('## Notes\n')
        f.write('- Radiance band names may vary across collections; the script selects the first available band.\n')
        f.write('- Thumbnails are generated with a linear stretch (min/max).\n')
    print(f"Report written: {report_md}")

    out_dirs = create_output_directories()
    cities = args.cities if args.cities else list(UZBEKISTAN_CITIES.keys())
    years = list(range(args.start_year, args.end_year + 1))
    results = analyze_nightlights.analyze_cities_years(out_dirs['base'], cities, years, lit_threshold=1.0)
    summary = analyze_nightlights.generate_summary_report(results, out_dirs['base'])
    print('Analysis complete. Summary markdown:', summary)

if __name__ == '__main__':
    main()
