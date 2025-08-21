"""Runner for auxiliary data unit tests: NDVI/EVI/LST seasonal composites.

Usage (simple):
  python run_auxiliary_unit.py

It will run the service for configured cities and years and write
results into `suhi_analysis_output/vegetation/<city>/` and
`suhi_analysis_output/temperature/<city>/` with per-city JSON summaries.
"""
import json
from pathlib import Path
from services.auxiliary_data import run_batch
from services.gee import initialize_gee


def main():
    # Ensure GEE is initialized (this may prompt for auth in interactive env)
    ok = initialize_gee()
    if not ok:
        print("GEE initialization failed or was cancelled. Authenticate and try again.")
        return

    # Default: run all configured cities and years in ANALYSIS_CONFIG
    results = run_batch()
    out = Path('suhi_analysis_output') / 'reports'
    out.mkdir(parents=True, exist_ok=True)
    p = out / 'auxiliary_batch_results.json'
    with open(p, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, indent=2)
    print(f"Wrote batch results to {p}")


if __name__ == '__main__':
    main()
