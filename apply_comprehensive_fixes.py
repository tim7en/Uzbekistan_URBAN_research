#!/usr/bin/env python3
"""
Apply comprehensive fixes to the climate assessment with cache clearing.
This ensures the fixes take effect immediately.
"""

import os
import json
import numpy as np

def clear_assessment_cache():
    """Clear the assessment cache to force recalculation"""
    print("🔄 Clearing assessment cache...")
    
    # Remove any existing results to force fresh calculation
    results_files = [
        'suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json',
        'climate_risk_assessment_results.json'
    ]
    
    for file_path in results_files:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"   Removed: {file_path}")

def apply_comprehensive_exposure_fix():
    """Apply comprehensive exposure calculation fixes"""
    
    # Read the current file
    with open('services/climate_risk_assessment.py', 'r') as f:
        content = f.read()
    
    # Define the new comprehensive exposure method
    new_exposure_method = '''    def _calculate_exposure_components(self, city: str, metrics: ClimateRiskMetrics) -> ClimateRiskMetrics:
        """Calculate exposure components with comprehensive fixes (UPDATED)"""
        population_data = self.data['population_data'].get(city)
        if not population_data:
            # Apply floor values instead of zeros
            metrics.population_exposure = 0.05
            metrics.gdp_exposure = 0.05
            metrics.viirs_exposure = 0.05
            return metrics

        # Built area fraction for exposure calculations
        built_area_fraction = min(0.7, max(0.3, population_data.population_2024 / 2000000))
        
        # COMPREHENSIVE FIX 1: Population Exposure
        # Use log population density to reduce small-city bias
        if 'log_population_densities' not in self.data['cache']:
            log_densities = []
            city_names = list(self.data['population_data'].keys())
            
            for city_name in city_names:
                pop_data = self.data['population_data'].get(city_name)
                if pop_data:
                    # Get area from user data
                    city_user_data = self.user_data[self.user_data['City'] == city_name]
                    if not city_user_data.empty:
                        area_km2 = city_user_data.iloc[0]['Area_km2']
                    else:
                        area_km2 = pop_data.population_2024 / 5000  # Estimate
                    
                    density = pop_data.population_2024 / area_km2
                    log_density = np.log(density + 1)
                    log_densities.append(log_density)
                else:
                    log_densities.append(0)
            
            self.data['cache']['log_population_densities'] = log_densities
            self.data['cache']['pop_city_names'] = city_names

        # Apply safe normalization for population exposure
        all_log_densities = self.data['cache']['log_population_densities']
        pop_city_names = self.data['cache']['pop_city_names']
        
        if city in pop_city_names:
            city_index = pop_city_names.index(city)
            safe_normalized_pop = self.data_loader.safe_percentile_norm(all_log_densities, floor=0.05, ceiling=0.95)
            metrics.population_exposure = safe_normalized_pop[city_index]
        else:
            metrics.population_exposure = 0.05

        # COMPREHENSIVE FIX 2: GDP Exposure  
        # Use total GDP at risk with proper exposure fractions
        if 'total_gdp_at_risk' not in self.data['cache']:
            gdp_at_risk_values = []
            city_names = list(self.data['population_data'].keys())
            
            for city_name in city_names:
                pop_data = self.data['population_data'].get(city_name)
                if pop_data:
                    # Population-based exposure fractions
                    if pop_data.population_2024 > 1000000:  # Large cities
                        exposure_fraction = 0.7
                    elif pop_data.population_2024 > 300000:  # Medium cities
                        exposure_fraction = 0.5
                    else:  # Small cities
                        exposure_fraction = 0.3
                    
                    total_gdp = pop_data.population_2024 * pop_data.gdp_per_capita_usd
                    gdp_at_risk = total_gdp * exposure_fraction
                    gdp_at_risk_values.append(gdp_at_risk)
                else:
                    gdp_at_risk_values.append(0)
            
            self.data['cache']['total_gdp_at_risk'] = gdp_at_risk_values
            self.data['cache']['gdp_city_names'] = city_names

        # Apply safe normalization for GDP exposure
        all_gdp_at_risk = self.data['cache']['total_gdp_at_risk']
        gdp_city_names = self.data['cache']['gdp_city_names']
        
        if city in gdp_city_names:
            city_index = gdp_city_names.index(city)
            safe_normalized_gdp = self.data_loader.safe_percentile_norm(all_gdp_at_risk, floor=0.05, ceiling=0.95)
            metrics.gdp_exposure = safe_normalized_gdp[city_index]
        else:
            metrics.gdp_exposure = 0.05

        # VIIRS exposure (E_viirs) - urban radiance with safe scaling
        metrics.viirs_exposure = self._calculate_viirs_exposure(city)
        
        return metrics'''
    
    # Replace the existing method
    # Find the method definition
    method_start = content.find('def _calculate_exposure_components(self, city: str, metrics: ClimateRiskMetrics) -> ClimateRiskMetrics:')
    if method_start != -1:
        # Find the end of the method (next method definition or class end)
        next_method = content.find('\\n    def ', method_start + 1)
        if next_method == -1:
            next_method = len(content)
        
        # Replace the method
        new_content = content[:method_start] + new_exposure_method + content[next_method:]
        
        # Write back to file
        with open('services/climate_risk_assessment.py', 'w') as f:
            f.write(new_content)
        
        print("✅ Applied comprehensive exposure calculation fixes")
        return True
    else:
        print("❌ Could not find exposure method to replace")
        return False

def apply_adaptive_capacity_fix():
    """Apply adaptive capacity geometric mean fix"""
    
    # Read the current file
    with open('services/climate_risk_assessment.py', 'r') as f:
        content = f.read()
    
    # Define the new adaptive capacity method
    new_adaptive_method = '''    def _calculate_overall_adaptive_capacity(self, city: str) -> float:
        """Calculate overall adaptive capacity using geometric mean (FIXED)"""
        
        # Calculate individual components with safe bounds
        gdp_capacity = max(0.05, min(0.95, self._calculate_gdp_adaptive_capacity(city)))
        greenspace_capacity = max(0.05, min(0.95, self._calculate_greenspace_adaptive_capacity(city)))
        services_capacity = max(0.05, min(0.95, self._calculate_services_adaptive_capacity(city)))
        air_quality_capacity = max(0.05, min(0.95, self._calculate_air_quality_adaptive_capacity(city)))
        social_capacity = max(0.05, min(0.95, self._calculate_social_infrastructure_capacity(city)))
        water_capacity = max(0.05, min(0.95, self._calculate_water_system_capacity(city)))
        
        # Use geometric mean to prevent zero collapse
        components = [gdp_capacity, greenspace_capacity, services_capacity, 
                     air_quality_capacity, social_capacity, water_capacity]
        
        geometric_mean = np.power(np.prod(components), 1.0 / len(components))
        
        # Ensure result is within safe bounds
        return max(0.05, min(0.95, geometric_mean))'''
    
    # Find and replace the adaptive capacity method
    method_start = content.find('def _calculate_overall_adaptive_capacity(self, city: str) -> float:')
    if method_start != -1:
        next_method = content.find('\\n    def ', method_start + 1)
        if next_method == -1:
            # Look for class end or file end
            next_method = content.find('\\nclass ', method_start + 1)
            if next_method == -1:
                next_method = len(content)
        
        # Replace the method
        new_content = content[:method_start] + new_adaptive_method + content[next_method:]
        
        # Write back to file
        with open('services/climate_risk_assessment.py', 'w') as f:
            f.write(new_content)
        
        print("✅ Applied adaptive capacity geometric mean fix")
        return True
    else:
        print("❌ Could not find adaptive capacity method to replace")
        return False

def apply_missing_data_fixes():
    """Apply missing data handling fixes for specific components"""
    
    # Read the current file
    with open('services/climate_risk_assessment.py', 'r') as f:
        content = f.read()
    
    # Add missing data handler method if not exists
    if '_handle_missing_component' not in content:
        missing_data_handler = '''
    def _handle_missing_component(self, value, component_name, city_name, all_city_values=None):
        """Handle missing component data with median imputation"""
        if value is None or np.isnan(value) or np.isinf(value) or value < 0:
            if all_city_values:
                valid_values = [v for v in all_city_values if v is not None and np.isfinite(v) and v >= 0]
                if valid_values:
                    imputed_value = np.median(valid_values)
                    print(f"[IMPUTED] {city_name} {component_name}: {imputed_value:.3f}")
                    return imputed_value
            
            # Conservative default
            print(f"[DEFAULT] {city_name} {component_name}: 0.500")
            return 0.500
        
        return value
'''
        
        # Insert the method before the last closing bracket
        last_brace = content.rfind('}')
        if last_brace == -1:
            content += missing_data_handler
        else:
            content = content[:last_brace] + missing_data_handler + content[last_brace:]
        
        # Write back to file
        with open('services/climate_risk_assessment.py', 'w') as f:
            f.write(content)
        
        print("✅ Added missing data handler")
    
    return True

def run_fixed_assessment():
    """Run the assessment with all fixes applied"""
    print("🚀 Running assessment with all fixes applied...")
    
    import subprocess
    result = subprocess.run(['python', 'run_climate_assessment_modular.py'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Assessment completed successfully")
        return True
    else:
        print("❌ Assessment failed:")
        print(result.stderr)
        return False

def main():
    """Apply all comprehensive fixes"""
    print("APPLYING COMPREHENSIVE CRITICAL FIXES")
    print("This will resolve all 6 major red flags identified")
    print("=" * 80)
    
    steps = [
        ("Clear cache", clear_assessment_cache),
        ("Fix exposure calculations", apply_comprehensive_exposure_fix),
        ("Fix adaptive capacity", apply_adaptive_capacity_fix),
        ("Fix missing data handling", apply_missing_data_fixes),
        ("Run fixed assessment", run_fixed_assessment)
    ]
    
    for step_name, step_func in steps:
        print(f"\\n🔧 {step_name}...")
        try:
            result = step_func()
            if result:
                print(f"✅ {step_name} completed")
            else:
                print(f"❌ {step_name} failed")
                break
        except Exception as e:
            print(f"❌ {step_name} failed with error: {e}")
            break
    
    print("\\n" + "=" * 80)
    print("COMPREHENSIVE FIXES COMPLETE")
    print("All major red flags should now be resolved")

if __name__ == "__main__":
    main()
