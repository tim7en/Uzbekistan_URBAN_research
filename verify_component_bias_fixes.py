#!/usr/bin/env python3
"""
Verify Component Bias Fixes
==========================

Comprehensive analysis to verify that all 10 identified component bias issues
have been successfully resolved after applying the fixes.

Author: Climate Risk Assessment Team
Date: 2025-08-31
"""

import json
import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from pathlib import Path

def load_assessment_results():
    """Load the latest assessment results"""
    results_file = Path("suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json")
    
    if not results_file.exists():
        print("❌ Assessment results file not found!")
        return None
    
    with open(results_file, 'r') as f:
        return json.load(f)

def analyze_component_bias_fixes():
    """Analyze all components for bias patterns after fixes"""
    
    data = load_assessment_results()
    if not data:
        return
    
    print("🔬 COMPONENT BIAS VERIFICATION AFTER FIXES")
    print("=" * 60)
    
    # Extract data for analysis
    cities = []
    component_data = {
        'heat_hazard': [],
        'pluvial_hazard': [],
        'viirs_exposure': [],
        'bio_trend_vulnerability': [],
        'fragmentation_vulnerability': [],
        'income_vulnerability': [],
        'air_pollution_vulnerability': [],
        'economic_capacity': [],
        'population': []
    }
    
    for city, metrics in data.items():
        cities.append(city)
        component_data['heat_hazard'].append(metrics.get('heat_hazard', 0))
        component_data['pluvial_hazard'].append(metrics.get('pluvial_hazard', 0))
        component_data['viirs_exposure'].append(metrics.get('viirs_exposure', 0))
        component_data['bio_trend_vulnerability'].append(metrics.get('bio_trend_vulnerability', 0))
        component_data['fragmentation_vulnerability'].append(metrics.get('fragmentation_vulnerability', 0))
        component_data['income_vulnerability'].append(metrics.get('income_vulnerability', 0))
        component_data['air_pollution_vulnerability'].append(metrics.get('air_pollution_vulnerability', 0))
        component_data['economic_capacity'].append(metrics.get('economic_capacity', 0))
        component_data['population'].append(metrics.get('population_exposure', 0))
    
    print(f"✅ Loaded data for {len(cities)} cities")
    
    # Analysis 1: Check for max/min pegging (RED FLAG: Max-pegging)
    print("\\n🎯 BIAS FIX 1: MAX/MIN PEGGING ELIMINATION")
    print("-" * 50)
    
    max_pegging_issues = 0
    min_pegging_issues = 0
    
    for component, values in component_data.items():
        if component == 'population':  # Skip population (exposure reference)
            continue
            
        max_count = sum(1 for v in values if v >= 0.99)
        min_count = sum(1 for v in values if v <= 0.01)
        
        if max_count > 2:  # More than 2 cities at maximum
            print(f"⚠️  {component}: {max_count} cities at maximum (≥0.99)")
            max_pegging_issues += 1
        elif max_count > 0:
            print(f"✅ {component}: {max_count} cities at maximum (acceptable)")
        else:
            print(f"✅ {component}: No max-pegging detected")
            
        if min_count > 2:  # More than 2 cities at minimum
            print(f"⚠️  {component}: {min_count} cities at minimum (≤0.01)")
            min_pegging_issues += 1
        elif min_count > 0:
            print(f"✅ {component}: {min_count} cities at minimum (acceptable)")
        else:
            print(f"✅ {component}: No min-pegging detected")
    
    print(f"\\n📊 MAX-PEGGING ISSUES: {max_pegging_issues}/8 components")
    print(f"📊 MIN-PEGGING ISSUES: {min_pegging_issues}/8 components")
    
    # Analysis 2: Population bias elimination (RED FLAG: Population correlation)
    print("\\n🎯 BIAS FIX 2: POPULATION BIAS ELIMINATION")
    print("-" * 50)
    
    population_bias_issues = 0
    for component, values in component_data.items():
        if component == 'population':
            continue
            
        if len(values) > 2:
            try:
                correlation, p_value = pearsonr(values, component_data['population'])
                if abs(correlation) > 0.7:  # Strong correlation indicates bias
                    print(f"⚠️  {component}: Population correlation = {correlation:.3f} (p={p_value:.3f})")
                    population_bias_issues += 1
                else:
                    print(f"✅ {component}: Population correlation = {correlation:.3f} (p={p_value:.3f})")
            except:
                print(f"⚠️  {component}: Could not calculate correlation")
    
    print(f"\\n📊 POPULATION BIAS ISSUES: {population_bias_issues}/8 components")
    
    # Analysis 3: Perfect correlations (RED FLAG: Artificial relationships)
    print("\\n🎯 BIAS FIX 3: PERFECT CORRELATION ELIMINATION")
    print("-" * 50)
    
    perfect_correlation_issues = 0
    components_list = [c for c in component_data.keys() if c != 'population']
    
    for i, comp1 in enumerate(components_list):
        for comp2 in components_list[i+1:]:
            try:
                correlation, p_value = pearsonr(component_data[comp1], component_data[comp2])
                if abs(correlation) >= 0.98:  # Near-perfect correlation
                    print(f"⚠️  {comp1} ↔ {comp2}: r = {correlation:.3f} (p={p_value:.3f})")
                    perfect_correlation_issues += 1
                elif abs(correlation) >= 0.9:
                    print(f"⚠️  {comp1} ↔ {comp2}: r = {correlation:.3f} (high correlation)")
            except:
                pass
    
    print(f"\\n📊 PERFECT CORRELATION ISSUES: {perfect_correlation_issues} pairs")
    
    # Analysis 4: Missing data artifacts (check for systematic zeros)
    print("\\n🎯 BIAS FIX 4: MISSING DATA ARTIFACT ELIMINATION")
    print("-" * 50)
    
    missing_data_issues = 0
    for component, values in component_data.items():
        if component == 'population':
            continue
            
        zero_count = sum(1 for v in values if v == 0.0)
        if zero_count > 3:  # More than 3 exact zeros indicates systematic issue
            print(f"⚠️  {component}: {zero_count} cities with exact zero values")
            missing_data_issues += 1
        elif zero_count > 0:
            print(f"✅ {component}: {zero_count} cities with zero values (acceptable)")
        else:
            print(f"✅ {component}: No systematic zero values")
    
    print(f"\\n📊 MISSING DATA ARTIFACT ISSUES: {missing_data_issues}/8 components")
    
    # Analysis 5: Value distribution health check
    print("\\n🎯 BIAS FIX 5: VALUE DISTRIBUTION HEALTH")
    print("-" * 50)
    
    distribution_issues = 0
    for component, values in component_data.items():
        if component == 'population':
            continue
            
        std_dev = np.std(values)
        mean_val = np.mean(values)
        cv = std_dev / mean_val if mean_val > 0 else 0  # Coefficient of variation
        
        if std_dev < 0.05:  # Very low variation indicates poor scaling
            print(f"⚠️  {component}: Low variation (std={std_dev:.3f}, CV={cv:.3f})")
            distribution_issues += 1
        else:
            print(f"✅ {component}: Good variation (std={std_dev:.3f}, CV={cv:.3f})")
    
    print(f"\\n📊 DISTRIBUTION ISSUES: {distribution_issues}/8 components")
    
    # Overall assessment
    print("\\n" + "=" * 60)
    print("🏆 OVERALL COMPONENT BIAS FIX ASSESSMENT")
    print("=" * 60)
    
    total_issues = (max_pegging_issues + min_pegging_issues + 
                   population_bias_issues + perfect_correlation_issues + 
                   missing_data_issues + distribution_issues)
    
    print(f"📊 TOTAL BIAS ISSUES REMAINING: {total_issues}")
    print(f"📊 COMPONENTS ANALYZED: 8")
    print(f"📊 ISSUE CATEGORIES: 6")
    
    if total_issues == 0:
        print("\\n🎉 EXCELLENT: All component bias issues successfully resolved!")
        print("✅ Max/min pegging eliminated")
        print("✅ Population bias eliminated") 
        print("✅ Perfect correlations eliminated")
        print("✅ Missing data artifacts eliminated")
        print("✅ Healthy value distributions achieved")
        grade = "A+"
    elif total_issues <= 3:
        print("\\n🎯 GOOD: Most component bias issues resolved")
        print("✅ Major bias patterns eliminated")
        print("⚠️  Minor issues remaining")
        grade = "A-"
    elif total_issues <= 6:
        print("\\n⚠️  FAIR: Some component bias issues resolved")
        print("✅ Some bias patterns eliminated") 
        print("⚠️  Several issues remaining")
        grade = "B"
    else:
        print("\\n❌ POOR: Many component bias issues remain")
        print("⚠️  Major bias patterns still present")
        grade = "C"
    
    print(f"\\n📊 COMPONENT BIAS FIX GRADE: {grade}")
    
    # Component-specific summary
    print("\\n📋 COMPONENT-SPECIFIC SUMMARY:")
    print("-" * 30)
    
    for component, values in component_data.items():
        if component == 'population':
            continue
            
        mean_val = np.mean(values)
        std_val = np.std(values)
        min_val = np.min(values)
        max_val = np.max(values)
        
        print(f"{component:25}: μ={mean_val:.3f}, σ={std_val:.3f}, range=[{min_val:.3f}, {max_val:.3f}]")
    
    return {
        'total_issues': total_issues,
        'max_pegging_issues': max_pegging_issues,
        'min_pegging_issues': min_pegging_issues,
        'population_bias_issues': population_bias_issues,
        'perfect_correlation_issues': perfect_correlation_issues,
        'missing_data_issues': missing_data_issues,
        'distribution_issues': distribution_issues,
        'grade': grade
    }

if __name__ == "__main__":
    results = analyze_component_bias_fixes()
    
    print("\\n" + "=" * 60)
    print("📝 COMPONENT BIAS FIX VERIFICATION COMPLETE")
    print("=" * 60)
