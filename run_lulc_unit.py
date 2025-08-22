"""Unit runner for LULC (land-use/land-cover) analysis per city.

This script performs two types of outputs for each city/year:
  1) Coarse local GeoTIFFs saved under `suhi_analysis_output/lulc/<city>/` (uses
     a coarse scale to keep files small). This uses `classification.load_all_classifications`
     and `Image.getDownloadURL`.
  2) Detailed exports via Earth Engine Drive export (high-resolution) when
     requested; creates ee.batch.Export tasks.

It also runs an ESRI-based landcover change analysis using
`classification.analyze_esri_landcover_changes` and saves results under
`suhi_analysis_output/lulc_analysis/`.

Defaults are safe: generation/export are opt-in. To run analysis-only call with
`--analyze`.
"""
import sys
from pathlib import Path

# Ensure repository root is on sys.path so local `services` package is importable
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import argparse
import json
import time
from typing import List, Dict, Any, Optional

from services import gee
from services.utils import create_output_directories, UZBEKISTAN_CITIES
from services import lulc
from services import lulc_analysis


# ... helper functions moved to `services.lulc` - root runner keeps only orchestration


def parse_args():
    p = argparse.ArgumentParser(description='LULC unit runner')
    p.add_argument('--generate', action='store_true', help='Run generation (requires GEE auth)')
    p.add_argument('--save-local', action='store_true', help='Save coarse local GeoTIFFs (200m)')
    p.add_argument('--save-highres', action='store_true', help='Save high-resolution local GeoTIFFs (30m) - WARNING: Large files!')
    p.add_argument('--export-drive', action='store_true', help='Start Drive export tasks for detailed LULC')
    p.add_argument('--analyze', action='store_true', help='Run ESRI-based landcover change analysis')
    p.add_argument('--cities', nargs='*', help='List of cities (default: all configured cities)')
    p.add_argument('--start-year', type=int, default=2017)
    p.add_argument('--end-year', type=int, default=2024)
    p.add_argument('--coarse-scale', type=int, default=200, help='Coarse local scale in meters')
    p.add_argument('--highres-scale', type=int, default=30, help='High-resolution local scale in meters')
    p.add_argument('--drive-scale', type=int, default=30, help='Drive export scale in meters')
    return p.parse_args()


def main():
    args = parse_args()
    out_dirs = create_output_directories()
    base = out_dirs['base']

    cities = args.cities if args.cities else list(UZBEKISTAN_CITIES.keys())
    start_year = args.start_year
    end_year = args.end_year

    do_generate = args.generate
    do_save_local = args.save_local
    do_save_highres = args.save_highres
    do_export_drive = args.export_drive
    do_analyze = args.analyze or (not do_generate and not do_save_local and not do_save_highres and not do_export_drive)

    # If any action requires Earth Engine, initialize it up front
    if do_generate or do_save_local or do_save_highres or do_export_drive or do_analyze:
        ok = gee.initialize_gee()
        if not ok:
            print('GEE initialization failed; aborting')
            return

    results = []
    for city in cities:
        for year in range(start_year, end_year + 1):
            rec = {'city': city, 'year': year}
            if do_generate and do_save_local:
                print(f"Generating coarse LULC local for {city} {year}...")
                rec['coarse'] = lulc.generate_coarse_local(base, city, year, coarse_scale=args.coarse_scale)
            if do_generate and do_save_highres:
                print(f"Generating high-resolution LULC local for {city} {year}...")
                rec['highres'] = lulc.generate_highres_local(base, city, year, highres_scale=args.highres_scale)
            if do_generate and do_export_drive:
                print(f"Starting Drive exports for detailed LULC for {city} {year}...")
                rec['drive'] = lulc.generate_detailed_drive(base, city, year, drive_scale=args.drive_scale)
            results.append(rec)

    # Save generation summary
    if any('coarse' in r or 'highres' in r or 'drive' in r for r in results):
        gen_file = base / 'reports' / 'lulc_summary.json'
        gen_file.parent.mkdir(parents=True, exist_ok=True)
        with open(gen_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print('Saved generation summary:', gen_file)

    if do_analyze:
        analysis_results = []
        for city in cities:
            print(f"Analyzing LULC changes for {city} {start_year}-{end_year}...")
            # run detailed LULC analysis (time series, trends, comparisons vs ESRI)
            r = lulc_analysis.run_city_lulc_analysis(base, city, start_year, end_year)
            analysis_results.append(r)
        analysis_file = base / 'reports' / 'lulc_analysis_summary.json'
        analysis_file.parent.mkdir(parents=True, exist_ok=True)
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, indent=2)
        print('Saved analysis summary:', analysis_file)


if __name__ == '__main__':
    main()
