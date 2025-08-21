# Uzbekistan Urban Heat Island Research Project

A comprehensive analysis tool for studying Surface Urban Heat Island (SUHI) effects across major cities in Uzbekistan using Google Earth Engine and satellite data.

## 🌡️ Project Overview

This project analyzes urban heat island effects in Uzbekistan's major cities by processing satellite temperature data from multiple sources (MODIS, Landsat, ASTER) to understand:

- Surface Urban Heat Island (SUHI) intensity variations
- Day vs night temperature differences
- Temporal trends from 2017 to 2024
- Land cover changes and urban expansion
- Statistical correlations and patterns

## 🏗️ Architecture

The project follows a modular service-oriented architecture:

```
📁 Uzbekistan_URBAN_research/
├── 🎯 main.py                    # Main orchestrator (minimal entry point)
├── 📋 README.md                  # This documentation
│
├── 🔧 services/                  # Core service modules
│   ├── utils.py                  # Configuration and utilities
│   ├── gee.py                    # Google Earth Engine initialization
│   ├── classification.py         # Land cover analysis
│   ├── temperature.py            # Temperature data loading
│   ├── vegetation.py             # Vegetation indices calculation
│   ├── suhi.py                   # SUHI computation algorithms
│   ├── visualization.py          # Plotting and heat maps
│   ├── reporting.py              # Report generation
│   ├── analyzer.py               # Statistical analysis
│   └── pipeline.py               # Analysis orchestration
│
├── 📊 outputs/                   # Generated analysis outputs
├── 📈 reporting/                 # HTML/PNG reports and charts
├── 📁 dashboard_deliverables/    # Dashboard components
├── 📁 statistical_review_output/ # Statistical analysis results
└── 📁 suhi_analysis_output/      # SUHI analysis results
```

## 🚀 Quick Start

### Prerequisites

```bash
# Required Python packages
pip install earthengine-api pandas numpy matplotlib seaborn scipy plotly
pip install cartopy rasterio geopandas

# Optional for enhanced visualizations
pip install kaleido jupyter
```

### Google Earth Engine Setup

1. Create a Google Earth Engine account at [earthengine.google.com](https://earthengine.google.com)
2. Authenticate your account:
```bash
earthengine authenticate
```

### Running the Analysis

```bash
# Run comprehensive analysis
python main.py

# The script will:
# 1. Initialize Google Earth Engine
# 2. Process multiple cities (Tashkent, Samarkand, Bukhara, etc.)
# 3. Analyze both 2017 and 2024 data
# 4. Generate visualizations and reports
# 5. Export results to outputs/ directory
```

## 🔬 Core Services

### 🛠️ services/utils.py
- **UZBEKISTAN_CITIES**: Configuration for 14 major cities
- **ANALYSIS_CONFIG**: Analysis parameters and settings
- **Helper functions**: Directory creation, scaling, rate limiting

### 🌍 services/gee.py
- Google Earth Engine authentication and initialization
- Dataset availability testing
- Connection management

### 🏞️ services/classification.py
- ESRI Land Cover classification analysis
- Urban expansion detection
- Land cover change quantification

### 🌡️ services/temperature.py
- MODIS Land Surface Temperature (LST) data loading
- Landsat thermal band processing
- ASTER temperature data integration
- Multi-sensor temperature analysis

### 🌿 services/vegetation.py
- NDVI (Normalized Difference Vegetation Index) calculation
- EVI (Enhanced Vegetation Index) computation
- Vegetation health assessment

### 🔥 services/suhi.py
- **Core SUHI algorithms**:
  - `compute_pixel_suhi()`: Pixel-level SUHI calculation
  - `compute_zonal_suhi()`: Zone-based SUHI analysis
  - `compute_day_night_suhi()`: Day/night comparison
- **Error metrics**: RMSE, MAE, bias calculation
- **Temporal analysis**: Multi-year trend detection

### 📊 services/visualization.py
- **SUHIChartGenerator**: Professional chart creation
- **Heat map generation**: GIS-style temperature maps
- **Comparative plots**: Multi-city analysis
- **Statistical visualizations**: Distribution plots, correlations

### 📋 services/reporting.py
- HTML report generation
- PDF export capabilities
- Comprehensive analysis summaries
- Error and validation reports

### 📈 services/analyzer.py
- **SUHIAnalyzer**: Comprehensive statistical analysis
- Temporal trend analysis
- Regional comparisons
- Statistical significance testing

### ⚙️ services/pipeline.py
- **run_comprehensive_analysis()**: Main orchestration function
- Multi-step analysis workflow
- Error handling and validation
- Results aggregation

## 📈 Analysis Workflow

### 1. Data Collection
- Load MODIS LST data (day/night)
- Process Landsat thermal imagery
- Extract ESRI land cover classifications
- Calculate vegetation indices

### 2. SUHI Computation
- Define urban and rural zones
- Calculate temperature differences
- Apply statistical corrections
- Validate results with error metrics

### 3. Temporal Analysis
- Compare 2017 vs 2024 data
- Identify warming/cooling trends
- Assess seasonal variations
- Calculate annual change rates

### 4. Visualization & Reporting
- Generate heat maps and charts
- Create comparative analyses
- Export professional reports
- Compile statistical summaries

## 🏙️ Supported Cities

The analysis covers 14 major cities across Uzbekistan:

| City | Province | Coordinates | Buffer (km) |
|------|----------|-------------|-------------|
| **Tashkent** | Capital | 41.30°N, 69.24°E | 25 |
| **Samarkand** | Samarkand | 39.65°N, 66.96°E | 20 |
| **Bukhara** | Bukhara | 39.77°N, 64.43°E | 15 |
| **Andijan** | Andijan | 40.79°N, 72.34°E | 15 |
| **Namangan** | Namangan | 41.00°N, 71.67°E | 15 |
| **Fergana** | Fergana | 40.38°N, 71.79°E | 15 |
| **Nukus** | Karakalpakstan | 42.47°N, 59.61°E | 15 |
| **Qarshi** | Kashkadarya | 38.86°N, 65.79°E | 15 |
| **Termez** | Surxondaryo | 37.22°N, 67.28°E | 12 |
| **Jizzakh** | Jizzakh | 40.12°N, 67.84°E | 12 |
| **Navoiy** | Navoiy | 40.08°N, 65.38°E | 15 |
| **Gulistan** | Sirdaryo | 40.48°N, 68.78°E | 10 |
| **Urgench** | Xorazm | 41.55°N, 60.63°E | 12 |
| **Nurafshon** | Tashkent Region | 41.56°N, 69.68°E | 8 |

## 📊 Output Files

### 📈 Visualizations
- `{city}_heat_map.png`: Professional temperature heat maps
- `{city}_day_night_suhi_{year}.png`: Day/night comparisons
- `multi_city_landcover_comparison_{timestamp}.png`: Regional analysis
- `statistical_summary_{timestamp}.png`: Statistical distributions

### 📋 Reports
- `comprehensive_suhi_analysis_{timestamp}.json`: Statistical summary
- `{city}_{year}_results.json`: Individual city analysis
- `{city}_annual_suhi_trends.json`: Temporal trend data

### 📁 Raw Data
- Processed satellite imagery
- Temperature data matrices
- Land cover classifications
- Validation metrics

## 🔧 Configuration

### Analysis Parameters
```python
ANALYSIS_CONFIG = {
    'years': [2017, 2024],
    'months': [6, 7, 8],  # Summer months
    'cloud_cover_threshold': 20,
    'resolution_meters': 1000,
    'confidence_level': 0.95
}
```

### Custom City Analysis
```python
# Add new city to services/utils.py
UZBEKISTAN_CITIES["YourCity"] = {
    "lat": 40.0,
    "lon": 65.0,
    "buffer_km": 15,
    "description": "Your city description"
}
```

## 🛠️ Development

### Project Structure Best Practices
- **Modular design**: Each service has a single responsibility
- **Error handling**: Comprehensive try/catch blocks
- **Type hints**: Full typing support for better IDE experience
- **Documentation**: Docstrings for all functions and classes

### Adding New Analysis
1. Create function in appropriate service module
2. Add to pipeline.py orchestration
3. Update visualization.py for new charts
4. Add tests in test files

### Contributing
1. Follow the established service-oriented architecture
2. Add comprehensive error handling
3. Include type hints and docstrings
4. Test with multiple cities before committing

## 📚 Scientific Background

### Surface Urban Heat Island (SUHI)
SUHI represents the temperature difference between urban and surrounding rural areas, measured via satellite Land Surface Temperature (LST) data.

**Formula**: `SUHI = LST_urban_mean - LST_rural_mean`

### Data Sources
- **MODIS**: 1km resolution, daily global coverage
- **Landsat**: 30m resolution, 16-day revisit
- **ASTER**: 90m resolution, on-demand acquisition
- **ESRI Land Cover**: 10m resolution annual classifications

### Validation Methods
- Root Mean Square Error (RMSE)
- Mean Absolute Error (MAE)
- Bias assessment
- Statistical significance testing

## 📄 License

This project is developed for research purposes studying urban climate patterns in Uzbekistan. Please cite appropriately if used in academic work.

## 🤝 Support

For issues, questions, or contributions:
1. Check existing documentation
2. Review the services/ module structure
3. Test with a single city first
4. Ensure Google Earth Engine authentication is working


**Last Updated**: August 2025  
**Version**: 2.0 (Modular Architecture)  
**Python**: 3.8+  
**Key Dependencies**: earthengine-api, pandas, matplotlib, plotly

## Auxiliary data — biomass model (short note)

The auxiliary data runner produces seasonal NDVI/EVI and Landsat-based LST rasters and computes a simple NDVI→biomass estimate used for quick comparisons across cities and seasons.

- Model type: a small, configurable function converts mean NDVI to biomass (t/ha). The default preset is `central_asia`, which uses an FVC-style scaling (fractional vegetation cover derived from NDVI) and a conservative maximum biomass value appropriate for semi-arid/steppe landscapes.
- Presets available: `arid`, `central_asia`, `semiarid`, `mesic`, and a `linear_example` for testing. These are heuristics and not calibrated field models.
- Caveat: this is a proxy for rapid analysis and visualization. For research-grade biomass estimates, supply a locally calibrated model (coefficients or an empirical formula) and replace the preset values or implement a model fit using field data.

How to change: edit `services/auxiliary_data.py`, function `ndvi_to_biomass_model(...)` and choose a different preset or provide `params` to tune the conversion. Future work: expose preset selection as a CLI flag or per-city configuration.
