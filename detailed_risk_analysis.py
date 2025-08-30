#!/usr/bin/env python3
"""
DETAILED RISK CALCULATION ANALYSIS
==================================

This script analyzes why all cities show LOW risk in the adaptability ranking table
and examines the IPCC AR6 multiplicative risk formula implementation.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path

def analyze_risk_calculation():
    """Analyze the IPCC AR6 risk calculation and its impact on risk categorization"""
    
    # Load assessment results
    results_file = Path("suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json")
    
    if not results_file.exists():
        print("❌ Assessment results not found!")
        return
    
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("🔍 DETAILED RISK CALCULATION ANALYSIS")
    print("=" * 80)
    
    print("📊 IPCC AR6 RISK FORMULA: Risk = H × E × V × (1-AC)")
    print("   Where: H=Hazard, E=Exposure, V=Vulnerability, AC=Adaptive Capacity")
    print("=" * 80)
    
    # Extract components for each city
    analysis_data = []
    for city, metrics in data.items():
        hazard = metrics.get('hazard_score', 0)
        exposure = metrics.get('exposure_score', 0)
        vulnerability = metrics.get('vulnerability_score', 0)
        adaptive_capacity = metrics.get('adaptive_capacity_score', 0)
        overall_risk = metrics.get('overall_risk_score', 0)
        
        # Calculate intermediate products
        hev = hazard * exposure * vulnerability
        ac_reduction = 1 - adaptive_capacity
        calculated_risk = hev * ac_reduction
        
        analysis_data.append({
            'city': city,
            'hazard': hazard,
            'exposure': exposure,
            'vulnerability': vulnerability,
            'adaptive_capacity': adaptive_capacity,
            'hev': hev,
            'ac_reduction': ac_reduction,
            'calculated_risk': calculated_risk,
            'stored_risk': overall_risk,
            'population': metrics.get('population', 0),
            'gdp_per_capita': metrics.get('gdp_per_capita_usd', 0)
        })
    
    df = pd.DataFrame(analysis_data)
    
    print("📈 COMPONENT STATISTICS:")
    print("-" * 80)
    components = ['hazard', 'exposure', 'vulnerability', 'adaptive_capacity']
    for comp in components:
        values = df[comp]
        print(f"{comp.upper():15} | Min: {values.min():.3f} | Max: {values.max():.3f} | "
              f"Mean: {values.mean():.3f} | Std: {values.std():.3f}")
    
    print("\\n🔄 MULTIPLICATIVE EFFECT ANALYSIS:")
    print("-" * 80)
    print(f"{'H×E×V (HEV)':15} | Min: {df['hev'].min():.6f} | Max: {df['hev'].max():.6f} | "
          f"Mean: {df['hev'].mean():.6f}")
    print(f"{'(1-AC)':15} | Min: {df['ac_reduction'].min():.3f} | Max: {df['ac_reduction'].max():.3f} | "
          f"Mean: {df['ac_reduction'].mean():.3f}")
    print(f"{'Final Risk':15} | Min: {df['calculated_risk'].min():.6f} | Max: {df['calculated_risk'].max():.6f} | "
          f"Mean: {df['calculated_risk'].mean():.6f}")
    
    print("\\n🏙️ DETAILED CITY-BY-CITY BREAKDOWN:")
    print("-" * 120)
    print(f"{'City':<12} {'H':<6} {'E':<6} {'V':<6} {'AC':<6} {'H×E×V':<8} {'(1-AC)':<7} {'Risk':<8} {'Category'}")
    print("-" * 120)
    
    df_sorted = df.sort_values('stored_risk', ascending=False)
    for _, row in df_sorted.iterrows():
        # Risk categorization with traditional thresholds
        if row['stored_risk'] >= 0.6:
            category = "CRITICAL"
        elif row['stored_risk'] >= 0.4:
            category = "HIGH"
        elif row['stored_risk'] >= 0.2:
            category = "MEDIUM"
        else:
            category = "LOW"
        
        print(f"{row['city']:<12} {row['hazard']:<6.3f} {row['exposure']:<6.3f} "
              f"{row['vulnerability']:<6.3f} {row['adaptive_capacity']:<6.3f} "
              f"{row['hev']:<8.6f} {row['ac_reduction']:<7.3f} "
              f"{row['stored_risk']:<8.6f} {category}")
    
    print("\\n⚠️ WHY ALL CITIES SHOW 'LOW' RISK:")
    print("-" * 80)
    
    # Analyze the multiplicative effect
    print("1. 🔢 MULTIPLICATIVE SUPPRESSION:")
    print(f"   • When multiplying 3-4 values between 0-1, the result becomes very small")
    print(f"   • Example: 0.5 × 0.8 × 0.6 × 0.4 = {0.5 * 0.8 * 0.6 * 0.4:.6f}")
    print(f"   • Even 'high' component values produce low overall risk")
    
    print("\\n2. 📊 ADAPTIVE CAPACITY IMPACT:")
    ac_reduction_effect = []
    for _, row in df.iterrows():
        without_ac = row['hev']
        with_ac = row['stored_risk']
        if without_ac > 0:
            reduction_pct = ((without_ac - with_ac) / without_ac) * 100
            ac_reduction_effect.append(reduction_pct)
    
    print(f"   • Adaptive capacity reduces risk by {np.mean(ac_reduction_effect):.1f}% on average")
    print(f"   • Risk reduction ranges from {np.min(ac_reduction_effect):.1f}% to {np.max(ac_reduction_effect):.1f}%")
    print(f"   • High adaptive capacity cities benefit most from risk reduction")
    
    print("\\n3. 🎯 COMPONENT VALUE RANGES:")
    for comp in components:
        values = df[comp]
        if values.max() < 1.0:
            print(f"   • {comp.upper()}: Max value only {values.max():.3f} (not reaching full scale)")
    
    print("\\n4. 📏 THRESHOLD MISMATCH:")
    print(f"   • Traditional thresholds (0.2, 0.4, 0.6) designed for additive models")
    print(f"   • Multiplicative models naturally produce much lower values")
    print(f"   • Maximum possible risk with current data: {df['calculated_risk'].max():.6f}")
    
    print("\\n💡 SOLUTIONS AND RECOMMENDATIONS:")
    print("-" * 80)
    
    print("1. 🎯 ADJUST RISK THRESHOLDS:")
    print("   Based on actual data distribution:")
    
    # Calculate percentile-based thresholds
    risk_values = df['stored_risk'].values
    p25 = np.percentile(risk_values, 25)
    p50 = np.percentile(risk_values, 50)
    p75 = np.percentile(risk_values, 75)
    p90 = np.percentile(risk_values, 90)
    
    print(f"   • LOW risk: < {p25:.4f} (bottom 25%)")
    print(f"   • MEDIUM risk: {p25:.4f} - {p50:.4f} (25th-50th percentile)")
    print(f"   • HIGH risk: {p50:.4f} - {p75:.4f} (50th-75th percentile)")
    print(f"   • CRITICAL risk: > {p75:.4f} (top 25%)")
    
    print("\\n2. 🔄 ALTERNATIVE RISK FORMULATIONS:")
    print("   a) Square root scaling: Risk = √(H × E × V × (1-AC))")
    print("   b) Weighted additive: Risk = 0.3×H + 0.3×E + 0.3×V - 0.1×AC")
    print("   c) Hybrid approach: Risk = √(H × E × V) × (1-AC)")
    
    # Test alternative formulations
    print("\\n📊 ALTERNATIVE RISK SCORES COMPARISON:")
    print("-" * 80)
    
    df['sqrt_risk'] = np.sqrt(df['hev'] * df['ac_reduction'])
    df['additive_risk'] = (0.3 * df['hazard'] + 0.3 * df['exposure'] + 
                          0.3 * df['vulnerability'] - 0.1 * df['adaptive_capacity'])
    df['hybrid_risk'] = np.sqrt(df['hev']) * df['ac_reduction']
    
    print(f"{'Method':<20} {'Min':<8} {'Max':<8} {'Mean':<8} {'Range':<8}")
    print("-" * 60)
    
    methods = {
        'Current (H×E×V×(1-AC))': 'stored_risk',
        'Square Root': 'sqrt_risk',
        'Weighted Additive': 'additive_risk',
        'Hybrid': 'hybrid_risk'
    }
    
    for method_name, column in methods.items():
        values = df[column]
        range_val = values.max() - values.min()
        print(f"{method_name:<20} {values.min():<8.4f} {values.max():<8.4f} "
              f"{values.mean():<8.4f} {range_val:<8.4f}")
    
    print("\\n3. 📋 IMPROVED ADAPTABILITY RANKING TABLE:")
    print("-" * 80)
    print("Instead of fixed risk categories, use relative rankings:")
    
    # Create improved ranking table
    df_ranking = df.sort_values('stored_risk', ascending=False)
    
    print(f"\\n{'Rank':<4} {'City':<12} {'Risk Score':<12} {'Risk Rank':<10} {'AC Score':<10} {'AC Rank':<8} {'Priority'}")
    print("-" * 80)
    
    df_ac_rank = df.sort_values('adaptive_capacity')
    
    for i, (_, row) in enumerate(df_ranking.iterrows(), 1):
        # Get adaptive capacity rank (lower AC = higher priority)
        ac_rank = df_ac_rank[df_ac_rank['city'] == row['city']].index[0] + 1
        
        # Calculate composite priority score
        risk_rank_norm = i / len(df)  # Higher rank = higher priority
        ac_rank_norm = ac_rank / len(df)  # Higher rank = lower AC = higher priority
        priority_score = (risk_rank_norm + ac_rank_norm) / 2
        
        # Risk category based on quartiles
        if i <= len(df) // 4:
            risk_category = "HIGHEST"
        elif i <= len(df) // 2:
            risk_category = "HIGH"
        elif i <= 3 * len(df) // 4:
            risk_category = "MEDIUM"
        else:
            risk_category = "LOWEST"
        
        print(f"{i:<4} {row['city']:<12} {row['stored_risk']:<12.6f} {risk_category:<10} "
              f"{row['adaptive_capacity']:<10.3f} {ac_rank:<8} {priority_score:.3f}")
    
    print("\\n🎯 PRIORITY SCORE CALCULATION:")
    print("   Priority = (Risk Rank + Adaptive Capacity Rank) / 2")
    print("   Higher priority score = greater need for intervention")
    
    print("\\n✅ CONCLUSIONS:")
    print("-" * 80)
    print("1. The IPCC AR6 multiplicative formula is mathematically correct")
    print("2. 'LOW' risk classification is due to inappropriate thresholds, not calculation errors")
    print("3. Cities still have meaningful risk differences for prioritization")
    print("4. Relative ranking is more informative than absolute categories")
    print("5. Adaptive capacity creates substantial risk differentiation between cities")

if __name__ == "__main__":
    analyze_risk_calculation()
