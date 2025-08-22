"""Runner for auxiliary data unit tests: NDVI/EVI/LST seasonal composites.

Usage (simple):
  python run_auxiliary_unit.py

It will run the service for configured cities and years and write
results into `suhi_analysis_output/vegetation/<city>/` and
`suhi_analysis_output/temperature/<city>/` with per-city JSON summaries.
"""
import argparse
import json
from pathlib import Path
from services.auxiliary_data import run_batch
from services.gee import initialize_gee


def main():
    p = argparse.ArgumentParser(description='Run auxiliary data extractor')
    p.add_argument('--start-year', type=int, default=None)
    p.add_argument('--end-year', type=int, default=None)
    p.add_argument('--cities', nargs='*', help='Cities to process')
    p.add_argument('--download-scale', type=int, default=30)
    p.add_argument('--verbose', action='store_true')
    args = p.parse_args()

    ok = initialize_gee()
    if not ok:
        print("GEE initialization failed or was cancelled. Authenticate and try again.")
        return

    years = None
    if args.start_year is not None and args.end_year is not None:
        years = list(range(args.start_year, args.end_year + 1))

    results = run_batch(cities=args.cities, years=years, download_scale=args.download_scale, verbose=args.verbose)

    out = Path('suhi_analysis_output') / 'reports'
    out.mkdir(parents=True, exist_ok=True)
    p = out / 'auxiliary_batch_results.json'
    with open(p, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, indent=2)
    print(f"Wrote batch results to {p}")


if __name__ == '__main__':
    main()
