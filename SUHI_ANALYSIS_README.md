# SUHI Analysis Tools

This directory contains comprehensive tools for analyzing Surface Urban Heat Island (SUHI) data from Uzbekistan urban centers.

## 📊 Generated Analysis

The analysis has been completed and generated the following outputs:

### 📈 Visualizations
- **Professional Grid Analysis**: `suhi_analysis_output/reports/professional_suhi_analysis_*.png`
- **Temporal Analysis**: `suhi_analysis_output/reports/temporal_suhi_analysis_*.png`
- **Comprehensive Visualization**: `suhi_analysis_output/visualizations/comprehensive_suhi_analysis_*.png`
- **Interactive Dashboard**: `suhi_analysis_output/visualizations/interactive_suhi_dashboard_*.html`

### 📋 Reports
- **Detailed Report**: `suhi_analysis_output/reports/detailed_suhi_report_*.md`
- **Comprehensive Report**: `suhi_analysis_output/reports/comprehensive_suhi_analysis_*.md`

### 💾 Data Exports
- **Summary Statistics**: `suhi_analysis_output/reports/comprehensive_summary_statistics_*.csv`
- **Detailed Data Export**: `suhi_analysis_output/reports/comprehensive_data_export_*.csv`

## 🛠️ Available Tools

### 1. Professional SUHI Reporter (`professional_suhi_reporter.py`)
Generates publication-quality static visualizations with:
- 6-panel professional grid layout
- Statistical summaries and rankings
- Temporal trend analysis
- Clean, professional styling
- Export-ready PNG files

### 2. Comprehensive SUHI Analyzer (`comprehensive_suhi_analyzer.py`) 
Creates comprehensive analysis with:
- Interactive Plotly dashboards
- 11-panel detailed analysis grid
- Correlation matrices
- Accuracy assessments
- HTML interactive outputs

### 3. Quick Runner (`run_suhi_analysis.py`)
Convenience script that runs both tools sequentially.

## 🚀 Usage

### Prerequisites
Ensure you have the required packages installed:
```bash
pip install pandas numpy matplotlib seaborn scipy plotly kaleido
```

### Running the Analysis

#### Option 1: Run Complete Analysis Suite
```bash
python run_suhi_analysis.py
```

#### Option 2: Run Individual Tools
```bash
# Professional static visualizations
python professional_suhi_reporter.py

# Comprehensive interactive analysis  
python comprehensive_suhi_analyzer.py
```

## 📁 Data Structure

The tools expect data in the following structure:
```
suhi_analysis_output/
├── data/
│   ├── {City}_2017_results.json
│   ├── {City}_2024_results.json
│   └── {City}_annual_suhi_trends.json
├── reports/           # Generated reports and static images
└── visualizations/    # Generated interactive visualizations
```

## 📊 Key Features

### Professional Grid Visualization
- **Panel A**: SUHI Intensity Comparison (2017 vs 2024)
- **Panel B**: SUHI Change Distribution  
- **Panel C**: Urban Area Expansion Rates
- **Panel D**: Temperature Trends Relationship
- **Panel E**: Statistical Distribution (Box plots)
- **Panel F**: Key Findings Summary

### Temporal Analysis
- Individual city trend analysis
- Multi-year SUHI evolution
- Urban vs rural temperature trends
- Regression trend lines with statistics

### Interactive Dashboard
- Plotly-based interactive charts
- Hover information and zoom capabilities
- Correlation heatmaps
- Multi-dimensional scatter plots

## 📈 Analysis Results Summary

Based on the 2017-2024 analysis of 14 Uzbekistan cities:

### Key Findings
- **Average SUHI Change**: +0.551°C
- **Cities with Increasing SUHI**: 10 out of 14
- **Cities with Decreasing SUHI**: 4 out of 14

### Priority Cities (Highest SUHI Increase)
1. **Tashkent**: +2.109°C (requires immediate attention)
2. **Bukhara**: +1.348°C 
3. **Termez**: +1.298°C

### Best Performing Cities (SUHI Decrease)
1. **Qarshi**: -0.539°C
2. **Nukus**: -0.438°C
3. **Urgench**: -0.172°C
4. **Andijan**: -0.123°C

## 🔄 Regenerating Analysis

To regenerate the analysis with updated data:

1. Ensure new data files are in `suhi_analysis_output/data/`
2. Run the analysis tools
3. Check output directories for new timestamped files

## 🎨 Customization

### Modifying Visualizations
- Edit color schemes in the `colors` dictionary
- Adjust figure sizes in `figsize` parameters
- Modify subplot layouts in `add_gridspec()` calls

### Adding New Analysis
- Extend the analyzer classes with new methods
- Add new panels to the grid layouts
- Include additional statistical calculations

## 📞 Support

For questions or issues with the analysis tools, check:
1. Data file formats match expected JSON structure
2. All required packages are installed
3. File paths are accessible
4. Python environment is properly configured

## 🏷️ File Naming Convention

Generated files use timestamp format: `YYYYMMDD_HHMMSS`
- Example: `professional_suhi_analysis_20250819_232506.png`

This ensures each analysis run creates unique files without overwriting previous results.
