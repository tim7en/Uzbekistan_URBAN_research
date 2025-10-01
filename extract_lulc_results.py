#!/usr/bin/env python3
"""
Extract LULC analysis results into a CSV table.

This script reads LULC analysis JSON files for all cities and extracts
land cover area data into a structured CSV format.
"""

import json
import csv
import os
from pathlib import Path
from typing import Dict, List, Any


def load_lulc_data(city: str, base_path: Path) -> Dict[str, Any] | None:
    """Load LULC analysis data for a specific city."""
    json_file = base_path / city / f"{city}_lulc_analysis_2016_2024.json"

    if not json_file.exists():
        print(f"Warning: LULC file not found for {city}: {json_file}")
        return None

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {json_file}: {e}")
        return None


def extract_city_data(city: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract area data for all years for a city."""
    if not data or 'areas_m2' not in data:
        return []

    rows = []
    land_cover_types = [
        'Water', 'Rangeland', 'Trees', 'Flooded_Vegetation',
        'Crops', 'Built_Area', 'Bare_Ground'
    ]

    for year in data.get('years', []):
        year_data = data['areas_m2'].get(str(year), {})

        row = {
            'City': city,
            'Year': year
        }

        for lc_type in land_cover_types:
            area_m2 = year_data.get(lc_type, {}).get('area_m2', 0)
            # Convert to square kilometers (1 km² = 1,000,000 m² = 100 ha)
            area_km2 = area_m2 / 1000000 if area_m2 else 0

            # Map to user-friendly column names
            column_name = {
                'Water': 'Water area (km²)',
                'Rangeland': 'Rangeland area (km²)',
                'Trees': 'Trees (km²)',
                'Flooded_Vegetation': 'Flooded vegetation (km²)',
                'Crops': 'Crops (km²)',
                'Built_Area': 'Built area (km²)',
                'Bare_Ground': 'Bare ground (km²)'
            }.get(lc_type, f'{lc_type} (km²)')

            row[column_name] = round(area_km2, 3)

        rows.append(row)

    return rows


def main():
    """Main function to extract LULC data into CSV."""
    # Define paths
    base_path = Path(__file__).parent / 'suhi_analysis_output' / 'lulc_analysis'
    output_file = Path(__file__).parent / 'lulc_analysis_summary.csv'

    # List of cities (from directory listing)
    cities = [
        'Andijan', 'Bukhara', 'Fergana', 'Gulistan', 'Jizzakh',
        'Namangan', 'Navoiy', 'Nukus', 'Nurafshon', 'Qarshi',
        'Samarkand', 'Tashkent', 'Termez', 'Urgench'
    ]

    all_rows = []

    print("Extracting LULC analysis data...")

    for city in cities:
        print(f"Processing {city}...")
        data = load_lulc_data(city, base_path)

        if data:
            city_rows = extract_city_data(city, data)
            all_rows.extend(city_rows)
            print(f"  - Extracted {len(city_rows)} year records")
        else:
            print(f"  - No data found")

    if not all_rows:
        print("No data found for any cities!")
        return

    # Sort by city, then year
    all_rows.sort(key=lambda x: (x['City'], x['Year']))

    # Write to CSV
    fieldnames = [
        'City', 'Year', 'Water area (km²)', 'Rangeland area (km²)', 'Trees (km²)',
        'Flooded vegetation (km²)', 'Crops (km²)', 'Built area (km²)', 'Bare ground (km²)'
    ]

    print(f"\nWriting {len(all_rows)} records to {output_file}...")

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print("Done!")
    print(f"Output file: {output_file}")

    # Print summary
    cities_with_data = set(row['City'] for row in all_rows)
    years_covered = sorted(set(row['Year'] for row in all_rows))

    print("\nSummary:")
    print(f"- Cities with data: {len(cities_with_data)}")
    print(f"- Years covered: {years_covered[0]} to {years_covered[-1]}")
    print(f"- Total records: {len(all_rows)}")


if __name__ == "__main__":
    main()