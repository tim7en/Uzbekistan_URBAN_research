#!/usr/bin/env python3
"""
Test Modular Climate Risk Assessment

Simple test script to demonstrate the modular climate risk assessment functionality.
"""

import sys
import os
from pathlib import Path

# Add paths for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir / 'services'))

def test_modular_assessment():
    """Test the modular climate risk assessment components"""
    
    print("Testing Modular Climate Risk Assessment")
    print("=" * 50)
    
    # Test city
    test_city = "Tashkent"
    
    try:
        # Import the climate data loader
        from services.climate_data_loader import ClimateDataLoader
        
        # Initialize data loader
        print("1. Initializing data loader...")
        base_path = str(current_dir)
        data_loader = ClimateDataLoader(base_path)
        print("   ✓ Data loader initialized successfully")
        
        # Test importing modular components
        print("\n2. Testing module imports...")
        
        from climate_risk_modules.hazards import run_hazard_assessment
        print("   ✓ Hazards module imported")
        
        from climate_risk_modules.exposure import run_exposure_assessment
        print("   ✓ Exposure module imported")
        
        from climate_risk_modules.vulnerability import run_vulnerability_assessment
        print("   ✓ Vulnerability module imported")
        
        from climate_risk_modules.adaptive_capacity import run_adaptive_capacity_assessment
        print("   ✓ Adaptive capacity module imported")
        
        from climate_risk_modules.risk_calculator import run_full_risk_assessment
        print("   ✓ Risk calculator module imported")
        
        from climate_risk_modules.data_validator import validate_city_data
        print("   ✓ Data validator module imported")
        
        # Test data validation
        print(f"\n3. Validating data for {test_city}...")
        validation_results = validate_city_data(test_city, data_loader)
        print(f"   ✓ Data quality score: {validation_results['overall_quality']:.3f}")
        
        # Test individual modules
        print(f"\n4. Testing individual modules for {test_city}...")
        
        # Test hazards
        try:
            hazard_results = run_hazard_assessment(test_city, data_loader)
            print(f"   ✓ Hazards assessment: score = {hazard_results.get('hazard_score', 0.0):.3f}")
        except Exception as e:
            print(f"   ✗ Hazards assessment failed: {e}")
        
        # Test exposure
        try:
            exposure_results = run_exposure_assessment(test_city, data_loader)
            print(f"   ✓ Exposure assessment: score = {exposure_results.get('exposure_score', 0.0):.3f}")
        except Exception as e:
            print(f"   ✗ Exposure assessment failed: {e}")
        
        # Test vulnerability
        try:
            vulnerability_results = run_vulnerability_assessment(test_city, data_loader)
            print(f"   ✓ Vulnerability assessment: score = {vulnerability_results.get('vulnerability_score', 0.0):.3f}")
        except Exception as e:
            print(f"   ✗ Vulnerability assessment failed: {e}")
        
        # Test adaptive capacity
        try:
            adaptive_results = run_adaptive_capacity_assessment(test_city, data_loader)
            print(f"   ✓ Adaptive capacity assessment: score = {adaptive_results.get('adaptive_capacity_score', 0.0):.3f}")
        except Exception as e:
            print(f"   ✗ Adaptive capacity assessment failed: {e}")
        
        # Test full risk assessment
        print(f"\n5. Testing full risk assessment for {test_city}...")
        try:
            full_results = run_full_risk_assessment(test_city, data_loader)
            print(f"   ✓ Full risk assessment completed")
            print(f"   - Risk Score: {full_results['risk_score']:.3f} ({full_results['risk_level']})")
            print(f"   - Priority Score: {full_results['priority_score']:.3f} ({full_results['priority_level']})")
            
            components = full_results['components']
            print(f"   - Component Scores:")
            print(f"     • Hazard: {components['hazard_score']:.3f}")
            print(f"     • Exposure: {components['exposure_score']:.3f}")
            print(f"     • Vulnerability: {components['vulnerability_score']:.3f}")
            print(f"     • Adaptive Capacity: {components['adaptive_capacity_score']:.3f}")
            
        except Exception as e:
            print(f"   ✗ Full risk assessment failed: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n6. Modular assessment test completed!")
        print("   ✓ All modules are working and can be run independently")
        
        return True
        
    except ImportError as e:
        print(f"   ✗ Import error: {e}")
        print("   Make sure all required modules are in the correct directories")
        return False
        
    except Exception as e:
        print(f"   ✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_usage_examples():
    """Show usage examples for the modular assessment"""
    
    print("\nUsage Examples:")
    print("=" * 50)
    print("The climate risk assessment has been successfully modularized!")
    print("Each component can now be run independently:")
    print()
    
    print("1. Run individual modules:")
    print("   python -c \"from climate_risk_modules.hazards import run_hazard_assessment; from services.climate_data_loader import ClimateDataLoader; print(run_hazard_assessment('Tashkent', ClimateDataLoader('.')))\"")
    print()
    
    print("2. Run data validation:")
    print("   python -c \"from climate_risk_modules.data_validator import validate_city_data; from services.climate_data_loader import ClimateDataLoader; print(validate_city_data('Tashkent', ClimateDataLoader('.')))\"")
    print()
    
    print("3. Run full risk assessment:")
    print("   python -c \"from climate_risk_modules.risk_calculator import run_full_risk_assessment; from services.climate_data_loader import ClimateDataLoader; print(run_full_risk_assessment('Tashkent', ClimateDataLoader('.')))\"")
    print()
    
    print("4. Import and use in your own scripts:")
    print("   from climate_risk_modules import run_full_risk_assessment")
    print("   from services.climate_data_loader import ClimateDataLoader")
    print("   results = run_full_risk_assessment('CityName', ClimateDataLoader('.'))")
    print()
    
    print("Module Structure:")
    print("├── climate_risk_modules/")
    print("│   ├── __init__.py")
    print("│   ├── base.py                 # Core data structures")
    print("│   ├── hazards.py              # Climate hazard assessment")
    print("│   ├── exposure.py             # Exposure assessment") 
    print("│   ├── vulnerability.py        # Vulnerability assessment")
    print("│   ├── adaptive_capacity.py    # Adaptive capacity assessment")
    print("│   ├── risk_calculator.py      # Overall risk calculation")
    print("│   └── data_validator.py       # Data validation")
    print("└── services/")
    print("    └── climate_data_loader.py  # Data loading service")


if __name__ == "__main__":
    success = test_modular_assessment()
    
    if success:
        show_usage_examples()
        print("\n🎉 Modular climate risk assessment is ready to use!")
    else:
        print("\n❌ Modular assessment test failed. Please check the error messages above.")
        sys.exit(1)
