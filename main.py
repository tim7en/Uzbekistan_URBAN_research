"""Orchestrator entrypoint for SUHI analysis (minimal).

Delegates all heavy work to the refactored `services` package. This file
is intentionally tiny so it's easy to run a quick smoke test or use as the
CI entrypoint.
"""

from services import gee, utils, pipeline, visualization, analyzer
from pathlib import Path


def main() -> None:
    print("COMPREHENSIVE SUHI ANALYSIS ORCHESTRATOR (minimal)")

    if not gee.initialize_gee():
        print("GEE initialization failed. Exiting.")
        return

    gee.test_dataset_availability()
    utils.create_output_directories()

    cities = list(utils.UZBEKISTAN_CITIES.keys())
    if not cities:
        print("No cities configured in services.utils.UZBEKISTAN_CITIES")
        return

    # Create output directories
    output_dir = Path("outputs")
    visualization_dir = output_dir / "visualizations"
    reports_dir = output_dir / "reports"
    
    output_dir.mkdir(exist_ok=True)
    visualization_dir.mkdir(exist_ok=True)
    reports_dir.mkdir(exist_ok=True)

    # Run comprehensive analysis for multiple cities and years
    print(f"\n🔍 Running analysis for {len(cities)} cities...")
    
    all_results = []
    for city in cities[:3]:  # Limit to first 3 cities for demo
        for year in [2017, 2024]:
            print(f"\n📊 Analyzing {city} for {year}...")
            
            results = pipeline.run_comprehensive_analysis(city, year)
            if results and 'error' not in results:
                all_results.append(results)
                
                # Create individual visualizations
                if 'day_night_analysis' in results:
                    visualization.create_day_night_comparison_plot(
                        results['day_night_analysis'], city, year, visualization_dir
                    )
    
    # Create multi-city comparisons
    if all_results:
        print("\n📈 Creating comparative visualizations...")
        visualization.create_multi_city_landcover_comparison(all_results, visualization_dir)
        visualization.create_statistical_summary_plot(
            {f"{r['city']}_{r['year']}": r for r in all_results}, 
            visualization_dir
        )
    
    # Run comprehensive statistical analysis
    if output_dir.exists():
        print("\n📊 Running comprehensive statistical analysis...")
        data_analyzer = analyzer.SUHIAnalyzer(str(output_dir))
        if data_analyzer.load_data():
            data_analyzer.calculate_comparative_statistics()
            data_analyzer.create_comprehensive_report()
            data_analyzer.export_summary_statistics(reports_dir)

    print(f"\n✅ Analysis complete! Check outputs in:")
    print(f"   📊 Visualizations: {visualization_dir}")
    print(f"   📋 Reports: {reports_dir}")
    print(f"   📁 Raw data: {output_dir}")


if __name__ == '__main__':
    main()
