#!/usr/bin/env python3
"""
Modular Climate Risk Assessment Runner

This script provides a command-line interface to run climate risk assessment
modules individually or together.
"""

import sys
import os
import argparse
import json
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from climate_risk_modules import (
    run_hazard_assessment,
    run_exposure_assessment, 
    run_vulnerability_assessment,
    run_adaptive_capacity_assessment,
    run_full_risk_assessment,
    validate_city_data
)

# Add services directory to path for data loader
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'services'))
from climate_data_loader import ClimateDataLoader


def run_individual_module(module: str, city: str, data_loader: ClimateDataLoader) -> dict:
    """Run an individual assessment module"""
    
    if module == 'hazards':
        return run_hazard_assessment(city, data_loader)
    elif module == 'exposure':
        return run_exposure_assessment(city, data_loader)
    elif module == 'vulnerability':
        return run_vulnerability_assessment(city, data_loader)
    elif module == 'adaptive_capacity':
        return run_adaptive_capacity_assessment(city, data_loader)
    elif module == 'validation':
        return validate_city_data(city, data_loader)
    else:
        raise ValueError(f"Unknown module: {module}")


def format_results(results: dict, module: str = None) -> str:
    """Format results for console output"""
    
    if module == 'validation':
        output = f"\nData Validation Results:\n"
        output += "=" * 50 + "\n"
        output += f"Overall Quality: {results['overall_quality']:.3f}\n\n"
        
        output += "Component Readiness:\n"
        for component, readiness in results['component_readiness'].items():
            score = readiness['readiness_score']
            status = "✓ READY" if score >= 0.8 else "⚠ PARTIAL" if score >= 0.5 else "✗ NOT READY"
            output += f"  {component.title()}: {score:.3f} {status}\n"
        
        if results['recommendations']:
            output += "\nRecommendations:\n"
            for i, rec in enumerate(results['recommendations'], 1):
                output += f"  {i}. {rec}\n"
                
        return output
    
    elif module in ['hazards', 'exposure', 'vulnerability', 'adaptive_capacity']:
        output = f"\n{module.title()} Assessment Results:\n"
        output += "=" * 50 + "\n"
        
        for metric, value in results.items():
            if isinstance(value, (int, float)):
                output += f"{metric.replace('_', ' ').title()}: {value:.4f}\n"
        
        return output
    
    else:
        # Full risk assessment
        output = f"\nClimate Risk Assessment Summary:\n"
        output += "=" * 60 + "\n"
        output += f"Overall Risk Score: {results['risk_score']:.4f} ({results['risk_level']})\n"
        output += f"Priority Score: {results['priority_score']:.4f} ({results['priority_level']})\n\n"
        
        output += "Component Scores:\n"
        output += "-" * 30 + "\n"
        components = results['components']
        output += f"Hazard Score: {components['hazard_score']:.4f}\n"
        output += f"Exposure Score: {components['exposure_score']:.4f}\n"
        output += f"Vulnerability Score: {components['vulnerability_score']:.4f}\n"
        output += f"Adaptive Capacity: {components['adaptive_capacity_score']:.4f} ({components['adaptive_capacity_level']})\n"
        
        return output


def save_results(results: dict, output_file: str, city: str, module: str = None):
    """Save results to JSON file"""
    import datetime
    
    output_data = {
        'city': city,
        'module': module or 'full_assessment',
        'results': results,
        'timestamp': datetime.datetime.now().isoformat()
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"Results saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Modular Climate Risk Assessment Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full risk assessment
  python run_modular_climate_assessment.py Tashkent
  
  # Run individual modules
  python run_modular_climate_assessment.py Tashkent --module hazards
  python run_modular_climate_assessment.py Tashkent --module exposure
  python run_modular_climate_assessment.py Tashkent --module vulnerability
  python run_modular_climate_assessment.py Tashkent --module adaptive_capacity
  
  # Validate data availability
  python run_modular_climate_assessment.py Tashkent --module validation
  
  # Run multiple cities
  python run_modular_climate_assessment.py Tashkent Samarkand --module hazards
  
  # Save results to file
  python run_modular_climate_assessment.py Tashkent --output tashkent_risk.json
  
  # List available cities
  python run_modular_climate_assessment.py --list-cities
        """
    )
    
    parser.add_argument('cities', nargs='*', help='City name(s) to assess')
    parser.add_argument('--module', '-m', 
                       choices=['hazards', 'exposure', 'vulnerability', 'adaptive_capacity', 'validation'],
                       help='Run specific module (default: full assessment)')
    parser.add_argument('--output', '-o', help='Output JSON file path')
    parser.add_argument('--list-cities', action='store_true', help='List available cities')
    parser.add_argument('--detailed', action='store_true', help='Show detailed component breakdown')
    
    args = parser.parse_args()
    
    # Initialize data loader
    try:
        data_loader = ClimateDataLoader()
        print("Climate data loader initialized successfully.")
    except Exception as e:
        print(f"Error initializing data loader: {e}")
        return 1
    
    # List cities if requested
    if args.list_cities:
        try:
            data = data_loader.load_all_data()
            cities = list(data.get('population_data', {}).keys())
            print(f"\nAvailable cities ({len(cities)}):")
            for city in sorted(cities):
                print(f"  - {city}")
        except Exception as e:
            print(f"Error loading cities: {e}")
        return 0
    
    # Check if cities provided
    if not args.cities:
        parser.print_help()
        return 1
    
    # Process each city
    all_results = {}
    
    for city in args.cities:
        print(f"\nProcessing {city}...")
        
        try:
            if args.module:
                # Run specific module
                results = run_individual_module(args.module, city, data_loader)
                print(format_results(results, args.module))
            else:
                # Run full assessment
                results = run_full_risk_assessment(city, data_loader)
                print(format_results(results))
                
                if args.detailed:
                    # Show detailed breakdown
                    metrics = results['detailed_metrics']
                    print("\nDetailed Component Breakdown:")
                    print("-" * 40)
                    
                    print("Hazard Components:")
                    print(f"  Temperature Anomaly: {metrics.temperature_anomaly:.4f}")
                    print(f"  Heat Island Intensity: {metrics.heat_island_intensity:.4f}")
                    print(f"  Temperature Trend: {metrics.temperature_trend:.4f}")
                    print(f"  Extreme Heat Days: {metrics.extreme_heat_days:.4f}")
                    
                    print("\nExposure Components:")
                    print(f"  Population Density: {metrics.population_density:.4f}")
                    print(f"  Built-up Area: {metrics.built_up_area:.4f}")
                    print(f"  Vegetation Accessibility: {metrics.vegetation_accessibility:.4f}")
                    print(f"  Air Quality Exposure: {metrics.air_quality_exposure:.4f}")
                    
                    print("\nVulnerability Components:")
                    print(f"  Social Vulnerability: {metrics.social_vulnerability:.4f}")
                    print(f"  Infrastructure Vulnerability: {metrics.infrastructure_vulnerability:.4f}")
                    print(f"  Health Vulnerability: {metrics.health_vulnerability:.4f}")
                    print(f"  Economic Vulnerability: {metrics.economic_vulnerability:.4f}")
                    
                    print("\nAdaptive Capacity Components:")
                    print(f"  Green Infrastructure: {metrics.green_infrastructure:.4f}")
                    print(f"  Institutional Capacity: {metrics.institutional_capacity:.4f}")
                    print(f"  Economic Capacity: {metrics.economic_capacity:.4f}")
                    print(f"  Social Capacity: {metrics.social_capacity:.4f}")
            
            all_results[city] = results
            
        except Exception as e:
            print(f"Error processing {city}: {e}")
            import traceback
            traceback.print_exc()
    
    # Save results if output file specified
    if args.output and all_results:
        try:
            save_results(all_results, args.output, 
                        args.cities[0] if len(args.cities) == 1 else 'multiple_cities',
                        args.module)
        except Exception as e:
            print(f"Error saving results: {e}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
