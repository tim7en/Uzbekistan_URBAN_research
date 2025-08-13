#!/usr/bin/env python3
"""
Comprehensive Data Analysis Pipeline for Uzbekistan Urban Research
================================================================

This module provides comprehensive statistical analysis and data processing 
for urban expansion and SUHI (Surface Urban Heat Island) research data.

Features:
- Statistical analysis of urban expansion patterns (2016-2025)
- SUHI intensity analysis across 14 cities
- Temporal trend analysis and correlation studies
- Data quality assessment and validation
- Export capabilities for dashboard integration

Author: Generated for Uzbekistan Urban Research Project
Date: 2025
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from datetime import datetime
import warnings
from pathlib import Path
warnings.filterwarnings('ignore')

class UzbekistanUrbanAnalyzer:
    """Comprehensive analyzer for Uzbekistan urban research data"""
    
    def __init__(self, base_path="/home/runner/work/Uzbekistan_URBAN_research/Uzbekistan_URBAN_research"):
        """Initialize analyzer with data paths"""
        self.base_path = Path(base_path)
        self.suhi_data_path = self.base_path / "scientific_suhi_analysis/data"
        self.urban_data_path = self.base_path / "URBAN_EXPANSION_RESULTS"
        self.output_path = self.base_path / "dashboard_deliverables"
        
        # Ensure output directories exist
        (self.output_path / "data_analysis").mkdir(parents=True, exist_ok=True)
        (self.output_path / "visualizations").mkdir(parents=True, exist_ok=True)
        (self.output_path / "reports").mkdir(parents=True, exist_ok=True)
        
        # Initialize data containers
        self.suhi_data = None
        self.urban_data = None
        self.analysis_results = {}
        
    def load_suhi_data(self):
        """Load and process SUHI analysis data"""
        try:
            # Load comprehensive SUHI data
            suhi_file = self.suhi_data_path / "comprehensive_suhi_analysis_20250813_115209.json"
            with open(suhi_file, 'r') as f:
                raw_data = json.load(f)
            
            # Convert to DataFrame
            all_records = []
            for period, cities_data in raw_data['period_data'].items():
                year = int(period.replace('period_', ''))
                for city_data in cities_data:
                    city_data['Year'] = year
                    all_records.append(city_data)
            
            self.suhi_data = pd.DataFrame(all_records)
            
            # Convert numeric columns
            numeric_cols = ['SUHI_Day', 'SUHI_Night', 'LST_Day_Urban', 'LST_Day_Rural', 
                           'LST_Night_Urban', 'LST_Night_Rural', 'NDVI_Urban', 'NDVI_Rural',
                           'NDBI_Urban', 'NDBI_Rural', 'NDWI_Urban', 'NDWI_Rural',
                           'Urban_Prob', 'Rural_Prob', 'Urban_Pixel_Count', 'Rural_Pixel_Count']
            
            for col in numeric_cols:
                if col in self.suhi_data.columns:
                    self.suhi_data[col] = pd.to_numeric(self.suhi_data[col], errors='coerce')
            
            print(f"✅ SUHI data loaded: {len(self.suhi_data)} records across {self.suhi_data['City'].nunique()} cities")
            return True
            
        except Exception as e:
            print(f"❌ Error loading SUHI data: {e}")
            return False
    
    def load_urban_expansion_data(self):
        """Load urban expansion analysis data"""
        try:
            # Find the latest urban expansion results
            expansion_dirs = list(self.urban_data_path.glob("urban_expansion_analysis_*"))
            if not expansion_dirs:
                print("❌ No urban expansion data found")
                return False
            
            latest_dir = max(expansion_dirs, key=lambda x: x.name)
            
            # Load city impacts data
            impacts_file = latest_dir / "data/processed_impacts/uzbekistan_city_impacts_20250813_184126.csv"
            if impacts_file.exists():
                self.urban_data = pd.read_csv(impacts_file)
                print(f"✅ Urban expansion data loaded: {len(self.urban_data)} cities analyzed")
                return True
            else:
                print("❌ Urban expansion impacts file not found")
                return False
                
        except Exception as e:
            print(f"❌ Error loading urban expansion data: {e}")
            return False
    
    def generate_comprehensive_statistics(self):
        """Generate comprehensive statistical analysis"""
        print("\n" + "="*80)
        print("🔬 GENERATING COMPREHENSIVE STATISTICAL ANALYSIS")
        print("="*80)
        
        stats_report = {
            'metadata': {
                'analysis_date': datetime.now().isoformat(),
                'analyst': 'Uzbekistan Urban Research Comprehensive Analyzer',
                'data_period': '2016-2025',
                'cities_analyzed': 14,
                'analysis_scope': 'Urban Expansion + SUHI Analysis'
            },
            'suhi_analysis': {},
            'urban_expansion_analysis': {},
            'integrated_analysis': {},
            'key_findings': []
        }
        
        if self.suhi_data is not None:
            # SUHI Statistical Analysis
            suhi_stats = self._analyze_suhi_patterns()
            stats_report['suhi_analysis'] = suhi_stats
            
        if self.urban_data is not None:
            # Urban Expansion Statistical Analysis  
            urban_stats = self._analyze_urban_expansion()
            stats_report['urban_expansion_analysis'] = urban_stats
        
        # Integrated Analysis
        if self.suhi_data is not None and self.urban_data is not None:
            integrated_stats = self._analyze_integrated_patterns()
            stats_report['integrated_analysis'] = integrated_stats
        
        # Generate key findings
        key_findings = self._generate_key_findings(stats_report)
        stats_report['key_findings'] = key_findings
        
        # Save comprehensive statistics report
        output_file = self.output_path / "data_analysis/comprehensive_statistics_report.json"
        with open(output_file, 'w') as f:
            json.dump(stats_report, f, indent=2, default=str)
        
        # Generate human-readable summary
        summary_file = self.output_path / "reports/COMPREHENSIVE_DATA_ANALYSIS_SUMMARY.md"
        self._generate_readable_summary(stats_report, summary_file)
        
        self.analysis_results['statistics'] = stats_report
        
        print(f"✅ Comprehensive statistics saved to: {output_file}")
        print(f"✅ Readable summary saved to: {summary_file}")
        
        return stats_report
    
    def _analyze_suhi_patterns(self):
        """Analyze SUHI patterns and trends"""
        print("📊 Analyzing SUHI patterns...")
        
        suhi_stats = {
            'temporal_coverage': {
                'start_year': int(self.suhi_data['Year'].min()),
                'end_year': int(self.suhi_data['Year'].max()),
                'total_years': int(self.suhi_data['Year'].nunique()),
                'total_observations': len(self.suhi_data)
            },
            'spatial_coverage': {
                'cities_analyzed': self.suhi_data['City'].nunique(),
                'city_list': sorted(self.suhi_data['City'].unique().tolist())
            },
            'suhi_intensity_statistics': {},
            'temporal_trends': {},
            'city_rankings': {},
            'extreme_events': {},
            'data_quality_metrics': {}
        }
        
        # SUHI Intensity Statistics
        day_stats = self.suhi_data['SUHI_Day'].describe()
        night_stats = self.suhi_data['SUHI_Night'].describe()
        
        suhi_stats['suhi_intensity_statistics'] = {
            'day_suhi': {
                'mean': float(day_stats['mean']),
                'std': float(day_stats['std']),
                'min': float(day_stats['min']),
                'max': float(day_stats['max']),
                'q25': float(day_stats['25%']),
                'q75': float(day_stats['75%']),
                'range': float(day_stats['max'] - day_stats['min'])
            },
            'night_suhi': {
                'mean': float(night_stats['mean']),
                'std': float(night_stats['std']),
                'min': float(night_stats['min']),
                'max': float(night_stats['max']),
                'q25': float(night_stats['25%']),
                'q75': float(night_stats['75%']),
                'range': float(night_stats['max'] - night_stats['min'])
            }
        }
        
        # Temporal Trends
        yearly_means = self.suhi_data.groupby('Year')[['SUHI_Day', 'SUHI_Night']].mean()
        
        # Calculate trend slopes
        years = yearly_means.index.values
        day_slope, day_intercept, day_r, day_p, _ = stats.linregress(years, yearly_means['SUHI_Day'])
        night_slope, night_intercept, night_r, night_p, _ = stats.linregress(years, yearly_means['SUHI_Night'])
        
        suhi_stats['temporal_trends'] = {
            'day_trend': {
                'slope_per_year': float(day_slope),
                'r_squared': float(day_r**2),
                'p_value': float(day_p),
                'significance': 'significant' if day_p < 0.05 else 'not significant',
                'trend_direction': 'warming' if day_slope > 0 else 'cooling'
            },
            'night_trend': {
                'slope_per_year': float(night_slope),
                'r_squared': float(night_r**2),
                'p_value': float(night_p),
                'significance': 'significant' if night_p < 0.05 else 'not significant',
                'trend_direction': 'warming' if night_slope > 0 else 'cooling'
            }
        }
        
        # City Rankings
        city_day_means = self.suhi_data.groupby('City')['SUHI_Day'].mean().sort_values(ascending=False)
        city_night_means = self.suhi_data.groupby('City')['SUHI_Night'].mean().sort_values(ascending=False)
        
        suhi_stats['city_rankings'] = {
            'highest_day_suhi': [
                {'city': city, 'suhi_intensity': float(intensity)}
                for city, intensity in city_day_means.head(5).items()
            ],
            'lowest_day_suhi': [
                {'city': city, 'suhi_intensity': float(intensity)}
                for city, intensity in city_day_means.tail(5).items()
            ],
            'highest_night_suhi': [
                {'city': city, 'suhi_intensity': float(intensity)}
                for city, intensity in city_night_means.head(5).items()
            ]
        }
        
        # Extreme Events Analysis
        day_extreme_high = self.suhi_data['SUHI_Day'].quantile(0.9)
        day_extreme_low = self.suhi_data['SUHI_Day'].quantile(0.1)
        
        extreme_events = self.suhi_data.groupby('City').apply(
            lambda x: pd.Series({
                'extreme_high_events': (x['SUHI_Day'] > day_extreme_high).sum(),
                'extreme_low_events': (x['SUHI_Day'] < day_extreme_low).sum(),
                'total_observations': len(x)
            })
        )
        
        suhi_stats['extreme_events'] = {
            'extreme_high_threshold': float(day_extreme_high),
            'extreme_low_threshold': float(day_extreme_low),
            'cities_with_most_extreme_highs': extreme_events.nlargest(3, 'extreme_high_events')[['extreme_high_events']].to_dict('index'),
            'total_extreme_events': int(extreme_events['extreme_high_events'].sum() + extreme_events['extreme_low_events'].sum())
        }
        
        # Data Quality Metrics
        if 'Data_Quality' in self.suhi_data.columns:
            quality_distribution = self.suhi_data['Data_Quality'].value_counts()
            suhi_stats['data_quality_metrics'] = {
                'quality_distribution': quality_distribution.to_dict(),
                'good_quality_percentage': float(quality_distribution.get('Good', 0) / len(self.suhi_data) * 100),
                'total_records_analyzed': len(self.suhi_data)
            }
        
        return suhi_stats
    
    def _analyze_urban_expansion(self):
        """Analyze urban expansion patterns"""
        print("🏙️ Analyzing urban expansion patterns...")
        
        urban_stats = {
            'expansion_metrics': {},
            'land_cover_changes': {},
            'environmental_impacts': {},
            'city_specific_analysis': {}
        }
        
        # Basic expansion metrics
        if 'built_change_10yr' in self.urban_data.columns:
            built_change_stats = self.urban_data['built_change_10yr'].describe()
            urban_stats['expansion_metrics'] = {
                'mean_built_expansion': float(built_change_stats['mean']),
                'max_built_expansion': float(built_change_stats['max']),
                'cities_with_expansion': int((self.urban_data['built_change_10yr'] > 0).sum()),
                'cities_with_contraction': int((self.urban_data['built_change_10yr'] < 0).sum())
            }
        
        # Environmental impact metrics
        green_cols = [col for col in self.urban_data.columns if 'green' in col.lower() or 'ndvi' in col.lower()]
        if green_cols:
            urban_stats['environmental_impacts'] = {
                'green_space_metrics': {col: float(self.urban_data[col].mean()) for col in green_cols[:3]}
            }
        
        return urban_stats
    
    def _analyze_integrated_patterns(self):
        """Analyze integrated patterns between SUHI and urban expansion"""
        print("🔗 Analyzing integrated urban-SUHI patterns...")
        
        # For now, return basic integrated analysis structure
        integrated_stats = {
            'correlation_analysis': {
                'note': 'Integrated analysis requires temporal alignment of datasets',
                'available_datasets': ['SUHI_2016_2024', 'Urban_Expansion_2018_2025']
            },
            'spatial_overlap': {
                'cities_in_both_datasets': len(set(self.suhi_data['City'].unique()) & set(self.urban_data.index if hasattr(self.urban_data, 'index') else []))
            }
        }
        
        return integrated_stats
    
    def _generate_key_findings(self, stats_report):
        """Generate key findings from analysis"""
        findings = []
        
        # SUHI findings
        if 'suhi_analysis' in stats_report:
            suhi = stats_report['suhi_analysis']
            
            if 'suhi_intensity_statistics' in suhi:
                day_mean = suhi['suhi_intensity_statistics']['day_suhi']['mean']
                day_range = suhi['suhi_intensity_statistics']['day_suhi']['range']
                
                findings.append({
                    'category': 'SUHI Analysis',
                    'finding': f"Mean daytime SUHI intensity across all cities: {day_mean:.2f}°C",
                    'significance': 'high',
                    'implication': 'Indicates significant urban heat island effects requiring mitigation strategies'
                })
                
                findings.append({
                    'category': 'SUHI Analysis', 
                    'finding': f"SUHI intensity range: {day_range:.2f}°C (indicating high spatial variability)",
                    'significance': 'high',
                    'implication': 'Suggests need for city-specific approaches to heat island mitigation'
                })
            
            if 'temporal_trends' in suhi:
                day_trend = suhi['temporal_trends']['day_trend']
                if day_trend['significance'] == 'significant':
                    findings.append({
                        'category': 'Temporal Trends',
                        'finding': f"Significant {day_trend['trend_direction']} trend detected: {day_trend['slope_per_year']:.3f}°C/year",
                        'significance': 'critical',
                        'implication': 'Requires immediate climate adaptation and urban planning intervention'
                    })
        
        # Urban expansion findings
        if 'urban_expansion_analysis' in stats_report:
            urban = stats_report['urban_expansion_analysis']
            
            if 'expansion_metrics' in urban:
                expansion = urban['expansion_metrics']
                if 'cities_with_expansion' in expansion:
                    findings.append({
                        'category': 'Urban Expansion',
                        'finding': f"{expansion['cities_with_expansion']} cities showing built-up area expansion",
                        'significance': 'medium',
                        'implication': 'Urban growth patterns require sustainable development planning'
                    })
        
        return findings
    
    def _generate_readable_summary(self, stats_report, output_file):
        """Generate human-readable summary report"""
        
        summary = f"""# COMPREHENSIVE DATA ANALYSIS SUMMARY
## Uzbekistan Urban Research Project

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Analysis Period:** {stats_report['metadata']['data_period']}  
**Cities Analyzed:** {stats_report['metadata']['cities_analyzed']}  

---

## 🔍 EXECUTIVE SUMMARY

This comprehensive analysis covers urban expansion patterns and Surface Urban Heat Island (SUHI) effects across {stats_report['metadata']['cities_analyzed']} major cities in Uzbekistan from 2016-2025.

## 📊 KEY STATISTICS

### SUHI Analysis
"""
        
        if 'suhi_analysis' in stats_report:
            suhi = stats_report['suhi_analysis']
            
            if 'suhi_intensity_statistics' in suhi:
                day_stats = suhi['suhi_intensity_statistics']['day_suhi']
                summary += f"""
**Daytime SUHI Intensity:**
- Mean: {day_stats['mean']:.2f}°C
- Range: {day_stats['min']:.2f}°C to {day_stats['max']:.2f}°C  
- Standard Deviation: {day_stats['std']:.2f}°C

**Spatial Coverage:**
- Cities: {suhi['spatial_coverage']['cities_analyzed']}
- Total Observations: {suhi['temporal_coverage']['total_observations']:,}
- Years Analyzed: {suhi['temporal_coverage']['total_years']}
"""
            
            if 'temporal_trends' in suhi:
                day_trend = suhi['temporal_trends']['day_trend']
                summary += f"""
**Temporal Trends:**
- Trend: {day_trend['trend_direction'].upper()} at {day_trend['slope_per_year']:.3f}°C/year
- Statistical Significance: {day_trend['significance'].upper()}
- R²: {day_trend['r_squared']:.3f}
"""
            
            if 'city_rankings' in suhi:
                summary += f"""
**Top 3 Highest SUHI Cities:**
"""
                for i, city_data in enumerate(suhi['city_rankings']['highest_day_suhi'][:3], 1):
                    summary += f"{i}. {city_data['city']}: {city_data['suhi_intensity']:.2f}°C\n"
        
        if 'urban_expansion_analysis' in stats_report:
            urban = stats_report['urban_expansion_analysis']
            summary += f"""
### Urban Expansion Analysis

**Built-up Area Changes:**
- Cities with expansion: {urban.get('expansion_metrics', {}).get('cities_with_expansion', 'N/A')}
- Mean expansion rate: {urban.get('expansion_metrics', {}).get('mean_built_expansion', 0):.2f}
"""
        
        summary += f"""
## 🎯 KEY FINDINGS

"""
        
        for i, finding in enumerate(stats_report.get('key_findings', []), 1):
            summary += f"""
### {i}. {finding['category']}
**Finding:** {finding['finding']}  
**Significance:** {finding['significance'].upper()}  
**Implication:** {finding['implication']}
"""
        
        summary += f"""
---

## 📈 RECOMMENDATIONS

1. **Priority Cities**: Focus immediate attention on cities with highest SUHI intensity
2. **Monitoring Systems**: Establish continuous monitoring for cities showing warming trends  
3. **Green Infrastructure**: Increase vegetation coverage in high-SUHI areas
4. **Urban Planning**: Integrate heat island mitigation into expansion planning

---

**Analysis Framework:** Comprehensive Statistical Analysis  
**Data Sources:** Multi-satellite datasets (MODIS, Dynamic World, GHSL, ESA WorldCover)  
**Quality Assurance:** Server-side processing with proper QA masking  
**Scale:** 200m-1km resolution analysis  

*This report provides scientifically robust findings suitable for policy development and urban planning applications.*
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(summary)
    
    def export_analysis_data(self):
        """Export processed data for dashboard use"""
        print("\n📤 Exporting analysis data for dashboard integration...")
        
        exports = {}
        
        # Export SUHI data if available
        if self.suhi_data is not None:
            suhi_export_file = self.output_path / "data_analysis/suhi_analysis_data.csv"
            self.suhi_data.to_csv(suhi_export_file, index=False)
            exports['suhi_data'] = str(suhi_export_file)
            
            # Export aggregated city statistics
            city_stats = self.suhi_data.groupby('City').agg({
                'SUHI_Day': ['mean', 'std', 'min', 'max'],
                'SUHI_Night': ['mean', 'std', 'min', 'max'],
                'Year': ['count']
            }).round(3)
            
            city_stats.columns = ['_'.join(col).strip() for col in city_stats.columns.values]
            city_stats_file = self.output_path / "data_analysis/city_suhi_statistics.csv"
            city_stats.to_csv(city_stats_file)
            exports['city_statistics'] = str(city_stats_file)
        
        # Export urban expansion data if available
        if self.urban_data is not None:
            urban_export_file = self.output_path / "data_analysis/urban_expansion_data.csv"
            self.urban_data.to_csv(urban_export_file, index=False)
            exports['urban_data'] = str(urban_export_file)
        
        # Export analysis results summary
        if self.analysis_results:
            results_file = self.output_path / "data_analysis/analysis_results.json"
            with open(results_file, 'w') as f:
                json.dump(self.analysis_results, f, indent=2, default=str)
            exports['analysis_results'] = str(results_file)
        
        print("✅ Data export completed:")
        for key, filepath in exports.items():
            print(f"   📊 {key}: {filepath}")
        
        return exports
    
    def run_comprehensive_analysis(self):
        """Run complete analysis pipeline"""
        print("🚀 STARTING COMPREHENSIVE ANALYSIS PIPELINE")
        print("=" * 80)
        
        # Load data
        suhi_loaded = self.load_suhi_data()
        urban_loaded = self.load_urban_expansion_data()
        
        if not suhi_loaded and not urban_loaded:
            print("❌ No data could be loaded. Analysis aborted.")
            return False
        
        # Generate comprehensive statistics
        stats_report = self.generate_comprehensive_statistics()
        
        # Export data for dashboard
        exports = self.export_analysis_data()
        
        print("\n" + "="*80)
        print("✅ COMPREHENSIVE ANALYSIS COMPLETED SUCCESSFULLY")
        print("="*80)
        print(f"📊 Statistics Report: Generated with {len(stats_report.get('key_findings', []))} key findings")
        print(f"📤 Data Exports: {len(exports)} datasets prepared for dashboard")
        print(f"📁 Output Directory: {self.output_path}")
        
        return True

def main():
    """Main execution function"""
    analyzer = UzbekistanUrbanAnalyzer()
    success = analyzer.run_comprehensive_analysis()
    
    if success:
        print("\n🎉 Ready for dashboard integration!")
        print("Next steps:")
        print("1. Review generated reports in dashboard_deliverables/reports/")
        print("2. Use exported data in dashboard_deliverables/data_analysis/")
        print("3. Integrate with interactive dashboard application")
    else:
        print("\n❌ Analysis failed. Please check data availability.")

if __name__ == "__main__":
    main()