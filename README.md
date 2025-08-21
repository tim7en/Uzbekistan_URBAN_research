# 🏙️ Uzbekistan Urban Research Project

## Comprehensive Analysis of Urban Heat Islands, Night Lights, and Urban Expansion (2017-2024)

This repository contains a production-ready, modular analysis system for studying urban development patterns in Uzbekistan using satellite remote sensing data and Google Earth Engine.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Analysis Components](#analysis-components)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Output Structure](#output-structure)
- [Services Architecture](#services-architecture)
- [Data Sources](#data-sources)
- [Contributing](#contributing)

---

## 🎯 Overview

This project performs comprehensive urban research analysis for major cities in Uzbekistan, focusing on three key aspects:

1. **🌙 Night Lights Analysis** - Urban development patterns using VIIRS nighttime imagery
2. **🔥 Surface Urban Heat Island (SUHI)** - Urban temperature dynamics using MODIS LST data  
3. **🏗️ Urban Expansion** - Land cover change analysis using ESRI Global Land Cover data

### Key Capabilities

- **Multi-temporal Analysis**: 2017-2024 time series analysis
- **Multi-city Coverage**: 14 major Uzbekistan cities including Tashkent, Samarkand, Bukhara
- **Configurable Resolution**: User-adjustable spatial resolution (100m-1km)
- **Production Ready**: Modular, scalable architecture with comprehensive error handling
- **Automated Outputs**: Raster files, visualizations, and statistical reports
- **Testing Mode**: Quick analysis on 2-3 cities for development/testing

---

## ✨ Features

### 🔧 Technical Features
- **Modular Services Architecture** - Clean separation of concerns
- **Configurable Resolution** - Adjust spatial detail vs processing speed
- **Synchronous Processing** - Optimized Earth Engine calls
- **Comprehensive Error Handling** - Robust failure recovery
- **Automated Raster Export** - GeoTIFF outputs for GIS software
- **Statistical Analysis** - Trend analysis and correlation studies
- **Professional Visualizations** - Publication-ready charts and maps

### 📊 Analysis Features
- **Surface Urban Heat Island Intensity** - Quantified UHI effects
- **Night Lights Change Detection** - Urban activity patterns
- **Urban Expansion Mapping** - Built area growth quantification
- **Multi-dataset Integration** - Cross-validated results
- **Temporal Trend Analysis** - Long-term pattern identification

---

## 🔬 Analysis Components

### 1. Night Lights Analysis
- **Data Source**: VIIRS DNB Monthly Composites
- **Time Period**: 2017-2024
- **Outputs**: 
  - Country-level night lights maps
  - City-level change analysis
  - Radiance change statistics
  - GeoTIFF exports for early/late years and change maps

### 2. Surface Urban Heat Island (SUHI) Analysis
- **Data Source**: MODIS Land Surface Temperature (MOD11A2)
- **Time Period**: 2017-2024 (warm months: June-August)
- **Methodology**: Urban vs rural temperature differential
- **Outputs**:
  - Annual SUHI intensity maps
  - Urban temperature rasters
  - Multi-year trend analysis
  - Statistical correlation studies

### 3. Urban Expansion Analysis
- **Data Source**: ESRI Global Land Cover (10m resolution)
- **Time Period**: 2017-2024
- **Methodology**: Built area change detection
- **Outputs**:
  - Land cover classification maps
  - Urban change detection maps
  - Built area statistics
  - Expansion/contraction quantification

---

## 🚀 Installation

### Prerequisites
- Python 3.8+
- Google Earth Engine account
- Required packages (see installation steps)

### Setup Instructions

1. **Clone the repository**:
```bash
git clone https://github.com/tim7en/Uzbekistan_URBAN_research.git
cd Uzbekistan_URBAN_research
```

2. **Install dependencies**:
```bash
pip install earthengine-api pandas numpy matplotlib seaborn scipy pathlib
```

3. **Authenticate Google Earth Engine**:
```bash
earthengine authenticate
```

4. **Verify installation**:
```python
python -c "import ee; ee.Initialize(project='your-project-id'); print('GEE Ready!')"
```

---

## 💻 Usage

### Quick Start (Testing Mode)

Run analysis on 3 cities with 500m resolution:

```python
from main_modular import run_analysis

# Test run with 3 cities
results = run_analysis(
    resolution_m=500,
    testing_mode=True,
    test_cities_count=3
)
```

### Full Production Analysis

Run complete analysis on all 14 cities:

```python
from main_modular import run_analysis

# Full analysis
results = run_analysis(
    resolution_m=500,
    testing_mode=False
)
```

### Command Line Usage

```bash
# Run with default settings (testing mode)
python main_modular.py

# For production analysis, edit TESTING_MODE = False in main_modular.py
```

### Alternative Legacy Mode

Use original analysis scripts:

```bash
python main.py  # Original monolithic version
python NightLightVisual.py  # Night lights only
python Stats.py  # Statistical analysis only
```

---

## ⚙️ Configuration

### Resolution Settings

Choose resolution based on your needs:

```python
# High detail, slower processing
resolution_m = 100  

# Balanced (recommended)
resolution_m = 500  

# Fast processing, lower detail
resolution_m = 1000
```

### City Selection

Modify cities in `services/config.py`:

```python
UZBEKISTAN_CITIES = {
    "Tashkent": {"lat": 41.2995, "lon": 69.2401, "buffer_m": 15000},
    "Samarkand": {"lat": 39.6542, "lon": 66.9597, "buffer_m": 12000},
    # Add more cities as needed
}
```

### Analysis Parameters

Customize analysis in `services/config.py`:

```python
class AnalysisConfig:
    def __init__(self):
        self.years = list(range(2017, 2025))  # Analysis years
        self.warm_months = [6, 7, 8]  # Peak SUHI months
        self.resolution_m = 500  # Spatial resolution
        # ... other parameters
```

---

## 📁 Output Structure

```
uzbekistan_urban_analysis_output/
├── data/                          # Raw analysis data (JSON)
├── night_lights/                  # Night lights analysis
│   ├── city_results/
│   └── comprehensive_results.json
├── temperature/                   # SUHI analysis
│   ├── city_suhi_maps/
│   └── trend_analysis.json
├── urban_expansion/               # Urban expansion analysis
│   ├── landcover_maps/
│   └── expansion_statistics.json
├── raster_outputs/               # GeoTIFF exports
│   ├── suhi_maps/
│   ├── landcover_maps/
│   └── night_lights_maps/
├── visualizations/               # Charts and plots
│   ├── suhi_analysis_visualization.png
│   ├── night_lights_visualization.png
│   ├── urban_expansion_visualization.png
│   └── comprehensive_dashboard.png
├── statistical/                  # Statistical analysis
└── reports/                      # Generated reports
```

### Key Output Files

- **Raster Files**: GeoTIFF format for GIS software
- **Visualizations**: High-resolution PNG charts
- **Data Files**: JSON format for further analysis
- **Reports**: Markdown summaries with key insights

---

## 🏗️ Services Architecture

The project uses a modular services-based architecture:

```
services/
├── config.py                    # Configuration management
├── utils/
│   ├── gee_utils.py            # Google Earth Engine utilities
│   └── output_utils.py         # File/directory management
├── data_processing/
│   ├── temperature.py          # LST data processing
│   └── landcover.py           # Land cover processing
├── analysis/
│   ├── night_lights.py        # Night lights analysis
│   ├── suhi.py                # SUHI analysis
│   └── urban_expansion.py     # Urban expansion analysis
└── visualization/
    └── generators.py           # Visualization creation
```

### Service Benefits

- **Modularity**: Independent, reusable components
- **Scalability**: Easy to add new analysis types
- **Maintainability**: Clear separation of concerns
- **Testing**: Individual services can be tested independently
- **Configuration**: Centralized parameter management

---

## 📊 Data Sources

### Primary Datasets

| Dataset | Source | Resolution | Time Period | Purpose |
|---------|--------|------------|-------------|---------|
| VIIRS DNB | NOAA | 500m | 2017-2024 | Night lights analysis |
| MODIS LST | NASA Terra/Aqua | 1km | 2017-2024 | Temperature analysis |
| ESRI Global LULC | ESRI | 10m | 2017-2024 | Land cover analysis |
| Dynamic World | Google | 10m | 2017-2024 | Land cover validation |
| GHSL | JRC | 10m | 2020 | Urban area reference |

### Data Quality Assurance

- **Cloud masking** for optical datasets
- **Quality flags** for MODIS LST data
- **Multi-dataset validation** for land cover
- **Temporal consistency** checks
- **Spatial accuracy** validation

---

## 🎯 Cities Analyzed

The analysis covers 14 major Uzbekistan cities:

### National & Republic Capitals
- **Tashkent** (National Capital) - 15km buffer
- **Nukus** (Karakalpakstan Capital) - 10km buffer

### Regional Capitals
- **Samarkand** - 12km buffer
- **Bukhara** - 10km buffer  
- **Andijan** - 12km buffer
- **Namangan** - 12km buffer
- **Fergana** - 12km buffer
- **Jizzakh** - 8km buffer
- **Qarshi** - 8km buffer
- **Navoiy** - 10km buffer
- **Termez** - 8km buffer
- **Gulistan** - 8km buffer
- **Urgench** - 10km buffer

### Additional Cities
- **Nurafshon** - 8km buffer

---

## 📈 Results Interpretation

### SUHI Intensity Classifications

- **Strong SUHI**: >2°C temperature difference
- **Moderate SUHI**: 0-2°C temperature difference  
- **Cooling Effect**: <0°C (rural warmer than urban)

### Night Lights Change Interpretation

- **Positive change**: Increasing urban activity/development
- **Negative change**: Decreasing activity or infrastructure changes
- **Large increases** (>50%): Rapid urban development

### Urban Expansion Metrics

- **Built area change**: Absolute area change in km²
- **Expansion rate**: km²/year growth rate
- **Relative change**: Percentage change from baseline

---

## 🧪 Testing and Validation

### Testing Mode Features

- **Quick validation**: 3-city subset for rapid testing
- **Resolution testing**: Verify different spatial scales  
- **Error handling**: Test failure recovery mechanisms
- **Output validation**: Verify all expected files are created

### Quality Checks

- **Data availability**: Verify all datasets are accessible
- **Spatial consistency**: Check coordinate systems and projections
- **Temporal coverage**: Validate data availability across analysis period
- **Statistical validity**: Check for reasonable value ranges

---

## 📝 Contributing

### Development Guidelines

1. **Follow services architecture**: Add new analysis types as services
2. **Maintain configuration system**: Use centralized config management
3. **Add comprehensive error handling**: Graceful failure recovery
4. **Include documentation**: Document all functions and services
5. **Test thoroughly**: Use testing mode before production runs

### Adding New Analysis Types

1. Create service in appropriate `services/` subdirectory
2. Add configuration parameters to `services/config.py`
3. Create visualization generator in `services/visualization/`
4. Update main analysis workflow
5. Add output directory structure

### Code Style

- Use type hints for function signatures
- Follow PEP 8 style guidelines  
- Add docstrings for all functions
- Use meaningful variable names
- Include error handling with informative messages

---

## ❓ Troubleshooting

### Common Issues

**Google Earth Engine Authentication**:
```bash
earthengine authenticate
# Follow browser authentication flow
```

**Memory Errors**:
```python
# Increase resolution to reduce memory usage
resolution_m = 1000  # or higher
```

**Missing Dependencies**:
```bash
pip install earthengine-api pandas numpy matplotlib seaborn scipy
```

**Dataset Access Errors**:
- Verify GEE project permissions
- Check dataset availability in GEE Code Editor
- Ensure project quotas are sufficient

### Performance Optimization

- **Use testing mode** for development and debugging
- **Increase resolution** (e.g., 1000m) for faster processing
- **Process fewer years** by modifying `analysis_config.years`
- **Reduce city count** in testing mode

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📧 Contact

For questions, issues, or collaboration opportunities:

- **Repository**: [https://github.com/tim7en/Uzbekistan_URBAN_research](https://github.com/tim7en/Uzbekistan_URBAN_research)
- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Discussions**: Use GitHub Discussions for general questions

---

## 🙏 Acknowledgments

- **Google Earth Engine** for cloud-based geospatial processing
- **NASA MODIS Science Team** for LST data
- **NOAA VIIRS Team** for night lights data  
- **ESRI** for global land cover data
- **European Space Agency** for additional validation datasets

---

## 📊 Project Status

- ✅ **Core Analysis**: Complete and validated
- ✅ **Modular Architecture**: Implemented
- ✅ **Production Ready**: Tested and optimized
- ✅ **Documentation**: Comprehensive
- ✅ **Testing Framework**: Implemented
- 🔄 **Continuous Improvement**: Ongoing optimization

---

*Last Updated: August 2024*
*Version: 2.0 - Modular Architecture*