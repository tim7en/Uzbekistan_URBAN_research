"""Spatial relationships service: proximity and fragmentation metrics - OPTIMIZED VERSION.

Exports a reusable function `run_for_cities` which performs the analysis
over years and returns a dict with per-year metrics and temporal changes.
This module assumes Earth Engine is already initialized by caller.
"""
import json
from typing import List, Dict, Any, Optional
import time

import ee

from .utils import UZBEKISTAN_CITIES, ANALYSIS_CONFIG, ESRI_CLASSES
from .classification import load_all_classifications
from . import error_assessment


def reduce_region(img: ee.Image, reducer: ee.Reducer, geom: ee.Geometry, scale: int, maxPixels: int = int(1e10)) -> ee.ComputedObject:
    """Helper to wrap reductions with tileScale for performance."""
    return img.reduceRegion(
        reducer=reducer,
        geometry=geom,
        scale=scale,
        maxPixels=maxPixels,
        bestEffort=True,
        tileScale=4  # Key performance improvement
    )


def _make_veg_mask(esri_full: ee.Image, region: ee.Geometry, scale: int) -> ee.Image:
    """Create vegetation mask from ESRI LULC classes."""
    veg_class_ids = [k for k, v in ESRI_CLASSES.items() if 'Tree' in v or 'Crops' in v or 'Vegetation' in v or 'Rangeland' in v]
    veg_mask = None
    
    # Use the correct band name 'esri_full' instead of index 0
    band = esri_full.select('esri_full')
    
    for cid in veg_class_ids:
        try:
            m = band.eq(cid)
            veg_mask = m if veg_mask is None else veg_mask.Or(m)
        except Exception:
            continue
    if veg_mask is None:
        # fallback: no vegetation
        return ee.Image(0).clip(region)
    
    # Reproject early to avoid hidden costs
    return veg_mask.rename('veg').clip(region).reproject(crs='EPSG:3857', scale=scale)


def _make_built_mask(esri_full: ee.Image, esri_built: Optional[ee.Image], region: ee.Geometry, scale: int) -> ee.Image:
    """Create built-up mask from ESRI data."""
    if esri_built is not None:
        built_mask = esri_built.rename('built').clip(region)
    else:
        try:
            # Use correct band name 'esri_full' instead of index 0
            built_mask = esri_full.select('esri_full').eq(7).rename('built').clip(region)
        except Exception:
            built_mask = ee.Image(0).clip(region)
    
    # Reproject early to avoid hidden costs
    return built_mask.reproject(crs='EPSG:3857', scale=scale)


def _fast_patch_stats(cc_image: ee.Image, region: ee.Geometry, scale: int) -> Dict[str, Any]:
    """Extract patch statistics without vectorization."""
    label_band = cc_image.select('labels')
    
    # Use connectedPixelCount for fast stats
    pixel_count_band = cc_image.select('pixelCount')
    
    # Get histogram with tileScale
    hist = reduce_region(
        label_band,
        ee.Reducer.frequencyHistogram(),
        region,
        scale
    )
    
    # Get basic statistics from pixelCount band
    count_stats = reduce_region(
        pixel_count_band,
        ee.Reducer.mean().combine(
            ee.Reducer.min(),
            sharedInputs=True
        ).combine(
            ee.Reducer.max(),
            sharedInputs=True
        ).combine(
            ee.Reducer.count(),
            sharedInputs=True
        ),
        region,
        scale
    )
    
    # Batch compute server-side
    results = ee.Dictionary({
        'histogram': hist,
        'stats': count_stats
    })
    
    return results  # Return server-side object, convert later


def _batch_compute_metrics(veg_mask: ee.Image, built_mask: ee.Image, region: ee.Geometry, scale: int) -> ee.Dictionary:
    """Compute all metrics server-side and return as single dictionary."""
    
    # Use circular region, not bounds
    region = region.simplify(50)
    
    # Connected components at coarser scale for speed
    cc_scale = max(scale * 2, 200)  # At least 200m for CC
    
    veg_cc = veg_mask.selfMask().reproject(crs='EPSG:3857', scale=cc_scale).connectedComponents(
        connectedness=ee.Kernel.plus(1),
        maxSize=64  # Reduced for speed
    )
    
    built_cc = built_mask.selfMask().reproject(crs='EPSG:3857', scale=cc_scale).connectedComponents(
        connectedness=ee.Kernel.plus(1),
        maxSize=64
    )
    
    # Fast edge detection (3x3 kernel instead of large morphology)
    built_edge = built_mask.focal_max(1).neq(built_mask.focal_min(1)).selfMask()
    edge_count = reduce_region(built_edge, ee.Reducer.count(), region, scale)
    
    # Distance calculation with reduced search radius
    # Calculate distance TO vegetation (pass vegetation mask to fastDistanceTransform)
    # This calculates distance from every pixel to nearest vegetation pixel
    veg_distance = veg_mask.fastDistanceTransform(
        neighborhood=int(3000 / scale),  # Convert 3km to pixels
        units='pixels',
        metric='squared_euclidean'
    ).sqrt().multiply(scale)  # Convert back to meters
    
    # For built-up areas specifically: distance from built pixels to nearest vegetation  
    built_distance = veg_distance.updateMask(built_mask)
    
    # Overall vegetation accessibility: distance from ALL pixels to nearest vegetation
    # But only where there's no vegetation (mask out vegetation pixels themselves)
    veg_accessibility_distance = veg_distance.updateMask(veg_mask.Not())
    
    # Sample-based percentiles for speed
    built_sample = built_distance.rename('distance').sample(
        region=region,
        scale=scale,
        numPixels=20000,
        geometries=False,
        tileScale=4
    )
    
    # Basic stats without percentiles first
    built_stats = built_distance.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            ee.Reducer.stdDev(),
            sharedInputs=True
        ).combine(
            ee.Reducer.min(),
            sharedInputs=True
        ).combine(
            ee.Reducer.max(),
            sharedInputs=True
        ),
        geometry=region,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
        tileScale=4
    )
    
    # Overall vegetation accessibility
    veg_access_stats = veg_accessibility_distance.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            ee.Reducer.stdDev(),
            sharedInputs=True
        ),
        geometry=region,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
        tileScale=4
    )
    
    # Get patch counts from histograms
    veg_hist = reduce_region(
        veg_cc.select('labels'),
        ee.Reducer.frequencyHistogram(),
        region,
        cc_scale
    )
    
    built_hist = reduce_region(
        built_cc.select('labels'),
        ee.Reducer.frequencyHistogram(),
        region,
        cc_scale
    )
    
    # Compute areas server-side
    region_area = region.area(maxError=100)
    
    # Create a single server-side dictionary with all results
    return ee.Dictionary({
        'veg_patch_histogram': veg_hist,
        'built_patch_histogram': built_hist,
        'edge_pixel_count': edge_count,
        'built_distance_stats': built_stats,
        'built_distance_sample': built_sample,
        'veg_access_stats': veg_access_stats,
        'region_area_m2': region_area,
        'cc_scale': cc_scale,
        'analysis_scale': scale
    })


def analyze_city_year(city: str, year: int, scale: int) -> Dict[str, Any]:
    """Analyze spatial relationships for a city in a specific year - OPTIMIZED."""
    city_info = UZBEKISTAN_CITIES[city]
    center = ee.Geometry.Point([city_info['lon'], city_info['lat']])
    # Don't use bounds() - keep it circular
    region = center.buffer(city_info['buffer_m'])

    out: Dict[str, Any] = {'city': city, 'year': year, 'scale': scale}

    # Load classifications
    classifications = load_all_classifications(
        year, region, f"{year}-01-01", f"{year}-12-31",
        optimal_scales={'scale': max(200, scale)}
    )
    esri_full = classifications.get('esri_full')
    esri_built = classifications.get('esri_built')
    
    if esri_full is None:
        out['error'] = 'ESRI LULC not available'
        return out

    # Create masks with reprojection
    veg_mask = _make_veg_mask(esri_full, region, scale)
    built_mask = _make_built_mask(esri_full, esri_built, region, scale)
    
    try:
        # Compute all metrics server-side
        metrics = _batch_compute_metrics(veg_mask, built_mask, region, scale)
        
        # Single getInfo() call for all metrics
        results = metrics.getInfo()
        
        # Process vegetation patches
        veg_hist = results.get('veg_patch_histogram', {})
        if veg_hist:
            vals = {}
            try:
                first = next(iter(veg_hist.values()))
                for k, v in first.items():
                    vals[int(k)] = int(v)
            except:
                vals = {}
            
            cc_scale = results.get('cc_scale', scale)
            pixel_area_m2 = cc_scale * cc_scale
            areas = [count * pixel_area_m2 for count in vals.values()]
            
            patch_count = len(areas)
            out['veg_patches'] = {
                'patch_count': patch_count,
                'mean_patch_area_m2': sum(areas) / patch_count if patch_count > 0 else 0,
                'max_patch_area_m2': max(areas) if areas else 0,
                'min_patch_area_m2': min(areas) if areas else 0,
                'total_area_m2': sum(areas)
            }
        
        # Process built patches similarly
        built_hist = results.get('built_patch_histogram', {})
        if built_hist:
            vals = {}
            try:
                first = next(iter(built_hist.values()))
                for k, v in first.items():
                    vals[int(k)] = int(v)
            except:
                vals = {}
            
            cc_scale = results.get('cc_scale', scale)
            pixel_area_m2 = cc_scale * cc_scale
            areas = [count * pixel_area_m2 for count in vals.values()]
            
            patch_count = len(areas)
            out['built_patches'] = {
                'patch_count': patch_count,
                'mean_patch_area_m2': sum(areas) / patch_count if patch_count > 0 else 0,
                'max_patch_area_m2': max(areas) if areas else 0,
                'min_patch_area_m2': min(areas) if areas else 0,
                'total_area_m2': sum(areas)
            }
        
        # Built distance stats
        bd_stats = results.get('built_distance_stats', {})
        if bd_stats:
            out['built_distance_stats'] = {
                'city': {
                    'mean': bd_stats.get('distance_mean', 0),
                    'stdDev': bd_stats.get('distance_stdDev', 0),
                    'min': bd_stats.get('distance_min', 0),
                    'max': bd_stats.get('distance_max', 0)
                }
            }
            
            # Get percentiles from sample if available
            sample = results.get('built_distance_sample')
            if sample and sample.get('features'):
                # Compute percentiles client-side from sample
                distances = [f['properties'].get('distance', 0) for f in sample['features']]
                if distances:
                    distances.sort()
                    n = len(distances)
                    out['built_distance_stats']['city']['percentiles'] = {
                        'p25': distances[int(n * 0.25)],
                        'p50': distances[int(n * 0.50)],
                        'p75': distances[int(n * 0.75)],
                        'p90': distances[int(n * 0.90)],
                        'p95': distances[int(n * 0.95)]
                    }
        
        # Vegetation accessibility
        va_stats = results.get('veg_access_stats', {})
        if va_stats:
            out['vegetation_accessibility'] = {
                'city': {
                    'mean': va_stats.get('distance_mean', 0),
                    'stdDev': va_stats.get('distance_stdDev', 0)
                }
            }
        
        # Edge density
        edge_count = results.get('edge_pixel_count', {})
        region_area_m2 = results.get('region_area_m2', 0)
        
        if edge_count and region_area_m2 > 0:
            edge_pixels = next(iter(edge_count.values())) if edge_count else 0
            edge_length_m = edge_pixels * scale
            area_km2 = region_area_m2 / 1e6
            out['edge_density_m_per_km2'] = edge_length_m / area_km2 if area_km2 > 0 else 0
            out['edge_metrics'] = {
                'edge_pixels': edge_pixels,
                'edge_length_m': edge_length_m,
                'region_area_km2': area_km2
            }
        
        # Skip patch isolation (vectorization is too expensive)
        out['veg_patch_isolation_note'] = 'Skipped for performance'
        
    except Exception as e:
        out['error'] = str(e)
    
    return out


def run_for_cities(cities: Optional[List[str]] = None, years: Optional[List[int]] = None, scale: Optional[int] = None) -> Dict[str, Any]:
    """Run spatial relationship analysis for multiple cities and years - OPTIMIZED."""
    if cities is None:
        cities = list(UZBEKISTAN_CITIES.keys())
    if years is None:
        years = [2016, 2024]  # Reduced default for development
    if scale is None:
        scale = ANALYSIS_CONFIG.get('target_resolution_m', 100)
    
    # Ensure scale is an int and reasonable
    scale = max(10, min(int(scale), 1000))  # Clamp between 10m and 1000m

    reports: Dict[str, Any] = {}
    total_analyses = len(cities) * len(years)
    completed = 0
    
    print(f"\n🚀 Running optimized spatial analysis for {len(cities)} cities × {len(years)} years = {total_analyses} analyses")
    print(f"   Scale: {scale}m")
    print(f"   Cities: {', '.join(cities[:5])}" + (f"... and {len(cities)-5} more" if len(cities) > 5 else ""))
    print(f"   Years: {years}")
    
    for city in cities:
        reports[city] = {}
        for y in years:
            try:
                print(f"\n   Processing {city} {y}...", end='', flush=True)
                start_time = time.time()
                
                reports[city][str(y)] = analyze_city_year(city, y, scale)
                
                elapsed = time.time() - start_time
                completed += 1
                remaining = total_analyses - completed
                eta = (elapsed * remaining) / 60 if completed > 0 else 0
                
                print(f" ✓ ({elapsed:.1f}s) [{completed}/{total_analyses}] ETA: {eta:.1f} min")
                
            except Exception as e:
                print(f" ✗ Error: {str(e)[:50]}")
                reports[city][str(y)] = {'error': str(e)}

    # Temporal summary between first and last year
    temporal_summary: Dict[str, Any] = {}
    if len(years) > 1:
        start_year = min(years)
        end_year = max(years)
        
        print(f"\n📊 Computing temporal changes ({start_year} → {end_year})...")
        
        for city in cities:
            cs = reports.get(city, {})
            start = cs.get(str(start_year), {})
            end = cs.get(str(end_year), {})
            changes: Dict[str, Any] = {}
            
            try:
                # Helper function to calculate change
                def calc_change(start_val, end_val, key_name):
                    if start_val is not None and end_val is not None and start_val != 0:
                        changes[f'{key_name}_change'] = end_val - start_val
                        changes[f'{key_name}_pct'] = ((end_val - start_val) / abs(start_val) * 100)
                
                # Vegetation patches
                sc = start.get('veg_patches', {}).get('patch_count')
                ec = end.get('veg_patches', {}).get('patch_count')
                calc_change(sc, ec, 'veg_patch_count')
                
                s_ma = start.get('veg_patches', {}).get('mean_patch_area_m2')
                e_ma = end.get('veg_patches', {}).get('mean_patch_area_m2')
                calc_change(s_ma, e_ma, 'veg_mean_patch_area_m2')
                
                # Built distance
                s_bd = start.get('built_distance_stats', {}).get('city', {}).get('mean')
                e_bd = end.get('built_distance_stats', {}).get('city', {}).get('mean')
                calc_change(s_bd, e_bd, 'built_mean_distance_m')
                
                # Vegetation accessibility
                s_va = start.get('vegetation_accessibility', {}).get('city', {}).get('mean')
                e_va = end.get('vegetation_accessibility', {}).get('city', {}).get('mean')
                calc_change(s_va, e_va, 'veg_access_mean_m')
                
                # Edge density
                s_ed = start.get('edge_density_m_per_km2')
                e_ed = end.get('edge_density_m_per_km2')
                calc_change(s_ed, e_ed, 'edge_density_m_per_km2')
                
            except Exception as e:
                changes['error'] = str(e)
                
            temporal_summary[city] = changes

    print("\n✅ Analysis complete!")
    
    return {
        'per_year': reports,
        'temporal_changes': temporal_summary,
        'analysis_period': f"{min(years)}-{max(years)}" if years else "N/A"
    }
