"""Coarse smoke-run orchestrator for all units at 500 m resolution.

This script runs a quick smoke test across all configured cities using coarse
resolution (500 m) and avoids any Drive exports or high-resolution downloads.
It calls service functions in-process so we can pass scale parameters directly.
"""
from pathlib import Path
import sys
import json

# Ensure repository root is on sys.path so local `services` package is importable
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from services import gee
from services.utils import create_output_directories, UZBEKISTAN_CITIES
from services import nightlight, lulc, suhi_unit, auxiliary_data, spatial_relationships


def main():
    ok = gee.initialize_gee()
    if not ok:
        print('GEE init failed; aborting coarse smoke runs')
        return

    out_dirs = create_output_directories()
    base = out_dirs['base']
    reports_dir = base / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)

    cities = list(UZBEKISTAN_CITIES.keys())
    years = [2018]  # single-year smoke run to keep time bounded

    results = {}

    # Nightlight (VIIRS) - native ~500-750m; run batch for all cities but keep it light
    print('Running nightlight coarse smoke...')
    try:
        nl = nightlight.run_batch_viirs(cities, years, base)
        p_nl = reports_dir / 'smoke_nightlight_coarse.json'
        with open(p_nl, 'w', encoding='utf-8') as fh:
            json.dump(nl, fh, indent=2)
        results['nightlight'] = str(p_nl)
        print('Nightlight coarse smoke done ->', p_nl)
    except Exception as e:
        print('Nightlight smoke failed:', e)

    # Auxiliary data at 500 m
    print('Running auxiliary coarse smoke...')
    try:
        aux = auxiliary_data.run_batch(cities=cities, years=years, download_scale=500, verbose=False)
        p_aux = reports_dir / 'smoke_auxiliary_coarse.json'
        with open(p_aux, 'w', encoding='utf-8') as fh:
            json.dump(aux, fh, indent=2)
        results['auxiliary'] = str(p_aux)
        print('Auxiliary coarse smoke done ->', p_aux)
    except Exception as e:
        print('Auxiliary smoke failed:', e)

    # LULC: generate ESRI-only local summaries using coarse_scale=500
    print('Running LULC coarse smoke (ESRI-only generation)...')
    try:
        lulc_results = []
        for city in cities:
            for y in years:
                try:
                    r = lulc.generate_esri_only_local(base, city, y, coarse_scale=500)
                    lulc_results.append(r)
                except Exception as e:
                    lulc_results.append({'city': city, 'year': y, 'error': str(e)})
        p_lulc = reports_dir / 'smoke_lulc_coarse.json'
        with open(p_lulc, 'w', encoding='utf-8') as fh:
            json.dump(lulc_results, fh, indent=2)
        results['lulc'] = str(p_lulc)
        print('LULC coarse smoke done ->', p_lulc)
    except Exception as e:
        print('LULC smoke failed:', e)

    # SUHI: call run_batch with download_scale=500
    print('Running SUHI coarse smoke...')
    try:
        suhi = suhi_unit.run_batch(cities=cities, years=years, download_scale=500)
        p_suhi = reports_dir / 'smoke_suhi_coarse.json'
        with open(p_suhi, 'w', encoding='utf-8') as fh:
            json.dump(suhi, fh, indent=2)
        results['suhi'] = str(p_suhi)
        print('SUHI coarse smoke done ->', p_suhi)
    except Exception as e:
        print('SUHI smoke failed:', e)

    # Spatial relationships: run with scale=500
    print('Running spatial relationships coarse smoke...')
    try:
        sr = spatial_relationships.run_for_cities(cities=cities, years=years, scale=500)
        p_sr = reports_dir / 'smoke_spatial_coarse.json'
        with open(p_sr, 'w', encoding='utf-8') as fh:
            json.dump(sr, fh, indent=2)
        results['spatial_relationships'] = str(p_sr)
        print('Spatial relationships coarse smoke done ->', p_sr)
    except Exception as e:
        print('Spatial relationships smoke failed:', e)

    # Master index
    master = reports_dir / 'smoke_runs_coarse_index.json'
    with open(master, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, indent=2)
    print('Coarse smoke runs complete. Index ->', master)


if __name__ == '__main__':
    main()
