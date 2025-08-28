#!/usr/bin/env python3
"""
Integrated Water Scarcity and Climate Risk Assessment Runner
Combines GEE-backed water scarcity assessment with IPCC AR6 climate risk framework
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService
from services.climate_assessment_reporter import ClimateAssessmentReporter

def run_integrated_assessment():
    """Run the complete integrated water scarcity and climate risk assessment"""
    print("=" * 80)
    print("INTEGRATED WATER SCARCITY & CLIMATE RISK ASSESSMENT")
    print("IPCC AR6 Framework with GEE-backed Water Scarcity Analysis")
    print("=" * 80)

    # Initialize services
    base_path = os.path.dirname(os.path.abspath(__file__))
    data_loader = ClimateDataLoader(base_path)
    assessment_service = IPCCRiskAssessmentService(data_loader)

    # Run assessment for all cities
    print("\n🔍 Running integrated assessment for all cities...")
    all_results = assessment_service.assess_all_cities()

    # Display results
    print(f"\n📊 ASSESSMENT RESULTS ({len(all_results)} cities)")
    print("-" * 100)
    print(f"{'City':<12} {'Water Scarcity':<15} {'Vulnerability':<12} {'Hazard':<8} {'Exposure':<9} {'Adaptive':<9} {'Risk Level':<12}")
    print("-" * 100)

    for city, metrics in all_results.items():
        # Get water scarcity data
        water_data = assessment_service.water_scarcity_data.get(city, {})
        water_scarcity = water_data.get('water_scarcity_index', 0.0) if water_data else 0.0

        # Determine risk level
        overall_risk = metrics.overall_risk_score
        if overall_risk >= 0.7:
            risk_level = "🔴 Critical"
        elif overall_risk >= 0.5:
            risk_level = "🟠 High"
        elif overall_risk >= 0.3:
            risk_level = "🟡 Medium"
        else:
            risk_level = "🟢 Low"

        print(f"{city:<12} {water_scarcity:.3f}          {metrics.vulnerability_score:.3f}      {metrics.hazard_score:.3f}  {metrics.exposure_score:.3f}  {metrics.adaptive_capacity_score:.3f}  {risk_level}")

    # Generate report
    print("\n📄 Generating assessment report...")
    reporter = ClimateAssessmentReporter("suhi_analysis_output/reports")
    reporter.generate_comprehensive_report(all_results)

    print("\n✅ Integrated assessment completed successfully!")
    print("   - Water scarcity data integrated into IPCC AR6 vulnerability framework")
    print("   - Real satellite data used (CHIRPS, ERA5, JRC GSW, ESRI LULC)")
    print("   - Comprehensive report generated")

if __name__ == "__main__":
    run_integrated_assessment()
