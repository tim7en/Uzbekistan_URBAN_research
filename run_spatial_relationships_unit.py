"""Unit test: spatial relationships between vegetation patches and built-up areas.

Produces per-city JSON reports with:
- distance-to-vegetation map stats for built-up pixels
- vegetation accessibility index (mean distance, population-weighted optional)
- edge density and fragmentation metrics (edge length per area, mean patch size)
- patch isolation (mean nearest-neighbor distance between vegetation patches)

This script runs independently and writes outputs to `suhi_analysis_output/reports/`.
"""
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure repository root is on sys.path so local `services` package is importable
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from services.utils import create_output_directories, UZBEKISTAN_CITIES, ANALYSIS_CONFIG
from services.gee import initialize_gee
from services.spatial_relationships import run_for_cities


def main(cities: Optional[List[str]] = None, years: Optional[List[int]] = None, scale: Optional[int] = None):
    start_time = time.time()
    
    print("🚀 Starting Optimized Spatial Relationships Analysis")
    print("=" * 50)
    
    # Initialize GEE
    print("🔑 Initializing Google Earth Engine...")
    gee_start = time.time()
    ok = initialize_gee()
    if not ok:
        print('❌ GEE init failed; aborting spatial relationships unit')
        return
    gee_time = time.time() - gee_start
    print(f"   ✅ GEE initialized in {gee_time:.2f} seconds")

    # Setup parameters
    if cities is None:
        cities = list(UZBEKISTAN_CITIES.keys())
    if years is None:
        years = [2016, 2024]  # Just start and end year for faster analysis
    if scale is None:
        scale = ANALYSIS_CONFIG.get('target_resolution_m', 100)
    
    print(f"\n📊 Analysis Configuration:")
    print(f"   🏙️  Cities: {len(cities)} ({', '.join(cities[:5])}" + (f"... and {len(cities)-5} more" if len(cities) > 5 else "") + ")")
    print(f"   📅 Years: {years}")
    print(f"   📏 Scale: {scale}m")
    print(f"   🎯 Total combinations: {len(cities) * len(years)}")
    print("\n   🚀 Using OPTIMIZED algorithms:")
    print("      ✓ Circular regions (not bounds)")
    print("      ✓ TileScale=4 for all reductions")
    print("      ✓ Reduced distance search to 3km")
    print("      ✓ Sample-based percentiles")
    print("      ✓ Single getInfo() per city-year")
    print("      ✓ Skipped vectorization")
    print()

    dirs = create_output_directories()
    
    # Create dedicated spatial relationships analysis folder
    spatial_output_dir = Path(__file__).parent / 'suhi_analysis_output' / 'spatial_relationship_analysis'
    spatial_output_dir.mkdir(exist_ok=True)
    print(f"📁 Created output directory: {spatial_output_dir}")
    
    # Run the analysis with progress tracking
    print("\n🔄 Running spatial relationships analysis...")
    analysis_start = time.time()
    
    result = run_for_cities(cities=cities, years=years, scale=scale)
    
    analysis_time = time.time() - analysis_start
    print(f"\n✅ Analysis completed in {analysis_time:.2f} seconds ({analysis_time/60:.1f} minutes)")
    print(f"   ⚡ Average per city-year: {analysis_time/(len(cities)*len(years)):.1f} seconds")
    
    # Save the comprehensive report
    print("\n💾 Saving results...")
    save_start = time.time()
    
    comprehensive_report_file = Path(__file__).parent / 'suhi_analysis_output' / 'reports' / 'spatial_relationships_report.json'
    with open(comprehensive_report_file, 'w', encoding='utf-8') as fh:
        json.dump(result, fh, indent=2)
    print(f"   📄 Comprehensive report: {comprehensive_report_file}")
    
    # Save individual city data files
    per_year_data = result.get('per_year', {})
    successful_analyses = 0
    failed_analyses = 0
    
    for i, (city, city_data) in enumerate(per_year_data.items(), 1):
        city_file = spatial_output_dir / f"{city.lower()}_spatial_relationships.json"
        
        # Count successful vs failed analyses for this city
        city_successful = sum(1 for year_data in city_data.values() if 'error' not in year_data)
        city_failed = len(city_data) - city_successful
        successful_analyses += city_successful
        failed_analyses += city_failed
        
        # Save city-specific data
        with open(city_file, 'w', encoding='utf-8') as fh:
            json.dump({
                'city': city,
                'years_analyzed': list(city_data.keys()),
                'data': city_data,
                'temporal_changes': result.get('temporal_changes', {}).get(city, {})
            }, fh, indent=2)
        
        status = "✓" if city_failed == 0 else "⚠" if city_successful > 0 else "✗"
        print(f"   {status} {city}: {city_file.name} ({city_successful}/{len(city_data)} years)")
    
    save_time = time.time() - save_start
    print(f"\n✅ Files saved in {save_time:.2f} seconds")
    
    # Summary statistics
    total_time = time.time() - start_time
    print("\n" + "=" * 50)
    print("📊 SUMMARY:")
    print(f"   ✅ Successful analyses: {successful_analyses}/{successful_analyses + failed_analyses}")
    print(f"   ❌ Failed analyses: {failed_analyses}")
    print(f"   ⏱️  Total runtime: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
    print(f"   🚀 Performance: {total_time/(successful_analyses + failed_analyses):.1f} sec/analysis")
    print(f"   📁 Output directory: {spatial_output_dir}")
    print("=" * 50)


if __name__ == '__main__':
    # Run comprehensive analysis for all Uzbekistan cities (14 total) from 2017-2024
    print("🌍 Running spatial relationships analysis for ALL cities (2017-2024)")
    print(f"   Cities: {len(UZBEKISTAN_CITIES)} total")
    print(f"   Years: 8 years (2017-2024)")
    print(f"   Total analyses: {len(UZBEKISTAN_CITIES) * 8} = 112 city-year combinations")
    print()
    
    main(cities=list(UZBEKISTAN_CITIES.keys()), years=list(range(2017, 2025)))
