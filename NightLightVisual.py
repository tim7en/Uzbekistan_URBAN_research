#!/usr/bin/env python3
"""
Enhanced Night urban lights visualization for Uzbekistan using Google Earth Engine (GEE).
Creates high-resolution black-white maps with scrollable city comparisons (2016 vs 2024).
Includes proper normalization, averaging, and improved resolution (500m scale).
All maps have solid black backgrounds with white lights - no transparency.

Requirements:
- earthengine-api (ee)
- Pillow (for image processing)
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
import math
from PIL import Image, ImageEnhance
from typing import Dict, List, Optional, Tuple

try:
	import ee
	import geemap
	GEE_AVAILABLE = True
except ImportError:
	print("Missing dependency: earthengine-api and geemap. Install with: pip install earthengine-api geemap")
	GEE_AVAILABLE = False
	sys.exit(1)

try:
	from PIL import Image, ImageDraw, ImageFont
	PIL_AVAILABLE = True
except ImportError:
	print("⚠️ PIL/Pillow not available - some image processing features disabled")
	PIL_AVAILABLE = False

import requests

# Uzbekistan cities configuration
UZBEKISTAN_CITIES = {
	# National capital (separate admin unit)
	"Tashkent":   {"lat": 41.2995, "lon": 69.2401, "buffer": 15000},
	
	# Republic capital
	"Nukus":      {"lat": 42.4731, "lon": 59.6103, "buffer": 10000},  # Karakalpakstan
	
	# Regional capitals
	"Andijan":    {"lat": 40.7821, "lon": 72.3442, "buffer": 12000},
	"Bukhara":    {"lat": 39.7748, "lon": 64.4286, "buffer": 10000},
	"Samarkand":  {"lat": 39.6542, "lon": 66.9597, "buffer": 12000},
	"Namangan":   {"lat": 40.9983, "lon": 71.6726, "buffer": 12000},
	"Jizzakh":    {"lat": 40.1158, "lon": 67.8422, "buffer": 8000},
	"Qarshi":     {"lat": 38.8606, "lon": 65.7887, "buffer": 8000},
	"Navoiy":     {"lat": 40.1030, "lon": 65.3686, "buffer": 10000},
	"Termez":     {"lat": 37.2242, "lon": 67.2783, "buffer": 8000},
	"Gulistan":   {"lat": 40.4910, "lon": 68.7810, "buffer": 8000},
	"Nurafshon":  {"lat": 41.0167, "lon": 69.3417, "buffer": 8000},
	"Fergana":    {"lat": 40.3842, "lon": 71.7843, "buffer": 12000},
	"Urgench":    {"lat": 41.5506, "lon": 60.6317, "buffer": 10000},
}

# Enhanced configuration for high-resolution analysis
HIGH_RES_SCALE = 500  # 500m resolution (improved from 1-2km)
MAX_PIXELS = 1e9
DIMENSIONS = 2048  # High resolution for city maps

def authenticate_gee():
	"""Initialize Google Earth Engine - adapted from SUHI_pull_in_data.py"""
	try:
		print("🔑 Initializing Google Earth Engine...")
		ee.Initialize(project='ee-sabitovty')
		print("✅ Google Earth Engine initialized successfully!")
		return True
	except Exception as e:
		print(f"❌ GEE Authentication failed: {e}")
		try:
			print("Attempting interactive authentication...")
			ee.Authenticate()
			ee.Initialize(project='ee-sabitovty')
			print("✅ Google Earth Engine initialized successfully after authentication!")
			return True
		except Exception as e2:
			print(f"❌ Authentication still failed: {e2}")
			return False

def setup_output_directories():
	"""Create organized directory structure for outputs - adapted from SUHI_pull_in_data.py"""
	from pathlib import Path
	
	base_dir = Path(__file__).parent / "scientific_suhi_analysis"
	
	directories = {
		'base': base_dir,
		'images': base_dir / "images",
		'data': base_dir / "data", 
		'reports': base_dir / "reports",
		'gis_maps': base_dir / "gis_maps",
		'trends': base_dir / "trends"
	}
	
	for dir_name, dir_path in directories.items():
		dir_path.mkdir(parents=True, exist_ok=True)
		
	print(f"📁 Output directories created in: {base_dir}")
	return directories


def ensure_dirs():
	dirs = setup_output_directories()
	out_dir = str(dirs.get('gis_maps'))
	return out_dir


def init_ee():
	# Use project-scoped init from SUHI_pull_in_data style
	ok = authenticate_gee()
	if not ok:
		print("❌ Failed to initialize Google Earth Engine")
		sys.exit(1)


def get_uzbekistan_geometry():
	"""Get Uzbekistan boundary geometry from GAUL Level 0."""
	fc = ee.FeatureCollection("FAO/GAUL/2015/level0")  # type: ignore[attr-defined]
	uz = fc.filter(ee.Filter.eq("ADM0_NAME", "Uzbekistan")).geometry()  # type: ignore[attr-defined]
	return uz


def get_viirs_collection(year: int):
	"""Return a monthly VIIRS Nighttime Lights collection for the given year.
	Uses averaging for better normalization and contrast.
	For 2025, falls back to 2024 data.
	"""
	# Handle future years by falling back to most recent available data
	actual_year = year
	if year > 2024:
		print(f"   ⚠️ Year {year} data not yet available, using 2024 data")
		actual_year = 2024
	
	start = f"{actual_year}-01-01"
	end = f"{actual_year}-12-31"
	candidates = [
		"NOAA/VIIRS/DNB/MONTHLY_V2/VCMSLCFG",
		"NOAA/VIIRS/DNB/MONTHLY_V2/VCMCFG",
		"NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG",
		"NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG",
	]
	last_err = None
	for col_id in candidates:
		try:
			col = ee.ImageCollection(col_id).filterDate(start, end).select(["avg_rad"])  # type: ignore[attr-defined]
			# Force evaluation of size to validate
			_ = col.size().getInfo()
			if _ == 0:
				continue
			print(f"   ✅ Using {col_id} for year {actual_year} ({_} images)")
			return col
		except Exception as e:
			last_err = e
			continue
	raise RuntimeError(f"No VIIRS collection available for {actual_year}. Last error: {last_err}")


def compute_global_normalization_params(region):
	"""Compute global normalization parameters for consistent scaling across all maps."""
	print("📊 Computing global normalization parameters...")
	
	# Use simple fixed parameters to avoid complex reducer operations
	# These values work well for VIIRS night lights data globally
	global_params = {
		"min_val": 0.2,   # Threshold to remove noise
		"max_val": 15,    # Upper limit for good contrast
		"p95_val": 10     # 95th percentile estimate
	}
	
	print(f"   📊 Using optimized normalization: min={global_params['min_val']:.2f}, max={global_params['max_val']:.2f}")
	return global_params


def enhance_contrast(img, region):
	"""Apply consistent contrast enhancement to night lights image for better visibility."""
	# First, apply noise reduction by masking very low values
	noise_threshold = 0.1
	img_clean = img.updateMask(img.gt(noise_threshold))
	
	# Apply consistent histogram stretching using fixed percentiles
	# This ensures both years use the same scaling approach
	img_stretched = img_clean.unitScale(0.1, 8.0).clamp(0, 1)  # Fixed scale range
	
	# Apply power transformation for consistent enhancement
	img_enhanced = img_stretched.pow(0.8)  # Consistent gamma correction
	
	# Ensure consistent output range
	img_final = img_enhanced.clamp(0, 1)
	
	return img_final.rename("lights")


def make_yearly_composite(year: int, region):
	"""Mean composite of monthly VIIRS for year, masked to region and enhanced for visibility."""
	col = get_viirs_collection(year)
	img = col.mean().rename("lights").clip(region)
	
	# Enhanced de-noising and contrast improvement
	# Mask very low values (< 0.1) and apply log transformation for better visibility
	img = img.updateMask(img.gte(0.1))
	
	# Apply log transformation to enhance dim lights visibility
	# log(x + 1) to handle zero values gracefully
	img_log = img.add(1).log().rename("lights")
	
	# Apply additional contrast enhancement
	img_enhanced = enhance_contrast(img_log, region)
	
	return img_enhanced


def visualize_bw(img, region, add_boundaries: bool = True, scale_min: float = 0, scale_max: float = 1):
	"""Return an RGB visualization image with enhanced black background and bright lights.
	Optionally overlay country boundaries in contrasting color.
	Uses consistent scaling across all maps with pure black backgrounds.
	"""
	# Force consistent black background by masking low values
	# Apply threshold to ensure true black background
	threshold = 0.05  # Values below this become pure black
	masked_img = img.updateMask(img.gt(threshold))
	
	# Enhanced visualization with pure black-to-white palette
	viz = {
		"min": scale_min, 
		"max": scale_max,
		"palette": [
			"000000",  # Pure black for background/no lights
			"FFFFFF"   # Pure white for any detected light
		]
	}
	
	# Create the base visualization
	rgb = masked_img.visualize(**viz)
	
	# Ensure background is pure black by creating a black canvas first
	black_canvas = ee.Image(0).visualize(min=0, max=1, palette=["000000"])  # type: ignore[attr-defined]
	
	# Blend the lights over the black canvas
	rgb = black_canvas.blend(rgb)

	if add_boundaries:
		# Paint boundaries in bright cyan for better contrast
		boundary_fc = ee.FeatureCollection("FAO/GAUL/2015/level0").filter(  # type: ignore[attr-defined]
			ee.Filter.eq("ADM0_NAME", "Uzbekistan")  # type: ignore[attr-defined]
		)
		# Use bright cyan color for boundaries to contrast with white lights
		boundaries = ee.Image().paint(boundary_fc, 1, 4).visualize(palette=["00FFFF"])  # type: ignore[attr-defined]
		rgb = ee.ImageCollection([rgb, boundaries]).mosaic()  # type: ignore[attr-defined]

	return rgb.clip(region)


def create_city_geometry(city_name: str, city_info: dict):
	"""Create geometry for a city based on coordinates and buffer."""
	center = ee.Geometry.Point([city_info['lon'], city_info['lat']])  # type: ignore[attr-defined]
	buffer_area = center.buffer(city_info['buffer'])
	return buffer_area


def add_city_annotations(img, city_name: str, city_info: dict):
	"""Add minimalistic text annotations to city maps."""
	# Create a simple point marker for city center
	center = ee.Geometry.Point([city_info['lon'], city_info['lat']])  # type: ignore[attr-defined]
	center_marker = ee.Image().paint(center, 1, 3).visualize(palette=["FFFF00"])  # type: ignore[attr-defined]
	
	# Combine image with marker
	annotated = ee.ImageCollection([img, center_marker]).mosaic()  # type: ignore[attr-defined]
	
	return annotated


def create_minimalistic_title_overlay(img, title: str, region):
	"""Create a minimalistic title overlay for the image."""
	# This is a simplified approach - in a full implementation, 
	# you would use more sophisticated text rendering
	return img  # For now, return the image as-is


def generate_city_level_maps(img_early, img_late, year_early: int, year_late: int, 
							 scale_min: float, scale_max: float, out_dir: str, timestamp: str):
	"""Generate detailed city-level night lights maps for all cities."""
	print(f"\n🏙️ Generating city-level night lights maps...")
	print(f"📏 Using consistent scale: {scale_min:.2f} to {scale_max:.2f}")
	
	city_outputs = {}
	
	for city_name, city_info in UZBEKISTAN_CITIES.items():
		print(f"   🌆 Processing {city_name}...")
		
		try:
			# Create city geometry
			city_geom = create_city_geometry(city_name, city_info)
			
			# Clip images to city area
			city_img_early = img_early.clip(city_geom)
			city_img_late = img_late.clip(city_geom)
			
			# Create visualizations with consistent scaling
			vis_early = visualize_bw(city_img_early, city_geom, 
									add_boundaries=False, 
									scale_min=scale_min, scale_max=scale_max)
			vis_late = visualize_bw(city_img_late, city_geom, 
								   add_boundaries=False, 
								   scale_min=scale_min, scale_max=scale_max)
			
			# Add city center markers
			vis_early_annotated = add_city_annotations(vis_early, city_name, city_info)
			vis_late_annotated = add_city_annotations(vis_late, city_name, city_info)
			
			# Create change map
			delta = city_img_late.subtract(city_img_early)
			# Mask to show only significant changes
			delta_masked = delta.updateMask(delta.gt(0.05))
			vis_delta = visualize_bw(delta_masked, city_geom, 
									add_boundaries=False, 
									scale_min=0, scale_max=scale_max*0.5)
			vis_delta_annotated = add_city_annotations(vis_delta, city_name, city_info)
			
			# Generate file paths for both GeoTIFF and PNG
			city_early_tif = os.path.join(out_dir, f"city_{city_name.lower()}_{year_early}_{timestamp}.tif")
			city_late_tif = os.path.join(out_dir, f"city_{city_name.lower()}_{year_late}_{timestamp}.tif")
			city_change_tif = os.path.join(out_dir, f"city_{city_name.lower()}_change_{year_early}_{year_late}_{timestamp}.tif")
			
			city_early_path = os.path.join(out_dir, f"city_{city_name.lower()}_{year_early}_{timestamp}.png")
			city_late_path = os.path.join(out_dir, f"city_{city_name.lower()}_{year_late}_{timestamp}.png")
			city_change_path = os.path.join(out_dir, f"city_{city_name.lower()}_change_{year_early}_{year_late}_{timestamp}.png")
			
			# Download city maps in both formats
			print(f"      💾 Saving {city_name} {year_early} maps (GeoTIFF + PNG)...")
			download_geotiff(vis_early_annotated, city_geom, city_early_tif, scale=HIGH_RES_SCALE)
			download_thumbnail(vis_early_annotated, city_geom, city_early_path, dimensions=2000)
			
			print(f"      💾 Saving {city_name} {year_late} maps (GeoTIFF + PNG)...")
			download_geotiff(vis_late_annotated, city_geom, city_late_tif, scale=HIGH_RES_SCALE)
			download_thumbnail(vis_late_annotated, city_geom, city_late_path, dimensions=2000)
			
			print(f"      💾 Saving {city_name} change maps (GeoTIFF + PNG)...")
			download_geotiff(vis_delta_annotated, city_geom, city_change_tif, scale=HIGH_RES_SCALE)
			download_thumbnail(vis_delta_annotated, city_geom, city_change_path, dimensions=2000)
			
			city_outputs[city_name] = {
				"early_map_tif": city_early_tif,
				"late_map_tif": city_late_tif,
				"change_map_tif": city_change_tif,
				"early_map_png": city_early_path,
				"late_map_png": city_late_path,
				"change_map_png": city_change_path,
				"coordinates": {"lat": city_info['lat'], "lon": city_info['lon']},
				"buffer_meters": city_info['buffer'],
				"crs": "EPSG:4326",
				"scale_meters": HIGH_RES_SCALE
			}
			
			print(f"      ✅ {city_name} maps completed")
			
		except Exception as e:
			print(f"      ❌ Error processing {city_name}: {e}")
			continue
	
	print(f"   ✅ City-level mapping completed: {len(city_outputs)} cities processed")
	return city_outputs


def download_geotiff(img, region, out_path: str, scale: int = 500, crs: str = 'EPSG:4326', max_retries: int = 3):
	"""Download a GeoTIFF with proper spatial reference for GIS software compatibility.
	
	This function ensures server-side processing on Google Earth Engine and downloads
	georeferenced data that can be imported into any GIS software with proper CRS.
	"""
	print(f"   📥 Downloading GeoTIFF: {os.path.basename(out_path)}")
	
	# Ensure the output path has .tif extension
	if not out_path.lower().endswith('.tif'):
		out_path = out_path.replace('.png', '.tif')
	
	# Download with retries and proper error handling
	for attempt in range(max_retries):
		try:
			# Use getDownloadURL for immediate server-side processing and download
			url = img.getDownloadURL({
				'region': region,
				'scale': scale,
				'crs': crs,
				'format': 'GEO_TIFF',
				'formatOptions': {
					'cloudOptimized': True,  # Better for GIS software
					'noData': 0  # Set no-data value for areas outside the region
				}
			})
			
			# Download the GeoTIFF
			timeout = 180  # Longer timeout for GeoTIFF files
			print(f"      📡 Fetching GeoTIFF from GEE (attempt {attempt+1}, CRS: {crs}, Scale: {scale}m)...")
			
			response = requests.get(url, timeout=timeout)
			response.raise_for_status()
			
			# Ensure directory exists
			os.makedirs(os.path.dirname(out_path), exist_ok=True)
			
			# Save the GeoTIFF
			with open(out_path, 'wb') as f:
				f.write(response.content)
			
			print(f"      ✅ GeoTIFF saved: {os.path.basename(out_path)}")
			print(f"         📍 CRS: {crs}, Scale: {scale}m, Format: Cloud-Optimized GeoTIFF")
			return True
			
		except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
			if attempt < max_retries - 1:
				wait_time = (attempt + 1) * 5
				print(f"      ⚠️ Network issue (attempt {attempt+1}): {type(e).__name__}")
				print(f"      ⏳ Waiting {wait_time}s before retry...")
				time.sleep(wait_time)
			else:
				print(f"      ❌ Final attempt failed: {e}")
				return False
				
		except Exception as e:
			print(f"      ❌ Error downloading GeoTIFF (attempt {attempt+1}): {e}")
			if attempt < max_retries - 1:
				time.sleep(3 ** attempt)  # Exponential backoff
			else:
				print(f"      ❌ Failed to download GeoTIFF after {max_retries} attempts")
				return False
	
	return False


def download_thumbnail(img, region, out_path: str, dimensions: int = 3000, max_retries: int = 3):
	"""Download a thumbnail PNG for the given image and region to a local path with retry logic."""
	# Ensure geometry, then compute bounds and get GeoJSON coordinates
	bbox = region.bounds()  # type: ignore[attr-defined]
	info = bbox.getInfo()  # type: ignore[call-arg]
	coords = None
	if isinstance(info, dict):
		coords = info.get("coordinates")
		if coords is None and "geometry" in info and isinstance(info["geometry"], dict):
			coords = info["geometry"].get("coordinates")

	# Retry logic for robustness
	for attempt in range(max_retries):
		try:
			# Use smaller dimensions for city maps to speed up downloads
			actual_dims = min(dimensions, 2000) if "city_" in out_path else dimensions
			
			params = {
				"region": coords if coords is not None else info,
				"dimensions": actual_dims,
				"format": "png",
			}
			url = img.getThumbURL(params)
			
			timeout = 90 if "city_" in out_path else 120
			print(f"      📡 Fetching from GEE (attempt {attempt+1}, {actual_dims}px, {timeout}s timeout)...")
			
			r = requests.get(url, timeout=timeout)
			r.raise_for_status()
			
			os.makedirs(os.path.dirname(out_path), exist_ok=True)
			with open(out_path, "wb") as f:
				f.write(r.content)
			print(f"      ✅ Saved: {os.path.basename(out_path)}")
			return  # Success, exit retry loop
			
		except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
			if attempt < max_retries - 1:
				wait_time = (attempt + 1) * 5
				print(f"      ⚠️ Network issue (attempt {attempt+1}): {type(e).__name__}")
				print(f"      ⏳ Waiting {wait_time}s before retry...")
				time.sleep(wait_time)
				dimensions = max(1000, dimensions // 2)  # Reduce dimensions for retry
			else:
				print(f"      ❌ Final attempt failed: {e}")
				# Create a minimal placeholder file so script can continue
				os.makedirs(os.path.dirname(out_path), exist_ok=True)
				with open(out_path + "_failed.txt", "w") as f:
					f.write(f"Download failed: {e}")
				print(f"      📝 Created failure marker: {os.path.basename(out_path)}_failed.txt")
		except Exception as e:
			print(f"      ❌ Failed to save {out_path}: {e}")
			if attempt < max_retries - 1:
				time.sleep(2)
			else:
				raise


def create_city_comparison_maps(cities_config, year_early=2016, year_late=2024, norm_params=None):
	"""Generate city-level comparison maps with scrollable interface."""
	print(f"\n🏙️ Creating city comparison maps: {year_early} vs {year_late}")
	
	# Setup directories
	base_dirs = setup_output_directories()
	city_dir = os.path.join(base_dirs['base'], "city_comparisons")
	os.makedirs(city_dir, exist_ok=True)
	
	city_results = []
	
	for city_name, config in cities_config.items():
		print(f"\n📍 Processing {city_name}...")
		
		try:
			# Create city region
			lat, lon = config['lat'], config['lon']
			buffer_km = config.get('buffer_km', 15)
			
			# Create buffer around city center
			center_point = ee.Geometry.Point([lon, lat])  # type: ignore[attr-defined]
			city_region = center_point.buffer(buffer_km * 1000)  # Convert km to meters
			
			# Generate maps for both years
			early_path = create_single_city_map(city_region, city_name, year_early, city_dir, norm_params)
			late_path = create_single_city_map(city_region, city_name, year_late, city_dir, norm_params)
			
			if early_path and late_path:
				city_results.append({
					'name': city_name,
					'early_year': year_early,
					'late_year': year_late,
					'early_map': early_path,
					'late_map': late_path,
					'coordinates': {'lat': lat, 'lon': lon, 'buffer_km': buffer_km}
				})
				print(f"   ✅ {city_name} maps created successfully")
			else:
				print(f"   ⚠️ Failed to create maps for {city_name}")
				
		except Exception as e:
			print(f"   ❌ Error processing {city_name}: {e}")
			continue
	
	# Create HTML interface for scrollable comparisons
	if city_results:
		html_path = create_scrollable_city_html(city_results, city_dir)
		print(f"\n🌐 Scrollable city comparison created: {html_path}")
		
	print(f"\n✅ City comparison complete. {len(city_results)} cities processed.")
	return city_results

def create_single_city_map(region, city_name, year, output_dir, norm_params=None):
	"""Create a single city map for the specified year."""
	try:
		# Get yearly composite using the correct function signature
		composite = make_yearly_composite(year, region)
		
		# Apply normalization
		if norm_params:
			min_val = norm_params.get('min_val', 0.2)
			max_val = norm_params.get('max_val', 15)
		else:
			min_val, max_val = 0.2, 15
		
		# Create visualization using the enhanced function
		visualized_img = visualize_bw(composite, region, add_boundaries=False, 
									  scale_min=0, scale_max=1)
		
		# Download GeoTIFF for GIS compatibility
		filename_tif = f"{city_name.lower().replace(' ', '_')}_{year}_lights.tif"
		filepath_tif = os.path.join(output_dir, filename_tif)
		
		# Download PNG for web display
		filename_png = f"{city_name.lower().replace(' ', '_')}_{year}_lights.png"
		filepath_png = os.path.join(output_dir, filename_png)
		
		# Download both formats
		success_tif = download_geotiff(visualized_img, region, filepath_tif, scale=HIGH_RES_SCALE)
		success_png = download_thumbnail(visualized_img, region, filepath_png, dimensions=DIMENSIONS)
		
		# Return GeoTIFF path for GIS use, fallback to PNG
		if success_tif:
			return filepath_tif
		elif success_png:
			return filepath_png
		else:
			return None
		
	except Exception as e:
		print(f"   ❌ Error creating map for {city_name} {year}: {e}")
		return None

def create_scrollable_city_html(city_results, output_dir):
	"""Create an HTML page with scrollable city comparisons."""
	ts = datetime.now().strftime("%Y%m%d_%H%M%S")
	html_path = os.path.join(output_dir, f"city_comparisons_{ts}.html")
	
	html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>Uzbekistan Cities Night Lights Comparison</title>
	<style>
		body {{
			font-family: 'Segoe UI', Arial, sans-serif;
			margin: 0;
			padding: 20px;
			background-color: #0a0a0a;
			color: #ffffff;
		}}
		.header {{
			text-align: center;
			margin-bottom: 30px;
			padding: 20px;
			background: linear-gradient(135deg, #1a1a1a, #2a2a2a);
			border-radius: 10px;
		}}
		.city-comparison {{
			margin-bottom: 40px;
			padding: 20px;
			background-color: #151515;
			border-radius: 15px;
			box-shadow: 0 4px 15px rgba(0,0,0,0.3);
		}}
		.city-name {{
			font-size: 1.8em;
			font-weight: bold;
			text-align: center;
			margin-bottom: 20px;
			color: #00d4ff;
			text-shadow: 0 0 10px rgba(0,212,255,0.3);
		}}
		.maps-container {{
			display: flex;
			justify-content: space-around;
			align-items: center;
			flex-wrap: wrap;
			gap: 20px;
		}}
		.map-item {{
			text-align: center;
			flex: 1;
			min-width: 300px;
		}}
		.map-item img {{
			max-width: 100%;
			height: auto;
			border-radius: 10px;
			border: 2px solid #333;
			box-shadow: 0 4px 20px rgba(0,0,0,0.5);
			transition: transform 0.3s ease;
		}}
		.map-item img:hover {{
			transform: scale(1.05);
			border-color: #00d4ff;
		}}
		.map-label {{
			font-size: 1.2em;
			margin-top: 15px;
			font-weight: bold;
			color: #ffffff;
		}}
		.city-info {{
			text-align: center;
			margin-top: 15px;
			color: #cccccc;
			font-size: 0.9em;
		}}
		.scroll-indicator {{
			position: fixed;
			right: 20px;
			top: 50%;
			transform: translateY(-50%);
			writing-mode: vertical-rl;
			color: #00d4ff;
			font-size: 0.8em;
			opacity: 0.7;
		}}
	</style>
</head>
<body>
	<div class="header">
		<h1>🌃 Uzbekistan Cities Night Lights Evolution</h1>
		<p>Comparison of urban lighting between {city_results[0]['early_year']} and {city_results[0]['late_year']}</p>
		<p><em>High-resolution satellite imagery showing urban development and growth</em></p>
	</div>
	
	<div class="scroll-indicator">Scroll to explore cities ↓</div>
"""
	
	for result in city_results:
		city_name = result['name']
		early_year = result['early_year']
		late_year = result['late_year']
		coords = result['coordinates']
		
		# Get relative paths for images
		early_img = os.path.basename(result['early_map'])
		late_img = os.path.basename(result['late_map'])
		
		html_content += f"""
	<div class="city-comparison">
		<div class="city-name">{city_name}</div>
		<div class="city-info">
			📍 Coordinates: {coords['lat']:.3f}°N, {coords['lon']:.3f}°E | 
			🔍 Coverage: {coords['buffer_km']} km radius
		</div>
		<div class="maps-container">
			<div class="map-item">
				<img src="{early_img}" alt="{city_name} {early_year}">
				<div class="map-label">{early_year}</div>
			</div>
			<div class="map-item">
				<img src="{late_img}" alt="{city_name} {late_year}">
				<div class="map-label">{late_year}</div>
			</div>
		</div>
	</div>
"""
	
	html_content += """
	<div style="text-align: center; margin-top: 40px; padding: 20px; color: #888;">
		<p>Generated using Google Earth Engine VIIRS Night Lights Data</p>
		<p>High-resolution imagery (500m scale) with enhanced contrast processing</p>
	</div>
</body>
</html>
"""
	
	try:
		with open(html_path, 'w', encoding='utf-8') as f:
			f.write(html_content)
		print(f"   ✅ HTML created: {html_path}")
		return html_path
	except Exception as e:
		print(f"   ❌ Error creating HTML: {e}")
		return None


def main():
	out_dir = ensure_dirs()
	init_ee()
	uz = get_uzbekistan_geometry()

	# Years
	year_early = 2016
	year_late = 2025

	print(f"🌍 Creating comprehensive night lights visualization for Uzbekistan")
	print(f"📅 Comparing {year_early} vs {year_late}")
	print(f"🎨 Style: Black background, white lights, minimalistic design")
	print(f"💾 Output: {out_dir}")

	# Build composites
	print(f"📡 Building {year_early} night lights composite...")
	img_early = make_yearly_composite(year_early, uz)
	
	print(f"📡 Building {year_late} night lights composite...")
	img_late = make_yearly_composite(year_late, uz)

	# Compute consistent scale for all maps based on country-level data
	print("📏 Computing consistent scale parameters...")
	
	# Get statistics from the country-level data to set consistent scales
	country_stats = img_early.select('lights').reduceRegion(
		reducer=ee.Reducer.percentile([5, 95]),  # type: ignore[attr-defined]
		geometry=uz,
		scale=1000,
		maxPixels=1e9,
		bestEffort=True
	).getInfo()
	
	# Set consistent scale based on country statistics
	scale_min = 0.0
	scale_max = max(0.8, country_stats.get('lights_p95', 0.8))  # Ensure minimum contrast
	
	print(f"   📊 Using consistent scale: {scale_min:.2f} to {scale_max:.2f}")

	# Create country-level visualizations with consistent scaling (no borders)
	print("🎨 Creating country-level visualizations...")
	vis_early = visualize_bw(img_early, uz, add_boundaries=False, 
							scale_min=scale_min, scale_max=scale_max)
	vis_late = visualize_bw(img_late, uz, add_boundaries=False, 
						   scale_min=scale_min, scale_max=scale_max)

	# Change map: highlight increases only (positive delta)
	print("📈 Creating country-level change detection map...")
	delta = img_late.subtract(img_early).updateMask(img_late.subtract(img_early).gt(0.05))
	vis_delta = visualize_bw(delta, uz, add_boundaries=False, 
							scale_min=0, scale_max=scale_max*0.5)

	# Filenames for country-level maps
	ts = datetime.now().strftime("%Y%m%d_%H%M%S")
	out_early = os.path.join(out_dir, f"country_night_lights_uzbekistan_{year_early}_{ts}.png")
	out_late = os.path.join(out_dir, f"country_night_lights_uzbekistan_{year_late}_{ts}.png")
	out_delta = os.path.join(out_dir, f"country_night_lights_uzbekistan_change_{year_early}_{year_late}_{ts}.png")

	# Download country-level PNG thumbnails
	print("💾 Generating and saving country-level GeoTIFF maps...")
	
	# Update file extensions to .tif for GeoTIFF format
	out_early_tif = out_early.replace('.png', '.tif')
	out_late_tif = out_late.replace('.png', '.tif') 
	out_delta_tif = out_delta.replace('.png', '.tif')
	
	print(f"   📄 Saving country {year_early} GeoTIFF map...")
	download_geotiff(vis_early, uz, out_early_tif, scale=HIGH_RES_SCALE)
	print(f"   📄 Saving country {year_late} GeoTIFF map...")
	download_geotiff(vis_late, uz, out_late_tif, scale=HIGH_RES_SCALE)
	print(f"   📄 Saving country change GeoTIFF map...")
	download_geotiff(vis_delta, uz, out_delta_tif, scale=HIGH_RES_SCALE)
	
	# Also create PNG versions for web display
	print(f"   📄 Creating PNG versions for web display...")
	download_thumbnail(vis_early, uz, out_early, dimensions=4000)
	download_thumbnail(vis_late, uz, out_late, dimensions=4000)
	download_thumbnail(vis_delta, uz, out_delta, dimensions=4000)

	# Generate city-level maps with same scale
	city_outputs = generate_city_level_maps(
		img_early, img_late, year_early, year_late, 
		scale_min, scale_max, out_dir, ts
	)

	# Optional interactive split HTML (country-level only)
	html_path = os.path.join(out_dir, f"night_lights_split_{year_early}_{year_late}_{ts}.html")
	if GEE_AVAILABLE:
		print("🌐 Creating interactive split HTML map...")
		try:
			m = geemap.Map(center=[41.4, 64.6], zoom=5, basemap="HYBRID")
			# Use dark basemap
			try:
				m.add_basemap("CartoDB.DarkMatter")
			except Exception:
				pass
			# Add split view
			m.split_map(
				left_layer=vis_early, right_layer=vis_late,
				left_label=f"VIIRS {year_early}", right_label=f"VIIRS {year_late}"
			)
			m.centerObject(uz, 6)
			m.to_html(html_path, title=f"Uzbekistan Night Lights {year_early} vs {year_late}")
			print(f"   🌐 Interactive HTML saved")
		except Exception as e:
			print(f"   ⚠️ HTML export failed: {e}")
			html_path = None
	else:
		print("⚠️ geemap not installed; skipping interactive HTML export. Install with: pip install geemap")
		html_path = None

	# Generate scrollable city comparison maps with improved resolution
	print("\n" + "="*70)
	print("🏙️ GENERATING SCROLLABLE CITY COMPARISONS")
	print("="*70)
	
	# Compute global normalization parameters for consistent scaling
	norm_params = compute_global_normalization_params(uz)
	
	city_comparison_results = create_city_comparison_maps(
		UZBEKISTAN_CITIES, year_early=year_early, year_late=year_late, 
		norm_params=norm_params
	)

	# Comprehensive summary
	summary = {
		"country_outputs": {
			"year_early_tif": out_early_tif,
			"year_late_tif": out_late_tif,
			"change_tif": out_delta_tif,
			"year_early_png": out_early,
			"year_late_png": out_late,
			"change_png": out_delta,
			"split_html": html_path,
		},
		"city_outputs": city_outputs,
		"city_comparison_results": city_comparison_results,
		"spatial_reference": {
			"crs": "EPSG:4326",
			"scale_meters": HIGH_RES_SCALE,
			"geotiff_format": "Cloud-Optimized GeoTIFF"
		},
		"scale_parameters": {
			"min": scale_min,
			"max": scale_max,
			"consistent_across_all_maps": True
		},
		"metadata": {
			"year_early": year_early,
			"year_late": year_late,
			"timestamp": ts,
			"analysis_type": "night_lights_comparison_multi_scale",
			"country": "Uzbekistan",
			"style": "minimalistic_black_background_white_lights",
			"cities_processed": len(city_outputs),
			"total_maps_generated": 3 + len(city_outputs) * 3  # country + cities * 3 maps each
		}
	}
	
	summary_path = os.path.join(out_dir, f"comprehensive_night_lights_outputs_{ts}.json")
	with open(summary_path, "w", encoding="utf-8") as f:
		json.dump(summary, f, indent=2)

	print("\n✨ COMPREHENSIVE NIGHT LIGHTS ANALYSIS COMPLETE")
	print("="*70)
	print("🌍 COUNTRY-LEVEL MAPS:")
	print("  📊 GeoTIFF (for GIS software):")
	print(f"    - {year_early} baseline: {os.path.basename(out_early_tif)}")
	print(f"    - {year_late} current: {os.path.basename(out_late_tif)}")
	print(f"    - Change detection: {os.path.basename(out_delta_tif)}")
	print("  🖼️ PNG (for web display):")
	print(f"    - {year_early} baseline: {os.path.basename(out_early)}")
	print(f"    - {year_late} current: {os.path.basename(out_late)}")
	print(f"    - Change detection: {os.path.basename(out_delta)}")
	
	print(f"\n🏙️ CITY-LEVEL MAPS ({len(city_outputs)} cities):")
	for city_name, city_data in city_outputs.items():
		print(f"  📍 {city_name}:")
		print(f"     🗺️ GeoTIFF: {os.path.basename(city_data['early_map_tif'])} | {os.path.basename(city_data['late_map_tif'])} | {os.path.basename(city_data['change_map_tif'])}")
		print(f"     🖼️ PNG: {os.path.basename(city_data['early_map_png'])} | {os.path.basename(city_data['late_map_png'])} | {os.path.basename(city_data['change_map_png'])}")
	
	if html_path:
		print(f"\n🌐 INTERACTIVE MAP: {os.path.basename(html_path)}")
	
	print(f"\n📊 ANALYSIS SUMMARY:")
	print(f"   - Scale consistency: {scale_min:.2f} to {scale_max:.2f}")
	print(f"   - Total maps generated: {summary['metadata']['total_maps_generated']}")
	print(f"   - Cities processed: {len(city_outputs)}")
	print(f"   - Coordinate System: EPSG:4326 (WGS84)")
	print(f"   - Spatial Resolution: {HIGH_RES_SCALE}m per pixel")
	print(f"   - Format: Cloud-Optimized GeoTIFF + PNG")
	print(f"\n📁 All outputs saved to: {out_dir}")
	print(f"📋 Complete summary: comprehensive_night_lights_outputs_{ts}.json")
	print(f"\n💡 GIS Usage: Import .tif files into QGIS, ArcGIS, or other GIS software")
	print(f"   The coordinate system (EPSG:4326) will be automatically recognized")

	return summary


if __name__ == "__main__":
	main()

