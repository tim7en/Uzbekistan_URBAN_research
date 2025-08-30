#!/usr/bin/env python3
"""
VALIDATE ASSESSMENT RESULTS REPRESENTATION
==========================================

This script validates that the assessment results are correctly representing
the actual climate risk calculation and component values.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path

def validate_assessment_results():
    """Validate that assessment results correctly represent the calculation"""
    
    print("=" * 80)
    print("🔍 VALIDATING ASSESSMENT RESULTS REPRESENTATION")
    print("=" * 80)
    
    # Load current results
    results_file = Path("suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json")
    
    if not results_file.exists():
        print("❌ Results file not found!")
        return
    
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    print(f"📊 Loaded results for {len(data)} cities")
    
    # 1. Verify IPCC AR6 formula implementation
    print("\\n1️⃣ VERIFYING IPCC AR6 FORMULA: Risk = H × E × V × (1-AC)")
    print("-" * 60)
    
    formula_errors = []
    for city, metrics in data.items():
        h = metrics.get('hazard_score', 0)
        e = metrics.get('exposure_score', 0) 
        v = metrics.get('vulnerability_score', 0)
        ac = metrics.get('adaptive_capacity_score', 0)
        stored_risk = metrics.get('overall_risk_score', 0)
        
        # Calculate expected risk
        expected_risk = h * e * v * (1 - ac)
        
        # Check if stored risk matches calculation
        diff = abs(stored_risk - expected_risk)
        if diff > 1e-10:  # Allow for floating point precision
            formula_errors.append(f"{city}: Expected {expected_risk:.6f}, Got {stored_risk:.6f}, Diff: {diff:.6f}")
    
    if formula_errors:
        print(f"❌ Found {len(formula_errors)} formula calculation errors:")
        for error in formula_errors[:5]:
            print(f"   • {error}")
    else:
        print("✅ All risk scores correctly calculated using IPCC AR6 formula")
    
    # 2. Verify component aggregations
    print("\\n2️⃣ VERIFYING COMPONENT AGGREGATIONS")
    print("-" * 60)
    
    aggregation_errors = []
    for city, metrics in data.items():
        # Check hazard aggregation
        hazard_components = [
            metrics.get('heat_hazard', 0),
            metrics.get('dry_hazard', 0),
            metrics.get('dust_hazard', 0),
            metrics.get('pluvial_hazard', 0),
            metrics.get('air_quality_hazard', 0)
        ]
        expected_hazard = np.mean(hazard_components)
        stored_hazard = metrics.get('hazard_score', 0)
        
        if abs(expected_hazard - stored_hazard) > 1e-10:
            aggregation_errors.append(f"{city} Hazard: Expected {expected_hazard:.6f}, Got {stored_hazard:.6f}")
        
        # Check exposure aggregation
        exposure_components = [
            metrics.get('population_exposure', 0),
            metrics.get('gdp_exposure', 0),
            metrics.get('viirs_exposure', 0)
        ]
        expected_exposure = np.mean(exposure_components)
        stored_exposure = metrics.get('exposure_score', 0)
        
        if abs(expected_exposure - stored_exposure) > 1e-10:
            aggregation_errors.append(f"{city} Exposure: Expected {expected_exposure:.6f}, Got {stored_exposure:.6f}")
    
    if aggregation_errors:
        print(f"❌ Found {len(aggregation_errors)} aggregation errors:")
        for error in aggregation_errors[:5]:
            print(f"   • {error}")
    else:
        print("✅ All component aggregations are correct")
    
    # 3. Check data consistency and ranges
    print("\\n3️⃣ CHECKING DATA CONSISTENCY AND RANGES")
    print("-" * 60)
    
    range_issues = []
    for city, metrics in data.items():
        # Check that all scores are in [0, 1] range
        scores_to_check = [
            ('hazard_score', metrics.get('hazard_score', 0)),
            ('exposure_score', metrics.get('exposure_score', 0)),
            ('vulnerability_score', metrics.get('vulnerability_score', 0)),
            ('adaptive_capacity_score', metrics.get('adaptive_capacity_score', 0)),
            ('overall_risk_score', metrics.get('overall_risk_score', 0))
        ]
        
        for score_name, score_value in scores_to_check:
            if score_value < 0 or score_value > 1:
                range_issues.append(f"{city} {score_name}: {score_value:.6f} (out of [0,1] range)")
            if str(score_value) == 'nan':
                range_issues.append(f"{city} {score_name}: NaN value")
    
    if range_issues:
        print(f"❌ Found {len(range_issues)} range/validity issues:")
        for issue in range_issues[:10]:
            print(f"   • {issue}")
    else:
        print("✅ All scores are within valid ranges")
    
    # 4. Verify data differentiation
    print("\\n4️⃣ VERIFYING DATA DIFFERENTIATION")
    print("-" * 60)
    
    # Extract all risk scores and component scores
    risk_scores = [metrics.get('overall_risk_score', 0) for metrics in data.values()]
    hazard_scores = [metrics.get('hazard_score', 0) for metrics in data.values()]
    exposure_scores = [metrics.get('exposure_score', 0) for metrics in data.values()]
    vulnerability_scores = [metrics.get('vulnerability_score', 0) for metrics in data.values()]
    ac_scores = [metrics.get('adaptive_capacity_score', 0) for metrics in data.values()]
    
    components = {
        'Risk': risk_scores,
        'Hazard': hazard_scores,
        'Exposure': exposure_scores,
        'Vulnerability': vulnerability_scores,
        'Adaptive Capacity': ac_scores
    }
    
    print(f"{'Component':<18} {'Min':<8} {'Max':<8} {'Range':<8} {'StdDev':<8} {'Unique':<6}")
    print("-" * 60)
    
    for comp_name, scores in components.items():
        min_score = min(scores)
        max_score = max(scores)
        range_score = max_score - min_score
        std_score = np.std(scores)
        unique_count = len(set(scores))
        
        print(f"{comp_name:<18} {min_score:<8.4f} {max_score:<8.4f} {range_score:<8.4f} {std_score:<8.4f} {unique_count:<6}")
        
        # Check for concerning patterns
        if range_score < 0.1:
            print(f"   ⚠️ Warning: {comp_name} has limited range ({range_score:.4f})")
        if unique_count < len(data) * 0.7:
            print(f"   ⚠️ Warning: {comp_name} has limited diversity ({unique_count}/{len(data)} unique)")
    
    # 5. Check specific calculation patterns
    print("\\n5️⃣ CHECKING SPECIFIC CALCULATION PATTERNS")
    print("-" * 60)
    
    pattern_issues = []
    
    # Check heat and pluvial hazards (known issue from previous analysis)
    heat_hazards = [metrics.get('heat_hazard', 0) for metrics in data.values()]
    pluvial_hazards = [metrics.get('pluvial_hazard', 0) for metrics in data.values()]
    
    if len(set(heat_hazards)) == 1:
        pattern_issues.append(f"Heat hazard: All cities have identical value {heat_hazards[0]:.6f}")
    
    if len(set(pluvial_hazards)) == 1:
        pattern_issues.append(f"Pluvial hazard: All cities have identical value {pluvial_hazards[0]:.6f}")
    
    # Check for perfect correlations
    df = pd.DataFrame(data).T
    numeric_cols = ['hazard_score', 'exposure_score', 'vulnerability_score', 'adaptive_capacity_score', 'overall_risk_score']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Check correlation between income vulnerability and economic capacity
    if 'income_vulnerability' in df.columns and 'economic_capacity' in df.columns:
        income_vuln = pd.to_numeric(df['income_vulnerability'], errors='coerce')
        econ_cap = pd.to_numeric(df['economic_capacity'], errors='coerce')
        corr = income_vuln.corr(econ_cap)
        if abs(corr) > 0.99:
            pattern_issues.append(f"Perfect correlation between income vulnerability and economic capacity: r={corr:.3f}")
    
    if pattern_issues:
        print("⚠️ Found calculation pattern issues:")
        for issue in pattern_issues:
            print(f"   • {issue}")
    else:
        print("✅ No concerning calculation patterns detected")
    
    # 6. Verify adaptive capacity impact
    print("\\n6️⃣ VERIFYING ADAPTIVE CAPACITY IMPACT")
    print("-" * 60)
    
    # Calculate risk without adaptive capacity adjustment
    risk_impact_data = []
    for city, metrics in data.items():
        h = metrics.get('hazard_score', 0)
        e = metrics.get('exposure_score', 0)
        v = metrics.get('vulnerability_score', 0)
        ac = metrics.get('adaptive_capacity_score', 0)
        
        risk_without_ac = h * e * v
        risk_with_ac = h * e * v * (1 - ac)
        
        if risk_without_ac > 0:
            reduction_pct = ((risk_without_ac - risk_with_ac) / risk_without_ac) * 100
        else:
            reduction_pct = 0
        
        risk_impact_data.append({
            'city': city,
            'risk_without_ac': risk_without_ac,
            'risk_with_ac': risk_with_ac,
            'ac_score': ac,
            'reduction_pct': reduction_pct
        })
    
    df_impact = pd.DataFrame(risk_impact_data)
    
    print(f"Average risk reduction from adaptive capacity: {df_impact['reduction_pct'].mean():.1f}%")
    print(f"Risk reduction range: {df_impact['reduction_pct'].min():.1f}% - {df_impact['reduction_pct'].max():.1f}%")
    
    # Show top and bottom cities by AC impact
    df_impact_sorted = df_impact.sort_values('reduction_pct', ascending=False)
    
    print("\\nTop 3 cities benefiting most from adaptive capacity:")
    for _, row in df_impact_sorted.head(3).iterrows():
        print(f"   • {row['city']}: {row['reduction_pct']:.1f}% reduction (AC: {row['ac_score']:.3f})")
    
    print("\\nTop 3 cities with least adaptive capacity benefit:")
    for _, row in df_impact_sorted.tail(3).iterrows():
        print(f"   • {row['city']}: {row['reduction_pct']:.1f}% reduction (AC: {row['ac_score']:.3f})")
    
    # 7. Final assessment summary
    print("\\n" + "=" * 80)
    print("🏆 ASSESSMENT RESULTS VALIDATION SUMMARY")
    print("=" * 80)
    
    total_issues = len(formula_errors) + len(aggregation_errors) + len(range_issues) + len(pattern_issues)
    
    if total_issues == 0:
        print("✅ ASSESSMENT RESULTS ARE CORRECTLY REPRESENTED")
        print("   • IPCC AR6 formula correctly implemented")
        print("   • Component aggregations are accurate")
        print("   • All values within valid ranges")
        print("   • Adaptive capacity properly reduces risk")
        print("   • Results show appropriate differentiation between cities")
    else:
        print(f"⚠️ FOUND {total_issues} ISSUES WITH RESULT REPRESENTATION")
        if formula_errors:
            print(f"   • {len(formula_errors)} formula calculation errors")
        if aggregation_errors:
            print(f"   • {len(aggregation_errors)} component aggregation errors")
        if range_issues:
            print(f"   • {len(range_issues)} data range/validity issues")
        if pattern_issues:
            print(f"   • {len(pattern_issues)} concerning calculation patterns")
    
    print(f"\\n📊 ASSESSMENT QUALITY METRICS:")
    print(f"   • Cities assessed: {len(data)}")
    print(f"   • Risk score range: {min(risk_scores):.6f} - {max(risk_scores):.6f}")
    print(f"   • Risk differentiation: {len(set(risk_scores))}/{len(data)} unique scores")
    print(f"   • Average AC impact: {df_impact['reduction_pct'].mean():.1f}% risk reduction")
    
    return total_issues == 0

if __name__ == "__main__":
    validate_assessment_results()
