#!/usr/bin/env python3
"""
ANALYZE RISK CATEGORIZATION AND ADAPTABILITY RANKING
===================================================

This script analyzes the risk categorization logic and adaptability ranking table
to understand why all cities show "LOW" risk and how priority scores are assigned.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path

def analyze_risk_categorization():
    """Analyze risk categorization and adaptability ranking logic"""
    
    # Load assessment results
    results_file = Path("suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json")
    
    if not results_file.exists():
        print("❌ Assessment results not found!")
        return
    
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("🔍 RISK CATEGORIZATION AND ADAPTABILITY RANKING ANALYSIS")
    print("=" * 80)
    
    # Extract risk scores
    risk_data = []
    for city, metrics in data.items():
        risk_score = metrics.get('overall_risk_score', 0)
        adaptability = metrics.get('adaptive_capacity_score', 0)
        adaptability_score = metrics.get('adaptability_score', 0)  # Check both keys
        
        risk_data.append({
            'city': city,
            'risk_score': risk_score,
            'adaptive_capacity': adaptability,
            'adaptability_score': adaptability_score,
            'population': metrics.get('population', 0),
            'gdp_per_capita': metrics.get('gdp_per_capita_usd', 0)
        })
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(risk_data)
    
    print(f"📊 RISK SCORE STATISTICS:")
    print(f"   Minimum Risk: {df['risk_score'].min():.6f}")
    print(f"   Maximum Risk: {df['risk_score'].max():.6f}")
    print(f"   Mean Risk: {df['risk_score'].mean():.6f}")
    print(f"   Median Risk: {df['risk_score'].median():.6f}")
    print(f"   Standard Deviation: {df['risk_score'].std():.6f}")
    
    print(f"\n📊 RISK DISTRIBUTION:")
    # Check different threshold schemes
    thresholds = [
        {"name": "Original (0.2, 0.4, 0.6)", "low": 0.2, "medium": 0.4, "high": 0.6},
        {"name": "Adjusted (0.05, 0.1, 0.15)", "low": 0.05, "medium": 0.1, "high": 0.15},
        {"name": "Percentile-based", "low": df['risk_score'].quantile(0.33), 
         "medium": df['risk_score'].quantile(0.67), "high": 1.0},
        {"name": "Standard Deviation", "low": df['risk_score'].mean() - df['risk_score'].std(),
         "medium": df['risk_score'].mean(), "high": df['risk_score'].mean() + df['risk_score'].std()}
    ]
    
    for threshold in thresholds:
        low_count = sum(1 for r in df['risk_score'] if r < threshold["low"])
        medium_count = sum(1 for r in df['risk_score'] if threshold["low"] <= r < threshold["medium"])
        high_count = sum(1 for r in df['risk_score'] if threshold["medium"] <= r < threshold["high"])
        critical_count = sum(1 for r in df['risk_score'] if r >= threshold["high"])
        
        print(f"\n   {threshold['name']}:")
        print(f"      🟢 LOW (<{threshold['low']:.3f}): {low_count} cities")
        print(f"      🟡 MEDIUM ({threshold['low']:.3f}-{threshold['medium']:.3f}): {medium_count} cities")
        print(f"      🟠 HIGH ({threshold['medium']:.3f}-{threshold['high']:.3f}): {high_count} cities")
        print(f"      🔴 CRITICAL (≥{threshold['high']:.3f}): {critical_count} cities")
    
    print(f"\n📋 DETAILED CITY RISK SCORES:")
    print("-" * 60)
    df_sorted = df.sort_values('risk_score', ascending=False)
    for idx, row in df_sorted.iterrows():
        # Categorize with original thresholds
        if row['risk_score'] >= 0.6:
            category = "🔴 CRITICAL"
        elif row['risk_score'] >= 0.4:
            category = "🟠 HIGH"
        elif row['risk_score'] >= 0.2:
            category = "🟡 MEDIUM"
        else:
            category = "🟢 LOW"
        
        # Categorize with adjusted thresholds
        if row['risk_score'] >= 0.15:
            adj_category = "🔴 CRITICAL"
        elif row['risk_score'] >= 0.1:
            adj_category = "🟠 HIGH"
        elif row['risk_score'] >= 0.05:
            adj_category = "🟡 MEDIUM"
        else:
            adj_category = "🟢 LOW"
        
        print(f"{row['city']:12} | Risk: {row['risk_score']:.6f} | "
              f"Original: {category:12} | Adjusted: {adj_category}")
    
    print(f"\n🛡️ ADAPTABILITY RANKING ANALYSIS:")
    print("-" * 60)
    
    # Check which adaptability metric is used
    print(f"Adaptive Capacity Score Range: {df['adaptive_capacity'].min():.3f} - {df['adaptive_capacity'].max():.3f}")
    if df['adaptability_score'].notna().any():
        print(f"Adaptability Score Range: {df['adaptability_score'].min():.3f} - {df['adaptability_score'].max():.3f}")
    
    # Sort by adaptive capacity (lower = worse adaptability = higher priority)
    df_adaptability = df.sort_values('adaptive_capacity')
    
    print(f"\n📊 ADAPTABILITY RANKING TABLE (Worst to Best):")
    print("-" * 80)
    print(f"{'Rank':<4} {'City':<12} {'Risk Score':<12} {'Adaptability':<12} {'Priority':<10}")
    print("-" * 80)
    
    for idx, (_, row) in enumerate(df_adaptability.iterrows(), 1):
        # Calculate priority score (example logic)
        risk_normalized = (row['risk_score'] - df['risk_score'].min()) / (df['risk_score'].max() - df['risk_score'].min())
        adaptability_inverted = 1 - row['adaptive_capacity']
        priority_score = (risk_normalized + adaptability_inverted) / 2
        
        # Risk category with adjusted thresholds
        if row['risk_score'] >= 0.15:
            risk_cat = "CRITICAL"
        elif row['risk_score'] >= 0.1:
            risk_cat = "HIGH"
        elif row['risk_score'] >= 0.05:
            risk_cat = "MEDIUM"
        else:
            risk_cat = "LOW"
        
        print(f"{idx:<4} {row['city']:<12} {row['risk_score']:<12.6f} "
              f"{row['adaptive_capacity']:<12.3f} {priority_score:<10.3f}")
    
    print(f"\n🔍 PRIORITY SCORE CALCULATION ANALYSIS:")
    print("-" * 60)
    
    # Analyze how priority scores might be calculated
    for idx, (_, row) in enumerate(df_adaptability.iterrows(), 1):
        risk_rank = len(df) - df_sorted[df_sorted['city'] == row['city']].index[0]
        adaptability_rank = idx
        
        # Different priority calculation methods
        priority_methods = {
            "Risk-weighted": row['risk_score'] * 0.7 + (1 - row['adaptive_capacity']) * 0.3,
            "Equal-weighted": (row['risk_score'] + (1 - row['adaptive_capacity'])) / 2,
            "Rank-based": (risk_rank + adaptability_rank) / 2,
            "Multiplicative": row['risk_score'] * (1 - row['adaptive_capacity'])
        }
        
        if idx <= 5:  # Show top 5
            print(f"\n{row['city']}:")
            for method, score in priority_methods.items():
                print(f"   {method}: {score:.4f}")
    
    print(f"\n⚠️ POTENTIAL ISSUES IDENTIFIED:")
    print("-" * 60)
    
    issues = []
    
    # Check if all risk scores are very low
    if df['risk_score'].max() < 0.2:
        issues.append("❌ All risk scores are below traditional 'LOW' threshold (0.2)")
        issues.append("   → Risk thresholds may need adjustment for this dataset")
    
    # Check risk score range
    risk_range = df['risk_score'].max() - df['risk_score'].min()
    if risk_range < 0.1:
        issues.append(f"❌ Very narrow risk score range ({risk_range:.6f})")
        issues.append("   → Limited differentiation between cities")
    
    # Check for potential calculation errors
    if df['risk_score'].min() < 0.001:
        issues.append("❌ Some cities have extremely low risk scores (<0.001)")
        issues.append("   → May indicate calculation issues or data artifacts")
    
    # Check adaptive capacity distribution
    ac_range = df['adaptive_capacity'].max() - df['adaptive_capacity'].min()
    if ac_range > 0.4:
        issues.append(f"✅ Good adaptive capacity differentiation (range: {ac_range:.3f})")
    else:
        issues.append(f"⚠️ Limited adaptive capacity differentiation (range: {ac_range:.3f})")
    
    for issue in issues:
        print(f"   {issue}")
    
    print(f"\n💡 RECOMMENDATIONS:")
    print("-" * 60)
    print("1. 🎯 ADJUST RISK THRESHOLDS:")
    print("   • Use percentile-based thresholds instead of fixed values")
    print("   • Consider dataset-specific thresholds (e.g., 0.05, 0.1, 0.15)")
    print("   • Implement relative risk categories within the data range")
    
    print("\n2. 🔍 VERIFY RISK CALCULATION:")
    print("   • Check if Risk = H × E × V × (1-AC) formula is correctly implemented")
    print("   • Verify that adaptive capacity is properly reducing risk")
    print("   • Ensure all components are on 0-1 scale")
    
    print("\n3. 📊 IMPROVE PRIORITY SCORING:")
    print("   • Combine risk score and adaptive capacity gaps")
    print("   • Weight by population or economic importance")
    print("   • Consider implementation feasibility")
    
    print("\n4. 📈 ENHANCE REPORTING:")
    print("   • Show relative risk rankings instead of absolute categories")
    print("   • Provide confidence intervals for risk estimates")
    print("   • Include sensitivity analysis for threshold choices")

if __name__ == "__main__":
    analyze_risk_categorization()
