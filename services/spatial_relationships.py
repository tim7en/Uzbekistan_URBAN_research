"""Spatial relationships service: proximity and fragmentation metrics.

Exports a reusable function `run_for_cities` which performs the analysis
over years and returns a dict with per-year metrics and temporal changes.
This module assumes Earth Engine is already initialized by caller.
"""
import json
from typing import List, Dict, Any, Optional

import ee

from .utils import UZBEKISTAN_CITIES, ANALYSIS_CONFIG, ESRI_CLASSES
from .classification import load_all_classifications
from . import error_assessment


def _make_veg_mask(esri_full: ee.Image, region: ee.Geometry) -> ee.Image:
    veg_class_ids = [k for k, v in ESRI_CLASSES.items() if 'Tree' in v or 'Crops' in v or 'Vegetation' in v or 'Rangeland' in v]
    veg_mask = None
    band = esri_full.select(0)
    for cid in veg_class_ids:
        try:
            m = band.eq(cid)
            veg_mask = m if veg_mask is None else veg_mask.Or(m)
        except Exception:
            continue
    if veg_mask is None:
        # fallback: no vegetation
        return ee.Image(0).clip(region)
    return veg_mask.rename('veg').clip(region)


def _make_built_mask(esri_full: ee.Image, esri_built: Optional[ee.Image], region: ee.Geometry) -> ee.Image:
    if esri_built is not None:
        return esri_built.rename('built').clip(region)
    try:
        return esri_full.select(0).eq(7).rename('built').clip(region)
    except Exception:
        return ee.Image(0).clip(region)


def _patch_stats_from_cc(cc_image: ee.Image, region: ee.Geometry, scale: int) -> Dict[str, Any]:
    label_band = cc_image.select('labels')
    hist = label_band.reduceRegion(reducer=ee.Reducer.frequencyHistogram(), geometry=region, scale=scale, maxPixels=1e10, bestEffort=True)
    hist_info = hist.getInfo() if hist else {}
    vals = {}
    try:
        first = next(iter(hist_info.values()))
        for k, v in first.items():
            vals[int(k)] = int(v)
    except Exception:
        vals = {}
    areas = [c * (scale * scale) for c in vals.values()]
    mean_area = sum(areas) / len(areas) if areas else 0
    median_area = sorted(areas)[len(areas)//2] if areas else 0
    return {'patch_count': len(areas), 'mean_patch_area_m2': mean_area, 'median_patch_area_m2': median_area}


def analyze_city_year(city: str, year: int, scale: int) -> Dict[str, Any]:
    city_info = UZBEKISTAN_CITIES[city]
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    region = center.buffer(city_info['buffer_m']).bounds()

    out: Dict[str, Any] = {'city': city, 'year': year, 'scale': scale}

    classifications = load_all_classifications(year, region, f"{year}-01-01", f"{year}-12-31", optimal_scales={'scale': max(200, scale)})
    esri_full = classifications.get('esri_full')
    esri_built = classifications.get('esri_built')
    if esri_full is None:
        out['error'] = 'ESRI LULC not available'
        return out

    veg_mask = _make_veg_mask(esri_full, region)
    built_mask = _make_built_mask(esri_full, esri_built, region)

    veg_cc = veg_mask.selfMask().connectedComponents(ee.Kernel.plus(1), 256)
    built_cc = built_mask.selfMask().connectedComponents(ee.Kernel.plus(1), 256)

    out['veg_patches'] = _patch_stats_from_cc(veg_cc, region, scale)
    out['built_patches'] = _patch_stats_from_cc(built_cc, region, scale)

    # Distance from each pixel to nearest veg (meters). Use a euclidean kernel
    # specified in meters to avoid API ambiguity. Cap search distance to 10 km.
    veg_distance = veg_mask.distance(ee.Kernel.euclidean(10000, 'meters'))
    built_distance = veg_distance.updateMask(built_mask)

    zones = {'city': region}
    try:
        out['built_distance_stats'] = error_assessment.compute_zonal_uncertainty(built_distance, zones, scale=scale)
    except Exception as e:
        out['built_distance_error'] = str(e)

    try:
        out['vegetation_accessibility'] = error_assessment.compute_zonal_uncertainty(veg_distance, zones, scale=scale)
    except Exception as e:
        out['vegetation_accessibility_error'] = str(e)

    # Edge density proxy
    try:
        built_dilate = built_mask.focal_max(1, 'square', 'meters')
        built_erode = built_mask.focal_min(1, 'square', 'meters')
        built_edge = built_dilate.And(built_erode.Not())

        edge_count = built_edge.reduceRegion(reducer=ee.Reducer.sum(), geometry=region, scale=scale, maxPixels=1e10, bestEffort=True).getInfo()
        first = next(iter(edge_count.values())) if edge_count else 0
        edge_pixels = int(first) if first else 0
        # Use explicit maxError to avoid geometry.area errors on complex geometries
        region_area_m2 = region.area(1).getInfo()
        edge_density_m_per_km2 = (edge_pixels * scale) / (region_area_m2 / 1e6) if region_area_m2 else None
        out['edge_density_m_per_km2'] = edge_density_m_per_km2
    except Exception as e:
        out['edge_density_error'] = str(e)

    # Patch isolation: centroids and mean nearest neighbor
    try:
        labels = veg_cc.select('labels')
        try:
            # Vectorize labeled patches server-side (reduceToVectors) and compute centroids
            # reduceToVectors with some reducers expects multiple bands; add a dummy band
            vectors = labels.addBands(ee.Image(0).rename('dummy')).reduceToVectors(reducer=ee.Reducer.first(), geometry=region, scale=scale, maxPixels=1e10)
            centroids = vectors.map(lambda f: ee.Feature(f.geometry().centroid(1)))
            centroids_info = centroids.getInfo() if centroids else None
            centroid_list = []
            if centroids_info and 'features' in centroids_info:
                for feat in centroids_info['features']:
                    geom = feat.get('geometry')
                    if geom and geom.get('coordinates'):
                        coords = geom['coordinates']
                        centroid_list.append((float(coords[0]), float(coords[1])))
            # compute pairwise nearest neighbor distances (client-side on small vector list)
            import math
            nn_distances = []
            for i, (lon1, lat1) in enumerate(centroid_list):
                mind = None
                for j, (lon2, lat2) in enumerate(centroid_list):
                    if i == j:
                        continue
                    R = 6371000.0
                    phi1 = math.radians(lat1)
                    phi2 = math.radians(lat2)
                    dphi = math.radians(lat2 - lat1)
                    dlambda = math.radians(lon2 - lon1)
                    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
                    d = 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))
                    if mind is None or d < mind:
                        mind = d
                if mind is not None:
                    nn_distances.append(mind)
            mean_nn = sum(nn_distances)/len(nn_distances) if nn_distances else None
            out['veg_patch_isolation_mean_m'] = mean_nn
        except Exception as e:
            out['veg_patch_isolation_error'] = str(e)
    except Exception as e:
        out['veg_patch_isolation_error'] = str(e)

    return out


def run_for_cities(cities: Optional[List[str]] = None, years: Optional[List[int]] = None, scale: Optional[int] = None) -> Dict[str, Any]:
    if cities is None:
        cities = list(UZBEKISTAN_CITIES.keys())
    if years is None:
        years = list(range(2017, 2025))
    if scale is None:
        scale = ANALYSIS_CONFIG.get('target_resolution_m', 100)
    # ensure scale is an int for downstream functions
    scale = int(scale)

    reports: Dict[str, Any] = {}
    for city in cities:
        reports[city] = {}
        for y in years:
            try:
                reports[city][str(y)] = analyze_city_year(city, y, scale)
            except Exception as e:
                reports[city][str(y)] = {'error': str(e)}

    # temporal summary between first and last
    temporal_summary: Dict[str, Any] = {}
    start_year = years[0]
    end_year = years[-1]
    for city in cities:
        cs = reports.get(city, {})
        start = cs.get(str(start_year), {})
        end = cs.get(str(end_year), {})
        changes: Dict[str, Any] = {}
        try:
            sc = start.get('veg_patches', {}).get('patch_count')
            ec = end.get('veg_patches', {}).get('patch_count')
            if sc is not None and ec is not None:
                changes['veg_patch_count_change'] = ec - sc
                changes['veg_patch_count_pct'] = ((ec - sc) / sc * 100) if sc else None

            s_ma = start.get('veg_patches', {}).get('mean_patch_area_m2')
            e_ma = end.get('veg_patches', {}).get('mean_patch_area_m2')
            if s_ma is not None and e_ma is not None:
                changes['veg_mean_patch_area_m2_change'] = e_ma - s_ma
                changes['veg_mean_patch_area_m2_pct'] = ((e_ma - s_ma) / s_ma * 100) if s_ma else None

            s_bd = start.get('built_distance_stats', {}).get('city', {}).get('mean')
            e_bd = end.get('built_distance_stats', {}).get('city', {}).get('mean')
            if s_bd is not None and e_bd is not None:
                changes['built_mean_distance_m_change'] = e_bd - s_bd
                changes['built_mean_distance_m_pct'] = ((e_bd - s_bd) / s_bd * 100) if s_bd else None

            s_va = start.get('vegetation_accessibility', {}).get('city', {}).get('mean')
            e_va = end.get('vegetation_accessibility', {}).get('city', {}).get('mean')
            if s_va is not None and e_va is not None:
                changes['veg_access_mean_m_change'] = e_va - s_va
                changes['veg_access_mean_m_pct'] = ((e_va - s_va) / s_va * 100) if s_va else None

            s_ed = start.get('edge_density_m_per_km2')
            e_ed = end.get('edge_density_m_per_km2')
            if s_ed is not None and e_ed is not None:
                try:
                    changes['edge_density_m_per_km2_change'] = e_ed - s_ed
                    changes['edge_density_m_per_km2_pct'] = ((e_ed - s_ed) / s_ed * 100) if s_ed else None
                except Exception:
                    pass

            s_pi = start.get('veg_patch_isolation_mean_m')
            e_pi = end.get('veg_patch_isolation_mean_m')
            if s_pi is not None and e_pi is not None:
                changes['veg_patch_isolation_mean_m_change'] = e_pi - s_pi
                changes['veg_patch_isolation_mean_m_pct'] = ((e_pi - s_pi) / s_pi * 100) if s_pi else None
        except Exception as e:
            changes['error'] = str(e)
        temporal_summary[city] = changes

    return {'per_year': reports, 'temporal_changes': temporal_summary, 'analysis_period': f"{start_year}-{end_year}"}
