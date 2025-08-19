# Error Analysis Charts - SUHI Research

This directory contains comprehensive error analysis visualizations extracted from the SUHI uncertainty assessment report. All charts compare 2017 vs 2024 data across 14 Uzbekistan cities.

## 📊 Chart Overview

### Error_01: SUHI with Error Bars (2017 vs 2024)
- **File**: `error_01_suhi_with_error_bars_2017_vs_2024.html/png`
- **Description**: SUHI intensity measurements with standard error bars for all cities
- **Key Features**: 
  - Blue circles for 2017, orange squares for 2024
  - Error bars show ±1 standard error
  - Zero reference line for heating/cooling interpretation

### Error_02: Confidence Intervals (2017 vs 2024)
- **File**: `error_02_confidence_intervals_2017_vs_2024.html/png`
- **Description**: 95% confidence intervals for SUHI measurements
- **Key Features**: 
  - Side-by-side comparison panels
  - Asymmetric error bars showing true confidence intervals
  - Statistical significance assessment capability

### Error_03: Relative Error Analysis (2017 vs 2024)
- **File**: `error_03_relative_error_analysis_2017_vs_2024.html/png`
- **Description**: Relative error percentages with color-coded quality assessment
- **Key Features**: 
  - Green ≤10% (Low Error), Orange 10-30% (Medium Error), Red >30% (High Error)
  - Reference lines at 10% and 30% thresholds
  - Grouped bars for direct year comparison

### Error_04: Classification Accuracy (2017 vs 2024)
- **File**: `error_04_classification_accuracy_2017_vs_2024.html/png`
- **Description**: Agreement scores between ESRI land cover and reference datasets
- **Key Features**: 
  - Four-panel comparison: ESA, GHSL, MODIS agreements, and 2024 dataset comparison
  - Validation of urban classification accuracy
  - Cross-dataset consistency assessment

### Error_05: Uncertainty vs SUHI Magnitude
- **File**: `error_05_uncertainty_vs_suhi_magnitude.html/png`
- **Description**: Relationship between SUHI intensity and measurement uncertainty
- **Key Features**: 
  - Scatter plot with city labels
  - Trend lines for both years
  - Correlation analysis between magnitude and error

### Error_06: Sample Size vs Uncertainty
- **File**: `error_06_sample_size_vs_uncertainty.html/png`
- **Description**: Impact of pixel count on measurement uncertainty
- **Key Features**: 
  - Left panel: Urban pixels vs Standard Error
  - Right panel: Total pixels vs Relative Error
  - Statistical power assessment

### Error_07: Error Summary Dashboard (2017 vs 2024)
- **File**: `error_07_summary_dashboard_2017_vs_2024.html/png`
- **Description**: Comprehensive uncertainty overview in dashboard format
- **Key Features**: 
  - Error distribution histograms
  - Accuracy score box plots
  - High vs low error city rankings
  - Temporal error change analysis

## 📈 Data Sources

- **Primary Data**: SUHI analysis results from `/suhi_analysis_output/data/`
- **Error Report**: `/suhi_analysis_output/error_analysis/error_report_20250819_221646.md`
- **Coverage**: 14 Uzbekistan cities (Andijan, Bukhara, Fergana, Jizzakh, Karshi, Kokand, Margilan, Namangan, Navoiy, Nukus, Samarkand, Tashkent, Termez, Urgench)
- **Time Period**: 2017 vs 2024 comparison
- **Datasets**: ESA Land Cover, GHSL Built-up, MODIS Land Cover validation

## 🎯 Key Insights from Error Analysis

### Statistical Quality
- **Standard Errors**: Range from 0.001°C to 0.156°C across cities
- **Confidence Intervals**: 95% CI ranges typically ±0.002°C to ±0.306°C
- **Relative Errors**: Most cities show <30% relative error (acceptable range)

### Classification Accuracy
- **ESA Agreement**: Generally high consistency with ESRI classifications
- **GHSL Agreement**: Strong built-up area classification accuracy
- **MODIS Agreement**: Good land cover classification validation

### Temporal Changes (2017→2024)
- **Error Evolution**: Most cities show stable or improving measurement precision
- **Uncertainty Patterns**: Larger cities tend to have lower relative errors
- **Sample Size Effects**: More pixels generally lead to lower uncertainty

## 🔧 Technical Details

- **Generator**: `error_chart_generator.py`
- **Format**: Interactive HTML + High-resolution PNG exports
- **Styling**: Professional Plotly visualizations with consistent color schemes
- **Data Processing**: Automatic parsing from markdown report with robust encoding handling

## 📚 Related Files

- **Main Analysis**: `/dashboard_deliverables/main_dashboard.py`
- **Individual Charts**: `/reporting/individual_charts/`
- **Dashboard Charts**: `/reporting/dashboard_charts/`
- **Comprehensive Reports**: `/dashboard_deliverables/reports/`

---

*Generated on August 19, 2025 - Part of comprehensive SUHI uncertainty quantification analysis*
