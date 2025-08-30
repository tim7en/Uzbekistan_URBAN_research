#!/usr/bin/env python3
"""
FIXED DIAGNOSTIC: Checks suspicious values using actual data structure.
Identifies real fallback/default values vs legitimate calculations.
"""

import json
import os
from pathlib import Path
from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService

class FixedSuspiciousValuesDiagnostic:
    def __init__(self):
        self.loader = ClimateDataLoader("suhi_analysis_output")
        self.service = IPCCRiskAssessmentService(self.loader)
        
        # Load the results file to compare
        with open("suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json", 'r') as f:
            self.results = json.load(f)
    
    def check_suspicious_patterns(self):
        """Check for suspicious patterns across all cities"""
        print("="*80)
        print("FIXED DIAGNOSTIC: REAL SUSPICIOUS VALUES ANALYSIS")
        print("="*80)
        
        # Collect all values for pattern analysis
        patterns = {}
        
        for city, data in self.results.items():
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    if key not in patterns:
                        patterns[key] = []
                    patterns[key].append(value)
        
        print("\n🔍 SUSPICIOUS PATTERN ANALYSIS:")
        print("-" * 50)
        
        for metric, values in patterns.items():
            unique_values = set(values)
            
            # Check for suspicious patterns
            suspicious_flags = []
            
            # All values the same
            if len(unique_values) == 1:
                suspicious_flags.append(f"ALL SAME VALUE: {list(unique_values)[0]}")
            
            # Many values are exactly 0.0, 0.5, or 1.0
            round_values = [v for v in values if v in [0.0, 0.5, 1.0]]
            if len(round_values) > len(values) * 0.7:  # More than 70% are round values
                suspicious_flags.append(f"TOO MANY ROUND VALUES: {len(round_values)}/{len(values)}")
            
            # All values are 1.0 (maximum)
            if all(v == 1.0 for v in values):
                suspicious_flags.append("ALL MAXIMUM (1.0)")
            
            # All values are 0.0 
            if all(v == 0.0 for v in values):
                suspicious_flags.append("ALL ZERO (0.0)")
                
            # All values are 0.5
            if all(v == 0.5 for v in values):
                suspicious_flags.append("ALL HALF (0.5)")
            
            if suspicious_flags:
                print(f"⚠️  {metric}: {' | '.join(suspicious_flags)}")
                print(f"   Values: {sorted(unique_values)}")
        
        return patterns
    
    def analyze_specific_suspicious_values(self):
        """Analyze the specific values mentioned by user"""
        print(f"\n{'='*60}")
        print("ANALYSIS OF USER-REPORTED SUSPICIOUS VALUES")
        print(f"{'='*60}")
        
        suspicious_cases = [
            ("Tashkent", "heat_hazard", 1.0, "Maximum heat hazard"),
            ("Tashkent", "pluvial_hazard", 1.0, "Maximum pluvial hazard"),
            ("Tashkent", "air_quality_hazard", 1.0, "Maximum air quality hazard"),
            ("Tashkent", "income_vulnerability", 0.0, "Zero income vulnerability"),
            ("Tashkent", "fragmentation_vulnerability", 1.0, "Maximum fragmentation vulnerability"),
            ("Tashkent", "bio_trend_vulnerability", 1.0, "Maximum bio trend vulnerability"),
            ("Tashkent", "surface_water_change", 0.0, "No surface water change"),
            ("Nukus", "pluvial_hazard", 0.1, "Minimum pluvial hazard"),
            ("Nukus", "bio_trend_vulnerability", 0.0, "Zero bio trend vulnerability"),
            ("Nukus", "surface_water_change", 0.0, "No surface water change"),
            ("Andijan", "air_quality_hazard", 1.0, "Maximum air quality hazard"),
            ("Andijan", "bio_trend_vulnerability", 1.0, "Maximum bio trend vulnerability"),
            ("Andijan", "water_system_capacity", 0.5, "Exactly half water system capacity")
        ]
        
        for city, metric, expected_value, description in suspicious_cases:
            actual_value = self.results.get(city, {}).get(metric, 'NOT_FOUND')
            
            if actual_value == expected_value:
                print(f"🚨 CONFIRMED SUSPICIOUS: {city} - {metric} = {actual_value} ({description})")
                self._investigate_metric_calculation(city, metric, actual_value)
            else:
                print(f"✅ VALUE CHANGED: {city} - {metric} = {actual_value} (was {expected_value})")
    
    def _investigate_metric_calculation(self, city, metric, value):
        """Investigate how a specific metric was calculated"""
        print(f"   🔍 Investigating {metric} calculation for {city}...")
        
        # Check raw data availability
        if "heat" in metric or "temperature" in metric:
            temp_data = self.service.data['temperature_data'].get(city, {})
            if temp_data:
                years = sorted(temp_data.keys())
                latest_year = years[-1] if years else 'None'
                print(f"   📊 Temperature data: {len(years)} years, latest: {latest_year}")
                
                if years:
                    latest_stats = temp_data[latest_year]
                    summer_stats = latest_stats.get('summer_season_summary', {})
                    urban_data = summer_stats.get('urban', {})
                    if urban_data:
                        urban_day = urban_data.get('day', {})
                        mean_temp = urban_day.get('mean', 'N/A')
                        max_temp = urban_day.get('max', 'N/A') 
                        print(f"   🌡️  Latest summer temps: mean={mean_temp}°C, max={max_temp}°C")
                        
                        if isinstance(mean_temp, (int, float)) and mean_temp > 45:
                            print(f"   ⚠️  Very high temperatures could justify heat_hazard=1.0")
                    else:
                        print(f"   ❌ No urban temperature data in latest year")
            else:
                print(f"   ❌ No temperature data available")
        
        elif "air_quality" in metric:
            aq_data = self.service.data['air_quality_data']
            city_aq = None
            for aq_city in aq_data:
                if aq_city.get('city') == city:
                    city_aq = aq_city
                    break
            
            if city_aq:
                print(f"   📊 Air quality data found")
                # Check for high pollution levels that could justify max hazard
                years_data = city_aq.get('years', {})
                if years_data:
                    latest_year = max(years_data.keys(), key=lambda x: int(x))
                    latest_aq = years_data[latest_year]
                    annual_data = latest_aq.get('annual', {})
                    pm25 = annual_data.get('PM2_5', 'N/A')
                    no2 = annual_data.get('NO2', 'N/A')
                    print(f"   💨 Latest air quality: PM2.5={pm25}, NO2={no2}")
                    
                    if isinstance(pm25, (int, float)) and pm25 > 50:
                        print(f"   ⚠️  Very high PM2.5 could justify air_quality_hazard=1.0")
            else:
                print(f"   ❌ No air quality data available")
        
        elif "income" in metric:
            gdp_per_capita = self.results.get(city, {}).get('gdp_per_capita_usd', 'N/A')
            print(f"   💰 GDP per capita: ${gdp_per_capita}")
            
            if isinstance(gdp_per_capita, (int, float)) and gdp_per_capita > 3000:
                print(f"   ⚠️  High GDP could justify income_vulnerability=0.0")
        
        elif "water_system_capacity" in metric:
            print(f"   💧 Checking if water_system_capacity=0.5 is hardcoded...")
            # Check if all cities have the same value
            all_water_values = [self.results[c].get('water_system_capacity', 'N/A') for c in self.results.keys()]
            unique_water_values = set(all_water_values)
            print(f"   🔍 All cities water_system_capacity: {unique_water_values}")
            
            if len(unique_water_values) == 1:
                print(f"   🚨 CONFIRMED: All cities have same water_system_capacity - likely hardcoded!")
        
        elif "surface_water_change" in metric:
            print(f"   🌊 Checking surface_water_change=0.0...")
            all_water_change = [self.results[c].get('surface_water_change', 'N/A') for c in self.results.keys()]
            unique_change_values = set(all_water_change)
            print(f"   🔍 All cities surface_water_change: {unique_change_values}")
            
            if len(unique_change_values) == 1 and list(unique_change_values)[0] == 0.0:
                print(f"   🚨 CONFIRMED: All cities have surface_water_change=0.0 - likely missing data!")
    
    def check_data_availability(self):
        """Check actual data availability in the loader"""
        print(f"\n{'='*60}")
        print("DATA AVAILABILITY CHECK")
        print(f"{'='*60}")
        
        data_types = [
            ('temperature_data', 'Temperature'),
            ('suhi_data', 'SUHI'), 
            ('lulc_data', 'Land Use/Land Cover'),
            ('air_quality_data', 'Air Quality'),
            ('nightlights_data', 'Nightlights'),
            ('population_data', 'Population')
        ]
        
        for attr_name, display_name in data_types:
            data = getattr(self.service.data, attr_name, None) or self.service.data.get(attr_name, {})
            
            if isinstance(data, dict):
                cities_count = len(data)
                print(f"📊 {display_name}: {cities_count} cities")
                
                if cities_count > 0:
                    sample_city = list(data.keys())[0]
                    sample_data = data[sample_city]
                    if isinstance(sample_data, dict) and 'years' in str(sample_data):
                        # Multi-year data
                        years = len(sample_data) if isinstance(sample_data, dict) else 'Unknown'
                        print(f"   Sample ({sample_city}): {years} years of data")
                    else:
                        print(f"   Sample ({sample_city}): Data structure looks good")
            elif isinstance(data, list):
                cities_count = len(data)
                print(f"📊 {display_name}: {cities_count} cities")
            else:
                print(f"❌ {display_name}: No data or wrong format")

def main():
    """Main diagnostic function"""
    diagnostic = FixedSuspiciousValuesDiagnostic()
    
    # Check for suspicious patterns
    patterns = diagnostic.check_suspicious_patterns()
    
    # Analyze specific suspicious values reported by user
    diagnostic.analyze_specific_suspicious_values()
    
    # Check data availability
    diagnostic.check_data_availability()
    
    print(f"\n{'='*80}")
    print("FIXED DIAGNOSTIC COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
