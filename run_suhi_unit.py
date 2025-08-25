"""Runner for SUHI unit maps (2017-2024 by default).

Usage: python run_suhi_unit.py
"""
import sys
from pathlib import Path

# Ensure repository root is on sys.path so local `services` package is importable
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import argparse
import json
from services.gee import initialize_gee
from services.suhi_unit import run_batch
from services.utils import UZBEKISTAN_CITIES


def parse_args():
    p = argparse.ArgumentParser(description='SUHI unit runner')
    p.add_argument('--cities', nargs='*', help='List of cities (default: all configured cities)')
    p.add_argument('--start-year', type=int, default=2016)
    p.add_argument('--end-year', type=int, default=2024)
    p.add_argument('--download-scale', type=int, default=100, help='Download scale in meters')
    return p.parse_args()


def main():
    args = parse_args()
    ok = initialize_gee()
    if not ok:
        print('GEE initialization failed. Authenticate and try again.')
        return
    # Process all configured cities
    cities = args.cities if args.cities else list(UZBEKISTAN_CITIES.keys())
    years = list(range(args.start_year, args.end_year + 1))
    results = run_batch(cities=cities, years=years, download_scale=args.download_scale)
    print('SUHI batch complete. Summary:')
    for c in results:
        for y in results[c]:
            print(c, y, results[c][y].get('summary_json'))
    # write combined batch summary into reports
    from pathlib import Path
    reports_dir = Path('suhi_analysis_output') / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_file = reports_dir / 'suhi_batch_summary.json'
    try:
        with open(out_file, 'w', encoding='utf-8') as fh:
            json.dump(results, fh, indent=2)
        print('Wrote SUHI batch summary to', out_file)
    except Exception:
        print('Failed to write SUHI batch summary')

if __name__ == '__main__':
    main()
