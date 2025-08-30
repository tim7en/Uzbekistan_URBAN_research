#!/usr/bin/env python3
"""
Diagnostic tool to investigate suspicious values in climate risk assessment results.
Checks for potential fallback values, data processing issues, and validates against raw data.
"""

import json
import os
from pathlib import Path
from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService

class SuspiciousValuesDiagnostic:
    def __init__(self):
        self.loader = ClimateDataLoader("suhi_analysis_output")
        self.service = IPCCRiskAssessmentService(self.loader)
        
        # Load the results file to compare
        with open("suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json", 'r') as f:
            self.results = json.load(f)
    
    def diagnose_all_suspicious_values(self):
        """Comprehensive diagnosis of all suspicious values"""
        print("="*80)
        print("DIAGNOSTIC: SUSPICIOUS VALUES IN CLIMATE RISK ASSESSMENT")
        print("="*80)
        
        # Focus on the three cities mentioned
        cities_to_check = ["Tashkent", "Nukus", "Andijan"]
        
        for city in cities_to_check:
            print(f"\n{'='*60}")
            print(f"DIAGNOSING: {city}")
            print(f"{'='*60}")
            
            self._diagnose_city_values(city)
    
    def _diagnose_city_values(self, city):
        """Diagnose suspicious values for a specific city"""
        city_results = self.results.get(city, {})
        
        print(f"\n1. HAZARD COMPONENTS DIAGNOSIS:")
        print("-" * 40)
        self._check_hazard_values(city, city_results)
        
        print(f"\n2. VULNERABILITY COMPONENTS DIAGNOSIS:")
        print("-" * 40)
        self._check_vulnerability_values(city, city_results)
        
        print(f"\n3. ADAPTIVE CAPACITY COMPONENTS DIAGNOSIS:")
        print("-" * 40)
        self._check_adaptive_capacity_values(city, city_results)
        
        print(f"\n4. WATER AND ENVIRONMENTAL DIAGNOSIS:")
        print("-" * 40)
        self._check_environmental_values(city, city_results)
    
    def _check_hazard_values(self, city, results):
        """Check hazard component values against raw data"""
        
        # Heat hazard - check temperature data
        heat_hazard = results.get('heat_hazard', 'N/A')
        print(f"🌡️  Heat Hazard: {heat_hazard}")
        
        temp_file = f"suhi_analysis_output/temperature/{city}_temperature_metrics.json"
        if os.path.exists(temp_file):
            with open(temp_file, 'r') as f:
                temp_data = json.load(f)
            
            summer_temp = temp_data.get('summer_season_summary', {}).get('mean_LST_C', 'N/A')
            annual_temp = temp_data.get('annual_summary', {}).get('mean_LST_C', 'N/A')
            heat_waves = temp_data.get('extreme_events', {}).get('heat_wave_frequency', 'N/A')
            
            print(f"   Raw Data: Summer {summer_temp}°C, Annual {annual_temp}°C, Heat waves: {heat_waves}")
            
            # Check if heat hazard = 1.0 is justified
            if heat_hazard == 1.0:
                print("   ⚠️  SUSPICIOUS: Heat hazard = 1.0 (maximum)")
        else:
            print("   ❌ No temperature data file found")
        
        # Pluvial hazard
        pluvial_hazard = results.get('pluvial_hazard', 'N/A')
        print(f"🌧️  Pluvial Hazard: {pluvial_hazard}")
        if pluvial_hazard == 1.0:
            print("   ⚠️  SUSPICIOUS: Pluvial hazard = 1.0 (maximum)")
        elif pluvial_hazard == 0.1:
            print("   ⚠️  SUSPICIOUS: Pluvial hazard = 0.1 (minimum)")
        
        # Air quality hazard
        air_quality_hazard = results.get('air_quality_hazard', 'N/A')
        print(f"💨 Air Quality Hazard: {air_quality_hazard}")
        
        aq_file = f"suhi_analysis_output/air_quality/{city}_air_quality_metrics.json"
        if os.path.exists(aq_file):
            with open(aq_file, 'r') as f:
                aq_data = json.load(f)
            
            if 'metrics' in aq_data and 'annual' in aq_data['metrics']:
                annual = aq_data['metrics']['annual']
                pm25 = annual.get('PM2_5', 'N/A')
                no2 = annual.get('NO2', 'N/A')
                print(f"   Raw Data: PM2.5 {pm25}, NO2 {no2}")
                
                if air_quality_hazard == 1.0:
                    print("   ⚠️  SUSPICIOUS: Air quality hazard = 1.0 (maximum) - check if justified by PM2.5 levels")
        else:
            print("   ❌ No air quality data file found")
    
    def _check_vulnerability_values(self, city, results):
        """Check vulnerability component values"""
        
        # Income vulnerability
        income_vuln = results.get('income_vulnerability', 'N/A')
        print(f"💰 Income Vulnerability: {income_vuln}")
        if income_vuln == 0.0:
            print("   ⚠️  SUSPICIOUS: Income vulnerability = 0.0 (no vulnerability)")
            gdp_per_capita = results.get('gdp_per_capita_usd', 'N/A')
            print(f"   GDP per capita: ${gdp_per_capita}")
        
        # Fragmentation vulnerability
        frag_vuln = results.get('fragmentation_vulnerability', 'N/A')
        print(f"🌿 Fragmentation Vulnerability: {frag_vuln}")
        if frag_vuln == 1.0:
            print("   ⚠️  SUSPICIOUS: Fragmentation vulnerability = 1.0 (maximum)")
        elif frag_vuln == 0.0:
            print("   ⚠️  SUSPICIOUS: Fragmentation vulnerability = 0.0 (minimum)")
        
        # Bio trend vulnerability
        bio_trend_vuln = results.get('bio_trend_vulnerability', 'N/A')
        print(f"🌱 Bio Trend Vulnerability: {bio_trend_vuln}")
        if bio_trend_vuln == 1.0:
            print("   ⚠️  SUSPICIOUS: Bio trend vulnerability = 1.0 (maximum)")
        elif bio_trend_vuln == 0.0:
            print("   ⚠️  SUSPICIOUS: Bio trend vulnerability = 0.0 (minimum)")
        
        # Air pollution vulnerability
        air_poll_vuln = results.get('air_pollution_vulnerability', 'N/A')
        print(f"💨 Air Pollution Vulnerability: {air_poll_vuln}")
        if air_poll_vuln == 0.8:
            print("   ⚠️  SUSPICIOUS: Air pollution vulnerability = 0.8 (suspiciously round number)")
    
    def _check_adaptive_capacity_values(self, city, results):
        """Check adaptive capacity component values"""
        
        # GDP adaptive capacity
        gdp_adaptive = results.get('gdp_adaptive_capacity', 'N/A')
        print(f"💰 GDP Adaptive Capacity: {gdp_adaptive}")
        if gdp_adaptive == 1.0:
            print("   ⚠️  SUSPICIOUS: GDP adaptive capacity = 1.0 (maximum)")
        
        # Services adaptive capacity
        services_adaptive = results.get('services_adaptive_capacity', 'N/A')
        print(f"🏢 Services Adaptive Capacity: {services_adaptive}")
        if services_adaptive == 1.0:
            print("   ⚠️  SUSPICIOUS: Services adaptive capacity = 1.0 (maximum)")
        elif services_adaptive == 0.1:
            print("   ⚠️  SUSPICIOUS: Services adaptive capacity = 0.1 (minimum)")
        
        # Water system capacity
        water_system = results.get('water_system_capacity', 'N/A')
        print(f"💧 Water System Capacity: {water_system}")
        if water_system == 0.5:
            print("   ⚠️  SUSPICIOUS: Water system capacity = 0.5 (exactly half - possible default)")
        
        # Economic capacity
        economic_capacity = results.get('economic_capacity', 'N/A')
        print(f"📈 Economic Capacity: {economic_capacity}")
        if economic_capacity == 1.0:
            print("   ⚠️  SUSPICIOUS: Economic capacity = 1.0 (maximum)")
    
    def _check_environmental_values(self, city, results):
        """Check environmental and water-related values"""
        
        # Surface water change
        surface_water = results.get('surface_water_change', 'N/A')
        print(f"🌊 Surface Water Change: {surface_water}")
        if surface_water == 0.0:
            print("   ⚠️  SUSPICIOUS: Surface water change = 0.0 (no change - unlikely)")
        
        # Drought frequency
        drought_freq = results.get('drought_frequency', 'N/A')
        print(f"🏜️  Drought Frequency: {drought_freq}")
        if drought_freq == 0.25:
            print("   ⚠️  SUSPICIOUS: Drought frequency = 0.25 (exactly 1/4 - suspiciously round)")
        
        # Check water scarcity data against raw files
        ws_file = f"suhi_analysis_output/water_scarcity/{city}_water_scarcity_assessment.json"
        if os.path.exists(ws_file):
            with open(ws_file, 'r') as f:
                ws_data = json.load(f)
            
            aridity = ws_data.get('aridity_index', 'N/A')
            precip = ws_data.get('precipitation_mm_year', 'N/A')
            print(f"   Water Data: Aridity {aridity}, Precipitation {precip}mm/year")
        else:
            print("   ❌ No water scarcity data file found")
    
    def check_percentile_normalization_issues(self):
        """Check if percentile normalization is causing suspicious values"""
        print(f"\n{'='*60}")
        print("PERCENTILE NORMALIZATION DIAGNOSIS")
        print(f"{'='*60}")
        
        cache = self.service.data.get('cache', {})
        
        for metric, values in cache.items():
            if values:
                unique_values = set(values)
                print(f"\n📊 {metric.upper()}:")
                print(f"   Total values: {len(values)}")
                print(f"   Unique values: {len(unique_values)}")
                print(f"   Range: {min(values):.3f} - {max(values):.3f}")
                
                # Check for suspicious patterns
                if len(unique_values) < len(values) / 2:
                    print("   ⚠️  SUSPICIOUS: Many duplicate values - possible data quality issue")
                
                # Check for extreme clustering
                sorted_vals = sorted(values)
                if len(sorted_vals) > 1:
                    q1 = sorted_vals[len(sorted_vals)//4]
                    q3 = sorted_vals[3*len(sorted_vals)//4]
                    if q1 == q3:
                        print("   ⚠️  SUSPICIOUS: Values highly clustered - may cause poor percentile discrimination")
    
    def validate_against_raw_data(self, city):
        """Validate calculated values against raw data files"""
        print(f"\n{'='*60}")
        print(f"RAW DATA VALIDATION FOR {city}")
        print(f"{'='*60}")
        
        # Check all raw data files
        data_components = [
            ("temperature", f"suhi_analysis_output/temperature/{city}_temperature_metrics.json"),
            ("suhi", f"suhi_analysis_output/suhi/{city}_suhi_metrics.json"),
            ("lulc", f"suhi_analysis_output/lulc/{city}_lulc_metrics.json"),
            ("air_quality", f"suhi_analysis_output/air_quality/{city}_air_quality_metrics.json"),
            ("water_scarcity", f"suhi_analysis_output/water_scarcity/{city}_water_scarcity_assessment.json"),
            ("nightlight", f"suhi_analysis_output/nightlight/{city}_nightlight_metrics.json"),
            ("social", f"suhi_analysis_output/social_sector/{city}_social_sector.json")
        ]
        
        for component, filepath in data_components:
            print(f"\n🔍 {component.upper()}:")
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    print(f"   ✅ File exists, size: {len(json.dumps(data))} characters")
                    
                    # Check for suspicious patterns in the data
                    self._check_data_quality(component, data)
                    
                except Exception as e:
                    print(f"   ❌ Error reading file: {e}")
            else:
                print(f"   ❌ File not found: {filepath}")
    
    def _check_data_quality(self, component, data):
        """Check data quality for potential issues"""
        
        if component == "temperature":
            summer_temp = data.get('summer_season_summary', {}).get('mean_LST_C')
            if summer_temp and summer_temp > 50:
                print(f"   ⚠️  Summer temperature {summer_temp}°C seems very high")
            elif summer_temp and summer_temp < 0:
                print(f"   ⚠️  Summer temperature {summer_temp}°C seems very low")
        
        elif component == "air_quality":
            if 'metrics' in data and 'annual' in data['metrics']:
                pm25 = data['metrics']['annual'].get('PM2_5')
                if pm25 and pm25 > 100:
                    print(f"   ⚠️  PM2.5 {pm25} μg/m³ is extremely high")
                elif pm25 and pm25 < 1:
                    print(f"   ⚠️  PM2.5 {pm25} μg/m³ seems unrealistically low")
        
        elif component == "water_scarcity":
            aridity = data.get('aridity_index')
            if aridity == 0:
                print(f"   ⚠️  Aridity index = 0 (no aridity - suspicious)")
            elif aridity and aridity > 2:
                print(f"   ⚠️  Aridity index {aridity} seems very high")

def main():
    """Main diagnostic function"""
    diagnostic = SuspiciousValuesDiagnostic()
    
    # Run comprehensive diagnosis
    diagnostic.diagnose_all_suspicious_values()
    
    # Check percentile normalization
    diagnostic.check_percentile_normalization_issues()
    
    # Validate against raw data for the three suspicious cities
    for city in ["Tashkent", "Nukus", "Andijan"]:
        diagnostic.validate_against_raw_data(city)
    
    print(f"\n{'='*80}")
    print("DIAGNOSTIC COMPLETE")
    print("="*80)
    print("🔍 SUMMARY OF FINDINGS:")
    print("• Check for values of exactly 0.0, 0.5, 1.0 - possible defaults/fallbacks")
    print("• Air quality hazard = 1.0 everywhere suggests data processing issue")
    print("• Surface water change = 0.0 everywhere is unrealistic")
    print("• Water system capacity = 0.5 everywhere suggests hardcoded default")
    print("• Bio trend vulnerability extreme values (0.0 or 1.0) need investigation")
    print("• Review percentile normalization for clustering issues")

if __name__ == "__main__":
    main()
