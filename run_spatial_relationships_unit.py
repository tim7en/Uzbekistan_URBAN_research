"""Unit test: spatial relationships between vegetation patches and built-up areas.

Produces per-city JSON reports with:
- distance-to-vegetation map stats for built-up pixels
- vegetation accessibility index (mean distance, population-weighted optional)
- edge density and fragmentation metrics (edge length per area, mean patch size)
- patch isolation (mean nearest-neighbor distance between vegetation patches)

This script runs independently and writes outputs to `suhi_analysis_output/reports/`.
"""
import json
from pathlib import Path
from typing import List, Dict, Any

import ee

from services.utils import create_output_directories
from services.gee import initialize_gee
from services.spatial_relationships import run_for_cities


def analyze_city(city: str, year: int = None, scale: int = None) -> Dict[str, Any]:
    if year is None:
        year = (ANALYSIS_CONFIG.get('years') or [2019])[0]
    city_info = UZBEKISTAN_CITIES[city]
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    region = center.buffer(city_info['buffer_m']).bounds()
    if scale is None:
        scale = ANALYSIS_CONFIG.get('target_resolution_m', 100)

    out: Dict[str, Any] = {'city': city, 'year': year, 'scale': scale}

    # Load ESRI LULC using existing helper
    classifications = load_all_classifications(year, region, f"{year}-01-01", f"{year}-12-31", optimal_scales={'scale': max(200, scale)})
    esri_full = classifications.get('esri_full')
    esri_built = classifications.get('esri_built')
    if esri_full is None:
        out['error'] = 'ESRI LULC not available'
        return out

    # Define vegetation classes from ESRI_CLASSES mapping
    from services.utils import ESRI_CLASSES
    veg_class_ids = [k for k, v in ESRI_CLASSES.items() if 'Tree' in v or 'Crops' in v or 'Vegetation' in v or 'Rangeland' in v]
    # Create binary masks
    veg_mask = None
    for cid in veg_class_ids:
        try:
            band = esri_full.select(0)
            m = band.eq(cid)
            veg_mask = m if veg_mask is None else veg_mask.Or(m)
        except Exception:
            continue
    if veg_mask is None:
        out['error'] = 'No vegetation classes found in ESRI mapping'
        return out

    built_mask = esri_built if esri_built is not None else esri_full.eq(7)

    # Connected components for patches (vegetation and built-up)
    veg_cc = veg_mask.selfMask().connectedComponents(ee.Kernel.plus(1), 256)
    built_cc = built_mask.selfMask().connectedComponents(ee.Kernel.plus(1), 256)

    # Patch size (pixel counts * scale^2) and mean patch area
    def patch_stats(cc_image):
        # cc_image has property 'labels'
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
        # compute areas (m2)
        areas = [c * (scale * scale) for c in vals.values()]
        mean_area = sum(areas) / len(areas) if areas else 0
        median_area = sorted(areas)[len(areas)//2] if areas else 0
        return {'patch_count': len(areas), 'mean_patch_area_m2': mean_area, 'median_patch_area_m2': median_area}

    out['veg_patches'] = patch_stats(veg_cc)
    out['built_patches'] = patch_stats(built_cc)

    # Distance from each built pixel to nearest vegetation patch
    # Use distance() on veg_mask (distance in meters if scale in meters)
    veg_distance = veg_mask.Not().distance(ee.Kernel.euclidean(1))
    # For built-up pixels only
    built_distance = veg_distance.updateMask(built_mask)

    # Compute zonal stats for built distances within city urban_core
    zones = {'city': region}
    try:
        dist_stats = error_assessment.compute_zonal_uncertainty(built_distance, zones, scale=scale)
        out['built_distance_stats'] = dist_stats
    except Exception as e:
        out['built_distance_error'] = str(e)

    # Vegetation accessibility index: mean distance to green for all pixels
    try:
        veg_dist_all = veg_distance
        acc_stats = error_assessment.compute_zonal_uncertainty(veg_dist_all, zones, scale=scale)
        out['vegetation_accessibility'] = acc_stats
    except Exception as e:
        out['vegetation_accessibility_error'] = str(e)

    # Edge density (approximate) - compute boundary length by differencing dilation/erosion
    try:
        # Use focal operations to approximate edges: built_mask XOR built_mask.focal_max(1)
        built_dilate = built_mask.focal_max(1, 'square', 'meters')
        built_erode = built_mask.focal_min(1, 'square', 'meters')
        built_edge = built_dilate.And(built_erode.Not())
        # Edge pixel count
        edge_count = built_edge.reduceRegion(reducer=ee.Reducer.sum(), geometry=region, scale=scale, maxPixels=1e10, bestEffort=True).getInfo()
        first = next(iter(edge_count.values())) if edge_count else 0
        edge_pixels = int(first) if first else 0
        region_area_m2 = region.area().getInfo()
        edge_density_m_per_km2 = (edge_pixels * scale) / (region_area_m2 / 1e6) if region_area_m2 else None
        out['edge_density_m_per_km2'] = edge_density_m_per_km2
    except Exception as e:
        out['edge_density_error'] = str(e)

    # Patch isolation: mean nearest-neighbor distance between vegetation patch centroids
    try:
        # centroids of veg patches via connectedComponents label reducer
        # compute centroid per label via ee.Image.pixelLonLat() weighted by label presence
        labels = veg_cc.select('labels')
        lab_hist = labels.reduceRegion(reducer=ee.Reducer.frequencyHistogram(), geometry=region, scale=scale, maxPixels=1e10, bestEffort=True).getInfo()
        centroid_list = []
        try:
            first = next(iter(lab_hist.values()))
            for lbl in first.keys():
                lbl_int = int(lbl)
                mask_lbl = labels.eq(lbl_int)
                coords = ee.Image.pixelLonLat().updateMask(mask_lbl).reduceRegion(reducer=ee.Reducer.mean(), geometry=region, scale=scale, maxPixels=1e10, bestEffort=True).getInfo()
                if coords:
                    lon = coords.get('longitude')
                    lat = coords.get('latitude')
                    if lon is not None and lat is not None:
                        centroid_list.append((float(lon), float(lat)))
        except Exception:
            centroid_list = []
        # compute pairwise nearest neighbor distances (approx on client)
        import math
        nn_distances = []
        for i, (lon1, lat1) in enumerate(centroid_list):
            mind = None
            for j, (lon2, lat2) in enumerate(centroid_list):
                if i == j:
                    continue
                # haversine
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

    return out


def main(cities: List[str] = None, years: List[int] = None, scale: int = None):
    ok = initialize_gee()
    if not ok:
        print('GEE init failed; aborting spatial relationships unit')
        return

    dirs = create_output_directories()
    result = run_for_cities(cities=cities, years=years, scale=scale)
    out_file = Path(__file__).parent / 'suhi_analysis_output' / 'reports' / 'spatial_relationships_report.json'
    with open(out_file, 'w', encoding='utf-8') as fh:
        json.dump(result, fh, indent=2)
    print(f"Wrote report: {out_file}")


if __name__ == '__main__':
    main(cities=['Tashkent','Nukus'], years=[2018,2019], scale=200)
