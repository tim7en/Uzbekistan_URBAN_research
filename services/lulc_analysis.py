import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
import rasterio
from rasterio.enums import Resampling
import rasterio.warp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def _read_image(path: Path) -> Tuple[np.ndarray, float]:
    """Read a single-band raster and return array and pixel area in m^2."""
    with rasterio.open(path) as src:
        arr = src.read(1, masked=True)
        transform = src.transform
        crs = src.crs
        # compute pixel area
        if crs and crs.is_geographic:
            pixel_deg_x = abs(transform.a)
            pixel_deg_y = abs(transform.e)
            meters_per_deg = 111320.0
            px_m = meters_per_deg * pixel_deg_x
            py_m = meters_per_deg * pixel_deg_y
            pixel_area = px_m * py_m
        else:
            pixel_area = abs(transform.a) * abs(transform.e)
    return np.array(arr), float(pixel_area)


def class_area_counts(arr: np.ndarray, pixel_area: float) -> Dict[str, float]:
    """Return area in m^2 per integer class in the array."""
    if np.ma.is_masked(arr):
        data = arr.filled(np.nan)
    else:
        data = arr.astype(float)
    uniq, counts = np.unique(data[~np.isnan(data)], return_counts=True)
    out = {str(int(u)): int(c) * pixel_area for u, c in zip(uniq, counts)}
    return out


def time_series_for_city(base: Path, city: str, dataset_prefix: str, years: List[int]) -> Dict[int, Dict[str, float]]:
    """For a dataset (e.g. 'esri_full' or 'dynamic_world'), compute area per class per year.
    Returns dict year -> {class: area_m2}
    """
    out: Dict[int, Dict[str, float]] = {}
    for year in years:
        high_path = base / 'lulc_highres' / city / f"{dataset_prefix}_{year}_highres.tif"
        coarse_path = base / 'lulc' / city / f"{dataset_prefix}_{year}_coarse.tif"
        chosen = None
        if high_path.exists():
            chosen = high_path
        elif coarse_path.exists():
            chosen = coarse_path
        else:
            out[year] = {}
            continue

        try:
            arr, pixel_area = _read_image(chosen)
            counts = class_area_counts(arr, pixel_area)
            out[year] = counts
        except Exception as e:
            out[year] = {'error': str(e)}
    return out


def trend_for_class(area_by_year: Dict[int, float]) -> Dict[str, Any]:
    """Compute linear trend (slope in m2 per year) and R^2 for a time series dict year->area."""
    years = sorted([y for y in area_by_year.keys() if isinstance(area_by_year[y], (int, float)) and area_by_year[y] >= 0])
    if len(years) < 2:
        return {'slope': None, 'r2': None}
    yvals = np.array([area_by_year[y] for y in years], dtype=float)
    x = np.array(years, dtype=float)
    m, b = np.polyfit(x, yvals, 1)
    yhat = m * x + b
    ss_res = np.sum((yvals - yhat) ** 2)
    ss_tot = np.sum((yvals - np.mean(yvals)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else None
    return {'slope_m2_per_year': float(m), 'intercept_m2': float(b), 'r2': float(r2) if r2 is not None else None}


def plot_trend(years: List[int], values: List[float], out_path: Path, title: str, ylabel: str = 'Area (m2)'):
    plt.figure(figsize=(6, 3.5))
    plt.plot(years, values, marker='o')
    plt.grid(True, alpha=0.3)
    plt.title(title)
    plt.xlabel('Year')
    plt.ylabel(ylabel)
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150)
    plt.close()


def compare_dataset_against_esri(base: Path, city: str, dataset_prefix: str, years: List[int]) -> Dict[int, Any]:
    """Compare a dataset to ESRI reference per year. Returns per-year overall accuracy and per-class producer/user accuracies."""
    results: Dict[int, Any] = {}
    for year in years:
        esri_path = base / 'lulc_highres' / city / f"esri_full_{year}_highres.tif"
        if not esri_path.exists():
            esri_path = base / 'lulc' / city / f"esri_full_{year}_coarse.tif"
        test_path = base / 'lulc_highres' / city / f"{dataset_prefix}_{year}_highres.tif"
        if not test_path.exists():
            test_path = base / 'lulc' / city / f"{dataset_prefix}_{year}_coarse.tif"

        if not esri_path.exists() or not test_path.exists():
            results[year] = {'error': 'missing files'}
            continue

        try:
            test_arr, _ = _read_image(test_path)
            esri_arr, _ = _read_image(esri_path)
            if test_arr.shape != esri_arr.shape:
                # resample test to esri using rasterio.warp
                with rasterio.open(test_path) as src_test, rasterio.open(esri_path) as src_esri:
                    dst_shape = (src_esri.height, src_esri.width)
                    dest = np.empty(dst_shape, dtype=src_test.dtypes[0])
                    rasterio.warp.reproject(
                        source=rasterio.band(src_test, 1),
                        destination=dest,
                        src_transform=src_test.transform,
                        src_crs=src_test.crs,
                        dst_transform=src_esri.transform,
                        dst_crs=src_esri.crs,
                        resampling=Resampling.nearest
                    )
                    test_flat = dest.ravel()
                    esri_flat = np.array(esri_arr).ravel()
            else:
                test_flat = np.array(test_arr).ravel()
                esri_flat = np.array(esri_arr).ravel()

            mask = (~np.isnan(test_flat)) & (~np.isnan(esri_flat))
            test_flat = test_flat[mask]
            esri_flat = esri_flat[mask]
            if test_flat.size == 0:
                results[year] = {'error': 'no overlapping pixels'}
                continue

            overall = float((test_flat == esri_flat).sum()) / float(test_flat.size)
            classes = np.unique(np.concatenate([np.unique(esri_flat), np.unique(test_flat)]))
            per_class = {}
            for c in classes:
                c = float(c)
                tp = float(((test_flat == c) & (esri_flat == c)).sum())
                ref_total = float((esri_flat == c).sum())
                test_total = float((test_flat == c).sum())
                producer = float(tp / ref_total) if ref_total > 0 else None
                user = float(tp / test_total) if test_total > 0 else None
                per_class[str(int(c))] = {'producer_accuracy': producer, 'user_accuracy': user, 'tp': int(tp), 'ref_total': int(ref_total), 'test_total': int(test_total)}

            results[year] = {'overall_accuracy': overall, 'per_class': per_class}
        except Exception as e:
            results[year] = {'error': str(e)}

    return results


def run_city_lulc_analysis(base: Path, city: str, start_year: int, end_year: int) -> Dict[str, Any]:
    years = list(range(start_year, end_year + 1))
    out_dir = base / 'lulc_analysis' / city
    out_dir.mkdir(parents=True, exist_ok=True)
    datasets = ['esri_full', 'dynamic_world', 'ghsl_pct', 'esa_map', 'modis_map']
    summary: Dict[str, Any] = {'city': city, 'years': years, 'datasets': {}}

    for ds in datasets:
        ts = time_series_for_city(base, city, ds, years)
        classes = set()
        for y, d in ts.items():
            if isinstance(d, dict):
                classes.update([k for k in d.keys() if k != 'error'])

        ds_summary = {'time_series': ts, 'trends': {}}
        for c in sorted(classes):
            series = {y: (ts[y].get(c, 0) if isinstance(ts[y], dict) else 0) for y in years}
            trend = trend_for_class(series)
            ds_summary['trends'][c] = {'series': series, 'trend': trend}
            try:
                yrs = sorted(series.keys())
                vals = [float(series[y]) for y in yrs]
                plot_trend(yrs, vals, out_dir / f'{ds}_class_{c}_trend.png', title=f'{city} {ds} class {c} trend')
            except Exception:
                pass

        summary['datasets'][ds] = ds_summary

    comparisons = {}
    for ds in [d for d in datasets if d != 'esri_full']:
        comp = compare_dataset_against_esri(base, city, ds, years)
        comparisons[ds] = comp

    summary['comparisons_against_esri'] = comparisons

    with open(out_dir / f'{city}_lulc_analysis_{years[0]}_{years[-1]}.json', 'w', encoding='utf-8') as fh:
        json.dump(summary, fh, indent=2)

    return summary
