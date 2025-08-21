"""
Statistical analysis service for comprehensive urban research data
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class UrbanStatisticalAnalyzer:
    """
    Comprehensive statistical analysis for urban research data
    """
    
    def __init__(self, results_data: Dict):
        """Initialize with comprehensive analysis results"""
        self.results_data = results_data
        self.night_lights_df = None
        self.suhi_df = None
        self.expansion_df = None
        self.combined_df = None
        
        self._prepare_dataframes()
    
    def _prepare_dataframes(self):
        """Prepare dataframes from analysis results"""
        
        # Night Lights DataFrame
        if self.results_data.get('night_lights') and 'cities' in self.results_data['night_lights']:
            nl_data = []
            for city_data in self.results_data['night_lights']['cities']:
                if 'error' not in city_data:
                    nl_data.append({
                        'city': city_data['city'],
                        'early_radiance': city_data.get('early_mean_radiance', 0),
                        'late_radiance': city_data.get('late_mean_radiance', 0),
                        'radiance_change_abs': city_data.get('change_absolute', 0),
                        'radiance_change_pct': city_data.get('change_percent', 0)
                    })
            self.night_lights_df = pd.DataFrame(nl_data)
        
        # SUHI DataFrame
        if self.results_data.get('suhi') and 'cities_analysis' in self.results_data['suhi']:
            suhi_data = []
            for city_analysis in self.results_data['suhi']['cities_analysis']:
                city = city_analysis['city']
                for annual_result in city_analysis.get('annual_results', []):
                    if 'error' not in annual_result:
                        suhi_data.append({
                            'city': city,
                            'year': annual_result['year'],
                            'suhi_intensity': annual_result.get('suhi_intensity_celsius', 0),
                            'urban_temp': annual_result.get('urban_temperature_celsius', 0),
                            'rural_temp': annual_result.get('rural_temperature_celsius', 0),
                            'urban_std': annual_result.get('urban_std_celsius', 0),
                            'rural_std': annual_result.get('rural_std_celsius', 0)
                        })
            self.suhi_df = pd.DataFrame(suhi_data)
        
        # Urban Expansion DataFrame
        if self.results_data.get('urban_expansion') and 'cities_analysis' in self.results_data['urban_expansion']:
            expansion_data = []
            for city_data in self.results_data['urban_expansion']['cities_analysis']:
                if 'error' not in city_data:
                    expansion_data.append({
                        'city': city_data['city'],
                        'start_area_km2': city_data.get('built_area_start_km2', 0),
                        'end_area_km2': city_data.get('built_area_end_km2', 0),
                        'area_change_km2': city_data.get('built_area_change_km2', 0),
                        'area_change_pct': city_data.get('built_area_change_percent', 0),
                        'expansion_km2': city_data.get('urban_expansion_km2', 0),
                        'loss_km2': city_data.get('urban_loss_km2', 0)
                    })
            self.expansion_df = pd.DataFrame(expansion_data)
        
        # Combined DataFrame for correlation analysis
        self._create_combined_dataframe()
    
    def _create_combined_dataframe(self):
        """Create combined dataframe for cross-analysis correlations"""
        if self.night_lights_df is not None and self.expansion_df is not None:
            # Merge on city
            combined = pd.merge(self.night_lights_df, self.expansion_df, on='city', how='inner')
            
            # Add SUHI summary data (mean per city)
            if self.suhi_df is not None:
                suhi_summary = self.suhi_df.groupby('city').agg({
                    'suhi_intensity': ['mean', 'std', 'max', 'min'],
                    'urban_temp': 'mean',
                    'rural_temp': 'mean'
                }).round(2)
                
                # Flatten column names
                suhi_summary.columns = ['_'.join(col).strip() for col in suhi_summary.columns]
                suhi_summary = suhi_summary.reset_index()
                
                combined = pd.merge(combined, suhi_summary, on='city', how='left')
            
            self.combined_df = combined
    
    def descriptive_statistics(self) -> Dict:
        """Generate descriptive statistics for all variables"""
        stats_dict = {
            'analysis_timestamp': datetime.now().isoformat(),
            'night_lights': {},
            'suhi': {},
            'urban_expansion': {},
            'combined': {}
        }
        
        # Night Lights Statistics
        if self.night_lights_df is not None and not self.night_lights_df.empty:
            nl_stats = self.night_lights_df.describe().round(3)
            stats_dict['night_lights'] = {
                'count': len(self.night_lights_df),
                'descriptive_stats': nl_stats.to_dict(),
                'cities_with_growth': len(self.night_lights_df[self.night_lights_df['radiance_change_pct'] > 0]),
                'mean_growth_rate': self.night_lights_df['radiance_change_pct'].mean(),
                'max_growth_city': self.night_lights_df.loc[self.night_lights_df['radiance_change_pct'].idxmax(), 'city'] if len(self.night_lights_df) > 0 else None
            }
        
        # SUHI Statistics
        if self.suhi_df is not None and not self.suhi_df.empty:
            suhi_stats = self.suhi_df.describe().round(3)
            stats_dict['suhi'] = {
                'total_observations': len(self.suhi_df),
                'cities_analyzed': self.suhi_df['city'].nunique(),
                'years_covered': sorted(self.suhi_df['year'].unique()),
                'descriptive_stats': suhi_stats.to_dict(),
                'strong_suhi_observations': len(self.suhi_df[self.suhi_df['suhi_intensity'] > 2]),
                'cooling_effect_observations': len(self.suhi_df[self.suhi_df['suhi_intensity'] < 0]),
                'mean_suhi_by_city': self.suhi_df.groupby('city')['suhi_intensity'].mean().round(2).to_dict()
            }
        
        # Urban Expansion Statistics
        if self.expansion_df is not None and not self.expansion_df.empty:
            exp_stats = self.expansion_df.describe().round(3)
            stats_dict['urban_expansion'] = {
                'cities_analyzed': len(self.expansion_df),
                'descriptive_stats': exp_stats.to_dict(),
                'cities_expanding': len(self.expansion_df[self.expansion_df['area_change_km2'] > 0]),
                'cities_contracting': len(self.expansion_df[self.expansion_df['area_change_km2'] < 0]),
                'total_expansion': self.expansion_df['area_change_km2'].sum(),
                'fastest_growing_city': self.expansion_df.loc[self.expansion_df['area_change_pct'].idxmax(), 'city'] if len(self.expansion_df) > 0 else None
            }
        
        return stats_dict
    
    def correlation_analysis(self) -> Dict:
        """Perform correlation analysis between different urban indicators"""
        if self.combined_df is None or self.combined_df.empty:
            return {'error': 'Insufficient data for correlation analysis'}
        
        # Select numeric columns for correlation
        numeric_cols = self.combined_df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) < 2:
            return {'error': 'Insufficient numeric variables for correlation'}
        
        # Calculate correlation matrix
        correlation_matrix = self.combined_df[numeric_cols].corr().round(3)
        
        # Find significant correlations (|r| > 0.5)
        significant_correlations = []
        for i, col1 in enumerate(numeric_cols):
            for j, col2 in enumerate(numeric_cols):
                if i < j:  # Avoid duplicates
                    corr_val = correlation_matrix.loc[col1, col2]
                    if abs(corr_val) > 0.5 and not np.isnan(corr_val):
                        significant_correlations.append({
                            'variable1': col1,
                            'variable2': col2,
                            'correlation': corr_val,
                            'strength': self._interpret_correlation(abs(corr_val))
                        })
        
        return {
            'correlation_matrix': correlation_matrix.to_dict(),
            'significant_correlations': significant_correlations,
            'interpretation': self._interpret_correlations(significant_correlations)
        }
    
    def _interpret_correlation(self, abs_corr: float) -> str:
        """Interpret correlation strength"""
        if abs_corr >= 0.8:
            return 'Very Strong'
        elif abs_corr >= 0.6:
            return 'Strong'
        elif abs_corr >= 0.4:
            return 'Moderate'
        elif abs_corr >= 0.2:
            return 'Weak'
        else:
            return 'Very Weak'
    
    def _interpret_correlations(self, correlations: List[Dict]) -> List[str]:
        """Generate interpretations for significant correlations"""
        interpretations = []
        
        for corr in correlations:
            var1, var2 = corr['variable1'], corr['variable2']
            strength = corr['strength']
            direction = 'positive' if corr['correlation'] > 0 else 'negative'
            
            # Create meaningful interpretations
            if 'suhi' in var1.lower() and 'radiance' in var2.lower():
                interpretations.append(f"Cities with stronger urban heat islands tend to have {'higher' if direction == 'positive' else 'lower'} night lights activity ({strength.lower()} {direction} correlation)")
            elif 'expansion' in var1.lower() and 'radiance' in var2.lower():
                interpretations.append(f"Urban expansion is {'positively' if direction == 'positive' else 'negatively'} associated with night lights growth ({strength.lower()} correlation)")
            elif 'suhi' in var1.lower() and 'area' in var2.lower():
                interpretations.append(f"Urban heat islands show {direction} correlation with urban area size ({strength.lower()} relationship)")
            else:
                interpretations.append(f"{strength} {direction} correlation between {var1} and {var2}")
        
        return interpretations
    
    def trend_analysis(self) -> Dict:
        """Analyze temporal trends in SUHI data"""
        if self.suhi_df is None or self.suhi_df.empty:
            return {'error': 'No SUHI data available for trend analysis'}
        
        trend_results = {
            'city_trends': {},
            'overall_trends': {}
        }
        
        # City-level trends
        for city in self.suhi_df['city'].unique():
            city_data = self.suhi_df[self.suhi_df['city'] == city].sort_values('year')
            
            if len(city_data) >= 3:  # Need at least 3 points for trend
                years = city_data['year'].values
                suhi_values = city_data['suhi_intensity'].values
                
                if SCIPY_AVAILABLE:
                    slope, intercept, r_value, p_value, std_err = stats.linregress(years, suhi_values)
                    
                    trend_results['city_trends'][city] = {
                        'slope_celsius_per_year': round(slope, 4),
                        'r_squared': round(r_value**2, 3),
                        'p_value': round(p_value, 4),
                        'trend_direction': 'increasing' if slope > 0 else 'decreasing',
                        'significance': 'significant' if p_value < 0.05 else 'not significant',
                        'observations': len(city_data)
                    }
                else:
                    # Simple trend without scipy
                    trend_results['city_trends'][city] = {
                        'mean_suhi': round(suhi_values.mean(), 2),
                        'change_total': round(suhi_values[-1] - suhi_values[0], 2),
                        'observations': len(city_data),
                        'note': 'Advanced trend analysis requires scipy'
                    }
        
        # Overall trend (all cities combined)
        if SCIPY_AVAILABLE and len(self.suhi_df) >= 3:
            years = self.suhi_df['year'].values
            suhi_values = self.suhi_df['suhi_intensity'].values
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(years, suhi_values)
            
            trend_results['overall_trends'] = {
                'slope_celsius_per_year': round(slope, 4),
                'r_squared': round(r_value**2, 3),
                'p_value': round(p_value, 4),
                'trend_interpretation': self._interpret_trend(slope, p_value)
            }
        
        return trend_results
    
    def _interpret_trend(self, slope: float, p_value: float) -> str:
        """Interpret trend significance and direction"""
        if p_value > 0.05:
            return "No statistically significant trend detected"
        
        if slope > 0.1:
            return "Strong increasing trend - urban heat islands are intensifying"
        elif slope > 0.01:
            return "Moderate increasing trend - gradual warming"
        elif slope > -0.01:
            return "Minimal change - relatively stable conditions"
        elif slope > -0.1:
            return "Moderate decreasing trend - gradual cooling"
        else:
            return "Strong decreasing trend - urban heat islands are weakening"
    
    def extreme_events_analysis(self) -> Dict:
        """Analyze extreme values and outliers"""
        results = {}
        
        # SUHI extremes
        if self.suhi_df is not None and not self.suhi_df.empty:
            suhi_data = self.suhi_df['suhi_intensity']
            
            # Calculate percentiles
            q95 = suhi_data.quantile(0.95)
            q05 = suhi_data.quantile(0.05)
            
            extreme_hot = self.suhi_df[self.suhi_df['suhi_intensity'] >= q95]
            extreme_cool = self.suhi_df[self.suhi_df['suhi_intensity'] <= q05]
            
            results['suhi_extremes'] = {
                'extreme_heat_threshold': round(q95, 2),
                'extreme_cool_threshold': round(q05, 2),
                'extreme_heat_events': len(extreme_hot),
                'extreme_cool_events': len(extreme_cool),
                'hottest_observation': {
                    'city': extreme_hot.loc[extreme_hot['suhi_intensity'].idxmax(), 'city'] if len(extreme_hot) > 0 else None,
                    'year': int(extreme_hot.loc[extreme_hot['suhi_intensity'].idxmax(), 'year']) if len(extreme_hot) > 0 else None,
                    'intensity': round(extreme_hot['suhi_intensity'].max(), 2) if len(extreme_hot) > 0 else None
                }
            }
        
        # Night lights extremes
        if self.night_lights_df is not None and not self.night_lights_df.empty:
            growth_data = self.night_lights_df['radiance_change_pct']
            
            results['night_lights_extremes'] = {
                'highest_growth': {
                    'city': self.night_lights_df.loc[growth_data.idxmax(), 'city'],
                    'growth_percent': round(growth_data.max(), 1)
                },
                'lowest_growth': {
                    'city': self.night_lights_df.loc[growth_data.idxmin(), 'city'],
                    'growth_percent': round(growth_data.min(), 1)
                }
            }
        
        return results
    
    def generate_comprehensive_report(self, output_dir: Path) -> Path:
        """Generate a comprehensive statistical analysis report"""
        
        # Run all analyses
        descriptive = self.descriptive_statistics()
        correlations = self.correlation_analysis()
        trends = self.trend_analysis()
        extremes = self.extreme_events_analysis()
        
        # Generate report content
        report_content = f"""# Comprehensive Statistical Analysis Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

This report provides comprehensive statistical analysis of urban development patterns across Uzbekistan cities for the period 2017-2024, including night lights evolution, surface urban heat island effects, and urban expansion patterns.

## 1. Descriptive Statistics

### Night Lights Analysis
"""
        
        if descriptive.get('night_lights'):
            nl_stats = descriptive['night_lights']
            report_content += f"""- **Cities Analyzed**: {nl_stats.get('count', 0)}
- **Cities with Growth**: {nl_stats.get('cities_with_growth', 0)}
- **Mean Growth Rate**: {nl_stats.get('mean_growth_rate', 0):.1f}%
- **Fastest Growing City**: {nl_stats.get('max_growth_city', 'N/A')}
"""
        
        if descriptive.get('suhi'):
            suhi_stats = descriptive['suhi']
            report_content += f"""
### Surface Urban Heat Island Analysis
- **Total Observations**: {suhi_stats.get('total_observations', 0)}
- **Cities Analyzed**: {suhi_stats.get('cities_analyzed', 0)}
- **Years Covered**: {', '.join(map(str, suhi_stats.get('years_covered', [])))}
- **Strong SUHI Events (>2°C)**: {suhi_stats.get('strong_suhi_observations', 0)}
- **Cooling Effects (<0°C)**: {suhi_stats.get('cooling_effect_observations', 0)}
"""
        
        if descriptive.get('urban_expansion'):
            exp_stats = descriptive['urban_expansion']
            report_content += f"""
### Urban Expansion Analysis
- **Cities Analyzed**: {exp_stats.get('cities_analyzed', 0)}
- **Cities Expanding**: {exp_stats.get('cities_expanding', 0)}
- **Cities Contracting**: {exp_stats.get('cities_contracting', 0)}
- **Total Expansion**: {exp_stats.get('total_expansion', 0):.1f} km²
- **Fastest Growing City**: {exp_stats.get('fastest_growing_city', 'N/A')}
"""
        
        # Add correlation analysis
        if 'error' not in correlations:
            report_content += f"""
## 2. Correlation Analysis

### Significant Relationships Found:
"""
            for interpretation in correlations.get('interpretation', []):
                report_content += f"- {interpretation}\n"
        
        # Add trend analysis
        if 'error' not in trends:
            report_content += f"""
## 3. Temporal Trend Analysis

### City-Level Trends:
"""
            for city, trend_data in trends.get('city_trends', {}).items():
                if 'slope_celsius_per_year' in trend_data:
                    slope = trend_data['slope_celsius_per_year']
                    significance = trend_data.get('significance', 'unknown')
                    report_content += f"- **{city}**: {slope:+.4f}°C/year ({significance})\n"
        
        # Add extreme events
        if extremes:
            report_content += f"""
## 4. Extreme Events Analysis

### SUHI Extremes:
"""
            if 'suhi_extremes' in extremes:
                se = extremes['suhi_extremes']
                report_content += f"""- **Extreme Heat Threshold**: {se.get('extreme_heat_threshold', 0)}°C
- **Extreme Heat Events**: {se.get('extreme_heat_events', 0)}
- **Hottest Observation**: {se.get('hottest_observation', {}).get('intensity', 0)}°C in {se.get('hottest_observation', {}).get('city', 'N/A')} ({se.get('hottest_observation', {}).get('year', 'N/A')})
"""
        
        report_content += f"""
## 5. Key Findings & Recommendations

### Urban Heat Island Management
- Cities with strong SUHI effects (>2°C) require immediate attention for heat mitigation strategies
- Consider implementing green infrastructure in areas with persistent high SUHI values
- Monitor temporal trends to assess effectiveness of cooling interventions

### Urban Development Planning
- Balance urban expansion with sustainable development practices
- Cities with rapid growth rates need comprehensive infrastructure planning
- Consider night lights patterns as indicators of economic activity and development pressure

### Data Quality & Monitoring
- Continue systematic monitoring using satellite-based indicators
- Integrate ground-based measurements for validation
- Develop early warning systems for extreme urban heat events

---
*Statistical analysis generated by Uzbekistan Urban Research Analysis System*
*Resolution: {self.results_data.get('metadata', {}).get('resolution_m', 'Unknown')}m*
*Analysis Period: {self.results_data.get('metadata', {}).get('years_analyzed', ['Unknown'])[0] if self.results_data.get('metadata', {}).get('years_analyzed') else 'Unknown'}-{self.results_data.get('metadata', {}).get('years_analyzed', ['Unknown'])[-1] if self.results_data.get('metadata', {}).get('years_analyzed') else 'Unknown'}*
"""
        
        # Save the report
        report_file = output_dir / f"comprehensive_statistical_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        # Also save raw statistics as JSON
        stats_file = output_dir / f"statistical_analysis_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        all_stats = {
            'descriptive_statistics': descriptive,
            'correlation_analysis': correlations,
            'trend_analysis': trends,
            'extreme_events': extremes
        }
        
        with open(stats_file, 'w') as f:
            json.dump(all_stats, f, indent=2)
        
        return report_file


def run_statistical_analysis(analysis_results: Dict, output_dir: Path) -> Dict:
    """
    Run comprehensive statistical analysis on urban research results
    """
    print("📊 STATISTICAL ANALYSIS")
    print("="*40)
    
    # Initialize analyzer
    analyzer = UrbanStatisticalAnalyzer(analysis_results)
    
    # Generate comprehensive report
    report_file = analyzer.generate_comprehensive_report(output_dir)
    
    print(f"✅ Statistical analysis complete")
    print(f"📄 Report saved: {report_file}")
    
    return {
        'analysis_complete': True,
        'report_file': str(report_file),
        'data_summary': {
            'night_lights_cities': len(analyzer.night_lights_df) if analyzer.night_lights_df is not None else 0,
            'suhi_observations': len(analyzer.suhi_df) if analyzer.suhi_df is not None else 0,
            'expansion_cities': len(analyzer.expansion_df) if analyzer.expansion_df is not None else 0
        }
    }