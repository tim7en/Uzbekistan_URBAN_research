"""
Data Validator Module

Validates data availability and quality for climate risk assessment components.
"""

from typing import Dict, List, Optional, Set
from .base import BaseRiskModule


class DataValidator(BaseRiskModule):
    """Data validation module for climate risk assessment"""
    
    def __init__(self, data_loader=None):
        super().__init__(data_loader)
        
        # Define required data types for each component
        self.required_data = {
            'hazards': [
                'temperature_data',
                'suhi_data'
            ],
            'exposure': [
                'population_data',
                'lulc_data',
                'spatial_data'
            ],
            'vulnerability': [
                'population_data',
                'air_quality_data',
                'lulc_data'
            ],
            'adaptive_capacity': [
                'population_data',
                'vegetation_data',
                'spatial_data'
            ]
        }
        
        # Optional data that enhances assessment quality
        self.optional_data = {
            'hazards': [
                'air_quality_data'
            ],
            'exposure': [
                'nightlight_data',
                'air_quality_data'
            ],
            'vulnerability': [
                'social_sector_data',
                'water_scarcity_data'
            ],
            'adaptive_capacity': [
                'social_sector_data',
                'nightlight_data'
            ]
        }
        
    def calculate(self, city: str, **kwargs) -> Dict[str, any]:
        """
        Validate data availability for the given city
        
        Args:
            city: City name
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of validation results
        """
        cache_key = f"validation_{city}"
        cached_result = self.get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result
            
        results = {
            'city': city,
            'overall_quality': 0.0,
            'component_readiness': {},
            'available_data': [],
            'missing_required': [],
            'missing_optional': [],
            'data_quality_issues': [],
            'recommendations': []
        }
        
        # Check data availability for each component
        for component in ['hazards', 'exposure', 'vulnerability', 'adaptive_capacity']:
            readiness = self._validate_component_data(city, component)
            results['component_readiness'][component] = readiness
            
        # Calculate overall quality score
        results['overall_quality'] = self._calculate_overall_quality(results['component_readiness'])
        
        # Generate recommendations
        results['recommendations'] = self._generate_recommendations(city, results)
        
        self.set_cached_result(cache_key, results)
        return results
        
    def _validate_component_data(self, city: str, component: str) -> Dict[str, any]:
        """Validate data availability for a specific component"""
        if not self.data_loader:
            return {
                'readiness_score': 0.0,
                'required_available': 0,
                'required_total': len(self.required_data.get(component, [])),
                'optional_available': 0,
                'optional_total': len(self.optional_data.get(component, [])),
                'missing_required': self.required_data.get(component, []),
                'missing_optional': self.optional_data.get(component, []),
                'quality_issues': []
            }
            
        required_data = self.required_data.get(component, [])
        optional_data = self.optional_data.get(component, [])
        
        available_required = []
        missing_required = []
        available_optional = []
        missing_optional = []
        quality_issues = []
        
        # Check required data
        for data_type in required_data:
            if self._check_data_availability(city, data_type):
                available_required.append(data_type)
                # Check data quality
                issues = self._check_data_quality(city, data_type)
                quality_issues.extend(issues)
            else:
                missing_required.append(data_type)
                
        # Check optional data
        for data_type in optional_data:
            if self._check_data_availability(city, data_type):
                available_optional.append(data_type)
                # Check data quality
                issues = self._check_data_quality(city, data_type)
                quality_issues.extend(issues)
            else:
                missing_optional.append(data_type)
        
        # Calculate readiness score
        required_score = len(available_required) / len(required_data) if required_data else 1.0
        optional_score = len(available_optional) / len(optional_data) if optional_data else 0.0
        
        # Weight: 80% required, 20% optional
        readiness_score = 0.8 * required_score + 0.2 * optional_score
        
        return {
            'readiness_score': readiness_score,
            'required_available': len(available_required),
            'required_total': len(required_data),
            'optional_available': len(available_optional),
            'optional_total': len(optional_data),
            'missing_required': missing_required,
            'missing_optional': missing_optional,
            'quality_issues': quality_issues
        }
        
    def _check_data_availability(self, city: str, data_type: str) -> bool:
        """Check if specific data type is available for the city"""
        try:
            if data_type == 'temperature_data':
                return bool(self.data_loader.get_temperature_data(city))
            elif data_type == 'suhi_data':
                return bool(self.data_loader.get_suhi_data(city))
            elif data_type == 'population_data':
                return bool(self.data_loader.get_population_data(city))
            elif data_type == 'lulc_data':
                return bool(self.data_loader.get_lulc_data(city))
            elif data_type == 'spatial_data':
                return bool(self.data_loader.get_spatial_data(city))
            elif data_type == 'air_quality_data':
                return bool(self.data_loader.get_air_quality_data(city))
            elif data_type == 'vegetation_data':
                return bool(self.data_loader.get_vegetation_data(city))
            elif data_type == 'nightlight_data':
                return bool(self.data_loader.get_nightlight_data(city))
            elif data_type == 'social_sector_data':
                if hasattr(self.data_loader, 'get_social_sector_data'):
                    return bool(self.data_loader.get_social_sector_data(city))
            elif data_type == 'water_scarcity_data':
                if hasattr(self.data_loader, 'get_water_scarcity_data'):
                    return bool(self.data_loader.get_water_scarcity_data(city))
            return False
        except Exception:
            return False
            
    def _check_data_quality(self, city: str, data_type: str) -> List[str]:
        """Check data quality issues for specific data type"""
        issues = []
        
        try:
            if data_type == 'temperature_data':
                temp_data = self.data_loader.get_temperature_data(city)
                if temp_data:
                    # Check for sufficient temporal coverage
                    if isinstance(temp_data, dict):
                        years = len(temp_data.keys()) if hasattr(temp_data, 'keys') else 0
                        if years < 2:
                            issues.append(f"Temperature data: insufficient temporal coverage ({years} years)")
                        
            elif data_type == 'population_data':
                pop_data = self.data_loader.get_population_data(city)
                if pop_data:
                    # Check for missing key fields
                    if not getattr(pop_data, 'population_2024', None):
                        issues.append("Population data: missing population_2024")
                    if not getattr(pop_data, 'gdp_per_capita_usd', None):
                        issues.append("Population data: missing gdp_per_capita_usd")
                        
            elif data_type == 'lulc_data':
                lulc_data = self.data_loader.get_lulc_data(city)
                if lulc_data:
                    # Check for temporal coverage
                    if isinstance(lulc_data, dict) and 'years' in lulc_data:
                        years = len(lulc_data['years']) if lulc_data['years'] else 0
                        if years < 1:
                            issues.append("LULC data: no temporal data available")
                            
        except Exception as e:
            issues.append(f"{data_type}: validation error - {str(e)}")
            
        return issues
        
    def _calculate_overall_quality(self, component_readiness: Dict[str, Dict]) -> float:
        """Calculate overall data quality score"""
        if not component_readiness:
            return 0.0
            
        # Weight components equally
        total_score = sum(comp['readiness_score'] for comp in component_readiness.values())
        return total_score / len(component_readiness)
        
    def _generate_recommendations(self, city: str, validation_results: Dict) -> List[str]:
        """Generate data improvement recommendations"""
        recommendations = []
        
        overall_quality = validation_results['overall_quality']
        component_readiness = validation_results['component_readiness']
        
        # Overall quality recommendations
        if overall_quality < 0.5:
            recommendations.append("CRITICAL: Low overall data quality. Consider data collection priority.")
        elif overall_quality < 0.7:
            recommendations.append("MODERATE: Some data gaps exist. Assessment results may have limitations.")
        
        # Component-specific recommendations
        for component, readiness in component_readiness.items():
            if readiness['readiness_score'] < 0.6:
                missing_req = readiness['missing_required']
                if missing_req:
                    recommendations.append(f"{component.title()}: Missing required data - {', '.join(missing_req)}")
                    
        # Priority recommendations based on component importance
        hazard_readiness = component_readiness.get('hazards', {}).get('readiness_score', 0)
        if hazard_readiness < 0.7:
            recommendations.append("PRIORITY: Improve hazard data (temperature, SUHI) for accurate risk assessment")
            
        exposure_readiness = component_readiness.get('exposure', {}).get('readiness_score', 0)
        if exposure_readiness < 0.7:
            recommendations.append("PRIORITY: Improve exposure data (population, LULC) for accurate risk assessment")
            
        # Enhancement recommendations
        vulnerability_readiness = component_readiness.get('vulnerability', {}).get('readiness_score', 0)
        if vulnerability_readiness < 0.8:
            recommendations.append("ENHANCE: Add social sector data to improve vulnerability assessment")
            
        adaptive_capacity_readiness = component_readiness.get('adaptive_capacity', {}).get('readiness_score', 0)
        if adaptive_capacity_readiness < 0.8:
            recommendations.append("ENHANCE: Add social infrastructure data to improve adaptive capacity assessment")
            
        return recommendations


def validate_city_data(city: str, data_loader=None) -> Dict[str, any]:
    """
    Standalone function to validate data for a city
    
    Args:
        city: City name
        data_loader: Optional data loader instance
        
    Returns:
        Dictionary of validation results
    """
    validator = DataValidator(data_loader)
    return validator.calculate(city)


if __name__ == "__main__":
    import sys
    import os
    
    # Add parent directory to path to import data loader
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from services.climate_data_loader import ClimateDataLoader
    
    # Example usage
    if len(sys.argv) > 1:
        city_name = sys.argv[1]
        
        # Initialize data loader
        loader = ClimateDataLoader()
        
        # Run validation
        results = validate_city_data(city_name, loader)
        
        print(f"\nData Validation Report for {city_name}")
        print("=" * 50)
        print(f"Overall Quality Score: {results['overall_quality']:.2f}")
        print()
        
        print("Component Readiness:")
        print("-" * 30)
        for component, readiness in results['component_readiness'].items():
            score = readiness['readiness_score']
            status = "✓ READY" if score >= 0.8 else "⚠ PARTIAL" if score >= 0.5 else "✗ NOT READY"
            print(f"{component.title()}: {score:.2f} {status}")
            
            if readiness['missing_required']:
                print(f"  Missing Required: {', '.join(readiness['missing_required'])}")
            if readiness['missing_optional']:
                print(f"  Missing Optional: {', '.join(readiness['missing_optional'])}")
            if readiness['quality_issues']:
                print(f"  Quality Issues: {'; '.join(readiness['quality_issues'])}")
            print()
        
        if results['recommendations']:
            print("Recommendations:")
            print("-" * 20)
            for i, rec in enumerate(results['recommendations'], 1):
                print(f"{i}. {rec}")
    else:
        print("Usage: python data_validator.py <city_name>")
        print("Example: python data_validator.py Tashkent")
