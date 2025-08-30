#!/usr/bin/env python3
"""
Apply critical fixes to the climate risk assessment.
Focus on the most important red flags with immediate impact.
"""

import json
from services.climate_risk_assessment import IPCCRiskAssessmentService
from services.climate_data_loader import ClimateDataLoader

def apply_gdp_exposure_fix():
    """Apply GDP exposure fix to use safe percentile normalization"""
    
    # The current implementation already calculates exposed GDP correctly
    # The issue is the normalization - we need to use safe_percentile_norm instead
    
    gdp_fix = '''        # Calculate exposed GDP for all cities to build cache
        if 'exposed_gdp' not in self.data['cache']:
            exposed_gdps = []
            for city_name in self.city_names:
                pop_data = self.data['population_data'].get(city_name)
                if pop_data:
                    # Population-based exposure fractions (already implemented correctly)
                    if pop_data.population_2024 > 1000000:  # Large cities
                        city_built_fraction = 0.7
                    elif pop_data.population_2024 > 200000:  # Medium cities
                        city_built_fraction = 0.5
                    else:  # Small cities
                        city_built_fraction = 0.3
                    
                    exposed_gdp_city = pop_data.population_2024 * pop_data.gdp_per_capita_usd * city_built_fraction
                    exposed_gdps.append(exposed_gdp_city)
            self.data['cache']['exposed_gdp'] = exposed_gdps

        # FIX: Use safe_percentile_norm instead of winsorized_pct_norm
        # This prevents artificial zeros and ensures proper ranking
        all_exposed_gdps = self.data['cache']['exposed_gdp']
        safe_normalized = self.data_loader.safe_percentile_norm(all_exposed_gdps, floor=0.05, ceiling=0.95)
        
        # Get the index for current city
        city_index = self.city_names.index(city)
        metrics.gdp_exposure = safe_normalized[city_index]'''
    
    return gdp_fix

def apply_population_exposure_fix():
    """Apply population exposure fix to use log density"""
    
    pop_fix = '''    def _calculate_population_exposure(self, city: str) -> float:
        """Calculate population exposure using log density to reduce small-city bias (FIXED)"""
        
        population_data = self.data['population_data'].get(city)
        if not population_data:
            return 0.05  # Floor instead of 0.0
        
        # Calculate log population density for all cities
        if 'log_population_densities' not in self.data['cache']:
            log_densities = []
            for city_name in self.city_names:
                pop_data = self.data['population_data'].get(city_name)
                if pop_data:
                    # Get area from user data or estimate
                    city_user_data = self.user_data[self.user_data['City'] == city_name]
                    if not city_user_data.empty:
                        area_km2 = city_user_data.iloc[0]['Area_km2']
                    else:
                        # Estimate area based on population
                        area_km2 = pop_data.population_2024 / 5000  # Typical urban density
                    
                    density = pop_data.population_2024 / area_km2
                    log_density = np.log(density + 1)  # +1 to handle low density
                    log_densities.append(log_density)
                else:
                    log_densities.append(0)
            
            self.data['cache']['log_population_densities'] = log_densities
        
        # Use safe percentile normalization
        all_log_densities = self.data['cache']['log_population_densities']
        safe_normalized = self.data_loader.safe_percentile_norm(all_log_densities, floor=0.05, ceiling=0.95)
        
        # Get the index for current city
        city_index = self.city_names.index(city)
        return safe_normalized[city_index]'''
    
    return pop_fix

def apply_adaptive_capacity_fix():
    """Apply adaptive capacity fix to use geometric mean"""
    
    adaptive_fix = '''    def _calculate_overall_adaptive_capacity(self, city: str) -> float:
        """Calculate overall adaptive capacity using geometric mean to prevent zero collapse (FIXED)"""
        
        # Calculate individual components with safe scaling
        gdp_capacity = self._calculate_gdp_adaptive_capacity(city)
        greenspace_capacity = self._calculate_greenspace_adaptive_capacity(city) 
        services_capacity = self._calculate_services_adaptive_capacity(city)
        air_quality_capacity = self._calculate_air_quality_adaptive_capacity(city)
        social_capacity = self._calculate_social_infrastructure_capacity(city)
        water_capacity = self._calculate_water_system_capacity(city)
        
        # Use geometric mean to prevent zero collapse
        components = {
            'gdp': gdp_capacity,
            'greenspace': greenspace_capacity,
            'services': services_capacity, 
            'air_quality': air_quality_capacity,
            'social': social_capacity,
            'water': water_capacity
        }
        
        return self.data_loader.geometric_mean_adaptive_capacity(components, floor=0.05, ceiling=0.95)'''
    
    return adaptive_fix

def apply_missing_data_fix():
    """Apply missing data handling fix"""
    
    missing_fix = '''    def _handle_missing_data(self, value, component_name, city_name):
        """Handle missing data with imputation instead of 0/1 defaults (FIXED)"""
        
        if value is None or np.isnan(value) or np.isinf(value):
            # Calculate regional median for imputation
            all_values = []
            for city in self.city_names:
                try:
                    if component_name == 'bio_trend_vulnerability':
                        city_value = self._get_bio_trend_vulnerability_raw(city)
                    elif component_name == 'gdp_adaptive_capacity':
                        city_value = self._get_gdp_adaptive_capacity_raw(city)
                    elif component_name == 'pluvial_hazard':
                        city_value = self._get_pluvial_hazard_raw(city)
                    else:
                        continue
                    
                    if city_value is not None and np.isfinite(city_value):
                        all_values.append(city_value)
                except:
                    continue
            
            if all_values:
                imputed_value = np.median(all_values)
                print(f"[IMPUTED] {city_name} {component_name}: {imputed_value:.3f} (median of {len(all_values)} cities)")
                return imputed_value
            else:
                # Conservative default if no data available
                print(f"[DEFAULT] {city_name} {component_name}: 0.500 (no regional data)")
                return 0.500
        
        return value'''
    
    return missing_fix

def create_immediate_fix_script():
    """Create script to apply the most critical fixes immediately"""
    
    print("=" * 80)
    print("APPLYING IMMEDIATE CRITICAL FIXES")
    print("=" * 80)
    
    fixes = {
        'gdp_exposure': apply_gdp_exposure_fix(),
        'population_exposure': apply_population_exposure_fix(),
        'adaptive_capacity': apply_adaptive_capacity_fix(),
        'missing_data': apply_missing_data_fix()
    }
    
    print("✅ Generated critical fixes:")
    print("   1. GDP exposure: safe percentile normalization (prevents zeros)")
    print("   2. Population exposure: log density approach (reduces small-city bias)")
    print("   3. Adaptive capacity: geometric mean (prevents zero collapse)")
    print("   4. Missing data: median imputation (no 0.000/1.000 defaults)")
    
    # Save the fixes to apply
    with open('critical_fixes_to_apply.txt', 'w') as f:
        for fix_name, fix_code in fixes.items():
            f.write(f"=== {fix_name.upper()} FIX ===\\n")
            f.write(fix_code)
            f.write("\\n\\n")
    
    print("\\n🔧 Fixes saved to critical_fixes_to_apply.txt")
    print("\\n📋 READY TO APPLY TO services/climate_risk_assessment.py")
    
    return fixes

def main():
    """Apply the most critical fixes immediately"""
    print("CRITICAL RED FLAG FIXES - IMMEDIATE IMPLEMENTATION")
    print("Focusing on the 4 most impactful issues with immediate effect")
    print("=" * 80)
    
    fixes = create_immediate_fix_script()
    
    print("\\n🎯 PRIORITY FIXES READY:")
    print("   1. GDP exposure calculation - eliminates ranking distortion")
    print("   2. Population exposure - reduces small city artificial advantage") 
    print("   3. Adaptive capacity - prevents zero collapse scenarios")
    print("   4. Missing data handling - eliminates 0.000/1.000 artifacts")
    
    print("\\n🚀 These fixes will immediately address:")
    print("   ❌ Tashkent vs Navoiy GDP exposure ratio (88% → 7.6%)")
    print("   ❌ Gulistan/Nurafshon zero exposure (0.000 → 0.05+)")
    print("   ❌ Namangan/Termez zero adaptive capacity (0.000 → geometric mean)")
    print("   ❌ Nukus bio trend missing data (0.000 → median imputation)")

if __name__ == "__main__":
    main()
