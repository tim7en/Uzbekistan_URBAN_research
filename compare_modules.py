#!/usr/bin/env python3
"""
Compare Climate Risk Assessment Results Across Cities and Modules

This script runs each module separately for multiple cities and provides
detailed comparisons of results.
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List, Any

# Add paths for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir / 'services'))

from climate_risk_modules import (
    run_hazard_assessment,
    run_exposure_assessment,
    run_vulnerability_assessment,
    run_adaptive_capacity_assessment,
    run_full_risk_assessment,
    validate_city_data
)
from services.climate_data_loader import ClimateDataLoader


def get_available_cities(data_loader: ClimateDataLoader) -> List[str]:
    """Get list of available cities from data loader"""
    try:
        data = data_loader.load_all_data()
        cities = list(data.get('population_data', {}).keys())
        return sorted(cities)
    except Exception as e:
        print(f"Error loading cities: {e}")
        return []


def run_module_comparison(cities: List[str], data_loader: ClimateDataLoader) -> Dict[str, Dict[str, Any]]:
    """Run all modules for all cities and collect results"""
    
    results = {}
    modules = ['hazards', 'exposure', 'vulnerability', 'adaptive_capacity', 'validation', 'full_assessment']
    
    print(f"Running assessment for {len(cities)} cities across {len(modules)} modules...")
    print("=" * 80)
    
    for i, city in enumerate(cities, 1):
        print(f"\n[{i}/{len(cities)}] Processing {city}...")
        city_results = {}
        
        # Run each module
        for module in modules:
            try:
                if module == 'hazards':
                    result = run_hazard_assessment(city, data_loader)
                elif module == 'exposure':
                    result = run_exposure_assessment(city, data_loader)
                elif module == 'vulnerability':
                    result = run_vulnerability_assessment(city, data_loader)
                elif module == 'adaptive_capacity':
                    result = run_adaptive_capacity_assessment(city, data_loader)
                elif module == 'validation':
                    result = validate_city_data(city, data_loader)
                elif module == 'full_assessment':
                    result = run_full_risk_assessment(city, data_loader)
                
                city_results[module] = result
                print(f"  ✓ {module}")
                
            except Exception as e:
                print(f"  ✗ {module}: {e}")
                city_results[module] = None
        
        results[city] = city_results
    
    return results


def create_comparison_dataframes(results: Dict[str, Dict[str, Any]]) -> Dict[str, pd.DataFrame]:
    """Create DataFrames for easy comparison across cities"""
    
    dataframes = {}
    
    # Hazards comparison
    hazard_data = []
    for city, city_results in results.items():
        if city_results.get('hazards'):
            hazards = city_results['hazards']
            hazard_data.append({
                'City': city,
                'Temperature_Anomaly': hazards.get('temperature_anomaly', 0.0),
                'Heat_Island_Intensity': hazards.get('heat_island_intensity', 0.0),
                'Temperature_Trend': hazards.get('temperature_trend', 0.0),
                'Extreme_Heat_Days': hazards.get('extreme_heat_days', 0.0),
                'Hazard_Score': hazards.get('hazard_score', 0.0)
            })
    
    if hazard_data:
        dataframes['hazards'] = pd.DataFrame(hazard_data).set_index('City')
    
    # Exposure comparison
    exposure_data = []
    for city, city_results in results.items():
        if city_results.get('exposure'):
            exposure = city_results['exposure']
            exposure_data.append({
                'City': city,
                'Population_Density': exposure.get('population_density', 0.0),
                'Built_Up_Area': exposure.get('built_up_area', 0.0),
                'Vegetation_Accessibility': exposure.get('vegetation_accessibility', 0.0),
                'Air_Quality_Exposure': exposure.get('air_quality_exposure', 0.0),
                'Exposure_Score': exposure.get('exposure_score', 0.0)
            })
    
    if exposure_data:
        dataframes['exposure'] = pd.DataFrame(exposure_data).set_index('City')
    
    # Vulnerability comparison
    vulnerability_data = []
    for city, city_results in results.items():
        if city_results.get('vulnerability'):
            vulnerability = city_results['vulnerability']
            vulnerability_data.append({
                'City': city,
                'Social_Vulnerability': vulnerability.get('social_vulnerability', 0.0),
                'Infrastructure_Vulnerability': vulnerability.get('infrastructure_vulnerability', 0.0),
                'Health_Vulnerability': vulnerability.get('health_vulnerability', 0.0),
                'Economic_Vulnerability': vulnerability.get('economic_vulnerability', 0.0),
                'Vulnerability_Score': vulnerability.get('vulnerability_score', 0.0)
            })
    
    if vulnerability_data:
        dataframes['vulnerability'] = pd.DataFrame(vulnerability_data).set_index('City')
    
    # Adaptive capacity comparison
    adaptive_data = []
    for city, city_results in results.items():
        if city_results.get('adaptive_capacity'):
            adaptive = city_results['adaptive_capacity']
            adaptive_data.append({
                'City': city,
                'Green_Infrastructure': adaptive.get('green_infrastructure', 0.0),
                'Institutional_Capacity': adaptive.get('institutional_capacity', 0.0),
                'Economic_Capacity': adaptive.get('economic_capacity', 0.0),
                'Social_Capacity': adaptive.get('social_capacity', 0.0),
                'Adaptive_Capacity_Score': adaptive.get('adaptive_capacity_score', 0.0)
            })
    
    if adaptive_data:
        dataframes['adaptive_capacity'] = pd.DataFrame(adaptive_data).set_index('City')
    
    # Data quality comparison
    quality_data = []
    for city, city_results in results.items():
        if city_results.get('validation'):
            validation = city_results['validation']
            component_readiness = validation.get('component_readiness', {})
            quality_data.append({
                'City': city,
                'Overall_Quality': validation.get('overall_quality', 0.0),
                'Hazards_Readiness': component_readiness.get('hazards', {}).get('readiness_score', 0.0),
                'Exposure_Readiness': component_readiness.get('exposure', {}).get('readiness_score', 0.0),
                'Vulnerability_Readiness': component_readiness.get('vulnerability', {}).get('readiness_score', 0.0),
                'Adaptive_Capacity_Readiness': component_readiness.get('adaptive_capacity', {}).get('readiness_score', 0.0)
            })
    
    if quality_data:
        dataframes['data_quality'] = pd.DataFrame(quality_data).set_index('City')
    
    # Overall risk comparison
    risk_data = []
    for city, city_results in results.items():
        if city_results.get('full_assessment'):
            full_assessment = city_results['full_assessment']
            components = full_assessment.get('components', {})
            risk_data.append({
                'City': city,
                'Risk_Score': full_assessment.get('risk_score', 0.0),
                'Risk_Level': full_assessment.get('risk_level', 'Unknown'),
                'Priority_Score': full_assessment.get('priority_score', 0.0),
                'Priority_Level': full_assessment.get('priority_level', 'Unknown'),
                'Hazard_Score': components.get('hazard_score', 0.0),
                'Exposure_Score': components.get('exposure_score', 0.0),
                'Vulnerability_Score': components.get('vulnerability_score', 0.0),
                'Adaptive_Capacity_Score': components.get('adaptive_capacity_score', 0.0)
            })
    
    if risk_data:
        dataframes['overall_risk'] = pd.DataFrame(risk_data).set_index('City')
    
    return dataframes


def print_comparison_summary(dataframes: Dict[str, pd.DataFrame]):
    """Print summary comparisons across modules and cities"""
    
    print("\n" + "="*80)
    print("CLIMATE RISK ASSESSMENT COMPARISON SUMMARY")
    print("="*80)
    
    for module_name, df in dataframes.items():
        if df.empty:
            continue
            
        print(f"\n{module_name.upper().replace('_', ' ')} COMPARISON:")
        print("-" * 60)
        
        # Show top cities by primary score
        score_cols = [col for col in df.columns if 'score' in col.lower()]
        if score_cols:
            primary_score = score_cols[0]
            top_cities = df.nlargest(5, primary_score)
            
            print(f"\nTop 5 Cities by {primary_score.replace('_', ' ')}:")
            for i, (city, row) in enumerate(top_cities.iterrows(), 1):
                print(f"  {i}. {city}: {row[primary_score]:.4f}")
        
        # Show summary statistics
        print(f"\nSummary Statistics:")
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        summary = df[numeric_cols].describe()
        
        print(f"  Mean values:")
        for col in numeric_cols:
            print(f"    {col.replace('_', ' ')}: {summary.loc['mean', col]:.4f}")
        
        print(f"  Standard deviation:")
        for col in numeric_cols:
            print(f"    {col.replace('_', ' ')}: {summary.loc['std', col]:.4f}")
    
    # Cross-module comparison
    if 'overall_risk' in dataframes and not dataframes['overall_risk'].empty:
        risk_df = dataframes['overall_risk']
        
        print(f"\n{'OVERALL RISK RANKING:'}")
        print("-" * 60)
        
        # Sort by risk score
        risk_ranking = risk_df.sort_values('Risk_Score', ascending=False)
        
        print(f"\nCities by Risk Score (Highest to Lowest):")
        for i, (city, row) in enumerate(risk_ranking.iterrows(), 1):
            risk_level = row['Risk_Level']
            priority_level = row['Priority_Level']
            print(f"  {i:2d}. {city:15s} | Risk: {row['Risk_Score']:.4f} ({risk_level:10s}) | Priority: {row['Priority_Score']:.4f} ({priority_level})")
        
        print(f"\nComponent Score Correlations:")
        corr_matrix = risk_df[['Hazard_Score', 'Exposure_Score', 'Vulnerability_Score', 'Adaptive_Capacity_Score']].corr()
        print(corr_matrix.round(3))


def save_results_to_csv(dataframes: Dict[str, pd.DataFrame], output_dir: str = "comparison_results"):
    """Save comparison results to CSV files"""
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    print(f"\nSaving results to {output_path}...")
    
    for module_name, df in dataframes.items():
        if not df.empty:
            csv_file = output_path / f"{module_name}_comparison.csv"
            df.to_csv(csv_file)
            print(f"  ✓ {csv_file}")
    
    # Create a combined summary
    if dataframes:
        combined_data = []
        for city in set().union(*[df.index for df in dataframes.values()]):
            row = {'City': city}
            
            for module_name, df in dataframes.items():
                if city in df.index:
                    # Add primary score from each module
                    score_cols = [col for col in df.columns if 'score' in col.lower()]
                    if score_cols:
                        row[f"{module_name.title()}_Score"] = df.loc[city, score_cols[0]]
            
            combined_data.append(row)
        
        if combined_data:
            combined_df = pd.DataFrame(combined_data).set_index('City')
            combined_file = output_path / "combined_summary.csv"
            combined_df.to_csv(combined_file)
            print(f"  ✓ {combined_file} (combined summary)")


def main():
    """Main function to run module comparison"""
    
    print("Climate Risk Assessment Module Comparison")
    print("=" * 60)
    
    # Initialize data loader
    try:
        base_path = str(Path(__file__).parent)
        data_loader = ClimateDataLoader(base_path)
        print("✓ Data loader initialized successfully")
    except Exception as e:
        print(f"✗ Error initializing data loader: {e}")
        return 1
    
    # Get available cities
    cities = get_available_cities(data_loader)
    if not cities:
        print("✗ No cities found in data")
        return 1
    
    print(f"✓ Found {len(cities)} cities: {', '.join(cities[:5])}{'...' if len(cities) > 5 else ''}")
    
    # Limit to top cities for demonstration (you can modify this)
    if len(cities) > 10:
        cities = cities[:10]
        print(f"✓ Using first {len(cities)} cities for comparison")
    
    # Run assessments
    results = run_module_comparison(cities, data_loader)
    
    # Create comparison dataframes
    print("\nCreating comparison dataframes...")
    dataframes = create_comparison_dataframes(results)
    
    # Print summary
    print_comparison_summary(dataframes)
    
    # Save results
    save_results_to_csv(dataframes)
    
    print(f"\n🎉 Module comparison completed successfully!")
    print(f"   Processed {len(cities)} cities across {len(dataframes)} modules")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
