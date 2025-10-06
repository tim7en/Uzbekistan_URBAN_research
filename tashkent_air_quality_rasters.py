"""Tashkent PM2.5 Raster Extraction and Visualization Script.

This script extracts monthly average raster data for PM2.5 pollutant
specifically for Tashkent city using CAMS Global Atmospheric Composition data. It creates:
- 12 GeoTIFF raster files for PM2.5 monthly averages
- A visualization showing 2024 trends for PM2.5

Data is extracted using Google Earth Engine with existing authentication routines.
"""
import sys
from pathlib import Path
import argparse
import json
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Ensure repository root is on sys.path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import ee
from services.gee import initialize_gee
from services.air_quality import AirQualityAnalyzer
from services.utils import UZBEKISTAN_CITIES, create_output_directories


def extract_monthly_rasters(city_name: str, year: int, pollutants: list = None) -> dict:
    """Extract monthly raster composites for specified pollutants.

    Args:
        city_name: Name of the city (must be in UZBEKISTAN_CITIES)
        year: Year to extract data for
        pollutants: List of pollutants to extract (default: ['PM25'])

    Returns:
        Dictionary containing extraction results and file paths
    """
    if pollutants is None:
        pollutants = ['PM25']

    analyzer = AirQualityAnalyzer()

    # Get city geometry
    geometries = analyzer.get_city_geometry(city_name)
    geometry = geometries['combined']  # Use combined urban + rural area

    results = {
        'city': city_name,
        'year': year,
        'extraction_timestamp': datetime.now().isoformat(),
        'rasters': {},
        'metadata': {}
    }

    # Create output directory for rasters
    output_base = Path('tashkent_air_quality_rasters')
    output_base.mkdir(parents=True, exist_ok=True)

    for pollutant in pollutants:
        print(f"📊 Extracting {pollutant} monthly rasters for {city_name} {year}...")

        pollutant_results = {
            'monthly_files': [],
            'extraction_status': 'success',
            'error_details': None
        }

        try:
            # Get pollutant configuration
            config = analyzer.pollutants[pollutant]
            dataset = analyzer.pollutants[pollutant]['dataset']

            monthly_files = []

            # Extract each month
            for month in range(1, 13):
                month_str = f"{month:02d}"
                month_name = datetime(year, month, 1).strftime('%B')

                print(f"   Processing {pollutant} for {month_name} {year}...")

                # Define date range for the month
                start_date = f"{year}-{month:02d}-01"
                if month == 12:
                    end_date = f"{year+1}-01-01"
                else:
                    end_date = f"{year}-{month+1:02d}-01"

                try:
                    # Get Sentinel-5P data for this month
                    collection = analyzer.get_sentinel5p_data(
                        pollutant, start_date, end_date, geometry
                    )

                    # Create monthly composite (mean)
                    if collection.size().getInfo() > 0:
                        monthly_composite = analyzer.calculate_monthly_composite(
                            collection, geometry, 'mean'
                        )

                        # Select the specific band
                        monthly_image = monthly_composite.select(config['band'])

                        # Define output filename
                        filename = f"{city_name.lower()}_{pollutant.lower()}_{year}_{month_str}_{month_name.lower()}.tif"
                        output_path = output_base / filename

                        # Export as GeoTIFF
                        task = ee.batch.Export.image.toDrive(
                            image=monthly_image,
                            description=f"{city_name}_{pollutant}_{year}_{month_str}",
                            folder="tashkent_air_quality_rasters",
                            fileNamePrefix=f"{city_name.lower()}_{pollutant.lower()}_{year}_{month_str}",
                            region=geometry,
                            scale=10000 if pollutant == 'PM25' else 7500,  # CAMS PM2.5 resolution vs Sentinel-5P
                            crs="EPSG:4326",
                            maxPixels=1e9
                        )

                        # Start the export task
                        task.start()

                        file_info = {
                            'month': month,
                            'month_name': month_name,
                            'filename': filename,
                            'local_path': str(output_path),
                            'gee_task_id': task.id,
                            'status': 'export_started',
                            'data_points': collection.size().getInfo()
                        }

                        monthly_files.append(file_info)
                        print(f"     ✅ Export started: {filename}")

                    else:
                        # No data for this month
                        file_info = {
                            'month': month,
                            'month_name': month_name,
                            'filename': None,
                            'status': 'no_data',
                            'data_points': 0
                        }
                        monthly_files.append(file_info)
                        print(f"     ⚠️ No {pollutant} data available for {month_name} {year}")

                except Exception as e:
                    print(f"     ❌ Error processing {pollutant} for {month_name} {year}: {e}")
                    file_info = {
                        'month': month,
                        'month_name': month_name,
                        'filename': None,
                        'status': 'error',
                        'error': str(e)
                    }
                    monthly_files.append(file_info)

            pollutant_results['monthly_files'] = monthly_files

        except Exception as e:
            print(f"❌ Error extracting {pollutant} rasters: {e}")
            pollutant_results['extraction_status'] = 'failed'
            pollutant_results['error_details'] = str(e)

        results['rasters'][pollutant] = pollutant_results

    # Save metadata
    metadata_file = output_base / f"{city_name.lower()}_air_quality_rasters_{year}_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    results['metadata']['metadata_file'] = str(metadata_file)

    return results


def create_pm25_trends_visualization(city_name: str, year: int = 2025) -> dict:
    """Create visualization showing PM2.5 trends for the specified year.

    Args:
        city_name: Name of the city
        year: Year to visualize (default: 2024)

    Returns:
        Dictionary with visualization results
    """
    print(f"📈 Creating PM2.5 trends visualization for {city_name} {year}...")

    analyzer = AirQualityAnalyzer()

    # Get city geometry
    geometries = analyzer.get_city_geometry(city_name)
    geometry = geometries['urban']  # Focus on urban area for trends

    # Collect monthly data for PM2.5
    monthly_data = {}
    pollutant = 'PM25'
    
    print(f"   Collecting {pollutant} data for {year}...")
    monthly_values = []
    months = []

    for month in range(1, 13):
        month_name = datetime(year, month, 1).strftime('%b')

        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1}-01-01"
        else:
            end_date = f"{year}-{month+1:02d}-01"

        try:
            # Get data for this month
            collection = analyzer.get_sentinel5p_data(pollutant, start_date, end_date, geometry)

            if collection.size().getInfo() > 0:
                # Calculate monthly mean
                monthly_composite = analyzer.calculate_monthly_composite(collection, geometry, 'mean')
                config = analyzer.pollutants[pollutant]

                # Extract mean value
                stats = analyzer.extract_pollutant_stats(
                    monthly_composite, geometry, config['band'], scale=10000  # CAMS resolution
                )

                if 'mean' in stats and stats['mean'] is not None:
                    # Convert to appropriate units
                    mean_value = stats['mean']
                    if config['factor'] != 1:
                        mean_value *= config['factor']

                    monthly_values.append(mean_value)
                    months.append(month_name)
                    print(f"     {month_name}: {mean_value:.2e} {config['display_units']}")
                else:
                    monthly_values.append(None)
                    months.append(month_name)
                    print(f"     {month_name}: No data")
            else:
                monthly_values.append(None)
                months.append(month_name)
                print(f"     {month_name}: No data")

        except Exception as e:
            print(f"     Error getting {pollutant} data for {month_name}: {e}")
            monthly_values.append(None)
            months.append(month_name)

    monthly_data[pollutant] = {
        'months': months,
        'values': monthly_values
    }

    # Create visualization
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    fig.suptitle(f'{city_name} PM2.5 Trends - {year}', fontsize=16, fontweight='bold')

    # PM2.5 plot
    pm25_data = monthly_data['PM25']
    valid_pm25 = [(m, v) for m, v in zip(pm25_data['months'], pm25_data['values']) if v is not None]

    if valid_pm25:
        months_pm25, values_pm25 = zip(*valid_pm25)
        ax.plot(months_pm25, values_pm25, 'go-', linewidth=2, markersize=8, label='PM₂.₅')
        ax.fill_between(months_pm25, values_pm25, alpha=0.3, color='green')
        ax.set_ylabel('PM₂.₅ (µg/m³)', fontsize=12)
        ax.set_title('Particulate Matter (PM₂.₅) Monthly Averages', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend()

        # Add value labels
        for i, v in enumerate(values_pm25):
            ax.annotate(f'{v:.2e}', (months_pm25[i], v),
                        xytext=(0, 10), textcoords='offset points',
                        ha='center', fontsize=9)
    else:
        ax.text(0.5, 0.5, 'No PM₂.₅ data available', transform=ax.transAxes,
                ha='center', va='center', fontsize=14)
        ax.set_title('Particulate Matter (PM₂.₅) Monthly Averages - No Data', fontsize=14)

    plt.tight_layout()

    # Save the plot
    output_dir = Path('tashkent_air_quality_rasters')
    output_dir.mkdir(parents=True, exist_ok=True)

    plot_filename = f"{city_name.lower()}_pm25_trends_{year}.png"
    plot_path = output_dir / plot_filename

    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"   ✅ PM2.5 trends visualization saved: {plot_path}")

    # Save data as CSV for further analysis
    csv_data = []
    for i, month in enumerate(pm25_data['months']):
        row = {
            'Month': month,
            'PM25_Value': pm25_data['values'][i]
        }
        csv_data.append(row)

    csv_filename = f"{city_name.lower()}_pm25_trends_{year}.csv"
    csv_path = output_dir / csv_filename

    df = pd.DataFrame(csv_data)
    df.to_csv(csv_path, index=False)

    print(f"   ✅ PM2.5 trends data saved: {csv_path}")

    return {
        'plot_file': str(plot_path),
        'data_file': str(csv_path),
        'monthly_data': monthly_data,
        'data_points_pm25': len(valid_pm25)
    }


def main():
    parser = argparse.ArgumentParser(description='Extract Tashkent air quality rasters and create visualizations')
    parser.add_argument('--year', type=int, default=2024, help='Year to extract data for (default: 2024)')
    parser.add_argument('--pollutants', nargs='*', choices=['NO2', 'SO2', 'PM25'],
                       default=['PM25'], help='Pollutants to extract (default: PM25)')
    parser.add_argument('--extract-rasters', action='store_true',
                       help='Extract monthly raster files')
    parser.add_argument('--create-visualization', action='store_true',
                       help='Create trends visualization')
    parser.add_argument('--all', action='store_true',
                       help='Extract rasters and create visualization (default if no action specified)')

    args = parser.parse_args()

    # Default to doing everything if no specific action requested
    if not (args.extract_rasters or args.create_visualization):
        args.all = True

    # Initialize Google Earth Engine
    print("🔑 Initializing Google Earth Engine...")
    ok = initialize_gee()
    if not ok:
        print("❌ GEE initialization failed. Please resolve authentication issues.")
        return 1

    city_name = "Tashkent"
    year = args.year

    print("🏙️ Tashkent PM2.5 Data Extraction")
    print("=" * 50)
    print(f"   City: {city_name}")
    print(f"   Year: {year}")
    print(f"   Pollutants: {', '.join(args.pollutants)}")
    print()

    results = {
        'city': city_name,
        'year': year,
        'extraction_timestamp': datetime.now().isoformat(),
        'raster_extraction': None,
        'visualization': None
    }

    # Extract rasters if requested
    if args.extract_rasters or args.all:
        print("📊 Starting raster extraction...")
        raster_results = extract_monthly_rasters(city_name, year, args.pollutants)
        results['raster_extraction'] = raster_results

        # Summary of raster extraction
        print("\n📊 Raster Extraction Summary:")
        for pollutant, data in raster_results['rasters'].items():
            successful_exports = sum(1 for f in data['monthly_files']
                                   if f.get('status') == 'export_started')
            total_months = len(data['monthly_files'])
            print(f"   {pollutant}: {successful_exports}/{total_months} months exported")

    # Create visualization if requested
    if args.create_visualization or args.all:
        print("\n📈 Creating PM2.5 trends visualization...")
        viz_results = create_pm25_trends_visualization(city_name, year)
        results['visualization'] = viz_results

        print("\n📈 Visualization Summary:")
        print(f"   Plot saved: {viz_results['plot_file']}")
        print(f"   Data saved: {viz_results['data_file']}")
        print(f"   PM2.5 data points: {viz_results['data_points_pm25']}")

    # Save overall results
    output_dir = Path('tashkent_air_quality_rasters')
    output_dir.mkdir(parents=True, exist_ok=True)

    results_file = output_dir / f"{city_name.lower()}_air_quality_extraction_{year}_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Complete results saved: {results_file}")

    print("\n🎯 Tashkent PM2.5 Extraction Complete!")
    print("=" * 50)
    print("Note: Raster exports to Google Drive may take several minutes to complete.")
    print("Check your Google Drive 'tashkent_air_quality_rasters' folder for the GeoTIFF files.")

    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)