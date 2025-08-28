"""Social sector analysis service for healthcare, education, and sanitation infrastructure.

Analyzes hospitals, schools, and kindergardens within city boundaries to assess
social infrastructure coverage, sanitation access, and educational/healthcare capacity.
"""

import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

from .utils import UZBEKISTAN_CITIES, create_output_directories


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points in kilometers."""
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    # Earth's radius in kilometers
    R = 6371
    return R * c


def is_point_in_city_buffer(lat: float, lon: float, city_lat: float, city_lon: float, buffer_m: float) -> bool:
    """Check if a point is within the city's buffer distance."""
    distance_km = haversine_distance(lat, lon, city_lat, city_lon)
    buffer_km = buffer_m / 1000.0
    return distance_km <= buffer_km


def load_external_data(data_dir: Path) -> Dict[str, Any]:
    """Load all external data files."""
    data = {}

    # Load schools data (GeoJSON format)
    schools_file = data_dir / "Schools_assessed.json"
    if schools_file.exists():
        with open(schools_file, 'r', encoding='utf-8') as f:
            data['schools'] = json.load(f)
    else:
        data['schools'] = {"type": "FeatureCollection", "features": []}

    # Load hospitals data
    hospitals_file = data_dir / "Hospitals.json"
    if hospitals_file.exists():
        with open(hospitals_file, 'r', encoding='utf-8') as f:
            hospitals_data = json.load(f)
            data['hospitals'] = hospitals_data.get('result', [])
    else:
        data['hospitals'] = []

    # Load government kindergardens
    kg_gov_file = data_dir / "KinderGardenGov.json"
    if kg_gov_file.exists():
        with open(kg_gov_file, 'r', encoding='utf-8') as f:
            kg_gov_data = json.load(f)
            data['kindergardens_gov'] = kg_gov_data.get('result', [])
    else:
        data['kindergardens_gov'] = []

    # Load private kindergardens
    kg_private_file = data_dir / "KinderGardenPrivate.json"
    if kg_private_file.exists():
        with open(kg_private_file, 'r', encoding='utf-8') as f:
            kg_private_data = json.load(f)
            data['kindergardens_private'] = kg_private_data.get('result', [])
    else:
        data['kindergardens_private'] = []

    return data


def analyze_city_social_sector(city: str, external_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze social sector infrastructure for a specific city."""
    if city not in UZBEKISTAN_CITIES:
        return {"error": f"City {city} not found in configuration"}

    city_info = UZBEKISTAN_CITIES[city]
    city_lat, city_lon = city_info['lat'], city_info['lon']
    buffer_m = city_info['buffer_m']
    population = city_info.get('population', 0)

    results = {
        "city": city,
        "city_info": city_info,
        "facilities": {
            "schools": [],
            "hospitals": [],
            "kindergardens_gov": [],
            "kindergardens_private": []
        },
        "summary": {
            "total_schools": 0,
            "total_hospitals": 0,
            "total_kindergardens": 0,
            "total_students_capacity": 0,
            "total_students_enrolled": 0,
            "sanitation_indicators": {},
            "infrastructure_quality": {},
            "water_by_district": {},
            "per_capita_metrics": {}
        }
    }

    # Analyze schools
    schools_data = external_data.get('schools', {})
    for feature in schools_data.get('features', []):
        geom = feature.get('geometry')
        if geom and geom.get('type') == 'Point':
            coords = geom.get('coordinates', [])
            if len(coords) >= 2:
                school_lon, school_lat = coords[0], coords[1]

                if is_point_in_city_buffer(school_lat, school_lon, city_lat, city_lon, buffer_m):
                    properties = feature.get('properties', {})

                    school_info = {
                        "id": feature.get('id'),
                        "name": properties.get('obekt_nomi', ''),
                        "name_en": properties.get('obekt_nomi_en', ''),
                        "viloyat": properties.get('viloyat', ''),
                        "tuman": properties.get('tuman', ''),
                        "coordinates": [school_lon, school_lat],
                        "capacity": int(properties.get('sigimi', 0)) if properties.get('sigimi') else 0,
                        "enrolled_students": int(properties.get('umumiy_uquvchi', 0)) if properties.get('umumiy_uquvchi') else 0,
                        "shifts": int(properties.get('smena', 1)) if properties.get('smena') else 1,
                        "construction_year": properties.get('qurilish_yili', ''),
                        "building_material": properties.get('material_sten', ''),
                        "sanitation": {
                            "electricity": properties.get('elektr_kun_davomida', ''),
                            "water_source": properties.get('ichimlik_suvi_manbaa', ''),
                            "internet": properties.get('internetga_ulanish_turi', ''),
                            "sports_hall": properties.get('sport_zal_holati', ''),
                            "activity_hall": properties.get('aktiv_zal_holati', ''),
                            "dining_hall": properties.get('oshhona_holati', '')
                        }
                    }

                    results["facilities"]["schools"].append(school_info)
                    results["summary"]["total_schools"] += 1
                    results["summary"]["total_students_capacity"] += school_info["capacity"]
                    results["summary"]["total_students_enrolled"] += school_info["enrolled_students"]

    # Analyze hospitals
    hospitals_data = external_data.get('hospitals', [])
    for hospital in hospitals_data:
        hosp_lat = hospital.get('lat')
        hosp_lon = hospital.get('long')

        if hosp_lat and hosp_lon:
            if is_point_in_city_buffer(hosp_lat, hosp_lon, city_lat, city_lon, buffer_m):
                hospital_info = {
                    "id": hospital.get('id'),
                    "name": hospital.get('title', ''),
                    "coordinates": [hosp_lon, hosp_lat],
                    "type": hospital.get('type', 'hospital')
                }

                results["facilities"]["hospitals"].append(hospital_info)
                results["summary"]["total_hospitals"] += 1

    # Analyze government kindergardens
    kg_gov_data = external_data.get('kindergardens_gov', [])
    for kg in kg_gov_data:
        kg_lat = kg.get('lat')
        kg_lon = kg.get('long')

        if kg_lat and kg_lon:
            if is_point_in_city_buffer(kg_lat, kg_lon, city_lat, city_lon, buffer_m):
                kg_info = {
                    "id": kg.get('id'),
                    "name": kg.get('title', ''),
                    "coordinates": [kg_lon, kg_lat],
                    "type": kg.get('type', 'kindergarden-legal')
                }

                results["facilities"]["kindergardens_gov"].append(kg_info)
                results["summary"]["total_kindergardens"] += 1

    # Analyze private kindergardens
    kg_private_data = external_data.get('kindergardens_private', [])
    for kg in kg_private_data:
        kg_lat = kg.get('lat')
        kg_lon = kg.get('long')

        if kg_lat and kg_lon:
            if is_point_in_city_buffer(kg_lat, kg_lon, city_lat, city_lon, buffer_m):
                kg_info = {
                    "id": kg.get('id'),
                    "name": kg.get('title', ''),
                    "coordinates": [kg_lon, kg_lat],
                    "type": kg.get('type', 'kindergarden')
                }

                results["facilities"]["kindergardens_private"].append(kg_info)
                results["summary"]["total_kindergardens"] += 1

    # Calculate sanitation and infrastructure indicators
    results["summary"]["sanitation_indicators"] = _calculate_sanitation_indicators(results["facilities"]["schools"])
    results["summary"]["infrastructure_quality"] = _calculate_infrastructure_quality(results["facilities"]["schools"])

    # Analyze water availability by administrative divisions
    results["summary"]["water_by_district"] = _analyze_water_by_district(results["facilities"]["schools"])

    # Calculate per capita social infrastructure metrics
    results["summary"]["per_capita_metrics"] = _calculate_per_capita_metrics(results["summary"], population)

    return results


def _calculate_sanitation_indicators(schools: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate sanitation indicators from school data."""
    if not schools:
        return {}

    indicators = {
        "electricity_access": 0.0,
        "water_access": 0.0,
        "internet_access": 0.0,
        "sports_facilities": 0.0,
        "dining_facilities": 0.0,
        "activity_halls": 0.0,
        "water_sources": {},  # Initialize as dict
        "water_vulnerability_index": 0.0
    }

    # Detailed water source categorization
    water_sources = {
        "centralized": 0.0,  # ichimlik_suvi_manbaa_markaz
        "local": 0.0,       # ichimlik_suvi_manbaa_lokal
        "carried": 0.0,     # ichimlik_suvi_manbaa_olib_kelinadi
        "none": 0.0         # ichimlik_suvi_yuq or empty
    }

    total_schools = len(schools)

    for school in schools:
        sanitation = school.get('sanitation', {})

        if sanitation.get('electricity') == 'elektr_bor':
            indicators["electricity_access"] += 1

        # Enhanced water source analysis
        water_source = sanitation.get('water_source', '')
        if water_source:
            if 'markaz' in water_source.lower():
                water_sources["centralized"] += 1
                indicators["water_access"] += 1  # Count as having water access
            elif 'lokal' in water_source.lower():
                water_sources["local"] += 1
                indicators["water_access"] += 1
            elif 'olib_kelinadi' in water_source.lower():
                water_sources["carried"] += 1
                indicators["water_access"] += 1
            elif 'yuq' in water_source.lower():
                water_sources["none"] += 1
        else:
            water_sources["none"] += 1

        if sanitation.get('internet'):
            indicators["internet_access"] += 1

        if sanitation.get('sports_hall') == 'sport_zal_qoniqarli':
            indicators["sports_facilities"] += 1

        if sanitation.get('dining_hall') == 'oshhona_holati_qoniqarli':
            indicators["dining_facilities"] += 1

        if sanitation.get('activity_hall') == 'aktiv_zal_qoniqarli':
            indicators["activity_halls"] += 1

    # Convert to percentages
    for key in ["electricity_access", "water_access", "internet_access", "sports_facilities", "dining_facilities", "activity_halls"]:
        indicators[key] = round((indicators[key] / total_schools) * 100, 1) if total_schools > 0 else 0.0

    # Convert water sources to percentages
    for key in water_sources:
        water_sources[key] = round((water_sources[key] / total_schools) * 100, 1) if total_schools > 0 else 0.0

    # Add water source breakdown to indicators
    indicators["water_sources"] = water_sources

    # Calculate water vulnerability index
    indicators["water_vulnerability_index"] = _calculate_water_vulnerability_index(water_sources)

    return indicators


def _calculate_water_vulnerability_index(water_sources: Dict[str, float]) -> float:
    """Calculate water vulnerability index based on water source types.

    Vulnerability scoring:
    - Centralized systems: Moderate vulnerability (0.3) - climate-sensitive infrastructure
    - Local systems: Low vulnerability (0.1) - more resilient but potentially contaminated
    - Carried water: High vulnerability (0.8) - severe infrastructure gaps
    - No water: Extreme vulnerability (1.0) - critical access issues

    Returns: Vulnerability index from 0.0 (no vulnerability) to 1.0 (extreme vulnerability)
    """
    weights = {
        "centralized": 0.3,
        "local": 0.1,
        "carried": 0.8,
        "none": 1.0
    }

    total_vulnerability = 0.0
    total_schools = sum(water_sources.values())

    if total_schools == 0:
        return 0.0

    for source_type, percentage in water_sources.items():
        if source_type in weights:
            # Convert percentage back to count for weighting
            count = (percentage / 100.0) * total_schools
            total_vulnerability += count * weights[source_type]

    return round(total_vulnerability / total_schools, 3)


def _calculate_infrastructure_quality(schools: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate infrastructure quality indicators."""
    if not schools:
        return {}

    quality = {
        "modern_buildings": 0.0,  # Built after 2000
        "brick_construction": 0.0,
        "multiple_shifts": 0.0
    }

    total_schools = len(schools)

    for school in schools:
        # Construction year
        try:
            year = int(school.get('construction_year', 0))
            if year >= 2000:
                quality["modern_buildings"] += 1
        except (ValueError, TypeError):
            pass

        # Building material
        if school.get('building_material') == 'gisht':
            quality["brick_construction"] += 1

        # Multiple shifts (overcrowding indicator)
        if school.get('shifts', 1) > 1:
            quality["multiple_shifts"] += 1

    # Convert to percentages
    for key in quality:
        quality[key] = round((quality[key] / total_schools) * 100, 1) if total_schools > 0 else 0.0

    return quality


def _analyze_water_by_district(schools: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze water availability patterns by administrative districts."""
    district_stats: Dict[str, Dict[str, Any]] = {}

    for school in schools:
        viloyat = school.get('viloyat', 'Unknown')
        tuman = school.get('tuman', 'Unknown')
        district_key = f"{viloyat} - {tuman}"

        if district_key not in district_stats:
            district_stats[district_key] = {
                "total_schools": 0,
                "water_sources": {"centralized": 0, "local": 0, "carried": 0, "none": 0},
                "sanitation_score": 0.0
            }

        district_stats[district_key]["total_schools"] += 1

        # Analyze water source
        water_source = school.get('sanitation', {}).get('water_source', '')
        if water_source:
            if 'markaz' in water_source.lower():
                district_stats[district_key]["water_sources"]["centralized"] += 1
            elif 'lokal' in water_source.lower():
                district_stats[district_key]["water_sources"]["local"] += 1
            elif 'olib_kelinadi' in water_source.lower():
                district_stats[district_key]["water_sources"]["carried"] += 1
            elif 'yuq' in water_source.lower():
                district_stats[district_key]["water_sources"]["none"] += 1

        # Calculate sanitation score for district
        sanitation = school.get('sanitation', {})
        score = 0.0
        if sanitation.get('electricity') == 'elektr_bor':
            score += 0.25
        if sanitation.get('water_source') and 'yuq' not in sanitation.get('water_source', '').lower():
            score += 0.25
        if sanitation.get('internet'):
            score += 0.25
        if sanitation.get('sports_hall') == 'sport_zal_qoniqarli':
            score += 0.25

        district_stats[district_key]["sanitation_score"] += score

    # Convert to percentages and finalize
    result = {}
    for district, stats in district_stats.items():
        total_schools = stats["total_schools"]
        result[district] = {
            "total_schools": total_schools,
            "water_sources_percent": {
                "centralized": round((stats["water_sources"]["centralized"] / total_schools) * 100, 1) if total_schools > 0 else 0.0,
                "local": round((stats["water_sources"]["local"] / total_schools) * 100, 1) if total_schools > 0 else 0.0,
                "carried": round((stats["water_sources"]["carried"] / total_schools) * 100, 1) if total_schools > 0 else 0.0,
                "none": round((stats["water_sources"]["none"] / total_schools) * 100, 1) if total_schools > 0 else 0.0
            },
            "average_sanitation_score": round(stats["sanitation_score"] / total_schools, 2) if total_schools > 0 else 0.0
        }

    return result


def _calculate_per_capita_metrics(summary: Dict[str, Any], population: int) -> Dict[str, Any]:
    """Calculate per capita social infrastructure metrics for risk analysis."""
    if population <= 0:
        return {
            "schools_per_1000": 0.0,
            "hospitals_per_1000": 0.0,
            "kindergardens_per_1000": 0.0,
            "student_capacity_per_1000": 0.0,
            "enrolled_students_per_1000": 0.0,
            "water_vulnerability_index": summary.get("sanitation_indicators", {}).get("water_vulnerability_index", 0.0)
        }

    population_in_thousands = population / 1000.0

    return {
        "schools_per_1000": round(summary.get("total_schools", 0) / population_in_thousands, 2),
        "hospitals_per_1000": round(summary.get("total_hospitals", 0) / population_in_thousands, 2),
        "kindergardens_per_1000": round(summary.get("total_kindergardens", 0) / population_in_thousands, 2),
        "student_capacity_per_1000": round(summary.get("total_students_capacity", 0) / population_in_thousands, 2),
        "enrolled_students_per_1000": round(summary.get("total_students_enrolled", 0) / population_in_thousands, 2),
        "water_vulnerability_index": summary.get("sanitation_indicators", {}).get("water_vulnerability_index", 0.0),
        "population": population
    }


def run_batch_social_analysis(cities: Optional[List[str]] = None, verbose: bool = False) -> Dict[str, Any]:
    """Run social sector analysis for multiple cities."""
    if cities is None:
        cities = list(UZBEKISTAN_CITIES.keys())

    # Load external data
    data_dir = Path(__file__).parent.parent / "ExternalData"
    if verbose:
        print(f"Loading external data from {data_dir}")

    external_data = load_external_data(data_dir)

    results = {}
    for city in cities:
        if verbose:
            print(f"Analyzing social sector for {city}")

        city_results = analyze_city_social_sector(city, external_data)
        results[city] = city_results

        if verbose:
            summary = city_results.get('summary', {})
            print(f"  {city}: {summary.get('total_schools', 0)} schools, "
                  f"{summary.get('total_hospitals', 0)} hospitals, "
                  f"{summary.get('total_kindergardens', 0)} kindergardens")

    return results


def save_social_analysis_results(results: Dict[str, Any], output_dir: Optional[Path] = None) -> None:
    """Save social analysis results to JSON files."""
    if output_dir is None:
        dirs = create_output_directories()
        output_dir = dirs['base'] / 'social_sector'

    output_dir.mkdir(parents=True, exist_ok=True)

    # Save overall results
    overall_file = output_dir / 'social_sector_analysis.json'
    with open(overall_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Save individual city files
    for city, city_results in results.items():
        city_file = output_dir / f'{city}_social_sector.json'
        with open(city_file, 'w', encoding='utf-8') as f:
            json.dump(city_results, f, indent=2, ensure_ascii=False)

    print(f"Saved social sector analysis results to {output_dir}")
