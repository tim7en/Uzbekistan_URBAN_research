"""
Detailed analysis of Priority and Exposure score calculations
to understand why some cities have specific scores.
"""

import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))

from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService
from services.climate_assessment_reporter import ClimateAssessmentReporter

def analyze_priority_scoring():
    """Analyze how priority scores are calculated"""
    
    # Initialize services
    base_path = "suhi_analysis_output"
    data_loader = ClimateDataLoader(base_path=base_path)
    assessment_service = IPCCRiskAssessmentService(data_loader)
    
    # Get all city assessments
    city_risk_profiles = assessment_service.assess_all_cities()
    
    print("PRIORITY SCORE ANALYSIS")
    print("=" * 60)
    
    # Extract data for priority calculation
    cities = list(city_risk_profiles.keys())
    overall_risk_scores = [city_risk_profiles[city].overall_risk_score for city in cities]
    adaptive_capacity_scores = [city_risk_profiles[city].adaptive_capacity_score for city in cities]
    populations = [city_risk_profiles[city].population or 0 for city in cities]
    
    # Replicate the quantile scaling function
    def qscale(series, x, lo=0.1, hi=0.9):
        s = pd.Series(series)
        a, b = s.quantile(lo), s.quantile(hi)
        if a == b: 
            return 0.5
        return float(np.clip((x - a) / (b - a), 0, 1))

    print("STEP 1: Raw Input Data")
    print("-" * 30)
    for city in cities:
        risk = city_risk_profiles[city].overall_risk_score
        ac = city_risk_profiles[city].adaptive_capacity_score
        pop = city_risk_profiles[city].population or 0
        print(f"{city:12}: Risk={risk:.3f}, AC={ac:.3f}, Population={pop:,}")
    
    print(f"\nSTEP 2: Quantile Ranges (10th-90th percentiles)")
    print("-" * 30)
    risk_range = pd.Series(overall_risk_scores)
    ac_gap_values = [1 - a for a in adaptive_capacity_scores]
    pop_range = pd.Series(populations)
    
    print(f"Risk range: {risk_range.quantile(0.1):.3f} - {risk_range.quantile(0.9):.3f}")
    print(f"AC Gap range: {pd.Series(ac_gap_values).quantile(0.1):.3f} - {pd.Series(ac_gap_values).quantile(0.9):.3f}")
    print(f"Population range: {pop_range.quantile(0.1):,.0f} - {pop_range.quantile(0.9):,.0f}")
    
    print(f"\nSTEP 3: Quantile Scores (0-1 scale)")
    print("-" * 30)
    
    # Calculate quantile scores for each component
    risk_q = [qscale(overall_risk_scores, r) for r in overall_risk_scores]
    ac_gap = [1 - a for a in adaptive_capacity_scores]  # low AC => high gap
    ac_q = [qscale(ac_gap, g) for g in ac_gap]
    pop_q = [qscale(populations, p) for p in populations]
    
    for i, city in enumerate(cities):
        print(f"{city:12}: Risk_Q={risk_q[i]:.3f}, AC_Gap_Q={ac_q[i]:.3f}, Pop_Q={pop_q[i]:.3f}")
    
    print(f"\nSTEP 4: Priority Score Calculation")
    print("-" * 30)
    print("Formula: (Risk_Q^0.8) × (AC_Gap_Q^0.6) × (max(0.2, Pop_Q)^0.4)")
    
    # Calculate priority scores
    alpha, beta = 0.8, 0.6   # emphasis on risk, then AC gap
    priority_scores = [
        (rq ** alpha) * (aq ** beta) * (max(0.2, pq) ** 0.4)  # ensure small cities not zeroed
        for rq, aq, pq in zip(risk_q, ac_q, pop_q)
    ]
    
    # Sort by priority score for ranking
    city_priority_data = list(zip(cities, priority_scores, overall_risk_scores, adaptive_capacity_scores, populations))
    city_priority_data.sort(key=lambda x: x[1], reverse=True)  # Sort by priority score desc
    
    print(f"\nFINAL PRIORITY RANKINGS:")
    print("-" * 30)
    for i, (city, priority, risk, ac, pop) in enumerate(city_priority_data):
        print(f"{i+1:2}. {city:12}: Priority={priority:.3f} (Risk={risk:.3f}, AC={ac:.3f}, Pop={pop:,})")
    
    # Identify zero priority cities
    zero_priority_cities = [(city, priority) for city, priority in zip(cities, priority_scores) if priority < 0.001]
    if zero_priority_cities:
        print(f"\nCITIES WITH NEAR-ZERO PRIORITY:")
        print("-" * 30)
        for city, priority in zero_priority_cities:
            idx = cities.index(city)
            print(f"{city}: Priority={priority:.6f}")
            print(f"  - Risk quantile: {risk_q[idx]:.3f}")
            print(f"  - AC Gap quantile: {ac_q[idx]:.3f}")  
            print(f"  - Population quantile: {pop_q[idx]:.3f}")
            print(f"  - Why low: ", end="")
            reasons = []
            if risk_q[idx] < 0.1:
                reasons.append("Very low risk")
            if ac_q[idx] < 0.1:
                reasons.append("High adaptive capacity (low gap)")
            if pop_q[idx] < 0.1:
                reasons.append("Small population")
            print(", ".join(reasons) if reasons else "Mathematical result of quantile scaling")

def analyze_exposure_scoring():
    """Analyze how exposure scores are calculated, especially Tashkent's perfect 1.0"""
    
    # Initialize services
    base_path = "suhi_analysis_output"
    data_loader = ClimateDataLoader(base_path=base_path)
    assessment_service = IPCCRiskAssessmentService(data_loader)
    
    print("\n\nEXPOSURE SCORE ANALYSIS")
    print("=" * 60)
    
    # Get all cities and their data
    all_data = data_loader.load_all_data()
    cities = list(all_data['population_data'].keys())
    
    print("STEP 1: Raw Exposure Components")
    print("-" * 30)
    
    # Extract raw data for all cities
    populations = []
    densities = []
    built_areas = []
    nightlights = []
    
    for city in cities:
        pop_data = all_data['population_data'].get(city)
        if pop_data:
            populations.append(pop_data.population_2024)
            densities.append(pop_data.density_per_km2)
        else:
            populations.append(0)
            densities.append(0)
        
        # Built area from LULC data
        built_pct = 0
        for lulc_city in all_data['lulc_data']:
            if lulc_city.get('city') == city:
                areas = lulc_city.get('areas_m2', {})
                if areas:
                    years = sorted([int(y) for y in areas.keys()])
                    if years:
                        latest_year = str(years[-1])
                        built_pct = areas[latest_year].get('Built_Area', {}).get('percentage', 0)
                break
        built_areas.append(built_pct)
        
        # Nightlights
        nl_value = 0
        for nl_city in all_data['nightlights_data']:
            if nl_city.get('city') == city:
                years_data = nl_city.get('years', {})
                if years_data:
                    years = sorted([int(y) for y in years_data.keys()])
                    if years:
                        latest_year = str(years[-1])
                        nl_value = years_data[latest_year].get('stats', {}).get('urban_core', {}).get('mean', 0)
                break
        nightlights.append(nl_value)
    
    # Display raw data
    for i, city in enumerate(cities):
        print(f"{city:12}: Pop={populations[i]:,}, Density={densities[i]:,.0f}/km², Built={built_areas[i]:.1f}%, NL={nightlights[i]:.2f}")
    
    print(f"\nSTEP 2: Percentile Ranges (10th-90th percentiles)")
    print("-" * 30)
    
    # Calculate percentile ranges
    pop_series = pd.Series(populations)
    den_series = pd.Series(densities)
    built_series = pd.Series(built_areas)
    nl_series = pd.Series(nightlights)
    
    print(f"Population: {pop_series.quantile(0.1):,.0f} - {pop_series.quantile(0.9):,.0f}")
    print(f"Density: {den_series.quantile(0.1):,.0f} - {den_series.quantile(0.9):,.0f} /km²")
    print(f"Built Area: {built_series.quantile(0.1):.1f}% - {built_series.quantile(0.9):.1f}%")
    print(f"Nightlights: {nl_series.quantile(0.1):.2f} - {nl_series.quantile(0.9):.2f}")
    
    print(f"\nSTEP 3: Percentile Normalized Scores (0-1 scale)")
    print("-" * 30)
    
    # Calculate percentile normalized scores for each component
    pop_scores = [data_loader.pct_norm(all_data['cache']['population'], p) for p in populations]
    density_scores = [data_loader.pct_norm(all_data['cache']['density'], d) for d in densities]
    built_scores = [data_loader.pct_norm(all_data['cache']['built_pct'], b) for b in built_areas]
    nl_scores = [data_loader.pct_norm(all_data['cache']['nightlights'], n) for n in nightlights]
    
    for i, city in enumerate(cities):
        print(f"{city:12}: Pop_Score={pop_scores[i]:.3f}, Den_Score={density_scores[i]:.3f}, "
              f"Built_Score={built_scores[i]:.3f}, NL_Score={nl_scores[i]:.3f}")
    
    print(f"\nSTEP 4: Final Exposure Score Calculation")
    print("-" * 30)
    print("Formula: (0.4 × Pop_Score) + (0.25 × Density_Score) + (0.2 × Built_Score) + (0.15 × NL_Score)")
    
    # Calculate final exposure scores
    exposure_scores = []
    for i in range(len(cities)):
        exposure = (0.4 * pop_scores[i] + 0.25 * density_scores[i] + 
                   0.2 * built_scores[i] + 0.15 * nl_scores[i])
        exposure_scores.append(min(1.0, exposure))
    
    # Sort by exposure score
    city_exposure_data = list(zip(cities, exposure_scores, populations, densities, built_areas, nightlights))
    city_exposure_data.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\nFINAL EXPOSURE RANKINGS:")
    print("-" * 30)
    for i, (city, exposure, pop, den, built, nl) in enumerate(city_exposure_data):
        print(f"{i+1:2}. {city:12}: Exposure={exposure:.3f} (Pop={pop:,}, Den={den:,.0f}/km²)")
    
    # Special analysis for Tashkent
    tashkent_idx = cities.index('Tashkent')
    print(f"\nWHY TASHKENT HAS PERFECT EXPOSURE SCORE (1.000):")
    print("-" * 30)
    print(f"Tashkent population: {populations[tashkent_idx]:,}")
    print(f"Tashkent is the largest city by far")
    print(f"Population percentile score: {pop_scores[tashkent_idx]:.3f}")
    print(f"Density percentile score: {density_scores[tashkent_idx]:.3f}")
    print(f"Built area percentile score: {built_scores[tashkent_idx]:.3f}")
    print(f"Nightlights percentile score: {nl_scores[tashkent_idx]:.3f}")
    
    tashkent_exposure = (0.4 * pop_scores[tashkent_idx] + 0.25 * density_scores[tashkent_idx] + 
                        0.2 * built_scores[tashkent_idx] + 0.15 * nl_scores[tashkent_idx])
    print(f"Calculated exposure: {tashkent_exposure:.3f}")
    print(f"Final exposure (capped at 1.0): {min(1.0, tashkent_exposure):.3f}")
    
    if pop_scores[tashkent_idx] >= 0.99:
        print(f"NOTE: Tashkent gets perfect/near-perfect population score because it's the largest city")
        print(f"      This dominates the exposure calculation (40% weight)")

if __name__ == "__main__":
    analyze_priority_scoring()
    analyze_exposure_scoring()
