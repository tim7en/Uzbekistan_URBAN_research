"""Comprehensive SUHI analysis and statistical processing."""
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
import warnings
from datetime import datetime
import scipy.stats as stats

warnings.filterwarnings('ignore')


class SUHIAnalyzer:
    """
    Comprehensive SUHI data analyzer and statistical processor.
    """
    
    def __init__(self, data_path: str):
        """Initialize the SUHI analyzer."""
        self.data_path = Path(data_path)
        self.cities_data = {}
        self.temporal_data = {}
        self.comparative_stats = {}
        self.summary_report = {}
        
    def load_data(self) -> bool:
        """Load all SUHI data from JSON files."""
        try:
            print("Loading SUHI data for comprehensive analysis...")
            
            # Get all cities from the data files
            cities = set()
            for file_path in self.data_path.glob("*_results.json"):
                parts = file_path.stem.split('_')
                if len(parts) >= 3 and parts[-1] == 'results':
                    city_name = '_'.join(parts[:-2])
                    year = parts[-2]
                    cities.add(city_name)
            
            # Load data for each city
            for city in cities:
                self.cities_data[city] = {}
                
                # Load available years
                for year_file in self.data_path.glob(f"{city}_*_results.json"):
                    year_part = year_file.stem.split('_')[-2]
                    try:
                        year = int(year_part)
                        with open(year_file, 'r') as f:
                            self.cities_data[city][year] = json.load(f)
                    except (ValueError, json.JSONDecodeError) as e:
                        print(f"Warning: Could not load {year_file}: {e}")
                
                # Load temporal trends if available
                trends_file = self.data_path / f"{city}_annual_suhi_trends.json"
                if trends_file.exists():
                    try:
                        with open(trends_file, 'r') as f:
                            self.temporal_data[city] = json.load(f)
                    except json.JSONDecodeError as e:
                        print(f"Warning: Could not load trends for {city}: {e}")
            
            print(f"Loaded data for {len(cities)} cities")
            return True
            
        except Exception as e:
            print(f"Error loading SUHI data: {e}")
            return False
    
    def calculate_comparative_statistics(self) -> Dict[str, Any]:
        """Calculate comparative statistics across all cities and years."""
        try:
            stats_summary = {
                'total_cities': len(self.cities_data),
                'years_analyzed': set(),
                'suhi_statistics': {},
                'temperature_statistics': {},
                'trend_analysis': {},
                'regional_comparison': {}
            }
            
            # Collect all data points
            all_suhi_values = []
            all_urban_temps = []
            all_rural_temps = []
            yearly_data = {}
            city_comparisons = {}
            
            for city, years_data in self.cities_data.items():
                city_comparisons[city] = {}
                
                for year, data in years_data.items():
                    stats_summary['years_analyzed'].add(year)
                    
                    # Extract SUHI data
                    if 'suhi' in data and isinstance(data['suhi'], dict):
                        suhi_intensity = data['suhi'].get('intensity', 0)
                        if suhi_intensity > 0:  # Valid SUHI value
                            all_suhi_values.append(suhi_intensity)
                            city_comparisons[city][year] = {
                                'suhi': suhi_intensity,
                                'urban_temp': data.get('urban_mean', 0),
                                'rural_temp': data.get('rural_mean', 0)
                            }
                            
                            # Collect temperature data
                            urban_temp = data.get('urban_mean', 0)
                            rural_temp = data.get('rural_mean', 0)
                            if urban_temp > 0:
                                all_urban_temps.append(urban_temp)
                            if rural_temp > 0:
                                all_rural_temps.append(rural_temp)
                            
                            # Group by year
                            if year not in yearly_data:
                                yearly_data[year] = {'suhi': [], 'urban': [], 'rural': []}
                            yearly_data[year]['suhi'].append(suhi_intensity)
                            yearly_data[year]['urban'].append(urban_temp)
                            yearly_data[year]['rural'].append(rural_temp)
            
            # Calculate SUHI statistics
            if all_suhi_values:
                stats_summary['suhi_statistics'] = {
                    'mean': np.mean(all_suhi_values),
                    'median': np.median(all_suhi_values),
                    'std': np.std(all_suhi_values),
                    'min': np.min(all_suhi_values),
                    'max': np.max(all_suhi_values),
                    'percentile_25': np.percentile(all_suhi_values, 25),
                    'percentile_75': np.percentile(all_suhi_values, 75),
                    'count': len(all_suhi_values)
                }
            
            # Calculate temperature statistics
            if all_urban_temps and all_rural_temps:
                stats_summary['temperature_statistics'] = {
                    'urban_mean': np.mean(all_urban_temps),
                    'rural_mean': np.mean(all_rural_temps),
                    'urban_std': np.std(all_urban_temps),
                    'rural_std': np.std(all_rural_temps),
                    'temp_difference': np.mean(all_urban_temps) - np.mean(all_rural_temps)
                }
            
            # Trend analysis by year
            if len(yearly_data) > 1:
                years = sorted(yearly_data.keys())
                annual_means = []
                for year in years:
                    if yearly_data[year]['suhi']:
                        annual_means.append(np.mean(yearly_data[year]['suhi']))
                
                if len(annual_means) > 1:
                    # Calculate trend
                    slope, intercept, r_value, p_value, std_err = stats.linregress(years, annual_means)
                    stats_summary['trend_analysis'] = {
                        'slope': slope,
                        'r_squared': r_value**2,
                        'p_value': p_value,
                        'trend_direction': 'increasing' if slope > 0 else 'decreasing',
                        'significant': p_value < 0.05,
                        'annual_change': slope
                    }
            
            # Regional comparison (identify strongest/weakest heat islands)
            if city_comparisons:
                city_averages = {}
                for city, years in city_comparisons.items():
                    if years:
                        avg_suhi = np.mean([data['suhi'] for data in years.values()])
                        city_averages[city] = avg_suhi
                
                if city_averages:
                    strongest_uhi = max(city_averages, key=city_averages.get)
                    weakest_uhi = min(city_averages, key=city_averages.get)
                    
                    stats_summary['regional_comparison'] = {
                        'strongest_heat_island': {
                            'city': strongest_uhi,
                            'average_suhi': city_averages[strongest_uhi]
                        },
                        'weakest_heat_island': {
                            'city': weakest_uhi,
                            'average_suhi': city_averages[weakest_uhi]
                        },
                        'city_rankings': sorted(city_averages.items(), 
                                              key=lambda x: x[1], reverse=True)
                    }
            
            self.comparative_stats = stats_summary
            return stats_summary
            
        except Exception as e:
            print(f"Error calculating comparative statistics: {e}")
            return {}
    
    def create_comprehensive_report(self) -> Dict[str, Any]:
        """Create a comprehensive analysis report."""
        try:
            report = {
                'analysis_metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'total_cities': len(self.cities_data),
                    'years_covered': sorted(list(self.comparative_stats.get('years_analyzed', set()))),
                    'analysis_type': 'Comprehensive SUHI Analysis'
                },
                'executive_summary': {},
                'detailed_statistics': self.comparative_stats,
                'city_profiles': {},
                'trends_and_patterns': {},
                'recommendations': []
            }
            
            # Executive summary
            suhi_stats = self.comparative_stats.get('suhi_statistics', {})
            temp_stats = self.comparative_stats.get('temperature_statistics', {})
            trend_stats = self.comparative_stats.get('trend_analysis', {})
            regional_stats = self.comparative_stats.get('regional_comparison', {})
            
            if suhi_stats:
                report['executive_summary'] = {
                    'average_suhi_intensity': round(suhi_stats.get('mean', 0), 2),
                    'suhi_range': f"{suhi_stats.get('min', 0):.2f} - {suhi_stats.get('max', 0):.2f} K",
                    'temperature_difference': round(temp_stats.get('temp_difference', 0), 2),
                    'trend_direction': trend_stats.get('trend_direction', 'stable'),
                    'trend_significance': trend_stats.get('significant', False),
                    'strongest_heat_island': regional_stats.get('strongest_heat_island', {}).get('city', 'N/A'),
                    'total_observations': suhi_stats.get('count', 0)
                }
            
            # City profiles
            for city, years_data in self.cities_data.items():
                if years_data:
                    city_suhi_values = []
                    for year, data in years_data.items():
                        if 'suhi' in data and isinstance(data['suhi'], dict):
                            suhi_val = data['suhi'].get('intensity', 0)
                            if suhi_val > 0:
                                city_suhi_values.append(suhi_val)
                    
                    if city_suhi_values:
                        report['city_profiles'][city] = {
                            'average_suhi': round(np.mean(city_suhi_values), 2),
                            'suhi_variability': round(np.std(city_suhi_values), 2),
                            'years_analyzed': len(years_data),
                            'trend': 'increasing' if len(city_suhi_values) > 1 and city_suhi_values[-1] > city_suhi_values[0] else 'stable/decreasing'
                        }
            
            # Generate recommendations based on findings
            recommendations = []
            if suhi_stats.get('mean', 0) > 3:
                recommendations.append("High average SUHI intensity detected - consider urban cooling strategies")
            if trend_stats.get('trend_direction') == 'increasing' and trend_stats.get('significant'):
                recommendations.append("Significant warming trend identified - monitor urban development patterns")
            if regional_stats.get('strongest_heat_island'):
                strongest_city = regional_stats['strongest_heat_island']['city']
                recommendations.append(f"Focus mitigation efforts on {strongest_city} as the strongest heat island")
            
            report['recommendations'] = recommendations
            self.summary_report = report
            
            return report
            
        except Exception as e:
            print(f"Error creating comprehensive report: {e}")
            return {}
    
    def export_summary_statistics(self, output_path: Path) -> bool:
        """Export summary statistics to JSON file."""
        try:
            output_file = output_path / f"comprehensive_suhi_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            export_data = {
                'analysis_report': self.summary_report,
                'comparative_statistics': self.comparative_stats,
                'data_summary': {
                    'cities_analyzed': list(self.cities_data.keys()),
                    'total_data_points': sum(len(years) for years in self.cities_data.values()),
                    'analysis_period': f"{min(self.comparative_stats.get('years_analyzed', []))} - {max(self.comparative_stats.get('years_analyzed', []))}" if self.comparative_stats.get('years_analyzed') else "Unknown"
                }
            }
            
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            print(f"📊 Comprehensive analysis exported to: {output_file}")
            return True
            
        except Exception as e:
            print(f"Error exporting summary statistics: {e}")
            return False
    
    def run_complete_analysis(self, output_path: Path) -> bool:
        """Run the complete analysis pipeline."""
        try:
            print("🔍 Starting comprehensive SUHI analysis...")
            
            # Load data
            if not self.load_data():
                print("❌ Failed to load data")
                return False
            
            # Calculate statistics
            print("📊 Calculating comparative statistics...")
            self.calculate_comparative_statistics()
            
            # Create comprehensive report
            print("📋 Creating comprehensive report...")
            self.create_comprehensive_report()
            
            # Export results
            print("💾 Exporting analysis results...")
            self.export_summary_statistics(output_path)
            
            print("✅ Comprehensive SUHI analysis completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error in complete analysis: {e}")
            return False


def run_comprehensive_suhi_analysis(data_path: str, output_path: str) -> bool:
    """Run comprehensive SUHI analysis on the provided data."""
    try:
        analyzer = SUHIAnalyzer(data_path)
        return analyzer.run_complete_analysis(Path(output_path))
    except Exception as e:
        print(f"Error running comprehensive analysis: {e}")
        return False
