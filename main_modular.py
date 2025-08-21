"""
Main entry point for Uzbekistan Urban Research Analysis

This modular version replaces the monolithic main.py with a clean,
production-ready structure using services-based architecture.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Import services
from services.config import get_default_config, UZBEKISTAN_CITIES
from services.utils.gee_utils import initialize_gee, test_dataset_availability
from services.utils.output_utils import create_output_directories, save_analysis_metadata
from services.analysis.night_lights import run_comprehensive_night_lights_analysis
from services.analysis.suhi import run_comprehensive_suhi_analysis
from services.analysis.urban_expansion import run_comprehensive_urban_expansion_analysis
from services.visualization.generators import (
    create_suhi_analysis_visualization,
    create_night_lights_visualization, 
    create_urban_expansion_visualization,
    create_comprehensive_dashboard
)


def run_analysis(resolution_m: int = 500, testing_mode: bool = False, 
                test_cities_count: int = 3) -> Dict:
    """
    Run comprehensive urban research analysis
    
    Args:
        resolution_m: Spatial resolution in meters (default: 500m)
        testing_mode: If True, run on limited cities for testing
        test_cities_count: Number of cities to analyze in testing mode
        
    Returns:
        Dict with analysis results and metadata
    """
    
    print("="*80)
    print("UZBEKISTAN URBAN RESEARCH - COMPREHENSIVE ANALYSIS")
    print("="*80)
    print(f"Resolution: {resolution_m}m")
    print(f"Testing Mode: {testing_mode}")
    if testing_mode:
        print(f"Test Cities Count: {test_cities_count}")
    
    # Initialize configuration
    analysis_config, gee_config = get_default_config(
        resolution_m=resolution_m,
        testing_mode=testing_mode
    )
    analysis_config.test_cities_count = test_cities_count
    
    # Get cities to process
    cities_to_process = analysis_config.get_cities_to_process()
    
    print(f"\n📍 Cities to analyze: {len(cities_to_process)}")
    print(f"📅 Years to analyze: {analysis_config.years[0]}-{analysis_config.years[-1]}")
    for city in cities_to_process:
        print(f"   • {city}")
    
    # Initialize Google Earth Engine
    if not initialize_gee():
        print("\n❌ Cannot proceed without Google Earth Engine access")
        return {"error": "GEE initialization failed"}
    
    # Test dataset availability
    print("\n🔍 Testing dataset availability...")
    dataset_status = test_dataset_availability()
    
    # Create output directories
    print("\n📁 Setting up output directories...")
    output_dirs = create_output_directories("uzbekistan_urban_analysis_output")
    
    # Save analysis metadata
    metadata = {
        "analysis_type": "comprehensive_urban_research",
        "resolution_m": resolution_m,
        "testing_mode": testing_mode,
        "cities_analyzed": cities_to_process,
        "years_analyzed": analysis_config.years,
        "dataset_availability": dataset_status,
        "started_at": datetime.now().isoformat()
    }
    save_analysis_metadata(output_dirs['base'], metadata)
    
    # Store all results
    results = {
        "metadata": metadata,
        "night_lights": None,
        "suhi": None,
        "urban_expansion": None,
        "visualizations": []
    }
    
    # 1. NIGHT LIGHTS ANALYSIS (2017-2024)
    print("\n" + "="*60)
    print("🌙 PHASE 1: NIGHT LIGHTS ANALYSIS")
    print("="*60)
    
    try:
        night_lights_results = run_comprehensive_night_lights_analysis(
            cities=cities_to_process,
            year_early=2017,
            year_late=2024,
            output_dir=output_dirs['night_lights'],
            gee_config=gee_config
        )
        results["night_lights"] = night_lights_results
        
        # Create night lights visualization
        viz_file = create_night_lights_visualization(
            night_lights_results, 
            output_dirs['visualizations']
        )
        results["visualizations"].append(str(viz_file))
        
    except Exception as e:
        print(f"❌ Night lights analysis failed: {e}")
        results["night_lights"] = {"error": str(e)}
    
    # 2. SUHI ANALYSIS (2017-2024)
    print("\n" + "="*60)
    print("🔥 PHASE 2: SURFACE URBAN HEAT ISLAND ANALYSIS")
    print("="*60)
    
    try:
        suhi_results = run_comprehensive_suhi_analysis(
            cities=cities_to_process,
            years=analysis_config.years,
            output_dir=output_dirs['temperature'],
            gee_config=gee_config
        )
        results["suhi"] = suhi_results
        
        # Create SUHI visualization
        viz_file = create_suhi_analysis_visualization(
            suhi_results,
            output_dirs['visualizations']
        )
        results["visualizations"].append(str(viz_file))
        
    except Exception as e:
        print(f"❌ SUHI analysis failed: {e}")
        results["suhi"] = {"error": str(e)}
    
    # 3. URBAN EXPANSION ANALYSIS (2017-2024)
    print("\n" + "="*60)
    print("🏗️ PHASE 3: URBAN EXPANSION ANALYSIS")
    print("="*60)
    
    try:
        expansion_results = run_comprehensive_urban_expansion_analysis(
            cities=cities_to_process,
            year_start=2017,
            year_end=2024,
            output_dir=output_dirs['urban_expansion'],
            gee_config=gee_config
        )
        results["urban_expansion"] = expansion_results
        
        # Create urban expansion visualization
        viz_file = create_urban_expansion_visualization(
            expansion_results,
            output_dirs['visualizations']
        )
        results["visualizations"].append(str(viz_file))
        
    except Exception as e:
        print(f"❌ Urban expansion analysis failed: {e}")
        results["urban_expansion"] = {"error": str(e)}
    
    # 4. COMPREHENSIVE DASHBOARD
    print("\n" + "="*60)
    print("📊 PHASE 4: COMPREHENSIVE VISUALIZATION DASHBOARD")
    print("="*60)
    
    try:
        if all(results[key] and "error" not in results[key] 
               for key in ["night_lights", "suhi", "urban_expansion"]):
            
            dashboard_file = create_comprehensive_dashboard(
                suhi_data=results["suhi"],
                night_lights_data=results["night_lights"],
                expansion_data=results["urban_expansion"],
                output_dir=output_dirs['visualizations']
            )
            results["visualizations"].append(str(dashboard_file))
            
        else:
            print("⚠️ Comprehensive dashboard skipped due to analysis errors")
    
    except Exception as e:
        print(f"❌ Dashboard creation failed: {e}")
    
    # 5. FINAL SUMMARY
    print("\n" + "="*80)
    print("✅ ANALYSIS COMPLETE")
    print("="*80)
    
    metadata["completed_at"] = datetime.now().isoformat()
    results["metadata"] = metadata
    
    # Count successful analyses
    successful_analyses = sum(1 for key in ["night_lights", "suhi", "urban_expansion"] 
                            if results[key] and "error" not in results[key])
    
    print(f"📊 Successful analyses: {successful_analyses}/3")
    print(f"📁 Output directory: {output_dirs['base']}")
    print(f"🖼️ Visualizations created: {len(results['visualizations'])}")
    
    # Print raster file information
    raster_count = 0
    for analysis_type, data in results.items():
        if analysis_type in ["night_lights", "suhi", "urban_expansion"] and data and "error" not in data:
            if "cities_analysis" in data:
                for city_data in data["cities_analysis"]:
                    if "raster_exports" in city_data:
                        raster_count += len(city_data["raster_exports"])
            elif "cities" in data:
                for city_data in data["cities"]:
                    if "raster_exports" in city_data:
                        raster_count += len(city_data["raster_exports"])
    
    print(f"📄 Raster files exported: {raster_count}")
    print(f"🔬 Analysis resolution: {resolution_m}m")
    
    if testing_mode:
        print(f"🧪 Testing mode: {len(cities_to_process)} cities analyzed")
    else:
        print(f"🏙️ Production mode: All {len(cities_to_process)} cities analyzed")
    
    print("\nKey insights:")
    
    # SUHI insights
    if results["suhi"] and "error" not in results["suhi"]:
        suhi_stats = results["suhi"].get("summary_statistics", {})
        mean_suhi = suhi_stats.get("mean_suhi_all_cities", 0)
        max_suhi = suhi_stats.get("max_suhi_observed", 0)
        print(f"• Average SUHI across cities: {mean_suhi:.2f}°C")
        print(f"• Maximum SUHI observed: {max_suhi:.2f}°C")
    
    # Urban expansion insights
    if results["urban_expansion"] and "error" not in results["urban_expansion"]:
        expansion_stats = results["urban_expansion"].get("summary_statistics", {})
        total_expansion = expansion_stats.get("total_urban_expansion_km2", 0)
        print(f"• Total urban expansion: {total_expansion:.2f} km²")
    
    # Night lights insights
    if results["night_lights"] and "error" not in results["night_lights"]:
        cities_data = results["night_lights"].get("cities", [])
        if cities_data:
            increases = [c.get("change_percent", 0) for c in cities_data if "error" not in c and c.get("change_percent", 0) > 0]
            print(f"• Cities with night lights increase: {len(increases)}")
    
    return results


def main():
    """Main entry point with user-configurable parameters"""
    
    # Configuration options - easily modifiable
    RESOLUTION_M = 500  # Spatial resolution in meters
    TESTING_MODE = True  # Set to False for full analysis
    TEST_CITIES_COUNT = 3  # Number of cities for testing
    
    print("CONFIGURATION:")
    print(f"• Resolution: {RESOLUTION_M}m")
    print(f"• Testing Mode: {TESTING_MODE}")
    if TESTING_MODE:
        print(f"• Test Cities: {TEST_CITIES_COUNT}")
    
    # Run the analysis
    results = run_analysis(
        resolution_m=RESOLUTION_M,
        testing_mode=TESTING_MODE,
        test_cities_count=TEST_CITIES_COUNT
    )
    
    return results


if __name__ == "__main__":
    main()