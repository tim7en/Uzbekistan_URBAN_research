# Comprehensive City GDP Estimator - Usage Guide

## Overview
The `comprehensive_city_gdp_estimator.py` script provides a sophisticated multi-method approach to estimate city-level GDP for Uzbekistan cities using all available data sources.

## Features
- **5 estimation methods** with weighted ensemble modeling
- **Comprehensive data integration** from all CSV files in the EstimateGDP folder
- **Confidence scoring** and uncertainty quantification
- **Regional validation** against official GDP statistics
- **Temporal coverage** from 2017-2024

## Methods Implemented

### Method 1: Population Allocation
- Allocates regional GDP based on city's population share
- **Input**: City population, regional population, regional GDP per capita
- **Confidence**: 70% (medium)

### Method 2: Salary Adjusted
- Uses salary differentials to adjust regional GDP per capita
- **Input**: City wages, regional wages, population
- **Confidence**: 80% (high)

### Method 3: Nightlight Correlation  
- Incorporates nighttime light intensity as economic activity proxy
- **Input**: City-to-rural nightlight ratios, base GDP data
- **Confidence**: 60% (medium-low)

### Method 4: Sectoral Composition
- Applies urban productivity multipliers by economic sector
- **Input**: Regional sectoral composition, urban multipliers
- **Confidence**: 70% (medium)

### Method 5: Regional Benchmarking
- Benchmarks against similar cities using size and wage factors
- **Input**: City size, salary levels, regional context
- **Confidence**: 60% (medium-low)

### Ensemble Method
- Weighted average of all methods based on confidence scores
- Includes uncertainty quantification (standard deviation)

## Usage

### Basic Usage
```bash
cd EstimateGDP
python comprehensive_city_gdp_estimator.py
```

### Required Data Files
All files must be in the same directory as the script:
- `City_population.csv` - Urban population by city and year
- `City_salary.csv` - Average city wages in USD  
- `Region_GDP_capita.csv` - Official regional GDP per capita
- `City_nightlights_ratio.csv` - Urban-to-rural luminosity ratios
- `Nightlights_city_rural.csv` - City-to-administrative region ratios
- `Contribution_GDP_sectors_2024.csv` - Economic sector breakdown
- `Region_population.csv` - Regional population data
- `Region_salary.csv` - Regional average salaries

## Output Files

### Main Results: `comprehensive_city_gdp_estimates_YYYYMMDD_HHMMSS.csv`
Contains:
- `year`, `city`, `region` - Identifiers
- `ensemble_gdp_billion` - Final GDP estimate (billions USD)
- `gdp_per_capita_usd` - GDP per capita
- `confidence_score` - Average confidence across methods (0-1)
- `uncertainty_std` - Standard deviation of method estimates
- `n_methods` - Number of methods with valid data
- `method_1_population` through `method_5_benchmark` - Individual method results

### Validation Results: `comprehensive_city_gdp_estimates_YYYYMMDD_HHMMSS_validation.csv`
Contains regional validation comparing city totals against regional GDP.

## Key Results Summary (Latest Run)

### Top Cities by GDP (2024)
1. **Tashkent**: $33.96B ($11,169/capita)
2. **Namangan**: $1.63B ($2,339/capita) 
3. **Samarkand**: $1.58B ($2,700/capita)
4. **Andijan**: $1.34B ($2,785/capita)
5. **Bukhara**: $1.13B ($3,850/capita)

### Quality Metrics
- **85.7% data coverage** across all methods
- **23.5% average coverage** of regional GDP (reflects urban share)
- **0.58 average confidence score** across all estimates
- **112 city-year observations** (14 cities × 8 years)

### Growth Leaders (CAGR 2017-2024)
- **Tashkent**: 13.2% annually
- **Namangan**: 7.5% annually
- **Andijan**: 7.5% annually 
- **Fergana**: 7.1% annually

## Interpretation Notes

### Coverage Ratio (23.5%)
This indicates cities represent about 23.5% of regional GDP on average, which is reasonable for:
- Rural regions with significant agricultural GDP
- Cities being economic centers but not entire regional economy
- Conservative estimation approach

### Confidence Scores
- **0.8**: High confidence (salary-adjusted method)
- **0.7**: Medium confidence (population, sectoral methods)  
- **0.6**: Medium-low confidence (nightlight, benchmark methods)

### Validation
The script validates estimates against regional GDP totals to ensure reasonableness and detect potential over/under-estimation.

## Customization

### Adjusting Urban Multipliers
Edit the `urban_multipliers` dictionary in `method_4_sectoral_composition()`:
```python
urban_multipliers = {
    'Agriculture': 0.5,      # Lower in cities
    'Industry': 1.3,         # Higher productivity  
    'Construction': 1.2,     # Urban construction premium
    'Services': 1.5          # Major urban advantage
}
```

### Modifying Confidence Weights
Adjust confidence scores in each method's return statement to emphasize certain approaches.

### Adding New Methods
Extend the class with additional `method_X_name()` functions following the same pattern.

## Technical Requirements
- Python 3.7+
- pandas, numpy, matplotlib, seaborn
- All CSV files in semicolon format (handled automatically)