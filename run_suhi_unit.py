"""Runner for SUHI unit maps (2017-2024 by default).

Usage: python run_suhi_unit.py
"""
import json
from services.gee import initialize_gee
from services.suhi_unit import run_batch

def main():
    ok = initialize_gee()
    if not ok:
        print('GEE initialization failed. Authenticate and try again.')
        return
    # Sample small batch to limit runtime and outputs
    cities = ['Tashkent','Nukus','Andijan']
    years = list(range(2017, 2025))
    results = run_batch(cities=cities, years=years, download_scale=100)
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
