"""Small smoke-run orchestrator for all units.

Runs a tiny subset of cities and years for quick verification and saves
compact JSON summaries under `suhi_analysis_output/reports`.
"""
from pathlib import Path
import json

from services import gee
from services.utils import create_output_directories
from services import nightlight, lulc, suhi_unit, auxiliary_data


def main():
    ok = gee.initialize_gee()
    if not ok:
        print('GEE init failed; aborting smoke runs')
        return

    out_dirs = create_output_directories()
    base = out_dirs['base']

    cities = ['Tashkent', 'Nukus']
    years = [2018, 2019]

    reports_dir = base / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    # Nightlight smoke (small): thumbnails + zonal stats
    print('Running nightlight smoke...')
    nl = nightlight.run_batch_viirs(cities, years, base)
    p_nl = reports_dir / 'smoke_nightlight.json'
    with open(p_nl, 'w', encoding='utf-8') as fh:
        json.dump(nl, fh, indent=2)
    results['nightlight'] = str(p_nl)
    print('Nightlight smoke done ->', p_nl)

    # Auxiliary smoke: vegetation/temperature and uncertainty
    print('Running auxiliary (vegetation) smoke...')
    aux = auxiliary_data.run_batch(cities=cities, years=years, download_scale=30)
    p_aux = reports_dir / 'smoke_auxiliary.json'
    with open(p_aux, 'w', encoding='utf-8') as fh:
        json.dump(aux, fh, indent=2)
    results['auxiliary'] = str(p_aux)
    print('Auxiliary smoke done ->', p_aux)

    # LULC smoke: ESRI-only generation (categorical uncertainty)
    print('Running LULC ESRI-only generation smoke...')
    lulc_results = []
    for city in cities:
        for y in years:
            print(f'  LULC ESRI-only {city} {y}...')
            r = lulc.generate_esri_only_local(base, city, y, coarse_scale=200)
            lulc_results.append(r)
    p_lulc = base / 'lulc_summary_smoke.json'
    with open(p_lulc, 'w', encoding='utf-8') as fh:
        json.dump(lulc_results, fh, indent=2)
    # Also store a copy in the reports folder for easy access
    p_lulc_report = reports_dir / 'smoke_lulc.json'
    with open(p_lulc_report, 'w', encoding='utf-8') as fh:
        json.dump(lulc_results, fh, indent=2)
    results['lulc'] = str(p_lulc_report)
    print('LULC smoke done ->', p_lulc_report)

    # SUHI smoke: small SUHI stats run
    print('Running SUHI smoke...')
    suhi = suhi_unit.run_batch(cities=cities, years=years, download_scale=100)
    p_suhi = reports_dir / 'smoke_suhi.json'
    with open(p_suhi, 'w', encoding='utf-8') as fh:
        json.dump(suhi, fh, indent=2)
    results['suhi'] = str(p_suhi)
    print('SUHI smoke done ->', p_suhi)

    # Master report
    master = reports_dir / 'smoke_runs_index.json'
    with open(master, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, indent=2)
    print('Smoke runs complete. Index ->', master)


if __name__ == '__main__':
    main()
