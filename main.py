"""Orchestrator entrypoint for SUHI analysis (minimal).

Delegates all heavy work to the refactored `services` package. This file
is intentionally tiny so it's easy to run a quick smoke test or use as the
CI entrypoint.
"""

import argparse
import subprocess
from pathlib import Path

from services import gee, utils


UNIT_RUNNERS = {
    'nightlight': Path('run_nightlight_unit.py'),
    'lulc': Path('run_lulc_unit.py'),
    'suhi': Path('run_suhi_unit.py'),
    'auxiliary': Path('run_auxiliary_unit.py'),
    'spatial_relationships': Path('run_spatial_relationships_unit.py'),
}


def _run_script(path: Path, args: list) -> int:
    cmd = ['python', str(path)] + args
    print('Running:', ' '.join(cmd))
    return subprocess.call(cmd)


def main():
    p = argparse.ArgumentParser(description='Run unit pipelines for SUHI project')
    p.add_argument('--unit', choices=['nightlight', 'lulc', 'suhi', 'auxiliary', 'spatial_relationships', 'all'], default='all', help='Which unit to run')
    p.add_argument('--start-year', type=int, default=2016)
    p.add_argument('--end-year', type=int, default=2024)
    p.add_argument('--cities', nargs='*', help='Cities to process (default: configured subset)')
    p.add_argument('--highres', action='store_true', help='Include high-res outputs where supported')
    p.add_argument('--export-drive', action='store_true', help='Start Drive exports for units that support it')
    args = p.parse_args()

    if not gee.initialize_gee():
        print('GEE initialization failed; aborting')
        return

    utils.create_output_directories()

    units = [args.unit] if args.unit != 'all' else ['nightlight', 'lulc', 'suhi', 'auxiliary', 'spatial_relationships']
    for unit in units:
        runner = UNIT_RUNNERS.get(unit)
        if not runner or not runner.exists():
            print(f"Runner script for unit '{unit}' not found: {runner}")
            continue

        common_args = [
            '--start-year', str(args.start_year), '--end-year', str(args.end_year)
        ]
        if args.cities:
            common_args += ['--cities'] + args.cities
        if args.highres:
            common_args += ['--save-highres']
        if args.export_drive:
            common_args += ['--export-drive']

        # Unit-specific flag mappings
        if unit == 'nightlight':
            # run generation + analysis for nightlight
            ret = _run_script(runner, ['--generate', '--save-local-geotiff', '--export-drive', '--analyze'] + common_args)
        elif unit == 'lulc':
            ret = _run_script(runner, ['--generate', '--save-local', '--save-highres', '--analyze'] + common_args)
        elif unit == 'suhi':
            # SUHI runner is self-contained; pass common args if present (some flags ignored)
            ret = _run_script(runner, common_args)
        elif unit == 'auxiliary':
            # Auxiliary/biodiversity-related runner is self-contained; run it
            ret = _run_script(runner, common_args)
        elif unit == 'spatial_relationships':
            # Spatial relationships unit (vegetation vs built-up metrics)
            ret = _run_script(runner, common_args)
        else:
            ret = 1

        if ret != 0:
            print(f"Unit '{unit}' runner exited with code {ret}")


if __name__ == '__main__':
    main()
