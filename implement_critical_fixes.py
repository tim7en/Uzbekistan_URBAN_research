#!/usr/bin/env python3
"""
CRITICAL BUG FIX IMPLEMENTATION
Fixes all 6 red flags identified in the climate assessment:
1. GDP exposure calculation (per capita → total GDP at risk)
2. Artificial zero exposure floors
3. Max-pegging prevention (winsorized scaling)
4. Missing data handling
5. Pluvial hazard methodology
6. Adaptive capacity calculations
"""

import numpy as np
import pandas as pd
from services.climate_data_loader import ClimateDataLoader

def implement_proper_scaling_functions():
    """Implement improved scaling functions with floor/ceiling protection"""
    
    # Add to climate_data_loader.py
    scaling_functions = '''
def safe_percentile_norm(values, floor=0.05, ceiling=0.95):
    """
    Safe percentile normalization with floor/ceiling protection.
    Prevents artificial zeros and ones that distort rankings.
    
    Args:
        values: array-like of values to normalize
        floor: minimum scaled value (default 0.05)
        ceiling: maximum scaled value (default 0.95)
    
    Returns:
        Array of normalized values in range [floor, ceiling]
    """
    values = np.array(values)
    
    # Handle NaN/inf values
    valid_mask = np.isfinite(values)
    if not np.any(valid_mask):
        return np.full_like(values, (floor + ceiling) / 2)
    
    # Calculate percentile ranks for valid values only
    valid_values = values[valid_mask]
    percentile_ranks = np.zeros_like(values, dtype=float)
    
    # Use scipy.stats.rankdata for proper percentile ranking
    from scipy.stats import rankdata
    ranks = rankdata(valid_values, method='average')
    percentile_ranks[valid_mask] = (ranks - 1) / (len(ranks) - 1) if len(ranks) > 1 else 0.5
    
    # Apply floor/ceiling scaling
    scaled_values = floor + (ceiling - floor) * percentile_ranks
    
    # Handle NaN values with median imputation
    if not np.all(valid_mask):
        median_value = np.median(scaled_values[valid_mask])
        scaled_values[~valid_mask] = median_value
    
    return scaled_values

def log_density_exposure(population, area_km2, floor=0.05, ceiling=0.95):
    """
    Calculate exposure based on log population density to reduce small-city bias.
    
    Args:
        population: Population count
        area_km2: Area in square kilometers
        floor: minimum scaled value
        ceiling: maximum scaled value
    
    Returns:
        Exposure score based on population density
    """
    # Calculate population density
    density = population / area_km2
    
    # Log transform to reduce skewness
    log_density = np.log(density + 1)  # +1 to handle zero density
    
    # Apply safe percentile normalization
    return safe_percentile_norm([log_density], floor, ceiling)[0]

def total_gdp_exposure(population_list, gdp_per_capita_list, exposure_fractions=None, floor=0.05, ceiling=0.95):
    """
    Calculate GDP exposure based on total GDP at risk, not per capita.
    
    Args:
        population_list: List of population counts
        gdp_per_capita_list: List of GDP per capita values
        exposure_fractions: List of exposure fractions (default: population-based)
        floor: minimum scaled value
        ceiling: maximum scaled value
    
    Returns:
        Array of GDP exposure scores
    """
    populations = np.array(population_list)
    gdp_per_capita = np.array(gdp_per_capita_list)
    
    # Calculate total GDP for each city
    total_gdp = populations * gdp_per_capita
    
    # Use population-based exposure fractions if not provided
    if exposure_fractions is None:
        # Large cities: 70%, Medium: 50%, Small: 30%
        exposure_fractions = []
        for pop in populations:
            if pop > 1000000:  # Large city
                exposure_fractions.append(0.70)
            elif pop > 200000:  # Medium city
                exposure_fractions.append(0.50)
            else:  # Small city
                exposure_fractions.append(0.30)
        exposure_fractions = np.array(exposure_fractions)
    
    # Calculate GDP at risk
    gdp_at_risk = total_gdp * exposure_fractions
    
    # Apply safe percentile normalization
    return safe_percentile_norm(gdp_at_risk, floor, ceiling)

def geometric_mean_adaptive_capacity(components_dict, floor=0.05, ceiling=0.95):
    """
    Calculate adaptive capacity using geometric mean to prevent zero collapse.
    
    Args:
        components_dict: Dictionary of adaptive capacity components
        floor: minimum component value before geometric mean
        ceiling: maximum component value
    
    Returns:
        Geometric mean adaptive capacity score
    """
    # Ensure all components are above floor to prevent zero collapse
    components = []
    for key, value in components_dict.items():
        # Floor individual components
        safe_value = max(value, floor)
        safe_value = min(safe_value, ceiling)
        components.append(safe_value)
    
    # Calculate geometric mean
    if len(components) == 0:
        return (floor + ceiling) / 2
    
    geometric_mean = np.power(np.prod(components), 1.0 / len(components))
    
    # Ensure result is within bounds
    return max(floor, min(ceiling, geometric_mean))
'''

    return scaling_functions

def implement_gdp_exposure_fix():
    """Fix GDP exposure calculation to use total GDP at risk"""
    
    gdp_fix = '''
    def _calculate_gdp_exposure(self, city_name):
        """Calculate GDP exposure based on total GDP at risk (FIXED)"""
        
        # Get all city data for proper scaling
        all_cities_data = []
        for city in self.city_names:
            city_data = self.user_data[self.user_data['City'] == city].iloc[0]
            pop = city_data['Population']
            gdp_pc = city_data['GDP_per_capita_USD']
            
            # Population-based exposure fractions
            if pop > 1000000:  # Large city
                exposure_fraction = 0.70
            elif pop > 200000:  # Medium city  
                exposure_fraction = 0.50
            else:  # Small city
                exposure_fraction = 0.30
            
            # Calculate total GDP at risk
            total_gdp = pop * gdp_pc
            gdp_at_risk = total_gdp * exposure_fraction
            
            all_cities_data.append({
                'city': city,
                'gdp_at_risk': gdp_at_risk
            })
        
        # Apply safe percentile normalization
        gdp_values = [d['gdp_at_risk'] for d in all_cities_data]
        normalized_gdp = self.safe_percentile_norm(gdp_values, floor=0.05, ceiling=0.95)
        
        # Return value for current city
        city_index = self.city_names.index(city_name)
        return normalized_gdp[city_index]
'''
    
    return gdp_fix

def implement_population_exposure_fix():
    """Fix population exposure to use log density and prevent zeros"""
    
    pop_fix = '''
    def _calculate_population_exposure(self, city_name):
        """Calculate population exposure using log density (FIXED)"""
        
        # Get all city data
        all_densities = []
        for city in self.city_names:
            city_data = self.user_data[self.user_data['City'] == city].iloc[0]
            pop = city_data['Population'] 
            area = city_data['Area_km2']
            density = pop / area
            
            # Log transform to reduce skewness
            log_density = np.log(density + 1)
            all_densities.append(log_density)
        
        # Apply safe percentile normalization
        normalized_density = self.safe_percentile_norm(all_densities, floor=0.05, ceiling=0.95)
        
        # Return value for current city
        city_index = self.city_names.index(city_name)
        return normalized_density[city_index]
'''
    
    return pop_fix

def implement_pluvial_hazard_fix():
    """Fix pluvial hazard calculation with proper winsorization"""
    
    pluvial_fix = '''
    def _calculate_pluvial_hazard(self, city_name):
        """Calculate pluvial (urban flooding) hazard with winsorization (FIXED)"""
        
        # Get precipitation and imperviousness data
        precip_data = self.get_city_data(city_name, 'temperature')  # Contains precipitation
        lulc_data = self.get_city_data(city_name, 'lulc')
        
        # Extract extreme precipitation metrics (P95, P99)
        if precip_data is not None and 'extreme_precip_intensity' in precip_data:
            extreme_precip = precip_data['extreme_precip_intensity']
        else:
            # Fallback calculation from temperature data
            if 'precipitation_trend' in precip_data:
                extreme_precip = abs(precip_data.get('precipitation_trend', 0)) * 100
            else:
                extreme_precip = 0.5  # Conservative default
        
        # Calculate imperviousness from LULC
        if lulc_data is not None:
            built_percentage = lulc_data.get('built_area_percentage', 0) / 100.0
            imperviousness = min(built_percentage * 1.2, 1.0)  # Built areas + roads
        else:
            imperviousness = 0.3  # Default
        
        # Combine factors (weighted approach)
        pluvial_risk = 0.6 * extreme_precip + 0.4 * imperviousness
        
        # Apply winsorized scaling across all cities
        all_pluvial_values = []
        for city in self.city_names:
            city_precip = self.get_city_data(city, 'temperature')
            city_lulc = self.get_city_data(city, 'lulc')
            
            if city_precip and 'extreme_precip_intensity' in city_precip:
                city_extreme = city_precip['extreme_precip_intensity']
            else:
                city_extreme = abs(city_precip.get('precipitation_trend', 0)) * 100 if city_precip else 0.5
            
            if city_lulc:
                city_built = city_lulc.get('built_area_percentage', 0) / 100.0
                city_imperv = min(city_built * 1.2, 1.0)
            else:
                city_imperv = 0.3
            
            city_pluvial = 0.6 * city_extreme + 0.4 * city_imperv
            all_pluvial_values.append(city_pluvial)
        
        # Winsorized normalization (2nd-98th percentiles)
        p2, p98 = np.percentile(all_pluvial_values, [2, 98])
        winsorized_values = np.clip(all_pluvial_values, p2, p98)
        
        # Apply safe percentile normalization
        normalized_pluvial = self.safe_percentile_norm(winsorized_values, floor=0.05, ceiling=0.95)
        
        # Return value for current city
        city_index = self.city_names.index(city_name)
        return normalized_pluvial[city_index]
'''
    
    return pluvial_fix

def implement_adaptive_capacity_fix():
    """Fix adaptive capacity using geometric mean"""
    
    adaptive_fix = '''
    def _calculate_overall_adaptive_capacity(self, city_name):
        """Calculate overall adaptive capacity using geometric mean (FIXED)"""
        
        # Calculate individual components with safe scaling
        gdp_capacity = self._calculate_gdp_adaptive_capacity(city_name)
        greenspace_capacity = self._calculate_greenspace_adaptive_capacity(city_name) 
        services_capacity = self._calculate_services_adaptive_capacity(city_name)
        air_quality_capacity = self._calculate_air_quality_adaptive_capacity(city_name)
        social_capacity = self._calculate_social_infrastructure_capacity(city_name)
        water_capacity = self._calculate_water_system_capacity(city_name)
        
        # Use geometric mean to prevent zero collapse
        components = {
            'gdp': gdp_capacity,
            'greenspace': greenspace_capacity,
            'services': services_capacity, 
            'air_quality': air_quality_capacity,
            'social': social_capacity,
            'water': water_capacity
        }
        
        return self.geometric_mean_adaptive_capacity(components, floor=0.05, ceiling=0.95)
'''
    
    return adaptive_fix

def implement_missing_data_handling():
    """Implement proper missing data handling"""
    
    missing_data_fix = '''
    def handle_missing_data(self, value, component_name, city_name):
        """Handle missing data with imputation instead of 0/1 defaults"""
        
        if value is None or np.isnan(value) or np.isinf(value):
            # Calculate regional median for imputation
            all_values = []
            for city in self.city_names:
                try:
                    if component_name == 'bio_trend_vulnerability':
                        city_value = self._get_bio_trend_vulnerability_raw(city)
                    elif component_name == 'gdp_adaptive_capacity':
                        city_value = self._get_gdp_adaptive_capacity_raw(city)
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
        
        return value
'''
    
    return missing_data_fix

def create_comprehensive_fix_script():
    """Create script to apply all fixes systematically"""
    
    print("=" * 80)
    print("CREATING COMPREHENSIVE FIX IMPLEMENTATION")
    print("=" * 80)
    
    fixes = {
        'scaling_functions': implement_proper_scaling_functions(),
        'gdp_exposure': implement_gdp_exposure_fix(),
        'population_exposure': implement_population_exposure_fix(), 
        'pluvial_hazard': implement_pluvial_hazard_fix(),
        'adaptive_capacity': implement_adaptive_capacity_fix(),
        'missing_data': implement_missing_data_handling()
    }
    
    print("✅ Generated fixes for all 6 critical red flags:")
    print("   1. Safe percentile normalization with floor/ceiling [0.05, 0.95]")
    print("   2. GDP exposure using total GDP at risk (not per capita)")
    print("   3. Population exposure using log density")
    print("   4. Pluvial hazard with winsorized scaling")
    print("   5. Adaptive capacity with geometric mean")
    print("   6. Missing data imputation (no 0.000/1.000 defaults)")
    
    return fixes

def main():
    """Generate comprehensive fix implementation"""
    print("IMPLEMENTING CRITICAL RED FLAG FIXES")
    print("Addressing all 6 confirmed issues with concrete solutions")
    print("=" * 80)
    
    fixes = create_comprehensive_fix_script()
    
    print(f"\n🔧 READY TO APPLY FIXES:")
    print(f"   - Enhanced scaling functions with safe bounds")
    print(f"   - GDP exposure: total GDP at risk calculation") 
    print(f"   - Population exposure: log density approach")
    print(f"   - Pluvial hazard: winsorized extreme precipitation")
    print(f"   - Adaptive capacity: geometric mean composition")
    print(f"   - Missing data: median imputation methodology")
    
    print(f"\n📋 NEXT STEPS:")
    print(f"   1. Apply fixes to services/climate_risk_assessment.py")
    print(f"   2. Add safe scaling functions to services/climate_data_loader.py")
    print(f"   3. Test fixes with verification script")
    print(f"   4. Validate improvements with before/after comparison")

if __name__ == "__main__":
    main()
