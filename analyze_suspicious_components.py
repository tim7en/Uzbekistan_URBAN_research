#!/usr/bin/env python3
"""
Detailed analysis of suspicious components in the climate assessment.
Focus on: heat_hazard, pluvial_hazard, viirs_exposure, bio_trend_vulnerability,
fragmentation_vulnerability, income_vulnerability, air_pollution_vulnerability, economic_capacity
"""

import json
import numpy as np
import pandas as pd

def analyze_component_distributions():
    """Analyze the distribution patterns of suspicious components"""
    
    print("=" * 80)
    print("ANALYZING SUSPICIOUS COMPONENT DISTRIBUTIONS")
    print("=" * 80)
    
    with open('suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json', 'r') as f:
        results = json.load(f)
    
    # Components to analyze
    suspicious_components = [
        'heat_hazard', 'pluvial_hazard', 'viirs_exposure', 
        'bio_trend_vulnerability', 'fragmentation_vulnerability', 
        'income_vulnerability', 'air_pollution_vulnerability', 'economic_capacity'
    ]
    
    component_data = {}
    
    for component in suspicious_components:
        values = []
        city_values = {}
        
        for city, data in results.items():
            if component in data:
                value = data[component]
                values.append(value)
                city_values[city] = value
        
        if values:
            component_data[component] = {
                'values': values,
                'city_values': city_values,
                'min': min(values),
                'max': max(values),
                'mean': np.mean(values),
                'std': np.std(values),
                'range': max(values) - min(values)
            }
    
    return component_data

def identify_bias_patterns(component_data):
    """Identify specific bias patterns in each component"""
    
    print("\n🔍 BIAS PATTERN ANALYSIS")
    print("=" * 60)
    
    bias_issues = {}
    
    for component, data in component_data.items():
        issues = []
        values = data['values']
        city_values = data['city_values']
        
        print(f"\n📊 {component.upper()}:")
        print(f"   Range: {data['min']:.3f} - {data['max']:.3f}")
        print(f"   Mean: {data['mean']:.3f}, Std: {data['std']:.3f}")
        
        # Check for max-pegging (too many 1.000 values)
        max_count = sum(1 for v in values if v >= 0.999)
        if max_count > 0:
            max_cities = [city for city, val in city_values.items() if val >= 0.999]
            issues.append(f"Max-pegging: {max_count} cities at 1.000 ({max_cities})")
            print(f"   🚨 Max-pegging: {max_count} cities = 1.000")
        
        # Check for min-pegging (too many 0.000 values)
        min_count = sum(1 for v in values if v <= 0.001)
        if min_count > 0:
            min_cities = [city for city, val in city_values.items() if val <= 0.001]
            issues.append(f"Min-pegging: {min_count} cities at 0.000 ({min_cities})")
            print(f"   🚨 Min-pegging: {min_count} cities = 0.000")
        
        # Check for lack of variance (all similar values)
        if data['std'] < 0.1:
            issues.append(f"Low variance: std = {data['std']:.3f}")
            print(f"   ⚠️  Low variance: std = {data['std']:.3f}")
        
        # Check for extreme skewness
        if len(values) > 3:
            # Calculate skewness manually
            mean_val = np.mean(values)
            skew_values = [(v - mean_val)**3 for v in values]
            skewness = np.mean(skew_values) / (data['std']**3) if data['std'] > 0 else 0
            
            if abs(skewness) > 2:
                issues.append(f"Extreme skewness: {skewness:.2f}")
                print(f"   ⚠️  Extreme skewness: {skewness:.2f}")
        
        # Check for city size bias (correlation with population)
        with open('suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json', 'r') as f:
            results = json.load(f)
        
        populations = []
        comp_values = []
        for city, comp_val in city_values.items():
            if city in results:
                populations.append(results[city]['population'])
                comp_values.append(comp_val)
        
        if len(populations) > 3:
            correlation = np.corrcoef(populations, comp_values)[0, 1] if len(populations) > 1 else 0
            if abs(correlation) > 0.7:
                issues.append(f"Population bias: correlation = {correlation:.2f}")
                print(f"   🚨 Population bias: r = {correlation:.2f}")
        
        bias_issues[component] = issues
        
        # Show top/bottom cities for suspicious patterns
        sorted_cities = sorted(city_values.items(), key=lambda x: x[1], reverse=True)
        print(f"   Top 3: {', '.join([f'{city}({val:.3f})' for city, val in sorted_cities[:3]])}")
        print(f"   Bottom 3: {', '.join([f'{city}({val:.3f})' for city, val in sorted_cities[-3:]])}")
    
    return bias_issues

def analyze_component_correlations(component_data):
    """Analyze suspicious correlations between components"""
    
    print(f"\n🔗 COMPONENT CORRELATION ANALYSIS")
    print("=" * 60)
    
    components = list(component_data.keys())
    
    # Create correlation matrix
    correlations = {}
    
    for i, comp1 in enumerate(components):
        for j, comp2 in enumerate(components[i+1:], i+1):
            values1 = list(component_data[comp1]['city_values'].values())
            values2 = list(component_data[comp2]['city_values'].values())
            
            if len(values1) == len(values2) and len(values1) > 1:
                correlation = np.corrcoef(values1, values2)[0, 1]
                correlations[(comp1, comp2)] = correlation
    
    # Report suspicious correlations
    print("🚨 HIGH CORRELATIONS (potential calculation errors):")
    for (comp1, comp2), corr in correlations.items():
        if abs(corr) > 0.9:
            print(f"   {comp1} ↔ {comp2}: r = {corr:.3f}")
    
    print("\n⚠️  MODERATE CORRELATIONS (worth investigating):")
    for (comp1, comp2), corr in correlations.items():
        if 0.7 <= abs(corr) < 0.9:
            print(f"   {comp1} ↔ {comp2}: r = {corr:.3f}")
    
    return correlations

def identify_specific_methodological_issues():
    """Identify specific methodological issues for each component"""
    
    print(f"\n🔬 METHODOLOGICAL ISSUE ANALYSIS")
    print("=" * 60)
    
    with open('suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json', 'r') as f:
        results = json.load(f)
    
    issues = {}
    
    # Heat Hazard Analysis
    print(f"\n🌡️  HEAT HAZARD:")
    heat_values = {city: data['heat_hazard'] for city, data in results.items()}
    tashkent_heat = heat_values.get('Tashkent', 0)
    if tashkent_heat >= 0.999:
        print(f"   🚨 Tashkent heat_hazard = {tashkent_heat:.3f} (max value)")
        print(f"   Issue: Likely temperature scaling issue or no relative comparison")
        issues['heat_hazard'] = "Max-pegged, needs relative temperature scaling"
    
    # Pluvial Hazard Analysis  
    print(f"\n🌧️  PLUVIAL HAZARD:")
    pluvial_values = {city: data['pluvial_hazard'] for city, data in results.items()}
    qarshi_pluvial = pluvial_values.get('Qarshi', 0)
    tashkent_pluvial = pluvial_values.get('Tashkent', 0)
    
    if qarshi_pluvial >= 0.999:
        print(f"   🚨 Qarshi (arid) pluvial_hazard = {qarshi_pluvial:.3f}")
        print(f"   Issue: Arid city shouldn't have maximum flood risk")
        issues['pluvial_hazard'] = "Methodology error - arid cities showing max flood risk"
    
    if tashkent_pluvial >= 0.999:
        print(f"   🚨 Tashkent pluvial_hazard = {tashkent_pluvial:.3f}")
        print(f"   Issue: May be using imperviousness only, not precipitation patterns")
        issues['pluvial_hazard'] = "Possibly using built area % instead of flood risk"
    
    # VIIRS Exposure Analysis
    print(f"\n💡 VIIRS EXPOSURE:")
    viirs_values = {city: data['viirs_exposure'] for city, data in results.items()}
    max_viirs_cities = [city for city, val in viirs_values.items() if val >= 0.999]
    if len(max_viirs_cities) > 2:
        print(f"   🚨 {len(max_viirs_cities)} cities at max VIIRS: {max_viirs_cities}")
        print(f"   Issue: Nightlight scaling not relative across cities")
        issues['viirs_exposure'] = "Too many cities at maximum - scaling issue"
    
    # Bio Trend Vulnerability Analysis
    print(f"\n🌱 BIO TREND VULNERABILITY:")
    bio_values = {city: data['bio_trend_vulnerability'] for city, data in results.items()}
    max_bio_cities = [city for city, val in bio_values.items() if val >= 0.999]
    min_bio_cities = [city for city, val in bio_values.items() if val <= 0.001]
    
    if len(max_bio_cities) > 3:
        print(f"   🚨 {len(max_bio_cities)} cities at max bio trend: {max_bio_cities}")
        issues['bio_trend_vulnerability'] = "Too many max values - vegetation trend calculation issue"
    
    if len(min_bio_cities) > 0:
        print(f"   🚨 {len(min_bio_cities)} cities at zero bio trend: {min_bio_cities}")
        print(f"   Issue: Likely missing data being treated as zero")
        issues['bio_trend_vulnerability'] = "Missing data being converted to zeros"
    
    # Income Vulnerability Analysis
    print(f"\n💰 INCOME VULNERABILITY:")
    income_values = {city: data['income_vulnerability'] for city, data in results.items()}
    zero_income_cities = [city for city, val in income_values.items() if val <= 0.001]
    
    if len(zero_income_cities) > 0:
        print(f"   🚨 {len(zero_income_cities)} cities with zero income vulnerability: {zero_income_cities}")
        print(f"   Issue: GDP-based calculation may be inverted or using total GDP instead of per capita")
        issues['income_vulnerability'] = "Wealthy cities showing zero vulnerability - calculation error"
    
    # Economic Capacity Analysis
    print(f"\n🏛️  ECONOMIC CAPACITY:")
    econ_values = {city: data.get('economic_capacity', 0.5) for city, data in results.items()}
    max_econ_cities = [city for city, val in econ_values.items() if val >= 0.999]
    
    if len(max_econ_cities) > 1:
        print(f"   🚨 {len(max_econ_cities)} cities at max economic capacity: {max_econ_cities}")
        print(f"   Issue: Economic capacity calculation may be binary or poorly scaled")
        issues['economic_capacity'] = "Too many cities at maximum - binary calculation suspected"
    
    return issues

def main():
    """Run comprehensive analysis of suspicious components"""
    
    print("SUSPICIOUS COMPONENT ANALYSIS")
    print("Detailed examination of potentially biased assessment components")
    print("=" * 80)
    
    # Analyze distributions
    component_data = analyze_component_distributions()
    
    # Identify bias patterns
    bias_issues = identify_bias_patterns(component_data)
    
    # Analyze correlations
    correlations = analyze_component_correlations(component_data)
    
    # Identify methodological issues
    method_issues = identify_specific_methodological_issues()
    
    # Summary report
    print(f"\n" + "=" * 80)
    print("SUSPICIOUS COMPONENT SUMMARY")
    print("=" * 80)
    
    total_issues = 0
    for component, issues in bias_issues.items():
        if issues:
            print(f"\n🚨 {component.upper()}:")
            for issue in issues:
                print(f"   - {issue}")
                total_issues += 1
    
    print(f"\n📊 OVERALL FINDINGS:")
    print(f"   Total bias issues identified: {total_issues}")
    print(f"   Components needing fixes: {len([c for c, i in bias_issues.items() if i])}")
    
    print(f"\n🔧 PRIORITY FIXES NEEDED:")
    if 'heat_hazard' in method_issues:
        print(f"   1. Heat hazard: Implement relative temperature scaling")
    if 'pluvial_hazard' in method_issues:
        print(f"   2. Pluvial hazard: Fix methodology for arid regions")
    if 'bio_trend_vulnerability' in method_issues:
        print(f"   3. Bio trend: Fix missing data handling")
    if 'income_vulnerability' in method_issues:
        print(f"   4. Income vulnerability: Fix GDP calculation logic")
    if 'viirs_exposure' in method_issues:
        print(f"   5. VIIRS exposure: Improve nightlight scaling")

if __name__ == "__main__":
    main()
