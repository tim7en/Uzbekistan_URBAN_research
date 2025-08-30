#!/usr/bin/env python3
"""
DEBUG CLIMATE ASSESSMENT EXECUTION
==================================

This script debugs the climate assessment modular execution to identify
issues with result generation and ensure data accuracy.
"""

import traceback
import json
from pathlib import Path
from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService

def debug_climate_assessment():
    """Debug the climate assessment execution step by step"""
    
    print("=" * 80)
    print("🔍 DEBUGGING CLIMATE ASSESSMENT EXECUTION")
    print("=" * 80)
    
    try:
        # Step 1: Initialize data loader
        print("\n1️⃣ INITIALIZING DATA LOADER...")
        repo_root = Path(__file__).resolve().parent
        candidates = [
            repo_root / "suhi_analysis_output",
            repo_root / "reports",
            Path.cwd() / "suhi_analysis_output",
            Path.cwd() / "reports",
            repo_root
        ]

        base_path = None
        for c in candidates:
            if c.exists():
                base_path = c
                break

        if base_path is None:
            base_path = repo_root
            print(f"⚠️ Warning: using repo root: {base_path}")
        else:
            print(f"✅ Using data base_path: {base_path}")

        data_loader = ClimateDataLoader(str(base_path))
        print("✅ Data loader initialized successfully")
        
        # Step 2: Initialize risk assessor
        print("\n2️⃣ INITIALIZING RISK ASSESSOR...")
        risk_assessor = IPCCRiskAssessmentService(data_loader)
        print("✅ Risk assessor initialized successfully")
        
        # Step 3: Check data availability
        print("\n3️⃣ CHECKING DATA AVAILABILITY...")
        data = risk_assessor.data
        
        print(f"   📊 Population data cities: {len(data.get('population_data', {}))}")
        print(f"   🌡️ Temperature data cities: {len(data.get('temperature_data', {}))}")
        print(f"   🌿 Vegetation data cities: {len(data.get('vegetation_data', {}))}")
        print(f"   🏙️ LULC data entries: {len(data.get('lulc_data', []))}")
        print(f"   🌙 Nightlights data entries: {len(data.get('nightlights_data', []))}")
        print(f"   🗺️ Spatial data cities: {len(data.get('spatial_data', {}).get('per_year', {}))}")
        print(f"   💨 Air quality data cities: {len(data.get('air_quality_data', {}))}")
        print(f"   💧 Water scarcity data: {hasattr(risk_assessor, 'water_scarcity_data')}")
        
        # Step 4: Test single city assessment
        print("\n4️⃣ TESTING SINGLE CITY ASSESSMENT...")
        if 'population_data' in data and data['population_data']:
            test_city = list(data['population_data'].keys())[0]
            print(f"   Testing city: {test_city}")
            
            try:
                metrics = risk_assessor.assess_city_climate_risk(test_city)
                print(f"   ✅ Assessment successful for {test_city}")
                print(f"      Risk Score: {metrics.overall_risk_score:.6f}")
                print(f"      Hazard: {metrics.hazard_score:.3f}")
                print(f"      Exposure: {metrics.exposure_score:.3f}")
                print(f"      Vulnerability: {metrics.vulnerability_score:.3f}")
                print(f"      Adaptive Capacity: {metrics.adaptive_capacity_score:.3f}")
                
                # Check individual components
                print(f"\\n   🔍 COMPONENT BREAKDOWN:")
                print(f"      Heat Hazard: {metrics.heat_hazard:.6f}")
                print(f"      Dry Hazard: {metrics.dry_hazard:.6f}")
                print(f"      Dust Hazard: {metrics.dust_hazard:.6f}")
                print(f"      Pluvial Hazard: {metrics.pluvial_hazard:.6f}")
                print(f"      Air Quality Hazard: {metrics.air_quality_hazard:.6f}")
                
                print(f"\\n      Population Exposure: {metrics.population_exposure:.6f}")
                print(f"      GDP Exposure: {metrics.gdp_exposure:.6f}")
                print(f"      VIIRS Exposure: {metrics.viirs_exposure:.6f}")
                
            except Exception as e:
                print(f"   ❌ Error assessing {test_city}: {str(e)}")
                traceback.print_exc()
        else:
            print("   ❌ No population data available for testing")
        
        # Step 5: Test all cities assessment
        print("\n5️⃣ TESTING ALL CITIES ASSESSMENT...")
        try:
            all_results = risk_assessor.assess_all_cities()
            print(f"   ✅ Assessment completed for {len(all_results)} cities")
            
            # Verify results quality
            risk_scores = [metrics.overall_risk_score for metrics in all_results.values()]
            print(f"   📊 Risk score range: {min(risk_scores):.6f} - {max(risk_scores):.6f}")
            
            # Check for suspicious patterns
            zero_risks = sum(1 for r in risk_scores if r == 0.0)
            identical_risks = len(set(risk_scores))
            
            if zero_risks > 0:
                print(f"   ⚠️ Warning: {zero_risks} cities have zero risk scores")
            
            if identical_risks < len(risk_scores) * 0.8:
                print(f"   ⚠️ Warning: Only {identical_risks} unique risk scores for {len(risk_scores)} cities")
            else:
                print(f"   ✅ Good risk score diversity: {identical_risks} unique scores")
                
        except Exception as e:
            print(f"   ❌ Error in all cities assessment: {str(e)}")
            traceback.print_exc()
            return
        
        # Step 6: Verify data integrity
        print("\n6️⃣ VERIFYING RESULT DATA INTEGRITY...")
        
        # Check for missing or invalid data
        issues = []
        for city, metrics in all_results.items():
            if metrics.overall_risk_score < 0 or metrics.overall_risk_score > 1:
                issues.append(f"{city}: Risk score out of bounds ({metrics.overall_risk_score})")
            
            if metrics.adaptive_capacity_score < 0 or metrics.adaptive_capacity_score > 1:
                issues.append(f"{city}: Adaptive capacity out of bounds ({metrics.adaptive_capacity_score})")
            
            # Check for NaN values
            if str(metrics.overall_risk_score) == 'nan':
                issues.append(f"{city}: Risk score is NaN")
            
            # Check component scores
            components = [
                ('hazard', metrics.hazard_score),
                ('exposure', metrics.exposure_score),
                ('vulnerability', metrics.vulnerability_score)
            ]
            
            for comp_name, comp_value in components:
                if comp_value < 0 or comp_value > 1:
                    issues.append(f"{city}: {comp_name} score out of bounds ({comp_value})")
        
        if issues:
            print(f"   ❌ Found {len(issues)} data integrity issues:")
            for issue in issues[:10]:  # Show first 10
                print(f"      • {issue}")
            if len(issues) > 10:
                print(f"      ... and {len(issues) - 10} more issues")
        else:
            print("   ✅ All data integrity checks passed")
        
        # Step 7: Compare with previous results
        print("\n7️⃣ COMPARING WITH PREVIOUS RESULTS...")
        results_file = base_path / "climate_assessment" / "climate_risk_assessment_results.json"
        
        if results_file.exists():
            with open(results_file, 'r') as f:
                previous_results = json.load(f)
            
            # Compare city counts
            current_cities = set(all_results.keys())
            previous_cities = set(previous_results.keys())
            
            print(f"   Current cities: {len(current_cities)}")
            print(f"   Previous cities: {len(previous_cities)}")
            
            if current_cities == previous_cities:
                print("   ✅ Same cities in both assessments")
                
                # Compare risk scores
                risk_differences = []
                for city in current_cities:
                    current_risk = all_results[city].overall_risk_score
                    previous_risk = previous_results[city].get('overall_risk_score', 0)
                    diff = abs(current_risk - previous_risk)
                    risk_differences.append(diff)
                
                avg_diff = sum(risk_differences) / len(risk_differences)
                max_diff = max(risk_differences)
                
                print(f"   📊 Average risk score difference: {avg_diff:.6f}")
                print(f"   📊 Maximum risk score difference: {max_diff:.6f}")
                
                if avg_diff > 0.01:
                    print("   ⚠️ Significant differences detected - may indicate calculation changes")
                else:
                    print("   ✅ Risk scores are consistent with previous assessment")
                    
            else:
                missing = previous_cities - current_cities
                added = current_cities - previous_cities
                if missing:
                    print(f"   ⚠️ Missing cities: {missing}")
                if added:
                    print(f"   ⚠️ Added cities: {added}")
        else:
            print("   ℹ️ No previous results found for comparison")
        
        # Step 8: Save current results
        print("\n8️⃣ SAVING CURRENT RESULTS...")
        output_path = base_path / "climate_assessment"
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Convert to dictionary format
        results_dict = {}
        for city, metrics in all_results.items():
            results_dict[city] = {
                'city': metrics.city,
                'population': metrics.population,
                'gdp_per_capita_usd': metrics.gdp_per_capita_usd,
                'hazard_score': metrics.hazard_score,
                'exposure_score': metrics.exposure_score,
                'vulnerability_score': metrics.vulnerability_score,
                'adaptive_capacity_score': metrics.adaptive_capacity_score,
                'heat_hazard': metrics.heat_hazard,
                'dry_hazard': metrics.dry_hazard,
                'dust_hazard': metrics.dust_hazard,
                'pluvial_hazard': metrics.pluvial_hazard,
                'air_quality_hazard': metrics.air_quality_hazard,
                'population_exposure': metrics.population_exposure,
                'gdp_exposure': metrics.gdp_exposure,
                'viirs_exposure': metrics.viirs_exposure,
                'income_vulnerability': metrics.income_vulnerability,
                'veg_access_vulnerability': metrics.veg_access_vulnerability,
                'fragmentation_vulnerability': metrics.fragmentation_vulnerability,
                'bio_trend_vulnerability': metrics.bio_trend_vulnerability,
                'air_pollution_vulnerability': metrics.air_pollution_vulnerability,
                'water_access_vulnerability': metrics.water_access_vulnerability,
                'healthcare_access_vulnerability': metrics.healthcare_access_vulnerability,
                'education_access_vulnerability': metrics.education_access_vulnerability,
                'sanitation_vulnerability': metrics.sanitation_vulnerability,
                'building_age_vulnerability': metrics.building_age_vulnerability,
                'gdp_adaptive_capacity': metrics.gdp_adaptive_capacity,
                'greenspace_adaptive_capacity': metrics.greenspace_adaptive_capacity,
                'services_adaptive_capacity': metrics.services_adaptive_capacity,
                'air_quality_adaptive_capacity': metrics.air_quality_adaptive_capacity,
                'social_infrastructure_capacity': metrics.social_infrastructure_capacity,
                'water_system_capacity': metrics.water_system_capacity,
                'overall_risk_score': metrics.overall_risk_score,
                'adaptability_score': metrics.adaptability_score,
                'current_suhi_intensity': metrics.current_suhi_intensity,
                'temperature_trend': metrics.temperature_trend,
                'suhi_trend': metrics.suhi_trend,
                'built_area_percentage': metrics.built_area_percentage,
                'green_space_accessibility': metrics.green_space_accessibility,
                'economic_capacity': metrics.economic_capacity,
                'co_level': metrics.co_level,
                'no2_level': metrics.no2_level,
                'o3_level': metrics.o3_level,
                'so2_level': metrics.so2_level,
                'ch4_level': metrics.ch4_level,
                'aerosol_index': metrics.aerosol_index,
                'air_quality_trend': metrics.air_quality_trend,
                'health_risk_score': metrics.health_risk_score,
                'water_supply_risk': metrics.water_supply_risk,
                'water_demand_risk': metrics.water_demand_risk,
                'overall_water_scarcity_score': metrics.overall_water_scarcity_score,
                'water_scarcity_level': metrics.water_scarcity_level,
                'aridity_index': metrics.aridity_index,
                'climatic_water_deficit': metrics.climatic_water_deficit,
                'drought_frequency': metrics.drought_frequency,
                'surface_water_change': metrics.surface_water_change,
                'cropland_fraction': metrics.cropland_fraction
            }
        
        output_file = output_path / "climate_risk_assessment_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)
        
        print(f"   ✅ Results saved to: {output_file}")
        
        print("\n" + "=" * 80)
        print("🏆 CLIMATE ASSESSMENT DEBUG COMPLETE")
        print("=" * 80)
        
        if not issues:
            print("✅ All checks passed - assessment results are valid")
        else:
            print(f"⚠️ {len(issues)} issues found - review needed")
        
        return all_results
        
    except Exception as e:
        print(f"❌ Critical error in assessment: {str(e)}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    debug_climate_assessment()
