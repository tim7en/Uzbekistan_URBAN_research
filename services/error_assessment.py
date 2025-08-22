"""Utilities to compute simple uncertainty/error assessments on Earth Engine rasters.

Provides server-side reducers (mean, stdDev, count) and derived statistics
like standard error and 95% confidence intervals. Designed to be robust to
collections/band name variations and to avoid client-side heavy downloads.
"""
from typing import Dict, Any
import ee


def _extract_scalar(info_dict):
    if not info_dict:
        return None
    try:
        k = list(info_dict.keys())[0]
        v = info_dict[k]
        if isinstance(v, dict):
            # try common nested keys
            for sub in ('mean', 'stdDev', 'stddev', 'count'):
                if sub in v and v[sub] is not None:
                    return v[sub]
            return None
        else:
            return v
    except Exception:
        return None


def compute_raster_zone_stats(image: ee.Image, geom: ee.Geometry, scale: int = 500, maxPixels: int = int(1e8)) -> Dict[str, Any]:
    """Compute mean, stdDev and count for the first band of `image` over `geom`.

    Returns a plain dict with float or None values for 'mean','stdDev','count',
    'stdError' and 'ci95' (tuple low, high) where computable.
    """
    out = {'mean': None, 'stdDev': None, 'count': None, 'stdError': None, 'ci95': (None, None)}
    try:
        # try to pick a band name
        try:
            band = image.bandNames().getInfo()[0]
        except Exception:
            band = None

        # reduceRegion separately for robustness
        mean_r = image.reduceRegion(reducer=ee.Reducer.mean(), geometry=geom, scale=scale, maxPixels=maxPixels, bestEffort=True)
        std_r = image.reduceRegion(reducer=ee.Reducer.stdDev(), geometry=geom, scale=scale, maxPixels=maxPixels, bestEffort=True)
        count_r = image.reduceRegion(reducer=ee.Reducer.count(), geometry=geom, scale=scale, maxPixels=maxPixels, bestEffort=True)

        mean_info = mean_r.getInfo() if mean_r else {}
        std_info = std_r.getInfo() if std_r else {}
        count_info = count_r.getInfo() if count_r else {}

        m = _extract_scalar(mean_info)
        s = _extract_scalar(std_info)
        c = _extract_scalar(count_info)

        if m is not None:
            out['mean'] = float(m)
        if s is not None:
            out['stdDev'] = float(s)
        if c is not None:
            try:
                out['count'] = int(c)
            except Exception:
                out['count'] = int(float(c))

        # derive standard error and 95% CI when possible
        if out['stdDev'] is not None and out['count'] and out['count'] > 0:
            se = out['stdDev'] / (out['count'] ** 0.5)
            out['stdError'] = float(se)
            lo = out['mean'] - 1.96 * se if out['mean'] is not None else None
            hi = out['mean'] + 1.96 * se if out['mean'] is not None else None
            out['ci95'] = (lo, hi)
    except Exception as e:
        out['error'] = str(e)
    return out


def compute_zonal_uncertainty(image: ee.Image, zones: Dict[str, ee.Geometry], scale: int = 500, maxPixels: int = int(1e8)) -> Dict[str, Any]:
    """Compute uncertainty metrics for a set of named zones.

    Returns dict keyed by zone name with stats produced by
    compute_raster_zone_stats.
    """
    res = {}
    for name, geom in zones.items():
        try:
            res[name] = compute_raster_zone_stats(image, geom, scale=scale, maxPixels=maxPixels)
        except Exception as e:
            res[name] = {'error': str(e)}
    return res


def compute_categorical_uncertainty(image: ee.Image, geom: ee.Geometry, scale: int = 200, maxPixels: int = int(1e8)) -> Dict[str, Any]:
    """Compute frequency histogram and class proportions for a categorical image.

    Returns a dict with 'histogram' (class->count), 'proportions', and 'entropy'
    (Shannon entropy in nats) as a simple uncertainty proxy.
    """
    out = {'histogram': None, 'proportions': None, 'entropy': None}
    try:
        # Try a normal reduceRegion call first.
        # If it fails with memory limits, retry with increasing tileScale.
        hist_info = {}
        try:
            hist_r = image.reduceRegion(reducer=ee.Reducer.frequencyHistogram(), geometry=geom, scale=scale, maxPixels=maxPixels, bestEffort=True)
            hist_info = hist_r.getInfo() if hist_r else {}
        except Exception as e:
            msg = str(e)
            # Retry with tileScale attempts to reduce memory pressure on the server
            for ts in (2, 4, 8, 16):
                try:
                    hist_r = image.reduceRegion(reducer=ee.Reducer.frequencyHistogram(), geometry=geom, scale=scale, maxPixels=maxPixels, bestEffort=True, tileScale=ts)
                    hist_info = hist_r.getInfo() if hist_r else {}
                    if hist_info:
                        break
                except Exception:
                    hist_info = {}
            if not hist_info:
                # re-raise original to be caught by outer handler
                raise

        # hist_info is expected to be a dict like { '<band>': { '<class>': count, ... } }
        hist = None
        if isinstance(hist_info, dict) and hist_info:
            # extract first value (the histogram dict) instead of using generic scalar extractor
            try:
                first_val = next(iter(hist_info.values()))
                if isinstance(first_val, dict):
                    hist = first_val
            except Exception:
                hist = None

        if isinstance(hist, dict):
            # convert keys to int where possible
            try:
                hist = {int(k): int(v) for k, v in hist.items()}
            except Exception:
                hist = {str(k): int(v) for k, v in hist.items()}
            out['histogram'] = hist
            total = sum(hist.values()) if hist else 0
            if total > 0:
                props = {k: v / total for k, v in hist.items()}
                out['proportions'] = props
                # Shannon entropy
                import math
                ent = -sum((p * math.log(p) for p in props.values() if p > 0))
                out['entropy'] = float(ent)
    except Exception as e:
        out['error'] = str(e)
    return out
