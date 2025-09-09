# Modular Climate Risk Assessment

This directory contains a modularized implementation of the IPCC AR6-based climate risk assessment framework for urban areas in Uzbekistan. The assessment has been broken down into independent modules that can be run separately or combined for comprehensive analysis.

## Architecture Overview

The climate risk assessment is organized into the following modules:

```
climate_risk_modules/
├── __init__.py                 # Package initialization and exports
├── base.py                     # Core data structures and base classes
├── hazards.py                  # Climate hazard assessment
├── exposure.py                 # Exposure assessment
├── vulnerability.py            # Vulnerability assessment
├── adaptive_capacity.py        # Adaptive capacity assessment
├── risk_calculator.py          # Overall risk calculation and integration
└── data_validator.py           # Data validation and quality checks
```

## Key Features

### ✅ **Modular Design**
- Each component (hazards, exposure, vulnerability, adaptive capacity) can be run independently
- Standardized interfaces for easy integration
- Cached results for efficient computation

### ✅ **Real Data Only**
- No default values used except for component weights
- All calculations based on actual available data
- Transparent handling of missing data (returns 0.0 when data unavailable)

### ✅ **IPCC AR6 Compliance**
- Follows IPCC AR6 framework: Risk = f(Hazard, Exposure, Vulnerability, Adaptive Capacity)
- Validated component weights that sum to 1.0
- Standard risk calculation formulas

### ✅ **Data Quality Control**
- Built-in data validation module
- Quality assessment for each component
- Recommendations for data improvement

## Module Descriptions

### Base Module (`base.py`)
- **Purpose**: Core data structures and abstract base class
- **Key Components**:
  - `ClimateRiskMetrics`: Data structure for storing all assessment results
  - `BaseRiskModule`: Abstract base class with common functionality
  - Configuration constants and default weights
- **Standalone**: No (used by other modules)

### Hazards Module (`hazards.py`)
- **Purpose**: Assess climate hazards including temperature and heat-related risks
- **Components**:
  - Temperature anomaly assessment
  - Heat island intensity evaluation
  - Temperature trend analysis
  - Extreme heat days calculation
- **Standalone**: ✅ Yes
- **Usage**: `python -m climate_risk_modules.hazards <city_name>`

### Exposure Module (`exposure.py`)
- **Purpose**: Assess exposure to climate hazards
- **Components**:
  - Population density exposure
  - Built-up area assessment
  - Vegetation accessibility (inverse exposure)
  - Air quality exposure
- **Standalone**: ✅ Yes
- **Usage**: `python -m climate_risk_modules.exposure <city_name>`

### Vulnerability Module (`vulnerability.py`)
- **Purpose**: Assess vulnerability factors that influence climate risk
- **Components**:
  - Social vulnerability (demographics, services access)
  - Infrastructure vulnerability (built environment, building age)
  - Health vulnerability (air quality, healthcare access)
  - Economic vulnerability (GDP-based assessments)
- **Standalone**: ✅ Yes
- **Usage**: `python -m climate_risk_modules.vulnerability <city_name>`

### Adaptive Capacity Module (`adaptive_capacity.py`)
- **Purpose**: Assess capacity to adapt to climate change
- **Components**:
  - Green infrastructure capacity
  - Institutional capacity (governance, resources)
  - Economic capacity (financial resources)
  - Social capacity (education, healthcare, connectivity)
- **Standalone**: ✅ Yes
- **Usage**: `python -m climate_risk_modules.adaptive_capacity <city_name>`

### Risk Calculator (`risk_calculator.py`)
- **Purpose**: Integrate all components into overall risk assessment
- **Features**:
  - Weighted and multiplicative risk calculation approaches
  - Priority scoring for intervention planning
  - Comprehensive risk summaries
  - Detailed component breakdown
- **Standalone**: ✅ Yes
- **Usage**: `python -m climate_risk_modules.risk_calculator <city_name> [--detailed]`

### Data Validator (`data_validator.py`)
- **Purpose**: Validate data availability and quality for assessments
- **Features**:
  - Component-wise data readiness assessment
  - Quality issue identification
  - Improvement recommendations
  - Overall quality scoring
- **Standalone**: ✅ Yes
- **Usage**: `python -m climate_risk_modules.data_validator <city_name>`

## Quick Start

### 1. Test the Modular Setup
```bash
python test_modular_assessment.py
```

### 2. Run Individual Components
```bash
# Hazards assessment
python -c "from climate_risk_modules.hazards import run_hazard_assessment; from services.climate_data_loader import ClimateDataLoader; print(run_hazard_assessment('Tashkent', ClimateDataLoader('.')))"

# Data validation
python -c "from climate_risk_modules.data_validator import validate_city_data; from services.climate_data_loader import ClimateDataLoader; print(validate_city_data('Tashkent', ClimateDataLoader('.')))"

# Full assessment
python -c "from climate_risk_modules.risk_calculator import run_full_risk_assessment; from services.climate_data_loader import ClimateDataLoader; print(run_full_risk_assessment('Tashkent', ClimateDataLoader('.')))"
```

### 3. Use in Your Scripts
```python
from climate_risk_modules import (
    run_hazard_assessment,
    run_exposure_assessment,
    run_vulnerability_assessment,
    run_adaptive_capacity_assessment,
    run_full_risk_assessment,
    validate_city_data
)
from services.climate_data_loader import ClimateDataLoader

# Initialize data loader
data_loader = ClimateDataLoader('.')

# Run individual assessments
hazard_results = run_hazard_assessment('Tashkent', data_loader)
exposure_results = run_exposure_assessment('Tashkent', data_loader)

# Or run full assessment
full_results = run_full_risk_assessment('Tashkent', data_loader)
print(f"Risk Score: {full_results['risk_score']:.3f}")
```

## Component Weights

The assessment uses IPCC AR6-validated weights:

### Hazard Components
- Temperature anomaly: 30%
- Heat island intensity: 30%
- Temperature trend: 20%
- Extreme heat days: 20%

### Exposure Components
- Population density: 40%
- Built-up area: 30%
- Vegetation accessibility: 20%
- Air quality exposure: 10%

### Vulnerability Components
- Social vulnerability: 30%
- Infrastructure vulnerability: 25%
- Health vulnerability: 25%
- Economic vulnerability: 20%

### Adaptive Capacity Components
- Green infrastructure: 40%
- Institutional capacity: 25%
- Economic capacity: 20%
- Social capacity: 15%

## Data Requirements

### Required Data (for full assessment):
- **Population data**: Demographics, GDP, density
- **Temperature data**: Historical time series, SUHI data
- **LULC data**: Land use/land cover classifications
- **Spatial data**: Vegetation accessibility, urban structure

### Optional Data (enhances assessment):
- **Air quality data**: Pollutant concentrations
- **Social sector data**: Healthcare, education infrastructure
- **Nightlight data**: Economic activity indicators
- **Water scarcity data**: Hydrological assessments

## Validation and Quality Control

The framework includes comprehensive validation:

1. **Data Availability Check**: Ensures required data exists
2. **Data Quality Assessment**: Identifies temporal coverage and completeness issues
3. **Component Readiness**: Evaluates readiness for each assessment component
4. **Recommendations**: Provides specific guidance for data improvement

## Integration with Existing Workflow

The modular framework is fully compatible with the existing climate risk assessment system:

- Uses the same `ClimateDataLoader` service
- Maintains compatibility with existing data structures
- Can be run alongside or replace the existing `IPCCRiskAssessmentService`
- Results format compatible with existing reporting tools

## Benefits of Modular Approach

1. **Flexibility**: Run only the components you need
2. **Debugging**: Easier to identify and fix issues in specific components
3. **Development**: Independent development and testing of components
4. **Scalability**: Easy to add new components or modify existing ones
5. **Transparency**: Clear separation of concerns and calculation steps
6. **Validation**: Component-level validation and quality control

## Next Steps

1. **Enhanced Data Integration**: Add more data sources for improved assessments
2. **Component Expansion**: Add new risk components (e.g., flood risk, drought risk)
3. **Validation Framework**: Expand validation with ground-truth data
4. **Automation**: Create automated pipelines for regular assessments
5. **Visualization**: Add component-specific visualization tools
