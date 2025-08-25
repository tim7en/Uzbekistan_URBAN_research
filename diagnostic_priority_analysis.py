"""
Diagnostic script to analyze priority scoring vs risk scoring methodology
Helps understand why priority rankings differ from pure risk rankings
"""

import pandas as pd
import numpy as np
from pathlib import Path
from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService
from services.climate_assessment_reporter import ClimateAssessmentReporter


def analyze_priority_methodology():
    """Analyze and explain priority scoring methodology vs risk scoring"""
    
    # Load data using same path detection as main script
    repo_root = Path(__file__).resolve().parent
    candidates = [
        repo_root / "suhi_analysis_output",
        repo_root / "reports",
        Path.cwd() / "suhi_analysis_output", 
        Path.cwd() / "reports",
        repo_root
    ]
    
    base_path = None
    for c in candidates:
        if c.exists():
            base_path = c
            break
    
    if base_path is None:
        base_path = repo_root
        print(f"Warning: no suhi_analysis_output/reports folder found; using repo root: {base_path}")
    else:
        print(f"Using data base_path: {base_path}")
    
    # Initialize services
    data_loader = ClimateDataLoader(str(base_path))
    risk_assessor = IPCCRiskAssessmentService(data_loader)
    reporter = ClimateAssessmentReporter(str(base_path / "climate_assessment"))
    
    # Run assessment
    city_risk_profiles = risk_assessor.assess_all_cities()
    
    if not city_risk_profiles:
        print("No city data available for analysis")
        return
    
    # Extract raw data for analysis
    cities = list(city_risk_profiles.keys())
    data_rows = []
    
    for city in cities:
        metrics = city_risk_profiles[city]
        data_rows.append({
            'City': city,
            'Population': metrics.population or 0,
            'Hazard_Score': metrics.hazard_score,
            'Exposure_Score': metrics.exposure_score,
            'Vulnerability_Score': metrics.vulnerability_score,
            'Adaptive_Capacity_Score': metrics.adaptive_capacity_score,
            'Overall_Risk_Score': metrics.overall_risk_score,
            'Adaptability_Score': metrics.adaptability_score
        })
    
    df = pd.DataFrame(data_rows)
    
    # Calculate priority scores using same methodology as reporter
    priority_scores = reporter._calculate_priority_scores(city_risk_profiles)
    priority_labels = reporter._get_priority_labels(priority_scores)
    
    # Add priority data to dataframe
    df['Priority_Score'] = priority_scores
    df['Priority_Label'] = priority_labels
    
    # Calculate the quantile-based components used in priority scoring
    def qscale(series, x, lo=0.1, hi=0.9):
        s = pd.Series(series)
        a, b = s.quantile(lo), s.quantile(hi)
        if a == b: 
            return 0.5
        return float(np.clip((x - a) / (b - a), 0, 1))
    
    overall_risk_scores = df['Overall_Risk_Score'].tolist()
    adaptive_capacity_scores = df['Adaptive_Capacity_Score'].tolist()
    populations = df['Population'].tolist()
    
    risk_q = [qscale(overall_risk_scores, r) for r in overall_risk_scores]
    ac_gap = [1 - a for a in adaptive_capacity_scores]  # low AC => high gap
    ac_q = [qscale(ac_gap, g) for g in ac_gap]
    pop_q = [qscale(populations, p) for p in populations]
    
    # Add quantile components to dataframe
    df['Risk_Quantile'] = risk_q
    df['AC_Gap_Quantile'] = ac_q
    df['Population_Quantile'] = pop_q
    
    # Calculate manual priority to verify formula
    alpha, beta = 0.8, 0.6
    manual_priority = [
        (rq ** alpha) * (aq ** beta) * (max(0.2, pq) ** 0.4)
        for rq, aq, pq in zip(risk_q, ac_q, pop_q)
    ]
    df['Manual_Priority_Check'] = manual_priority
    
    # Add risk categories
    df['Risk_Category'] = [reporter.risk_category_from_score(r) for r in overall_risk_scores]
    
    # Sort by priority score (descending) to match table
    df_by_priority = df.sort_values('Priority_Score', ascending=False).reset_index(drop=True)
    df_by_risk = df.sort_values('Overall_Risk_Score', ascending=False).reset_index(drop=True)
    
    print("\n" + "="*100)
    print("PRIORITY SCORING METHODOLOGY ANALYSIS")
    print("="*100)
    
    print(f"\nOverall Risk Score Range: {df['Overall_Risk_Score'].min():.3f} - {df['Overall_Risk_Score'].max():.3f}")
    print(f"Priority Score Range: {df['Priority_Score'].min():.3f} - {df['Priority_Score'].max():.3f}")
    
    print(f"\nPRIORITY FORMULA:")
    print(f"  Priority = (Risk_Quantile^{alpha}) * (AC_Gap_Quantile^{beta}) * (max(0.2, Pop_Quantile)^0.4)")
    print(f"  Where:")
    print(f"    - Risk_Quantile = percentile rank of raw risk score (10th-90th percentile scaling)")
    print(f"    - AC_Gap_Quantile = percentile rank of (1 - adaptive_capacity)")
    print(f"    - Pop_Quantile = percentile rank of population")
    print(f"    - Alpha={alpha} (risk emphasis), Beta={beta} (AC gap emphasis)")
    
    print(f"\nTOP 5 CITIES BY PRIORITY SCORE:")
    print(df_by_priority[['City', 'Overall_Risk_Score', 'Risk_Category', 'Priority_Score', 'Priority_Label',
                         'Risk_Quantile', 'AC_Gap_Quantile', 'Population_Quantile']].head().to_string(index=False))
    
    print(f"\nTOP 5 CITIES BY RAW RISK SCORE:")
    print(df_by_risk[['City', 'Overall_Risk_Score', 'Risk_Category', 'Priority_Score', 'Priority_Label',
                     'Population']].head().to_string(index=False))
    
    print(f"\nKEY DIFFERENCES EXPLANATION:")
    
    # Find cities with high risk but low priority
    high_risk_low_priority = df[(df['Overall_Risk_Score'] > df['Overall_Risk_Score'].quantile(0.7)) & 
                               (df['Priority_Score'] < df['Priority_Score'].quantile(0.5))]
    
    if not high_risk_low_priority.empty:
        print(f"\nCities with HIGH RISK but LOW PRIORITY:")
        for _, row in high_risk_low_priority.iterrows():
            print(f"  {row['City']}: Risk={row['Overall_Risk_Score']:.3f}, Priority={row['Priority_Score']:.3f}")
            print(f"    -> Population: {row['Population']:,} (Pop_Quantile: {row['Population_Quantile']:.2f})")
            print(f"    -> AC Score: {row['Adaptive_Capacity_Score']:.3f} (AC_Gap_Quantile: {row['AC_Gap_Quantile']:.2f})")
            print(f"    -> Reason: Low population and/or high adaptive capacity reduces priority")
    
    # Find cities with low risk but high priority
    low_risk_high_priority = df[(df['Overall_Risk_Score'] < df['Overall_Risk_Score'].quantile(0.3)) & 
                               (df['Priority_Score'] > df['Priority_Score'].quantile(0.7))]
    
    if not low_risk_high_priority.empty:
        print(f"\nCities with LOW RISK but HIGH PRIORITY:")
        for _, row in low_risk_high_priority.iterrows():
            print(f"  {row['City']}: Risk={row['Overall_Risk_Score']:.3f}, Priority={row['Priority_Score']:.3f}")
            print(f"    -> Population: {row['Population']:,} (Pop_Quantile: {row['Population_Quantile']:.2f})")
            print(f"    -> AC Score: {row['Adaptive_Capacity_Score']:.3f} (AC_Gap_Quantile: {row['AC_Gap_Quantile']:.2f})")
            print(f"    -> Reason: Large population and/or low adaptive capacity increases priority")
    
    # Save detailed diagnostic CSV
    output_file = base_path / "climate_assessment" / "priority_methodology_diagnostics.csv"
    df_detailed = df_by_priority[['City', 'Population', 'Overall_Risk_Score', 'Risk_Category', 
                                 'Adaptive_Capacity_Score', 'Priority_Score', 'Priority_Label',
                                 'Risk_Quantile', 'AC_Gap_Quantile', 'Population_Quantile',
                                 'Hazard_Score', 'Exposure_Score', 'Vulnerability_Score']]
    df_detailed.to_csv(output_file, index=False)
    print(f"\n✓ Saved detailed diagnostics to: {output_file}")
    
    print("="*100)
    
    return df


if __name__ == "__main__":
    analyze_priority_methodology()
