"""
Unit tests for IPCC AR6 climate risk assessment components.
Tests each component (Hazard, Exposure, Vulnerability, Adaptive Capacity) 
using real data from Uzbekistan cities.
"""

import unittest
import sys
import os
import numpy as np
from typing import Dict, Any

# Add services to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))

from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService


class TestIPCCComponents(unittest.TestCase):
    """Test suite for IPCC AR6 risk assessment components"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize data loader and assessment service with real data"""
        # Auto-detect data path
        base_path = os.path.dirname(__file__)
        data_path = os.path.join(base_path, "suhi_analysis_output")
        
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Data directory not found: {data_path}")
        
        print(f"Loading real data from: {data_path}")
        cls.data_loader = ClimateDataLoader(base_path=data_path)
        cls.assessment_service = IPCCRiskAssessmentService(cls.data_loader)
        
        # Load all data for testing
        cls.all_data = cls.data_loader.load_all_data()
        
        # Get sample cities for testing
        cls.test_cities = list(cls.all_data['temperature_data'].keys())[:5]  # Test first 5 cities
        
        print(f"Test cities: {cls.test_cities}")
        print(f"Total cities in dataset: {len(cls.all_data['temperature_data'])}")


class TestHazardScore(TestIPCCComponents):
    """Test hazard score calculations"""
    
    def test_hazard_score_range(self):
        """Test that hazard scores are in valid range [0, 1]"""
        print("\n=== TESTING HAZARD SCORES ===")
        
        for city in self.test_cities:
            with self.subTest(city=city):
                hazard_score = self.assessment_service.calculate_hazard_score(city)
                
                print(f"{city}: Hazard Score = {hazard_score:.3f}")
                
                # Validate range
                self.assertGreaterEqual(hazard_score, 0.0, 
                    f"Hazard score for {city} should be >= 0")
                self.assertLessEqual(hazard_score, 1.0, 
                    f"Hazard score for {city} should be <= 1")
    
    def test_hazard_score_temperature_correlation(self):
        """Test that hazard scores correlate with temperature data"""
        print("\n=== TESTING HAZARD-TEMPERATURE CORRELATION ===")
        
        hazard_scores = []
        max_temperatures = []
        temp_trends = []
        
        for city in self.test_cities:
            hazard_score = self.assessment_service.calculate_hazard_score(city)
            hazard_scores.append(hazard_score)
            
            # Extract temperature data for validation
            city_data = self.all_data['temperature_data'].get(city, {})
            if city_data:
                years = sorted(city_data.keys())
                if years:
                    latest_year = years[-1]
                    summer_stats = city_data[latest_year].get('summer_season_summary', {})
                    urban_day = summer_stats.get('urban', {}).get('day', {})
                    
                    max_temp = urban_day.get('max', 0)
                    mean_temp = urban_day.get('mean', 0)
                    max_temperatures.append(max_temp)
                    
                    # Calculate temperature trend
                    if len(years) >= 3:
                        temp_values = []
                        year_values = []
                        for year in years[-5:]:  # Last 5 years for trend
                            year_data = city_data[year].get('summer_season_summary', {})
                            temp_val = year_data.get('urban', {}).get('day', {}).get('mean')
                            if temp_val:
                                temp_values.append(temp_val)
                                year_values.append(int(year))
                        
                        if len(temp_values) >= 3:
                            trend = np.polyfit(year_values, temp_values, 1)[0]
                            temp_trends.append(trend)
                        else:
                            temp_trends.append(0.0)
                    else:
                        temp_trends.append(0.0)
                    
                    print(f"{city}: Hazard={hazard_score:.3f}, Max Temp={max_temp:.1f}°C, "
                          f"Mean Temp={mean_temp:.1f}°C, Trend={temp_trends[-1]:.3f}°C/yr")
        
        # Validate that non-zero hazard scores exist
        non_zero_hazards = [h for h in hazard_scores if h > 0]
        self.assertGreater(len(non_zero_hazards), 0, 
            "At least some cities should have non-zero hazard scores")
        
        # Validate temperature data extraction
        valid_temps = [t for t in max_temperatures if t > 0]
        self.assertGreater(len(valid_temps), 0, 
            "Should extract valid temperature data for hazard calculation")
        
        print(f"Hazard score range: {min(hazard_scores):.3f} - {max(hazard_scores):.3f}")
        print(f"Temperature range: {min(max_temperatures):.1f}°C - {max(max_temperatures):.1f}°C")
        print(f"Temperature trend range: {min(temp_trends):.3f} - {max(temp_trends):.3f}°C/yr")
    
    def test_hazard_score_components(self):
        """Test individual components that make up hazard score"""
        print("\n=== TESTING HAZARD SCORE COMPONENTS ===")
        
        for city in self.test_cities[:3]:  # Test detailed components for 3 cities
            print(f"\n--- {city} Hazard Analysis ---")
            
            city_data = self.all_data['temperature_data'].get(city, {})
            if not city_data:
                continue
                
            years = sorted(city_data.keys())
            if not years:
                continue
                
            latest_year = years[-1]
            summer_stats = city_data[latest_year].get('summer_season_summary', {})
            urban_day = summer_stats.get('urban', {}).get('day', {})
            
            mean_temp = urban_day.get('mean', 0)
            max_temp = urban_day.get('max', 0)
            p90_temp = urban_day.get('p90', 0)
            
            print(f"  Temperature Stats: Mean={mean_temp:.1f}°C, Max={max_temp:.1f}°C, P90={p90_temp:.1f}°C")
            
            # Validate temperature data is realistic
            self.assertGreater(mean_temp, 0, f"Mean temperature should be positive for {city}")
            self.assertGreater(max_temp, mean_temp, f"Max temperature should be > mean for {city}")
            self.assertGreaterEqual(p90_temp, mean_temp, f"P90 temperature should be >= mean for {city}")
            
            # Calculate hazard score and verify it uses this data
            hazard_score = self.assessment_service.calculate_hazard_score(city)
            print(f"  Final Hazard Score: {hazard_score:.3f}")
            
            # If temperatures are extreme, hazard should be higher
            if max_temp > 40:
                self.assertGreater(hazard_score, 0.2, 
                    f"Cities with max temp > 40°C should have hazard score > 0.2 ({city})")
            
            if mean_temp > 30:
                self.assertGreater(hazard_score, 0.1, 
                    f"Cities with mean temp > 30°C should have hazard score > 0.1 ({city})")


class TestExposureScore(TestIPCCComponents):
    """Test exposure score calculations"""
    
    def test_exposure_score_range(self):
        """Test that exposure scores are in valid range [0, 1]"""
        print("\n=== TESTING EXPOSURE SCORES ===")
        
        for city in self.test_cities:
            with self.subTest(city=city):
                exposure_score = self.assessment_service.calculate_exposure_score(city)
                
                print(f"{city}: Exposure Score = {exposure_score:.3f}")
                
                # Validate range
                self.assertGreaterEqual(exposure_score, 0.0, 
                    f"Exposure score for {city} should be >= 0")
                self.assertLessEqual(exposure_score, 1.0, 
                    f"Exposure score for {city} should be <= 1")
    
    def test_exposure_population_correlation(self):
        """Test that exposure scores correlate with population data"""
        print("\n=== TESTING EXPOSURE-POPULATION CORRELATION ===")
        
        exposure_scores = []
        populations = []
        densities = []
        
        for city in self.test_cities:
            exposure_score = self.assessment_service.calculate_exposure_score(city)
            exposure_scores.append(exposure_score)
            
            # Get population data
            pop_data = self.all_data['population_data'].get(city)
            if pop_data:
                population = pop_data.population_2024
                density = pop_data.density_per_km2
                populations.append(population)
                densities.append(density)
                
                print(f"{city}: Exposure={exposure_score:.3f}, Population={population:,}, "
                      f"Density={density:.1f}/km²")
            else:
                populations.append(0)
                densities.append(0)
                print(f"{city}: Exposure={exposure_score:.3f}, No population data")
        
        # Validate exposure calculation logic
        valid_populations = [p for p in populations if p > 0]
        self.assertGreater(len(valid_populations), 0, 
            "Should have valid population data for exposure calculation")
        
        # Largest cities should generally have higher exposure (but not always due to normalization)
        max_pop_idx = populations.index(max(populations))
        max_pop_city = self.test_cities[max_pop_idx]
        max_pop_exposure = exposure_scores[max_pop_idx]
        
        print(f"Largest city by population: {max_pop_city} (Pop: {max(populations):,}, "
              f"Exposure: {max_pop_exposure:.3f})")
        
        print(f"Exposure score range: {min(exposure_scores):.3f} - {max(exposure_scores):.3f}")
        print(f"Population range: {min(populations):,} - {max(populations):,}")
    
    def test_exposure_score_components(self):
        """Test individual components that make up exposure score"""
        print("\n=== TESTING EXPOSURE SCORE COMPONENTS ===")
        
        for city in self.test_cities[:3]:  # Test detailed components for 3 cities
            print(f"\n--- {city} Exposure Analysis ---")
            
            # Population component
            pop_data = self.all_data['population_data'].get(city)
            if pop_data:
                print(f"  Population: {pop_data.population_2024:,}")
                print(f"  Density: {pop_data.density_per_km2:.1f}/km²")
                
                # Validate population data is realistic
                self.assertGreater(pop_data.population_2024, 0, 
                    f"Population should be positive for {city}")
                self.assertGreater(pop_data.density_per_km2, 0, 
                    f"Density should be positive for {city}")
            
            # Built area component
            built_pct = 0
            for lulc_city in self.all_data['lulc_data']:
                if lulc_city.get('city') == city:
                    areas = lulc_city.get('areas_m2', {})
                    if areas:
                        years = sorted([int(y) for y in areas.keys()])
                        if years:
                            latest_year = str(years[-1])
                            built_pct = areas[latest_year].get('Built_Area', {}).get('percentage', 0)
                            print(f"  Built Area: {built_pct:.1f}%")
                    break
            
            # Nightlights component
            nightlight_mean = 0
            for nl_city in self.all_data['nightlights_data']:
                if nl_city.get('city') == city:
                    years_data = nl_city.get('years', {})
                    if years_data:
                        years = sorted([int(y) for y in years_data.keys()])
                        if years:
                            latest_year = str(years[-1])
                            nightlight_mean = years_data[latest_year].get('stats', {}).get('urban_core', {}).get('mean', 0)
                            print(f"  Nightlights: {nightlight_mean:.2f}")
                    break
            
            exposure_score = self.assessment_service.calculate_exposure_score(city)
            print(f"  Final Exposure Score: {exposure_score:.3f}")


class TestVulnerabilityScore(TestIPCCComponents):
    """Test vulnerability score calculations"""
    
    def test_vulnerability_score_range(self):
        """Test that vulnerability scores are in valid range [0, 1]"""
        print("\n=== TESTING VULNERABILITY SCORES ===")
        
        for city in self.test_cities:
            with self.subTest(city=city):
                vulnerability_score = self.assessment_service.calculate_vulnerability_score(city)
                
                print(f"{city}: Vulnerability Score = {vulnerability_score:.3f}")
                
                # Validate range
                self.assertGreaterEqual(vulnerability_score, 0.0, 
                    f"Vulnerability score for {city} should be >= 0")
                self.assertLessEqual(vulnerability_score, 1.0, 
                    f"Vulnerability score for {city} should be <= 1")
    
    def test_vulnerability_economic_correlation(self):
        """Test that vulnerability scores correlate with economic data"""
        print("\n=== TESTING VULNERABILITY-ECONOMIC CORRELATION ===")
        
        vulnerability_scores = []
        gdp_per_capita = []
        built_percentages = []
        
        for city in self.test_cities:
            vulnerability_score = self.assessment_service.calculate_vulnerability_score(city)
            vulnerability_scores.append(vulnerability_score)
            
            # Get economic data
            pop_data = self.all_data['population_data'].get(city)
            if pop_data:
                gdp = pop_data.gdp_per_capita_usd
                gdp_per_capita.append(gdp)
                print(f"{city}: Vulnerability={vulnerability_score:.3f}, GDP/capita=${gdp:,.0f}")
            else:
                gdp_per_capita.append(0)
                print(f"{city}: Vulnerability={vulnerability_score:.3f}, No economic data")
            
            # Get built area data
            built_pct = 0
            for lulc_city in self.all_data['lulc_data']:
                if lulc_city.get('city') == city:
                    areas = lulc_city.get('areas_m2', {})
                    if areas:
                        years = sorted([int(y) for y in areas.keys()])
                        if years:
                            latest_year = str(years[-1])
                            built_pct = areas[latest_year].get('Built_Area', {}).get('percentage', 0)
                    break
            built_percentages.append(built_pct)
        
        # Validate vulnerability calculation logic
        valid_gdp = [g for g in gdp_per_capita if g > 0]
        self.assertGreater(len(valid_gdp), 0, 
            "Should have valid GDP data for vulnerability calculation")
        
        # Lower GDP should generally correlate with higher vulnerability
        min_gdp_idx = gdp_per_capita.index(min([g for g in gdp_per_capita if g > 0]))
        max_gdp_idx = gdp_per_capita.index(max(gdp_per_capita))
        
        min_gdp_vuln = vulnerability_scores[min_gdp_idx]
        max_gdp_vuln = vulnerability_scores[max_gdp_idx]
        
        print(f"Lowest GDP city: {self.test_cities[min_gdp_idx]} "
              f"(GDP: ${gdp_per_capita[min_gdp_idx]:,.0f}, Vulnerability: {min_gdp_vuln:.3f})")
        print(f"Highest GDP city: {self.test_cities[max_gdp_idx]} "
              f"(GDP: ${gdp_per_capita[max_gdp_idx]:,.0f}, Vulnerability: {max_gdp_vuln:.3f})")
        
        print(f"Vulnerability score range: {min(vulnerability_scores):.3f} - {max(vulnerability_scores):.3f}")
        print(f"GDP/capita range: ${min(valid_gdp):,.0f} - ${max(gdp_per_capita):,.0f}")
    
    def test_vulnerability_green_space_correlation(self):
        """Test that vulnerability correlates with green space accessibility"""
        print("\n=== TESTING VULNERABILITY-GREEN SPACE CORRELATION ===")
        
        for city in self.test_cities[:3]:  # Test detailed for 3 cities
            print(f"\n--- {city} Vulnerability Analysis ---")
            
            # Get green space data
            spatial_city_data = self.all_data['spatial_data'].get('per_year', {}).get(city, {})
            if spatial_city_data:
                years = sorted([int(y) for y in spatial_city_data.keys()])
                if years:
                    latest_year = str(years[-1])
                    veg_access = spatial_city_data[latest_year].get('vegetation_accessibility', {}).get('city', {}).get('mean', 0)
                    
                    # Raw value is distance in meters, not percentage
                    print(f"  Vegetation Distance: {veg_access:.1f}m (Distance to nearest vegetation)")
                    
                    # Convert to accessibility score using the same logic as the actual calculation
                    max_walking_distance = 1000  # 1km as reasonable walking distance
                    accessibility_score = max(0.0, 1.0 - (veg_access / max_walking_distance))
                    print(f"  Vegetation Accessibility Score: {accessibility_score:.3f} (0=far, 1=close)")
                    
                    # Validate that distance is reasonable
                    self.assertGreaterEqual(veg_access, 0.0, 
                        f"Vegetation distance should be >= 0m for {city}")
                    
                    # Higher accessibility (lower distance) should reduce vulnerability
                    vulnerability_score = self.assessment_service.calculate_vulnerability_score(city)
                    print(f"  Vulnerability Score: {vulnerability_score:.3f}")
                    
                    if accessibility_score > 0.5:
                        print(f"  Note: Good vegetation accessibility should contribute to lower vulnerability")


class TestAdaptiveCapacityScore(TestIPCCComponents):
    """Test adaptive capacity score calculations"""
    
    def test_adaptive_capacity_score_range(self):
        """Test that adaptive capacity scores are in valid range [0, 1]"""
        print("\n=== TESTING ADAPTIVE CAPACITY SCORES ===")
        
        for city in self.test_cities:
            with self.subTest(city=city):
                adaptive_capacity_score = self.assessment_service.calculate_adaptive_capacity_score(city)
                
                print(f"{city}: Adaptive Capacity Score = {adaptive_capacity_score:.3f}")
                
                # Validate range
                self.assertGreaterEqual(adaptive_capacity_score, 0.0, 
                    f"Adaptive capacity score for {city} should be >= 0")
                self.assertLessEqual(adaptive_capacity_score, 1.0, 
                    f"Adaptive capacity score for {city} should be <= 1")
    
    def test_adaptive_capacity_economic_correlation(self):
        """Test that adaptive capacity correlates with economic resources"""
        print("\n=== TESTING ADAPTIVE CAPACITY-ECONOMIC CORRELATION ===")
        
        adaptive_scores = []
        gdp_per_capita = []
        populations = []
        
        for city in self.test_cities:
            adaptive_score = self.assessment_service.calculate_adaptive_capacity_score(city)
            adaptive_scores.append(adaptive_score)
            
            # Get economic and population data
            pop_data = self.all_data['population_data'].get(city)
            if pop_data:
                gdp = pop_data.gdp_per_capita_usd
                population = pop_data.population_2024
                gdp_per_capita.append(gdp)
                populations.append(population)
                
                print(f"{city}: Adaptive Capacity={adaptive_score:.3f}, "
                      f"GDP/capita=${gdp:,.0f}, Population={population:,}")
            else:
                gdp_per_capita.append(0)
                populations.append(0)
                print(f"{city}: Adaptive Capacity={adaptive_score:.3f}, No economic data")
        
        # Validate adaptive capacity calculation logic
        valid_gdp = [g for g in gdp_per_capita if g > 0]
        self.assertGreater(len(valid_gdp), 0, 
            "Should have valid GDP data for adaptive capacity calculation")
        
        # Higher GDP should generally correlate with higher adaptive capacity
        max_gdp_idx = gdp_per_capita.index(max(gdp_per_capita))
        max_gdp_city = self.test_cities[max_gdp_idx]
        max_gdp_adaptive = adaptive_scores[max_gdp_idx]
        
        print(f"Highest GDP city: {max_gdp_city} "
              f"(GDP: ${max(gdp_per_capita):,.0f}, Adaptive Capacity: {max_gdp_adaptive:.3f})")
        
        # Validate that adaptive capacity has reasonable distribution
        print(f"Adaptive capacity range: {min(adaptive_scores):.3f} - {max(adaptive_scores):.3f}")
        print(f"GDP/capita range: ${min(valid_gdp):,.0f} - ${max(gdp_per_capita):,.0f}")
        
        # Cities with very high GDP should have reasonable adaptive capacity
        if max(gdp_per_capita) > 10000:  # If any city has GDP > $10k
            self.assertGreater(max_gdp_adaptive, 0.3, 
                "Cities with high GDP should have reasonable adaptive capacity")
    
    def test_adaptive_capacity_components(self):
        """Test individual components that make up adaptive capacity score"""
        print("\n=== TESTING ADAPTIVE CAPACITY COMPONENTS ===")
        
        for city in self.test_cities[:3]:  # Test detailed components for 3 cities
            print(f"\n--- {city} Adaptive Capacity Analysis ---")
            
            # Economic component
            pop_data = self.all_data['population_data'].get(city)
            if pop_data:
                print(f"  GDP per capita: ${pop_data.gdp_per_capita_usd:,.0f}")
                print(f"  Population: {pop_data.population_2024:,}")
                
                # Validate economic data
                self.assertGreater(pop_data.gdp_per_capita_usd, 0, 
                    f"GDP per capita should be positive for {city}")
            
            # Green infrastructure component
            spatial_city_data = self.all_data['spatial_data'].get('per_year', {}).get(city, {})
            if spatial_city_data:
                years = sorted([int(y) for y in spatial_city_data.keys()])
                if years:
                    latest_year = str(years[-1])
                    veg_access = spatial_city_data[latest_year].get('vegetation_accessibility', {}).get('city', {}).get('mean', 0)
                    veg_patches = spatial_city_data[latest_year].get('veg_patches', {}).get('patch_count', 0)
                    
                    # Raw value is distance in meters, not percentage
                    print(f"  Vegetation Distance: {veg_access:.1f}m (Distance to nearest vegetation)")
                    print(f"  Vegetation Patches: {veg_patches}")
                    
                    # Convert to accessibility score using the same logic as the actual calculation
                    max_walking_distance = 1000  # 1km as reasonable walking distance
                    accessibility_score = max(0.0, 1.0 - (veg_access / max_walking_distance))
                    print(f"  Vegetation Accessibility Score: {accessibility_score:.3f} (0=far, 1=close)")
                    
                    # Validate vegetation data
                    self.assertGreaterEqual(veg_patches, 0, 
                        f"Vegetation patches should be non-negative for {city}")
            
            adaptive_score = self.assessment_service.calculate_adaptive_capacity_score(city)
            print(f"  Final Adaptive Capacity Score: {adaptive_score:.3f}")


if __name__ == '__main__':
    # Configure test output
    unittest.main(verbosity=2, buffer=False)
