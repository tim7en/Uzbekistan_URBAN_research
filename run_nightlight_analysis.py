"""Runner script: batch nightlight analysis (VIIRS) for selected Uzbekistan cities.

Generates thumbnails, per-city statistics JSON, histograms and a short markdown
report describing spatial and temporal characteristics of the used datasets.
"""
from pathlib import Path
import json
from services import analyze_nightlights, gee
from services import nightlight
from services.utils import create_output_directories, UZBEKISTAN_CITIES, ANALYSIS_CONFIG


def main():
    out_dirs = create_output_directories()
    success = gee.initialize_gee()
    if not success:
        print("GEE init failed — aborting nightlight run")
        return

    years = list(range(2016, 2025))  # inclusive 2016-2024
    # Select first 14 cities from config
    cities = list(UZBEKISTAN_CITIES.keys())[:2]

    # Choose whether to save a coarse local GeoTIFF and whether to export a high-res GeoTIFF to Drive
    SAVE_LOCAL_GEOTIFF = True
    LOCAL_GTIFF_SCALE = 1000  # meters (coarse)
    EXPORT_TO_DRIVE = False
    DRIVE_GTIFF_SCALE = 200   # meters (higher resolution export)

    results = []
    for city in cities:
        city_info = UZBEKISTAN_CITIES[city]
        for y in years:
            print(f"Running VIIRS for {city} {y}...")
            # run thumbnail + stats
            res = nightlight.run_city_year_viirs(city, city_info, y, out_dirs['base'])
            # if export enabled and viirs image available, create export task
            try:
                zones = nightlight.create_analysis_zones(city_info)
            except Exception:
                zones = None
            # Optionally save a coarse GeoTIFF locally
            if SAVE_LOCAL_GEOTIFF:
                try:
                    if zones:
                        geom = zones['full_extent']
                        viirs_img = nightlight.load_viirs_monthly(y, geom)
                        out_dir = out_dirs['base'] / 'nightlights' / city
                        local_tif = nightlight.download_viirs_geotiff(viirs_img, geom, scale=LOCAL_GTIFF_SCALE, out_path=out_dir, file_name=f"viirs_{y}_coarse")
                        res.setdefault('exports', {})['local_tif'] = str(local_tif) if local_tif else None
                except Exception as e:
                    res.setdefault('exports', {})['local_error'] = str(e)

            if EXPORT_TO_DRIVE:
                try:
                    geom = zones['full_extent'] if zones else None
                    if geom is not None:
                        viirs_img = nightlight.load_viirs_monthly(y, geom)
                        description = f"VIIRS_{city}_{y}"
                        folder = 'Nightlights_Exports'
                        task = nightlight.export_viirs_geotiff_drive(viirs_img, geom, scale=DRIVE_GTIFF_SCALE, description=description, folder=folder, file_prefix=description)
                        res.setdefault('exports', {})['drive_task'] = getattr(task, 'id', None) if task else None
                except Exception as e:
                    res.setdefault('exports', {})['drive_error'] = str(e)
            results.append(res)
            


    # Save aggregated results
    out_file = out_dirs['base'] / 'nightlights_summary.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
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
    cities = list(UZBEKISTAN_CITIES.keys())[:2]
    years = list(range(2016, 2025))
    results = analyze_nightlights.analyze_cities_years(out_dirs['base'], cities, years, lit_threshold=1.0)
    summary = analyze_nightlights.generate_summary_report(results, out_dirs['base'])
    print('Analysis complete. Summary markdown:', summary)

if __name__ == '__main__':
    main()
