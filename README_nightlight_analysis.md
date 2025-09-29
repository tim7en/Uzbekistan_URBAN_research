# Uzbekistan Regional Nightlight Analysis

This directory contains a comprehensive analysis system for comparing nighttime lights between Uzbekistan cities and their regional contexts from 2017-2024.

## 📋 Overview

The analysis compares:
- **City + buffer zones** vs **regional averages** 
- **All major Uzbekistan regions** including Andijan, Bukhara, Navoi, and others
- **Complete temporal coverage** from 2017 to 2024
- **VIIRS DNB monthly composites** for consistent nightlight data

## 🗂️ Files Description

### Main Analysis Scripts

1. **`run_uzbekistan_nightlight_regional_analysis.py`** - Main comprehensive analysis script
2. **`test_regional_nightlight_analysis.py`** - Test script to verify functionality
3. **`analyze_nightlight_results.py`** - Quick summary analysis of results

### Supporting Scripts
- **`run_nightlight_unit.py`** - Original nightlight analysis (existing)
- Other analysis modules in `services/` directory

## 🚀 Quick Start

### 1. Test the System
```bash
python test_regional_nightlight_analysis.py
```
This will verify:
- Google Earth Engine connectivity
- Regional boundary retrieval  
- VIIRS data loading
- Basic statistics computation

### 2. Run Sample Analysis
```bash
# Analyze 3 cities for 2022-2024
python run_uzbekistan_nightlight_regional_analysis.py --cities Tashkent Andijan Bukhara --start-year 2022 --end-year 2024
```

### 3. Run Full Analysis
```bash
# Analyze all cities for complete period (2017-2024)
python run_uzbekistan_nightlight_regional_analysis.py

# Or specify custom parameters
python run_uzbekistan_nightlight_regional_analysis.py --cities Tashkent Samarkand Bukhara --start-year 2017 --end-year 2024
```

### 4. Analyze Results
```bash
python analyze_nightlight_results.py
```

## 📊 Output Files

The analysis generates several output files in `suhi_analysis_output/nightlight_regional_analysis/`:

### Data Files
- **`uzbekistan_nightlight_regional_analysis.csv`** - Complete results dataset
- **`complete_results.json`** - Full JSON results with metadata
- **Individual city directories** - Per-city analysis JSON files

### Visualizations  
- **`nightlight_analysis_comprehensive.png`** - 4-panel comprehensive analysis
- **`nightlight_ratio_heatmap.png`** - City-to-region ratios heatmap
- **`quick_analysis_overview.png`** - Quick summary plots
- **`thumbnails/`** - Individual city thumbnail images

### Reports
- **`uzbekistan_nightlight_regional_summary.md`** - Comprehensive markdown report

## 🎯 Key Metrics

The analysis calculates:

### Basic Statistics
- Mean radiance (nanoWatts/cm²/sr)
- Median radiance  
- Standard deviation
- Pixel count
- Min/max values

### Spatial Metrics
- **Lit area** (km² above 1.0 threshold)
- **City-to-region ratio** - How much brighter cities are vs regions
- **City-background difference** - Urban vs rural contrast

### Temporal Analysis
- **Growth trends** over time
- **Ratio changes** between years
- **Comparative development** patterns

## 🗺️ Regional Coverage

The analysis covers all major Uzbekistan administrative regions:

| Region | Capital City |
|--------|-------------|
| Andijan Region | Andijan |
| Bukhara Region | Bukhara |
| Fergana Region | Fergana |
| Jizzakh Region | Jizzakh |
| Kashkadarya Region | Qarshi |
| Khorezm Region | Urgench |
| Namangan Region | Namangan |
| Navoi Region | Navoiy |
| Republic of Karakalpakstan | Nukus |
| Samarkand Region | Samarkand |
| Surkhandarya Region | Termez |
| Syrdarya Region | Gulistan |
| Tashkent Region | Nurafshon |
| Tashkent City | Tashkent |

## 📈 Sample Results

From a recent analysis (2022-2024):

**City-to-Region Ratios (2024):**
- **Bukhara**: 8.93x (highest urban concentration)
- **Andijan**: 2.83x  
- **Tashkent**: 2.46x (most balanced development)

**Growth Trends:**
- **Tashkent**: 2.50 → 2.46 (-1.9% decline)
- **Andijan**: 2.84 → 2.83 (-0.3% stable)  
- **Bukhara**: 11.87 → 8.93 (-24.7% significant decline)

## 🔧 Command Line Options

### Main Analysis Script
```bash
python run_uzbekistan_nightlight_regional_analysis.py [OPTIONS]

Options:
  --cities CITY [CITY ...]     Specific cities to analyze (default: all)
  --start-year YEAR           Start year (default: 2017)  
  --end-year YEAR             End year (default: 2024)
  --output-dir PATH           Custom output directory
  --skip-thumbnails           Skip thumbnail generation for speed
```

### Example Commands
```bash
# Analyze specific cities and years
python run_uzbekistan_nightlight_regional_analysis.py --cities Tashkent Samarkand --start-year 2020 --end-year 2024

# Fast analysis without thumbnails  
python run_uzbekistan_nightlight_regional_analysis.py --skip-thumbnails --start-year 2022

# Custom output location
python run_uzbekistan_nightlight_regional_analysis.py --output-dir /custom/path --cities Bukhara Andijan
```

## 🔍 Understanding the Results

### CSV Data Structure
| Column | Description |
|--------|-------------|
| `city` | City name |
| `year` | Analysis year |
| `region` | Administrative region name |
| `city_mean_radiance` | Average radiance in city buffer |
| `region_mean_radiance` | Average radiance in full region |
| `city_to_region_ratio` | City brightness relative to region |
| `city_lit_area_km2` | Urban lit area above threshold |
| `city_background_difference` | Urban vs rural contrast |

### Interpretation Guide
- **High ratios (>5x)**: Strong urban concentration, sparse regional development
- **Low ratios (2-3x)**: More balanced urban-regional development  
- **Declining ratios**: Regional development catching up to cities
- **Growing ratios**: Cities developing faster than regions

## 🛠️ Technical Details

### Data Sources
- **Nightlight Data**: NOAA VIIRS DNB Monthly V1 (`NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG`)
- **Administrative Boundaries**: FAO GAUL Simplified 500m (2015)
- **City Coordinates**: Pre-defined in `services/utils.py`

### Analysis Zones  
- **City Zone**: Urban center + buffer (varies by city: 8-15km radius)
- **Regional Zone**: Full administrative boundary of containing region
- **Background Zone**: Regional area excluding city buffer

### Processing Scale
- **City analysis**: 500m resolution
- **Regional analysis**: 1000m resolution  
- **Thumbnail exports**: ~1km resolution

## 🚨 Prerequisites

### Required Python Packages
- `earthengine-api` - Google Earth Engine
- `pandas` - Data analysis
- `matplotlib` - Plotting
- `seaborn` - Statistical visualizations  
- `geopandas` - Spatial data (optional)
- `rasterio` - Raster processing (optional)

### Google Earth Engine Setup
1. Create GEE account at https://earthengine.google.com/
2. Install Earth Engine: `pip install earthengine-api`
3. Authenticate: `earthengine authenticate`

## 📞 Support

For questions or issues:
1. Check the test script output: `python test_regional_nightlight_analysis.py`
2. Review existing nightlight analysis in `run_nightlight_unit.py`  
3. Check GEE authentication and quotas
4. Verify network connectivity for large downloads

## 📝 Notes

- **Processing time**: ~1-2 minutes per city-year combination
- **GEE quotas**: Monitor usage for large analyses  
- **Memory usage**: Thumbnails and large regions may require more RAM
- **Network**: Stable internet required for GEE operations