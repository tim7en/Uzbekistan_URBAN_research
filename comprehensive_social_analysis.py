import json
import pandas as pd
from pathlib import Path

def analyze_social_sector_comprehensive():
    """Comprehensive analysis of social sector data with district-level water patterns and per capita metrics."""

    cities = ['Tashkent', 'Nukus', 'Termez', 'Jizzakh']
    results = {}

    print("🔍 COMPREHENSIVE SOCIAL SECTOR ANALYSIS")
    print("=" * 60)

    for city in cities:
        file_path = Path(f'suhi_analysis_output/social_sector/{city}_social_sector.json')
        if not file_path.exists():
            print(f"⚠️  Data not found for {city}")
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        results[city] = data
        summary = data['summary']
        per_capita = summary['per_capita_metrics']

        print(f"\n🏙️  {city.upper()}")
        print("-" * 40)

        # Basic infrastructure counts
        print(f"📊 INFRASTRUCTURE COUNTS:")
        print(f"   Schools: {summary['total_schools']}")
        print(f"   Hospitals: {summary['total_hospitals']}")
        print(f"   Kindergardens: {summary['total_kindergardens']}")
        print(f"   Population: {per_capita['population']:,}")

        # Per capita metrics
        print(f"\n📈 PER CAPITA METRICS (per 1000 people):")
        print(f"   Schools: {per_capita['schools_per_1000']}")
        print(f"   Hospitals: {per_capita['hospitals_per_1000']}")
        print(f"   Kindergardens: {per_capita['kindergardens_per_1000']}")
        print(f"   Student Capacity: {per_capita['student_capacity_per_1000']}")
        print(f"   Enrolled Students: {per_capita['enrolled_students_per_1000']}")

        # Water vulnerability
        water_sources = summary['sanitation_indicators']['water_sources']
        vuln_index = per_capita['water_vulnerability_index']
        print(f"\n💧 WATER VULNERABILITY:")
        print(f"   Centralized: {water_sources['centralized']}%")
        print(f"   Local: {water_sources['local']}%")
        print(f"   Carried: {water_sources['carried']}%")
        print(f"   None: {water_sources['none']}%")
        print(f"   Vulnerability Index: {vuln_index}")

        # District analysis (top 3 districts by school count)
        water_by_district = summary.get('water_by_district', {})
        if water_by_district:
            print(f"\n🏘️  DISTRICT WATER PATTERNS (Top districts by school count):")
            sorted_districts = sorted(water_by_district.items(),
                                    key=lambda x: x[1]['total_schools'],
                                    reverse=True)[:3]

            for district, stats in sorted_districts:
                ws = stats['water_sources_percent']
                print(f"   {district}:")
                print(f"     Schools: {stats['total_schools']}")
                print(f"     Water - Central:{ws['centralized']}%, Local:{ws['local']}%, None:{ws['none']}%")
                print(f"     Sanitation Score: {stats['average_sanitation_score']}")

    # Comparative analysis
    print(f"\n📊 COMPARATIVE ANALYSIS")
    print("=" * 40)

    comparison_data = []
    for city, data in results.items():
        per_capita = data['summary']['per_capita_metrics']
        water_sources = data['summary']['sanitation_indicators']['water_sources']

        comparison_data.append({
            'City': city,
            'Schools/1000': per_capita['schools_per_1000'],
            'Hospitals/1000': per_capita['hospitals_per_1000'],
            'Water_Centralized_%': water_sources['centralized'],
            'Water_Local_%': water_sources['local'],
            'Water_None_%': water_sources['none'],
            'Vulnerability_Index': per_capita['water_vulnerability_index']
        })

    df = pd.DataFrame(comparison_data)
    print(df.to_string(index=False, float_format='%.2f'))

    # Key insights
    print(f"\n🎯 KEY INSIGHTS:")
    print("-" * 40)

    # Best water resilience
    best_water = min(comparison_data, key=lambda x: x['Vulnerability_Index'])
    print(f"💧 Most water-resilient city: {best_water['City']} (Index: {best_water['Vulnerability_Index']})")

    # Best healthcare access
    best_healthcare = max(comparison_data, key=lambda x: x['Hospitals/1000'])
    print(f"🏥 Best healthcare access: {best_healthcare['City']} ({best_healthcare['Hospitals/1000']} hospitals/1000)")

    # Education capacity
    best_education = max(comparison_data, key=lambda x: x['Schools/1000'])
    print(f"📚 Best education access: {best_education['City']} ({best_education['Schools/1000']} schools/1000)")

    # Water access challenges
    water_challenges = [city for city in comparison_data if city['Water_None_%'] > 5]
    if water_challenges:
        print(f"⚠️  Cities with water access challenges (>5% no water): {', '.join([c['City'] for c in water_challenges])}")

if __name__ == "__main__":
    analyze_social_sector_comprehensive()
