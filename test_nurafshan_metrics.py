#!/usr/bin/env python3
"""
Comprehensive test of all metrics used for Nurafshan city climate risk analysis.
Investigates why exposure score is 0 and validates all data components.
"""

import json
import os
from pathlib import Path
import pandas as pd
from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService

class NurafshonMetricsAnalyzer:
    def __init__(self):
        self.loader = ClimateDataLoader("suhi_analysis_output")
        self.service = IPCCRiskAssessmentService(self.loader)
        self.city = "Nurafshon"
        
    def analyze_all_components(self):
        """Comprehensive analysis of all data components for Nurafshan"""
        print("="*80)
        print(f"COMPREHENSIVE NURAFSHAN METRICS ANALYSIS")
        print("="*80)
        
        # 1. Basic city information
        self._analyze_basic_info()
        
        # 2. Temperature data
        self._analyze_temperature_data()
        
        # 3. SUHI data
        self._analyze_suhi_data()
        
        # 4. LULC data
        self._analyze_lulc_data()
        
        # 5. Spatial relationships
        self._analyze_spatial_data()
        
        # 6. Nightlights
        self._analyze_nightlights_data()
        
        # 7. Air quality
        self._analyze_air_quality_data()
        
        # 8. Water scarcity
        self._analyze_water_scarcity_data()
        
        # 9. Social infrastructure
        self._analyze_social_data()
        
        # 10. Run full assessment and break down scores
        self._analyze_assessment_breakdown()
        
    def _analyze_basic_info(self):
        """Analyze basic city information"""
        print("\n1. BASIC CITY INFORMATION:")
        print("-" * 40)
        
        # Check user population data
        pop_file = "ExternalData/uzbekistan_pop_grp.xlsx"
        if os.path.exists(pop_file):
            df = pd.read_excel(pop_file)
            nurafshan_data = df[df['City'] == 'Nurafshon']
            if not nurafshan_data.empty:
                row = nurafshan_data.iloc[0]
                print(f"✅ Population: {row['Population']:,.0f}")
                print(f"✅ GDP per capita: ${row['GDP_per_capita']:,.0f}")
                print(f"✅ Area: {row['Area_km2']:.1f} km²")
            else:
                print("❌ No data found for Nurafshon in population file")
        else:
            print("❌ Population file not found")
            
    def _analyze_temperature_data(self):
        """Analyze temperature data"""
        print("\n2. TEMPERATURE DATA:")
        print("-" * 40)
        
        temp_file = f"suhi_analysis_output/temperature/{self.city}_temperature_metrics.json"
        if os.path.exists(temp_file):
            with open(temp_file, 'r') as f:
                data = json.load(f)
            print(f"✅ Temperature file exists")
            print(f"📊 Summer LST mean: {data.get('summer_season_summary', {}).get('mean_LST_C', 'N/A')}")
            print(f"📊 Winter LST mean: {data.get('winter_season_summary', {}).get('mean_LST_C', 'N/A')}")
            print(f"📊 Annual mean: {data.get('annual_summary', {}).get('mean_LST_C', 'N/A')}")
            print(f"📊 Heat wave frequency: {data.get('extreme_events', {}).get('heat_wave_frequency', 'N/A')}")
        else:
            print(f"❌ Temperature file not found: {temp_file}")
            
    def _analyze_suhi_data(self):
        """Analyze SUHI data"""
        print("\n3. SUHI DATA:")
        print("-" * 40)
        
        suhi_file = f"suhi_analysis_output/suhi/{self.city}_suhi_metrics.json"
        if os.path.exists(suhi_file):
            with open(suhi_file, 'r') as f:
                data = json.load(f)
            print(f"✅ SUHI file exists")
            print(f"📊 Summer SUHI intensity: {data.get('summer_season_summary', {}).get('suhi_intensity', 'N/A')}")
            print(f"📊 Winter SUHI intensity: {data.get('winter_season_summary', {}).get('suhi_intensity', 'N/A')}")
            print(f"📊 Annual SUHI intensity: {data.get('annual_summary', {}).get('suhi_intensity', 'N/A')}")
        else:
            print(f"❌ SUHI file not found: {suhi_file}")
            
    def _analyze_lulc_data(self):
        """Analyze LULC data"""
        print("\n4. LULC DATA:")
        print("-" * 40)
        
        lulc_file = f"suhi_analysis_output/lulc/{self.city}_lulc_metrics.json"
        if os.path.exists(lulc_file):
            with open(lulc_file, 'r') as f:
                data = json.load(f)
            print(f"✅ LULC file exists")
            print(f"📊 Urban area %: {data.get('class_percentages', {}).get('Urban', 'N/A')}")
            print(f"📊 Vegetation %: {data.get('class_percentages', {}).get('Vegetation', 'N/A')}")
            print(f"📊 Water %: {data.get('class_percentages', {}).get('Water', 'N/A')}")
            print(f"📊 Bare soil %: {data.get('class_percentages', {}).get('Bare_Soil', 'N/A')}")
        else:
            print(f"❌ LULC file not found: {lulc_file}")
            
    def _analyze_spatial_data(self):
        """Analyze spatial relationships data"""
        print("\n5. SPATIAL RELATIONSHIPS DATA:")
        print("-" * 40)
        
        spatial_file = "suhi_analysis_output/spatial_relationships/spatial_relationships_analysis.json"
        if os.path.exists(spatial_file):
            with open(spatial_file, 'r') as f:
                data = json.load(f)
            if self.city in data:
                city_data = data[self.city]
                print(f"✅ Spatial data exists for {self.city}")
                print(f"📊 Population density: {city_data.get('population_density_per_km2', 'N/A')}")
                print(f"📊 Distance to coast: {city_data.get('distance_to_coast_km', 'N/A')} km")
                print(f"📊 Elevation: {city_data.get('elevation_m', 'N/A')} m")
            else:
                print(f"❌ No spatial data found for {self.city}")
        else:
            print(f"❌ Spatial file not found: {spatial_file}")
            
    def _analyze_nightlights_data(self):
        """Analyze nightlights data"""
        print("\n6. NIGHTLIGHTS DATA:")
        print("-" * 40)
        
        nl_file = f"suhi_analysis_output/nightlight/{self.city}_nightlight_metrics.json"
        if os.path.exists(nl_file):
            with open(nl_file, 'r') as f:
                data = json.load(f)
            print(f"✅ Nightlights file exists")
            print(f"📊 Mean nightlight intensity: {data.get('mean_nightlight', 'N/A')}")
            print(f"📊 Max nightlight intensity: {data.get('max_nightlight', 'N/A')}")
            print(f"📊 Percentage lit area: {data.get('percentage_lit_area', 'N/A')}")
        else:
            print(f"❌ Nightlights file not found: {nl_file}")
            
    def _analyze_air_quality_data(self):
        """Analyze air quality data"""
        print("\n7. AIR QUALITY DATA:")
        print("-" * 40)
        
        aq_file = f"suhi_analysis_output/air_quality/{self.city}_air_quality_metrics.json"
        if os.path.exists(aq_file):
            with open(aq_file, 'r') as f:
                data = json.load(f)
            print(f"✅ Air quality file exists")
            # Navigate the nested structure
            if 'metrics' in data and 'annual' in data['metrics']:
                annual = data['metrics']['annual']
                print(f"📊 PM2.5: {annual.get('PM2_5', 'N/A')}")
                print(f"📊 NO2: {annual.get('NO2', 'N/A')}")
                print(f"📊 SO2: {annual.get('SO2', 'N/A')}")
                print(f"📊 CO: {annual.get('CO', 'N/A')}")
            else:
                print(f"📊 Data structure: {list(data.keys())}")
        else:
            print(f"❌ Air quality file not found: {aq_file}")
            
    def _analyze_water_scarcity_data(self):
        """Analyze water scarcity data"""
        print("\n8. WATER SCARCITY DATA:")
        print("-" * 40)
        
        ws_file = f"suhi_analysis_output/water_scarcity/{self.city}_water_scarcity_assessment.json"
        if os.path.exists(ws_file):
            with open(ws_file, 'r') as f:
                data = json.load(f)
            print(f"✅ Water scarcity file exists")
            print(f"📊 Aridity index: {data.get('aridity_index', 'N/A')}")
            print(f"📊 Water stress: {data.get('water_stress_index', 'N/A')}")
            print(f"📊 Precipitation: {data.get('precipitation_mm_year', 'N/A')} mm/year")
            print(f"📊 Evapotranspiration: {data.get('evapotranspiration_mm_year', 'N/A')} mm/year")
        else:
            print(f"❌ Water scarcity file not found: {ws_file}")
            
    def _analyze_social_data(self):
        """Analyze social infrastructure data"""
        print("\n9. SOCIAL INFRASTRUCTURE DATA:")
        print("-" * 40)
        
        social_file = f"suhi_analysis_output/social_sector/{self.city}_social_sector.json"
        if os.path.exists(social_file):
            with open(social_file, 'r') as f:
                data = json.load(f)
            print(f"✅ Social data file exists")
            print(f"📊 Schools: {data.get('infrastructure_counts', {}).get('schools', 'N/A')}")
            print(f"📊 Hospitals: {data.get('infrastructure_counts', {}).get('hospitals', 'N/A')}")
            print(f"📊 Kindergartens: {data.get('infrastructure_counts', {}).get('kindergartens', 'N/A')}")
            print(f"📊 Schools per 1000: {data.get('per_capita_metrics', {}).get('schools_per_1000', 'N/A')}")
            print(f"📊 Hospitals per 1000: {data.get('per_capita_metrics', {}).get('hospitals_per_1000', 'N/A')}")
        else:
            print(f"❌ Social data file not found: {social_file}")
            
    def _analyze_assessment_breakdown(self):
        """Run full assessment and break down the scores"""
        print("\n10. CLIMATE RISK ASSESSMENT BREAKDOWN:")
        print("-" * 50)
        
        try:
            # Run assessment
            result = self.service.assess_city_climate_risk(self.city)
            
            print(f"🎯 FINAL SCORES:")
            print(f"   Hazard Score: {result['hazard_score']:.3f}")
            print(f"   Exposure Score: {result['exposure_score']:.3f} ⚠️")
            print(f"   Vulnerability Score: {result['vulnerability_score']:.3f}")
            print(f"   Adaptive Capacity Score: {result['adaptive_capacity_score']:.3f}")
            print(f"   Overall Risk Score: {result['risk_score']:.3f}")
            
            # Try to get detailed breakdown if available
            if 'components' in result:
                print(f"\n📊 COMPONENT BREAKDOWN:")
                for component, value in result['components'].items():
                    print(f"   {component}: {value}")
                    
        except Exception as e:
            print(f"❌ Error running assessment: {e}")
            
    def investigate_exposure_zero(self):
        """Specifically investigate why exposure score is 0"""
        print("\n" + "="*80)
        print("INVESTIGATING EXPOSURE SCORE = 0")
        print("="*80)
        
        # Load data directly and check exposure components
        try:
            # Get the loader data
            print("Loading data for exposure calculation...")
            
            # Check each component that goes into exposure
            print("\n🔍 EXPOSURE COMPONENTS CHECK:")
            
            # Population density (from spatial data)
            spatial_file = "suhi_analysis_output/spatial_relationships/spatial_relationships_analysis.json"
            if os.path.exists(spatial_file):
                with open(spatial_file, 'r') as f:
                    spatial_data = json.load(f)
                if self.city in spatial_data:
                    pop_density = spatial_data[self.city].get('population_density_per_km2')
                    print(f"   Population density: {pop_density} people/km²")
                else:
                    print(f"   ❌ No spatial data for {self.city}")
            
            # Urban area percentage (from LULC)
            lulc_file = f"suhi_analysis_output/lulc/{self.city}_lulc_metrics.json"
            if os.path.exists(lulc_file):
                with open(lulc_file, 'r') as f:
                    lulc_data = json.load(f)
                urban_pct = lulc_data.get('class_percentages', {}).get('Urban')
                print(f"   Urban area percentage: {urban_pct}%")
            
            # Economic activity (from nightlights)
            nl_file = f"suhi_analysis_output/nightlight/{self.city}_nightlight_metrics.json"
            if os.path.exists(nl_file):
                with open(nl_file, 'r') as f:
                    nl_data = json.load(f)
                nl_intensity = nl_data.get('mean_nightlight')
                print(f"   Nightlight intensity: {nl_intensity}")
                
            # Check if this combination leads to 0 exposure
            print(f"\n🧮 MANUAL EXPOSURE CALCULATION:")
            print(f"   This requires checking the exact formula in climate_risk_assessment.py")
            
        except Exception as e:
            print(f"❌ Error investigating exposure: {e}")

def main():
    """Main function to run the comprehensive analysis"""
    analyzer = NurafshonMetricsAnalyzer()
    
    # Run comprehensive analysis
    analyzer.analyze_all_components()
    
    # Investigate exposure specifically
    analyzer.investigate_exposure_zero()
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
