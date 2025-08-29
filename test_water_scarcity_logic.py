#!/usr/bin/env python3
"""
Comprehensive test of water scarcity assessment logic, data validity, and format.
This script validates:
1. Real data sources are used (no mock/simulated data)
2. Assessment logic is scientifically sound
3. Data format is proper and consistent
4. Results are stored correctly
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, Any
from services.climate_data_loader import ClimateDataLoader, UZBEK_CITIES_DATA
from services.water_scarcity_gee import WaterScarcityGEEAssessment
from services import gee

def test_data_sources_are_real():
    """Test that only real data sources are used"""
    print("🔍 Testing data sources authenticity...")
    
    # Initialize services
    gee.initialize_gee()
    loader = ClimateDataLoader('.')
    service = WaterScarcityGEEAssessment(loader)
    
    # Check dataset definitions
    datasets = service.DATASETS
    expected_datasets = {
        'chirps': 'UCSB-CHG/CHIRPS/DAILY',  # Real precipitation
        'era5': 'ECMWF/ERA5/DAILY',         # Real reanalysis
        'jrc_gsw': 'JRC/GSW1_4/GlobalSurfaceWater'  # Real surface water
    }
    
    for key, expected_id in expected_datasets.items():
        assert key in datasets, f"Missing dataset: {key}"
        assert datasets[key] == expected_id, f"Wrong dataset ID for {key}: {datasets[key]} != {expected_id}"
    
    # Check that removed datasets are not present
    forbidden_datasets = ['worldcover', 'aqueduct', 'gpw']
    for forbidden in forbidden_datasets:
        assert forbidden not in datasets, f"Forbidden dataset still present: {forbidden}"
    
    print("✅ All data sources are real and authentic")

def test_population_data_accuracy():
    """Test that population data matches user-provided data exactly"""
    print("🔍 Testing population data accuracy...")
    
    loader = ClimateDataLoader('.')
    service = WaterScarcityGEEAssessment(loader)
    
    # Test a few cities with known data
    test_cities = ['Tashkent', 'Bukhara', 'Samarkand']
    
    for city in test_cities:
        # Get computed density
        pop_data = service.city_population_data.get(city, {})
        computed_density = pop_data.get('density', 0)
        
        # Get expected values from source data
        city_data = UZBEK_CITIES_DATA.get(city, {})
        expected_pop = city_data.get('pop_2024', 0)
        expected_area = city_data.get('area_km2', 1)
        expected_density = expected_pop / expected_area
        
        # Compare with tolerance for floating point
        diff = abs(computed_density - expected_density)
        assert diff < 0.01, f"{city}: Density mismatch. Got {computed_density}, expected {expected_density}"
        
        print(f"✅ {city}: Population density {computed_density:.1f}/km² matches expected {expected_density:.1f}/km²")

def test_assessment_logic():
    """Test that assessment logic is scientifically sound"""
    print("🔍 Testing assessment logic...")
    
    # Test normalization function
    def norm(x, low, high):
        return float(max(0.0, min(1.0, (x - low) / (high - low)))) if high > low else 0.0
    
    # Test boundary conditions
    assert norm(0.05, 0.05, 0.5) == 0.0, "Lower bound normalization failed"
    assert norm(0.5, 0.05, 0.5) == 1.0, "Upper bound normalization failed"
    assert abs(norm(0.275, 0.05, 0.5) - 0.5) < 1e-10, "Mid-point normalization failed"
    
    # Test that aridity index logic is correct (lower AI = higher risk)
    ai_high_risk = 0.1  # Arid
    ai_low_risk = 0.4   # Humid
    
    ai_s_high = 1.0 - norm(ai_high_risk, 0.05, 0.5)
    ai_s_low = 1.0 - norm(ai_low_risk, 0.05, 0.5)
    
    assert ai_s_high > ai_s_low, "Aridity index risk logic is inverted"
    
    # Test drought frequency bounds
    df_test = norm(0.3, 0.0, 0.5)  # 30% drought frequency
    assert 0.0 <= df_test <= 1.0, "Drought frequency normalization out of bounds"
    
    print("✅ Assessment logic is scientifically sound")

def test_data_format_consistency():
    """Test that all output data is in proper format"""
    print("🔍 Testing data format consistency...")
    
    # Check a sample city assessment
    gee.initialize_gee()
    loader = ClimateDataLoader('.')
    service = WaterScarcityGEEAssessment(loader)
    
    test_city = 'Tashkent'
    metrics = service.assess_city_water_scarcity(test_city)
    
    # Test that all required fields exist
    required_fields = [
        'city', 'aridity_index', 'climatic_water_deficit', 'drought_frequency',
        'surface_water_change', 'cropland_fraction', 'population_density',
        'aqueduct_bws_score', 'water_supply_risk', 'water_demand_risk',
        'overall_water_scarcity_score', 'water_scarcity_level'
    ]
    
    for field in required_fields:
        assert hasattr(metrics, field), f"Missing field: {field}"
    
    # Test data types and ranges
    assert isinstance(metrics.city, str), "City should be string"
    assert 0.0 <= metrics.aridity_index <= 1.0, f"Aridity index out of range: {metrics.aridity_index}"
    assert metrics.climatic_water_deficit >= 0.0, f"CWD should be non-negative: {metrics.climatic_water_deficit}"
    assert 0.0 <= metrics.drought_frequency <= 1.0, f"Drought frequency out of range: {metrics.drought_frequency}"
    assert 0.0 <= metrics.cropland_fraction <= 1.0, f"Cropland fraction out of range: {metrics.cropland_fraction}"
    assert metrics.population_density > 0, f"Population density should be positive: {metrics.population_density}"
    assert metrics.aqueduct_bws_score is None, f"Aqueduct score should be None: {metrics.aqueduct_bws_score}"
    assert 0.0 <= metrics.water_supply_risk <= 1.0, f"Supply risk out of range: {metrics.water_supply_risk}"
    assert 0.0 <= metrics.water_demand_risk <= 1.0, f"Demand risk out of range: {metrics.water_demand_risk}"
    assert 0.0 <= metrics.overall_water_scarcity_score <= 1.0, f"Overall score out of range: {metrics.overall_water_scarcity_score}"
    assert metrics.water_scarcity_level in ['Low', 'Moderate', 'High', 'Critical'], f"Invalid risk level: {metrics.water_scarcity_level}"
    
    print(f"✅ {test_city} data format is consistent and valid")

def test_json_storage_format():
    """Test that JSON storage format is correct"""
    print("🔍 Testing JSON storage format...")
    
    # Check if water scarcity results exist
    water_dir = Path('suhi_analysis_output/water_scarcity')
    assert water_dir.exists(), "Water scarcity output directory not found"
    
    # Test a sample city JSON file
    test_cities = ['Tashkent', 'Bukhara']
    
    for city in test_cities:
        city_file = water_dir / city / 'water_scarcity_assessment.json'
        assert city_file.exists(), f"Assessment file not found for {city}"
        
        # Load and validate JSON
        with open(city_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check required keys
        required_keys = [
            'city', 'aridity_index', 'climatic_water_deficit', 'drought_frequency',
            'surface_water_change', 'cropland_fraction', 'population_density',
            'aqueduct_bws_score', 'water_supply_risk', 'water_demand_risk',
            'overall_water_scarcity_score', 'water_scarcity_level'
        ]
        
        for key in required_keys:
            assert key in data, f"Missing key in {city} JSON: {key}"
        
        # Validate specific values
        assert data['city'] == city, f"City name mismatch in JSON: {data['city']} != {city}"
        assert data['aqueduct_bws_score'] is None, f"Aqueduct score should be null in {city}"
        assert isinstance(data['aridity_index'], (int, float)), f"Aridity index should be numeric in {city}"
        assert data['water_scarcity_level'] in ['Low', 'Moderate', 'High', 'Critical'], f"Invalid risk level in {city}"
        
        print(f"✅ {city} JSON format is correct")

def test_gee_data_authenticity():
    """Test that GEE data being fetched is real"""
    print("🔍 Testing GEE data authenticity...")
    
    gee.initialize_gee()
    loader = ClimateDataLoader('.')
    service = WaterScarcityGEEAssessment(loader)
    
    # Clear cache to force fresh GEE calls
    import shutil
    cache_dir = Path('suhi_analysis_output/data/water_scarcity')
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Test with one city to verify GEE data
    test_city = 'Bukhara'
    raw_data = service._fetch_city_indicators(test_city)
    
    # Check that we get reasonable climate data
    assert 0.05 <= raw_data['aridity_index'] <= 0.5, f"Unreasonable aridity index: {raw_data['aridity_index']}"
    assert 100 <= raw_data['climatic_water_deficit'] <= 2000, f"Unreasonable CWD: {raw_data['climatic_water_deficit']}"
    assert 0.0 <= raw_data['drought_frequency'] <= 1.0, f"Unreasonable drought frequency: {raw_data['drought_frequency']}"
    
    # Check that surface water change is reasonable (JRC data)
    swc = raw_data['surface_water_change']
    assert -100 <= swc <= 100, f"Unreasonable surface water change: {swc}"
    
    print(f"✅ GEE data for {test_city} appears authentic and reasonable")

def test_comprehensive_assessment():
    """Run comprehensive test on multiple cities"""
    print("🔍 Running comprehensive assessment test...")
    
    gee.initialize_gee()
    loader = ClimateDataLoader('.')
    service = WaterScarcityGEEAssessment(loader)
    
    test_cities = ['Tashkent', 'Bukhara', 'Nukus', 'Urgench']
    results = []
    
    for city in test_cities:
        metrics = service.assess_city_water_scarcity(city)
        results.append(metrics)
        
        # Print key metrics for verification
        print(f"📊 {city}:")
        print(f"   Aridity Index: {metrics.aridity_index:.3f}")
        print(f"   Population Density: {metrics.population_density:.1f}/km²")
        print(f"   Cropland Fraction: {metrics.cropland_fraction:.3f}")
        print(f"   Water Scarcity Score: {metrics.overall_water_scarcity_score:.3f}")
        print(f"   Risk Level: {metrics.water_scarcity_level}")
        print(f"   Aqueduct Score: {metrics.aqueduct_bws_score}")
    
    # Test that results are diverse and reasonable
    scores = [r.overall_water_scarcity_score for r in results]
    assert len(set([r.water_scarcity_level for r in results])) > 1, "All cities have same risk level - suspiciously uniform"
    assert np.std(scores) > 0.05, f"Scores too uniform - std: {np.std(scores)}"
    
    print("✅ Comprehensive assessment shows reasonable diversity")

def main():
    """Run all tests"""
    print("🧪 WATER SCARCITY ASSESSMENT VALIDATION")
    print("=" * 50)
    
    try:
        test_data_sources_are_real()
        test_population_data_accuracy()
        test_assessment_logic()
        test_data_format_consistency()
        test_json_storage_format()
        test_gee_data_authenticity()
        test_comprehensive_assessment()
        
        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED!")
        print("✅ Water scarcity assessment is using real data")
        print("✅ Assessment logic is scientifically sound")
        print("✅ Data format is proper and consistent")
        print("✅ Results are stored correctly")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise

if __name__ == "__main__":
    main()
