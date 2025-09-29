# Uzbekistan Nightlight Analysis - Comprehensive Report

Generated: 2025-09-29 18:22:25

## Dataset Overview

- **Cities Analyzed**: 14
- **Years Covered**: 2017-2024
- **Total Records**: 112
- **Administrative Regions**: 13

## Data Quality

✅ **No missing data detected**

## Key Findings

### Top 5 Brightest Cities (Average 2017-2024)

1. **Tashkent**: 14.4 nW/cm²/sr
2. **Samarkand**: 8.1 nW/cm²/sr
3. **Qarshi**: 5.7 nW/cm²/sr
4. **Termez**: 5.4 nW/cm²/sr
5. **Andijan**: 5.1 nW/cm²/sr

### Highest City-to-Regional Contrasts

1. **Navoiy** (2020): 21.7x brighter than regional background
2. **Tashkent** (2021): 16.1x brighter than regional background
3. **Samarkand** (2022): 15.6x brighter than regional background
4. **Jizzakh** (2022): 13.7x brighter than regional background
5. **Bukhara** (2022): 13.2x brighter than regional background

## Regional Analysis

### Administrative Regions by City

- **Andijan**: Andijan Region
- **Bukhara**: Bukhara Region
- **Fergana**: Fergana Region
- **Jizzakh**: Jizzakh Region
- **Qarshi**: KashKadarya Region
- **Urgench**: Khorezm Region
- **Namangan**: Namangan Region
- **Navoiy**: Navoi Region
- **Nukus**: Republic of Karakalpakstan
- **Samarkand**: Samarkand Region
- **Termez**: Surkhandarya Region
- **Gulistan**: Syrdarya Region
- **Nurafshon**: Tashkent Region
- **Tashkent**: Tashkent Region

## Data Files

- **Comprehensive CSV**: `uzbekistan_nightlight_regional_analysis.csv`
- **Individual JSON files**: Available in city subdirectories
- **Visualizations**: `comprehensive_nightlight_analysis.png`

## Analysis Methodology

This analysis compares urban nightlight intensities at city centers (using circular buffers) 
against their respective administrative region backgrounds using:

- **Data Source**: VIIRS DNB Monthly Composites (Google Earth Engine)
- **Administrative Boundaries**: FAO GAUL Simplified 500m (2015, Level 1)
- **City Approach**: Center points + circular buffers (8-15km radius)
- **Regional Background**: Administrative boundaries excluding city buffers

